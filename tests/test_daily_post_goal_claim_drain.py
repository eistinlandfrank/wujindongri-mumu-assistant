"""The 325 target stops new work, but must not discard earned rewards."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = (ROOT / "wjdr_mumu_assistant_qt.py").read_text(encoding="utf-8")


def main() -> None:
    target_gate = SOURCE[
        SOURCE.index("activity = estimate_daily_activity_progress(image)") :
        SOURCE.index("open_chest_pending = False", SOURCE.index("activity = estimate_daily_activity_progress(image)"))
    ]
    assert "if activity_goal_streak and not activity_goal_confirmed:" in target_gate
    assert target_gate.index("if activity_goal_streak and not activity_goal_confirmed:") < target_gate.index(
        "elif not alliance_help_checked:"
    )
    assert "允许最终活跃度超过 325" in target_gate
    assert "立即停止，未再点击宝箱、领取" not in SOURCE

    claim_only = SOURCE[
        SOURCE.index("# Claim-only terminal scan.") :
        SOURCE.index("warehouse_mission = (", SOURCE.index("# Claim-only terminal scan."))
    ]
    for required in (
        "match_daily_task_completed_check",
        "daily_task_list_viewport_mean_change",
        "DAILY_TASK_LIST_BOUNDARY_CONFIRMATIONS",
        "DAILY_TASK_LIST_MAX_SCAN_SWIPES",
        "最终活跃度约",
        "未点击任何前往或未完成任务",
    ):
        assert required in claim_only
    for forbidden in (
        "match_daily_warehouse_supply_mission",
        "match_daily_intel_mission",
        "match_daily_arena_mission",
        "match_daily_alliance_donate_mission",
        "match_daily_training_missions",
        "match_daily_gather_missions",
        "run_warehouse_supply_plan",
        "run_intel_rescue_plan",
        "run_arena_plan",
        "run_gather_plan",
    ):
        assert forbidden not in claim_only

    assert "达到325后仍允许排空当前已完成奖励" in SOURCE
    print("post-goal claim drain: PASS (325 minimum; claims only; no new work)")


if __name__ == "__main__":
    main()
