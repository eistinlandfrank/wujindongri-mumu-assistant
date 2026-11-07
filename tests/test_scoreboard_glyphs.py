import unittest
import tempfile
from pathlib import Path

import numpy as np
from PIL import Image

import wjdr_scoreboard as scores
from wjdr_backend import resource_path


class ScoreboardGlyphTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        atlas = np.asarray(Image.open(resource_path('assets/scoreboard_rank_digits.png')).convert('L')) > 0
        cls.glyphs = []
        for digit in range(10):
            cell = atlas[:, digit * 64:(digit + 1) * 64]
            yy, xx = np.nonzero(cell)
            cls.glyphs.append(cell[yy.min():yy.max()+1, xx.min():xx.max()+1])

    def render(self, text):
        pixels = np.zeros((2560, 1440, 3), dtype=np.uint8)
        x, y = 155, 1200
        for char in text:
            glyph = self.glyphs[int(char)]
            h, w = glyph.shape
            pixels[y:y+h, x:x+w] = glyph[:, :, None] * 255
            x += w + 7
        return Image.fromarray(pixels)

    def test_all_digits_and_three_digit_ranks(self):
        for text in ('1', '2', '3', '4', '5', '6', '7', '8', '9', '10', '17', '70', '107', '170', '200'):
            with self.subTest(text=text):
                self.assertEqual(scores.read_rank_glyphs(self.render(text), [1200]), {0: text})

    def test_invalid_or_non_glyph_shape_is_not_accepted(self):
        self.assertEqual(scores.read_rank_glyphs(self.render('201'), [1200]), {})
        frame = Image.new('RGB', (1440, 2560))
        frame.paste('white', (160, 1200, 190, 1247))
        self.assertEqual(scores.read_rank_glyphs(frame, [1200]), {})

    def test_bracket_confusions_are_only_suggestions(self):
        self.assertEqual(scores.split_ocr_alliance('[RMBlNico'), ('RMB', 'Nico'))
        self.assertEqual(scores.split_ocr_alliance('[CH刂幻海幻听'), ('CH', '幻海幻听'))
        self.assertEqual(scores.split_ocr_alliance('普通昵称'), ('', '普通昵称'))

    def test_draft_is_recoverable_and_separate_from_snapshots(self):
        identity = 'mumu:2:android:abcd'
        other = 'mumu:0:android:1234'
        rows = [dict(rank=1, country='#523', alliance='RMB', name='测试', score=123)]
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            scores.save_capture_draft(identity, rows, 'a' * 32, root)
            self.assertEqual(scores.load_latest_capture_draft(identity, root), rows)
            self.assertEqual(scores.load_snapshots(identity, root), [])
            with self.assertRaises(ValueError):
                scores.load_latest_capture_draft(other, root)


if __name__ == '__main__':
    unittest.main()
