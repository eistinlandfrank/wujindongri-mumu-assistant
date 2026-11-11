import unittest

from wjdr_mumu_assistant_qt import beast_reconcile_sent_item_overlay


class NoOcrItemRecoveryTests(unittest.TestCase):
    def run_case(self, *, entry=None, reserved=0, first=None, second=None,
                 after=None, stop=False, lost_lease=False):
        entry = {'id': 'old', 'mode': 'fast', 'phase': 'sent'} if entry is None else entry
        first = {'item': (1, 2), 'close': (3, 4)} if first is None else first
        second = first if second is None else second
        frames = iter(after if after is not None else [{'formation': (5, 6)}] * 2)
        events = []
        def lease():
            events.append('lease')
            if lost_lease:
                raise InterruptedError()
        result = beast_reconcile_sent_item_overlay(
            first, second, entry, match_item=lambda f: f.get('item'),
            close_point=lambda f: f.get('close'), match_formation=lambda f: f.get('formation'),
            network=lambda f: f.get('network', False), stable=lambda a,b: bool(a and a == b),
            reserved=lambda: reserved, check_active=lease, tap=lambda p: events.append(p),
            capture=lambda: next(frames), archive=lambda token: events.append(('archive', token)),
            stopped=lambda: stop)
        return result, events

    def test_only_close_once_then_archive_without_item_use(self):
        result, events = self.run_case()
        self.assertTrue(result)
        self.assertEqual(events, ['lease', (3, 4), 'lease', ('archive', 'old')])

    def test_unproven_input_or_dispatch_reservation_never_touches_page(self):
        for kwargs in ({'entry': {'id': 'x', 'mode': 'fast', 'phase': 'prepared'}},
                       {'reserved': 25}, {'first': {'item': (1, 2), 'close': (3, 4), 'network': True}},
                       {'second': {'item': (9, 2), 'close': (3, 4)}}, {'stop': True}):
            result, events = self.run_case(**kwargs)
            self.assertFalse(result)
            self.assertEqual(events, [])

    def test_unrecognized_after_close_never_archives_or_retries(self):
        result, events = self.run_case(after=[{}, {}])
        self.assertFalse(result)
        self.assertEqual(events, ['lease', (3, 4)])

    def test_lost_lease_never_closes_or_archives(self):
        with self.assertRaises(InterruptedError):
            self.run_case(lost_lease=True)


if __name__ == '__main__':
    unittest.main()
