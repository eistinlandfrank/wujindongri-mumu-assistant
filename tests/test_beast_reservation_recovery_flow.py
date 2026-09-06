"""Execute the real nested recovery controller with deterministic fresh frames."""
import ast
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock
from wjdr_backend import DailyMarchCapacity


class RecoveryControllerTest(unittest.TestCase):
    def run_controller(self, frame_states):
        tree = ast.parse(Path("wjdr_mumu_assistant_qt.py").read_text(encoding="utf-8"))
        function = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)
                        and n.name == "recover_pending_reservation")
        log, reconcile, collapse = Mock(), Mock(return_value=20), Mock(return_value=True)
        frames = iter(frame_states)
        env = dict(
            load_beast_rally_stamina_reserved=lambda _: 20, identity="test-account",
            set_state=Mock(), open_wilderness_queue_panel=Mock(return_value=(True,) * 6),
            ensure_compact_march_panel=Mock(return_value=True),
            read_compact_rally_rows=lambda _: (),
            read_beast_rally_collapsed_march_capacity=lambda image, _: image,
            time=SimpleNamespace(monotonic=Mock(side_effect=range(0, 400, 5))),
            self=SimpleNamespace(stop_event=SimpleNamespace(is_set=lambda: False), _log_for_device=log),
            target=SimpleNamespace(device="test"), capture=lambda: next(frames), threshold=0.9,
            read_beast_rally_wilderness_queue_states=lambda image, _: image,
            read_beast_rally_expanded_march_capacity=lambda image, _: None,
            reconcile_beast_rally_idle_reservation=reconcile,
            collapse_wilderness_queue_panel=collapse, save_evidence=Mock(), pause=lambda: False,
        )
        exec(compile(ast.fix_missing_locations(ast.Module(body=[function], type_ignores=[])), "recovery", "exec"), env)
        return env["recover_pending_reservation"](), reconcile, collapse, env

    def test_existing_busy_team_waits_then_idle_recovers_without_dispatch(self):
        idle = DailyMarchCapacity(0, 6, 1.0)
        busy = DailyMarchCapacity(1, 6, 1.0)
        result, reconcile, collapse, env = self.run_controller([busy, busy, idle, idle])
        self.assertTrue(result)
        reconcile.assert_called_once_with("test-account", None, None, first_capacity=idle, second_capacity=idle)
        collapse.assert_not_called()
        env["open_wilderness_queue_panel"].assert_not_called()
        # No tap or Expedition interface is provided: recovery must not dispatch.
        self.assertGreaterEqual(env["set_state"].call_count, 2)

    def test_unknown_frames_never_clear_old_record(self):
        result, reconcile, collapse, _ = self.run_controller([None] * 16)
        self.assertFalse(result)
        reconcile.assert_not_called()
        collapse.assert_not_called()


if __name__ == "__main__":
    unittest.main()
