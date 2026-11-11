import unittest
from pathlib import Path

from PIL import Image, ImageOps

from wjdr_daily_visuals import expedition_claim, expedition_idle_claim, intel_coloured_candidates, intel_expert, intel_station_expert, recommended_tech


ASSETS = Path(__file__).resolve().parents[1] / "assets"


def scene(placements):
    image = Image.new("RGB", (1035, 1841), (20, 38, 65))
    for name, position, grey in placements:
        with Image.open(ASSETS / name) as asset:
            asset = asset.convert("RGB")
            if grey:
                asset = ImageOps.grayscale(asset).convert("RGB")
            image.paste(asset, position)
    return image


class DailyVisualTests(unittest.TestCase):
    def test_thumb_and_grey_negative(self):
        item = "daily_recommended_thumb.png"
        self.assertEqual(recommended_tech(scene([(item, (745, 1040), False)]))[0], (772, 1070))
        self.assertIsNone(recommended_tech(scene([(item, (745, 1040), True)]))[0])
        self.assertIsNone(recommended_tech(scene([(item, (745, 20), False)]))[0])

    def test_expert_location(self):
        item = "daily_intel_expert_icon.png"
        self.assertEqual(intel_expert(scene([(item, (42, 257), False)]))[0], (85, 301))
        self.assertIsNone(intel_expert(scene([(item, (400, 257), False)]))[0])

    def test_station_expert_excludes_grey_and_wrong_region(self):
        item = "daily_intel_station_expert.png"
        self.assertIsNotNone(intel_station_expert(scene([(item, (450, 700), False)]))[0])
        self.assertIsNone(intel_station_expert(scene([(item, (450, 700), True)]))[0])
        self.assertIsNone(intel_station_expert(scene([(item, (30, 700), False)]))[0])

    def test_reviewed_intel_colours_and_grey_negative(self):
        placements = [("daily_intel_orange_tent.png", (665, 482), False),
                      ("daily_intel_purple_paw.png", (611, 704), False),
                      ("daily_intel_blue_paw.png", (186, 891), False)]
        found = intel_coloured_candidates(scene(placements))
        self.assertEqual({item[0] for item in found}, {"orange", "purple", "blue"})
        grey = [(name, position, True) for name, position, _ in placements]
        self.assertEqual(intel_coloured_candidates(scene(grey)), [])

    def test_claim_needs_both_header_and_green_button(self):
        header = ("daily_expedition_header.png", (130, 27), False)
        button = ("daily_expedition_claim_button.png", (801, 1211), False)
        point, _ = expedition_claim(scene([header, button]))
        self.assertIsNotNone(point)
        self.assertLess(abs(point[0] - 888), 4)
        self.assertLess(abs(point[1] - 1240), 4)
        self.assertIsNone(expedition_claim(scene([button]))[0])
        self.assertIsNone(expedition_claim(scene([header]))[0])
        self.assertIsNone(expedition_claim(scene([header, (button[0], button[1], True)]))[0])

    def test_scaled_content(self):
        image = scene([("daily_recommended_thumb.png", (745, 1040), False)])
        image = image.resize((1440, 2560), Image.Resampling.LANCZOS)
        point, _ = recommended_tech(image)
        self.assertIsNotNone(point)
        self.assertLess(abs(point[0] - round(772 * 1440 / 1035)), 3)
        self.assertLess(abs(point[1] - round(1070 * 2560 / 1841)), 3)

    def test_idle_rewards_require_title_and_green_claim(self):
        title = ("daily_expedition_idle_title.png", (425, 395), False)
        button = ("daily_expedition_idle_claim.png", (455, 1282), False)
        self.assertIsNotNone(expedition_idle_claim(scene([title, button]))[0])
        self.assertIsNone(expedition_idle_claim(scene([button]))[0])
        self.assertIsNone(expedition_idle_claim(scene([title, (button[0], button[1], True)]))[0])


if __name__ == "__main__":
    unittest.main()
