from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from PIL import Image, ImageDraw
from wjdr_backend import fast_capture_is_blank


def test_blank_gdi_frame_is_rejected():
    assert fast_capture_is_blank(Image.new('RGB', (1440, 2560), 'black'))
    assert fast_capture_is_blank(Image.new('RGB', (1440, 2560), (2, 2, 2)))
    frame = Image.new('RGB', (1440, 2560), 'black')
    ImageDraw.Draw(frame).rectangle((300, 300, 900, 900), fill=(50, 80, 120))
    assert not fast_capture_is_blank(frame)


if __name__ == '__main__':
    test_blank_gdi_frame_is_rejected()
    print('fast capture blank-frame guard: PASS')
