# Milestone 162 — existing training queue fast yield

- Device scope: `127.0.0.1:16448` only; stable per-account identity remains the runtime key.
- Live failure: after the exact Spear Daily `Go`, the reviewed fixed camp and ordinary entry opened an already-running natural queue. The old second-entry loop ignored this page for about 22 seconds and then stopped.
- Evidence: `training_active_queue_account_free.png` is a tight account-free crop proving the static `训练中` row and natural countdown. The yellow instant-complete and blue speed-up controls are excluded from the crop and are never candidates.
- Fix: `finish_training_camp_double_enter` now double-confirms `match_daily_training_active` and immediately reuses `defer_active_training_and_reopen_daily`. It returns the explicit `active_queue` state so Shield/Spear/Archer callers stop the camp route and continue Daily tasks.
- Verification: `python -m py_compile wjdr_mumu_assistant_qt.py`, `tests/test_training_active_queue_double_entry.py`, and `tests/test_training_fixed_camp_fallback.py` all pass within the 30-second command ceiling.
- Live acceptance: a fresh source process repeated the exact Spear lineage at `16:05:18`, tapped the reviewed camp at `16:05:20`, and entered the exact ordinary-training surface at `16:05:22`. By `16:05:25` it had double-confirmed and cropped the natural countdown; at `16:05:26` it used only the reviewed Back point, and at `16:05:28` it reopened Daily. No instant completion, speed-up, duplicate Train, or diamond input occurred.
