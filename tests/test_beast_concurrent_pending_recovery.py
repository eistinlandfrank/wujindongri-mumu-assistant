"""Exercise the actual dispatch monitor without any game input."""
import ast
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock


class ConcurrentPendingRecoveryTest(unittest.TestCase):
    def run_monitor(self, frames, pauses, conflict=lambda _: False, network=lambda _: False,
                    recover=lambda *_: False):
        tree = ast.parse(Path('wjdr_mumu_assistant_qt.py').read_text(encoding='utf-8'))
        function = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)
                        and n.name == 'monitor_new_concurrent_rally')
        class Globals(ast.NodeTransformer):
            def visit_Nonlocal(self, node):
                return ast.copy_location(ast.Global(names=node.names), node)
        function = Globals().visit(function)
        before = SimpleNamespace(rallies=1)
        confirmed = SimpleNamespace(rallies=2, green=2, used=2, total=6)
        frame_iter = iter(frames(confirmed))
        env = dict(baseline_concurrent=before, confirmed_dispatches=0,
            tracked_green=1, tracked_rallies=1, identity='test-account',
            profile=SimpleNamespace(max_concurrent_rallies=6), line_tracker=Mock(),
            self=SimpleNamespace(stop_event=SimpleNamespace(is_set=lambda: False), _log_for_device=Mock()),
            target=SimpleNamespace(device='test'), time=SimpleNamespace(monotonic=Mock(side_effect=range(0, 400, 5))),
            capture=lambda: next(frame_iter), match_same_target_conflict=conflict,
            daily_network_dialog_is_visible=lambda frame, threshold: network(frame), threshold=0.9,
            read_concurrent_snapshot=lambda frame: frame,
            confirms_new_concurrent_rally=lambda old, new: new is confirmed,
            confirm_beast_rally_stamina_reservation=Mock(return_value=20),
            reconcile_unconfirmed_hidden_idle=Mock(side_effect=recover),
            resolve_target_conflict=Mock(), save_evidence=Mock(), set_state=Mock(),
            pause=Mock(side_effect=pauses))
        exec(compile(ast.fix_missing_locations(ast.Module(body=[function], type_ignores=[])),
                     'concurrent_monitor', 'exec'), env)
        return env['monitor_new_concurrent_rally'](), env

    def test_unknown_waits_past_timeout_without_confirming_or_retrying(self):
        result, env = self.run_monitor(lambda _: [None] * 16, [False] * 7 + [True])
        self.assertFalse(result)
        env['confirm_beast_rally_stamina_reservation'].assert_not_called()
        self.assertGreater(env['set_state'].call_count, 0)
        self.assertEqual(env['confirmed_dispatches'], 0)

    def test_late_dual_frame_confirmation_resolves_original_attempt(self):
        result, env = self.run_monitor(lambda marker: [None] * 12 + [marker, marker], [False] * 6)
        self.assertTrue(result)
        env['confirm_beast_rally_stamina_reservation'].assert_called_once_with('test-account')
        self.assertEqual(env['confirmed_dispatches'], 1)

    def test_hidden_idle_after_timeout_returns_uncertain_not_confirmation(self):
        idle = object()
        result, env = self.run_monitor(lambda _: [idle] * 20, [False] * 9,
                                       recover=lambda a, b: a is idle and b is idle)
        self.assertEqual(result, 'idle_reconciled')
        env['reconcile_unconfirmed_hidden_idle'].assert_called_once_with(idle, idle)
        env['confirm_beast_rally_stamina_reservation'].assert_not_called()
        self.assertEqual(env['confirmed_dispatches'], 0)

    def test_conflict_stops_and_calls_conflict_handler(self):
        result, env = self.run_monitor(lambda _: [object(), object()], [], lambda _: True)
        self.assertFalse(result)
        env['resolve_target_conflict'].assert_called_once()
        env['confirm_beast_rally_stamina_reservation'].assert_not_called()

    def test_network_failure_stops_without_clearing_reservation(self):
        result, env = self.run_monitor(lambda _: [object(), object()], [], network=lambda _: True)
        self.assertFalse(result)
        env['confirm_beast_rally_stamina_reservation'].assert_not_called()
        env['pause'].assert_not_called()


if __name__ == '__main__':
    unittest.main()
