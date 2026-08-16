from __future__ import annotations

from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
SOURCE = (
    ROOT
    / "evidence"
    / "milestone-94-high-account-intel-audit"
    / "high-daily-tab-1450ms-private.png"
)
OUTPUT = ROOT / "evidence" / "milestone-95-instance-account-isolation"


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    with Image.open(SOURCE).convert("RGB") as frame:
        # Daily header, score and first task rows only.  The blurred game
        # account header and all player-identifying city content are excluded.
        safe = frame.crop((0, 145, frame.width, 1745))
        safe.save(OUTPUT / "new-account-daily-safe.png")


if __name__ == "__main__":
    main()
