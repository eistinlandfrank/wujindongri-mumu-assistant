# WJDR Agent Rules

## Bounded, stable operation
- Give commands/helpers/probes/tests an explicit <=30-second watchdog and terminate their process tree on timeout. Split longer work into independent slices. Natural rally countdowns are monitored state, not blocking commands.
- Report meaningful progress within30s during unfinished work. Aim for <=200ms local recognition/intentional delays; never invent that bound for ADB transport or game response.
- Current task priority is reliable Beast automation; performance optimizations must preserve ownership, no-duplicate-input and account-isolation checks.

## Project
- wjdr_mumu_assistant_qt.py is the desktop entry; wjdr_backend.py owns ADB, persistence and core recognition; wjdr_beast_hunt.py owns compact Beast semantics.
- Use per-account stable identity (MuMu manager index + Android ID) for profiles, locks and ledgers. Explicitly bind the current ADB; never migrate an in-flight job.
- The current WJDR skill and references/beast-rally.md are the compact workflow authority. Obsolete expanded-panel/always-visible0/6/first-formation instructions are historical, not fallbacks.
- No purchases, diamonds, speed-ups, Auto Join, unrelated battles or arbitrary recovery clicks. No repeated input after an unknown acknowledgement.
- User confirms empty compact list disappears when all armies return. Two fresh known-world, collapsed-panel, no-list proofs may establish hidden idle; present-but-unreadable list is unknown. Never invent six slots.
- Require exact named 打野; otherwise promptly tell the user to save that formation in-game. Never select another team by default.
- Keep only tight de-identified milestone evidence. Saved images never replace fresh runtime frames. Curated assets require focused positive/negative tests.
- Normalize Android game-content coordinates; do not mix Windows DPI/window pixels into ADB taps.

## Test and release
- Focused gate: python C:/Users/TSUKI/.codex/skills/wjdr-mumu-daily-automation/scripts/verify_beast_rally_candidate.py --repo C:/Users/TSUKI/Documents/WJDR, with a30s outer watchdog.
- Before presenting a revision as ready, live-test the changed gate on the actual selected ADB. Beast lifecycle changes require a continuous idle→owned rally→march/return→idle→safe next cycle trace.
- After the relevant live gate, show the current frontend, verify its window, and commit/push scoped source to GitHub main. Preserve active workers. Source preview is not portable release acceptance.
- Fast preview: scripts/demo_frontend.ps1 -Device <current-adb> (15s startup deadline; no automatic game task). Do not reopen an old package to test current source.
- Primary release is no-install WJDRMuMuAssistant_vX.Y.Z_Portable.exe. Test actual one-click boot, source-current runtime/assets and absence of developer-path dependencies. Do not publish Setup.exe as primary.
- Other-account/machine support is pending until a compatibility matrix is verified. Do not generalize one successful account into universal support.

## Current status
- Source candidate5.63.0;78 focused tests. Milestone179 proved two completed cycles and third owned rally in continuous PID54760 on instance2,19:28–19:33, including two ordinary inventory stamina uses. QA cycle limit is consumed once at construction, never reused by user starts/child windows. Preserve the running worker. Allied-overlap live acceptance and new portable boot remain pending; milestone178 proved green marching on instance0.
- The root working folder is not the public Git checkout. Scoped source is published via release_publish_v5_63/main; exclude account ledgers, raw screenshots, runtime caches and build residue.
- User-deleted cron must not be recreated without a new request. No cleanup of historical build/worktree directories without a separately reviewed exact target list.
