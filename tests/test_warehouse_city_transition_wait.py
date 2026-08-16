from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = (ROOT / "wjdr_mumu_assistant_qt.py").read_text(encoding="utf-8")


def test_warehouse_city_is_passive_transition_not_immediate_failure() -> None:
    plan = SOURCE[
        SOURCE.index("def run_warehouse_supply_plan") : SOURCE.index(
            "def run_intel_rescue_plan"
        )
    ]
    city_branch = plan[
        plan.index("if city_streak >= 2 and city_point:") : plan.index(
            "if result_streak >= 2"
        )
    ]
    assert "target.tap(*city_point)" not in city_branch
    assert "target.tap(*prior_city)" not in city_branch
    assert "target.tap(*supply_bubble)" in city_branch
    assert "继续每0.25秒动态识图" in city_branch


def test_warehouse_city_recovery_uses_bounded_retry_without_tight_loop() -> None:
    plan = SOURCE[
        SOURCE.index("def run_warehouse_supply_plan") : SOURCE.index(
            "def run_intel_rescue_plan"
        )
    ]
    deadline_recovery = plan[
        plan.index("else:\n                    if (") : plan.index(
            "# The normal result overlays"
        )
    ]
    assert "city_streak >= 2" in deadline_recovery
    assert "defer_warehouse_supply(" in deadline_recovery
    assert "DAILY_WAREHOUSE_SUPPLY_FAILURE_RETRY_SECONDS" in deadline_recovery
    assert "target.tap(*prior_city)" in deadline_recovery
    assert "仓库补给关联窗口结束" in deadline_recovery


def test_warehouse_bubble_gets_own_window_and_keeps_three_minute_boundary() -> None:
    plan = SOURCE[
        SOURCE.index("def run_warehouse_supply_plan") : SOURCE.index(
            "def run_intel_rescue_plan"
        )
    ]
    bubble_click = plan[
        plan.index("target.tap(*supply_bubble)") : plan.index(
            "if result_streak >= 2"
        )
    ]
    assert "post_bubble_deadline" in bubble_click
    assert "bounded_step_timeout(8.0)" in bubble_click
    assert "deadline = max(" in bubble_click

    deadline_recovery = plan[
        plan.index("else:\n                    if (") : plan.index(
            "# The normal result overlays"
        )
    ]
    bubble_success = deadline_recovery[
        deadline_recovery.index("if supply_bubble_tapped:") : deadline_recovery.index(
            "target.tap(*prior_city)"
        )
    ]
    assert "保留三分钟复查期限" in bubble_success
    before_else, after_else = bubble_success.split("else:", 1)
    assert "defer_warehouse_supply(" not in before_else
    assert "DAILY_WAREHOUSE_SUPPLY_FAILURE_RETRY_SECONDS" in after_else
