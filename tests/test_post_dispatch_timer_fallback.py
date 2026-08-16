"""Regression for a gather card that appears after the short evidence window."""

from pathlib import Path
import sys

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from wjdr_backend import daily_gather_march_is_active, daily_gather_remaining_time_crop


def test_live_late_gather_card_is_recognised() -> None:
    frame = Image.open(
        ROOT
        / "evidence"
        / "milestone-37-post-dispatch-countdown-v504"
        / "post-dispatch-private.png"
    )
    crop = daily_gather_remaining_time_crop(frame, 0.94)
    assert crop is not None
    assert crop.size == (460, 130)
    assert daily_gather_march_is_active(frame, 0.94)


def test_dispatch_lock_precedes_timer_observation_and_timeout_continues() -> None:
    source = (ROOT / "wjdr_mumu_assistant_qt.py").read_text(encoding="utf-8")
    section = source.split("def record_active_gather_countdown", 1)[1].split(
        "def record_active_training_countdown", 1
    )[0]
    # The settle delay is device-adaptive and deliberately capped well below
    # the old 2.5-second fixed pause.  Keep this regression coupled to the
    # current fast path while still proving that the march lock is installed
    # before any passive timer observation begins.
    observation_start = section.index("if self.stop_event.wait(max(interval, 0.20))")
    assert section.index("active_gather_kind = kind") < observation_start
    assert section.index("dispatched_gather_kinds.add(kind)") < observation_start
    assert section.index("active_gather_recheck_at =") < observation_start

    timeout_branch = section.split("if matched_frames < 2 or countdown is None:", 1)[1].split(
        "record_path: Path | None = None", 1
    )[0]
    assert "时间记为未知并继续返回每日任务处理独立项目" in timeout_branch
    assert "return True" in timeout_branch
    assert "return False" not in timeout_branch


def main() -> None:
    test_live_late_gather_card_is_recognised()
    test_dispatch_lock_precedes_timer_observation_and_timeout_continues()
    print("post-dispatch timer fallback regression checks passed")


if __name__ == "__main__":
    main()
