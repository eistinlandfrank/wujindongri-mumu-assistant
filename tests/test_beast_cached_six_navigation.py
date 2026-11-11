import unittest
from types import SimpleNamespace
from unittest.mock import Mock

from wjdr_mumu_assistant_qt import beast_cached_six_navigation, beast_should_use_cached_six_route


class CachedSixNavigationTest(unittest.TestCase):
    def setUp(self):
        self.points = {'world_search': (1, 1), 'beast_card': (2, 2),
                       'selector_search': (3, 3), 'rally_button': (4, 4),
                       'three_minutes': (5, 5), 'launch': (6, 6)}
        self.positions = SimpleNamespace(cached_point=lambda name, image: self.points.get(name))
        self.target = SimpleNamespace(check_active=Mock(), tap=Mock(), screenshot=Mock())
        self.stop = SimpleNamespace(is_set=Mock(return_value=False), wait=Mock(return_value=False))

    def test_uses_cached_positions_without_screenshots(self):
        self.assertTrue(beast_cached_six_navigation(object(), self.positions, self.target, self.stop))
        self.assertEqual([call.args for call in self.target.tap.call_args_list],
                         [(1, 1), (2, 2), (3, 3), (4, 4), (6, 6)])
        self.assertEqual([call.args for call in self.stop.wait.call_args_list], [(1.0,)] * 5)
        self.target.screenshot.assert_not_called()

    def test_previously_required_three_minutes_is_selected(self):
        self.assertTrue(beast_cached_six_navigation(object(), self.positions, self.target, self.stop,
                                                    select_three=True))
        self.assertEqual([call.args for call in self.target.tap.call_args_list][-2:], [(5, 5), (6, 6)])

    def test_recovered_account_uses_adaptive_transitions_without_screenshots(self):
        for delay in (2.0, 3.0, 4.0):
            with self.subTest(delay=delay):
                self.stop.wait.reset_mock()
                self.assertTrue(beast_cached_six_navigation(object(), self.positions, self.target, self.stop,
                                                            page_wait_seconds=delay))
                self.assertEqual([call.args for call in self.stop.wait.call_args_list], [(delay,)] * 5)
        self.target.screenshot.assert_not_called()

    def test_recovery_delay_is_interruptible_and_invalid_delay_never_taps(self):
        self.stop.wait.side_effect = [False, True]
        self.assertFalse(beast_cached_six_navigation(object(), self.positions, self.target, self.stop,
                                                     page_wait_seconds=2.0))
        self.assertEqual(self.target.tap.call_count, 2)
        self.target.tap.reset_mock()
        with self.assertRaises(ValueError):
            beast_cached_six_navigation(object(), self.positions, self.target, self.stop,
                                        page_wait_seconds=5.0)
        self.target.tap.assert_not_called()

    def test_missing_cache_sends_no_input_and_allows_normal_path(self):
        del self.points['rally_button']
        self.assertIsNone(beast_cached_six_navigation(object(), self.positions, self.target, self.stop))
        self.target.tap.assert_not_called()

    def test_stop_after_first_input_does_not_replay_or_continue(self):
        self.stop.wait.return_value = True
        self.assertFalse(beast_cached_six_navigation(object(), self.positions, self.target, self.stop))
        self.assertEqual([call.args for call in self.target.tap.call_args_list], [(1, 1)])
        self.target.screenshot.assert_not_called()

    def test_stop_during_later_page_transition_is_immediate(self):
        self.stop.wait.side_effect = [False, True]
        self.assertFalse(beast_cached_six_navigation(object(), self.positions, self.target, self.stop))
        self.assertEqual([call.args for call in self.target.tap.call_args_list], [(1, 1), (2, 2)])
        self.assertEqual([call.args for call in self.stop.wait.call_args_list], [(1.0,), (1.0,)])
        self.target.screenshot.assert_not_called()

    def test_failed_input_is_not_retried(self):
        self.target.tap.side_effect = RuntimeError('unknown acknowledgement')
        with self.assertRaises(RuntimeError):
            beast_cached_six_navigation(object(), self.positions, self.target, self.stop)
        self.target.tap.assert_called_once_with(1, 1)

    def test_later_cycle_uses_cache_after_page_recovery(self):
        # Eligibility depends on the recovered current world, not on which
        # page happened to appear in the first frame of this cycle.
        self.assertTrue(beast_should_use_cached_six_route(1, False, 6, 'manual', (1, 0, 0), 0))
        self.assertTrue(beast_should_use_cached_six_route(0, True, 6, 'manual', (1, 0, 0), 0))
        self.assertFalse(beast_should_use_cached_six_route(0, False, 6, 'manual', (1, 0, 0), 0))
        self.assertFalse(beast_should_use_cached_six_route(1, False, 1, 'manual', (1, 0, 0), 0))
        self.assertFalse(beast_should_use_cached_six_route(1, False, 6, 'formation', (1, 0, 0), 0))
        self.assertFalse(beast_should_use_cached_six_route(1, False, 6, 'manual', (1, 0, 0), 20))


if __name__ == '__main__':
    unittest.main()
