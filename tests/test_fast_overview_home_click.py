"""Focused regression for the transient anywhere-on-map home button."""

import sys
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from wjdr_backend import match_daily_world_overview_home_button_fast  # noqa: E402


def main() -> None:
    positive = Image.open(
        ROOT
        / "evidence"
        / "milestone-79-live-green-marker-miss"
        / "overview-after-entry-private.png"
    ).convert("RGB")
    point, score = match_daily_world_overview_home_button_fast(positive)
    assert point == (1179, 231) and score >= 0.87

    # Move the reviewed button crop to the middle-left map area.  The fast
    # matcher must follow the visual, never a hard-coded right-top region.
    moved = positive.copy()
    moved.paste(positive.crop((820, 900, 938, 956)), (1120, 203))
    button_asset = Image.open(
        ROOT / "assets" / "daily_world_overview_home_button.png"
    ).convert("RGB")
    moved.paste(button_asset, (360, 900))
    moved_point, moved_score = match_daily_world_overview_home_button_fast(moved)
    assert moved_point == (447, 941) and moved_score >= 0.99

    for negative_path in (
        ROOT
        / "evidence"
        / "milestone-75-castle-home-recovery"
        / "current-private.png",
        ROOT
        / "evidence"
        / "milestone-79-live-green-marker-miss"
        / "after-home-stable-private.png",
    ):
        negative = Image.open(negative_path).convert("RGB")
        assert match_daily_world_overview_home_button_fast(negative)[0] is None

    controller = (ROOT / "wjdr_mumu_assistant_qt.py").read_text(encoding="utf-8")
    section = controller.split("def establish_world_resource_level()", 1)[1].split(
        "def confirm_daily_free_march_capacity", 1
    )[0]
    assert "match_daily_world_overview_home_button_fast(first_overview, 0.76)" in section
    assert section.index("match_daily_world_overview_home_button_fast") < section.index(
        "deadline = time.monotonic() + AUTOMATION_STEP_TIMEOUT_SECONDS"
    )
    assert "fast_home_started + 2.2" in section
    assert "target.tap(*fast_home_point)" in section
    assert "match_recentred_world_globe" not in section
    assert "target.back()" not in section

    print("focused transient home-button regression passed")


if __name__ == "__main__":
    main()
