"""Regression checks for safe skipping of completed Daily rows."""

import sys
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from wjdr_backend import match_daily_task_completed_check  # noqa: E402


def main() -> None:
    completed = Image.open(
        ROOT
        / "evidence"
        / "milestone-20-completed-zone-shortcut"
        / "completed-zone-20260805-171950-private.png"
    ).convert("RGB")
    point, score = match_daily_task_completed_check(completed, 0.94)
    assert point is not None and score >= 0.99
    assert completed.width * 0.72 <= point[0] <= completed.width * 0.92

    unfinished_top = Image.open(
        ROOT
        / "evidence"
        / "milestone-19-v489-live-check"
        / "daily-open-20260805-170538-private.png"
    ).convert("RGB")
    miss, miss_score = match_daily_task_completed_check(unfinished_top, 0.94)
    assert miss is None and miss_score < 0.80

    completed_at_top = Image.open(
        ROOT
        / "evidence"
        / "milestone-88-completed-check-top-loop"
        / "low-daily-top-redacted-full.png"
    ).convert("RGB")
    current_point, current_score = match_daily_task_completed_check(completed_at_top, 0.94)
    assert current_point is not None and current_score >= 0.99

    controller = (ROOT / "wjdr_mumu_assistant_qt.py").read_text(encoding="utf-8")
    shortcut = controller[
        controller.index("completed_check, completed_check_score") : controller.index(
            "if daily_list_scan_before_image is not None"
        )
    ]
    assert "daily_completed_zone_streak += 1" in shortcut
    assert "daily_completed_zone_streak >= 2" in shortcut
    assert "daily_completed_zone_wait_after_top = True" in shortcut
    assert "restart_daily_list_scan()" in shortcut
    assert "send_daily_fast_top_gesture(image)" in shortcut
    assert "target.tap" not in shortcut
    assert "已进入打勾区，立即高速回到列表顶部；不再扫描其下方" in shortcut
    assert "daily_completed_zone_wait_after_top" in controller
    assert 'idle_no_input_label = "30 秒"' in controller
    print(
        "daily completed-tail immediate top return: PASS "
        f"(historical={score:.4f}, current-top={current_score:.4f}, negative={miss_score:.4f})"
    )


if __name__ == "__main__":
    main()
