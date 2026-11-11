"""Known-page recovery does not repeat Back or read the level digit."""
import ast
import threading
import unittest
from types import SimpleNamespace
from pathlib import Path
from unittest.mock import patch

from PIL import Image
import wjdr_backend as backend


class DrawerRecognitionTest(unittest.TestCase):
    def test_exploration_requires_both_title_and_arrow_in_place(self):
        with Image.open(backend.resource_path(backend.BUILTIN_BEAST_EXPLORATION_HEADER_ASSET)) as asset:
            header = asset.convert('RGB')
        frame = Image.new('RGB', (1440, 2560), (36, 75, 110))
        frame.paste(header, (0, 0))
        self.assertTrue(backend.match_beast_exception_exploration_header(frame))
        for box in ((0, 0, 150, 145), (150, 0, 340, 145)):
            damaged = frame.copy()
            damaged.paste((36, 75, 110), box)
            self.assertFalse(backend.match_beast_exception_exploration_header(damaged))
        misplaced = Image.new('RGB', (1440, 2560), (36, 75, 110))
        misplaced.paste(header, (400, 400))
        self.assertFalse(backend.match_beast_exception_exploration_header(misplaced))
        self.assertFalse(backend.match_beast_exception_exploration_header(Image.new('RGB', (1440, 2560))))
        scaled = frame.resize((720, 1280), Image.Resampling.BILINEAR)
        self.assertTrue(backend.match_beast_exception_exploration_header(scaled))

    def test_search_and_both_level_field_ends_required_without_ocr(self):
        frame = Image.new('RGB', (1440, 2560), (36, 75, 110))
        with Image.open('assets/beast_rally_search_button.png') as asset:
            frame.paste(asset.convert('RGB'), (430, 2310))
        self.assertIsNone(backend.match_beast_rally_search_drawer_without_level(frame.copy()))
        with Image.open('assets/beast_rally_level_field_8.png') as asset:
            frame.paste(asset.convert('RGB'), (1075, 2020))
        with patch.object(backend, 'read_beast_rally_selector_level', side_effect=AssertionError('OCR called')):
            self.assertIsNotNone(backend.match_beast_rally_search_drawer_without_level(frame.copy()))
        damaged = frame.copy()
        damaged.paste((36, 75, 110), (1290, 2045, 1350, 2095))
        self.assertIsNone(backend.match_beast_rally_search_drawer_without_level(damaged))

    def test_alliance_home_anchor_must_be_in_expected_location(self):
        canvas = Image.new('RGB', (1440, 2560), (36, 75, 110))
        asset_path = backend.resource_path(backend.BUILTIN_MUTUAL_ENTRY_TEMPLATE_ASSET)
        with Image.open(asset_path) as asset:
            icon = asset.convert('RGB')
            valid = canvas.copy()
            valid.paste(icon, (740, 1600))
            wrong_place = canvas.copy()
            wrong_place.paste(icon, (10, 200))
        self.assertIs(backend.detect_alliance_page(valid, .98).page, backend.AlliancePage.ALLIANCE_HOME)
        self.assertIsNot(backend.detect_alliance_page(canvas, .98).page, backend.AlliancePage.ALLIANCE_HOME)
        self.assertIsNot(backend.detect_alliance_page(wrong_place, .98).page, backend.AlliancePage.ALLIANCE_HOME)


class WildernessRecoveryTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        source = Path('wjdr_mumu_assistant_qt.py').read_text(encoding='utf-8')
        tree = ast.parse(source)
        node = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == 'ensure_wilderness')
        module = ast.Module(body=[ast.ImportFrom(module='__future__', names=[ast.alias(name='annotations')], level=0), node], type_ignores=[])
        cls.code = compile(ast.fix_missing_locations(module), '<wilderness-recovery>', 'exec')

    def run_case(self, frames, *, include_delay=False, existing_target=None):
        class Target:
            device = 'test'
            input_attempted = True
            def __init__(self): self.backs = 0
            def check_active(self): pass
            def back(self): self.backs += 1
        class Window:
            stop_event = threading.Event()
            def _log_for_device(self, *args): pass
        class Clock:
            n = 0
            def monotonic(self): self.n += 1; return self.n
        target, clock = existing_target if existing_target is not None else Target(), Clock()
        frames = iter(frames)
        env = {'self': Window(), 'target': target, 'time': clock, 'AUTOMATION_STEP_TIMEOUT_SECONDS': 8,
               'completed_cycles': 1, 'threshold': .9, 'capture': lambda: next(frames, 'unknown'),
               'daily_network_dialog_is_visible': lambda f, t: f == 'network',
               'match_world': lambda f: ((1, 2), 1) if f == 'world' else (None, 0),
               'match_daily_city_wilderness_entry': lambda f, t: (None, 0),
               'match_same_target_conflict': lambda f: f == 'conflict',
               'match_beast_rally_open_button': lambda f, t: ((3, 4), 1) if f == 'card' else (None, 0),
               'match_beast_rally_search_drawer_without_level': lambda f: (5, 6) if f == 'drawer' else None,
               'match_beast_exception_exploration_header': lambda f: f == 'exploration',
               'AlliancePage': backend.AlliancePage,
               'detect_alliance_page': lambda f, t: SimpleNamespace(page={
                   'alliance': backend.AlliancePage.ALLIANCE_HOME,
                   'city': backend.AlliancePage.CITY,
                   'mutual': backend.AlliancePage.MUTUAL_HELP,
               }.get(f, backend.AlliancePage.UNKNOWN)),
               'stable': lambda a, b: bool(a and b and a == b), 'set_state': lambda *_: None,
               'save_evidence': lambda *_: None, 'pause': lambda: False}
        exec(self.code, env)
        result = env['ensure_wilderness']()
        if include_delay:
            return result, target.backs, getattr(target, 'beast_navigation_page_delay', 1.0)
        return result, target.backs

    def test_card_and_drawer_back_once_each_then_world(self):
        result, backs = self.run_case(['card', 'drawer', 'world'])
        self.assertEqual(result, ('world', (1, 2)))
        self.assertEqual(backs, 2)

    def test_unchanged_card_does_not_repeat_back(self):
        result, backs = self.run_case(['card'] * 8)
        self.assertIsNone(result)
        self.assertEqual(backs, 1)

    def test_network_and_unknown_pages_are_not_backed(self):
        for page in ('network', 'unknown', 'conflict', 'city', 'mutual'):
            result, backs = self.run_case([page] * 8)
            self.assertIsNone(result)
            self.assertEqual(backs, 0)

    def test_alliance_home_only_gets_one_back(self):
        result, backs = self.run_case(['alliance', 'world'])
        self.assertEqual(result, ('world', (1, 2)))
        self.assertEqual(backs, 1)
        result, backs = self.run_case(['alliance'] * 8)
        self.assertIsNone(result)
        self.assertEqual(backs, 1)

    def test_exploration_only_gets_one_back(self):
        result, backs = self.run_case(['exploration', 'world'])
        self.assertEqual(result, ('world', (1, 2)))
        self.assertEqual(backs, 1)
        result, backs = self.run_case(['exploration'] * 8)
        self.assertIsNone(result)
        self.assertEqual(backs, 1)

    def test_only_account_that_recovers_known_page_increases_transition_delay(self):
        for page in ('card', 'drawer', 'alliance', 'exploration'):
            result, backs, delay = self.run_case([page, 'world'], include_delay=True)
            self.assertEqual((result, backs, delay), (('world', (1, 2)), 1, 2.0))
        result, backs, delay = self.run_case(['world'], include_delay=True)
        self.assertEqual((result, backs, delay), (('world', (1, 2)), 0, 1.0))

    def test_repeated_recoveries_increase_once_per_episode_and_cap_at_four(self):
        target = SimpleNamespace(device='test', input_attempted=True, backs=0)
        target.check_active = lambda: None
        target.back = lambda: setattr(target, 'backs', target.backs + 1)
        episodes = [(['card', 'drawer', 'world'], 2, 2.0),
                    (['alliance', 'world'], 3, 3.0),
                    (['alliance', 'world'], 4, 4.0),
                    (['alliance', 'world'], 5, 4.0)]
        for frames, total_backs, expected_delay in episodes:
            with self.subTest(expected_delay=expected_delay, total_backs=total_backs):
                result, backs, delay = self.run_case(frames, existing_target=target, include_delay=True)
                self.assertEqual((result, backs, delay), (('world', (1, 2)), total_backs, expected_delay))
        # A separate account worker starts at the default, even after the first
        # has reached its cap.
        self.assertEqual(self.run_case(['world'], include_delay=True)[2], 1.0)


if __name__ == '__main__':
    unittest.main()
