"""Shield must yield an already-running natural queue before slider input."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_shield_checks_active_queue_before_quantity_slider() -> None:
    source = (ROOT / "wjdr_mumu_assistant_qt.py").read_text(encoding="utf-8")
    start = source.index("def run_shield_training_plan")
    end = source.index("def run_auxiliary_training_plan", start)
    route = source[start:end]
    assert "盾兵营已有训练队列" in route
    assert route.index("match_daily_training_active") < route.index(
        'set_daily_training_quantity_to_max("盾兵")'
    )
    active_branch = route[route.index("if active_stage:") :]
    assert "defer_active_training_and_reopen_daily" in active_branch


if __name__ == "__main__":
    test_shield_checks_active_queue_before_quantity_slider()
    print("shield existing queue yield: PASS")
