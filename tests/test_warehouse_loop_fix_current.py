"""Focused regression for the high-account Warehouse loop fix."""

from pathlib import Path
import sys

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from wjdr_backend import (  # noqa: E402
    DailyMissionKind,
    match_daily_warehouse_result,
    match_daily_warehouse_supply_mission,
)


def main() -> None:
    evidence = ROOT / "evidence" / "milestone-140-high-account-daily-switch"
    matches = []
    for name in (
        "warehouse-loop-fix-passive-1.png",
        "warehouse-loop-fix-passive-2.png",
    ):
        image = Image.open(evidence / name).convert("RGB")
        match = match_daily_warehouse_supply_mission(image, 0.90)
        assert match and match.kind is DailyMissionKind.WAREHOUSE_SUPPLY
        assert match.score >= 0.985
        matches.append(match)
    assert matches[0].task_point == matches[1].task_point
    assert matches[0].go_point == matches[1].go_point

    for name in ("warehouse-fix-result-0.png", "warehouse-fix-result-1.png"):
        visible, score = match_daily_warehouse_result(
            Image.open(evidence / name).convert("RGB"), 0.90
        )
        assert visible and score >= 0.985
    for name in ("warehouse-fix-post-go-0.png", "warehouse-fix-pre-go-0.png"):
        assert not match_daily_warehouse_result(
            Image.open(evidence / name).convert("RGB"), 0.90
        )[0]

    low_evidence = ROOT / "evidence" / "milestone-148-warehouse-result-low-account"
    visible, score = match_daily_warehouse_result(
        Image.open(low_evidence / "warehouse-result-account-free.png").convert("RGB"),
        0.94,
    )
    assert visible and score >= 0.93
    assert not match_daily_warehouse_result(
        Image.open(low_evidence / "warehouse-city-negative-account-free.png").convert(
            "RGB"
        ),
        0.94,
    )[0]

    controller = (ROOT / "wjdr_mumu_assistant_qt.py").read_text(encoding="utf-8")
    assert "DAILY_WAREHOUSE_SUPPLY_RETRY_SECONDS = 3 * 60" in controller
    assert "DAILY_WAREHOUSE_SUPPLY_FAILURE_RETRY_SECONDS = 30" in controller
    assert "bounded_step_timeout(8.0)" in controller
    assert "DAILY_WAREHOUSE_SUPPLY_FAILURE_RETRY_SECONDS" in controller[
        controller.index("def run_warehouse_supply_plan") : controller.index(
            "def defer_active_training_and_reopen_daily"
        )
    ]


if __name__ == "__main__":
    main()
    print("warehouse loop fix focused checks: PASS")
