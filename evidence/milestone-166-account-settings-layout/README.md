# Milestone 166 — page-local account settings layout

- Cause: the mining and Icefield Beast account buttons were added to the shared window header, outside the `QStackedWidget`, so they appeared on every product page and compressed the device controls.
- Fix: the shared header now contains only device selection, scan, and connection state. Mining configuration lives in `dailyAccountSettingsCard`; Beast level/stamina configuration lives in `beastAccountSettingsCard`.
- Account isolation is unchanged: both cards refresh from the selected device's stable identity and explicitly state that the setting applies only to the current account.
- Visual QA: `daily-page.png` and `beast-page.png` are synthetic, account-free 1440×900 offscreen renders. The suffix `…123456` is fictional.
- Regression: `python -m unittest tests.test_account_settings_page_layout tests.test_mining_level_settings_dialog` passes 6 tests; source compilation and the 29-test Beast candidate verifier pass.
- Package: v5.62.0 portable EXE reports `5.62.0.0`, contains 234 byte-matched runtime assets, and survives both `--help` and a one-second GUI boot smoke. After final documentation staging, the full installer SHA256 is `BE8D3BAA93A6ABBA43F1CF8F52D3512E834F08FE13C2DBAD730062C39E2B879A`.

No ADB or game input was used for this UI-only change.
