"""The selector must prove the selected account's level on both fresh frames."""
import unittest
from types import SimpleNamespace
from unittest.mock import Mock

from PIL import Image

from tests.test_beast_safe_recovery import nested


class BeastLevelConfigurationTests(unittest.TestCase):
    def run_configuration(self, confirmation_levels):
        target = SimpleNamespace(device="test-adb", tap=Mock(), shell=Mock())
        selected_frame = SimpleNamespace(level=9)
        calls = []

        def wait_for_double(label, matcher):
            calls.append(label)
            if len(calls) <= 2:
                return selected_frame, (1, 2), None
            frames = [SimpleNamespace(level=level) for level in confirmation_levels]
            results = [matcher(frame) for frame in frames]
            if len(results) == 2 and all(point for point, _ in results):
                return frames[-1], results[-1][0], results[-1][1]
            return None

        env = dict(Image=Image, profile=SimpleNamespace(beast_level=9),
                   wait_for_double=wait_for_double, selector_match=Mock(),
                   beast_rally_beast_target_point=lambda _: (3, 4), target=target,
                   cycle_position=lambda _name, _image, point: point,
                   self=SimpleNamespace(_log_for_device=Mock()),
                   read_beast_rally_selector_level=lambda image: image.level,
                   beast_rally_selector_search_point=lambda _: (1, 2))
        return nested("configure_level", env)(), target, calls

    def test_unchanged_level_requires_two_matching_frames(self):
        result, target, calls = self.run_configuration([9, 9])
        self.assertIsNotNone(result)
        self.assertEqual(len(calls), 3)
        target.shell.assert_not_called()

    def test_disagreeing_or_unreadable_frame_blocks_search(self):
        for levels in ([9, 8], [None, 9]):
            with self.subTest(levels=levels):
                result, target, _ = self.run_configuration(levels)
                self.assertIsNone(result)
                target.shell.assert_not_called()


if __name__ == "__main__":
    unittest.main()
