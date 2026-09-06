import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
import unittest
from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QApplication, QDialogButtonBox
from wjdr_mumu_assistant_qt import MiningLevelSettingsDialog, BeastRallySettingsDialog
from wjdr_backend import MiningLevelProfile, BeastRallyProfile


class SettingsLightPaletteTest(unittest.TestCase):
    def test_dialogs_override_dark_system_palette(self):
        app = QApplication.instance() or QApplication([])
        original = app.palette()
        dark = QPalette()
        dark.setColor(QPalette.ColorRole.Window, QColor("#151515"))
        dark.setColor(QPalette.ColorRole.Base, QColor("#202020"))
        dark.setColor(QPalette.ColorRole.Text, QColor("#EEEEEE"))
        app.setPalette(dark)
        try:
            dialogs = [
                MiningLevelSettingsDialog("Test account", "test", MiningLevelProfile()),
                BeastRallySettingsDialog("Test account", "test", BeastRallyProfile(), 60),
            ]
            for dialog in dialogs:
                dialog.show()
                app.processEvents()
                self.assertGreater(dialog.palette().color(QPalette.ColorRole.Window).lightness(), 230)
                self.assertLess(dialog.palette().color(QPalette.ColorRole.WindowText).lightness(), 100)
                for button in dialog.findChildren(QDialogButtonBox)[0].buttons():
                    self.assertGreater(button.palette().color(QPalette.ColorRole.Button).lightness(), 230)
                    self.assertLess(button.palette().color(QPalette.ColorRole.ButtonText).lightness(), 120)
                dialog.close()
        finally:
            app.setPalette(original)


if __name__ == "__main__":
    unittest.main()
