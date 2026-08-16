# Milestone 159 — corrected Beast continuous-cycle live run

- Scope: manager instance 2 (`16448`) only; no other ADB instance was read or controlled.
- The source worker began at 15:24:40 with persisted `Lv.8 / stamina cap unlimited`.
- Two fresh expanded-panel frames established the account baseline `0/6`; the blue allied-rally row was excluded.
- The reviewed route then clicked only Wilderness Search, Icefield Beast, level 8 Search, exact three-minute Launch Rally, first formation, and ordinary Expedition.
- At 15:25:10 the same worker read an exact expanded account header transition `0/6 -> 1/6`; stamina 20 settled once to `spent=60, reserved=0`.
- `busy-1-of-6.png` is the tight account-free busy proof: exact `1/6`, `集结等待：深渊龙龟`, its countdown, and the other five idle rows.
- At 15:27:14 that same worker proved the newly busy account queue returned idle. It immediately re-established `0/6`, reopened Search at 15:27:28, and completed the reviewed route again.
- The second ordinary Expedition at 15:27:41 changed the same account capacity `0/6 -> 1/6` at 15:27:49 and settled one further stamina 20 to `spent=80, reserved=0`.
- Therefore the corrected source worker has live-proved the continuous `idle -> busy -> idle -> next-cycle busy` lifecycle. This proves source behavior, not a packaged release.
- Candidate integrity: `verify_beast_rally_candidate.py` passed all 29 focused tests before the worker started.
