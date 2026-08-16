import sys
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from wjdr_backend import (  # noqa: E402
    daily_gather_march_is_active,
    read_daily_gather_formation_capacity,
    read_daily_march_capacity,
)


EVIDENCE = ROOT / "evidence" / "milestone-21-multi-march-capacity"
COMPACT = ROOT / "evidence" / "milestone-36-formation-proof-v503"
FULL_QUEUE = ROOT / "evidence" / "milestone-40-full-queue-continue-v507"
RIGHT_COMPACT = ROOT / "evidence" / "milestone-56-right-compact-march-v522"
LONG_CAPACITY = ROOT / "evidence" / "milestone-146-long-carry-capacity"


def test_reads_live_proved_multi_march_header() -> None:
    reading = read_daily_march_capacity(
        Image.open(EVIDENCE / "16384-world-map-private-2.png")
    )
    assert reading is not None
    assert (reading.used, reading.total, reading.free) == (1, 6, 5)
    assert reading.confidence >= 0.90


def test_hidden_header_never_invents_capacity() -> None:
    assert (
        read_daily_march_capacity(
            Image.open(EVIDENCE / "16384-world-map-free2-private.png")
        )
        is None
    )


def test_reads_live_proved_selected_troops_and_carrying_capacity() -> None:
    reading = read_daily_gather_formation_capacity(
        Image.open(EVIDENCE / "16384-meat-formation-private.png")
    )
    assert reading is not None
    assert reading.selected_troops == 3_167
    assert reading.carrying_capacity == 1_200_293
    assert reading.confidence >= 0.90


def test_gather_capacity_rejects_animated_partial_value() -> None:
    source = (ROOT / "wjdr_backend.py").read_text(encoding="utf-8")
    helper = source[
        source.index("def read_daily_gather_formation_capacity") : source.index(
            "def daily_gather_march_is_active"
        )
    ]
    assert "carrying_capacity < selected_troops" in helper
    assert "this is an incomplete rendering" in helper


def test_reads_current_eight_digit_mature_capacity_without_left_clipping() -> None:
    frame = Image.new("RGB", (1440, 2560), (8, 52, 93))
    frame.paste(
        Image.open(LONG_CAPACITY / "wood-formation-header-account-free.png"),
        (150, 340),
    )
    reading = read_daily_gather_formation_capacity(frame)
    assert reading is not None
    assert reading.selected_troops == 65_964
    assert reading.carrying_capacity == 25_000_356
    assert reading.confidence >= 0.90


def test_non_formation_page_never_invents_troops() -> None:
    assert (
        read_daily_gather_formation_capacity(
            Image.open(EVIDENCE / "16384-world-map-private-2.png")
        )
        is None
    )


def test_reads_compact_low_level_formation_twice() -> None:
    for name in ("formation-stop-private.png", "formation-stop-2-private.png"):
        reading = read_daily_gather_formation_capacity(Image.open(COMPACT / name))
        assert reading is not None
        assert reading.selected_troops == 770
        assert reading.carrying_capacity == 83_160
        assert reading.confidence >= 0.88


def test_reads_live_full_one_slot_queue_twice() -> None:
    for name in ("wood_full_queue_1-private.png", "wood_full_queue_2-private.png"):
        reading = read_daily_march_capacity(Image.open(FULL_QUEUE / name))
        assert reading is not None
        assert (reading.used, reading.total, reading.free) == (1, 1, 0)
        assert reading.confidence >= 0.93


def test_right_side_compact_march_indicator_blocks_duplicate_dispatch() -> None:
    # Rebuild a reference-size, account-free frame from the central evidence
    # crop.  The recogniser must see the live indicator even though the old
    # ``used/total`` header is absent; a blank frame must stay negative.
    frame = Image.new("RGB", (1440, 2560), (224, 229, 243))
    frame.paste(Image.open(RIGHT_COMPACT / "right_compact_march_safe.png"), (1190, 1000))
    assert read_daily_march_capacity(frame) is None
    assert daily_gather_march_is_active(frame, 0.90)
    assert not daily_gather_march_is_active(
        Image.new("RGB", (1440, 2560), (224, 229, 243)),
        0.90,
    )


def test_hidden_header_bootstrap_is_consumed_only_by_dispatch() -> None:
    source = (ROOT / "wjdr_mumu_assistant_qt.py").read_text(encoding="utf-8")
    capacity_helper = source.split("def confirm_daily_free_march_capacity", 1)[1].split(
        "def wait_for_natural_gather_return", 1
    )[0]
    assert "bootstrap_dispatch_used = True" not in capacity_helper
    assert source.count("bootstrap_dispatch_used = True") == 1
    dispatch_tail = source.split("target.tap(*dispatch_point)", 1)[1].split(
        "completed_dispatches += 1", 1
    )[0]
    assert "if known_march_total is None" in dispatch_tail
    assert "bootstrap_dispatch_used = True" in dispatch_tail


def main() -> None:
    test_reads_live_proved_multi_march_header()
    test_hidden_header_never_invents_capacity()
    test_reads_live_proved_selected_troops_and_carrying_capacity()
    test_gather_capacity_rejects_animated_partial_value()
    test_reads_current_eight_digit_mature_capacity_without_left_clipping()
    test_non_formation_page_never_invents_troops()
    test_reads_compact_low_level_formation_twice()
    test_reads_live_full_one_slot_queue_twice()
    test_right_side_compact_march_indicator_blocks_duplicate_dispatch()
    test_hidden_header_bootstrap_is_consumed_only_by_dispatch()
    print("multi-march capacity regression checks passed")


if __name__ == "__main__":
    main()
