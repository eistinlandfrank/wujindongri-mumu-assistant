import unittest
import json
import tempfile
from pathlib import Path

from wjdr_backend import DailyMarchCapacity, reconcile_beast_rally_gathering_reservation
from wjdr_beast_hunt import (CompactRallyRow, ConcurrentRallySnapshot,
                             classify_concurrent_rows, confirms_new_concurrent_rally)


def row(owner, y, phase='icon'):
    return CompactRallyRow(owner, (70, y), None, phase)


class ConcurrentRallyTests(unittest.TestCase):
    def test_mixed_gathering_rally_and_march(self):
        icons = (row('gathering', 545), row('gathering', 667),
                 row('own', 789), row('own', 911))
        state = classify_concurrent_rows(DailyMarchCapacity(4, 6, 1), icons,
                                         (row('own', 789, 'rallying'),),
                                         (row('own', 911, 'marching'),))
        self.assertEqual((state.rallies, state.green, state.free), (1, 2, True))

    def test_full_capacity_waits_and_green_must_be_classified(self):
        capacity = DailyMarchCapacity(2, 2, 1)
        icons = (row('gathering', 545), row('own', 667))
        self.assertIsNone(classify_concurrent_rows(capacity, icons, (), ()))
        self.assertFalse(classify_concurrent_rows(capacity, icons, (row('own', 667),), ()).free)
        self.assertIsNone(classify_concurrent_rows(capacity, icons, (row('own', 667),), (row('own', 667),)))
        self.assertIsNone(classify_concurrent_rows(capacity, icons[:1], (), ()))

    def test_hidden_idle_does_not_invent_capacity(self):
        state = classify_concurrent_rows(DailyMarchCapacity(0, 0, 1, 'hidden_idle'), (), (), ())
        self.assertEqual((state.used, state.total, state.free), (0, 0, True))

    def test_new_rally_can_coincide_with_tracked_march_return(self):
        before = ConcurrentRallySnapshot(5, 6, 'numeric', ('gathering',) * 4 + ('marching',))
        after = ConcurrentRallySnapshot(5, 6, 'numeric', ('gathering',) * 4 + ('rallying',))
        self.assertTrue(confirms_new_concurrent_rally(before, after))
        self.assertFalse(confirms_new_concurrent_rally(before, before))
        self.assertFalse(confirms_new_concurrent_rally(before, ConcurrentRallySnapshot(
            4, 6, 'numeric', ('gathering',) * 3 + ('rallying',))))
        self.assertFalse(confirms_new_concurrent_rally(before, ConcurrentRallySnapshot(
            5, 7, 'numeric', ('gathering',) * 4 + ('rallying',))))

    def test_pending_hold_recovers_only_on_two_complete_gathering_snapshots(self):
        idle = ConcurrentRallySnapshot(4, 6, 'numeric', ('gathering',) * 4)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'ledger.json'
            path.write_text(json.dumps({'accounts': {'account': {'day': 'today', 'spent': 50, 'reserved': 25}}}), encoding='utf-8')
            for a, b in ((idle, None), (idle, ConcurrentRallySnapshot(4, 6, 'numeric', ('gathering',)*3 + ('marching',))),
                         (ConcurrentRallySnapshot(4, 4, 'numeric', ('gathering',)*4),)*2,
                         (ConcurrentRallySnapshot(4, 6, 'numeric', ('gathering',)*3),)*2):
                with self.assertRaises(ValueError):
                    reconcile_beast_rally_gathering_reservation('account', a, b, day='today', path=path)
            self.assertEqual(reconcile_beast_rally_gathering_reservation('account', idle, idle, day='today', path=path), 25)
            account = json.loads(path.read_text(encoding='utf-8'))['accounts']['account']
            self.assertEqual((account['reserved'], account['spent'], account['uncertain']), (0, 50, 25))
            self.assertEqual(reconcile_beast_rally_gathering_reservation('account', idle, idle, day='today', path=path), 0)


if __name__ == '__main__':
    unittest.main()
