"""Real ADB, real timer/lease, isolated schedule file; callback is read-only."""
import os
import sys
import tempfile
import threading
import time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QDateTime
from wjdr_mumu_assistant_qt import MainWindow
import wjdr_schedule as s

guard = threading.Timer(25, lambda: os._exit(124))
guard.daemon = True
guard.start()
app = QApplication([])
app.setStyle("Fusion")
output = Path("evidence/milestone-182-scheduler")
output.mkdir(parents=True, exist_ok=True)
with tempfile.TemporaryDirectory() as temp:
    window = MainWindow(sys.argv[1], False, False, False, False)
    window.schedule_path = Path(temp) / "schedule.json"
    window._show_page(5)
    window.show()
    deadline = time.monotonic() + 12
    while not (window.current_image is not None and window.device_combo.currentData()):
        app.processEvents()
        if time.monotonic() > deadline:
            raise RuntimeError("Device readiness deadline")
        time.sleep(0.05)
    assert window.adb.device == sys.argv[1]
    calls = []
    def read_only_callback():
        calls.append(time.time())
        window.adb.clone_for_device().screenshot(timeout=3)
    # Preserve the actual _start_worker ownership and persisted transition gate.
    window._start_beast_rally_flow = lambda: window._start_worker(window.adb.device, read_only_callback)
    window.schedule_time.setDateTime(QDateTime.currentDateTime().addSecs(2))
    window._add_schedule()
    job = s.read_jobs(window.schedule_path)[0]
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        app.processEvents()
        state = s.read_jobs(window.schedule_path)[0]["state"]
        if state in {"failed", "skipped", "missed"}:
            raise RuntimeError(s.read_jobs(window.schedule_path))
        if state == "finished":
            break
        time.sleep(0.02)
    else:
        raise RuntimeError("Schedule callback deadline")
    for _ in range(10):
        window._schedule_tick()
        app.processEvents()
    assert len(calls) == 1 and calls[0] >= job["run_at"]
    window.grab().save(str(output / "trigger-once.png"))
    print(f"PASS real device {sys.argv[1]}: due→fresh identity→lease→one read-only callback→finished; delay {calls[0]-job['run_at']:.3f}s", flush=True)
    # Verify cancellation through the UI; leave no real future task behind.
    window.schedule_time.setDateTime(QDateTime.currentDateTime().addSecs(60))
    window._add_schedule()
    window.schedule_table.selectRow(0)
    window._cancel_schedule()
    assert any(j["state"] == "cancelled" for j in s.read_jobs(window.schedule_path))
    print("PASS UI cancellation; zero game inputs; temporary schedule only", flush=True)
    window.close()
guard.cancel()
