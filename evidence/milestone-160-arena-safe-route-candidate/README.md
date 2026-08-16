# Milestone 160 — Arena safe-route candidate (offline only)

Date: 2026-08-15

## Outcome

- The reviewed Daily card now requires the exact `进行1次竞技场挑战` title **and** its own same-row blue `前往`; title-only, missing-Go, and adjacent-row-Go frames return no candidate.
- The candidate uses a distinct non-actionable type. The Daily controller records it once, makes **zero Arena input**, and immediately continues later tasks without creating a failure/skip lock.
- This is deliberately `implemented + focused-regression-tested`, not live proof and not an executable Arena battle route. No ADB/device discovery, game input, packaging, purchase, refresh, paid attempt, opponent choice, or battle occurred.

## Why the route remains fail-closed

The Word guide provides tight crops for the Daily card, a `挑战` button with a red `5`, five anonymous crossed-swords controls, `战斗`, pause, exit, tap-anywhere result, free refresh, X, and the `万国竞技场` title. It does **not** provide:

1. a complete two-anchor Arena landing frame that proves the `5` is an ordinary free attempt rather than a paid/replenished count;
2. a complete opponent card with stable identity/geometry, so every crossed-swords button is currently an unknown opponent;
3. complete two-anchor formation/battle/pause/exit/result frames tied to that exact opponent lineage.

Without those assets, even tapping the Daily `前往` would leave the worker unable to prove the next safe action. Coordinates were not invented from button-only crops.

## Evidence and checks

- Tight de-identified source crop: `reviewed-daily-arena-card.png` (copied from the user-provided Word guide; no account data).
- Focused regression: `python tests\test_arena_safe_route_candidate.py`
- Syntax: `python -m py_compile wjdr_backend.py wjdr_mumu_assistant_qt.py`
- Code anchors: `ArenaMissionCandidate`, `match_daily_arena_mission`, and `arena_card_staged_fail_closed`.
