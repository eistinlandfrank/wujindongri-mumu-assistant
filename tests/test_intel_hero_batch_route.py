"""Exact crossed-swords Intel recognition and all-at-once controller regression."""

from pathlib import Path

from PIL import Image

from wjdr_backend import (
    match_daily_intel_hero_detail,
    match_daily_intel_hero_pin,
    match_daily_intel_hero_preview,
    match_daily_intel_hero_ready_battle,
    match_daily_intel_hero_setup,
    match_daily_intel_hero_victory,
    match_daily_intel_completed_check,
    match_daily_intel_wolf_pin,
    match_daily_intel_wolf_preview,
    match_daily_intel_wolf_target,
)


ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets"


def frame_with(*placements: tuple[str, tuple[int, int]]) -> Image.Image:
    frame = Image.new("RGB", (1440, 2560), (185, 202, 220))
    for name, top_left in placements:
        asset = Image.open(ASSETS / name).convert("RGB")
        frame.paste(asset, top_left)
    return frame


def test_crossed_swords_pin_requires_intel_map_header() -> None:
    positive = frame_with(
        ("daily_intel_map_header_live.png", (130, 24)),
        ("daily_intel_swords_pin_live.png", (985, 690)),
    )
    assert match_daily_intel_hero_pin(positive, 0.90)[0] == (1090, 810)
    assert match_daily_intel_hero_pin(
        frame_with(("daily_intel_swords_pin_live.png", (985, 690))), 0.90
    )[0] is None


def test_completed_check_is_claimable_only_on_the_intel_map() -> None:
    positive = frame_with(
        ("daily_intel_map_header_live.png", (130, 24)),
        ("daily_intel_completed_check_live.png", (225, 1104)),
    )
    assert match_daily_intel_completed_check(positive, 0.90)[0] == (262, 1141)
    assert match_daily_intel_completed_check(
        frame_with(("daily_intel_completed_check_live.png", (225, 1104))), 0.90
    )[0] is None


def test_current_completed_tent_and_pin_variants_are_exact_map_only() -> None:
    current = frame_with(
        ("daily_intel_map_header_live.png", (130, 24)),
        ("daily_intel_completed_tent_current_live.png", (835, 1485)),
        ("daily_intel_wolf_pin_current_live.png", (620, 600)),
        ("daily_intel_swords_pin_current_live.png", (885, 1105)),
    )
    assert match_daily_intel_completed_check(current, 0.90)[0] == (925, 1615)
    assert match_daily_intel_wolf_pin(current, 0.90)[0] == (705, 705)
    assert match_daily_intel_hero_pin(current, 0.90)[0] == (990, 1232)
    assert match_daily_intel_wolf_pin(
        frame_with(("daily_intel_wolf_pin_current_live.png", (620, 600))), 0.90
    )[0] is None


def test_current_wolf_preview_and_world_target_require_title_action_pairs() -> None:
    preview = frame_with(
        ("daily_intel_wolf_preview_title_current_live.png", (425, 650)),
        ("daily_intel_wolf_preview_go_current_live.png", (430, 1680)),
    )
    target = frame_with(
        ("daily_intel_wolf_target_title_current_live.png", (475, 765)),
        ("daily_intel_wolf_march_current_live.png", (480, 1190)),
    )
    assert match_daily_intel_wolf_preview(preview, 0.90)[0] == (722, 1777)
    assert match_daily_intel_wolf_target(target, 0.90)[0] == (720, 1262)
    assert match_daily_intel_wolf_preview(
        frame_with(("daily_intel_wolf_preview_go_current_live.png", (430, 1680))), 0.90
    )[0] is None
    assert match_daily_intel_wolf_target(
        frame_with(("daily_intel_wolf_march_current_live.png", (480, 1190))), 0.90
    )[0] is None


def test_preview_and_detail_require_same_page_title_and_exact_action() -> None:
    preview = frame_with(
        ("daily_intel_hero_preview_title_live.png", (412, 650)),
        ("daily_intel_hero_preview_go_live.png", (412, 1680)),
    )
    detail = frame_with(
        ("daily_intel_hero_detail_title_live.png", (480, 805)),
        ("daily_intel_hero_explore_live.png", (480, 1170)),
    )
    assert match_daily_intel_hero_preview(preview, 0.90)[0] == (724, 1770)
    assert match_daily_intel_hero_detail(detail, 0.90)[0] == (725, 1257)
    assert match_daily_intel_hero_preview(
        frame_with(("daily_intel_hero_preview_go_live.png", (412, 1680))), 0.90
    )[0] is None
    assert match_daily_intel_hero_detail(
        frame_with(("daily_intel_hero_explore_live.png", (480, 1170))), 0.90
    )[0] is None


def test_setup_and_victory_are_multi_anchor_gates() -> None:
    setup = frame_with(
        ("daily_intel_hero_setup_header_live.png", (125, 10)),
        ("daily_intel_hero_auto_deploy_live.png", (55, 2300)),
        ("daily_intel_hero_battle_live.png", (730, 2300)),
    )
    auto, battle, score = match_daily_intel_hero_setup(setup, 0.90)
    assert auto == (380, 2392) and battle == (1055, 2392) and score >= 0.99
    assert match_daily_intel_hero_ready_battle(setup, 0.90)[0] == (1055, 2392)
    assert match_daily_intel_hero_ready_battle(
        frame_with(("daily_intel_hero_battle_live.png", (730, 2300))), 0.90
    )[0] is None

    victory = frame_with(
        ("daily_intel_hero_victory_live.png", (485, 830)),
        ("daily_intel_hero_exit_text_live.png", (420, 2180)),
    )
    assert match_daily_intel_hero_victory(victory, 0.90)[0] == (90, 1200)
    assert match_daily_intel_hero_victory(
        frame_with(("daily_intel_hero_victory_live.png", (485, 830))), 0.90
    )[0] is None


def test_controller_drains_reviewed_intel_before_reopening_daily() -> None:
    source = (ROOT / "wjdr_mumu_assistant_qt.py").read_text(encoding="utf-8")
    start = source.index("def run_intel_rescue_plan")
    end = source.index("def defer_active_training_and_reopen_daily", start)
    route = source[start:end]
    assert "batch_count >= 5" in route
    assert "return run_intel_rescue_plan(batch_count + 1)" in route
    assert "match_daily_intel_hero_pin" in route
    assert "match_daily_intel_hero_ready_battle" in route
    assert "match_daily_intel_completed_check" in route
    assert "return run_intel_rescue_plan(batch_count)" in route
    assert "diagnose_daily_abnormal_exit(frame, threshold)" in route
    assert "DailyAbnormalExitKind.REWARD_TAP_ANYWHERE" in route
    assert "target.tap(*reward_point)" in route
    assert "reward_exit_count >= 2" in route
    assert "继续确认回到地图并领取下一完成点" in route
    assert "mean_change >= 2.0" in route
    assert "未审核狼点保持零点击" in route


if __name__ == "__main__":
    test_crossed_swords_pin_requires_intel_map_header()
    test_completed_check_is_claimable_only_on_the_intel_map()
    test_current_completed_tent_and_pin_variants_are_exact_map_only()
    test_current_wolf_preview_and_world_target_require_title_action_pairs()
    test_preview_and_detail_require_same_page_title_and_exact_action()
    test_setup_and_victory_are_multi_anchor_gates()
    test_controller_drains_reviewed_intel_before_reopening_daily()
    print("intel hero batch route: PASS")
