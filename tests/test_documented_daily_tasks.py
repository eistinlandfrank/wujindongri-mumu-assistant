"""Regression checks for the task images supplied in the user's Word guide."""

import sys
import time
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from wjdr_backend import (  # noqa: E402
    DailyMissionKind,
    DailyTaskState,
    daily_warehouse_result_exit_point,
    detect_daily_task_state,
    match_daily_arena_mission,
    match_daily_arena_mission_title,
    match_daily_intel_mission,
    match_daily_warehouse_result,
    match_daily_warehouse_supply_mission,
)
from wjdr_fast_vision import FastVisionEngine, builtin_template_specs  # noqa: E402


def main() -> None:
    inventory = Image.open(
        ROOT / "evidence" / "milestone-07-task-inventory" / "inventory-00-private.png"
    ).convert("RGB")
    intel = match_daily_intel_mission(inventory, 0.90)
    warehouse = match_daily_warehouse_supply_mission(inventory, 0.90)
    assert intel and intel.kind is DailyMissionKind.PROCESS_INTEL
    assert warehouse and warehouse.kind is DailyMissionKind.WAREHOUSE_SUPPLY
    assert intel.go_point[0] > intel.task_point[0]
    assert warehouse.go_point[0] > warehouse.task_point[0]
    assert warehouse.go_point[1] > intel.go_point[1]

    arena_frame = Image.open(
        ROOT / "evidence" / "milestone-08-live-day2-inventory" / "day2-scan-04-private.png"
    ).convert("RGB")
    arena_visible, arena_score = match_daily_arena_mission_title(arena_frame, 0.90)
    assert arena_visible and arena_score >= 0.95
    assert not any("arena" in kind.value for kind in DailyMissionKind)

    result = Image.open(
        ROOT / "evidence" / "milestone-18-user-docx-intake" / "media" / "image11.png"
    ).convert("RGB")
    result_visible, result_score = match_daily_warehouse_result(result, 0.90)
    assert result_visible and result_score >= 0.99
    assert not match_daily_warehouse_result(inventory, 0.90)[0]
    exit_point = daily_warehouse_result_exit_point(result)
    assert exit_point[0] < result.width * 0.10
    assert exit_point[1] < result.height * 0.16

    controller = (ROOT / "wjdr_mumu_assistant_qt.py").read_text(encoding="utf-8")
    warehouse_plan = controller[
        controller.index("def run_warehouse_supply_plan") : controller.index(
            "def defer_active_training_and_reopen_daily"
        )
    ]
    assert "self.stop_event.wait(0.25)" in warehouse_plan
    assert "daily_warehouse_result_exit_point" in warehouse_plan
    assert "随机倒计时未等待" in warehouse_plan
    assert "仓库补给结果页未出现；已双帧确认仍在每日任务页（含可领取态）" in warehouse_plan
    assert "DailyTaskState.TASK_CLAIM_READY" in warehouse_plan
    assert "仓库补给前往未跳转；已双帧确认主城并重开每日任务" in warehouse_plan
    assert warehouse_plan.index("city_streak >= 2") < warehouse_plan.index(
        "仓库补给前往后未在限时内双帧确认结果页"
    )
    warehouse_stop = ROOT / "evidence" / "milestone-39-warehouse-continue-v506"
    for name in ("warehouse_stop_1-private.png", "warehouse_stop_2-private.png"):
        live = Image.open(warehouse_stop / name)
        assert not match_daily_warehouse_result(live, 0.90)[0]
        assert detect_daily_task_state(live, 0.90).state in (
            DailyTaskState.DAILY_PAGE,
            DailyTaskState.TASK_CLAIM_READY,
        )
    assert "deadline = time.monotonic() + bounded_step_timeout(24.0)" in warehouse_plan
    fresh_daily = Image.open(
        ROOT
        / "evidence"
        / "milestone-91-warehouse-no-result-stop"
        / "warehouse-stop-redacted-full.png"
    ).convert("RGB")
    assert not match_daily_warehouse_result(fresh_daily, 0.90)[0]
    assert detect_daily_task_state(fresh_daily, 0.90).state is DailyTaskState.DAILY_PAGE
    intel_plan = controller[
        controller.index("def run_intel_rescue_plan") : controller.index(
            "def defer_active_training_and_reopen_daily"
        )
    ]
    for proof in (
        "match_daily_intel_station_bubble",
        "match_daily_intel_map_page",
        "match_daily_intel_rescue_pin",
        "match_daily_intel_rescue_preview",
        "match_daily_intel_rescue_target",
        "match_daily_intel_rescue_active",
        "daily_intel_active_countdown_crop",
    ):
        assert proof in intel_plan
    assert "绿色狼保持零点击" in intel_plan
    assert "不使用钻石或加速" in intel_plan
    arena_route = controller[
        controller.index("arena_candidate = match_daily_arena_mission") : controller.index(
            "donation_mission = ("
        )
    ]
    assert "target.tap(*verified_arena.go_point)" in arena_route
    assert "run_arena_plan" in arena_route
    assert "DAILY_RETRY_LOCK_MAX_SECONDS" in arena_route

    specs = builtin_template_specs(r"^user_doc_")
    keys = {spec.key for spec in specs}
    assert {
        "user_doc_intel_mission_title",
        "user_doc_warehouse_mission_title",
        "user_doc_arena_mission_title",
        "user_doc_daily_mission_go",
        "user_doc_intel_map_entry",
        "user_doc_intel_map_page_anchor",
        "user_doc_warehouse_result",
    } <= keys
    started = time.perf_counter()
    _frame, results, elapsed_ms = FastVisionEngine(specs).inspect(inventory, threshold=0.90)
    wall_ms = (time.perf_counter() - started) * 1000.0
    assert elapsed_ms < 1200.0 and wall_ms < 1500.0
    assert results[0].key in {
        "user_doc_intel_mission_title",
        "user_doc_warehouse_mission_title",
        "user_doc_daily_mission_go",
    }
    print(
        "documented daily tasks: PASS "
        f"({len(specs)} compact templates, engine={elapsed_ms:.1f} ms, wall={wall_ms:.1f} ms)"
    )


if __name__ == "__main__":
    main()
