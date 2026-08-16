"""Focused regression for the training-guide highlighted city task strip."""

from pathlib import Path
import sys

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from wjdr_backend import match_daily_city_entry  # noqa: E402


def main() -> None:
    base = Image.open(
        ROOT
        / "evidence"
        / "milestone-148-warehouse-result-low-account"
        / "warehouse-city-negative-account-free.png"
    ).convert("RGB")
    highlighted = Image.open(
        ROOT / "assets" / "daily_city_entry_training_highlight_current_live.png"
    ).convert("RGB")
    base.paste(highlighted, (53, 2048))
    point, score = match_daily_city_entry(base, 0.94)
    assert point == (74, 2110)
    assert score >= 0.999

    wilderness = Image.open(
        ROOT
        / "evidence"
        / "milestone-111-small-account-town-return"
        / "wilderness-anchor-account-free.png"
    ).convert("RGB")
    assert match_daily_city_entry(wilderness, 0.94)[0] is None


if __name__ == "__main__":
    main()
    print("training highlight city recovery focused checks: PASS")
