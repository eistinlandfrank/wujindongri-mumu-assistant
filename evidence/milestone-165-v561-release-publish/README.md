# Milestone 165 — v5.61 complete package and GitHub publication

Date: 2026-08-16

## Package acceptance

- Source and Windows version resource: `5.61.0` / `5.61.0.0`.
- Portable package: `release_v5_61/dist/WJDRMuMuAssistant`.
- Single-file installer: `release_v5_61/WJDRMuMuAssistant_v5.61.0_Setup.exe`.
- Portable EXE SHA256: `0F478B80167F4F4AC0F5411394E5064AAACE0B9BC98FFD1473406C32FDD66A09`.
- Installer SHA256: `64BB007590A83623444F6C5821F8AB61450F960BC77985E94446B9A3627E8C97`.
- Both the PyInstaller rebuild and Inno Setup compile completed inside independent 30-second hard boundaries.
- The package contains 234 runtime assets in `_internal/assets` and the same 234 diagnostic sidecar assets; every file matched the source SHA256.
- The packaged executable passed a no-input `--help` smoke check with exit code 0.

## Focused source checks

- Beast candidate verifier: 29 focused tests passed.
- Arena five-free route: passed.
- Post-325 claim-only drain: passed.
- Daily retry-lock ceiling: passed.
- `py_compile` for both runtime entry modules: passed.
- The Beast dispatch-cost regression was migrated from historical evidence retention to the repository-owned account-free fixture `tests/fixtures/beast_rally_dispatch_cost_20_live.png`; a clean remote clone now remains self-contained.

No ADB or game input was used during packaging. The GitHub publication contains current source, runtime assets, focused tests and release documentation; legacy release directories, logs, account audits and temporary screenshots are excluded.
