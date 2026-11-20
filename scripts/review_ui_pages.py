"""Render every page without ADB, accounts or game input (25s watchdog)."""
import os
os.environ.setdefault("QT_QPA_PLATFORM", "windows" if os.name == "nt" else "offscreen")
import argparse
import sys
import threading
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QScrollArea, QToolButton
from wjdr_mumu_assistant_qt import MiningLevelSettingsDialog, BeastRallySettingsDialog
from wjdr_backend import MiningLevelProfile, BeastRallyProfile
from tests.test_multi_device_ui import make_window

guard = threading.Timer(25, lambda: os._exit(124))
guard.daemon = True
guard.start()
app = QApplication([])
app.setStyle("Fusion")
window = make_window()
window.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen)
parser = argparse.ArgumentParser()
parser.add_argument("output", type=Path)
parser.add_argument("--theme", choices=("light", "dark"), default="light")
args = parser.parse_args()
window.appearance.set_mode(args.theme, persist=False)
output = args.output
output.mkdir(parents=True, exist_ok=True)
for width, height in ((1080, 720), (1280, 840)):
    window.resize(width, height)
    window.show()
    for index in range(window.stack.count()):
        window._show_page(index)
        app.processEvents()
        assert window.width() == width, (index, window.width(), width)
        assert window.height() == height, (index, window.height(), height)
        assert window.grab().save(str(output / f"page-{index}-{width}.png"))
        page = window.stack.widget(index)
        if isinstance(page, QScrollArea) and page.verticalScrollBar().maximum():
            page.verticalScrollBar().setValue(page.verticalScrollBar().maximum())
            app.processEvents()
            assert window.grab().save(str(output / f"page-{index}-{width}-bottom.png"))
            page.verticalScrollBar().setValue(0)
        for toggle in page.findChildren(QToolButton, "disclosureButton"):
            toggle.setChecked(True)
            app.processEvents()
            if isinstance(page, QScrollArea):
                assert page.horizontalScrollBar().maximum() == 0, (width, index)
                page.verticalScrollBar().setValue(page.verticalScrollBar().maximum())
                app.processEvents()
            assert window.grab().save(str(output / f"page-{index}-{width}-expanded.png"))
            toggle.setChecked(False)
            if isinstance(page, QScrollArea):
                page.verticalScrollBar().setValue(0)
        print(f"{width}x{height} page {index}: rendered", flush=True)
window.hide()
for name, dialog in (
    ("mining", MiningLevelSettingsDialog("演示账号", "演示设备", MiningLevelProfile(), window)),
    ("beast", BeastRallySettingsDialog("演示账号", "演示设备", BeastRallyProfile(), 0, window)),
):
    dialog.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen)
    dialog.show()
    app.processEvents()
    assert dialog.grab().save(str(output / f"settings-{name}.png"))
    dialog.hide()
guard.cancel()
