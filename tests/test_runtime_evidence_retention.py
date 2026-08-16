"""Runtime evidence is rolling storage and never a recognition input."""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from wjdr_backend import prune_runtime_evidence  # noqa: E402


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="wjdr-evidence-retention-") as raw:
        directory = Path(raw)
        for index in range(30):
            path = directory / f"frame-{index:02d}.png"
            path.write_bytes(b"png-test")
            os.utime(path, (index + 1, index + 1))
        note = directory / "run-notes.md"
        note.write_text("keep", encoding="utf-8")
        removed = prune_runtime_evidence(directory, 24)
        remaining = sorted(path.name for path in directory.glob("*.png"))
        assert removed == 6
        assert len(remaining) == 24
        assert remaining[0] == "frame-06.png"
        assert remaining[-1] == "frame-29.png"
        assert note.read_text(encoding="utf-8") == "keep"

    source = (ROOT / "wjdr_mumu_assistant_qt.py").read_text(encoding="utf-8")
    # Helper definition plus gather, training, documented-task and Intel
    # countdown call sites must all remain on rolling storage.
    assert source.count("prune_saved_runtime_evidence(") == 5
    assert "识图仍只使用实时ADB帧" in source
    assert 'CONFIG_DIR / "evidence" / "gather_countdowns"' in source
    assert 'CONFIG_DIR / "evidence" / "training_countdowns"' in source
    assert 'CONFIG_DIR / "evidence" / "documented_daily_tasks"' in source
    assert 'CONFIG_DIR / "evidence" / "intel_countdowns"' in source
    print("runtime evidence retention: PASS")


if __name__ == "__main__":
    main()
