# Milestone 161 — Alliance donation short-segment fallback

Date: 2026-08-15

## Outcome

- Replaced the single 10,000-ms ordinary-food hold with one exact 1,200-ms segment (`timeout=3`).
- The segment starts only after the existing helper has proved the precise blue ordinary-food button and its yellow-diamond sibling in two fresh stable frames. The sibling remains page evidence only and never yields an input coordinate.
- Immediately after the segment, the worker captures exactly two frames with no intentional inter-frame delay:
  - two grey/page frames mark only the current availability window exhausted;
  - two still-blue frames cannot authorise another segment because the repository has no reliable Alliance-Coin numeric reader;
  - inconsistent/unknown frames also stop segmentation.
- The still-blue and uncertain branches defer only donation for at most 30 seconds, then continue independent Daily items. Daily-task progress remains the only authority for completed-count growth; hold duration is never converted into click/donation count.
- The donation segment route has an explicit deadline capped by both the shared automation-step ceiling and the 30-second retry-lock ceiling.

## Safety boundary

- No yellow-diamond coordinate is returned to this controller.
- No purchase, refresh, second segment, generic dialog, or recovery click was added.
- This was offline-only: no ADB/device access, game input, packaging, or live claim.

## Evidence and regression

- Tight de-identified control crop: `ordinary-food-control.png`.
- `python tests\test_daily_donation_short_segments.py`
- `python tests\test_daily_donation_long_press.py`
- `python tests\test_daily_donation_persistence.py`
- `python tests\test_daily_lock_ceiling.py`
- `python -m py_compile wjdr_mumu_assistant_qt.py`

The larger `test_daily_route_safety.py` reaches and passes the updated donation assertions, then stops later at the pre-existing unrelated `gather_recheck_candidates` assertion.
