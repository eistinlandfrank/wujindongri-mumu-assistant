"""The auxiliary-camp transition must not stack two recognition windows."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    source = (ROOT / "wjdr_mumu_assistant_qt.py").read_text(encoding="utf-8")
    start = source.index("def run_auxiliary_training_plan")
    end = source.index("def run_daily_building_upgrade_plan", start)
    flow = source[start:end]
    helper_start = flow.index("def wait_for_auxiliary_transition")
    helper_end = flow.index("transition = wait_for_auxiliary_transition()")
    helper = flow[helper_start:helper_end]
    assert "time.monotonic() + AUTOMATION_STEP_TIMEOUT_SECONDS" in helper
    assert "match_daily_training_entry" in helper
    assert "tutorial_probe" in helper
    assert 'return "normal_entry"' in helper
    assert 'return "completed_tutorial"' in helper
    assert "wait_for_gather_step" not in helper

    transition = flow[
        flow.index("transition = wait_for_auxiliary_transition()") : flow.index(
            "def wait_for_auxiliary_normal_panel"
        )
    ]
    assert "未在30秒统一窗口确认" in transition
    assert "tutorial_stage = wait_for_gather_step" not in transition
    assert "finish_training_camp_double_enter" in transition


if __name__ == "__main__":
    main()
    print("training shared transition deadline checks: PASS")
