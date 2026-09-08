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
        self=SimpleNamespace(_log_for_device=Mock(), stop_event=threading.Event()),
        time=SimpleNamespace(monotonic=lambda: next(clock)),
        save_evidence=Mock(), wait_for_double=Mock(return_value=('formation', (1, 2), None)),
        exact_formation_match=Mock(), capture=Mock(side_effect=frames),
        read_beast_rally_dispatch_stamina=Mock(return_value=20),
        match_hunt_formation=Mock(return_value=SimpleNamespace(state=BeastRallyState.FORMATION)),
        BeastRallyState=BeastRallyState, identity='account-a',
        load_beast_rally_stamina_reserved=Mock(return_value=20),
        cancel_beast_rally_conflict_reservation=Mock(),
        match_beast_rally_open_button=Mock(return_value=(None, 0)), threshold=.9,
        ensure_wilderness=Mock(return_value=True),
        baseline_march_capacity=(0, 6), SingleBeastCycle=SingleBeastCycle)


class ConflictTransitionTest(unittest.TestCase):
    def test_actual_monitor_waits_for_pair_then_requests_research(self):
        env = context(['transition', 'warning', 'warning', 'formation', 'world', 'world'])
        env['resolve_target_conflict'] = nested('resolve_target_conflict', env)
        self.assertFalse(nested('monitor_single_team', env)())  # not a completed battle
        self.assertTrue(env['retry_target_requested'])
        self.assertEqual(env['target_conflicts'], 1)
        env['target'].tap.assert_called_once_with(420, 1580)
        env['cancel_beast_rally_conflict_reservation'].assert_called_once_with(
            'account-a', 20, cancelled_and_formation_restored=True)
        self.assertEqual(env['capture'].call_count, 6)

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
        self.assertEqual(env['capture'].call_count, 3)  # restoration + known return only


if __name__ == '__main__':
    unittest.main()
