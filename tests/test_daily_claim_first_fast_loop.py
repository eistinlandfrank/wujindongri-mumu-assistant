"""Claims must drain quickly before any Daily task Go route starts."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    source = (ROOT / "wjdr_mumu_assistant_qt.py").read_text(encoding="utf-8")
    actionable = source.index(
        "actionable = (DailyTaskState.CLAIM_READY, DailyTaskState.TASK_CLAIM_READY)"
    )
    daily_page = source.index(
        "if page.state in (DailyTaskState.DAILY_PAGE, DailyTaskState.DAILY_LOGIN_COMPLETED):",
        actionable,
    )
    claim_flow = source[actionable:daily_page]
    assert "pending_claim_point" in claim_flow
    assert "pending_claim_activity_before" in claim_flow
    assert "claim_point_moved" in claim_flow
    assert "activity_increased" in claim_flow
    assert "pending_claim_settle_streak >= 2" in claim_flow
    assert "立即继续排空领取，不复位列表、不进入任务前往" in claim_flow
    assert "pending_claim_deadline = time.monotonic() + 8.0" in claim_flow
    assert "pending_claim_deadline = time.monotonic() + 12.0" not in claim_flow

    first_mission = source.index("warehouse_mission = (", daily_page)
    no_claim_settlement = source[daily_page:first_mission]
    assert "已连续两帧确认领取按钮消失" in no_claim_settlement
    assert "完成后才扫描任务" in no_claim_settlement
    assert source.index("pending_claim_settle_streak >= 2", daily_page) < first_mission

    print("daily claim-first fast loop: PASS")


if __name__ == "__main__":
    main()
