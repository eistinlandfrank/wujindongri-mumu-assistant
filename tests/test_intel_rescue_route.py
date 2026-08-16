from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageEnhance

from wjdr_backend import (
    match_daily_intel_map_page,
    match_daily_intel_mission,
    match_daily_intel_rescue_active,
    match_daily_intel_rescue_pin,
    match_daily_intel_rescue_preview,
    match_daily_intel_rescue_target,
    match_daily_intel_station_bubble,
)


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "evidence" / "milestone-93-intel-single-route"


def frame(name: str) -> Image.Image:
    return Image.open(EVIDENCE / name).convert("RGB")


def test_first_and_progressive_intel_daily_cards_pair_with_their_own_go() -> None:
    first = match_daily_intel_mission(frame("intel-card-second-private.png"), 0.91)
    progressive = match_daily_intel_mission(frame("intel-five-card-private.png"), 0.91)
    assert first and first.go_point == (1193, 1154)
    assert progressive and progressive.go_point == (1190, 1160)


def test_exact_nonbattle_rescue_route_controls() -> None:
    assert match_daily_intel_station_bubble(frame("landing-800ms-private.png"), 0.91)[0] == (
        720,
        1077,
    )
    map_frame = frame("intel-map-second-private.png")
    assert match_daily_intel_map_page(map_frame, 0.91)[0]
    tent, tent_score = match_daily_intel_rescue_pin(map_frame, 0.91)
    assert tent == (667, 755) and tent_score >= 0.98
    assert match_daily_intel_rescue_preview(frame("tent-real-800ms-private.png"), 0.91)[0] == (
        720,
        1762,
    )
    assert match_daily_intel_rescue_target(frame("rescue-view-850ms-private.png"), 0.91)[0] == (
        720,
        1257,
    )
    assert match_daily_intel_rescue_active(frame("rescue-result-1s-private.png"), 0.91)[0]


def test_green_wolf_never_substitutes_for_removed_tent_and_dimmed_actions_fail() -> None:
    map_without_tent = frame("intel-map-second-private.png")
    ImageDraw.Draw(map_without_tent).rectangle((560, 620, 780, 880), fill=(190, 210, 225))
    assert match_daily_intel_rescue_pin(map_without_tent, 0.91)[0] is None

    preview = frame("tent-real-800ms-private.png")
    assert match_daily_intel_rescue_preview(ImageEnhance.Brightness(preview).enhance(0.94), 0.91)[0] is None
    target = frame("rescue-view-850ms-private.png")
    assert match_daily_intel_rescue_target(ImageEnhance.Brightness(target).enhance(0.94), 0.91)[0] is None
