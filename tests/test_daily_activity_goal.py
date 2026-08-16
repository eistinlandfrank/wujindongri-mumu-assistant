"""Regression checks for the daily 325-point stop gate.

Run with:
    python tests/test_daily_activity_goal.py
"""

from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from wjdr_backend import (  # noqa: E402
    DAILY_ACTIVITY_TARGET_POINTS,
    DailyActivityProgress,
    daily_activity_target_reached,
    estimate_daily_activity_progress,
)


def main() -> None:
    # A maximum bar may visually under-read by roughly three points.  The gate
    # accepts it only with a trustworthy fill, and rejects the preceding
    # 320-point step as well as low-confidence/no-fill observations.
    assert DAILY_ACTIVITY_TARGET_POINTS == 325.0
    assert daily_activity_target_reached(DailyActivityProgress(322.0, 1290, 1.0))
    assert not daily_activity_target_reached(DailyActivityProgress(321.9, 1290, 1.0))
    assert not daily_activity_target_reached(DailyActivityProgress(325.0, None, 1.0))
    assert not daily_activity_target_reached(DailyActivityProgress(325.0, 1290, 0.89))

    # The captured 180-point board must remain actionable and cannot trigger
    # the terminal 325 path at native or scaled portrait resolutions.
    screen = Image.open(ROOT / "evidence" / "milestone-01-environment" / "overview.png").convert("RGB")
    for size in ((1440, 2560), (1080, 1920), (720, 1280)):
        progress = estimate_daily_activity_progress(screen.resize(size))
        assert progress.confidence >= 0.90, (size, progress)
        assert not daily_activity_target_reached(progress), (size, progress)

    # A fresh, account-redacted high-account board visibly reads 375 and its
    # native ADB progress strip must independently authorise the terminal
    # stop.  This fixture deliberately comes from ADB rather than the MuMu
    # render HWND, whose window scaling is unsuitable for Daily-bar geometry.
    final_screen = Image.open(
        ROOT
        / "evidence"
        / "milestone-87-high-account-325-stop"
        / "high-account-final-daily-redacted-full.png"
    ).convert("RGB")
    final_progress = estimate_daily_activity_progress(final_screen)
    assert final_progress.confidence == 1.0, final_progress
    assert daily_activity_target_reached(final_progress), final_progress

    print("daily 325 target gate: PASS")


if __name__ == "__main__":
    main()
