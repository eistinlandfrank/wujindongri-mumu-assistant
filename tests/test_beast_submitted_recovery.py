import tempfile
import unittest
from pathlib import Path

from wjdr_backend import (archive_beast_rally_unconfirmed_reservation,
                          begin_beast_stamina_fast_batch,
                          clear_beast_rally_submitted_pending,
                          load_beast_rally_submitted_pending,
                          load_beast_stamina_item_pending,
                          reserve_beast_rally_stamina)


class SubmittedRecoveryTest(unittest.TestCase):
    def test_pending_survives_restart_and_wrong_account_cannot_consume(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'stamina.json'
            reserve_beast_rally_stamina('a', 25, estimated=True, day='2026-01-01', path=path)
            archive_beast_rally_unconfirmed_reservation('a', 25, day='2026-01-01', path=path)
            token = load_beast_rally_submitted_pending('a', path=path)
            self.assertTrue(token)
            self.assertIsNone(load_beast_rally_submitted_pending('b', path=path))
            for account, supplied in [('b', token), ('a', 'other')]:
                with self.assertRaises(ValueError):
                    clear_beast_rally_submitted_pending(account, supplied, path=path)
            with self.assertRaises(ValueError):
                reserve_beast_rally_stamina('a', 25, day='2026-01-02', path=path)
            self.assertEqual(load_beast_rally_submitted_pending('a', path=path), token)
            clear_beast_rally_submitted_pending('a', token, path=path)
            self.assertIsNone(load_beast_rally_submitted_pending('a', path=path))

    def test_item_guard_precedes_marker_consumption_on_interruption(self):
        with tempfile.TemporaryDirectory() as folder:
            path, items = Path(folder) / 'stamina.json', Path(folder) / 'items.json'
            reserve_beast_rally_stamina('a', 25, day='2026-01-01', path=path)
            archive_beast_rally_unconfirmed_reservation('a', 25, day='2026-01-01', path=path)
            submission = load_beast_rally_submitted_pending('a', path=path)
            item = begin_beast_stamina_fast_batch('a', path=items)
            # Simulated crash before consuming submitted marker: neither a new
            # dispatch nor a second item batch may be started on restart.
            with self.assertRaises(ValueError):
                begin_beast_stamina_fast_batch('a', path=items)
            self.assertEqual(load_beast_stamina_item_pending('a', path=items)['id'], item)
            self.assertEqual(load_beast_rally_submitted_pending('a', path=path), submission)
            clear_beast_rally_submitted_pending('a', submission, path=path)
            with self.assertRaises(ValueError):
                begin_beast_stamina_fast_batch('a', path=items)


if __name__ == '__main__':
    unittest.main()
