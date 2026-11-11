"""An old unknown dispatch must never be cleared from empty frames alone."""
import ast
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock


class RecoveryControllerTest(unittest.TestCase):
    def run_controller(self, reserved=20, conflict=lambda _: False):
        tree = ast.parse(Path('wjdr_mumu_assistant_qt.py').read_text(encoding='utf-8'))
        function = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)
                        and n.name == 'recover_pending_reservation')
        env = dict(load_beast_rally_stamina_reserved=lambda _: reserved, identity='test-account',
            set_state=Mock(), ensure_compact_march_panel=Mock(return_value=True),
            time=SimpleNamespace(monotonic=Mock(side_effect=range(0, 400, 5))),
            self=SimpleNamespace(stop_event=SimpleNamespace(is_set=lambda: False), _log_for_device=Mock()),
            target=SimpleNamespace(device='test'), capture=Mock(return_value=None),
            match_same_target_conflict=conflict, stable=lambda a, b: bool(a and b),
            daily_network_dialog_is_visible=lambda frame, threshold: False, threshold=0.9,
            pause=Mock(side_effect=[False] * 7 + [True]),
            reconcile_beast_rally_idle_reservation=Mock(), reconcile_beast_rally_gathering_reservation=Mock())
        exec(compile(ast.fix_missing_locations(ast.Module(body=[function], type_ignores=[])), 'recovery', 'exec'), env)
        return env['recover_pending_reservation'](), env

    def test_unknown_or_empty_frames_never_clear_reservation(self):
        result, env = self.run_controller()
        self.assertFalse(result)
        self.assertEqual(env['capture'].call_count, 16)
        env['reconcile_beast_rally_idle_reservation'].assert_not_called()
        env['reconcile_beast_rally_gathering_reservation'].assert_not_called()

    def test_no_reservation_needs_no_capture(self):
        result, env = self.run_controller(reserved=0)
        self.assertTrue(result)
        env['capture'].assert_not_called()

    def test_conflict_stops_without_clearing(self):
        result, env = self.run_controller(conflict=lambda _: True)
        self.assertFalse(result)
        env['reconcile_beast_rally_idle_reservation'].assert_not_called()


if __name__ == '__main__':
    unittest.main()
