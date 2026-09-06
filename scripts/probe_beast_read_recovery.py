"""Same-device fresh-frame recovery micro-test; zero game inputs."""
import argparse
from pathlib import Path
import sys
import threading
import time
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import wjdr_backend as b
from wjdr_beast_hunt import GuardedBeastADB, read_compact_capacity

p = argparse.ArgumentParser()
p.add_argument('--device', required=True)
p.add_argument('--window-benchmark', action='store_true')
a = p.parse_args()
adb = b.MuMuADB()
adb.connect(a.device)
lease = b.DeviceLease(adb.device_identity())
assert lease.acquire(), 'Account worker owns lease; probe skipped'
try:
    assert adb.foreground_is_game(), 'Not foreground game; no input'
    class ReadOnlyFault:
        device = adb.device
        failed = False
        def screenshot(self, **kwargs):
            if not self.failed:
                self.failed = True
                raise b.AdbError('INJECTED one-read failure; ADB itself is not disconnected')
            return adb.screenshot(**kwargs)
    guard = GuardedBeastADB(ReadOnlyFault(), threading.Event(), print)
    out = Path('evidence/milestone-175-bounded-read-recovery')
    out.mkdir(parents=True, exist_ok=True)
    for i in range(2):
        started = time.perf_counter()
        frame = guard.screenshot()
        captured = time.perf_counter()
        world = b.match_beast_rally_world_search(frame)
        print('frame', i, 'ADB', adb.device, 'capture_ms', round((captured-started)*1000),
              'recognition_ms', round((time.perf_counter()-captured)*1000), 'world', world)
        started = time.perf_counter()
        print('compact', read_compact_capacity(frame), 'ms', round((time.perf_counter()-started)*1000), 'ADB_size', frame.size)
        b._daily_reference_crop(frame, (1260, 2400, 1420, 2550)).save(out/f'world-control-{i}.png')
    for i in range(3 if a.window_benchmark else 0):
        started = time.perf_counter()
        fast = adb.fast_window_screenshot()
        captured = time.perf_counter()
        world = b.match_beast_rally_world_search(fast)
        print('window', i, 'capture_ms', round((captured-started)*1000, 1),
              'recognition_ms', round((time.perf_counter()-captured)*1000, 1),
              'size', fast.size, 'world', world)
        # Compare only a reviewed opaque control, not animated background.
        region = (1290, 2410, 1390, 2530)
        aa = np.asarray(b._daily_reference_crop(frame, region)).astype(float)
        bb = np.asarray(b._daily_reference_crop(fast, region).resize((aa.shape[1], aa.shape[0]))).astype(float)
        print('window_control_vs_adb_mae', round(float(np.abs(aa-bb).mean()), 2))
        if i == 0:
            b._daily_reference_crop(fast, (1200, 2310, 1440, 2560)).save(out/'window-control.png')
finally:
    lease.release()
