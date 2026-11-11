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

    def test_mixed_shield_total_with_touching_digits(self):
        strips = Image.open('tests/fixtures/beast_mixed_touching_digits.png').convert('RGB')
        self.frame.paste(strips.crop((0, 0, 365, 65)), (165, 355))
        self.frame.paste(strips.crop((0, 65, 225, 106)), (840, 1295))
        self.frame.paste(Image.open('assets/beast_withdraw_all.png').convert('RGB'), (50, 2290))
        self.assertEqual(beast.beast_mixed_single_shield(self.frame), (184440, 92220, (145, 2364)))
        self.frame.paste((0, 0, 0), (259, 355, 318, 420))
        self.assertIsNone(beast.beast_mixed_single_shield(self.frame))

    def test_touching_digits_ambiguous_split_is_rejected(self):
        import numpy as np
        glyph = np.ones((31, 59), dtype=bool)
        readings = {27: (4, .99), 32: (5, .99), 28: (3, .99), 31: (6, .99)}
        with patch.object(beast, '_read_daily_numeric_glyph', side_effect=lambda g: readings.get(g.shape[1])):
            self.assertIsNone(beast._beast_total_digits([(0, 0, 59, 31, glyph)]))

    def test_six_digit_shield_count_with_thousands_spacing(self):
        total = Image.open('tests/fixtures/beast_six_digit_total.png').convert('RGB')
        self.frame.paste(total, (165, 355))
        self.frame.paste(Image.open('assets/beast_withdraw_all.png').convert('RGB'), (50, 2290))
        count = Image.open('tests/fixtures/beast_shield_six_digit_count.png').convert('RGB')
        self.frame.paste(count, (840, 1295))
        self.assertEqual(beast.beast_mixed_single_shield(self.frame)[:2], (188310, 188310))
        self.frame.paste((0, 0, 0), (870, 1295, 900, 1336))
        self.assertIsNone(beast.beast_mixed_single_shield(self.frame))

    def test_touching_digits_do_not_bypass_page_or_shield_checks(self):
        strips = Image.open('tests/fixtures/beast_mixed_touching_digits.png').convert('RGB')
        self.frame.paste(strips.crop((0, 0, 365, 65)), (165, 355))
        self.frame.paste(strips.crop((0, 65, 225, 106)), (840, 1295))
        self.frame.paste(Image.open('assets/beast_withdraw_all.png').convert('RGB'), (50, 2290))
        with patch.object(beast, 'match_beast_rally_formation_controls',
                          return_value=SimpleNamespace(state=None)):
            self.assertIsNone(beast.beast_mixed_single_shield(self.frame))
        self.frame.paste(self.frame.crop((52, 1578, 108, 1628)), (52, 1298))
        self.assertIsNone(beast.beast_mixed_single_shield(self.frame))

    def test_first_row_one_does_not_hide_other_selected_troops(self):
        strips = Image.open('tests/fixtures/beast_mixed_touching_digits.png').convert('RGB')
        self.frame.paste(strips.crop((0, 0, 365, 65)), (165, 355))
        self.frame.paste(Image.open('assets/beast_withdraw_all.png').convert('RGB'), (50, 2290))
        # setUp supplies a real first-row "1"; the header proves more troops
        # remain selected, so the state cannot pass the (total, first) == (1, 1) gate.
        state = beast.beast_mixed_single_shield(self.frame)
        self.assertEqual(state[:2], (184440, 1))
        self.assertNotEqual(state[:2], (1, 1))

    def test_archer_first_shield_second_selects_shield_count(self):
        icons = Image.open('tests/fixtures/beast_shield_second_row_icons.png').convert('RGB')
        self.frame.paste(icons.crop((0, 0, 72, 66)), (44, 1290))
        self.frame.paste(icons.crop((0, 66, 72, 132)), (44, 1570))
        strips = Image.open('tests/fixtures/beast_mixed_touching_digits.png').convert('RGB')
        self.frame.paste(strips.crop((0, 0, 365, 65)), (165, 355))
        self.frame.paste(strips.crop((0, 65, 225, 106)), (840, 1575))
        self.frame.paste(Image.open('assets/beast_withdraw_all.png').convert('RGB'), (50, 2290))
        self.assertEqual(beast.beast_first_visible_shield_row(self.frame), 1)
        self.assertEqual(beast.beast_mixed_single_shield(self.frame)[:2], (184440, 92220))
        self.frame.paste((0, 0, 0), (44, 1290, 116, 1356))
        self.assertIsNone(beast.beast_mixed_single_shield(self.frame))


if __name__ == '__main__':
    unittest.main()
