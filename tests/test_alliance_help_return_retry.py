from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = (ROOT / "wjdr_mumu_assistant_qt.py").read_text(encoding="utf-8")


def test_alliance_home_exit_is_double_confirmed_and_bounded() -> None:
    start = SOURCE.index("def run_alliance_help_cycle")
    end = SOURCE.index("def run_alliance_food_donation_plan", start)
    route = SOURCE[start:end]
    assert "home_exit_attempts = 0" in route
    assert "home_exit_streak >= 2 and home_exit_attempts < 2" in route
    assert 'target.shell(["input", "keyevent", "4"])' in route
    assert "home_exit_attempts += 1" in route
    assert "generic" in route


def test_alliance_home_retry_uses_no_coordinate_recovery() -> None:
    start = SOURCE.index("elif mutual_entry_tapped and page.point:")
    end = SOURCE.index("elif page.page is AlliancePage.CITY", start)
    branch = SOURCE[start:end]
    assert "target.tap" not in branch
    assert "home_exit_attempts < 2" in branch
