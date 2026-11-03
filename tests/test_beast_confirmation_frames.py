"""Frame-count policy for the actual Beast workflow, without device input."""
import threading
import time
import unittest
from types import SimpleNamespace
from typing import Any, Callable
from unittest.mock import Mock

from PIL import Image
from tests.test_beast_safe_recovery import nested


class BeastConfirmationFramesTests(unittest.TestCase):
    def confirm(self, label, cycles, matches=None, network=False):
        frames = [object(), object(), object()]
        capture = Mock(side_effect=frames)
        target = SimpleNamespace(device="test-adb")
        env = dict(
            Image=Image, Any=Any, Callable=Callable, time=time,
            AUTOMATION_STEP_TIMEOUT_SECONDS=1, bounded_step_timeout=lambda n: n,
            completed_cycles=cycles, capture=capture, threshold=.9,
            daily_network_dialog_is_visible=Mock(return_value=network),
            self=SimpleNamespace(stop_event=threading.Event(), _log_for_device=Mock()),
            target=target, set_state=Mock(), pause=Mock(return_value=False),
            stable=lambda point, previous: point == previous,
        )
        matcher = Mock(side_effect=matches or [((7, 9), "ok")] * 3)
        return nested("wait_for_double", env)(label, matcher), capture, matcher

    def test_first_cycle_uses_two_frames_and_later_routine_uses_one(self):
        for label in ("确认橙色集结按钮", "确认冰原巨兽搜索页", "确认等级为 9",
                      "确认第 1 行兵力为 1", "复核出征配置与普通出征"):
            with self.subTest(label=label):
                first, captures, _ = self.confirm(label, 0)
                self.assertIsNotNone(first)
                self.assertEqual(captures.call_count, 2)
                later, captures, _ = self.confirm(label, 1)
                self.assertIsNotNone(later)
                self.assertEqual(captures.call_count, 1)

    def test_sensitive_or_unrelated_labels_keep_two_frames(self):
        for label in ("确认队列", "确认自建归属", "冲突取消后确认出征配置", "确认第 1 个其他步骤"):
            with self.subTest(label=label):
                result, captures, _ = self.confirm(label, 1)
                self.assertIsNotNone(result)
                self.assertEqual(captures.call_count, 2)

    def test_single_frame_requires_positive_match_and_rejects_network_dialog(self):
        result, captures, _ = self.confirm("确认手动兵力", 1, [(None, None), ((7, 9), "ok")])
        self.assertIsNotNone(result)
        self.assertEqual(captures.call_count, 2)
        result, captures, matcher = self.confirm("确认手动兵力", 1, network=True)
        self.assertIsNone(result)
        self.assertEqual(captures.call_count, 1)
        matcher.assert_not_called()

    def test_wilderness_search_reuses_one_frame_only_after_first_cycle(self):
        for cycles, frames, expected in (
            (0, ['world', 'world'], 2),
            (1, ['world'], 1),
            (1, ['city', 'city', 'world', 'world'], 4),
        ):
            with self.subTest(cycles=cycles, frames=frames):
                capture = Mock(side_effect=frames)
                target = SimpleNamespace(device='test-adb', tap=Mock())
                env = dict(
                    Image=Image, time=time, completed_cycles=cycles,
                    AUTOMATION_STEP_TIMEOUT_SECONDS=1, capture=capture, threshold=.9,
                    daily_network_dialog_is_visible=Mock(return_value=False),
                    match_world=lambda image: ((7, 9), 1) if image == 'world' else (None, 0),
                    match_daily_city_wilderness_entry=lambda image, threshold: ((3, 4), 1) if image == 'city' else (None, 0),
                    self=SimpleNamespace(stop_event=threading.Event(), _log_for_device=Mock()),
                    target=target, set_state=Mock(), pause=Mock(return_value=False),
                    save_evidence=Mock(), stable=lambda point, previous: point == previous,
                )
                self.assertIsNotNone(nested('ensure_wilderness', env)())
                self.assertEqual(capture.call_count, expected)
                self.assertEqual(target.tap.call_count, int(frames[0] == 'city'))


if __name__ == "__main__":
    unittest.main()
