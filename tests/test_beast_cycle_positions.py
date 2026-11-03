import unittest

from PIL import Image, ImageDraw

from wjdr_beast_hunt import CycleActionPositions


class CycleActionPositionsTest(unittest.TestCase):
    def test_reuse_requires_same_viewport_and_local_button(self):
        frame = Image.new('RGB', (720, 1280), (30, 30, 30))
        ImageDraw.Draw(frame).rectangle((315, 588, 345, 612), fill=(235, 140, 20))
        positions = CycleActionPositions()
        self.assertEqual(positions.remember('rally', frame, (330, 600)), (330, 600))
        self.assertEqual(positions.reuse('rally', frame), (330, 600))
        self.assertEqual(positions.reuse('rally', frame, (331, 601)), (330, 600))
        self.assertIsNone(positions.reuse('rally', frame, (340, 600)))
        self.assertIsNone(positions.reuse('rally', Image.new('RGB', frame.size, (30, 30, 30))))
        self.assertIsNone(positions.reuse('rally', frame.resize((1440, 2560))))
        self.assertIsNone(positions.reuse('other', frame))


if __name__ == '__main__':
    unittest.main()
