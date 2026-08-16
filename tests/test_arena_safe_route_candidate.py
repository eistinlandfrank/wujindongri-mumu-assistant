"""Focused offline checks for the executable free Arena route."""

import sys
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from wjdr_backend import (  # noqa: E402
    match_arena_home,
    match_arena_opponent_list,
    match_arena_result_exit,
    match_arena_setup,
    match_daily_arena_claim,
    match_daily_arena_mission,
)


def synthetic_arena_card(*, include_title: bool = True, include_go: bool = True,
                         adjacent_go: bool = False) -> Image.Image:
    frame = Image.new("RGB", (865, 1536), (187, 211, 237))
    if include_title:
        title = Image.open(ROOT / "assets" / "user_doc_arena_mission_title.png").convert("RGB")
        frame.paste(title, (24, 600))
    if include_go:
        go = Image.open(ROOT / "assets" / "user_doc_daily_mission_go.png").convert("RGB")
        frame.paste(go, (622, 630 if not adjacent_go else 850))
    return frame


def main() -> None:
    candidate = match_daily_arena_mission(synthetic_arena_card(), 0.90)
    assert candidate is not None and candidate.target_count == 1
    assert candidate.go_point[0] > candidate.task_point[0]
    assert candidate.score >= 0.99
    assert match_daily_arena_mission(synthetic_arena_card(include_title=False), 0.90) is None
    assert match_daily_arena_mission(synthetic_arena_card(include_go=False), 0.90) is None
    assert match_daily_arena_mission(synthetic_arena_card(adjacent_go=True), 0.90) is None

    # The 5-times row remains recognisable for diagnostics, but controller
    # authority below is intentionally restricted to target_count == 1.
    five_candidate = match_daily_arena_mission(
        Image.open(ROOT / "tests" / "fixtures" / "arena_daily_five_sanitized.png"),
        0.90,
    )
    assert five_candidate is not None and five_candidate.target_count == 5

    fixtures = ROOT / "tests" / "fixtures"
    home = match_arena_home(Image.open(fixtures / "arena_home_sanitized.png"), 0.90)
    assert home is not None and home.remaining == 5 and home.challenge_point

    opponents = match_arena_opponent_list(
        Image.open(fixtures / "arena_list_sanitized.png"), 0.90
    )
    assert opponents is not None
    assert opponents.my_power == 14_688_162 and opponents.remaining == 5
    assert [item.power for item in opponents.opponents] == [
        20_569_000, 30_711_000, 13_144_000, 4_595_000, 3_653_000
    ]
    assert opponents.safest() == opponents.opponents[-1]

    setup = match_arena_setup(
        Image.open(fixtures / "arena_setup_sanitized.png"), 0.90
    )
    assert setup is not None
    assert setup.my_power == 14_688_162
    assert setup.opponent_power == 3_653_034
    assert setup.selected_heroes == 5 and setup.my_power > setup.opponent_power

    # The live Arena result uses a distinct complete exit-sentence rendering.
    # Keep it Arena-only: two repository-owned, account-free sentence crops
    # must match in the fixed result lane, while a blank/partial frame stays
    # closed.  The returned input is the reviewed neutral side point, not the
    # video control beside the text.
    for crop_path in (
        ROOT / "assets" / "daily_arena_result_exit_text_live.png",
        fixtures / "arena_result_exit_text_second_live.png",
    ):
        result_frame = Image.new("RGB", (1440, 2560), (20, 20, 24))
        result_frame.paste(Image.open(crop_path).convert("RGB"), (470, 2280))
        exit_point, exit_score = match_arena_result_exit(result_frame, 0.90)
        assert exit_point == (120, 2200) and exit_score >= 0.99
    assert match_arena_result_exit(Image.new("RGB", (1440, 2560)), 0.90)[0] is None
    partial = Image.new("RGB", (1440, 2560), (20, 20, 24))
    full_exit = Image.open(
        ROOT / "assets" / "daily_arena_result_exit_text_live.png"
    ).convert("RGB")
    partial.paste(full_exit.crop((0, 0, full_exit.width // 2, full_exit.height)), (470, 2280))
    assert match_arena_result_exit(partial, 0.90)[0] is None

    claim_one = match_daily_arena_claim(
        Image.open(fixtures / "arena_claim_one_sanitized.png"), 0.90
    )
    claim_five = match_daily_arena_claim(
        Image.open(fixtures / "arena_claim_five_sanitized.png"), 0.90
    )
    assert claim_one is not None and claim_one.target_count == 1
    assert claim_five is not None and claim_five.target_count == 5

    controller = (ROOT / "wjdr_mumu_assistant_qt.py").read_text(encoding="utf-8")
    plan = controller[
        controller.index("def run_arena_plan") : controller.index("def run_warehouse_supply_plan")
    ]
    for required in (
        "match_arena_home",
        "match_arena_opponent_list",
        "match_arena_result_exit",
        ".safest()",
        "match_arena_setup",
        "selected_heroes != 5",
        "match_daily_tap_anywhere_exit_text",
        "after.remaining != before_remaining - 1",
        "arena_candidate.target_count == 1",
        "DAILY_RETRY_LOCK_MAX_SECONDS",
    ):
        assert required in controller
    assert "免费刷新" not in plan
    assert "免费次数未恰好减一" in plan
    assert "免费刷新" not in plan
    assert "completed >= 1" not in plan
    assert "if list_state.remaining == 0" in plan
    assert "match_daily_arena_claim" in controller
    assert "30.0" in plan and "maximum=0.25" in plan
    assert "达到325后仍允许排空当前已完成奖励" in controller
    print("arena safe route: PASS (one Go, drain 5 free, claim 1+5)")


if __name__ == "__main__":
    main()
