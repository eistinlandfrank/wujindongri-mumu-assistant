"""Auxiliary training must consume a reviewed unlock reveal in one deadline."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    source = (ROOT / "wjdr_mumu_assistant_qt.py").read_text(encoding="utf-8")
    start = source.index("def run_auxiliary_training_plan")
    end = source.index("def run_daily_building_upgrade_plan", start)
    flow = source[start:end]
    helper_start = flow.index("def wait_for_auxiliary_normal_panel")
    helper_end = flow.index("stage = wait_for_auxiliary_normal_panel()")
    helper = flow[helper_start:helper_end]

    assert "time.monotonic() + AUTOMATION_STEP_TIMEOUT_SECONDS" in helper
    assert "match_daily_training_normal_button" in helper
    assert "match_daily_training_unlock_continue" in helper
    assert "unlock_streak >= 2" in helper
    assert "unlock_continue_sent = True" in helper
    assert "target.tap(*unlock_point)" in helper
    assert "return image, normal_point" in helper
    assert "wait_for_gather_step" not in helper

    after = flow[helper_end:]
    assert "stage = wait_for_auxiliary_normal_panel()" in after
    assert "lambda image: match_daily_training_normal_button" not in after


if __name__ == "__main__":
    main()
    print("auxiliary training unlock-continuation checks: PASS")
