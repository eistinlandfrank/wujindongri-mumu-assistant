"""Reviewed Pet scenes must reject missing controls and dark overlays."""
from pathlib import Path
import sys

from PIL import Image, ImageEnhance

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import wjdr_backend as b

ROOT = Path(__file__).resolve().parents[1] / "tests" / "fixtures"
CASES = (
    ("checked", b.match_pet_checked_treasure, (370, 480, 730, 800)),
    ("completed", b.match_pet_completed_chest, (500, 1300, 1000, 1900)),
    ("completed_close", b.match_pet_completed_close, (1190, 400, 1360, 560)),
    ("unassigned", b.match_pet_unassigned_treasure, (520, 300, 1100, 850)),
    ("entry", b.match_pet_dispatch_entry, (400, 1900, 1050, 2250)),
    ("start", b.match_pet_start_ten_stamina, (400, 1850, 1050, 2150)),
    ("active", b.match_pet_active_close, (240, 1110, 500, 1180)),
    ("back", b.match_pet_map_back, (0, 0, 200, 170)),
)


def test_pet_scene_proofs():
    for name, matcher, erased_box in CASES:
        frame = Image.open(ROOT / f"pet_scene_{name}.png").convert("RGB")
        assert matcher(frame) is not None, name
        assert matcher(ImageEnhance.Brightness(frame).enhance(0.55)) is None, name
        missing = frame.copy()
        missing.paste((40, 60, 90), erased_box)
        assert matcher(missing) is None, name
    selected = Image.open(ROOT / "pet_scene_start.png").convert("RGB")
    selected.paste((40, 60, 90), (80, 1100, 480, 1250))
    assert b.match_pet_start_ten_stamina(selected) is None
    assert b.match_pet_checked_treasure(Image.open(ROOT / "pet_scene_unassigned.png")) is None
    assert b.match_pet_unassigned_treasure(Image.open(ROOT / "pet_scene_checked.png")) is None


if __name__ == "__main__":
    test_pet_scene_proofs()
    print("pet scene gates: PASS")
