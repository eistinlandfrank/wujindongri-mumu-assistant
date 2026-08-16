"""Focused structural contract for the transient-window capture path."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    backend = (ROOT / "wjdr_backend.py").read_text(encoding="utf-8")
    method = backend.split("def fast_window_screenshot(", 1)[1].split("def tap(", 1)[0]
    assert "render_wnd" in method
    assert "PrintWindow(hwnd, memory_dc, 3)" in method
    assert "image.resize(reference_size" in method
    assert "capture_width, capture_height = reference_width, reference_height" in method
    assert "abs(source_ratio - reference_ratio) <= 0.01" in method
    assert "self.screenshot()" not in method

    controller = (ROOT / "wjdr_mumu_assistant_qt.py").read_text(encoding="utf-8")
    section = controller.split("fast_home_deadline", 1)[1].split(
        "deadline = time.monotonic() + AUTOMATION_STEP_TIMEOUT_SECONDS", 1
    )[0]
    assert "target.fast_window_screenshot(_world_image.size)" in section
    assert "target.screenshot()" not in section
    assert "未用过期ADB帧点击临时小房子" in section
    assert "target.back()" not in section

    print("focused fast-window capture contract passed")


if __name__ == "__main__":
    main()
