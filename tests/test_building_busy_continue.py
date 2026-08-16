from __future__ import annotations

from pathlib import Path

from PIL import Image

from wjdr_backend import (
    match_daily_building_active_upgrading,
    match_daily_city_entry,
    match_daily_normal_build_action,
)


ROOT = Path(__file__).resolve().parents[1]
SOURCE = (ROOT / "wjdr_mumu_assistant_qt.py").read_text(encoding="utf-8")


def test_city_without_normal_build_is_a_passive_busy_building_state() -> None:
    frame = Image.new("RGB", (1440, 2560), (16, 24, 32))
    clipboard = Image.open(ROOT / "assets" / "daily_city_entry.png").convert("RGB")
    frame.paste(clipboard, (15, 1980))

    assert match_daily_city_entry(frame, 0.94)[0] == (74, 2110)
    assert match_daily_normal_build_action(frame, 0.94)[0] is None


def test_busy_building_yields_only_that_mission_and_continues() -> None:
    start = SOURCE.index("def run_daily_building_upgrade_plan")
    end = SOURCE.index("def run_alliance_help_cycle", start)
    route = SOURCE[start:end]

    assert "deadline = started_wait + 6.0" in route
    assert route.index("match_daily_normal_build_action") < route.index(
        "match_daily_city_entry"
    )
    assert "city_streak >= 2" in route
    assert "building_upgrade_unavailable = True" in route
    assert "building_upgrade_retry_at = (" in route
    assert "DAILY_RETRY_LOCK_MAX_SECONDS" in route
    assert "target.tap(*city_point)" in route
    assert "未点击立即完成、钻石或加速" in route
    assert route.index("match_daily_building_active_upgrading") < route.index(
        'target.shell(["input", "keyevent", "4"])'
    )
    assert "active_detail_streak >= 2" in route
    assert "active_detail_back_sent" in route

    mission_start = SOURCE.index("building_mission = (")
    mission_end = SOURCE.index("hero_mission = (", mission_start)
    mission = SOURCE[mission_start:mission_end]
    assert "if building_upgrade_unavailable" in mission
    assert "time.monotonic() >= building_upgrade_retry_at" in SOURCE
    assert "if not building_upgrade_unavailable:" in mission
    assert "建筑升级任务二次复核未通过：不输入并快速重扫" in mission
    mismatch_start = mission.index("if not (")
    mismatch_end = mission.index("target.tap(*verified_building.go_point)", mismatch_start)
    mismatch = mission[mismatch_start:mismatch_end]
    assert "restart_daily_list_scan()" in mismatch
    assert "last_state = None" in mismatch
    assert "continue" in mismatch
    assert "break" not in mismatch


def test_active_upgrade_detail_has_one_tight_observation_anchor() -> None:
    frame = Image.new("RGB", (1440, 2560), (16, 24, 32))
    label = Image.open(
        ROOT / "assets" / "daily_building_active_upgrading_label.png"
    ).convert("RGB")
    frame.paste(label, (65, 1770))

    point, score = match_daily_building_active_upgrading(frame, 0.94)
    assert point == (212, 1830)
    assert score >= 0.999

    blank = Image.new("RGB", (1440, 2560), (16, 24, 32))
    assert match_daily_building_active_upgrading(blank, 0.94)[0] is None
