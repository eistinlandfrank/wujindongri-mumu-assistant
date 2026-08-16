"""Exact city-to-world entry variants and negative fixtures."""

from pathlib import Path
import sys

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from wjdr_backend import match_daily_city_wilderness_entry


def test_current_day_city_matches_twice() -> None:
    evidence = ROOT / "evidence" / "milestone-38-two-account-resume"
    for name in (
        "16416_city_return_check_1-private.png",
        "16416_city_return_check_2-private.png",
    ):
        point, score = match_daily_city_wilderness_entry(Image.open(evidence / name), 0.94)
        assert point == (1310, 2430)
        assert score >= 0.985


def test_world_map_never_matches_city_entry() -> None:
    world = Image.open(
        ROOT
        / "evidence"
        / "milestone-37-post-dispatch-countdown-v504"
        / "post-dispatch-private.png"
    )
    point, _score = match_daily_city_wilderness_entry(world, 0.94)
    assert point is None


def test_current_tight_variant_keeps_city_gate_and_live_center() -> None:
    source = (ROOT / "wjdr_backend.py").read_text(encoding="utf-8")
    start = source.index("def match_daily_city_wilderness_entry")
    end = source.index("def match_daily_world_overview_entry", start)
    matcher = source[start:end]
    assert matcher.index("match_daily_city_entry") < matcher.index(
        "BUILTIN_DAILY_CITY_WILDERNESS_ENTRY_TIGHT_DAY_ASSET"
    )
    assert "max(0.97, float(threshold))" in matcher
    assert "map_content_point((1310, 2430)" in matcher


def main() -> None:
    test_current_day_city_matches_twice()
    test_world_map_never_matches_city_entry()
    test_current_tight_variant_keeps_city_gate_and_live_center()
    print("city wilderness entry regression checks passed")


if __name__ == "__main__":
    main()
