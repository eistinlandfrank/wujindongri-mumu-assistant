import unittest
import tempfile
from pathlib import Path

from wjdr_mumu_assistant_qt import beast_recover_receipt_stamina, beast_tap_stamina_four
from wjdr_backend import (begin_beast_stamina_fast_batch, load_beast_stamina_item_pending,
                          update_beast_stamina_fast_batch)


class ReceiptStaminaRecoveryTests(unittest.TestCase):
    def test_four_fast_taps_are_sent_in_one_shell_call(self):
        calls = []
        class Target:
            def shell(self, args, timeout):
                calls.append((args, timeout))
        beast_tap_stamina_four(Target(), (12, 34))
        self.assertEqual(calls, [(['input tap 12 34; sleep 0.1; input tap 12 34; sleep 0.1; input tap 12 34; sleep 0.1; input tap 12 34'], 10)])

    def run_case(self, *, first=None, second=None, frames=None, reserved=True,
                 pending=False, stop_after=None, diagnostics=None, use_frames=None,
                 fast_batch=False):
        item = {'item': (12, 34), 'obs': (1346, 22)}
        first = item if first is None else first
        second = item if second is None else second
        frames = iter(frames if frames is not None else [
            {'close': (50, 60), 'obs': (1343, 52)}, {'close': (50, 60), 'obs': (1343, 52)},
            {'world': (70, 80)}, {'world': (70, 80)}])
        events = []
        ledger = {'reservation': 25 if reserved else 0, 'pending': pending}
        use_frames = iter(use_frames if use_frames is not None else [item] * 4)

        def capture():
            if ledger['pending'] == 'prepared':
                return next(use_frames, {})
            return next(frames, {})

        def begin():
            events.append('begin')
            ledger['pending'] = 'prepared'
            return 'account-token'

        def mark(token):
            self.assertEqual(token, 'account-token')
            events.append('sent')
            ledger['pending'] = 'sent'

        def complete(token):
            self.assertEqual(token, 'account-token')
            events.append('complete')
            ledger['pending'] = False

        def tap(point):
            events.append(point)

        result = beast_recover_receipt_stamina(
            first, second, match_item=lambda f: f.get('item'),
            observation=lambda f: self.fail('stamina numbers must not be read'), network=lambda f: f.get('network', False),
            stable=lambda a, b: bool(a and a == b),
            reserved=lambda: ledger['reservation'], pending=lambda: ledger['pending'],
            check_active=lambda: events.append('lease'), begin=begin, mark_sent=mark,
            complete=complete, tap=tap, capture=capture,
            close_point=lambda f: f.get('close'), match_world=lambda f: f.get('world'),
            match_formation=lambda f: f.get('formation'),
            stopped=lambda: stop_after is not None and events.count((12, 34)) >= stop_after,
            diagnose=(diagnostics.append if diagnostics is not None else lambda reason: None),
            fast_batch_tap=(lambda point: events.append(('batch', point))) if fast_batch else None)
        return result, events, ledger

    def test_fast_batch_sends_once_without_item_recognition_between_taps(self):
        result, events, ledger = self.run_case(fast_batch=True, use_frames=[])
        self.assertTrue(result)
        self.assertEqual(events.count(('batch', (12, 34))), 1)
        self.assertLess(events.index('sent'), events.index(('batch', (12, 34))))
        self.assertEqual(events.count((50, 60)), 1)
        self.assertFalse(ledger['pending'])

    def test_paid_or_unknown_button_is_not_tapped_and_guard_is_preserved(self):
        for frame in ({'paid': (12, 34)}, {}, {'item': (99, 99)},
                      {'item': (12, 34), 'network': True}):
            with self.subTest(frame=frame):
                result, events, ledger = self.run_case(use_frames=[frame])
                self.assertFalse(result)
                self.assertNotIn((12, 34), events)
                self.assertEqual(ledger['pending'], 'prepared')
                self.assertNotIn('sent', events)
                self.assertNotIn('complete', events)

    def test_one_dialog_never_sends_a_second_use(self):
        result, events, ledger = self.run_case(use_frames=[{'item': (12, 34)}, {'paid': (12, 34)}])
        self.assertTrue(result)
        self.assertEqual(events.count((12, 34)), 1)
        self.assertEqual(events.count('sent'), 1)

    def test_last_free_use_then_paid_page_closes_without_purchase(self):
        paid_close = {'paid': (12, 34), 'close': (50, 60)}
        frames = [paid_close] * 2 + [{'formation': (1, 2)}] * 2
        result, events, ledger = self.run_case(use_frames=[{'item': (12, 34)}], frames=frames)
        self.assertEqual(result, 'formation_after_stamina')
        self.assertEqual(events.count((12, 34)), 1)
        self.assertEqual(events.count((50, 60)), 1)
        self.assertEqual(events.count('complete'), 1)
        self.assertFalse(ledger['pending'])

    def test_four_taps_with_three_confirmed_uses_preserve_dispatch_reservation(self):
        result, events, ledger = self.run_case()
        self.assertTrue(result)
        self.assertEqual(events.count((12, 34)), 1)
        self.assertEqual(events.count((50, 60)), 1)
        self.assertLess(events.index('begin'), events.index((12, 34)))
        self.assertLess(events.index('sent'), events.index((50, 60)))
        self.assertEqual(ledger, {'reservation': 25, 'pending': False})

    def test_unsafe_initial_evidence_has_no_input(self):
        variants = [
            {'first': {'item': (12, 34), 'obs': (1346, 22), 'network': True}},
            {'reserved': False}, {'pending': 'unknown'},
            {'second': {}, 'frames': [{}] * 6},
        ]
        for kwargs in variants:
            with self.subTest(kwargs=kwargs):
                result, events, ledger = self.run_case(**kwargs)
                self.assertFalse(result)
                self.assertNotIn('begin', events)
                self.assertNotIn((12, 34), events)

    def test_transition_frames_are_rechecked_before_one_batch(self):
        item = {'item': (12, 34), 'obs': (1346, 22)}
        frames = [item, item,
                  {'close': (50, 60), 'obs': (1343, 52)},
                  {'close': (50, 60), 'obs': (1343, 52)},
                  {'world': (70, 80)}, {'world': (70, 80)}]
        result, events, ledger = self.run_case(first={}, second=item, frames=frames)
        self.assertTrue(result)
        self.assertEqual(events.count('begin'), 1)
        self.assertEqual(events.count((12, 34)), 1)
        self.assertEqual(ledger, {'reservation': 25, 'pending': False})

    def test_inconsistent_page_never_starts_batch(self):
        item = {'item': (12, 34), 'obs': (1346, 22)}
        changed = {'item': (99, 99), 'obs': (1345, 22)}
        result, events, ledger = self.run_case(first=item, second=changed,
                                               frames=[item, changed] * 3)
        self.assertFalse(result)
        self.assertNotIn('begin', events)
        self.assertNotIn((12, 34), events)
        self.assertEqual(ledger, {'reservation': 25, 'pending': False})

    def test_interrupted_batch_stays_pending(self):
        result, events, ledger = self.run_case(stop_after=1)
        self.assertFalse(result)
        self.assertEqual(ledger['pending'], 'sent')
        self.assertEqual(ledger['reservation'], 25)
        self.assertIn('sent', events)

    def test_unknown_close_or_post_close_keeps_sent_guard(self):
        for frames in ([{}, {}], [{'close': (50, 60), 'obs': (1343, 52)},
                                    {'close': (50, 60), 'obs': (1343, 52)}, {}, {}]):
            result, events, ledger = self.run_case(frames=frames)
            self.assertFalse(result)
            self.assertEqual(ledger, {'reservation': 25, 'pending': 'sent'})
            self.assertNotIn('complete', events)

    def test_transient_close_animation_recovers_without_repeating_items(self):
        frames = [{}, {}] + [{'close': (50, 60)}] * 2 + [{'world': (70, 80)}] * 2
        result, events, ledger = self.run_case(frames=frames)
        self.assertTrue(result)
        self.assertEqual(events.count((12, 34)), 1)
        self.assertEqual(events.count((50, 60)), 1)
        self.assertEqual(events.count('complete'), 1)
        self.assertFalse(ledger['pending'])

    def test_transient_post_close_page_is_reread_without_repeating_close(self):
        frames = [{'close': (50, 60)}] * 2 + [{}, {}] + [{'formation': (1, 2)}] * 2
        result, events, ledger = self.run_case(frames=frames)
        self.assertEqual(result, 'formation_after_stamina')
        self.assertEqual(events.count((12, 34)), 1)
        self.assertEqual(events.count((50, 60)), 1)
        self.assertEqual(events.count('complete'), 1)
        self.assertFalse(ledger['pending'])

    def test_unrecognized_post_close_keeps_guard_and_never_repeats_close(self):
        diagnostics = []
        frames = [{'close': (50, 60)}] * 2 + [{}] * 8
        result, events, ledger = self.run_case(frames=frames, diagnostics=diagnostics)
        self.assertFalse(result)
        self.assertEqual(events.count((12, 34)), 1)
        self.assertEqual(events.count((50, 60)), 1)
        self.assertEqual(ledger['pending'], 'sent')
        self.assertEqual(diagnostics, ['关闭后页面未就绪，保留道具未决'])

    def test_formation_page_requests_live_episode_continuation_without_confirming_dispatch(self):
        diagnostics = []
        result, events, ledger = self.run_case(frames=[
            {'close': (50, 60), 'obs': (1343, 52)}, {'close': (50, 60), 'obs': (1343, 52)},
            {'formation': (1, 2)}, {'formation': (1, 2)}], diagnostics=diagnostics)
        self.assertEqual(result, 'formation_after_stamina')
        self.assertEqual(ledger['reservation'], 25)
        self.assertFalse(ledger['pending'])
        self.assertEqual(events.count((12, 34)), 1)
        self.assertNotIn('complete_dispatch', events)

    def test_no_overlay_is_read_only(self):
        result, events, ledger = self.run_case(first={}, second={})
        self.assertIsNone(result)
        self.assertEqual(events, [])
        self.assertEqual(ledger['reservation'], 25)

    def test_four_confirmed_uses_complete_once(self):
        frames = [{'close': (50, 60), 'obs': (1342, 62)}] * 2 + [{'world': (70, 80)}] * 2
        result, events, ledger = self.run_case(frames=frames)
        self.assertTrue(result)
        self.assertEqual(events.count((12, 34)), 1)
        self.assertEqual(ledger, {'reservation': 25, 'pending': False})

    def test_numeric_readings_are_never_used_for_batch(self):
        for after in [[(1344, 42), (1344, 42)], [(1343, 52), (1342, 62)]]:
            frames = [{'close': (50, 60), 'obs': value} for value in after] + [{'world': (70, 80)}] * 2
            result, events, ledger = self.run_case(frames=frames)
            self.assertTrue(result)
            self.assertEqual(events.count((12, 34)), 1)
            self.assertEqual(events.count((50, 60)), 1)
            self.assertEqual(ledger, {'reservation': 25, 'pending': False})

    def test_fast_item_guards_are_account_isolated(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'isolated-test-items.json'
            a, b = 'mumu:5:android-a', 'mumu:6:android-b'
            token_a = begin_beast_stamina_fast_batch(a, path=path)
            token_b = begin_beast_stamina_fast_batch(b, path=path)
            update_beast_stamina_fast_batch(a, token_a, path=path)
            update_beast_stamina_fast_batch(a, token_a, complete=True, path=path)
            self.assertIsNone(load_beast_stamina_item_pending(a, path=path))
            self.assertEqual(load_beast_stamina_item_pending(b, path=path)['id'], token_b)


if __name__ == '__main__':
    unittest.main()
