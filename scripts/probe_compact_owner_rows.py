"""Bounded passive queue evidence; never acquire input or interrupt workers."""
import sys
import time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import wjdr_backend as b
import wjdr_beast_hunt as h

out = Path('evidence/milestone-183-owned-disappearance')
out.mkdir(parents=True, exist_ok=True)
adb = b.MuMuADB()
devices = adb.connect()
for device in devices:
    adb.device = device
    print(device, adb.device_identity(), flush=True)
    for i in range(2):
        started = time.monotonic()
        frame = adb.screenshot(timeout=3)
        print('world', b.match_beast_rally_world_search(frame), 'numeric', b.read_daily_march_capacity(frame), flush=True)
        cap = h.read_compact_capacity(frame)
        icons = h.read_compact_queue_icons(frame, cap)
        print('icons', icons, 'blue_free', h.blue_only_free_slot(cap, icons), flush=True)
        print(i, h.read_compact_capacity(frame), h.read_compact_rally_rows(frame),
              h.read_compact_marching_rows(frame), 'seconds', time.monotonic()-started, flush=True)
        b._daily_reference_crop(frame, (0,300,590,1400)).save(out / f'{device.split(":")[-1]}-rows-{i}.png')
