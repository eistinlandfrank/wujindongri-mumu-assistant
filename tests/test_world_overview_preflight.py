"""Regression checks for the Word-documented castle-band preflight."""

import sys
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from wjdr_backend import (  # noqa: E402
    daily_world_overview_resource_is_enabled,
    detect_world_castle_marker_tip,
    detect_world_resource_level,
    match_daily_city_wilderness_entry,
    match_daily_world_overview_entry,
    match_daily_world_overview_home_button,
    match_daily_world_overview_resource_off,
    match_daily_world_overview_search_entry,
)


M22 = ROOT / "evidence" / "milestone-22-docx-mining-review"
M23 = ROOT / "evidence" / "milestone-23-bounded-steps"


def main() -> None:
    city1 = Image.open(M23 / "worker-now-private.png").convert("RGB")
    city2 = Image.open(M23 / "worker-city-private-2.png").convert("RGB")
    event = Image.open(M22 / "resource-fresh-private-2.png").convert("RGB")
    for image in (city1, city2):
        point, score = match_daily_city_wilderness_entry(image, 0.90)
        assert point is not None and score >= 0.98
    assert match_daily_city_wilderness_entry(event, 0.90)[0] is None

    world1 = Image.open(M22 / "overview-probe-private-1.png").convert("RGB")
    world2 = Image.open(M22 / "overview-probe-private-2.png").convert("RGB")
    for image in (world1, world2):
        point, score = match_daily_world_overview_entry(image, 0.90)
        assert point is not None and score >= 0.90
    assert match_daily_world_overview_entry(city1, 0.90)[0] is None

    overview1 = Image.open(M22 / "overview-private-1.png").convert("RGB")
    overview2 = Image.open(M22 / "overview-private-2.png").convert("RGB")
    for image in (overview1, overview2):
        point, score = match_daily_world_overview_resource_off(image, 0.90)
        assert point is not None and score >= 0.99
        assert not daily_world_overview_resource_is_enabled(image, 0.90)
        assert detect_world_resource_level(image) is None
    assert match_daily_world_overview_resource_off(city1, 0.90)[0] is None

    # Unit-test the green-state gate without pretending it is live proof: copy
    # the same frame's reviewed Threat check into the Resource square. A real
    # enabled frame is still required before packaging/live use.
    synthetic_enabled = overview2.copy()
    synthetic_enabled.paste(overview2.crop((15, 230, 100, 330)), (15, 340))
    assert daily_world_overview_resource_is_enabled(synthetic_enabled, 0.90)

    enabled1 = Image.open(M22 / "low-resource-on-private-1.png").convert("RGB")
    enabled2 = Image.open(M22 / "low-resource-on-private-2.png").convert("RGB")
    for image in (enabled1, enabled2):
        assert daily_world_overview_resource_is_enabled(image, 0.90)
        assert match_daily_world_overview_resource_off(image, 0.90)[0] is None
        # These historical frames do not expose a unique green player pin in
        # the main map.  The old fixed-coordinate implementation guessed 9;
        # the Word-guided implementation must now fail closed instead.
        assert detect_world_castle_marker_tip(image) is None
        assert detect_world_resource_level(image) is None

    marker_frame = Image.open(
        ROOT / "evidence" / "milestone-75-castle-home-recovery" / "current-private.png"
    ).convert("RGB")
    # Fast-vision annotation labels cover the panel anchor in this saved
    # private frame.  Restore only the unchanged reviewed panel from an
    # enabled fixture; the live marker and every map pixel stay untouched.
    marker_frame.paste(enabled1.crop((0, 0, 400, 800)), (0, 0))
    marker_tip = detect_world_castle_marker_tip(marker_frame)
    assert marker_tip is not None
    assert abs(marker_tip[0] - 780) <= 3 and abs(marker_tip[1] - 1224) <= 3
    assert detect_world_resource_level(marker_frame) == 5

    # The green castle pin, not a fixed screen coordinate, selects the map
    # band.  Move that exact reviewed pin onto clean medium/dark terrain in
    # the same frame and require the corresponding 7/9 selectors.  The small
    # copied rectangle ends at the pin tip, so each classification still
    # samples the destination terrain rather than copied source pixels.
    pin_crop = marker_frame.crop(
        (marker_tip[0] - 60, marker_tip[1] - 120, marker_tip[0] + 60, marker_tip[1] + 5)
    )
    erase_crop = marker_frame.crop(
        (marker_tip[0] + 60, marker_tip[1] - 120, marker_tip[0] + 180, marker_tip[1] + 5)
    )
    for target_tip, expected_level in (((800, 1700), 7), ((500, 2000), 9)):
        moved = marker_frame.copy()
        moved.paste(erase_crop, (marker_tip[0] - 60, marker_tip[1] - 120))
        moved.paste(pin_crop, (target_tip[0] - 60, target_tip[1] - 120))
        assert detect_world_castle_marker_tip(moved) == target_tip
        assert detect_world_resource_level(moved) == expected_level

    # A clustered-account live frame placed the unique green pin at x=1336.
    # It is still main-map content: only the minimap above y=450 and the
    # navigation controls below y=2050 are excluded.  Do not reintroduce the
    # old x=1240 cutoff that silently discarded this valid marker.
    right_edge = marker_frame.copy()
    right_edge.paste(erase_crop, (marker_tip[0] - 60, marker_tip[1] - 120))
    right_edge_tip = (1336, 1226)
    right_edge.paste(
        pin_crop,
        (right_edge_tip[0] - 60, right_edge_tip[1] - 120),
    )
    assert detect_world_castle_marker_tip(right_edge) == right_edge_tip

    marker_gone = enabled1
    assert detect_world_castle_marker_tip(marker_gone) is None
    assert detect_world_resource_level(marker_gone) is None

    home_asset = Image.open(ROOT / "assets" / "daily_world_overview_home_button.png").convert(
        "RGB"
    )
    synthetic_home = marker_frame.copy()
    synthetic_home.paste(home_asset, (1178, 280))
    home_point, home_score = match_daily_world_overview_home_button(synthetic_home, 0.90)
    assert home_point is not None and home_score >= 0.99
    assert match_daily_world_overview_home_button(marker_frame, 0.90)[0] is None

    # The matcher returns ``(point, score)``.  The controller must unpack it;
    # passing the outer tuple to a coordinate-stability test subtracts
    # ``None - None`` on a missing point and caused the live v4.96 stop.
    controller = (ROOT / "wjdr_mumu_assistant_qt.py").read_text(encoding="utf-8")
    overview_flow = controller.split("def establish_world_resource_level()", 1)[1].split(
        "def confirm_daily_free_march_capacity", 1
    )[0]
    assert "search_point, search_score = match_daily_world_overview_search_entry(" in overview_flow
    assert "search_point = match_daily_world_overview_search_entry(" not in overview_flow
    assert "def match_reviewed_gather_search(" in controller
    assert "world_point, _world_score = match_reviewed_gather_search(image)" in controller
    assert controller.count("match_reviewed_gather_search,") >= 2
    enabled_live = Image.open(
        ROOT / "evidence" / "milestone-31-world-search-tuple-v497" / "enabled-overview-private.png"
    ).convert("RGB")
    point, score = match_daily_world_overview_search_entry(enabled_live, 0.90)
    assert point == (88, 2213) and score >= 0.98
    wide_live = Image.open(
        ROOT / "evidence" / "milestone-33-overview-preflight-timeout-v500" / "timeout-overview-private.png"
    ).convert("RGB")
    assert daily_world_overview_resource_is_enabled(wide_live, 0.90)
    assert detect_world_castle_marker_tip(wide_live) is None
    assert detect_world_resource_level(wide_live) is None
    point, score = match_daily_world_overview_search_entry(wide_live, 0.90)
    assert point == (95, 2236) and score >= 0.99
    assert "match_daily_world_overview_home_button(" in overview_flow
    assert "等待绿色城堡坐标进入主地图" in overview_flow

    print("world overview preflight regression checks passed")


if __name__ == "__main__":
    main()
