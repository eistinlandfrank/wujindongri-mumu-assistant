from __future__ import annotations

from pathlib import Path

from PIL import Image

from wjdr_backend import match_daily_warehouse_supply_mission


ROOT = Path(__file__).resolve().parents[1]
SOURCE = (ROOT / "wjdr_mumu_assistant_qt.py").read_text(encoding="utf-8")


def test_warehouse_uses_account_scoped_three_minute_recheck() -> None:
    assert "DAILY_WAREHOUSE_SUPPLY_RETRY_SECONDS = 3 * 60" in SOURCE
    assert "DAILY_WAREHOUSE_SUPPLY_FAILURE_RETRY_SECONDS = 30" in SOURCE
    assert 'f"daily_warehouse_supply_{donation_identity}.json"' in SOURCE
    assert "def warehouse_supply_is_deferred" in SOURCE
    assert "if warehouse_supply_is_deferred()" in SOURCE
    assert "warehouse_supply_attempted" not in SOURCE


def test_warehouse_tap_persists_deadline_before_result_poll() -> None:
    start = SOURCE.index("target.tap(*verified_warehouse.go_point)")
    end = SOURCE.index("city_entry_tapped = True", start)
    route = SOURCE[start:end]
    assert route.index("defer_warehouse_supply()") < route.index(
        "run_warehouse_supply_plan()"
    )


def test_failed_warehouse_probe_uses_short_account_backoff() -> None:
    plan = SOURCE[
        SOURCE.index("def run_warehouse_supply_plan") : SOURCE.index(
            "def run_intel_rescue_plan"
        )
    ]
    assert "defer_warehouse_supply(" in plan
    assert "DAILY_WAREHOUSE_SUPPLY_FAILURE_RETRY_SECONDS" in plan


def test_current_three_claim_warehouse_card_pairs_its_own_go() -> None:
    frame = Image.new("RGB", (1440, 2560), (170, 205, 232))
    title = Image.open(
        ROOT / "assets" / "daily_warehouse_mission_three_current_live.png"
    ).convert("RGB")
    go = Image.open(
        ROOT / "assets" / "daily_mission_go_button_current.png"
    ).convert("RGB")
    frame.paste(title, (65, 1170))
    frame.paste(go, (1025, 1330))
    match = match_daily_warehouse_supply_mission(frame, 0.94)
    assert match is not None
    assert match.go_point[0] > match.task_point[0]
    assert match.score >= 0.985

    no_go = Image.new("RGB", frame.size, (170, 205, 232))
    no_go.paste(title, (65, 1170))
    assert match_daily_warehouse_supply_mission(no_go, 0.94) is None
