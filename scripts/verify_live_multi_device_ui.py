"""Read-only live UI gate: two real ADBs, fresh frames, no game tasks."""
import os
import sys
import time
import threading
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from PySide6.QtWidgets import QApplication, QDialog, QPushButton
from PySide6.QtCore import QTimer
from wjdr_mumu_assistant_qt import MainWindow

guard = threading.Timer(25, lambda: os._exit(124))
guard.daemon = True
guard.start()
devices = sys.argv[1:]
assert len(devices) == 2 and devices[0] != devices[1]
app = QApplication([])
app.setStyle("Fusion")
windows = [MainWindow(device, False, False, False, False) for device in devices]
for i, window in enumerate(windows):
    window.move(30 + i * 100, 30 + i * 50)
    window.show()
deadline = time.monotonic() + 20
while time.monotonic() < deadline:
    app.processEvents()
    if all(w.adb and w.adb.device == d and w.current_image is not None and
           w.device_combo.currentData() and w.device_combo.currentData()["device"] == d
           for w, d in zip(windows, devices)):
        break
    time.sleep(0.05)
else:
    raise RuntimeError("Two devices did not become independently ready within 20s")
for window, device in zip(windows, devices):
    identity = window.device_combo.currentData()["identity"]
    assert identity
    for index in range(8):
        window._show_page(index)
        app.processEvents()
        assert window.adb.device == device and window.worker is None
    window._show_page(4)
    assert f"[{devices[1] if device == devices[0] else devices[0]}]" not in window.log_edit.toPlainText()
    print(f"PASS {device}: fresh {window.current_image.size}; 8 pages; no worker; isolated logs", flush=True)
assert windows[0].device_combo.currentData()["identity"] != windows[1].device_combo.currentData()["identity"]
result = []
def inspect_manager():
    dialog = app.activeModalWidget()
    if isinstance(dialog, QDialog):
        buttons = [b.accessibleName() for b in dialog.findChildren(QPushButton)]
        result.append(all(f"打开手机 {device}" in buttons for device in devices))
        dialog.grab().save("evidence/milestone-181-ui-multidevice/device-manager.png")
        dialog.reject()
QTimer.singleShot(100, inspect_manager)
windows[0]._open_device_manager()
assert result == [True]
print("PASS real two-device manager; zero game-task starts", flush=True)
for window in windows:
    window.close()
guard.cancel()
