"""Safe, exact Daily-page one-key claim regression."""

import sys
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from wjdr_backend import (  # noqa: E402
    DailyTaskState,
    detect_daily_task_state,
    match_daily_growth_task_daily_tab,
    match_daily_one_key_claim_button,
)


def paste_center(canvas: Image.Image, asset_name: str, center: tuple[int, int]) -> None:
    asset = Image.open(ROOT / "assets" / asset_name).convert("RGB")
    canvas.paste(asset, (center[0] - asset.width // 2, center[1] - asset.height // 2))


def main() -> None:
    page = Image.new("RGB", (1440, 2560), (184, 207, 235))
    paste_center(page, "daily_task_header.png", (721, 248))
    # Live two-tab high-level layout, rather than the historic x=1160 tab.
    paste_center(page, "daily_task_selected_tab.png", (929, 2261))
    paste_center(page, "daily_one_key_claim_button.png", (720, 2058))

    point, score = match_daily_one_key_claim_button(page, 0.92)
    assert point == (720, 2058)
    assert score >= 0.999
    state = detect_daily_task_state(page, 0.92)
    assert state.state is DailyTaskState.TASK_CLAIM_READY
    assert state.point == (720, 2058)

    # A generic per-row 领取 button in the same lower area cannot substitute
    # for the exact 一键领取 label.
    generic = Image.new("RGB", (1440, 2560), (184, 207, 235))
    paste_center(generic, "daily_task_header.png", (721, 248))
    paste_center(generic, "daily_task_selected_tab.png", (929, 2261))
    paste_center(generic, "daily_claim_button.png", (720, 2058))
    assert match_daily_one_key_claim_button(generic, 0.92)[0] is None
    assert detect_daily_task_state(generic, 0.92).state is DailyTaskState.DAILY_PAGE

    growth = Image.new("RGB", (1440, 2560), (184, 207, 235))
    paste_center(growth, "daily_main_task_page_title.png", (720, 417))
    paste_center(
        growth,
        "daily_growth_two_tab_unselected_daily_tab.png",
        (927, 2290),
    )
    growth_tab, growth_score = match_daily_growth_task_daily_tab(growth, 0.92)
    assert growth_tab == (927, 2290)
    assert growth_score >= 0.999
    growth_state = detect_daily_task_state(growth, 0.92)
    assert growth_state.state is DailyTaskState.DAILY_TAB_READY
    assert growth_state.point == (927, 2290)

    # The same still-visible one-key control must never be clicked twice
    # while the first click is awaiting its correlated settlement.
    controller = (ROOT / "wjdr_mumu_assistant_qt.py").read_text(encoding="utf-8")
    actionable = controller.index(
        "actionable = (DailyTaskState.CLAIM_READY, DailyTaskState.TASK_CLAIM_READY)"
    )
    tap = controller.index("target.tap(*page.point)", actionable)
    guard = controller.index("if pending_claim:", actionable)
    assert guard < tap
    guarded_flow = controller[guard:tap]
    assert "pending_claim_settle_streak" in guarded_flow
    assert "continue" in guarded_flow
    assert "break" in guarded_flow
    assert "time.monotonic() + 8.0" in controller
    assert "time.monotonic() + 12.0" not in controller[actionable:tap + 1200]

    print("daily one-key claim: PASS")


if __name__ == "__main__":
    main()
