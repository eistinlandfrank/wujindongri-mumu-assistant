from pathlib import Path

from PIL import Image

import wjdr_backend as backend


ROOT = Path(__file__).resolve().parents[1]


def _chapter_sheet(*, include_header: bool = True, include_tab: bool = True) -> Image.Image:
    frame = Image.new("RGB", (1440, 2560), (18, 31, 47))
    if include_header:
        header = Image.open(
            ROOT / "assets" / "daily_task_chapter_header_current_live.png"
        ).convert("RGB")
        frame.paste(header, (500, 180))
    if include_tab:
        tab = Image.open(ROOT / "assets" / "daily_task_unselected_tab.png").convert("RGB")
        frame.paste(tab, (960, 2180))
    return frame


def test_current_chapter_title_and_daily_tab_authorise_exact_tab_switch() -> None:
    match = backend.detect_daily_task_state(_chapter_sheet(), 0.89)

    assert match.state is backend.DailyTaskState.DAILY_TAB_READY
    assert match.point == (1200, 2345)
    assert match.score >= 0.99


def test_unselected_daily_tab_alone_never_authorises_a_switch() -> None:
    match = backend.detect_daily_task_state(
        _chapter_sheet(include_header=False),
        0.89,
    )

    assert match.state is backend.DailyTaskState.UNKNOWN


def test_chapter_title_alone_never_authorises_a_switch() -> None:
    match = backend.detect_daily_task_state(
        _chapter_sheet(include_tab=False),
        0.89,
    )

    assert match.state is backend.DailyTaskState.UNKNOWN
