from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageEnhance

from wjdr_backend import match_daily_city_entry, match_daily_world_town_entry


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "evidence" / "milestone-94-high-account-intel-audit"


def test_dense_alliance_world_frames_return_exact_town_control() -> None:
    for name in ("candidate-25664-private.png", "high-world-second-private.png"):
        frame = Image.open(EVIDENCE / name).convert("RGB")
        point, score = match_daily_world_town_entry(frame, 0.94)
        assert point == (1330, 2395), (name, point, score)
        assert score >= 0.95, (name, score)


def test_daily_page_and_dimmed_world_frame_never_authorise_town_tap() -> None:
    daily = Image.open(EVIDENCE / "high-daily-tab-1450ms-private.png").convert("RGB")
    assert match_daily_world_town_entry(daily, 0.94)[0] is None

    world = Image.open(EVIDENCE / "high-world-second-private.png").convert("RGB")
    dimmed = ImageEnhance.Brightness(world).enhance(0.94)
    assert match_daily_world_town_entry(dimmed, 0.94)[0] is None


def test_expanded_toolbar_world_state_uses_exact_town_variant() -> None:
    """The expanded wilderness toolbar still exposes Town, not Wilderness."""

    frame = Image.new("RGB", (1440, 2560), (16, 24, 32))
    town = Image.open(
        ROOT / "assets" / "daily_world_town_entry_toolbar_live.png"
    ).convert("RGB")
    frame.paste(town, (1235, 2300))

    point, score = match_daily_world_town_entry(frame, 0.94)
    assert point == (1330, 2395), (point, score)
    assert score >= 0.985, score

    dimmed = ImageEnhance.Brightness(frame).enhance(0.94)
    assert match_daily_world_town_entry(dimmed, 0.94)[0] is None


def test_clipboard_plus_town_is_wilderness_not_city() -> None:
    """The shared left clipboard must not override the visible Town state."""

    frame = Image.new("RGB", (1440, 2560), (16, 24, 32))
    clipboard = Image.open(ROOT / "assets" / "daily_city_entry.png").convert("RGB")
    town = Image.open(
        ROOT / "assets" / "daily_world_town_entry_toolbar_live.png"
    ).convert("RGB")
    frame.paste(clipboard, (15, 1980))
    frame.paste(town, (1235, 2300))

    assert match_daily_world_town_entry(frame, 0.94)[0] == (1330, 2395)
    assert match_daily_city_entry(frame, 0.94)[0] is None
