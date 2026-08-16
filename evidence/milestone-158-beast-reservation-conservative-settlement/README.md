# Milestone 158 — conservative settlement of a pre-fix Beast reservation

- Scope: manager instance 2 (`16448`) only; no other ADB instance was read or controlled.
- The pre-fix worker logged one exact ordinary Expedition at 15:18:48 and reserved stamina 20, but it was stopped before the account-row transition could be persisted.
- A later zero-input process refused to dispatch while that reservation remained unresolved. At 15:23:20 two fresh frames showed all six account-owned Wilderness rows idle; `returned-six-idle.png` is the tight account-free crop.
- The reservation was moved to conservative committed spend (`spent=40`, `reserved=0`) only to avoid a permanent retry lock. This does **not** prove the missing row association and does not upgrade the Beast live-acceptance matrix.
- The following run must still prove `0/6 -> 1/6 -> 0/6` continuously in one worker before the repeating route can be accepted.
