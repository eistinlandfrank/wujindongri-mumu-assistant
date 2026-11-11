import ast
import unittest
from pathlib import Path
from types import SimpleNamespace


class StartupReconciliationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        source = Path(__file__).resolve().parents[1] / 'wjdr_mumu_assistant_qt.py'
        tree = ast.parse(source.read_text(encoding='utf8'))
        node = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == 'run_one_cycle')
        end = next(i for i, n in enumerate(node.body)
                   if isinstance(n, ast.If) and isinstance(n.test, ast.Name) and n.test.id == 'reconciliation_only')
        node.body = [n for n in node.body[:end + 1] if not isinstance(n, ast.Nonlocal)]
        # The extracted function has no enclosing worker closure; supply its
        # initial submitted-state value exactly as the real worker does.
        node.body.insert(0, ast.parse('recent_unconfirmed_dispatch = False').body[0])
        node.body.append(ast.parse('raise AssertionError("entered game input path")').body[0])
        node.returns = None
        cls.module = compile(ast.fix_missing_locations(ast.Module(body=[node], type_ignores=[])), str(source), 'exec')

    def run_case(self, pending, *, network=False, confirmed=False):
        calls = []
        ns = dict(capture=lambda: object(), match_wilderness_context=lambda _: (None, None),
                  beast_close_paid_stamina_overlay=lambda *a, **kw: None,
                  old_reservation=0, beast_reconcile_sent_item_overlay=lambda *a, **kw: False,
                  load_beast_stamina_item_pending=lambda _: pending,
                  stamina_more_controls_match=lambda _: ((1, 1), None),
                  read_beast_stamina_item_observation=lambda _: (12, 30),
                  stable=lambda a, b: a == b,
                  daily_network_dialog_is_visible=lambda *_: network,
                  confirm_beast_stamina_item_use=lambda *a: calls.append('confirm') or confirmed,
                  record_beast_stamina_batch_partial=lambda *a: calls.append('partial'),
                  beast_shield_plus_pending=lambda _: False,
                  read_beast_rally_collapsed_march_capacity=lambda *_: None,
                  match_world=lambda _: (None, None),
                  match_same_target_conflict=lambda _: None,
                  self=SimpleNamespace(stop_event=SimpleNamespace(is_set=lambda: False), _log_for_device=lambda *a: None),
                  target=SimpleNamespace(device='test', check_active=lambda: None, tap=lambda *a: None), identity='account', threshold=0.8)
        exec(self.module, ns)
        self.assertFalse(ns['run_one_cycle'](reconciliation_only=True))
        return calls

    def test_no_record_still_cannot_enter_input_path(self):
        self.assertEqual(self.run_case(None), [])

    def test_ordinary_unknown_is_only_checked_once(self):
        self.assertEqual(self.run_case({'id': 'x', 'count': 1}), [])

    def test_partial_batch_requires_anchored_clean_frames(self):
        self.assertEqual(self.run_case({'id': 'x', 'count': 3}), [])
        self.assertEqual(self.run_case({'id': 'x', 'count': 3}, network=True), [])
        self.assertEqual(self.run_case({'id': 'x', 'count': 3}, confirmed=True), [])

    def test_fast_batch_is_never_replayed_or_numerically_reconciled(self):
        self.assertEqual(self.run_case({'id': 'x', 'count': 3, 'mode': 'fast'}), [])

    def test_reconciliation_entry_initializes_cycle_state_before_callback(self):
        source = Path(__file__).resolve().parents[1] / 'wjdr_mumu_assistant_qt.py'
        tree = ast.parse(source.read_text(encoding='utf8'))
        job = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)
                   and n.name == 'job' and any(
                       isinstance(child, ast.FunctionDef) and child.name == 'run_one_cycle'
                       for child in n.body))
        selected = []
        for node in job.body:
            if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'completed_cycles' for t in node.targets):
                selected.append(node)
            elif isinstance(node, ast.If) and ast.unparse(node.test) == 'reconciliation_only and (not pending_submission_token)':
                selected.append(node)
        self.assertEqual(len(selected), 2)
        probe = ast.parse('def probe():\n def run_one_cycle(*, reconciliation_only):\n  seen.append(completed_cycles)\n  return True\n').body[0]
        probe.body.extend(selected)
        probe.body.append(ast.parse('seen.append("continued")').body[0])
        ns = dict(seen=[], reconciliation_only=True, pending_submission_token=None,
                  initial_test_cycles=0,
                  self=SimpleNamespace(stop_event=SimpleNamespace(is_set=lambda: False, wait=lambda _: False)),
                  target=SimpleNamespace(foreground_is_game=lambda: True))
        exec(compile(ast.fix_missing_locations(ast.Module(body=[probe], type_ignores=[])), str(source), 'exec'), ns)
        ns['probe']()
        self.assertEqual(ns['seen'], [0, 'continued'])


class RestartIdleRecoveryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        StartupReconciliationTests.setUpClass()

    def run_case(self, *, idle=True, network=False, conflict=False, reservation=25,
                 reconcile=True, marker=True, stop=False, lost_lease=False):
        calls = []
        cap = SimpleNamespace(used=0, total=0, evidence='hidden_idle') if idle else None
        def check_active():
            calls.append('lease')
            if lost_lease:
                raise InterruptedError()
        env = dict(capture=lambda: object(), match_wilderness_context=lambda _: (None, None),
            old_reservation=0,
            load_beast_stamina_item_pending=lambda _: None,
            read_beast_rally_collapsed_march_capacity=lambda *_: cap,
            match_world=lambda _: ((10, 10), 1), stable=lambda a, b: bool(a and b and a == b),
            daily_network_dialog_is_visible=lambda *_: network,
            match_same_target_conflict=lambda _: conflict,
            load_beast_rally_stamina_reserved_any_day=lambda _: reservation,
            reconcile_unconfirmed_hidden_idle=lambda *_: calls.append('uncertain') or reconcile,
            beast_shield_plus_pending=lambda _: marker,
            beast_shield_plus_receipt=lambda *_: False,
            beast_mixed_single_shield=lambda _: None,
            match_beast_rally_formation_controls=lambda *_: SimpleNamespace(point=None),
            beast_shield_plus_confirm=lambda _: calls.append('marker'),
            self=SimpleNamespace(stop_event=SimpleNamespace(is_set=lambda: stop), _log_for_device=lambda *a: None),
            target=SimpleNamespace(device='test', check_active=check_active), identity='account', threshold=.8)
        exec(StartupReconciliationTests.module, env)
        if lost_lease and idle and not network and not conflict and not stop:
            with self.assertRaises(InterruptedError):
                env['run_one_cycle'](reconciliation_only=True)
        else:
            self.assertFalse(env['run_one_cycle'](reconciliation_only=True))
        return calls

    def test_accounts_before_marker_and_never_sends_input(self):
        self.assertEqual(self.run_case(), ['lease', 'uncertain', 'lease', 'marker'])
        self.assertEqual(self.run_case(reservation=0), ['lease', 'lease', 'marker'])
        self.assertEqual(self.run_case(marker=False), ['lease', 'uncertain'])

    def test_unknown_or_interrupted_states_preserve_records(self):
        for opts in ({'idle': False}, {'network': True}, {'conflict': True}, {'stop': True}):
            self.assertEqual(self.run_case(**opts), [])
        self.assertEqual(self.run_case(reconcile=False), ['lease', 'uncertain'])
        self.assertEqual(self.run_case(lost_lease=True), ['lease'])


if __name__ == '__main__':
    unittest.main()
