import tempfile
import unittest
from pathlib import Path

from wjdr_backend import BeastRallyProfile, load_beast_rally_profile, save_beast_rally_profile
from wjdr_mumu_assistant_qt import beast_should_use_cached_six_route, beast_cached_six_navigation


class BeastSpeedModeTests(unittest.TestCase):
    def test_mode_is_per_account_and_old_profile_defaults_to_normal(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'profiles.json'
            save_beast_rally_profile('first', BeastRallyProfile(run_mode='fast'), path)
            save_beast_rally_profile('second', BeastRallyProfile(), path)
            self.assertEqual(load_beast_rally_profile('first', path).run_mode, 'fast')
            self.assertEqual(load_beast_rally_profile('second', path).run_mode, 'normal')
            self.assertEqual(load_beast_rally_profile('third', path).run_mode, 'normal')

    def test_cached_route_in_fast_mode_also_works_with_one_team_cap(self):
        self.assertTrue(beast_should_use_cached_six_route(1, False, 1, 'manual', (1, 0, 0), 0, fast_mode=True))
        self.assertFalse(beast_should_use_cached_six_route(1, False, 1, 'manual', (1, 0, 0), 0))
        self.assertFalse(beast_should_use_cached_six_route(1, False, 1, 'formation', (1, 0, 0), 0, fast_mode=True))

    def test_fast_navigation_uses_cached_positions_once(self):
        class Positions:
            def cached_point(self, name, image):
                return (10, 20)
        class Target:
            def __init__(self): self.taps = []
            def check_active(self): pass
            def tap(self, *point): self.taps.append(point)
        class Stop:
            def __init__(self): self.waits = []
            def is_set(self): return False
            def wait(self, seconds): self.waits.append(seconds); return False
        target, stop = Target(), Stop()
        self.assertTrue(beast_cached_six_navigation(None, Positions(), target, stop, page_wait_seconds=0.1))
        self.assertEqual(len(target.taps), 5)
        self.assertEqual(stop.waits, [0.1] * 5)


if __name__ == '__main__':
    unittest.main()
