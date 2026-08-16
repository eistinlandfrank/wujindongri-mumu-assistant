from pathlib import Path

from PIL import Image

from wjdr_backend import match_daily_warehouse_city_supply_bubble


ROOT = Path(__file__).resolve().parents[1]
ASSET = ROOT / "assets" / "daily_warehouse_city_supply_bubble_live.png"
NIGHT_ASSETS = tuple(
    ROOT / "assets" / f"daily_warehouse_city_supply_bubble_night_pose_{index}_live.png"
    for index in range(1, 6)
)
SOURCE = (ROOT / "wjdr_mumu_assistant_qt.py").read_text(encoding="utf-8")


def test_warehouse_city_supply_bubble_requires_exact_tight_asset() -> None:
    asset = Image.open(ASSET).convert("RGB")
    frame = Image.new("RGB", (1440, 2560), (33, 55, 78))
    frame.paste(asset, (625, 1030))
    point, score = match_daily_warehouse_city_supply_bubble(frame, 0.94)
    assert point is not None and score >= 0.999
    assert abs(point[0] - 672) <= 2
    assert abs(point[1] - 1110) <= 2
    assert match_daily_warehouse_city_supply_bubble(
        Image.new("RGB", (1440, 2560), (33, 55, 78)), 0.94
    )[0] is None


def test_warehouse_night_hand_poses_share_one_stable_action_point() -> None:
    for path in NIGHT_ASSETS:
        frame = Image.new("RGB", (1440, 2560), (33, 55, 78))
        frame.paste(Image.open(path).convert("RGB"), (625, 1030))
        point, score = match_daily_warehouse_city_supply_bubble(frame, 0.94)
        assert point is not None and score >= 0.999
        assert abs(point[0] - 672) <= 2 and abs(point[1] - 1110) <= 2


def test_warehouse_continuous_hand_fallback_needs_city_bubble_and_chest() -> None:
    frame = Image.new("RGB", (1440, 2560), (33, 55, 78))
    city = Image.open(ROOT / "assets" / "daily_city_entry.png").convert("RGB")
    frame.paste(city, (15, 1980))
    frame.paste((225, 225, 225), (600, 1030, 680, 1110))
    frame.paste((160, 105, 55), (600, 1110, 680, 1160))
    point, score = match_daily_warehouse_city_supply_bubble(frame, 0.94)
    assert point == (672, 1110)
    assert score >= 0.96

    no_chest = frame.copy()
    no_chest.paste((225, 225, 225), (600, 1030, 680, 1160))
    assert match_daily_warehouse_city_supply_bubble(no_chest, 0.94)[0] is None

    no_city = frame.copy()
    no_city.paste((33, 55, 78), (0, 1900, 230, 2330))
    assert match_daily_warehouse_city_supply_bubble(no_city, 0.94)[0] is None


def test_warehouse_bubble_click_is_correlated_and_double_confirmed() -> None:
    plan = SOURCE[
        SOURCE.index("def run_warehouse_supply_plan") : SOURCE.index(
            "def run_intel_rescue_plan"
        )
    ]
    assert "if city_streak >= 2 and city_point" in plan
    assert "supply_bubble_streak >= 2" in plan
    assert "supply_bubble_tapped = True" in plan
    assert plan.count("target.tap(*supply_bubble)") == 1
