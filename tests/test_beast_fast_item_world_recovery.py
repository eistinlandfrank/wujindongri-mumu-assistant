import unittest

from wjdr_mumu_assistant_qt import beast_reconcile_fast_item_world


class FastItemWorldRecoveryTests(unittest.TestCase):
    def run_case(self, *, phase='sent', world=(True, True), network=False,
                 conflict=False, reserved=False, pending=False, stopped=False):
        events = []
        frames = (0, 1)
        result = beast_reconcile_fast_item_world(
            *frames, {'id': 'batch', 'mode': 'fast', 'phase': phase},
            match_world=lambda f: (1, 1) if world[f] else None,
            network=lambda f: network, conflict=lambda f: conflict,
            stable=lambda a, b: bool(a and a == b),
            reserved=lambda: reserved, pending_submission=lambda: pending,
            check_active=lambda: events.append('active'),
            archive_prepared=lambda t: events.append(('prepared', t)),
            archive_sent=lambda t: events.append(('sent', t)),
            stopped=lambda: stopped)
        return result, events

    def test_sent_and_prepared_batches_archive_as_unknown_without_input(self):
        for phase in ('sent', 'prepared'):
            with self.subTest(phase=phase):
                self.assertEqual(self.run_case(phase=phase),
                                 (True, ['active', (phase, 'batch')]))

    def test_unproven_world_or_pending_work_is_not_archived(self):
        for kwargs in ({'world': (True, False)}, {'network': True},
                       {'conflict': True}, {'reserved': True}, {'pending': True},
                       {'stopped': True}, {'phase': 'other'}):
            with self.subTest(**kwargs):
                self.assertEqual(self.run_case(**kwargs), (False, []))


if __name__ == '__main__':
    unittest.main()
