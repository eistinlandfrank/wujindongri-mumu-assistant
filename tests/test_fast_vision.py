"""Accuracy and speed smoke tests for the read-only batch vision tool."""

import sys
import time
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from wjdr_fast_vision import (  # noqa: E402
    FastVisionEngine,
    builtin_template_specs,
    region_diff,
)


def main() -> None:
    source = (ROOT / "wjdr_fast_vision.py").read_text(encoding="utf-8")
    for forbidden in (
        '"input", "tap"',
        '"input", "swipe"',
        '"input", "keyevent"',
        "shell input tap",
        "shell input swipe",
        "shell input keyevent",
    ):
        assert forbidden not in source, f"read-only boundary violated: {forbidden}"

    evidence = ROOT / "evidence" / "milestone-09-alliance-tech-scan"
    specs = builtin_template_specs(r"daily_alliance_tech_.*tab_strip")
    assert {spec.key for spec in specs} == {
        "daily_alliance_tech_battle_tab_strip",
        "daily_alliance_tech_development_tab_strip",
        "daily_alliance_tech_territory_tab_strip",
    }
    engine = FastVisionEngine(specs, workers=3)

    cases = (
        (
            ROOT / "evidence" / "milestone-06-live-run" / "v474-batch4-safe-stop-private.png",
            "daily_alliance_tech_battle_tab_strip",
        ),
        (
            ROOT / "evidence" / "milestone-06-live-run" / "v475-after-development-private.png",
            "daily_alliance_tech_development_tab_strip",
        ),
        (evidence / "territory-00-private.png", "daily_alliance_tech_territory_tab_strip"),
    )
    for path, expected in cases:
        image = Image.open(path).convert("RGB")
        _frame, results, elapsed_ms = engine.inspect(image, threshold=0.94)
        assert results[0].key == expected
        assert results[0].score >= 0.985
        assert elapsed_ms < 2000.0

    moving = region_diff(
        Image.open(evidence / "viewport-02-safe.png"),
        Image.open(evidence / "viewport-03-safe.png"),
        (0, 0, 1360, 1550),
    )
    stationary = region_diff(
        Image.open(evidence / "viewport-03-safe.png"),
        Image.open(evidence / "viewport-04-safe.png"),
        (0, 0, 1360, 1550),
    )
    assert moving.mean_change > 0.7
    assert stationary.mean_change == 0.0
    assert stationary.changed_pixel_ratio == 0.0

    all_daily = builtin_template_specs(r"^daily_")
    all_engine = FastVisionEngine(all_daily)
    image = Image.open(evidence / "territory-00-private.png").convert("RGB")
    started = time.perf_counter()
    _frame, results, elapsed_ms = all_engine.inspect(image, threshold=0.94)
    wall_ms = (time.perf_counter() - started) * 1000.0
    assert len(results) >= 70
    assert results[0].key == "daily_alliance_tech_territory_tab_strip"
    assert elapsed_ms < 5000.0
    print(
        f"fast vision: PASS ({len(results)} templates, "
        f"engine={elapsed_ms:.1f} ms, wall={wall_ms:.1f} ms)"
    )


if __name__ == "__main__":
    main()
