"""Regression for the current five-collection Warehouse Daily card."""

from pathlib import Path
import sys

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from wjdr_backend import (  # noqa: E402
    BUILTIN_DAILY_MISSION_GO_CURRENT_ASSET,
    BUILTIN_DAILY_MISSION_WAREHOUSE_SUPPLY_FIVE_CURRENT_ASSET,
    DailyMissionKind,
    match_daily_warehouse_supply_mission,
)


def paste_center(
    frame: Image.Image, asset: Image.Image, center: tuple[int, int]
) -> None:
    frame.paste(asset, (center[0] - asset.width // 2, center[1] - asset.height // 2))


def main() -> None:
    title = Image.open(
        ROOT / BUILTIN_DAILY_MISSION_WAREHOUSE_SUPPLY_FIVE_CURRENT_ASSET
    ).convert("RGB")
    go = Image.open(ROOT / BUILTIN_DAILY_MISSION_GO_CURRENT_ASSET).convert("RGB")
    positive = Image.new("RGB", (1440, 2560), (173, 203, 229))
    paste_center(positive, title, (330, 1659))
    paste_center(positive, go, (1165, 1821))
    match = match_daily_warehouse_supply_mission(positive, 0.90)
    assert match and match.kind is DailyMissionKind.WAREHOUSE_SUPPLY
    assert match.task_point == (330, 1659)
    assert match.go_point == (1165, 1821)
    assert match.score >= 0.99

    title_only = Image.new("RGB", positive.size, (173, 203, 229))
    paste_center(title_only, title, (330, 1659))
    assert match_daily_warehouse_supply_mission(title_only, 0.90) is None


if __name__ == "__main__":
    main()
    print("warehouse five-current checks: PASS")
