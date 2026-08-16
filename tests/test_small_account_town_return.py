from __future__ import annotations

from pathlib import Path

from PIL import Image

from wjdr_backend import match_daily_city_wilderness_entry


ROOT = Path(__file__).resolve().parents[1]


def test_small_account_city_variant_needs_same_frame_city_anchor() -> None:
    frame = Image.new("RGB", (1440, 2560), (18, 28, 38))
    clipboard = Image.open(ROOT / "assets" / "daily_city_entry.png").convert("RGB")
    wilderness = Image.open(
        ROOT / "assets" / "daily_city_wilderness_entry_tight_low_account_live.png"
    ).convert("RGB")
    frame.paste(clipboard, (15, 1980))
    frame.paste(wilderness, (1215, 2310))

    assert match_daily_city_wilderness_entry(frame, 0.94)[0] == (1310, 2430)

    without_city = Image.new("RGB", frame.size, (18, 28, 38))
    without_city.paste(wilderness, (1215, 2310))
    assert match_daily_city_wilderness_entry(without_city, 0.94)[0] is None


def test_persistent_town_return_uses_native_frames_only() -> None:
    source = (ROOT / "wjdr_mumu_assistant_qt.py").read_text(encoding="utf-8")
    start = source.index("def reopen_daily_tasks_from_gather_world")
    end = source.index("def yield_gather_search_timeout", start)
    route = source[start:end]
    town_wait = route.split("target.tap(*town_point)", 1)[1]

    assert "target.fast_window_screenshot(reference_size)" not in town_wait
    assert "image = capture_daily_image()" in town_wait
    assert "city_streak >= 2" in town_wait
    assert "target.tap(*city_point)" in town_wait


def main() -> None:
    test_small_account_city_variant_needs_same_frame_city_anchor()
    test_persistent_town_return_uses_native_frames_only()
    print("small-account Town return regression checks passed")


if __name__ == "__main__":
    main()
