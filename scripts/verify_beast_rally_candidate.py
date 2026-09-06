from __future__ import annotations

import argparse
import py_compile
import subprocess
import sys
from pathlib import Path


REQUIRED_ASSETS = (
    "beast_rally_compact_rallying_title.png",
    "beast_rally_hunt_name.png",
    "beast_rally_world_search_dense_live.png",
    "beast_rally_world_search_round_live.png",
    "beast_rally_progress_sidebar_collapsed_round_live_1.png",
    "beast_rally_progress_sidebar_collapsed_round_live_2.png",
    "beast_rally_world_town_dense_live.png",
    "beast_rally_beast_target.png",
    "beast_rally_search_button.png",
    "beast_rally_sheet_header.png",
    "beast_rally_three_minutes_selected.png",
    "beast_rally_launch_button.png",
    "beast_rally_formation_anchor.png",
    "beast_rally_first_formation_selected.png",
    "beast_rally_dispatch_label.png",
    "beast_rally_progress_sidebar_collapsed_live.png",
    "beast_rally_progress_wilderness_selected_live.png",
    "beast_rally_progress_sidebar_expanded_live.png",
    "beast_rally_progress_queue_label_live.png",
    "beast_rally_progress_idle_live.png",
)
FOCUSED_MODULES = (
    "tests.test_beast_reservation_recovery_flow",
    "tests.test_settings_light_palette",
    "tests.test_account_settings_page_layout",
    "tests.test_mining_level_settings_dialog",
    "tests.test_beast_hunt",
    "tests.test_beast_rally_profile",
    "tests.test_beast_rally_recognition",
    "tests.test_beast_rally_expanded_capacity_baseline",
)
FORBIDDEN_FIXTURE_TEXT = (
    "appdata\\local\\temp",
    "codex-clipboard",
)


def fail(message: str) -> None:
    raise SystemExit(f"FAIL: {message}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Read-only integrity check for the WJDR Beast-rally candidate."
    )
    parser.add_argument("--repo", type=Path, required=True)
    args = parser.parse_args()
    repo = args.repo.resolve()
    if not (repo / "wjdr_backend.py").is_file():
        fail(f"not a WJDR repository: {repo}")

    missing = [name for name in REQUIRED_ASSETS if not (repo / "assets" / name).is_file()]
    if missing:
        fail("missing reviewed assets: " + ", ".join(missing))

    focused_files = (
        repo / "tests" / "test_beast_hunt.py",
        repo / "tests" / "test_beast_rally_profile.py",
        repo / "tests" / "test_beast_rally_recognition.py",
        repo / "tests" / "test_beast_rally_expanded_capacity_baseline.py",
    )
    for path in focused_files:
        text = path.read_text(encoding="utf-8").lower()
        forbidden = [value for value in FORBIDDEN_FIXTURE_TEXT if value in text]
        if forbidden:
            fail(f"temporary fixture dependency in {path.name}: {forbidden}")

    for path in (repo / "wjdr_backend.py", repo / "wjdr_mumu_assistant_qt.py", repo / "wjdr_beast_hunt.py", *focused_files):
        py_compile.compile(str(path), doraise=True)

    command = [sys.executable, "-m", "unittest", *FOCUSED_MODULES]
    result = subprocess.run(
        command,
        cwd=repo,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=25,
        check=False,
    )
    if result.returncode:
        sys.stdout.write(result.stdout)
        sys.stderr.write(result.stderr)
        fail(f"focused tests exited {result.returncode}")
    if "Ran 50 tests" not in result.stderr + result.stdout:
        fail("focused suite did not execute the expected 50 tests")

    print("PASS: candidate source/assets are self-contained; 50 focused tests passed.")
    print("STATUS: live end-to-end acceptance is still required; this is not release proof.")


if __name__ == "__main__":
    main()

