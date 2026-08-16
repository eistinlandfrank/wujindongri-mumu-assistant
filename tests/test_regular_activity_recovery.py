from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageEnhance

from wjdr_backend import match_daily_regular_activity_back


ROOT = Path(__file__).resolve().parents[1]
SOURCE = (ROOT / "wjdr_mumu_assistant_qt.py").read_text(encoding="utf-8")


def _synthetic_regular_activity_frame() -> Image.Image:
    frame = Image.new("RGB", (1440, 2560), (11, 45, 76))
    back = Image.open(ROOT / "assets" / "daily_regular_activity_back_live.png").convert(
        "RGB"
    )
    title = Image.open(
        ROOT / "assets" / "daily_regular_activity_title_live.png"
    ).convert("RGB")
    frame.paste(back, (10, 10))
    frame.paste(title, (130, 20))
    return frame


def test_regular_activity_requires_back_and_complete_title_with_raw_colour() -> None:
    frame = _synthetic_regular_activity_frame()
    point, score = match_daily_regular_activity_back(frame, 0.92)
    assert point == (70, 70)
    assert score >= 0.999

    title_missing = frame.copy()
    title_missing.paste((11, 45, 76), (130, 20, 460, 125))
    assert match_daily_regular_activity_back(title_missing, 0.92)[0] is None

    dimmed = ImageEnhance.Brightness(frame).enhance(0.94)
    assert match_daily_regular_activity_back(dimmed, 0.92)[0] is None


def test_gather_return_handles_only_the_exact_regular_activity_back() -> None:
    start = SOURCE.index("def reopen_daily_tasks_from_gather_world")
    end = SOURCE.index("def yield_gather_search_timeout", start)
    route = SOURCE[start:end]
    activity = route[route.index("match_daily_regular_activity_back") :]

    assert "detect_daily_task_state(image, threshold)" in route
    assert route.index('page.state is getattr(DailyTaskState, "BLOCKED", None)') < route.index(
        "match_daily_regular_activity_back"
    )
    assert "regular_back_streak >= 2" in activity
    assert activity.index("regular_back_streak >= 2") < activity.index(
        "target.tap(*regular_back)"
    )
    assert "regular_back_sent = True" in activity
    assert "未点击钻石刷新、加号、标签或活动卡" in activity
    assert 'target.shell(["input", "keyevent", "4"])' not in activity


def test_main_loop_can_resume_a_saved_exact_regular_activity_page() -> None:
    marker = "regular_activity_back_point, _regular_activity_score"
    start = SOURCE.index(marker)
    end = SOURCE.index("active_march_visible = (", start)
    recovery = SOURCE[start:end]

    assert "regular_activity_back_streak += 1" in recovery
    assert "regular_activity_back_streak < 2" in recovery
    assert "target.tap(*regular_activity_back_point)" in recovery
    assert "regular_activity_back_sent = True" in recovery
    assert "未点击钻石刷新、加号、标签或活动卡" in recovery
    assert 'target.shell(["input", "keyevent", "4"])' not in recovery
