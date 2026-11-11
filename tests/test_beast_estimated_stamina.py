import tempfile
import unittest
from pathlib import Path

from wjdr_backend import (reserve_beast_rally_stamina,
                          archive_beast_rally_unconfirmed_reservation,
                          confirm_beast_rally_stamina_reservation,
                          load_beast_rally_stamina_uncertain,
                          load_beast_rally_stamina_reserved_any_day)


class EstimatedStaminaTest(unittest.TestCase):
    def test_unconfirmed_reservation_is_archived_once_and_not_cross_account(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'ledger.json'
            reserve_beast_rally_stamina('a', 25, estimated=True, day='2026-11-04', path=path)
            for identity, amount in [('b', 25), ('a', 20)]:
                with self.assertRaises(ValueError):
                    archive_beast_rally_unconfirmed_reservation(identity, amount, day='2026-11-04', path=path)
            self.assertEqual(load_beast_rally_stamina_reserved_any_day('a', path=path), 25)
            self.assertEqual(archive_beast_rally_unconfirmed_reservation('a', 25, day='2026-11-04', path=path), 25)
            self.assertEqual(load_beast_rally_stamina_uncertain('a', day='2026-11-04', path=path), 25)
            with self.assertRaises(ValueError):
                archive_beast_rally_unconfirmed_reservation('a', 25, day='2026-11-04', path=path)

    def test_estimate_goes_to_uncertain_not_confirmed_spend(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'ledger.json'
            reserve_beast_rally_stamina('a', 25, estimated=True, day='2026-11-04', path=path)
            self.assertEqual(confirm_beast_rally_stamina_reservation('a', day='2026-11-04', path=path), 0)
            self.assertEqual(load_beast_rally_stamina_uncertain('a', day='2026-11-04', path=path), 25)
            self.assertEqual(load_beast_rally_stamina_reserved_any_day('a', path=path), 0)
            self.assertEqual(confirm_beast_rally_stamina_reservation('a', day='2026-11-04', path=path), 0)
            self.assertEqual(load_beast_rally_stamina_uncertain('a', day='2026-11-04', path=path), 25)

    def test_known_cost_and_next_estimate_are_distinct(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'ledger.json'
            reserve_beast_rally_stamina('a', 20, day='2026-11-04', path=path)
            self.assertEqual(confirm_beast_rally_stamina_reservation('a', day='2026-11-04', path=path), 20)
            reserve_beast_rally_stamina('a', 25, estimated=True, day='2026-11-04', path=path)
            self.assertEqual(confirm_beast_rally_stamina_reservation('a', day='2026-11-04', path=path), 20)
            self.assertEqual(load_beast_rally_stamina_uncertain('a', day='2026-11-04', path=path), 25)

    def test_estimated_reservation_survives_new_day(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'ledger.json'
            reserve_beast_rally_stamina('a', 25, estimated=True, day='2026-11-04', path=path)
            with self.assertRaises(ValueError):
                reserve_beast_rally_stamina('a', 25, estimated=True, day='2026-11-05', path=path)
            self.assertEqual(load_beast_rally_stamina_reserved_any_day('a', path=path), 25)


if __name__ == '__main__':
    unittest.main()
