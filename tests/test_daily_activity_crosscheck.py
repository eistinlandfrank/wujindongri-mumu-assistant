from pathlib import Path
import sys

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from wjdr_backend import read_daily_activity_score


ROOT = Path(__file__).resolve().parents[1] / "tests" / "fixtures"


def frame_with(bar_name, score_name="daily_score_185_crop.png"):
    frame = Image.new("RGB", (1440, 2560), (40, 60, 90))
    frame.paste(Image.open(ROOT / score_name), (125, 762))
    frame.paste(Image.open(ROOT / bar_name), (220, 650))
    return frame


def test_score_requires_independent_bar_agreement():
    assert read_daily_activity_score(frame_with("daily_bar_185_crop.png"))[0] == 185
    # This OCR looks like 185, but the game bar is around 125.  It must not
    # authorize the 160 chest, much less the final 325 milestone.
    assert read_daily_activity_score(frame_with("daily_bar_125_crop.png")) is None
    assert read_daily_activity_score(frame_with("daily_bar_135_crop.png", "daily_score_135_crop.png"))[0] == 135
    assert read_daily_activity_score(frame_with("daily_bar_185_crop.png", "daily_score_135_crop.png")) is None


def full_frame(score_name, bar_name=None):
    frame = Image.new("RGB", (1440, 2560), (40, 60, 90))
    frame.paste(Image.open(ROOT / f"activity_bar_full_{bar_name or score_name}.png"), (220, 650))
    frame.paste(Image.open(ROOT / f"activity_score_full_{score_name}.png"), (105, 755))
    return frame


def test_full_scores_and_disagreement():
    for score in (125, 140, 165, 185, 195):
        assert read_daily_activity_score(full_frame(str(score)))[0] == score
    for size in ((1080, 1920), (720, 1280)):
        assert read_daily_activity_score(full_frame("140").resize(size, Image.Resampling.LANCZOS))[0] == 140
    # The 325 glyph and filled bar are synthetic; this proves the code path,
    # not a live 325-point outcome.
    assert read_daily_activity_score(full_frame("325_synthetic"))[0] == 325
    # This de-identified crop is from a real game screen displaying 375; the
    # progress track saturates at 325 while the printed total continues.
    assert read_daily_activity_score(full_frame("375"))[0] == 375
    for size in ((1080, 1920), (720, 1280)):
        assert read_daily_activity_score(full_frame("375").resize(size, Image.Resampling.LANCZOS))[0] == 375
    assert read_daily_activity_score(full_frame("325_synthetic", "140")) is None
    assert read_daily_activity_score(full_frame("375", "140")) is None
    assert read_daily_activity_score(full_frame("140", "325_synthetic")) is None
    obscured = full_frame("140")
    obscured.paste((40, 60, 90), (120, 760, 205, 810))
    assert read_daily_activity_score(obscured) is None


if __name__ == "__main__":
    test_score_requires_independent_bar_agreement()
    test_full_scores_and_disagreement()
    print("daily score/bar cross-check: PASS")
