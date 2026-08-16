"""Regression for the tutorial-covered Archer Camp training entry."""

from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from wjdr_backend import (  # noqa: E402
    DAILY_TRAINING_MAX_DECREMENTS,
    DailyMissionKind,
    daily_training_count_is_ten,
    daily_training_input_focus_is_proven,
    daily_training_minus_point,
    daily_training_quantity_is_maxed,
    daily_training_quantity_field_point,
    daily_training_quantity_slider_points,
    daily_training_remaining_time_crop,
    match_daily_training_archer_tutorial_entry,
    match_daily_training_entry,
    match_daily_training_active,
    match_daily_training_collect_tutorial,
    match_daily_training_normal_button,
    match_daily_training_missions,
    match_daily_training_unlock_continue,
)


def main() -> None:
    archer = Image.open(ROOT / "evidence" / "milestone-05-training-route" / "archer-after-go.png")
    hand_covered_archer = Image.open(
        ROOT / "evidence" / "milestone-06-live-run" / "v428-gather-claim-80.png"
    )
    city = Image.open(ROOT / "evidence" / "milestone-04-live-feasibility" / "city-before-profile.png")
    point, score = match_daily_training_entry(archer, 0.90)
    assert point == (960, 1720), (point, score)
    point, score = match_daily_training_entry(hand_covered_archer, 0.90)
    assert point == (960, 1720), (point, score)
    assert match_daily_training_entry(city, 0.90)[0] is None
    for name in (
        "01-safe-stop-private.png",
        "26-archer-camp-tutorial-private.png",
        "27-archer-camp-tutorial-private.png",
    ):
        archer_tutorial = Image.open(
            ROOT / "evidence" / "milestone-16-archer-entry-v485" / name
        )
        point, score = match_daily_training_archer_tutorial_entry(archer_tutorial, 0.90)
        assert point == (720, 1130), (name, point, score)
        assert score >= 0.65, (name, score)
    assert match_daily_training_archer_tutorial_entry(archer, 0.90)[0] is None
    assert match_daily_training_archer_tutorial_entry(city, 0.90)[0] is None
    false_tutorial = Image.open(
        ROOT / "evidence" / "milestone-06-live-run" / "v446-transition-unmatched.png"
    )
    assert match_daily_training_archer_tutorial_entry(false_tutorial, 0.90)[0] is None
    thirty_unit_page = Image.open(
        ROOT / "evidence" / "milestone-16-archer-entry-v485" / "28-post-v486-passive-private.png"
    )
    thirty_unit_missions = match_daily_training_missions(thirty_unit_page, 0.90)
    assert [(item.kind, item.go_point) for item in thirty_unit_missions] == [
        (DailyMissionKind.TRAIN_SHIELD, (1165, 1488)),
        (DailyMissionKind.TRAIN_SPEAR, (1165, 1821)),
    ]
    current_cards = Image.new("RGB", (1440, 2560), (224, 229, 243))
    current_cards.paste(
        Image.open(
            ROOT
            / "evidence"
            / "milestone-57-training-20of30-v523"
            / "unfinished_training_cards_safe.png"
        ),
        (40, 1280),
    )
    current_matches = match_daily_training_missions(current_cards, 0.90)
    assert [(item.kind, item.go_point) for item in current_matches] == [
        (DailyMissionKind.TRAIN_SHIELD, (1165, 1488)),
        (DailyMissionKind.TRAIN_SPEAR, (1165, 1821)),
    ]
    # The Archer Go control is clipped by the tab strip in the first live
    # viewport, so it must wait for the normal next list viewport.  Recreate
    # that same-card geometry for both unfinished 10/30 and 20/30 states.
    for archer_asset in (
        "daily_mission_train_archer_30_10.png",
        "daily_mission_train_archer_30_20.png",
    ):
        archer_card = Image.new("RGB", (1440, 2560), (224, 229, 243))
        archer_card.paste(Image.open(ROOT / "assets" / archer_asset), (57, 1300))
        archer_card.paste(
            Image.open(ROOT / "assets" / "daily_mission_go_button_current.png"),
            (1000, 1405),
        )
        matches = match_daily_training_missions(archer_card, 0.90)
        assert [(item.kind, item.go_point) for item in matches] == [
            (DailyMissionKind.TRAIN_ARCHER, (1165, 1480))
        ], archer_asset
    covered_panel = Image.open(ROOT / "evidence" / "milestone-06-live-run" / "archer-training-panel-failed.png")
    point, score = match_daily_training_normal_button(covered_panel, 0.90)
    assert point == (1057, 2241), (point, score)
    shield_panel = Image.open(ROOT / "evidence" / "milestone-06-live-run" / "v433-shield-decrement-limit.png")
    short_slider_panel = Image.open(ROOT / "evidence" / "milestone-06-live-run" / "v435-shield-panel-changed.png")
    low_slider_panel = Image.open(ROOT / "evidence" / "milestone-06-live-run" / "v436-shield-low-count-stop.png")
    moving_handle_panel = Image.open(ROOT / "evidence" / "milestone-06-live-run" / "v437-shield-low-count-minus-stop.png")
    eleven_panel = Image.open(ROOT / "evidence" / "milestone-06-live-run" / "v438-shield-eleven-stop.png")
    ten_panel = Image.open(ROOT / "evidence" / "milestone-06-live-run" / "v439-shield-ten-stop.png")
    # The old fixed point (115, 2110) was below the actual blue minus button
    # in this live panel.  The recogniser must centre its one permitted input
    # on the visible control itself, and reject an unrelated city screenshot.
    assert daily_training_minus_point(shield_panel) == (114, 1954)
    assert daily_training_quantity_field_point(shield_panel) == (1040, 1954)
    max_handle, max_endpoint = daily_training_quantity_slider_points(shield_panel) or (None, None)
    assert max_handle == (758, 1955), max_handle
    assert max_endpoint == (757, 1955), max_endpoint
    assert daily_training_quantity_is_maxed(shield_panel)
    assert match_daily_training_normal_button(short_slider_panel, 0.90)[0] == (1057, 2241)
    assert daily_training_minus_point(short_slider_panel) == (113, 1954)
    short_handle, short_endpoint = daily_training_quantity_slider_points(short_slider_panel) or (None, None)
    assert short_handle == (557, 1955), short_handle
    assert short_endpoint and abs(short_endpoint[0] - 757) <= 1 and short_endpoint[1] == 1955, short_endpoint
    assert not daily_training_quantity_is_maxed(short_slider_panel)
    assert match_daily_training_normal_button(low_slider_panel, 0.90)[0] == (1057, 2241)
    assert daily_training_minus_point(low_slider_panel) == (113, 1954)
    assert match_daily_training_normal_button(moving_handle_panel, 0.90)[0] == (1057, 2241)
    assert daily_training_minus_point(moving_handle_panel) == (113, 1954)
    assert match_daily_training_normal_button(eleven_panel, 0.90)[0] == (1057, 2241)
    assert daily_training_minus_point(eleven_panel) == (113, 1954)
    assert daily_training_count_is_ten(ten_panel, 0.90)
    assert not daily_training_quantity_is_maxed(ten_panel)
    assert match_daily_training_normal_button(ten_panel, 0.90)[0] == (1057, 2241)
    active_panel = Image.open(ROOT / "evidence" / "milestone-06-live-run" / "v442-shield-normal-train-click.png")
    assert match_daily_training_active(active_panel, 0.90)[0] is not None
    assert daily_training_remaining_time_crop(active_panel, 0.90) is not None
    assert match_daily_training_active(ten_panel, 0.90)[0] is None
    assert daily_training_remaining_time_crop(ten_panel, 0.90) is None
    for screenshot_name in (
        "v443-shield-entry-unconfirmed.png",
        "v443-collect-confirm-1.png",
        "v443-collect-confirm-2.png",
        "v444-collect-tutorial-unmatched.png",
        "v446-transition-unmatched.png",
    ):
        tutorial_point, tutorial_score = match_daily_training_collect_tutorial(
            Image.open(ROOT / "evidence" / "milestone-06-live-run" / screenshot_name),
            0.90,
        )
        assert tutorial_point == (720, 1200), (
            screenshot_name,
            tutorial_point,
            tutorial_score,
        )
    assert match_daily_training_collect_tutorial(city, 0.90)[0] is None
    for size in ((1080, 1920), (720, 1280)):
        assert daily_training_count_is_ten(ten_panel.resize(size), 0.90), size
    assert match_daily_training_unlock_continue(
        Image.open(ROOT / "evidence" / "milestone-06-live-run" / "v440-shield-training-active-unconfirmed.png"),
        0.90,
    )[0] == (720, 2472)
    for size, expected in (
        ((1080, 1920), (86, 1466)),
        ((720, 1280), (57, 977)),
    ):
        point = daily_training_minus_point(shield_panel.resize(size))
        assert point and abs(point[0] - expected[0]) <= 3 and abs(point[1] - expected[1]) <= 3, (size, point)
    for size, expected in (
        ((1080, 1920), (780, 1466)),
        ((720, 1280), (520, 977)),
    ):
        point = daily_training_quantity_field_point(shield_panel.resize(size))
        assert point and abs(point[0] - expected[0]) <= 3 and abs(point[1] - expected[1]) <= 3, (size, point)
    assert daily_training_minus_point(city) is None
    assert daily_training_quantity_field_point(city) is None
    assert daily_training_quantity_slider_points(city) is None
    assert not daily_training_quantity_is_maxed(city)
    live_focus = (
        "mInputShown=true mServedInputConnection=EditableInputConnection "
        "mServedView=com.unity3d.player.UnityPlayer"
    )
    assert daily_training_input_focus_is_proven(live_focus)
    mumu_focus = live_focus.replace(
        "com.unity3d.player.UnityPlayer",
        "com.unity3d.player.Q",
    )
    assert daily_training_input_focus_is_proven(mumu_focus)
    assert not daily_training_input_focus_is_proven(live_focus.replace("mInputShown=true", "mInputShown=false"))
    assert not daily_training_input_focus_is_proven(live_focus.replace("EditableInputConnection", "RemoteInputConnection"))
    assert not daily_training_input_focus_is_proven(
        live_focus.replace("com.unity3d.player.UnityPlayer", "android.widget.EditText")
    )
    assert match_daily_training_normal_button(archer, 0.90)[0] is None
    assert match_daily_training_normal_button(city, 0.90)[0] is None
    assert DAILY_TRAINING_MAX_DECREMENTS >= 117 - 10
    print("daily tutorial-covered training entry: PASS")


if __name__ == "__main__":
    main()
