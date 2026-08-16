"""Build compact world-route anchors from the milestone-94 high-account audit."""

from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "evidence" / "milestone-94-high-account-intel-audit"
ASSETS = ROOT / "assets"
SAFE_EVIDENCE = SOURCE / "safe"


CROPS = {
    # Static circular lens face only; excludes alliance names and terrain.
    "daily_world_search_tight_dense_live.png": (
        "high-world-second-private.png",
        (42, 1695, 123, 1765),
    ),
    # Static orange Town door only; excludes the dynamic settlement behind it.
    "daily_world_town_entry_tight_dense_live.png": (
        "high-world-second-private.png",
        (1235, 2300, 1405, 2495),
    ),
}


def main() -> None:
    ASSETS.mkdir(parents=True, exist_ok=True)
    for output_name, (source_name, box) in CROPS.items():
        with Image.open(SOURCE / source_name) as source:
            if source.size != (1440, 2560):
                raise RuntimeError(f"unexpected geometry for {source_name}: {source.size}")
            crop = source.convert("RGB").crop(box)
            crop.save(ASSETS / output_name, optimize=True)
            print(output_name, crop.size, "<-", source_name, box)

    SAFE_EVIDENCE.mkdir(parents=True, exist_ok=True)
    with Image.open(SOURCE / "high-world-second-private.png").convert("RGB") as source:
        # Only the two static navigation controls are retained.  Alliance
        # labels, castle names, minimap, resources and account header remain
        # outside the safe proof.
        search = source.crop((30, 1660, 145, 1810))
        town = source.crop((1215, 2265, 1440, 2560))
        proof = Image.new("RGB", (search.width + town.width + 24, max(search.height, town.height)), "#203c59")
        proof.paste(search, (0, 0))
        proof.paste(town, (search.width + 24, 0))
        proof.save(SAFE_EVIDENCE / "dense-world-return-controls-safe.png", optimize=True)


if __name__ == "__main__":
    main()
