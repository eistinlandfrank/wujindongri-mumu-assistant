from __future__ import annotations

from pathlib import Path

from PIL import Image

import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from wjdr_backend import match_daily_welcome_back_confirm  # noqa: E402


def test_reviewed_welcome_back_sheet_requires_both_exact_anchors() -> None:
    frame = Image.open(
        ROOT
        / "evidence"
        / "milestone-62-resume-later-tasks-v527"
        / "16416-full-private.png"
    ).convert("RGB")
    assert match_daily_welcome_back_confirm(frame, 0.90) == (720, 2050)

    missing_confirm = frame.copy()
    missing_confirm.paste((30, 30, 30), (350, 1850, 1100, 2200))
    assert match_daily_welcome_back_confirm(missing_confirm, 0.90) is None

    missing_title = frame.copy()
    missing_title.paste((30, 30, 30), (450, 400, 1000, 650))
    assert match_daily_welcome_back_confirm(missing_title, 0.90) is None


def test_controller_double_confirms_and_taps_only_once_before_daily_scan() -> None:
    source = (ROOT / "wjdr_mumu_assistant_qt.py").read_text(encoding="utf-8")
    guard = source.index("welcome_back_point = match_daily_welcome_back_confirm")
    scan = source.index("page = detect_daily_task_state(image, threshold)", guard)
    block = source[guard:scan]

    assert "welcome_back_streak < 2" in block
    assert "welcome_back_confirm_sent" in block
    assert "target.tap(*welcome_back_point)" in block
    assert block.count("target.tap(*welcome_back_point)") == 1
    assert "等待页面自然离开，不重复输入" in block
    assert "立即恢复后续每日任务" in block


def main() -> None:
    test_reviewed_welcome_back_sheet_requires_both_exact_anchors()
    test_controller_double_confirms_and_taps_only_once_before_daily_scan()
    print("welcome-back exact recovery: PASS")


if __name__ == "__main__":
    main()
