import json
import tempfile
import unittest
from pathlib import Path

import wjdr_backend as backend
from wjdr_mumu_assistant_qt import beast_resume_dispatch_after_stamina


class FastModeTests(unittest.TestCase):
    def test_no_consumption_total_but_submission_guard_survives(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'ledger.json'
            backend.reserve_beast_rally_stamina('a', 25, day='2026-11-04', path=path)
            backend.archive_beast_rally_unconfirmed_reservation(
                'a', 25, record_uncertain=False, day='2026-11-04', path=path)
            account = json.loads(path.read_text(encoding='utf-8'))['accounts']['a']
            self.assertEqual(account.get('uncertain', 0), 0)
            self.assertEqual(account.get('reserved'), 0)
            self.assertNotIn('submitted_debit', account)
            token = backend.load_beast_rally_submitted_pending('a', path=path)
            self.assertTrue(token)
            backend.clear_beast_rally_submitted_pending('a', token, path=path)

    def test_stamina_overlay_returns_to_dispatch_without_back(self):
        actions = []
        ok = beast_resume_dispatch_after_stamina(
            (12, 34), stopped=lambda: False,
            check_active=lambda: actions.append('lease'),
            reserve=lambda: actions.append('guard'),
            tap=lambda p: actions.append(('dispatch', p)),
            archive=lambda: actions.append('submitted'))
        self.assertTrue(ok)
        self.assertEqual(actions, ['lease', 'guard', ('dispatch', (12, 34)), 'submitted'])

    def test_missing_dispatch_position_never_taps(self):
        actions = []
        ok = beast_resume_dispatch_after_stamina(
            None, stopped=lambda: False, check_active=lambda: actions.append('lease'),
            reserve=lambda: actions.append('guard'), tap=lambda p: actions.append(p),
            archive=lambda: actions.append('submitted'))
        self.assertFalse(ok)
        self.assertEqual(actions, [])
