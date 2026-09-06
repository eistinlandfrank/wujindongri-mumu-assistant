# WJDR Agent Rules

## Hard timeout — highest priority (updated 2026-09-06)

- The user's latest limit is five minutes: every command, helper, build, test, ADB request, screenshot probe, recognition loop, and live step must have an explicit wall-clock timeout of 300 seconds or less. Prefer shorter scoped timeouts; do not extend normal game waits or safety retry locks merely because the command ceiling increased.
- Interrupt the operation immediately at the timeout. Never extend it into an unbounded wait.
- Split longer policies into bounded slices and re-read fresh state between slices; keep progress updates frequent, rather than remaining silent for five minutes.
- Keep every intentional game-input delay <=1.5 seconds; take passive recognition frames immediately when possible.

## Project

- `wjdr_mumu_assistant_qt.py` is the desktop entry; `wjdr_backend.py` owns recognition, persistence, and ADB logic.
- Use the per-account stable identity (`MuMu manager index + Android ID`) for profiles, locks, and ledgers.
- Run focused checks before release. For Icefield Beast: `python C:\Users\TSUKI\.codex\skills\wjdr-mumu-daily-automation\scripts\verify_beast_rally_candidate.py --repo C:\Users\TSUKI\Documents\WJDR` with a 30-second outer timeout.
- Preserve fail-closed safety: no purchases, diamonds, speed-ups, Auto Join, unreviewed battles, generic dialogs, or arbitrary recovery clicks.
- Store only tight de-identified milestone evidence. Saved images never feed runtime recognition.
- Treat `C:\Users\TSUKI\.codex\skills\wjdr-mumu-daily-automation\SKILL.md` and its routed references as the compact cross-session workflow.

## Release contract

- After every completed revision, run focused tests, open the current frontend for the user (no auto-task flags), verify its visible window, then commit and push the scoped changes to GitHub main. Do not wait for EXE packaging to show a source demo or publish source. Never interrupt an active worker simply to refresh the demo.
- Fast preview: `powershell -NoProfile -File scripts/demo_frontend.ps1` (15-second startup deadline, leaves the app open). Use the full portable build for distributable releases; `-SkipRuntime` only rewraps an already verified, source-current runtime and is not a source compilation shortcut. A source preview does not prove the packaged executable boots.

- The primary public artifact must be a no-install portable build named `WJDRMuMuAssistant_vX.Y.Z_Portable.exe` (or a portable archive only when a single executable is technically impossible). The user must be able to download it and start the assistant directly without an installation wizard.
- A portable launcher may download and SHA256-verify bounded release parts, then unpack/update its private portable runtime and launch the assistant. It must not install into Program Files, create Start Menu entries, register an uninstaller, or require administrator rights.
- Do not publish `Setup.exe` as the primary download. An installer is optional only when the user explicitly asks for one; portable remains the default and must be tested through the real one-click launch path before release.

## Current release

- Current source candidate: v5.63.0. Primary artifact path is `release_v5_63/WJDRMuMuAssistant_v5.63.0_Portable.exe`; do not treat its existence as release acceptance. Source GUI preview boots in 3.9 seconds; 50 focused tests pass. Fixed Lv.8/3-minute/`打野`; green compact rally ICON plus same-row title proves own rally, not the green timer bar. Old reservations recover after fresh double six-idle-row proofs and move into uncertain budget accounting, not confirmed spend. Mining/Beast dialogs force a light palette. New ownership/recovery continuous live acceptance and final downloaded-portable GUI smoke remain pending. Previous v5.62 installer is historical only.
- v5.58 at `release_v5_58\dist\WJDRMuMuAssistant\WJDRMuMuAssistant.exe`, SHA256 `64712D1C95ED9B74F1B06486EF5FBC683CC81F58BD081187F53A999FFFB4FCAE`, remains the fallback baseline.
- The v5.57 and v5.59 build directories were interrupted at the hard 30-second boundary and are not releases; never launch or publish them.
- Current source live-proved the instance-2 Lv.8 Beast lifecycle `0/6 -> 1/6 -> 0/6 -> next-cycle 1/6` while excluding the blue allied-rally row. Evidence: `evidence\milestone-159-beast-continuous-cycle-live`.
- Every Daily failure/yield/suppression/idle retry gate is capped at 30 seconds. Warehouse three-minute, free-recruit five-minute, and natural training/gather countdowns are business reminders only and cannot postpone an independent full scan beyond 30 seconds.
