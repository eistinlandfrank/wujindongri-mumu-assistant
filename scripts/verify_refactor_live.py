"""Read-only single-device check of the refactored frontend."""
import os
import sys
import threading
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from PySide6.QtWidgets import QApplication
from wjdr_mumu_assistant_qt import MainWindow

guard = threading.Timer(24, lambda: os._exit(124))
guard.daemon = True
guard.start()
device = sys.argv[1]
app = QApplication([])
window = MainWindow(device, False, False, False, False)
window.show()
deadline = time.monotonic() + 19
while time.monotonic() < deadline:
    app.processEvents()
    if (window.adb and window.adb.device == device and window.current_image is not None
            and window.device_combo.currentData() and window.device_combo.currentData().get('identity')):
        break
    time.sleep(0.05)
else:
    raise RuntimeError('Device window or fresh frame unavailable')
for index in range(window.stack.count()):
    window._show_page(index)
    app.processEvents()
    assert window.adb.device == device and window.worker is None
queued = []
window._start_worker = lambda serial, job: queued.append((serial, job))
window._start_daily_rewards_flow()
assert len(queued) == 1 and queued[0][0] == device and callable(queued[0][1])
assert window.worker is None
print(f'PASS: fresh {window.current_image.size} frame; {window.stack.count()} pages; Daily preflight bound to selected device; no game worker', flush=True)
window.close()
guard.cancel()
