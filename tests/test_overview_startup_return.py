"""Kingdom-overview startup recovery can resume later Daily items."""

from pathlib import Path
import sys

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from wjdr_backend import (
    match_daily_world_overview_search_entry,
    match_daily_world_town_entry,
)


def test_live_overview_requires_the_dedicated_gate() -> None:
    frame = Image.open(
        ROOT
        / "evidence"
        / "milestone-33-overview-preflight-timeout-v500"
        / "timeout-overview-private.png"
    )
    overview, score = match_daily_world_overview_search_entry(frame, 0.94)
    ordinary, _ = match_daily_world_town_entry(frame, 0.94)
    assert overview == (95, 2236)
    assert score > 0.99
    assert ordinary is None


def test_controller_maps_only_the_reviewed_overview_to_town() -> None:
    source = (ROOT / "wjdr_mumu_assistant_qt.py").read_text(encoding="utf-8")
    helper = source.split("def match_reviewed_world_town_entry", 1)[1].split(
        "def observe", 1
    )[0]
    assert "match_daily_world_town_entry" in helper
    assert "match_daily_world_overview_search_entry" in helper
    assert "map_content_point((1330, 2395), (1440, 2560), image)" in helper
    assert "target.tap" not in helper
    assert source.count("match_reviewed_world_town_entry(image)") >= 2
    reopen = source.split("def reopen_daily_tasks_from_gather_world", 1)[1].split(
        "def yield_gather_search_timeout", 1
    )[0]
    assert "match_reviewed_world_town_entry" in reopen
    assert "match_reviewed_city_daily_entry" in reopen
    city_helper = source.split("def match_reviewed_city_daily_entry", 1)[1].split(
        "def observe", 1
    )[0]
    assert "match_daily_city_entry" in city_helper
    assert "match_daily_city_wilderness_entry" in city_helper
    assert "target.tap" not in city_helper


def main() -> None:
    test_live_overview_requires_the_dedicated_gate()
    test_controller_maps_only_the_reviewed_overview_to_town()
    print("overview startup return regression checks passed")


if __name__ == "__main__":
    main()
