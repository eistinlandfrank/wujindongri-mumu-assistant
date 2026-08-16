"""Regression for the compact left/down-shifted gather formation header."""

from pathlib import Path
import sys

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from wjdr_backend import read_daily_gather_formation_capacity


def main() -> None:
    # The persisted fixture is a de-identified header-only crop. Reconstruct
    # its original reference position on an otherwise blank 1440x2560 canvas.
    crop = Image.open(
        ROOT
        / "evidence"
        / "milestone-48-formation-timeout-yield-v514"
        / "iron_formation_header.png"
    ).convert("RGB")
    canvas = Image.new("RGB", (1440, 2560), (8, 52, 93))
    # ``--safe-relative-box 0.10,0.10,0.98,0.25`` maps to this reference
    # origin on the 1440x2560 device. The crop excludes account identity and
    # preserves only the reviewed formation header plus generic troop cards.
    canvas.paste(crop, (144, 256))
    reading = read_daily_gather_formation_capacity(canvas)
    assert reading is not None
    assert reading.selected_troops == 770
    assert reading.carrying_capacity == 4158
    print("compact left formation layout: PASS")


if __name__ == "__main__":
    main()
