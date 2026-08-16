from __future__ import annotations

import os
import unittest
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QMainWindow, QPushButton

from wjdr_backend import MiningLevelProfile
from wjdr_mumu_assistant_qt import MainWindow, MiningLevelSettingsDialog


class MiningLevelSettingsDialogTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_manual_mode_is_exclusive_and_is_limited_to_one_through_nine(self):
        dialog = MiningLevelSettingsDialog(
            "账号 …50ce",
            "127.0.0.1:25632",
            MiningLevelProfile("manual", 7),
        )
        self.assertTrue(dialog.mode_group.exclusive())
        self.assertTrue(dialog.manual_radio.isChecked())
        self.assertFalse(dialog.auto_radio.isChecked())
        self.assertEqual(dialog.manual_level_spin.minimum(), 1)
        self.assertEqual(dialog.manual_level_spin.maximum(), 9)
        self.assertTrue(dialog.manual_level_spin.isEnabled())
        self.assertEqual(dialog.profile(), MiningLevelProfile("manual", 7))

    def test_auto_mode_disables_manual_input_and_returns_only_auto(self):
        dialog = MiningLevelSettingsDialog(
            "账号 …d5ab",
            "127.0.0.1:25600",
            MiningLevelProfile("auto", 9),
        )
        self.assertTrue(dialog.auto_radio.isChecked())
        self.assertFalse(dialog.manual_radio.isChecked())
        self.assertFalse(dialog.manual_level_spin.isEnabled())
        self.assertEqual(dialog.profile(), MiningLevelProfile("auto", 9))

    def test_switching_android_identity_refreshes_the_visible_account_mode(self):
        window = MainWindow.__new__(MainWindow)
        QMainWindow.__init__(window)
        window.adb = None
        window.mining_level_button = QPushButton()
        profiles = {
            "android:low": MiningLevelProfile("manual", 6),
            "android:high": MiningLevelProfile("auto", 9),
        }
        with patch(
            "wjdr_mumu_assistant_qt.load_mining_level_profile",
            side_effect=lambda identity: profiles[identity],
        ):
            window._update_mining_level_button({"identity": "android:low"})
            self.assertEqual(window.mining_level_button.text(), "采矿：手动 Lv.6")
            window._update_mining_level_button({"identity": "android:high"})
            self.assertEqual(window.mining_level_button.text(), "采矿：自动识别")


if __name__ == "__main__":
    unittest.main()
