import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from PIL import Image
import wjdr_beast_hunt as beast
from wjdr_backend import BeastRallyState


class SingleShieldRecognitionTest(unittest.TestCase):
    def setUp(self):
        self.frame = Image.new('RGB', (1440, 2560))
        icons = Image.open('assets/beast_soldier_types.png').convert('RGB')
        digits = Image.open(Path('tests/fixtures/beast_single_shield_digits.png')).convert('RGB')
        for i, y in enumerate((1298, 1578, 1858)):
            self.frame.paste(icons.crop((0, i * 50, 56, (i + 1) * 50)), (52, y))
            self.frame.paste(digits.crop((0, i * 41, 225, (i + 1) * 41)), (840, y - 3))
        self.page = patch.object(beast, 'match_beast_rally_formation_controls',
                                 return_value=SimpleNamespace(state=BeastRallyState.FORMATION))
        self.viewport = patch.object(beast, 'content_viewport',
            return_value=SimpleNamespace(left=0, top=0, right=1440, bottom=2560, width=1440, height=2560))
        self.page.start()
        self.viewport.start()
        self.addCleanup(self.page.stop)
        self.addCleanup(self.viewport.stop)

    def test_actual_single_shield_and_nonzero_other_troop(self):
        self.assertEqual(beast.beast_soldier_rows(self.frame), (1, 0, 0))
        self.frame.paste(self.frame.crop((840, 1295, 1065, 1336)), (840, 1575))
        self.assertEqual(beast.beast_soldier_rows(self.frame), (1, 1, 0))

    def test_unreadable_digit_or_wrong_type_is_never_safe(self):
        self.frame.paste((0, 0, 0), (840, 1295, 1065, 1336))
        self.assertNotEqual(beast.beast_soldier_rows(self.frame), (1, 0, 0))
        self.frame.paste(self.frame.crop((52, 1578, 108, 1628)), (52, 1298))
        self.assertIsNone(beast.beast_soldier_rows(self.frame))


if __name__ == '__main__':
    unittest.main()
