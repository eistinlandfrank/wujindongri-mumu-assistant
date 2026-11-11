from pathlib import Path
import sys

from PIL import Image, ImageEnhance

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from wjdr_backend import DailyMissionKind, match_daily_pet_treasure_mission

ROOT = Path(__file__).resolve().parents[1]


def test_pet_treasure_card_requires_exact_title_and_same_row_blue_go():
    frame = Image.new("RGB", (1440, 2560), (40, 60, 90))
    frame.paste(Image.open(ROOT / "tests/fixtures/daily_pet_treasure_row.png"), (30, 1160))
    match = match_daily_pet_treasure_mission(frame, 0.9)
    assert match and match.kind is DailyMissionKind.PET_TREASURE
    assert abs(match.go_point[0] - 1165) < 10
    assert match_daily_pet_treasure_mission(ImageEnhance.Brightness(frame).enhance(0.55), 0.9) is None
    no_title = frame.copy()
    no_title.paste((40, 60, 90), (110, 1170, 690, 1260))
    assert match_daily_pet_treasure_mission(no_title, 0.9) is None
    no_go = frame.copy()
    no_go.paste((40, 60, 90), (1000, 1270, 1400, 1440))
    assert match_daily_pet_treasure_mission(no_go, 0.9) is None


if __name__ == "__main__":
    test_pet_treasure_card_requires_exact_title_and_same_row_blue_go()
    print("pet treasure card gate: PASS")
