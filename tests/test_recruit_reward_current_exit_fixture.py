from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np
from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
CURRENT = ROOT / "assets" / "daily_tap_anywhere_exit_reward_current_live.png"
LEGACY = ROOT / "assets" / "daily_hero_recruit_exit_hint_live.png"


def _score(frame: Image.Image, template_path: Path) -> float:
    frame_bgr = cv2.cvtColor(np.asarray(frame.convert("RGB")), cv2.COLOR_RGB2BGR)
    template_bgr = cv2.imread(str(template_path), cv2.IMREAD_COLOR)
    assert template_bgr is not None
    result = cv2.matchTemplate(frame_bgr, template_bgr, cv2.TM_CCOEFF_NORMED)
    return float(result.max())


def test_current_reward_exit_fixture_is_tight_and_account_free() -> None:
    phrase = Image.open(CURRENT).convert("RGB")

    assert phrase.size == (430, 70)


def test_current_reward_exit_fixture_matches_at_multiple_native_positions() -> None:
    phrase = Image.open(CURRENT).convert("RGB")
    for position in ((20, 180), (505, 1240), (990, 2180)):
        frame = Image.new("RGB", (1440, 2560), (15, 15, 15))
        frame.paste(phrase, position)

        assert _score(frame, CURRENT) >= 0.999


def test_previous_exit_fixture_is_not_an_exact_match_for_current_rendering() -> None:
    current_rendering = Image.open(CURRENT).convert("RGB")

    current_score = _score(current_rendering, CURRENT)
    legacy_score = _score(current_rendering, LEGACY)

    assert current_score >= 0.999
    assert 0.89 <= legacy_score < 0.985


def test_plain_page_does_not_match_current_reward_exit_fixture() -> None:
    frame = Image.new("RGB", (1440, 2560), (15, 78, 145))

    assert _score(frame, CURRENT) < 0.985
