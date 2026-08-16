"""Exact network sheet must pause without exposing a dialog action."""

from pathlib import Path
import sys

from PIL import Image, ImageEnhance


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from wjdr_backend import daily_network_dialog_is_visible  # noqa: E402


def main() -> None:
    frame = Image.new("RGB", (1440, 2560), (224, 229, 243))
    frame.paste(
        Image.open(
            ROOT
            / "evidence"
            / "milestone-60-network-no-input-pause-v526"
            / "network_dialog_safe.png"
        ),
        (40, 800),
    )
    assert daily_network_dialog_is_visible(frame, 0.90)
    assert not daily_network_dialog_is_visible(
        Image.new("RGB", (1440, 2560), (224, 229, 243)),
        0.90,
    )

    forced_offline = Image.new("RGB", (1440, 2560), (224, 229, 243))
    forced_offline.paste(
        Image.open(
            ROOT / "assets" / "daily_forced_offline_message_live.png"
        ).convert("RGB"),
        (175, 1170),
    )
    assert daily_network_dialog_is_visible(forced_offline, 0.90)
    assert not daily_network_dialog_is_visible(
        ImageEnhance.Brightness(forced_offline).enhance(0.94),
        0.90,
    )

    source = (ROOT / "wjdr_mumu_assistant_qt.py").read_text(encoding="utf-8")
    assert source.count("if daily_network_dialog_is_visible(image, threshold):") >= 2
    start = source.rindex("if daily_network_dialog_is_visible(image, threshold):")
    end = source.index(
        "welcome_back_point = match_daily_welcome_back_confirm",
        start,
    )
    pause = source[start:end]
    assert "continue" in pause
    assert (
        "self.stop_event.wait" in pause
        or "adaptive_operation_wait" in pause
    )
    assert "target.tap" not in pause
    assert "target.shell" not in pause
    capture_candidates = (
        source.rfind("image = target.screenshot()", 0, start),
        source.rfind("image = capture_daily_image()", 0, start),
    )
    latest_capture = max(capture_candidates)
    assert latest_capture >= 0
    assert latest_capture < start < end
    assert end < source.index("page = detect_daily_task_state(image, threshold)", end)
    print("network/forced-offline zero-input pause: PASS")


if __name__ == "__main__":
    main()
