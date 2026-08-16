from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageEnhance

from wjdr_backend import (
    DailyAbnormalExitKind,
    daily_hero_recruit_result_is_visible,
    diagnose_daily_abnormal_exit,
    match_daily_hero_recruit_summary_exit,
    match_daily_tap_anywhere_exit_text,
)


ROOT = Path(__file__).resolve().parents[1]


def test_duplicate_owned_prefix_is_a_passive_recruit_result_variant() -> None:
    frame = Image.new("RGB", (1440, 2560), (15, 78, 145))
    prefix = Image.open(
        ROOT / "assets" / "daily_hero_recruit_duplicate_owned_live.png"
    ).convert("RGB")
    frame.paste(prefix, (220, 2420))

    assert daily_hero_recruit_result_is_visible(frame, 0.90)


def test_dimmed_duplicate_lookalike_and_plain_page_do_not_match() -> None:
    frame = Image.new("RGB", (1440, 2560), (15, 78, 145))
    prefix = Image.open(
        ROOT / "assets" / "daily_hero_recruit_duplicate_owned_live.png"
    ).convert("RGB")
    frame.paste(prefix, (220, 2420))

    assert not daily_hero_recruit_result_is_visible(
        ImageEnhance.Brightness(frame).enhance(0.94), 0.90
    )
    assert not daily_hero_recruit_result_is_visible(
        Image.new("RGB", (1440, 2560), (15, 78, 145)), 0.90
    )


def test_duplicate_variant_has_no_standalone_exit_coordinate() -> None:
    source = (ROOT / "wjdr_mumu_assistant_qt.py").read_text(encoding="utf-8")
    start = source.index("def wait_for_correlated_hero_result")
    end = source.index('"免费招募后的英雄招募页"', start)
    route = source[start:end]

    assert "match_daily_hero_recruit_duplicate_result" in route
    assert "match_daily_hero_recruit_summary_exit" in route
    assert 'target.shell(["input", "keyevent", "4"])' in route
    assert "target.tap(*result_point)" in route
    assert "黄色招募、钥匙或钻石" in route


def test_legacy_summary_exact_exit_text_returns_left_side_blank() -> None:
    summary = Image.open(
        ROOT
        / "evidence"
        / "milestone-06-live-run"
        / "v472-after-one-free-hero-private.png"
    ).convert("RGB")
    point, score = match_daily_hero_recruit_summary_exit(summary, 0.90)

    assert point == (96, 1500)
    assert score >= 0.98


def test_exact_exit_text_is_actionable_without_reward_title() -> None:
    frame = Image.new("RGB", (1440, 2560), (15, 78, 145))
    phrase = Image.open(
        ROOT / "assets" / "daily_hero_recruit_exit_hint_live.png"
    ).convert("RGB")
    frame.paste(phrase, (505, 2420))

    point, score = match_daily_tap_anywhere_exit_text(frame, 0.90)
    abnormal = diagnose_daily_abnormal_exit(frame, 0.90)

    assert point == (96, 1500)
    assert score >= 0.98
    assert abnormal.kind is DailyAbnormalExitKind.REWARD_TAP_ANYWHERE
    assert abnormal.point == (96, 1500)


def test_exact_exit_text_is_found_anywhere_in_the_game_viewport() -> None:
    phrase = Image.open(
        ROOT / "assets" / "daily_tap_anywhere_exit_native_old_live.png"
    ).convert("RGB")

    for paste_at in ((20, 180), (505, 1240), (990, 2180)):
        frame = Image.new("RGB", (1440, 2560), (15, 15, 15))
        frame.paste(phrase, paste_at)

        point, score = match_daily_tap_anywhere_exit_text(frame, 0.90)

        assert point == (96, 1500)
        assert score >= 0.98


def test_current_recruit_reward_exit_text_is_an_exact_phrase_variant() -> None:
    phrase = Image.open(
        ROOT / "assets" / "daily_tap_anywhere_exit_reward_current_live.png"
    ).convert("RGB")
    frame = Image.new("RGB", (1440, 2560), (15, 15, 15))
    frame.paste(phrase, (505, 2420))

    point, score = match_daily_tap_anywhere_exit_text(frame, 0.90)
    abnormal = diagnose_daily_abnormal_exit(frame, 0.90)

    assert point == (96, 1500)
    assert score >= 0.999
    assert abnormal.kind is DailyAbnormalExitKind.REWARD_TAP_ANYWHERE
    assert abnormal.point == (96, 1500)


def test_dimmed_current_recruit_reward_exit_text_is_not_actionable() -> None:
    phrase = Image.open(
        ROOT / "assets" / "daily_tap_anywhere_exit_reward_current_live.png"
    ).convert("RGB")
    frame = Image.new("RGB", (1440, 2560), (15, 15, 15))
    frame.paste(phrase, (505, 2420))

    point, _score = match_daily_tap_anywhere_exit_text(
        ImageEnhance.Brightness(frame).enhance(0.94),
        0.90,
    )

    assert point is None


def test_dimmed_exit_text_does_not_authorise_side_tap() -> None:
    frame = Image.new("RGB", (1440, 2560), (15, 78, 145))
    phrase = Image.open(
        ROOT / "assets" / "daily_hero_recruit_exit_hint_live.png"
    ).convert("RGB")
    frame.paste(phrase, (505, 2420))

    point, _score = match_daily_tap_anywhere_exit_text(
        ImageEnhance.Brightness(frame).enhance(0.94),
        0.90,
    )

    assert point is None
