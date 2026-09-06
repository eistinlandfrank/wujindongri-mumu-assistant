from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from wjdr_backend import (
    BeastRallyProfile,
    beast_rally_stamina_limit_allows,
    load_beast_rally_profile,
    load_beast_rally_stamina_spent,
    load_beast_rally_stamina_reserved,
    record_beast_rally_stamina_spent,
    reserve_beast_rally_stamina,
    confirm_beast_rally_stamina_reservation,
    save_beast_rally_profile,
    reconcile_beast_rally_idle_reservation,
    load_beast_rally_stamina_uncertain,
)


class BeastRallyProfileTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        root = Path(self.directory.name)
        self.profiles = root / "profiles.json"
        self.ledger = root / "ledger.json"

    def tearDown(self):
        self.directory.cleanup()

    def test_default_is_level_eight_and_unlimited(self):
        self.assertEqual(
            load_beast_rally_profile("mumu:1:android:one", self.profiles),
            BeastRallyProfile(8, 0),
        )

    def test_profiles_are_isolated_by_manager_scoped_identity(self):
        first = "mumu:0:android:cloned"
        second = "mumu:2:android:cloned"
        save_beast_rally_profile(first, BeastRallyProfile(9, 100), self.profiles)
        self.assertEqual(load_beast_rally_profile(first, self.profiles), BeastRallyProfile(9, 100))
        self.assertEqual(load_beast_rally_profile(second, self.profiles), BeastRallyProfile(8, 0))

    def test_stamina_ledger_is_daily_and_atomic(self):
        identity = "mumu:1:android:one"
        self.assertEqual(load_beast_rally_stamina_spent(identity, day="2026-08-12", path=self.ledger), 0)
        self.assertEqual(record_beast_rally_stamina_spent(identity, 20, day="2026-08-12", path=self.ledger), 20)
        self.assertEqual(record_beast_rally_stamina_spent(identity, 25, day="2026-08-12", path=self.ledger), 45)
        self.assertEqual(load_beast_rally_stamina_spent(identity, day="2026-08-13", path=self.ledger), 0)
        self.assertEqual(json.loads(self.ledger.read_text(encoding="utf-8"))["version"], 2)

    def test_zero_limit_means_unlimited_and_nonzero_is_preflighted(self):
        self.assertTrue(beast_rally_stamina_limit_allows(1000, 20, 0))
        self.assertTrue(beast_rally_stamina_limit_allows(80, 20, 100))
        self.assertFalse(beast_rally_stamina_limit_allows(81, 20, 100))

    def test_reservation_is_crash_safe_and_finalised_once(self):
        identity = "mumu:2:android:two"
        reserve_beast_rally_stamina(identity, 20, day="2026-08-12", path=self.ledger)
        self.assertEqual(load_beast_rally_stamina_reserved(identity, day="2026-08-12", path=self.ledger), 20)
        self.assertEqual(confirm_beast_rally_stamina_reservation(identity, day="2026-08-12", path=self.ledger), 20)
        self.assertEqual(confirm_beast_rally_stamina_reservation(identity, day="2026-08-12", path=self.ledger), 20)
        self.assertEqual(load_beast_rally_stamina_reserved(identity, day="2026-08-12", path=self.ledger), 0)

    def test_idle_recovery_is_idempotent_and_keeps_uncertain_budget(self):
        key = "mumu:0:android:test"
        opts = {"day": "2026-09-06", "path": self.ledger}
        idle = (True,) * 6
        record_beast_rally_stamina_spent(key, 60, **opts)
        reserve_beast_rally_stamina(key, 20, **opts)
        self.assertEqual(reconcile_beast_rally_idle_reservation(key, idle, idle, **opts), 20)
        self.assertEqual(reconcile_beast_rally_idle_reservation(key, idle, idle, **opts), 0)
        self.assertEqual(load_beast_rally_stamina_spent(key, **opts), 60)
        self.assertEqual(load_beast_rally_stamina_reserved(key, **opts), 0)
        self.assertEqual(load_beast_rally_stamina_uncertain(key, **opts), 20)
        self.assertFalse(beast_rally_stamina_limit_allows(60 + 20, 25, 100))
        reserve_beast_rally_stamina(key, 20, **opts)
        confirm_beast_rally_stamina_reservation(key, **opts)
        self.assertEqual(load_beast_rally_stamina_uncertain(key, **opts), 20)
        self.assertEqual(load_beast_rally_stamina_spent(key, **opts), 80)
        self.assertEqual(load_beast_rally_stamina_uncertain("mumu:1:android:test", **opts), 0)

    def test_recovery_rejects_busy_unknown_mismatch_and_truncated_rows(self):
        key = "mumu:0:android:test"
        opts = {"day": "2026-09-06", "path": self.ledger}
        reserve_beast_rally_stamina(key, 20, **opts)
        idle = (True,) * 6
        for first, second in [(None, None), (idle, (True,) * 5),
                              ((False,) + idle[1:], (False,) + idle[1:]),
                              ((True,) * 5, (True,) * 5)]:
            with self.assertRaises(ValueError):
                reconcile_beast_rally_idle_reservation(key, first, second, **opts)
        self.assertEqual(load_beast_rally_stamina_reserved(key, **opts), 20)
        self.assertEqual(load_beast_rally_stamina_uncertain(key, **opts), 0)


if __name__ == "__main__":
    unittest.main()
