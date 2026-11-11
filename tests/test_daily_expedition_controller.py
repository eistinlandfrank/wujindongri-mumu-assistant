import unittest
import tempfile
from pathlib import Path
from unittest.mock import patch

from wjdr_daily_expedition import ExpeditionClaimLedger, run_expedition_claim


class ExpeditionControllerTests(unittest.TestCase):
    def execute(self, frames, reserve=lambda: True, confirm=lambda: True):
        taps = []
        captured = iter(frames)
        def capture():
            return next(captured)
        def matcher(name):
            return lambda frame: ((10, 20), 1.0) if frame == name else (None, 0.0)
        with patch("wjdr_daily_expedition.expedition_city_entry", matcher("city")), \
             patch("wjdr_daily_expedition.expedition_claim", matcher("chest")), \
             patch("wjdr_daily_expedition.expedition_idle_claim", matcher("idle")), \
             patch("wjdr_daily_expedition.expedition_back", matcher("back")):
            outcome = run_expedition_claim(capture, lambda x, y: taps.append((x, y)),
                lambda: False, lambda _: False, lambda frame: frame == "city",
                lambda frame: (10, 20) if frame == "result" else None,
                reserve, confirm, lambda _: None)
        return outcome, taps

    def test_full_route_and_return(self):
        events = []
        outcome, taps = self.execute([x for x in ("city", "chest", "idle", "result", "back", "city") for _ in range(2)],
            lambda: events.append("reserve") or True, lambda: events.append("confirm") or True)
        self.assertEqual(outcome, "claimed")
        self.assertEqual(len(taps), 5)
        self.assertEqual(events, ["reserve", "confirm"])

    def test_failed_reservation_never_clicks_idle_claim(self):
        outcome, taps = self.execute([x for x in ("city", "chest", "idle") for _ in range(2)], lambda: False)
        self.assertEqual(outcome, "unconfirmed")
        self.assertEqual(len(taps), 2)

    def test_unknown_ack_never_repeats_claim(self):
        outcome, taps = self.execute([x for x in ("city", "chest", "idle", "idle", "idle") for _ in range(2)])
        self.assertEqual(outcome, "unconfirmed")
        self.assertEqual(len(taps), 3)

    def test_ledger_is_isolated_and_pending_survives_restart(self):
        with tempfile.TemporaryDirectory() as folder:
            identity = "mumu:2:android:example"
            ledger = ExpeditionClaimLedger(identity, "2026-11-10", Path(folder))
            self.assertTrue(ledger.reserve())
            self.assertFalse(ExpeditionClaimLedger(identity, "2026-11-11", Path(folder)).available())
            self.assertTrue(ExpeditionClaimLedger("mumu:0:android:other", "2026-11-10", Path(folder)).available())
            self.assertTrue(ledger.confirm())
            self.assertFalse(ExpeditionClaimLedger(identity, "2026-11-10", Path(folder)).available())
            self.assertTrue(ExpeditionClaimLedger(identity, "2026-11-11", Path(folder)).available())


if __name__ == "__main__":
    unittest.main()
