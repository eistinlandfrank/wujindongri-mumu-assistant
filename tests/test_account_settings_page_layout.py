from __future__ import annotations

import os
import unittest
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QMainWindow, QWidget

from wjdr_backend import BeastRallyProfile, MiningLevelProfile
from wjdr_mumu_assistant_qt import MainWindow


def ancestor_names(widget: QWidget) -> list[str]:
    names: list[str] = []
    parent = widget.parentWidget()
    while parent is not None:
        if parent.objectName():
            names.append(parent.objectName())
        parent = parent.parentWidget()
    return names


class AccountSettingsPageLayoutTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def build_window(self) -> MainWindow:
        window = MainWindow.__new__(MainWindow)
        QMainWindow.__init__(window)
        window.adb = None
        window._build_ui()
        return window

    def test_account_controls_belong_to_their_business_pages(self) -> None:
        window = self.build_window()
        self.assertIn("dailyAccountSettingsCard", ancestor_names(window.mining_level_button))
        self.assertNotIn("beastAccountSettingsCard", ancestor_names(window.mining_level_button))
        self.assertIn("beastAccountSettingsCard", ancestor_names(window.beast_rally_settings_button))
        self.assertNotIn("dailyAccountSettingsCard", ancestor_names(window.beast_rally_settings_button))
        self.assertEqual(window.mining_level_button.accessibleName(), "当前账号采矿设置")
        self.assertEqual(window.beast_rally_settings_button.accessibleName(), "当前账号巨兽设置")

    def test_selected_account_refreshes_both_page_local_summaries(self) -> None:
        window = self.build_window()
        item = {"identity": "mumu:2:android:a195ab448b7cd5ab"}
        with (
            patch(
                "wjdr_mumu_assistant_qt.load_mining_level_profile",
                return_value=MiningLevelProfile("manual", 9),
            ),
            patch(
                "wjdr_mumu_assistant_qt.load_beast_rally_profile",
                return_value=BeastRallyProfile(8, 0),
            ),
            patch("wjdr_mumu_assistant_qt.load_beast_rally_stamina_spent", return_value=40),
        ):
            window._update_mining_level_button(item)
            window._update_beast_rally_settings(item)

        self.assertEqual(window.mining_level_button.text(), "手动采矿 Lv.9")
        self.assertEqual(window.beast_rally_settings_button.text(), "修改巨兽参数")
        self.assertEqual(window.beast_rally_profile_summary.text(), "8级 · 打野 · 单队 · 上限 不限 · 今日 40")
        self.assertIn("账号 …7cd5ab", window.mining_profile_context.text())
        self.assertIn("账号 …7cd5ab", window.beast_rally_profile_context.text())
        self.assertIn("仅作用于当前账号", window.mining_profile_context.text())
        self.assertIn("仅作用于当前账号", window.beast_rally_profile_context.text())

    def test_no_account_disables_only_page_local_setting_actions(self) -> None:
        window = self.build_window()
        window._update_mining_level_button(None)
        window._update_beast_rally_settings(None)
        self.assertFalse(window.mining_level_button.isEnabled())
        self.assertFalse(window.beast_rally_settings_button.isEnabled())
        self.assertEqual(window.mining_profile_context.text(), "选择在线 MuMu 账号后可配置")
        self.assertEqual(window.beast_rally_profile_context.text(), "选择在线 MuMu 账号后可配置")


if __name__ == "__main__":
    unittest.main()
