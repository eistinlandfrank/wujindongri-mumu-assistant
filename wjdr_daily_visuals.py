"""Small, read-only visual probes for reviewed Daily screens.

These probes return candidates, not permission to tap. Callers must prove the
page and require the same candidate in two fresh frames before acting.
"""
from __future__ import annotations

import sys
from functools import lru_cache
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

_REFERENCE = (1035, 1841)


@lru_cache(maxsize=8)
def _asset(name: str) -> np.ndarray:
    root = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
    with Image.open(root / "assets" / name) as image:
        return np.asarray(image.convert("RGB"))


def _find(image: Image.Image, name: str, region: tuple[float, float, float, float],
          minimum: float = 0.96, max_difference: float = 12.0) -> tuple[tuple[int, int] | None, float]:
    """Match in game-content pixels; colour check excludes grey variants."""
    width, height = image.size
    if width < 400 or height < 700 or abs(width / height - 1035 / 1841) > 0.025:
        return None, 0.0
    left, top, right, bottom = (round(region[0] * width), round(region[1] * height),
                                round(region[2] * width), round(region[3] * height))
    source = np.asarray(image.crop((left, top, right, bottom)).convert("RGB"))
    original = _asset(name)
    size = (max(1, round(original.shape[1] * width / _REFERENCE[0])),
            max(1, round(original.shape[0] * height / _REFERENCE[1])))
    template = cv2.resize(original, size, interpolation=cv2.INTER_AREA if width < _REFERENCE[0] else cv2.INTER_LINEAR)
    if source.shape[0] < size[1] or source.shape[1] < size[0]:
        return None, 0.0
    result = cv2.matchTemplate(source, template, cv2.TM_CCOEFF_NORMED)
    _, score, _, pos = cv2.minMaxLoc(result)
    if score < minimum:
        return None, float(score)
    x, y = pos
    patch = source[y:y + size[1], x:x + size[0]]
    if np.mean(np.abs(patch.astype(np.float32) - template.astype(np.float32))) > max_difference:
        return None, float(score)
    return (left + x + size[0] // 2, top + y + size[1] // 2), float(score)


def recommended_tech(image: Image.Image) -> tuple[tuple[int, int] | None, float]:
    """Find the green recommendation marker on an already-proved tech page."""
    return _find(image, "daily_recommended_thumb.png", (0.04, 0.25, 0.96, 0.96))


def intel_expert(image: Image.Image) -> tuple[tuple[int, int] | None, float]:
    """Find the reviewed expert portrait on an already-proved Intel map."""
    matches = [_find(image, name, (0.0, 0.10, 0.20, 0.26)) for name in (
        "daily_intel_expert_icon.png", "daily_intel_expert_icon_city.png")]
    return max(matches, key=lambda match: (match[0] is not None, match[1]))


def intel_expert_maybe_visible(image: Image.Image) -> bool:
    """Conservative presence check used only to confirm an expert disappeared."""
    return any(_find(image, name, (0.0, 0.10, 0.20, 0.26), .75, 40.0)[0]
               for name in ("daily_intel_expert_icon.png", "daily_intel_expert_icon_city.png"))


def intel_station_expert(image: Image.Image) -> tuple[tuple[int, int] | None, float]:
    """Find the expert bubble after the verified Intel daily Go."""
    # Lighting changes while the spotlight rotates. Keep a strict colour and
    # similarity check against two observed appearances instead of accepting
    # a weak match. The caller also proves the city on two fresh frames.
    matches = [_find(image, name, (.15, .20, .80, .70), .93, 20.0) for name in (
        "daily_intel_station_expert.png", "daily_intel_station_expert_city.png")]
    return max(matches, key=lambda match: (match[0] is not None, match[1]))


def intel_coloured_candidates(image: Image.Image) -> list[tuple[str, str, tuple[int, int], float]]:
    """Return reviewed orange/purple/blue candidates; page proof is separate.

    These are observations only. Each type still needs its own verified route
    and the same marker on two fresh map frames before any game input.
    """
    probes = (
        ("orange", "tent", "daily_intel_orange_tent.png"),
        ("orange", "paw", "daily_intel_orange_paw.png"),
        ("purple", "axes", "daily_intel_purple_axes.png"),
        ("purple", "paw", "daily_intel_purple_paw.png"),
        ("blue", "paw", "daily_intel_blue_paw.png"),
    )
    # The map contains large pins. Search one bounded 720-pixel-wide copy
    # rather than running five full-resolution template searches.
    original_size = image.size
    if image.width > 720:
        image = image.resize((720, round(image.height * 720 / image.width)), Image.Resampling.LANCZOS)
    found = []
    for colour, kind, asset in probes:
        point, score = _find(image, asset, (.05, .15, .95, .75), minimum=.945, max_difference=20.0)
        if point is not None:
            point = (round(point[0] * original_size[0] / image.width),
                     round(point[1] * original_size[1] / image.height))
            found.append((colour, kind, point, score))
    return found


def expedition_claim(image: Image.Image) -> tuple[tuple[int, int] | None, float]:
    """Return a claim button only when its Expedition header also matches."""
    header, header_score = _find(image, "daily_expedition_header.png", (0.08, 0.0, 0.30, 0.08))
    if not header:
        return None, header_score
    # The chest moves and flashes; the text is more stable than the button's
    # animated background. Colour remains a separate proof against grey or
    # paid controls, and the header constrains the page.
    point, score = _find(image, "daily_expedition_claim_text.png", (0.70, 0.50, 0.99, 0.75),
                         minimum=0.93, max_difference=35.0)
    if point:
        x, y = point
        rx, ry = round(image.width * .045), round(image.height * .018)
        patch = np.asarray(image.crop((x-rx, y-ry, x+rx, y+ry)).convert("RGB"))
        green = ((patch[:, :, 1] > 110) & (patch[:, :, 1] > patch[:, :, 0] * 1.25)
                 & (patch[:, :, 1] > patch[:, :, 2] * 1.15))
        if green.mean() < .25:
            point = None
    return point, min(header_score, score)


def expedition_city_entry(image: Image.Image) -> tuple[tuple[int, int] | None, float]:
    """Locate the bottom Expedition entry on an independently proved city."""
    return _find(image, "daily_expedition_city_entry.png", (0.03, 0.91, 0.18, 1.0), 0.94)


def expedition_idle_claim(image: Image.Image) -> tuple[tuple[int, int] | None, float]:
    """Find the ordinary claim in the reviewed idle-rewards dialog."""
    title, title_score = _find(image, "daily_expedition_idle_title.png", (0.35, 0.20, 0.65, 0.27))
    if not title:
        return None, title_score
    point, score = _find(image, "daily_expedition_idle_claim.png", (0.38, 0.68, 0.62, 0.76))
    return point, min(title_score, score)


def expedition_back(image: Image.Image) -> tuple[tuple[int, int] | None, float]:
    """Return the fixed back coordinate after the Expedition header is proved."""
    header, score = _find(image, "daily_expedition_header.png", (0.08, 0.0, 0.30, 0.08))
    if not header:
        return None, score
    return (round(image.width * .055), round(image.height * .032)), score
