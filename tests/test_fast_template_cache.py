"""Template matching reuses pixels and skips redundant native scaling."""

import sys
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from wjdr_backend import (  # noqa: E402
    _load_template_grayscale_cached,
    match_template,
    template_reference_size,
)


def main() -> None:
    screenshot = Image.open(
        ROOT / "evidence" / "milestone-68-adaptive-device-pacing-v534" / "live-state-private.png"
    ).convert("RGB")
    template = ROOT / "assets" / "daily_city_entry.png"
    _load_template_grayscale_cached.cache_clear()

    first, first_score = match_template(
        screenshot,
        template,
        0.90,
        template_reference_size(template),
    )
    second, second_score = match_template(
        screenshot,
        template,
        0.90,
        template_reference_size(template),
    )
    assert first == second and first is not None
    assert first_score >= 0.90 and second_score >= 0.90
    assert hasattr(screenshot, "_wjdr_grayscale_cache")
    cache = _load_template_grayscale_cached.cache_info()
    assert cache.misses == 1
    assert cache.hits >= 1

    source = (ROOT / "wjdr_backend.py").read_text(encoding="utf-8")
    assert "native_scale = (" in source
    assert "if not native_scale:" in source
    print("fast template cache: PASS")


if __name__ == "__main__":
    main()
