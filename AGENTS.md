# WJDR Agent Rules

## Hard timeout — highest priority

- Give every shell command, helper, build, test, ADB request, screenshot probe, recognition loop, and live automation step an explicit wall-clock timeout of 30 seconds or less.
- Interrupt the operation immediately at the timeout. Never extend it into an unbounded wait.
- Split longer policies into independent <=30-second slices and re-read fresh state between slices.
- Keep every intentional game-input delay <=1.5 seconds; take passive recognition frames immediately when possible.

## Project

- `wjdr_mumu_assistant_qt.py` is the desktop entry; `wjdr_backend.py` owns recognition, persistence, and ADB logic.
- Use the per-account stable identity (`MuMu manager index + Android ID`) for profiles, locks, and ledgers.
- Run focused checks before release. For Icefield Beast: `python C:\Users\TSUKI\.codex\skills\wjdr-mumu-daily-automation\scripts\verify_beast_rally_candidate.py --repo C:\Users\TSUKI\Documents\WJDR` with a 30-second outer timeout.
- Preserve fail-closed safety: no purchases, diamonds, speed-ups, Auto Join, unreviewed battles, generic dialogs, or arbitrary recovery clicks.
- Store only tight de-identified milestone evidence. Saved images never feed runtime recognition.
- Treat `C:\Users\TSUKI\.codex\skills\wjdr-mumu-daily-automation\SKILL.md` and its routed references as the compact cross-session workflow.

## Current release

- Current source and packaged release: v5.61. Portable EXE: `release_v5_61\dist\WJDRMuMuAssistant\WJDRMuMuAssistant.exe`, SHA256 `0F478B80167F4F4AC0F5411394E5064AAACE0B9BC98FFD1473406C32FDD66A09`. The package contains 234 byte-verified runtime assets and passed the no-input `--help` smoke check.
- v5.58 at `release_v5_58\dist\WJDRMuMuAssistant\WJDRMuMuAssistant.exe`, SHA256 `64712D1C95ED9B74F1B06486EF5FBC683CC81F58BD081187F53A999FFFB4FCAE`, remains the fallback baseline.
- The v5.57 and v5.59 build directories were interrupted at the hard 30-second boundary and are not releases; never launch or publish them.
- Current source live-proved the instance-2 Lv.8 Beast lifecycle `0/6 -> 1/6 -> 0/6 -> next-cycle 1/6` while excluding the blue allied-rally row. Evidence: `evidence\milestone-159-beast-continuous-cycle-live`.
- Every Daily failure/yield/suppression/idle retry gate is capped at 30 seconds. Warehouse three-minute, free-recruit five-minute, and natural training/gather countdowns are business reminders only and cannot postpone an independent full scan beyond 30 seconds.
