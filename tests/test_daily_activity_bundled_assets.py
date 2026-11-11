"""The score reader must use the files shipped inside a frozen bundle."""
from pathlib import Path
import importlib
import shutil
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import wjdr_backend as backend


def test_score_assets_resolve_from_bundle():
    root = Path(__file__).resolve().parents[1]
    previous = getattr(sys, "_MEIPASS", None)
    with tempfile.TemporaryDirectory() as directory:
        bundle = Path(directory)
        (bundle / "assets").mkdir()
        for name in ("activity_digit_prototypes_full.npz", "daily_activity_full_glyphs.npz"):
            shutil.copyfile(root / "assets" / name, bundle / "assets" / name)
        try:
            sys._MEIPASS = str(bundle)
            importlib.reload(backend)
            assert backend._ACTIVITY_PROTOTYPES_PATH == bundle / "assets" / "activity_digit_prototypes_full.npz"
            assert len(backend._ACTIVITY_PROTOTYPES) == 10
            assert len(backend._ACTIVITY_FULL_GLYPHS) == 10
        finally:
            if previous is None:
                del sys._MEIPASS
            else:
                sys._MEIPASS = previous
            importlib.reload(backend)


if __name__ == "__main__":
    test_score_assets_resolve_from_bundle()
    print("bundled score assets: PASS")
