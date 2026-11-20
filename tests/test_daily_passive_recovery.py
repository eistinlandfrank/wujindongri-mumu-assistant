"""A late page transition never replays the Daily navigation or claim."""
import importlib
import unittest
from unittest.mock import Mock, patch

from wjdr_mumu_assistant_qt import MainWindow


class DailyPassiveRecoveryTest(unittest.TestCase):
    def test_unknown_frames_and_delayed_receipt_resume_without_duplicate_inputs(self):
        start = MainWindow._start_daily_task_flow
        module = importlib.import_module(start.__module__)
        state = module.DailyTaskState
        city, claim = (100, 200), (300, 400)
        frames = [
            state.UNKNOWN, state.CITY_ENTRY, state.CITY_ENTRY, state.CITY_ENTRY,
            state.UNKNOWN, state.CLAIM_READY, state.CLAIM_READY, state.CLAIM_READY,
            state.UNKNOWN, state.DAILY_PAGE, state.DAILY_PAGE,
        ]
        target = Mock(device="test-device")
        target.screenshot.side_effect = frames
        window = Mock()
        window.adb.clone_for_device.return_value = target
        window.daily_interval_spin.value.return_value = 0.1
        window.daily_duration_spin.value.return_value = 0
        window.daily_guard_check.isChecked.return_value = False
        window.stop_event.is_set.return_value = False
        window.stop_event.wait.return_value = False
        window._start_worker.side_effect = lambda device, run: run()

        def classify(frame, _threshold):
            return Mock(state=frame, point=claim if frame is state.CLAIM_READY else None, score=0.99)

        with (
            patch.object(module, "DAILY_BUILTIN_TEMPLATES", ()),
            patch.object(module, "detect_daily_task_state", side_effect=classify),
            patch.object(module, "daily_network_dialog_is_visible", return_value=False),
            patch.object(module, "match_daily_city_entry", return_value=(city, 0.99)),
        ):
            start(window)
        self.assertEqual([call.args for call in target.tap.call_args_list], [city, claim])
        window.signals.clicks.emit.assert_called_once_with(1)
        self.assertEqual(target.screenshot.call_count, len(frames))


if __name__ == "__main__":
    unittest.main()
