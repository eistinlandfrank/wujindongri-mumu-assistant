import unittest
from pathlib import Path
from unittest.mock import patch

import cv2
import numpy as np
from PIL import Image

import wjdr_beast_hunt as beast
from wjdr_backend import DailyMarchCapacity


class GatheringProofTest(unittest.TestCase):
    def setUp(self):
        self.capacity = DailyMarchCapacity(4, 6, .99, 'numeric')
        self.rgb = np.full((2560, 1440, 3), 30, dtype=np.uint8)
        sample = np.asarray(Image.open(Path(__file__).parent / 'fixtures/beast_gather_rows.png').convert('RGB'))
        for index in range(4):
            cy = 449 + 141 + 122*index
            cv2.circle(self.rgb, (70,cy), 32, (5,220,10), 9)
            self.rgb[cy-52:cy+4,115:255] = sample[index*56:(index+1)*56]
        self.anchor = patch.object(beast, '_compact_shifted_header', return_value=(87,449))
        self.header = patch.object(beast, 'read_compact_header_digits', return_value=self.capacity)
        self.world = patch.object(beast, 'match_beast_rally_world_search', return_value=((20,20),1.0))
        self.anchor.start(); self.header.start(); self.world.start()
        self.addCleanup(self.anchor.stop); self.addCleanup(self.header.stop); self.addCleanup(self.world.stop)

    def test_all_four_rows_and_two_frames_are_required(self):
        image = Image.fromarray(self.rgb)
        self.assertEqual([r.owner for r in beast.read_compact_queue_icons(image,self.capacity)], ['gathering']*4)
        self.assertTrue(beast.gathering_pair_free(image,image,self.capacity,self.capacity))
        hidden = self.rgb.copy()
        hidden[449+141+122-52:449+141+122+4,115:255] = 0
        self.assertFalse(beast.gathering_pair_free(image,Image.fromarray(hidden),self.capacity,self.capacity))
        full = DailyMarchCapacity(4,4,.99,'numeric')
        self.assertFalse(beast.gathering_pair_free(image,image,full,full))
        mismatch = DailyMarchCapacity(3,6,.99,'numeric')
        self.assertFalse(beast.gathering_pair_free(image,image,self.capacity,mismatch))

    def test_text_alone_or_green_icon_without_text_cannot_pass(self):
        no_green = self.rgb.copy()
        cv2.circle(no_green,(70,590),36,(0,0,0),-1)
        self.assertFalse(beast._compact_gathering_row(no_green,70,590))
        no_text = self.rgb.copy()
        no_text[538:594,115:255] = 0
        self.assertFalse(beast._compact_gathering_row(no_text,70,590))
        self.assertFalse(beast.gathering_pair_free(Image.fromarray(self.rgb),Image.fromarray(no_text),self.capacity,self.capacity))

    def test_real_detailed_background_and_other_statuses(self):
        row = self.rgb.copy()
        region = np.asarray(Image.open(Path(__file__).parent / 'fixtures/beast_gather_background.png').convert('RGB'))
        row[538:594, 115:255] = region
        gray = cv2.cvtColor(region, cv2.COLOR_RGB2GRAY)
        raw = cv2.minMaxLoc(cv2.matchTemplate(gray, beast.compact_gathering_title(), cv2.TM_CCOEFF_NORMED))[1]
        self.assertLess(raw, .94)  # The original matcher rejected this live background.
        self.assertTrue(beast._compact_gathering_row(row, 70, 590))
        self.assertTrue(beast.gathering_pair_free(Image.fromarray(row), Image.fromarray(row), self.capacity, self.capacity))

        for name in ('beast_rally_compact_march_title.png', 'beast_rally_compact_rallying_title.png'):
            wrong = row.copy()
            wrong[538:594, 115:255] = (53, 62, 84)
            title = np.asarray(Image.open(Path('assets') / name).convert('RGB'))
            height, width = title.shape[:2]
            wrong[550:550+height, 115:115+width] = title
            self.assertFalse(beast._compact_gathering_row(wrong, 70, 590), name)
        for a, b in ((115, 153), (153, 192), (192, 230)):
            missing = row.copy()
            missing[545:590, a:b] = (53, 62, 84)
            self.assertFalse(beast._compact_gathering_row(missing, 70, 590))

    def test_second_real_background_requires_all_characters_and_strong_rim(self):
        row = self.rgb.copy()
        region = np.asarray(Image.open(Path(__file__).parent / 'fixtures/beast_gather_background_2.png').convert('RGB'))
        row[538:594, 115:255] = region
        self.assertTrue(beast._compact_gathering_row(row, 70, 590))
        for a, b in ((115, 153), (153, 192), (192, 230)):
            wrong = row.copy()
            wrong[545:590, a:b] = (53, 62, 84)
            self.assertFalse(beast._compact_gathering_row(wrong, 70, 590))
        wrong = row.copy()
        cv2.circle(wrong, (70, 590), 36, (0, 0, 0), -1)
        self.assertFalse(beast._compact_gathering_row(wrong, 70, 590))


if __name__ == '__main__':
    unittest.main()
