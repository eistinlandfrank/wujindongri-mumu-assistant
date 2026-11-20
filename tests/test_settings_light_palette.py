import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
from PySide6.QtCore import QSettings
from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QApplication
from wjdr_mumu_assistant_qt import MiningLevelSettingsDialog, BeastRallySettingsDialog
from wjdr_backend import MiningLevelProfile, BeastRallyProfile
from wjdr_ui_appearance import ApplicationAppearance, THEMES


class SettingsPaletteTest(unittest.TestCase):
    def test_open_dialogs_follow_assistant_appearance(self):
        app = QApplication.instance() or QApplication([])
        original = app.palette()
        with TemporaryDirectory() as temp:
            settings = QSettings(str(Path(temp) / "appearance.ini"), QSettings.Format.IniFormat)
            appearance = ApplicationAppearance(app, settings)
            try:
                with patch.object(ApplicationAppearance, "current", return_value=appearance):
                    dialogs = [
                        MiningLevelSettingsDialog("Test account", "test", MiningLevelProfile()),
                        BeastRallySettingsDialog("Test account", "test", BeastRallyProfile(), 60),
                    ]
                for dialog in dialogs:
                    dialog.show()
                for mode, colors in THEMES.items():
                    appearance.set_mode(mode, persist=False)
                    app.processEvents()
                    for dialog in dialogs:
                        palette = dialog.palette()
                        self.assertEqual(palette.color(QPalette.ColorRole.Window), QColor(colors["window"]))
                        self.assertEqual(palette.color(QPalette.ColorRole.WindowText), QColor(colors["text"]))
                        self.assertIn(colors["surface"], dialog.styleSheet())
                for dialog in dialogs:
                    dialog.close()
            finally:
                appearance.sync_timer.stop()
                appearance.deleteLater()
                app.setPalette(original)


if __name__ == "__main__":
    unittest.main()
