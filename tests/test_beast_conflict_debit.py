import ast
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from unittest.mock import Mock
from types import SimpleNamespace
import wjdr_backend as b

DAY = '2026-11-04'

class ConflictDebitTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / 'ledger.json'
        self.path.write_text(json.dumps({'version': 2, 'accounts': {
            'a': {'day': DAY, 'spent': 11, 'uncertain': 70, 'reserved': 0},
            'b': {'day': DAY, 'spent': 3, 'uncertain': 45, 'reserved': 0}}}), encoding='utf-8')
        b.reserve_beast_rally_stamina('a', 25, day=DAY, path=self.path)
        b.archive_beast_rally_unconfirmed_reservation('a', 25, day=DAY, path=self.path)
        self.token = b.load_beast_rally_submitted_pending('a', path=self.path)

    def data(self):
        return json.loads(self.path.read_text(encoding='utf-8'))

    def cancel(self, identity='a', token=None, **kw):
        return b.cancel_beast_rally_submitted_conflict(identity, self.token if token is None else token,
                  cancelled_and_formation_restored=True, day=DAY, path=self.path, **kw)

    def test_linked_cancellation_is_atomic_once_and_does_not_touch_other_history(self):
        before = self.data()
        self.assertEqual(before['accounts']['a']['uncertain'], 95)
        self.assertEqual(self.cancel(), 25)
        after = self.data()
        self.assertEqual(after['accounts']['a']['uncertain'], 70)
        self.assertEqual(after['accounts']['a']['spent'], 11)
        self.assertEqual(after['accounts']['b'], before['accounts']['b'])
        self.assertEqual(after['accounts']['a']['last_recovery'], before['accounts']['a']['last_recovery'])
        self.assertNotIn('submitted_pending', after['accounts']['a'])
        self.assertNotIn('submitted_debit', after['accounts']['a'])
        with self.assertRaises(ValueError): self.cancel()
        self.assertEqual(self.data(), after)

    def test_legacy_marker_never_guesses_or_changes_history(self):
        payload = self.data(); del payload['accounts']['a']['submitted_debit']
        self.path.write_text(json.dumps(payload), encoding='utf8')
        self.assertIsNone(self.cancel())
        self.assertEqual(self.data(), payload)

    def test_mismatch_or_unconfirmed_evidence_preserves_file(self):
        before = self.data()
        for identity, token in [('a', 'wrong'), ('b', self.token), ('missing', self.token)]:
            with self.subTest(identity=identity), self.assertRaises(ValueError): self.cancel(identity, token)
            self.assertEqual(self.data(), before)
        with self.assertRaises(ValueError):
            b.cancel_beast_rally_submitted_conflict('a', self.token, day=DAY, path=self.path)
        self.assertEqual(self.data(), before)

    def test_insufficient_total_wrong_link_cross_day_and_reservation_fail_closed(self):
        for field, value in [('uncertain', 24), ('reserved', 25), ('day', '2026-11-03')]:
            with self.subTest(field=field):
                original = self.data(); damaged = json.loads(json.dumps(original))
                damaged['accounts']['a'][field] = value
                self.path.write_text(json.dumps(damaged), encoding='utf8')
                with self.assertRaises(ValueError): self.cancel()
                self.assertEqual(self.data(), damaged)
                self.path.write_text(json.dumps(original), encoding='utf8')
        original = self.data(); damaged = json.loads(json.dumps(original))
        damaged['accounts']['a']['submitted_debit']['token'] = 'not-the-token'
        self.path.write_text(json.dumps(damaged), encoding='utf8')
        with self.assertRaises(ValueError): self.cancel()
        self.assertEqual(self.data(), damaged)

    def test_write_failure_preserves_marker_total_and_retry_is_once(self):
        before = self.data()
        with patch.object(b.os, 'replace', side_effect=OSError('disk full')):
            with self.assertRaises(OSError): self.cancel()
        self.assertEqual(self.data(), before)
        self.assertEqual(self.cancel(), 25)
        with self.assertRaises(ValueError): self.cancel()

    def test_committed_but_acknowledgement_failed_cannot_reverse_twice(self):
        write = b._durable_beast_item_write
        def commit_then_fail(*args):
            write(*args)
            raise OSError('lost acknowledgement')
        with patch.object(b, '_durable_beast_item_write', side_effect=commit_then_fail):
            with self.assertRaises(OSError): self.cancel()
        committed = self.data()
        self.assertEqual(committed['accounts']['a']['uncertain'], 70)
        with self.assertRaises(ValueError): self.cancel()
        self.assertEqual(self.data(), committed)

    def test_normal_marker_clear_does_not_change_uncertain(self):
        b.clear_beast_rally_submitted_pending('a', self.token, path=self.path)
        account = self.data()['accounts']['a']
        self.assertEqual(account['uncertain'], 95)
        self.assertNotIn('submitted_pending', account)
        self.assertNotIn('submitted_debit', account)

    def test_orphaned_link_blocks_new_reservation_before_any_input(self):
        payload = self.data(); del payload['accounts']['a']['submitted_pending']
        self.path.write_text(json.dumps(payload), encoding='utf8')
        with self.assertRaises(ValueError):
            b.reserve_beast_rally_stamina('a', 25, day=DAY, path=self.path)
        self.assertEqual(self.data(), payload)


class ConflictControllerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        source = Path(__file__).with_name('wjdr_mumu_assistant_qt.py')
        if not source.exists():
            source = Path(__file__).resolve().parents[1] / 'wjdr_mumu_assistant_qt.py'
        tree = ast.parse(source.read_text(encoding='utf8'))
        node = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == 'run_one_cycle')
        outer = next(n for n in node.body if isinstance(n, ast.If)
                     and ast.unparse(n.test) == 'not reconciliation_only and recent_unconfirmed_dispatch and (not item_pending)')
        conflict = outer.body[0]
        outer.body = [conflict, ast.parse('return pending_submission_token, recent_unconfirmed_dispatch').body[0]]
        stop = node.body.index(outer)
        node.body = [n for n in node.body[:stop+1] if not isinstance(n, ast.Nonlocal)]
        node.body[0:0] = ast.parse('pending_submission_token = initial_token\nrecent_unconfirmed_dispatch = True').body
        node.body.append(ast.parse('raise AssertionError("missed conflict branch")').body[0])
        cls.code = compile(ast.fix_missing_locations(ast.Module(body=[node], type_ignores=[])), str(source), 'exec')

    def run_case(self, *, result=25, conflict=True, restored=True, stopped=False, lease_error=False):
        target = Mock(device='test')
        if lease_error: target.check_active.side_effect = InterruptedError('lost lease')
        fake = Mock(return_value=result)
        env = dict(initial_token='tok', capture=lambda:'warning',
            match_wilderness_context=lambda _: (None,None),
            load_beast_stamina_item_pending=lambda _: None, identity='a',
            completed_cycles=0, match_world=lambda _: (None,None), profile=SimpleNamespace(run_mode='normal'),
            daily_network_dialog_is_visible=lambda *_: False,
            match_same_target_conflict=lambda _: (2,3) if conflict else None,
            beast_close_paid_stamina_overlay=lambda *a,**kw: None,
            target=target, stable=lambda a,b: a==b, threshold=.9,
            formation_controls_match=lambda _: (None,None),
            self=SimpleNamespace(stop_event=SimpleNamespace(is_set=lambda: stopped), _log_for_device=Mock()),
            resolve_target_conflict=Mock(return_value=restored))
        exec(self.code, env)
        with patch.object(b, 'cancel_beast_rally_submitted_conflict', fake):
            if lease_error:
                with self.assertRaises(InterruptedError): env['run_one_cycle']()
                result = 'lease-lost'
            else: result = env['run_one_cycle']()
        return result, fake, target

    def test_proved_cancel_reverses_only_once_and_clears_local_token(self):
        result, cancel, target = self.run_case()
        self.assertEqual(result, (None, False))
        target.check_active.assert_called_once()
        cancel.assert_called_once_with('a', 'tok', cancelled_and_formation_restored=True)

    def test_old_token_leaves_pending_and_unknown_ledger_untouched(self):
        result, cancel, _ = self.run_case(result=None)
        self.assertEqual(result, ('tok', True))
        cancel.assert_called_once()

    def test_missing_restoration_stop_or_lease_loss_never_reverses(self):
        for options in ({'restored': False}, {'stopped': True}, {'lease_error': True}):
            with self.subTest(options=options):
                _, cancel, _ = self.run_case(**options)
                cancel.assert_not_called()


if __name__ == '__main__': unittest.main()
