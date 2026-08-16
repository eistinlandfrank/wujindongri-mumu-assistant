from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image


NATIVE_WIDTH = 1440


def normalized_crop(
    source_path: Path,
    box: tuple[int, int, int, int],
    output_path: Path,
    *,
    source_full_width: int,
) -> None:
    """Crop one reviewed control and normalize it to native 1440px scale."""
    with Image.open(source_path) as source:
        crop = source.convert("RGB").crop(box)
    scale = NATIVE_WIDTH / float(source_full_width)
    size = (
        max(8, round(crop.width * scale)),
        max(8, round(crop.height * scale)),
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    crop.resize(size, Image.Resampling.LANCZOS).save(output_path, "PNG")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--world", type=Path, required=True)
    parser.add_argument("--selector", type=Path, required=True)
    parser.add_argument("--rally-button", type=Path, required=True)
    parser.add_argument("--rally-sheet", type=Path, required=True)
    parser.add_argument("--formation", type=Path, required=True)
    parser.add_argument("--progress", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--evidence", type=Path)
    args = parser.parse_args()

    jobs = (
        # The red rectangles and every account/chat field are deliberately
        # outside these boxes. The resulting assets are account-free.
        (args.world, (22, 1274, 114, 1388), "beast_rally_world_search.png", 1092),
        (args.selector, (306, 20, 462, 178), "beast_rally_beast_target.png", 1086),
        (args.selector, (811, 269, 1034, 350), "beast_rally_level_field_8.png", 1086),
        (args.selector, (324, 499, 765, 612), "beast_rally_search_button.png", 1086),
        (args.rally_button, (5, 2, 377, 128), "beast_rally_open_button_25.png", 1092),
        (args.rally_button, (128, 9, 251, 66), "beast_rally_open_label.png", 1092),
        (args.rally_sheet, (332, 19, 625, 102), "beast_rally_sheet_header.png", 1092),
        (args.rally_sheet, (101, 322, 290, 397), "beast_rally_three_minutes_selected.png", 1092),
        (args.rally_sheet, (185, 326, 292, 393), "beast_rally_three_minutes_label.png", 1092),
        (args.rally_sheet, (303, 684, 641, 773), "beast_rally_launch_button.png", 1092),
        (args.formation, (105, 26, 294, 100), "beast_rally_formation_anchor.png", 1092),
        (args.formation, (48, 151, 143, 238), "beast_rally_first_formation_selected.png", 1092),
        (args.formation, (702, 1784, 945, 1842), "beast_rally_dispatch_label.png", 1092),
        (args.progress, (4, 2, 70, 70), "beast_rally_progress_icon.png", 1092),
        (args.progress, (77, 2, 181, 43), "beast_rally_state_rallying.png", 1092),
    )
    for source, box, name, source_full_width in jobs:
        normalized_crop(
            source,
            box,
            args.output / name,
            source_full_width=source_full_width,
        )
    if args.evidence:
        args.evidence.mkdir(parents=True, exist_ok=True)
        for name in (
            "beast_rally_beast_target.png",
            "beast_rally_three_minutes_selected.png",
            "beast_rally_dispatch_label.png",
            "beast_rally_state_rallying.png",
        ):
            with Image.open(args.output / name) as crop:
                crop.convert("RGB").save(args.evidence / name, "PNG")


if __name__ == "__main__":
    main()
