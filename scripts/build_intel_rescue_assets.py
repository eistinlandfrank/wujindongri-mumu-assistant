"""Build compact, account-free Intel Rescue templates from milestone 93.

The source frames are live 1440x2560 captures.  Every crop stays inside the
game's central content and excludes the account header, alliance chat, map
coordinates, mail count, and other identifying edges.
"""

from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "evidence" / "milestone-93-intel-single-route"
ASSETS = ROOT / "assets"
SAFE_EVIDENCE = SOURCE / "safe"


CROPS = {
    # Exact live progressive Daily title.  The crop stops before ``(n/5)`` so
    # later progress values keep matching, while the full Chinese title keeps
    # it distinct from every other card.
    "daily_mission_process_intel_5_live.png": (
        "intel-five-card-private.png",
        (75, 980, 520, 1068),
    ),
    # The station speech bubble remains above the centred building after the
    # Daily Go route.  The crop excludes the tutorial hand and account bar.
    "daily_intel_station_bubble_live.png": (
        "landing-800ms-private.png",
        (660, 1020, 780, 1135),
    ),
    # Live Intel page title; this proves the map even when no safe tent pin is
    # available, allowing a reviewed upper-left return instead of a blind tap.
    "daily_intel_map_header_live.png": (
        "intel-map-second-private.png",
        (130, 25, 350, 130),
    ),
    # Green tent pin only.  The white tent glyph differentiates it from the
    # green wolf combat pin on the same map.
    "daily_intel_rescue_pin_live.png": (
        "intel-map-second-private.png",
        (590, 665, 745, 845),
    ),
    # Rescue preview title and its exact blue navigation button.
    "daily_intel_rescue_preview_title_live.png": (
        "tent-real-800ms-private.png",
        (440, 640, 1000, 760),
    ),
    "daily_intel_rescue_preview_go_live.png": (
        "tent-real-800ms-private.png",
        (435, 1670, 1005, 1855),
    ),
    # World target panel title and the ordinary green Intel-stamina action.
    "daily_intel_rescue_target_title_live.png": (
        "rescue-view-850ms-private.png",
        (470, 830, 980, 930),
    ),
    "daily_intel_rescue_action_live.png": (
        "rescue-view-850ms-private.png",
        (470, 1180, 970, 1335),
    ),
    # Active non-battle rescue row.  It is observation-only and excludes the
    # changing countdown digits and map coordinates.
    "daily_intel_rescue_active_live.png": (
        "rescue-result-1s-private.png",
        (0, 300, 500, 495),
    ),
}


def main() -> None:
    ASSETS.mkdir(parents=True, exist_ok=True)
    for output_name, (source_name, box) in CROPS.items():
        source_path = SOURCE / source_name
        with Image.open(source_path) as source:
            if source.size != (1440, 2560):
                raise RuntimeError(f"unexpected source geometry for {source_name}: {source.size}")
            crop = source.convert("RGB").crop(box)
            crop.save(ASSETS / output_name, optimize=True)
            print(output_name, crop.size, "<-", source_name, box)

    SAFE_EVIDENCE.mkdir(parents=True, exist_ok=True)
    names = (
        "daily_mission_process_intel_5_live.png",
        "daily_intel_station_bubble_live.png",
        "daily_intel_map_header_live.png",
        "daily_intel_rescue_pin_live.png",
        "daily_intel_rescue_preview_title_live.png",
        "daily_intel_rescue_preview_go_live.png",
        "daily_intel_rescue_target_title_live.png",
        "daily_intel_rescue_action_live.png",
        "daily_intel_rescue_active_live.png",
    )
    tiles = [Image.open(ASSETS / name).convert("RGB") for name in names]
    try:
        width = max(tile.width for tile in tiles) + 24
        height = sum(tile.height for tile in tiles) + 12 * (len(tiles) + 1)
        proof = Image.new("RGB", (width, height), "#203c59")
        y = 12
        for tile in tiles:
            proof.paste(tile, (12, y))
            y += tile.height + 12
        proof.save(SAFE_EVIDENCE / "intel-rescue-route-safe.png", optimize=True)
    finally:
        for tile in tiles:
            tile.close()


if __name__ == "__main__":
    main()
