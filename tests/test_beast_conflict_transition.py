"""Exercise actual controller entry with a modal arriving between captures."""
import threading
import unittest
from types import SimpleNamespace
from unittest.mock import Mock
from tests.test_beast_safe_recovery import nested
from wjdr_backend import BeastRallyState
from wjdr_beast_hunt import SingleBeastCycle


def context(frames):
    clock = iter(i / 10 for i in range(100))
    return dict(
        match_same_target_conflict=lambda frame: (420, 1580) if frame == 'warning' else None,
        stable=lambda p, q: bool(p and q and p == q),
        target_conflicts=0, retry_target_requested=False, target=Mock(device='test'),
        profile=SimpleNamespace(beast_level=8, troop_mode='manual'), wanted_troops=(1, 0, 0),
        self=SimpleNamespace(_log_for_device=Mock(), stop_event=threading.Event()),
        time=SimpleNamespace(monotonic=lambda: next(clock)),
        save_evidence=Mock(), wait_for_double=Mock(return_value=('formation', (1, 2), None)),
        exact_formation_match=Mock(return_value=((1, 2), None)), capture=Mock(side_effect=frames),
        read_beast_rally_dispatch_stamina=Mock(return_value=20),
        match_hunt_formation=Mock(return_value=SimpleNamespace(state=BeastRallyState.FORMATION)),
        BeastRallyState=BeastRallyState, identity='account-a',
        load_beast_rally_stamina_reserved=Mock(return_value=20),
        cancel_beast_rally_conflict_reservation=Mock(),
        beast_shield_plus_pending=Mock(return_value=True), beast_shield_plus_confirm=Mock(),
        match_beast_rally_open_button=Mock(return_value=(None, 0)), threshold=.9,
        ensure_wilderness=Mock(return_value=True),
        baseline_march_capacity=(0, 6), SingleBeastCycle=SingleBeastCycle)


class ConflictTransitionTest(unittest.TestCase):
    def test_confirmed_single_shield_conflict_clears_marker_after_release(self):
        env = context(['formation', 'world', 'world'])
        actions = []
        env['cancel_beast_rally_conflict_reservation'].side_effect = lambda *a, **kw: actions.append('release')
        env['beast_shield_plus_confirm'].side_effect = lambda *a: actions.append('clear')
        self.assertTrue(nested('resolve_target_conflict', env)('warning', 'warning'))
        self.assertEqual(actions, ['release', 'clear'])
        env['beast_shield_plus_confirm'].assert_called_once_with('account-a')

    def test_unproven_restoration_keeps_marker(self):
        env = context(['formation'])
        env['wait_for_double'].return_value = None
        self.assertFalse(nested('resolve_target_conflict', env)('warning', 'warning'))
        env['cancel_beast_rally_conflict_reservation'].assert_not_called()
        env['beast_shield_plus_confirm'].assert_not_called()

    def test_conflict_cancellation_does_not_read_stamina(self):
        env = context(['world', 'world'])
        self.assertTrue(nested('resolve_target_conflict', env)('warning', 'warning'))
        env['read_beast_rally_dispatch_stamina'].assert_not_called()
        env['cancel_beast_rally_conflict_reservation'].assert_called_once_with(
            'account-a', 20, cancelled_and_formation_restored=True)

    def test_failed_release_keeps_marker(self):
        env = context(['formation'])
        env['cancel_beast_rally_conflict_reservation'].side_effect = ValueError('ledger mismatch')
        with self.assertRaises(ValueError):
            nested('resolve_target_conflict', env)('warning', 'warning')
        env['beast_shield_plus_confirm'].assert_not_called()

    def test_other_configuration_or_missing_reservation_keeps_marker(self):
        for scenario in ('formation', 'other_troops', 'no_reservation'):
            env = context(['formation', 'world', 'world'])
            if scenario == 'formation':
                env['profile'].troop_mode = 'formation'
            elif scenario == 'other_troops':
                env['wanted_troops'] = (2, 0, 0)
            else:
                env['load_beast_rally_stamina_reserved'].return_value = 0
            self.assertTrue(nested('resolve_target_conflict', env)('warning', 'warning'))
            env['beast_shield_plus_confirm'].assert_not_called()

    def test_actual_monitor_waits_for_pair_then_requests_research(self):
        env = context(['transition', 'warning', 'warning', 'formation', 'world', 'world'])
        env['resolve_target_conflict'] = nested('resolve_target_conflict', env)
        self.assertFalse(nested('monitor_single_team', env)())  # not a completed battle
        self.assertTrue(env['retry_target_requested'])
        self.assertEqual(env['target_conflicts'], 1)
        env['target'].tap.assert_called_once_with(420, 1580)
        env['cancel_beast_rally_conflict_reservation'].assert_called_once_with(
            'account-a', 20, cancelled_and_formation_restored=True)
        self.assertEqual(env['capture'].call_count, 5)

    def test_disappearing_candidate_never_clicks_or_releases(self):
        env = context(['unknown'] * 4)
        self.assertFalse(nested('resolve_target_conflict', env)('warning', 'unknown'))
        self.assertEqual(env['capture'].call_count, 4)
        env['target'].tap.assert_not_called()
        env['cancel_beast_rally_conflict_reservation'].assert_not_called()
        self.assertFalse(env['retry_target_requested'])

    def test_deadline_does_not_keep_capturing(self):
        env = context([])
        env['time'] = SimpleNamespace(monotonic=Mock(side_effect=[0, 5]))
        self.assertFalse(nested('resolve_target_conflict', env)('transition', 'warning'))
        env['capture'].assert_not_called()
        env['target'].tap.assert_not_called()

    def test_stop_after_fresh_match_blocks_cancel(self):
        env = context([])
        def captured():
            env['self'].stop_event.set()
            return 'warning'
        env['capture'].side_effect = captured
        self.assertFalse(nested('resolve_target_conflict', env)('transition', 'warning'))
        env['target'].tap.assert_not_called()
        env['cancel_beast_rally_conflict_reservation'].assert_not_called()

    def test_stable_pair_has_no_extra_confirmation_delay(self):
        env = context(['formation', 'world', 'world'])
        self.assertTrue(nested('resolve_target_conflict', env)('warning', 'warning'))
        self.assertEqual(env['capture'].call_count, 2)  # known return only


if __name__ == '__main__':
    unittest.main()
