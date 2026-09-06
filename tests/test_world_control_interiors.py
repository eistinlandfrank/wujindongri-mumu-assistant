import unittest
from PIL import Image, ImageEnhance
from wjdr_backend import (match_world_control_interiors,
                          match_beast_rally_world_search, match_daily_city_wilderness_entry)


class WorldControlInteriorTests(unittest.TestCase):
    def frame(self, background=(45, 76, 115)):
        frame = Image.new('RGB', (1440, 2560), background)
        for name, at in [('beast_rally_world_town_dense_live.png', (1225, 2250)),
                         ('beast_rally_world_search_round_live.png', (25, 1682))]:
            with Image.open('assets/'+name) as asset:
                frame.paste(asset, at)
        return frame

    def test_pair_proves_world_not_city(self):
        frame = self.frame()
        self.assertEqual(match_world_control_interiors(frame)[:2], (True, True))
        self.assertEqual(match_beast_rally_world_search(frame)[0], (90, 1754))
        self.assertIsNone(match_daily_city_wilderness_entry(frame, .9)[0])

    def test_outside_pixels_do_not_control_recognition(self):
        original = self.frame()
        for background in [(180, 120, 150), (40, 200, 100), (230, 230, 250)]:
            frame = Image.new('RGB', original.size, background)
            frame.paste(original.crop((1260, 2362, 1335, 2457)), (1260, 2362))
            frame.paste(original.crop((45, 1704, 138, 1800)), (45, 1704))
            self.assertEqual(match_world_control_interiors(frame)[:2], (True, True))

    def test_dimmed_dialog_does_not_expose_new_action(self):
        for level in (.94, .75, .4):
            self.assertFalse(all(match_world_control_interiors(ImageEnhance.Brightness(self.frame()).enhance(level))[:2]))

    def test_plain_white_patch_missing_icon_and_wrong_position_fail(self):
        frame = self.frame()
        frame.paste('white', (27, 1686, 156, 1818))
        self.assertFalse(match_world_control_interiors(frame)[1])
        frame = self.frame()
        frame.paste((45, 76, 115), (1242, 2344, 1353, 2475))
        self.assertFalse(match_world_control_interiors(frame)[0])

    def test_scaled_portrait(self):
        self.assertEqual(match_world_control_interiors(self.frame().resize((1080, 1920)))[:2], (True, True))


if __name__ == '__main__':
    unittest.main()
