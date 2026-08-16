# Milestone 164 — Arena executable route (offline integration)

Date: 2026-08-15

Scope was deliberately offline: no ADB connection, no emulator input, no package build.
The source material was the reviewed `arena_*` live sequence in `%TEMP%`; repository
fixtures contain only account-free page anchors, digits, buttons and selection checks.

## Implemented lineage

1. Require the exact Daily title `进行1次竞技场挑战` and its same-row blue `前往` in two frames.
2. Require two frames of `万国竞技场`, the ordinary `挑战` control and a red remaining count `1..5`.
3. Read the challenge list twice: my exact power, remaining free count and all five opponent powers.
   Select only the lowest power strictly below mine. No refresh, plus, shop or paid coordinate exists.
4. Require two setup frames proving my exact power is greater, the opponent corresponds to the chosen
   rounded list value, exactly five green hero checks are present, and the ordinary green `战斗` is visible.
5. Accept victory or defeat only through the correlated full `点击任意位置退出` sentence. Back on the
   same list, require the free count to have decreased by exactly one before another battle.
6. Continue inside Arena until the count reaches zero. There is no intermediate Daily return and the
   `进行5次竞技场挑战` Go is never a second entry authority.
7. Return once to Daily. Exact completed 1-times and 5-times rows can each authorise their own green
   `领取`; the existing claim drain may also collect other already-completed rewards. Reaching 325 is a
   minimum target: completed claimable rewards remain eligible, but no unfinished task receives a new Go.

All recognition waits use immediate frames with an intentional delay at most 0.25 s. Every bounded stage
is at most 30 s and the Arena failure retry lock is the shared maximum of 30 s.

## Offline regression

- `python tests/test_arena_safe_route_candidate.py` — PASS
- `python -m py_compile wjdr_backend.py wjdr_mumu_assistant_qt.py` — PASS
- The Arena-only result-exit matcher is scoped to the immediately correlated ordinary battle result;
  both retained live victory frames match the complete sentence at the neutral side point `(120,2200)`
  with score `1.000000`. It is not registered as a global abnormal-page recovery rule.
- Sanitised numeric proof: my power `14,688,162`; five opponents
  `20,569,000 / 30,711,000 / 13,144,000 / 4,595,000 / 3,653,000`; chosen opponent `3,653,000`.
- Sanitised setup proof: exact opponent `3,653,034`, my power is higher, selected heroes `5`.

This milestone does not claim that the newly integrated source route has completed a new autonomous live
run or that a new package was built. Focused game-workflow acceptance remains milestone 163.
