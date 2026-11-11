from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from PIL import Image, ImageEnhance
from wjdr_backend import match_daily_intel_tutorial_station

ROOT = Path(__file__).resolve().parents[1]

def test_intel_tutorial_requires_bubble_and_city():
    frame = Image.new('RGB', (1440, 2560), (50, 75, 100))
    frame.paste(Image.open(ROOT/'tests/fixtures/daily_intel_tutorial_city.png'), (0,1980))
    frame.paste(Image.open(ROOT/'assets/daily_intel_tutorial_bubble.png'), (650,1000))
    frame.paste(Image.open(ROOT/'assets/daily_intel_tutorial_hand.png'), (685,1120))
    assert match_daily_intel_tutorial_station(frame) == (720,1430)
    # A second live frame has a shifted hand and animated portrait lighting.
    # The portrait and city remain sufficient after the verified Daily Go.
    animated = frame.copy()
    animated.paste((50,75,100), (650,1000,950,1500))
    animated.paste(Image.open(ROOT/'tests/fixtures/daily_intel_tutorial_bubble_alt.png'), (652,1000))
    assert match_daily_intel_tutorial_station(animated) == (720,1430)
    assert match_daily_intel_tutorial_station(ImageEnhance.Brightness(frame).enhance(.7)) is None
    missing = frame.copy(); missing.paste((50,75,100), (650,1000,790,1155))
    assert match_daily_intel_tutorial_station(missing) is None
    missing_city = frame.copy(); missing_city.paste((50,75,100), (0,1980,220,2210))
    assert match_daily_intel_tutorial_station(missing_city) is None

if __name__ == '__main__':
    test_intel_tutorial_requires_bubble_and_city()
    print('intel tutorial station gate: PASS')
