from pathlib import Path

from PIL import Image

from wjdr_backend import match_daily_intel_rescue_pin


ROOT = Path(__file__).resolve().parents[1]


def _synthetic_intel_map(*, include_grey_tent: bool) -> Image.Image:
    frame = Image.new("RGB", (1440, 2560), (185, 202, 220))
    header = Image.open(ROOT / "assets" / "daily_intel_map_header_live.png").convert(
        "RGB"
    )
    frame.paste(header, (130, 24))
    if include_grey_tent:
        pin = Image.open(
            ROOT / "assets" / "daily_intel_rescue_grey_pin_current_live.png"
        ).convert("RGB")
        frame.paste(pin, (842, 1490))
    return frame


def test_current_grey_tent_is_an_exact_reviewed_rescue_pin() -> None:
    frame = _synthetic_intel_map(include_grey_tent=True)

    point, score = match_daily_intel_rescue_pin(frame, 0.89)

    assert point == (912, 1587)
    assert score >= 0.99


def test_current_map_without_the_grey_tent_exposes_no_grey_tent_point() -> None:
    frame = _synthetic_intel_map(include_grey_tent=False)

    point, _score = match_daily_intel_rescue_pin(frame, 0.89)

    assert point != (912, 1587)
