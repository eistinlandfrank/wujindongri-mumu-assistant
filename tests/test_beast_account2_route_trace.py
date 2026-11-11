import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

import wjdr_mumu_assistant_qt as qt


class Account2RouteTraceTest(unittest.TestCase):
    def test_only_account_two_creates_anonymous_timing_record(self):
        report = Mock()
        disabled_clock = Mock(side_effect=AssertionError('other accounts must not start a timer'))
        for identity in ('mumu:0:android:abc', 'mumu:5:android:abc', 'mumu:20:android:abc', 'bad'):
            self.assertIsNone(qt.beast_account2_route_trace(identity, report, clock=disabled_clock))
        disabled_clock.assert_not_called()
        clock = Mock(side_effect=[10.0, 10.2, 11.5])
        mark, finish = qt.beast_account2_route_trace('mumu:2:android:private-id', report, clock=clock)
        mark('world_search:before')
        mark('world_search:returned')
        finish()
        message = report.call_args.args[0]
        self.assertIn('world_search:before=0.200s', message)
        self.assertIn('world_search:returned=1.500s', message)
        self.assertNotIn('private-id', message)

    def test_tracing_keeps_navigation_and_dispatch_input_order(self):
        coords = {'world_search': (1, 1), 'beast_card': (2, 2), 'selector_search': (3, 3),
                  'rally_button': (4, 4), 'launch': (5, 5)}
        positions = SimpleNamespace(cached_point=lambda name, image: coords.get(name))
        target = SimpleNamespace(check_active=Mock(), tap=Mock(), screenshot=Mock())
        stop = SimpleNamespace(is_set=Mock(return_value=False), wait=Mock(return_value=False))
        marks = []
        self.assertTrue(qt.beast_cached_six_navigation(object(), positions, target, stop, trace=marks.append))
        with patch.object(qt, 'beast_shield_plus_claim', return_value=True), \
             patch.object(qt, 'reserve_beast_rally_stamina'):
            self.assertTrue(qt.beast_fast_single_shield_dispatch(
                'account', 25, (7, 7), (8, 8), target, stop,
                clear=(6, 6), estimated=True, trace=marks.append))
        self.assertEqual([call.args for call in target.tap.call_args_list],
                         [(1, 1), (2, 2), (3, 3), (4, 4), (5, 5), (6, 6), (7, 7), (8, 8)])
        self.assertEqual(marks[-2:], ['dispatch:before', 'dispatch:returned'])
        target.screenshot.assert_not_called()

    def test_failed_tap_is_recorded_before_but_never_repeated(self):
        coords = {'world_search': (1, 1), 'beast_card': (2, 2), 'selector_search': (3, 3),
                  'rally_button': (4, 4), 'launch': (5, 5)}
        positions = SimpleNamespace(cached_point=lambda name, image: coords.get(name))
        target = SimpleNamespace(check_active=Mock(), tap=Mock(side_effect=[None, RuntimeError('unknown')]))
        stop = SimpleNamespace(is_set=Mock(return_value=False), wait=Mock(return_value=False))
        marks = []
        with self.assertRaises(RuntimeError):
            qt.beast_cached_six_navigation(object(), positions, target, stop, trace=marks.append)
        self.assertEqual([call.args for call in target.tap.call_args_list], [(1, 1), (2, 2)])
        self.assertEqual(marks[-1], 'beast_card:before')
        self.assertNotIn('beast_card:returned', marks)


if __name__ == '__main__':
    unittest.main()
