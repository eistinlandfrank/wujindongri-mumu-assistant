from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from wjdr_backend import match_daily_training_collect_tutorial  # noqa: E402


def _synthetic(*, camp: bool, hand: bool) -> Image.Image:
    frame = Image.new("RGB", (1440, 2560), (105, 150, 215))
    if camp:
        frame.paste(
            Image.open(ROOT / "assets" / "daily_training_shield_camp_current_live.png"),
            (260, 1100),
        )
    if hand:
        frame.paste(
            Image.open(ROOT / "assets" / "daily_training_collect_tutorial_target.png"),
            (596, 804),
        )
    return frame


def main() -> None:
    point, score = match_daily_training_collect_tutorial(
        _synthetic(camp=True, hand=True),
        0.90,
    )
    assert point == (720, 1200), (point, score)
    assert score >= 0.96, score

    # The current camp skin is only an additional scene anchor.  It never
    # authorises a tap by itself, and the animated hand never authorises a tap
    # without the exact reviewed camp skin in the central city ROI.
    assert match_daily_training_collect_tutorial(
        _synthetic(camp=True, hand=False),
        0.90,
    )[0] is None
    assert match_daily_training_collect_tutorial(
        _synthetic(camp=False, hand=True),
        0.90,
    )[0] is None
    print("current shield-camp tutorial skin: PASS")


if __name__ == "__main__":
    main()
