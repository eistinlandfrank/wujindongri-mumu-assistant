"""Same-device fresh-frame recovery micro-test; zero game inputs."""
import argparse
from pathlib import Path
import sys
import threading
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import wjdr_backend as b
from wjdr_beast_hunt import GuardedBeastADB, read_compact_capacity

p = argparse.ArgumentParser()
p.add_argument('--device', required=True)
p.add_argument('--ipc-benchmark', '--window-benchmark', action='store_true')
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
    for i in range(2):
        started = time.perf_counter()
        frame = guard.screenshot()
        captured = time.perf_counter()
        world = b.match_beast_rally_world_search(frame)
        print('frame', i, 'ADB', adb.device, 'capture_ms', round((captured-started)*1000),
              'recognition_ms', round((time.perf_counter()-captured)*1000), 'world', world)
        started = time.perf_counter()
        print('compact', read_compact_capacity(frame), 'ms', round((time.perf_counter()-started)*1000), 'IPC_size', frame.size)
    for i in range(3 if a.ipc_benchmark else 0):
        started = time.perf_counter()
        frame = adb.screenshot()
        print('ipc', i, 'capture_ms', round((time.perf_counter()-started)*1000, 1), 'size', frame.size)
finally:
    lease.release()
