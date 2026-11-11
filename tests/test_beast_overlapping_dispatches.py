import json
import tempfile
import unittest
from pathlib import Path

from wjdr_backend import reconcile_beast_overlapping_dispatches


class OverlappingDispatchTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / 'ledger.json'
        self.account = {'day': '2026-11-04', 'reserved': 20, 'uncertain': 120,
                        'submitted_pending': 'pending',
                        'submitted_debit': {'token': 'pending', 'amount': 25, 'day': '2026-11-04'}}
        self.save()

    def save(self):
        self.path.write_text(json.dumps({'accounts': {'a': self.account}}), encoding='utf-8')

    def test_preserves_both_unknown_costs_and_is_not_replayable(self):
        reconcile_beast_overlapping_dispatches('a', 20, 'pending', path=self.path)
        data = json.loads(self.path.read_text(encoding='utf-8'))['accounts']['a']
        self.assertEqual((data['reserved'], data['uncertain']), (0, 140))
        self.assertNotIn('submitted_pending', data)
        self.assertEqual(data['last_recovery']['reason'], 'overlapping_dispatches_unknown')
        with self.assertRaises(ValueError):
            reconcile_beast_overlapping_dispatches('a', 20, 'pending', path=self.path)

    def test_changed_or_invalid_records_remain_untouched(self):
        for field, value in [('reserved', 21), ('submitted_pending', 'other'),
                             ('submitted_debit', {'token': 'other', 'amount': 25, 'day': '2026-11-04'})]:
            with self.subTest(field=field):
                original = dict(self.account)
                self.account[field] = value
                self.save()
                before = self.path.read_bytes()
                with self.assertRaises(ValueError):
                    reconcile_beast_overlapping_dispatches('a', 20, 'pending', path=self.path)
                self.assertEqual(self.path.read_bytes(), before)
                self.account = original


if __name__ == '__main__':
    unittest.main()
