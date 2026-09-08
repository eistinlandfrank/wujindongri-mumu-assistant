import unittest
from unittest.mock import patch
from PIL import Image, ImageDraw
import wjdr_beast_hunt as h
from wjdr_backend import DailyMarchCapacity


class BluePhaseTest(unittest.TestCase):
    def test_clear_numeric_and_complete_icons_survive_title_background_failure(self):
        cap=DailyMarchCapacity(5,6,1)
        im=self.frame([(50,135,215)]*5)
        with patch.object(h,'read_beast_rally_collapsed_march_capacity',return_value=None), \
             patch.object(h,'match_beast_rally_world_search',return_value=((90,1754),1)), \
             patch.object(h,'match_beast_rally_progress_sidebar_expanded',return_value=(None,0)), \
             patch.object(h,'read_compact_header_digits',return_value=cap):
            self.assertEqual(h.read_compact_capacity(im),cap)

    def test_live_numeric_crop_excludes_bright_map_background(self):
        im=Image.new('RGB',(1440,2560),(205,207,220))
        with Image.open('tests/fixtures/beast_compact_header_3of6.png') as crop:
            im.paste(crop,(395,400))
        for size in ((720,1280),(1080,1920),(1440,2560)):
            cap=h.read_compact_header_digits(im.resize(size))
            self.assertIsNotNone(cap)
            self.assertEqual((cap.used,cap.total),(3,6))

    def frame(self, colors):
        im=Image.new('RGB',(1440,2560),(30,50,90))
        d=ImageDraw.Draw(im)
        for i,color in enumerate(colors):
            cy=545+122*i
            d.ellipse((32,cy-38,108,cy+38),fill=color)
            d.rectangle((53,cy-21,83,cy+17),fill='white')
            # All bars are green regardless of ownership.
            d.rectangle((123,cy+20,370,cy+45),fill=(20,200,35))
        return im

    def test_blue_return_march_independent_of_text_and_bar(self):
        for count in (2,3,5):
            for size in ((720,1280),(1080,1920),(1440,2560)):
                im=self.frame([(50,135,215)]*count).resize(size)
                cap=DailyMarchCapacity(count,6,1)
                rows=h.read_compact_queue_icons(im,cap)
                self.assertTrue(h.blue_only_free_slot(cap,rows))

    def test_green_unknown_missing_full_or_mismatched_cannot_pass(self):
        cap=DailyMarchCapacity(2,6,1)
        for colors in ([(50,135,215),(20,175,20)],[(50,135,215),(110,110,110)],[(50,135,215)]):
            im=self.frame(colors)
            self.assertFalse(h.blue_only_free_slot(cap,h.read_compact_queue_icons(im,cap)))
        im=self.frame([(50,135,215)]*2)
        full=DailyMarchCapacity(2,2,1)
        self.assertFalse(h.blue_only_free_slot(full,h.read_compact_queue_icons(im,full)))
        with patch.object(h,'match_beast_rally_world_search',return_value=((90,1754),1)):
            self.assertFalse(h.blue_pair_free(im,im,cap,DailyMarchCapacity(3,6,1)))
            self.assertTrue(h.blue_pair_free(im,im,cap,cap))
        with patch.object(h,'match_beast_rally_world_search',return_value=(None,0)):
            self.assertFalse(h.blue_pair_free(im,im,cap,cap))

    def test_controller_can_finish_without_catching_short_green_march(self):
        from tests.test_beast_safe_recovery import nested
        from types import SimpleNamespace
        from unittest.mock import Mock
        import threading
        frames=iter(['own','own','blue','blue'])
        env=dict(baseline_march_capacity=(0,6),SingleBeastCycle=h.SingleBeastCycle,
                 match_same_target_conflict=lambda _:None,
                 time=SimpleNamespace(monotonic=Mock(side_effect=range(100))),
                 capture=lambda:next(frames),threshold=.9,identity='test',
                 read_compact_rally_rows=lambda f:(h.CompactRallyRow('own',(70,545),1),) if f=='own' else (),
                 read_compact_marching_rows=lambda _:(),
                 read_beast_rally_collapsed_march_capacity=lambda *_:DailyMarchCapacity(3,6,1),
                 blue_pair_free=lambda a,b,*_:a==b=='blue',
                 stable=lambda p,q:p==q,confirm_beast_rally_stamina_reservation=Mock(return_value=25),
                 self=SimpleNamespace(stop_event=threading.Event(),_log_for_device=Mock()),
                 target=SimpleNamespace(device='test'),set_state=Mock(),save_evidence=Mock(),pause=lambda:False)
        self.assertTrue(nested('monitor_single_team',env)())
        self.assertEqual(env['save_evidence'].call_args.args[2],'hunt_no_green_blue_remaining')
