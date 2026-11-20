"""UI-only checks: no ADB/game input is issued."""
import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import Mock, patch
from PIL import Image
from PySide6.QtCore import QSettings, Qt
from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QApplication, QLabel, QMainWindow, QMenu, QMessageBox, QPushButton, QScrollArea, QToolButton
from wjdr_mumu_assistant_qt import MainWindow, UiSignals
from wjdr_ui_appearance import THEME_KEY, THEMES, ApplicationAppearance
from wjdr_ui_components import LightSettingsDialog


def make_window(appearance_settings=None):
    window = MainWindow.__new__(MainWindow)
    QMainWindow.__init__(window)
    window.adb = Mock(device="device-a")
    window.worker = None
    window.signals = UiSignals()
    window.devices = ["device-a", "device-b"]
    settings = appearance_settings if appearance_settings is not None else Mock()
    with patch("wjdr_ui_appearance.QSettings", return_value=settings):
        window._build_ui()
    window._apply_style()
    return window


class MultiDeviceUITests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])
        cls.temp = TemporaryDirectory()
        cls.addClassCleanup(cls.temp.cleanup)
        cls.settings_path = str(Path(cls.temp.name) / "appearance.ini")
        cls.settings = QSettings(cls.settings_path, QSettings.Format.IniFormat)

    def setUp(self):
        self.window = make_window(self.settings)
        self.window.appearance.set_mode("light")

    def tearDown(self):
        self.window.hide()
        self.window.deleteLater()

    def test_all_pages_remain_in_order_and_accessible(self):
        window = self.window
        window.resize(1080, 720)
        window.show()
        titles = ["设备中心", "联盟帮助", "联盟红包", "每日任务", "巨兽集结",
                  "定时启动", "任务编排", "运行日志", "关于与安全", "备战积分"]
        if hasattr(window, "_build_fortress_page"):
            titles.append("堡垒跑联盟")
        self.assertEqual(window.stack.count(), len(titles))
        for index, title in enumerate(titles):
            window._show_page(index)
            self.app.processEvents()
            self.assertEqual(window.page_title.text(), title)
            self.assertEqual(window.width(), 1080)
            self.assertEqual(window.height(), 720)
            self.assertTrue(window.stop_button.isVisible())
            self.assertTrue(window.appearance_combo.isVisible())
            if index not in (7, 9):
                self.assertIsInstance(window.stack.widget(index), QScrollArea)
                self.assertLessEqual(window.stack.widget(index).horizontalScrollBar().maximum(), 0)

    def test_sidebar_orders_workflows_before_management_and_support(self):
        nav = self.window.nav_scroll.widget().layout()
        labels = [
            item.text()
            for index in range(nav.count())
            if isinstance(item := nav.itemAt(index).widget(), (QPushButton, QLabel))
        ]
        expected = ["设备中心", "自动化", "巨兽集结", "每日任务", "联盟帮助", "联盟红包"]
        if hasattr(self.window, "_build_fortress_page"):
            expected.append("堡垒跑联盟")
        expected.extend(["任务管理", "定时启动", "备战积分", "任务编排", "排查与帮助", "运行日志", "关于与安全"])
        self.assertEqual(labels, expected)
        self.window.nav_buttons[4].click()
        self.assertEqual(self.window.stack.currentIndex(), 4)
        self.assertTrue(self.window.nav_buttons[4].isChecked())

    def test_shortcuts_navigate_and_batch_start_is_in_disclosure(self):
        window = self.window
        window.show()
        shortcuts = window.stack.widget(0).findChildren(QPushButton, "quickTask")
        self.assertEqual([button.text() for button in shortcuts], ["巨兽集结", "每日任务", "联盟帮助"])
        shortcuts[0].click()
        self.assertEqual(window.stack.currentIndex(), 4)
        self.assertIsNone(window.worker)
        beast = window.stack.currentWidget()
        batch = next(button for button in beast.findChildren(QPushButton) if button.text() == "全部实例分别启动")
        self.assertFalse(batch.isVisible())
        beast.findChild(QToolButton, "disclosureButton").click()
        self.assertTrue(batch.isVisible())

    def test_appearance_updates_all_windows_and_open_dialogs(self):
        window = self.window
        window._show_page(4)
        window._set_status("测试状态", "error")
        worker = Mock()
        window.worker = worker
        other = make_window()
        dialog = LightSettingsDialog(other)
        message = QMessageBox(other)
        menu = QMenu()
        index = window.appearance_combo.findData("dark")
        window.appearance_combo.activated.emit(index)
        self.app.processEvents()
        self.assertEqual(other.appearance_combo.currentText(), "深色")
        self.assertIs(other.appearance, window.appearance)
        self.assertEqual(window.stack.currentIndex(), 4)
        self.assertIs(window.worker, worker)
        self.assertEqual(window.status_pill.property("statusKind"), "error")
        self.assertEqual(window.status_pill.text(), "测试状态")
        for widget in (self.app, window, other, dialog, message, menu):
            self.assertEqual(
                widget.palette().color(QPalette.ColorRole.Window),
                QColor(THEMES["dark"]["window"]),
                type(widget).__name__,
            )
        self.assertIn(THEMES["dark"]["window"], dialog.styleSheet())
        self.assertEqual(self.settings.value(THEME_KEY), "dark")
        other.deleteLater()
        menu.deleteLater()

    def test_cleared_preferences_default_to_system_and_track_external_changes(self):
        appearance = self.window.appearance
        other_settings = QSettings(self.settings_path, QSettings.Format.IniFormat)
        other_settings.remove(THEME_KEY)
        other_settings.sync()
        appearance.sync_preferences()
        self.assertEqual(self.window.appearance_combo.currentData(), "system")
        other_settings.setValue(THEME_KEY, "dark")
        other_settings.sync()
        appearance.sync_preferences()
        self.assertEqual(self.window.appearance_combo.currentData(), "dark")
        self.assertEqual(appearance.theme, "dark")

    def test_system_notification_changes_only_system_mode(self):
        appearance = ApplicationAppearance.current()
        hints = appearance.style_hints
        with patch.object(hints, "colorScheme", return_value=Qt.ColorScheme.Light) as scheme:
            appearance.set_mode("system")
            self.assertEqual(appearance.theme, "light")
            scheme.return_value = Qt.ColorScheme.Dark
            hints.colorSchemeChanged.emit(Qt.ColorScheme.Dark)
            self.app.processEvents()
            self.assertEqual(appearance.theme, "dark")
            self.assertEqual(self.window.appearance_combo.currentData(), "system")
            appearance.set_mode("light")
            hints.colorSchemeChanged.emit(Qt.ColorScheme.Dark)
            self.app.processEvents()
            self.assertEqual(appearance.theme, "light")

    def test_stale_device_frame_is_rejected(self):
        self.window.current_image = None
        self.window._apply_image(("device-b", Image.new("RGB", (10, 10))))
        self.assertIsNone(self.window.current_image)
        frame = Image.new("RGB", (10, 10))
        self.window._apply_image(("device-a", frame))
        self.assertIs(self.window.current_image, frame)

    def test_capture_explicitly_binds_serial(self):
        self.window._capture_job()
        self.window.adb.screenshot.assert_called_once_with(device="device-a")

    def test_open_other_windows_never_starts_tasks(self):
        with patch.object(self.window, "_spawn_instance") as spawn:
            self.window._open_other_windows()
            spawn.assert_called_once_with("device-b")

    def test_child_does_not_inherit_qa_and_is_not_duplicated(self):
        process = Mock()
        process.poll.return_value = None
        with patch.dict(os.environ, {"WJDR_BEAST_MAX_CYCLES": "2", "WJDR_QA_PAGE": "4"}), \
             patch("wjdr_mumu_assistant_qt.subprocess.Popen", return_value=process) as spawn:
            self.window._spawn_instance("device-b")
            self.window._spawn_instance("device-b")
            self.assertEqual(spawn.call_count, 1)
            args = spawn.call_args.args[0]
            self.assertEqual(args[-2:], ["--device", "device-b"])
            self.assertNotIn("WJDR_BEAST_MAX_CYCLES", spawn.call_args.kwargs["env"])
            self.assertNotIn("WJDR_QA_PAGE", spawn.call_args.kwargs["env"])

    def test_running_rescan_preserves_adb(self):
        adb = self.window.adb
        self.window.worker = Mock()
        self.window.worker.is_alive.return_value = True
        self.window._connect_job()
        self.assertIs(self.window.adb, adb)

    def test_logs_are_filtered_to_bound_device(self):
        with patch("wjdr_mumu_assistant_qt.LOG_FILE"):
            self.window._append_log("[now] [device-b] private other account")
            self.window._append_log("[now] [device-a] current account")
        self.assertNotIn("private", self.window.log_edit.toPlainText())
        self.assertIn("current account", self.window.log_edit.toPlainText())


if __name__ == "__main__":
    unittest.main()
