"""Focused regression for double-enter camps and max-filled ordinary queues."""

from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from wjdr_backend import (  # noqa: E402
    DailyMissionKind,
    daily_training_quantity_is_maxed,
    daily_training_quantity_slider_points,
    read_daily_training_progress,
)


def main() -> None:
    evidence = ROOT / "evidence" / "milestone-06-live-run"
    full = Image.open(evidence / "v433-shield-decrement-limit.png")
    partial = Image.open(evidence / "v435-shield-panel-changed.png")
    ten = Image.open(evidence / "v439-shield-ten-stop.png")

    full_points = daily_training_quantity_slider_points(full)
    partial_points = daily_training_quantity_slider_points(partial)
    assert full_points is not None and partial_points is not None
    assert full_points[0][0] > partial_points[0][0]
    assert abs(full_points[1][0] - partial_points[1][0]) <= 2
    assert daily_training_quantity_is_maxed(full)
    assert not daily_training_quantity_is_maxed(partial)
    assert not daily_training_quantity_is_maxed(ten)

    for size in ((1080, 1920), (720, 1280)):
        resized = full.resize(size)
        points = daily_training_quantity_slider_points(resized)
        assert points is not None, size
        assert daily_training_quantity_is_maxed(resized), (size, points)

    daily = Image.open(
        ROOT
        / "evidence"
        / "milestone-74-training-double-enter-max"
        / "live-after-user-correction-full-safe.png"
    )
    assert read_daily_training_progress(daily, DailyMissionKind.TRAIN_SHIELD, 0.90) == (10, 30)
    assert read_daily_training_progress(daily, DailyMissionKind.TRAIN_SPEAR, 0.90) == (10, 30)
    assert read_daily_training_progress(daily, DailyMissionKind.TRAIN_ARCHER, 0.90) == (10, 30)

    source = (ROOT / "wjdr_mumu_assistant_qt.py").read_text(encoding="utf-8")
    helper_start = source.index("def finish_training_camp_double_enter")
    helper_end = source.index("def run_shield_training_plan", helper_start)
    helper = source[helper_start:helper_end]
    max_start = source.index("def set_daily_training_quantity_to_max")
    max_end = helper_start
    max_flow = source[max_start:max_end]
    assert helper.count("target.tap(*reviewed_camp_point)") == 1
    assert "second_camp_tapped" in helper
    assert "tutorial_streak >= 2" in helper
    assert "city_streak >= 2" in helper
    assert "time.monotonic() + bounded_step_timeout(30.0)" in helper
    assert '["input", "swipe", str(handle[0])' in max_flow
    assert "daily_training_quantity_is_maxed(image)" in max_flow
    assert 'input", "text", "10"' not in max_flow
    assert source.count("finish_training_camp_double_enter(") == 3
    assert source.count("set_daily_training_quantity_to_max(") == 3
    assert "返回每日任务复读进度" in source
    print("training double-enter and max queue: PASS")


if __name__ == "__main__":
    main()
