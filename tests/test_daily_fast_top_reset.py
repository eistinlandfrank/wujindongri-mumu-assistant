from pathlib import Path
import sys

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from wjdr_backend import (
    DAILY_TASK_LIST_BOUNDARY_CONFIRMATIONS,
    DAILY_TASK_LIST_BOUNDARY_MAX_MEAN_CHANGE,
    DAILY_TASK_LIST_FAST_TOP_MAX_GESTURES,
    DAILY_TASK_LIST_FAST_TOP_SWIPE,
    daily_task_list_viewport_mean_change,
)


def test_fast_top_uses_one_inertial_list_only_fling_then_pixel_confirmation() -> None:
    x1, y1, x2, y2, duration = DAILY_TASK_LIST_FAST_TOP_SWIPE
    assert (x1, x2) == (900, 900)
    # The gesture must start below the fixed activity-chest band.  A live
    # y=650 start produced a false zero-movement boundary because the list did
    # not own that pixel; y>=1000 stays in the task viewport.
    assert y1 >= 1000
    assert y2 - y1 >= 1100
    assert duration <= 100
    # Account list lengths vary.  Ten possible movement gestures plus the two
    # stationary comparisons fit the global twelve-step fail-closed envelope.
    assert DAILY_TASK_LIST_FAST_TOP_MAX_GESTURES == 12
    assert DAILY_TASK_LIST_BOUNDARY_CONFIRMATIONS == 2


def test_identical_task_viewports_are_a_top_boundary_observation() -> None:
    frame = Image.new("RGB", (1440, 2560), (40, 90, 150))
    assert (
        daily_task_list_viewport_mean_change(frame, frame.copy())
        <= DAILY_TASK_LIST_BOUNDARY_MAX_MEAN_CHANGE
    )


def test_reset_fast_path_precedes_whole_page_classification() -> None:
    source = (ROOT / "wjdr_mumu_assistant_qt.py").read_text(encoding="utf-8")
    start = source.index("def _start_daily_rewards_flow")
    end = source.index("def _start_red_packet_flow", start)
    daily_flow = source[start:end]
    fast_path = daily_flow.index(
        "if daily_list_reset_pending and daily_list_reset_before_image is not None:"
    )
    classifier = daily_flow.index("page = detect_daily_task_state(image, threshold)", fast_path)
    assert fast_path < classifier
    assert "send_daily_fast_top_gesture(image)" in daily_flow[fast_path:classifier]
    settle_gate = daily_flow.index(
        "if daily_list_reset_settle_image is None:", fast_path
    )
    next_gesture = daily_flow.index(
        "if not send_daily_fast_top_gesture(image):", settle_gate
    )
    assert settle_gate < next_gesture < classifier
    assert "未叠加下一次手势" in daily_flow[settle_gate:next_gesture]
    assert "轻量像素比对" in daily_flow


def test_transient_anchor_miss_falls_back_without_input_or_worker_stop() -> None:
    source = (ROOT / "wjdr_mumu_assistant_qt.py").read_text(encoding="utf-8")
    start = source.index("if daily_list_fast_anchor_miss_streak >= 2:")
    end = source.index("continue", start) + len("continue")
    branch = source[start:end]
    assert "丢弃本次手势关联并回退到完整页面分类" in branch
    assert "daily_list_reset_before_image = None" in branch
    assert "daily_list_reset_settle_image = None" in branch
    assert "target.tap" not in branch
    assert "target.shell" not in branch
    assert "break" not in branch


if __name__ == "__main__":
    test_fast_top_uses_one_inertial_list_only_fling_then_pixel_confirmation()
    test_identical_task_viewports_are_a_top_boundary_observation()
    test_reset_fast_path_precedes_whole_page_classification()
    test_transient_anchor_miss_falls_back_without_input_or_worker_stop()
    print("daily fast top reset: PASS")
