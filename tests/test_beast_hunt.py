import unittest
from pathlib import Path
from PIL import Image, ImageDraw
from wjdr_beast_hunt import match_hunt_formation, SingleBeastCycle, read_sidebar_countdown
from wjdr_backend import BeastRallyState
from wjdr_beast_hunt import read_compact_rally_rows
from wjdr_beast_hunt import read_compact_marching_rows, only_joined_rallies, CompactRallyRow
from wjdr_backend import DailyMarchCapacity
import numpy as np


class HuntTests(unittest.TestCase):
    def test_specific_conflict_warning_cancel_and_scaling(self):
        from wjdr_beast_hunt import match_same_target_conflict
        frame=Image.new('RGB',(1440,2560),(30,50,90))
        with Image.open('tests/fixtures/beast_same_target_dialog.png') as crop:
            frame.paste(crop,(100,820))
        for size in ((720,1280),(1080,1920),(1440,2560)):
            self.assertIsNotNone(match_same_target_conflict(frame.resize(size)))
        frame.paste((180,200,220),(180,1120,1260,1300))
        self.assertIsNone(match_same_target_conflict(frame))

    def test_conflict_cancel_releases_only_verified_same_account_cost(self):
        import tempfile
        import json
        import wjdr_backend as b
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'ledger.json'
            b.reserve_beast_rally_stamina('a',20,path=path)
            b.reserve_beast_rally_stamina('b',25,path=path)
            with self.assertRaises(ValueError):
                b.cancel_beast_rally_conflict_reservation('a',20,path=path)
            with self.assertRaises(ValueError):
                b.cancel_beast_rally_conflict_reservation('a',25,cancelled_and_formation_restored=True,path=path)
            self.assertEqual(b.cancel_beast_rally_conflict_reservation('a',20,cancelled_and_formation_restored=True,path=path),20)
            data=json.loads(path.read_text())['accounts']
            self.assertEqual(data['a']['reserved'],0)
            self.assertEqual(data['a']['spent'],0)
            self.assertEqual(data['b']['reserved'],25)
            with self.assertRaises(ValueError):
                b.cancel_beast_rally_conflict_reservation('a',20,cancelled_and_formation_restored=True,path=path)
    def test_race_pause_requires_explicit_launch_and_is_consumed(self):
        from wjdr_beast_hunt import consume_beast_search_race_pause
        env={'WJDR_BEAST_SEARCH_RACE_PAUSE':'20'}
        self.assertEqual(consume_beast_search_race_pause(env,True),20)
        self.assertEqual(consume_beast_search_race_pause(env,True),0)
        self.assertFalse(env)
        self.assertEqual(consume_beast_search_race_pause({'WJDR_BEAST_SEARCH_RACE_PAUSE':'20'},False),0)
        self.assertEqual(consume_beast_search_race_pause({'WJDR_BEAST_SEARCH_RACE_PAUSE':'999'},True),0)
    def test_cycle_cap_is_launch_only_not_inherited_or_reused(self):
        from wjdr_beast_hunt import consume_beast_test_cycle_limit
        env={'WJDR_BEAST_MAX_CYCLES':'1'}
        self.assertEqual(consume_beast_test_cycle_limit(env,True),1)
        self.assertEqual(consume_beast_test_cycle_limit(env,True),0)
        self.assertNotIn('WJDR_BEAST_MAX_CYCLES',env)
        self.assertEqual(consume_beast_test_cycle_limit({'WJDR_BEAST_MAX_CYCLES':'1'},False),0)
        self.assertEqual(consume_beast_test_cycle_limit({'WJDR_BEAST_MAX_CYCLES':'bad'},True),0)
    def test_green_marching_icon_timer_and_blue_negative(self):
        with Image.open('tests/fixtures/beast_green_marching_row.png') as crop:
            rgb=np.array(crop.convert('RGB'))
        for blue in (False,True):
            candidate=rgb.copy()
            if blue:
                icon=candidate[:,:95]
                green=(icon[:,:,1]>100)&(icon[:,:,0]<100)&(icon[:,:,2]<100)
                icon[green]=(45,128,210)
            frame=Image.new('RGB',(1440,2560),(30,50,90))
            frame.paste(Image.fromarray(candidate),(20,480))
            for size in ((720,1280),(1080,1920),(1440,2560)):
                rows=read_compact_marching_rows(frame.resize(size))
                if blue:
                    self.assertFalse(rows)
                else:
                    self.assertEqual(len(rows),1)
                    self.assertEqual((rows[0].phase,rows[0].seconds),('marching',16))

    def test_only_full_known_blue_rally_list_allows_free_beast(self):
        row=CompactRallyRow('joined',(70,530),60)
        self.assertTrue(only_joined_rallies(DailyMarchCapacity(1,6,1),[row]))
        for used in (2,3):
            allied=[CompactRallyRow('joined',(70,530+120*i),60) for i in range(used)]
            self.assertTrue(only_joined_rallies(DailyMarchCapacity(used,6,1),allied))
        for capacity,rows in [(None,[row]),(DailyMarchCapacity(2,6,1),[row]),
                              (DailyMarchCapacity(1,1,1),[row]),
                              (DailyMarchCapacity(1,6,1),[CompactRallyRow('unknown',(70,530),60)]),
                              (DailyMarchCapacity(1,6,1),[CompactRallyRow('joined',(70,530),60,'returning')])]:
            self.assertFalse(only_joined_rallies(capacity,rows))

    def frame(self, x=1115, selected=False):
        frame = Image.new('RGB', (1440, 2560), (20, 65, 109))
        for name, xy in [('beast_rally_formation_anchor.png', (105, 26)),
                         ('beast_rally_dispatch_label.png', (925, 2360))]:
            with Image.open(Path('assets') / name) as asset:
                frame.paste(asset, xy)
        if selected:
            ImageDraw.Draw(frame).rectangle((x-20, 180, x+100, 285), fill=(240, 195, 45))
        with Image.open('assets/beast_rally_hunt_name.png') as asset:
            frame.paste(asset, (x, 248))
        return frame

    def test_named_team_any_position(self):
        for x in (60, 630, 1115):
            match = match_hunt_formation(self.frame(x))
            self.assertIs(match.state, BeastRallyState.FORMATION)
            self.assertEqual(dict(match.anchors)['hunt'][0], x + 40)

    def test_large_named_team_variant_and_mixed_duplicates(self):
        frame = self.frame(x=650, selected=True)
        frame.paste((240,195,45), (645,245,750,300))
        with Image.open('assets/beast_rally_hunt_name_large.png') as asset:
            frame.paste(asset, (650,247))
        self.assertIs(match_hunt_formation(frame, selected=True).state, BeastRallyState.FORMATION)
        with Image.open('assets/beast_rally_hunt_name.png') as asset:
            frame.paste(asset, (450,248))
        self.assertIs(match_hunt_formation(frame).state, BeastRallyState.UNKNOWN)

    def test_selected_required_before_dispatch(self):
        self.assertIs(match_hunt_formation(self.frame(), selected=True).state, BeastRallyState.UNKNOWN)
        self.assertIs(match_hunt_formation(self.frame(selected=True), selected=True).state, BeastRallyState.FORMATION)

    def test_missing_header_and_duplicate_name_fail(self):
        frame = self.frame()
        frame.paste((20,65,109), (0,0,700,140))
        self.assertIs(match_hunt_formation(frame).state, BeastRallyState.UNKNOWN)
        frame = self.frame()
        with Image.open('assets/beast_rally_hunt_name.png') as asset:
            frame.paste(asset, (450,248))
        self.assertIs(match_hunt_formation(frame).state, BeastRallyState.UNKNOWN)

    def test_one_team_until_busy_then_return(self):
        c = SingleBeastCycle(6)
        self.assertEqual(c.observe(0,6), 'ready')
        c.dispatch()
        self.assertEqual(c.observe(0,6), 'awaiting_dispatch_proof')
        with self.assertRaises(ValueError): c.dispatch()
        self.assertEqual(c.observe(1,6), 'busy')
        self.assertEqual(c.observe(1,6), 'busy')
        self.assertEqual(c.observe(0,6), 'returned')
        self.assertEqual(c.observe(2,6), 'occupied_multiple')
        with self.assertRaises(ValueError): c.observe(0,5)

    def test_sidebar_timer_live_and_allied_exclusion(self):
        frame = Image.new('RGB', (1440,2560), (50,70,110))
        with Image.open('tests/fixtures/beast_hunt_timer.png') as crop:
            frame.paste(crop, (150,745))
            self.assertEqual(read_sidebar_countdown(frame), 123)
            frame = Image.new('RGB', (1440,2560), (50,70,110))
            frame.paste(crop, (150,480))
            self.assertIsNone(read_sidebar_countdown(frame))
            frame.paste(crop, (150,745))
            frame.paste(crop, (150,900))
            self.assertIsNone(read_sidebar_countdown(frame))

    def test_extra_queue_does_not_release_beast(self):
        cycle = SingleBeastCycle(6)
        cycle.dispatch()
        self.assertEqual(cycle.observe(1,6), 'busy')
        self.assertEqual(cycle.observe(2,6), 'occupied_multiple')
        self.assertEqual(cycle.observe(1,6), 'busy')
        self.assertFalse(cycle.returned)
        self.assertEqual(cycle.observe(0,6), 'returned')

    def test_icon_ownership_ignores_opposite_colour_background(self):
        for joined in (False, True):
            frame = self.compact_frame(joined=joined)
            row = read_compact_rally_rows(frame)[0]
            x, y = row.point
            rgb = np.array(frame)
            roi = rgb[y-35:y+45, x-42:x+38]
            yy, xx = np.ogrid[:80,:80]
            outside = (xx-40)**2+(yy-40)**2 > 31**2
            roi[outside] = (20,200,20) if joined else (30,130,240)
            rows = read_compact_rally_rows(Image.fromarray(rgb))
            self.assertEqual(rows[0].owner, 'joined' if joined else 'own')

    def compact_frame(self, joined=False, returning=False):
        frame = Image.new('RGB',(1440,2560),(30,50,90))
        name = 'beast_owner_return_row.png' if returning else 'beast_owner_green_row.png'
        with Image.open(Path('tests/fixtures')/name) as im:
            row=np.array(im.convert('RGB'))
        if joined:
            icon=row[:,:65]
            green=(icon[:,:,1]>100)&(icon[:,:,0]<100)&(icon[:,:,2]<100)
            icon[green]=(45,128,210)
        frame.paste(Image.fromarray(row).resize((356,85)),(35,620))
        return frame

    def test_green_icon_is_own(self):
        rows=read_compact_rally_rows(self.compact_frame())
        self.assertEqual(len(rows),1)
        self.assertEqual(rows[0].owner,'own')
        self.assertEqual(rows[0].seconds,89)

    def test_blue_icon_with_green_bar_is_joined(self):
        rows=read_compact_rally_rows(self.compact_frame(joined=True))
        self.assertEqual(len(rows),1)
        self.assertEqual(rows[0].owner,'joined')

    def test_returning_blue_is_not_joined_rally(self):
        self.assertEqual(read_compact_rally_rows(self.compact_frame(returning=True)),())

    def test_capacity_does_not_prove_ownership(self):
        cycle=SingleBeastCycle(6,require_owner=True)
        cycle.dispatch()
        self.assertEqual(cycle.observe(1,6),'awaiting_dispatch_proof')
        self.assertEqual(cycle.observe(0,6),'awaiting_dispatch_proof')
        cycle.confirm_owned_rally()
        self.assertEqual(cycle.observe(1,6),'busy')
        self.assertEqual(cycle.observe(0,6),'returned')


if __name__ == '__main__': unittest.main()
