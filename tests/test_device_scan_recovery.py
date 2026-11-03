"""Discovery must survive a missing bound device without changing accounts."""
import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
import unittest
from unittest.mock import Mock, patch

from PySide6.QtWidgets import QApplication
from wjdr_backend import AdbError, MuMuADB
from wjdr_mumu_assistant_qt import MainWindow
from tests.test_multi_device_ui import make_window


class DeviceScanRecoveryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def fake_backend(self):
        adb = MuMuADB.__new__(MuMuADB)
        adb.device = ""
        adb.players = [{"is_process_started": True, "adb_port": 16448}]
        adb._candidate_ports = lambda: []
        adb._run = lambda args, **kw: "List of devices attached\n127.0.0.1:16448\tdevice\n" if args == ["devices"] else ""
        adb.device_identity = lambda serial: "index:2:android-id"
        return adb

    def test_strict_and_discovery_modes(self):
        adb = self.fake_backend()
        with self.assertRaises(AdbError):
            adb.connect("127.0.0.1:16544")
        devices = adb.connect("127.0.0.1:16544", allow_unavailable=True)
        self.assertEqual(devices, ["127.0.0.1:16448"])
        self.assertEqual(adb.device, "")

    def test_missing_binding_displays_online_device_without_auto_switch(self):
        window = make_window()
        window.preferred_device = "127.0.0.1:16544"
        window.adb = Mock(device=window.preferred_device)
        discovered = self.fake_backend()
        summary = {"device": "127.0.0.1:16448", "index": "2", "name": "2号", "resolution": "1440x2560", "state": "在线", "identity": "index:2:android-id"}
        discovered.device_summary = lambda device: summary
        emitted = []
        window.signals.devices.connect(lambda summaries, selected: emitted.append((summaries, selected)))
        with patch("wjdr_mumu_assistant_qt.MuMuADB", return_value=discovered), patch.object(window, "log"), patch.object(window, "_capture_job") as capture:
            window._connect_job()
        self.assertIsNone(window.adb)
        capture.assert_not_called()
        with patch.object(window, "_load_log_tail"), patch.object(window, "_update_mining_level_button"), patch.object(window, "_update_beast_rally_settings"):
            window._apply_devices(*emitted[0])
            self.assertIsNone(window.device_combo.currentData())
            self.assertEqual(window.devices, ["127.0.0.1:16448"])
            self.assertEqual(window.device_combo.itemData(1), summary)
            with patch.object(window, "_run_async"), patch.object(window, "log"):
                window.device_combo.setCurrentIndex(1)
                window._device_changed(1)
            self.assertEqual(window.adb.device, "127.0.0.1:16448")
            self.assertEqual(window.preferred_device, "127.0.0.1:16448")
        window.deleteLater()


if __name__ == "__main__":
    unittest.main()
