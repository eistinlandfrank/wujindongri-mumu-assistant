"""Regression checks for the one live capture path and its device binding."""
from pathlib import Path
import unittest
from unittest.mock import Mock, patch

from PIL import Image

from wjdr_backend import AdbError, MuMuADB


ROOT = Path(__file__).resolve().parents[1]
BOOT = "8e5a12ad-9365-4809-8baf-f031fc00a381"
OTHER_BOOT = "7a3032ce-45bc-400e-8a11-77123df0d94f"


def transport():
    adb = MuMuADB("test-adb")
    adb.set_device("127.0.0.1:16480")
    adb.players = [
        {"index": "2", "adb_port": 16448},
        {"index": "3", "adb_port": 16480},
    ]
    adb.device_identities = {adb.device: "mumu:3:android:abcdef"}
    adb._run = Mock(return_value=f"abcdef\n{BOOT}\nPhysical size: 1440x2560")
    return adb


class IpcCaptureContract(unittest.TestCase):
    def test_uses_verified_index_and_reuses_session_for_new_frames(self):
        adb = transport()
        session = Mock()
        session.screenshot.side_effect = [Image.new("RGB", (2, 4), color) for color in ("red", "blue")]
        with patch("wjdr_mumu_ipc._IpcCapture", return_value=session) as open_session:
            self.assertEqual(adb.screenshot().getpixel((0, 0)), (255, 0, 0))
            self.assertEqual(adb.screenshot().getpixel((0, 0)), (0, 0, 255))
        self.assertEqual(open_session.call_args.args, (adb, 3, (1440, 2560)))
        self.assertFalse(open_session.call_args.kwargs["game_display"])
        adb._run.assert_called_once()
        self.assertEqual(adb._run.call_args.args[0][:3], ["-s", adb.device, "shell"])

    def test_timeout_closes_renderer_and_reopen_rejects_different_boot(self):
        adb = transport()
        session = Mock()
        session.screenshot.side_effect = TimeoutError("renderer timeout")
        with patch("wjdr_mumu_ipc._IpcCapture", return_value=session) as open_session:
            with self.assertRaisesRegex(AdbError, "renderer timeout"):
                adb.screenshot()
            adb._run.return_value = f"abcdef\n{OTHER_BOOT}\nPhysical size: 1440x2560"
            with self.assertRaisesRegex(AdbError, "已重启或改变"):
                adb.screenshot()
        open_session.assert_called_once()
        session.close.assert_called_once()

    def test_cloned_android_id_is_not_enough_to_accept_wrong_adb_alias(self):
        adb = transport()
        adb.set_device("emulator-5558")
        adb.device_identities[adb.device] = "mumu:3:android:abcdef"
        adb._run.side_effect = [f"abcdef\n{BOOT}\nPhysical size: 1440x2560", OTHER_BOOT]
        with patch("wjdr_mumu_ipc._IpcCapture") as open_session:
            with self.assertRaisesRegex(AdbError, "管理器实例不一致"):
                adb.screenshot()
        open_session.assert_not_called()
        self.assertEqual(adb._run.call_args.args[0][:2], ["-s", "127.0.0.1:16480"])

    def test_selected_serial_does_not_use_other_account_session(self):
        adb = transport()
        first, second = Mock(), Mock()
        first.screenshot.return_value = Image.new("RGB", (2, 4), "red")
        second.screenshot.return_value = Image.new("RGB", (2, 4), "green")
        with patch("wjdr_mumu_ipc._IpcCapture", side_effect=[first, second]) as open_session:
            self.assertIs(adb.screenshot(), first.screenshot.return_value)
            self.assertIs(adb.screenshot(device="127.0.0.1:16448"), second.screenshot.return_value)
            self.assertIs(adb.screenshot(), first.screenshot.return_value)
        self.assertEqual([call.args[1] for call in open_session.call_args_list], [3, 2])

    def test_transient_mining_control_uses_fresh_bounded_capture(self):
        source = (ROOT / "wjdr_daily_controller.py").read_text(encoding="utf-8")
        section = source.split("fast_home_deadline", 1)[1].split(
            "deadline = time.monotonic() + AUTOMATION_STEP_TIMEOUT_SECONDS", 1
        )[0]
        self.assertIn("target.screenshot(timeout=fast_home_deadline - time.monotonic())", section)
        self.assertIn("临时小房子未确认，本轮停止搜索和派遣", section)
        self.assertNotIn("target.back()", section)


if __name__ == "__main__":
    unittest.main()
