import tempfile
import threading
import unittest
import json
import hashlib
from pathlib import Path

from wjdr_beast_supervision import read_intent, set_intent, start_if_unchanged, token_matches, perform_if_current, ManagedBeastSupervisor, has_unresolved_actions, verify_bound_identity
from wjdr_backend import begin_beast_stamina_item_use, confirm_beast_stamina_item_use


class BeastSupervisionIntentTests(unittest.TestCase):
    def test_fresh_identity_discards_cache_and_rejects_changed_or_missing_manager(self):
        class FakeADB:
            def __init__(self, actual, players):
                self.actual, self.available_players = actual, players
                self.device_identities = {"serial": "mumu:5:android:abc123"}
                self.device_boot_ids = {"serial": "old-boot"}
                self.players = ["old"]
            def clone_for_device(self, device):
                self.clone = FakeADB(self.actual, self.available_players)
                return self.clone
            def _manager_players(self):
                return self.available_players
            def device_identity(self, device):
                if self.device_identities or self.device_boot_ids:
                    raise AssertionError("stale identity cache was used")
                return self.actual
        adb = FakeADB("mumu:5:android:abc123", ["fresh"])
        self.assertTrue(verify_bound_identity(adb, "serial", "mumu:5:android:abc123"))
        self.assertEqual(adb.clone.players, ["fresh"])
        adb.actual = "mumu:6:android:abc123"
        self.assertFalse(verify_bound_identity(adb, "serial", "mumu:5:android:abc123"))
        adb.available_players = []
        self.assertFalse(verify_bound_identity(adb, "serial", "mumu:5:android:abc123"))
        self.assertFalse(verify_bound_identity(adb, "serial", "adb:serial"))

    def test_unresolved_actions_preserve_prior_day_reservation_and_budget_debit(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            identity = "mumu:5:android:abc123"
            args = dict(stamina_path=root / "stamina.json", item_path=root / "item.json", config_dir=root)
            self.assertFalse(has_unresolved_actions(identity, **args))
            path = args["stamina_path"]
            def save(reserved=0, uncertain=0):
                path.write_text(json.dumps({"version": 2, "accounts": {identity: {"day": "2020-01-01", "reserved": reserved, "uncertain": uncertain, "spent": 0}}}), encoding="utf-8")
            save(reserved=25)
            self.assertTrue(has_unresolved_actions(identity, **args))
            save(uncertain=25)
            self.assertFalse(has_unresolved_actions(identity, **args))
            self.assertEqual(json.loads(path.read_text(encoding="utf-8"))["accounts"][identity]["uncertain"], 25)
            save(uncertain=-1)
            with self.assertRaises(ValueError):
                has_unresolved_actions(identity, **args)
            save()
            self.assertFalse(has_unresolved_actions(identity, **args))
            save(reserved=-1)
            with self.assertRaises(ValueError):
                has_unresolved_actions(identity, **args)
            path.write_text("{", encoding="utf-8")
            with self.assertRaises(ValueError):
                has_unresolved_actions(identity, **args)

    def test_unresolved_actions_detect_shield_and_item_transaction(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            identity = "mumu:5:android:abc123"
            args = dict(stamina_path=root / "stamina.json", item_path=root / "item.json", config_dir=root)
            marker = root / ("beast_single_shield_plus_pending_" + hashlib.sha256(identity.encode()).hexdigest() + ".marker")
            marker.touch()
            self.assertTrue(has_unresolved_actions(identity, **args))
            marker.unlink()
            token = begin_beast_stamina_item_use(identity, (3, 10), (3, 10), path=args["item_path"])
            self.assertTrue(has_unresolved_actions(identity, **args))
            self.assertTrue(confirm_beast_stamina_item_use(identity, token, (2, 20), (2, 20), path=args["item_path"]))
            self.assertFalse(has_unresolved_actions(identity, **args))

    def test_manager_executes_recoverable_once_and_does_not_replay_on_exit(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "intent.json"
            identity = "mumu:5:android:abc123"
            generation = set_intent(identity, True, path=path)["generation"]
            entered, proceed, finished = threading.Event(), threading.Event(), threading.Event()
            calls = []
            class Lease:
                def release(self): finished.set()
            def run(account, token):
                entered.set()
                self.assertTrue(proceed.wait(2))
                perform_if_current(account, token, lambda: calls.append("input"), path=path)
            supervisor = ManagedBeastSupervisor(lambda _: Lease(), lambda x: x,
                                                lambda _: False, run, path=path)
            supervisor.start()
            try:
                supervisor.register(identity, generation)
                self.assertTrue(supervisor.recover(identity, generation, reason="pre_input_transport"))
                self.assertTrue(entered.wait(2))
                self.assertFalse(supervisor.recover(identity, generation, reason="pre_input_transport"))
                proceed.set()
                self.assertTrue(finished.wait(2))
                self.assertEqual(calls, ["input"])
            finally:
                proceed.set()
                supervisor.close()

    def test_manager_requires_registration_recoverable_reason_and_no_pending(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "intent.json"
            identity = "mumu:9:android:abc123"
            generation = set_intent(identity, True, path=path)["generation"]
            entered = threading.Event()
            reports = []
            class Lease:
                def release(self):
                    reports.append("released")
                    entered.set()
            supervisor = ManagedBeastSupervisor(lambda _: Lease(), lambda x: x, lambda _: True,
                                                lambda *_: self.fail("pending must never run"),
                                                lambda _, msg: reports.append(msg), path=path)
            supervisor.start()
            try:
                self.assertFalse(supervisor.recover(identity, generation, reason="pre_input_transport"))
                supervisor.register(identity, generation)
                self.assertFalse(supervisor.recover(identity, generation, reason="unknown_ack"))
                self.assertTrue(supervisor.recover(identity, generation, reason="pre_input_transport"))
                self.assertTrue(entered.wait(2))
                self.assertTrue(any("未决" in message for message in reports))
            finally:
                supervisor.close()

    def test_manager_rechecks_identity_and_stopped_generation(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "intent.json"
            identity = "mumu:9:android:abc123"
            generation = set_intent(identity, True, path=path)["generation"]
            finished = threading.Event()
            class Lease:
                def release(self): finished.set()
            supervisor = ManagedBeastSupervisor(lambda _: Lease(), lambda _: "mumu:5:android:abc123",
                                                lambda _: False, lambda *_: self.fail("wrong identity"), path=path)
            supervisor.start()
            try:
                supervisor.register(identity, generation)
                self.assertTrue(supervisor.recover(identity, generation, reason="pre_input_transport"))
                self.assertTrue(finished.wait(2))
                set_intent(identity, False, path=path)
                with self.assertRaises(ValueError):
                    supervisor.register(identity, generation)
            finally:
                supervisor.close()

    def test_pending_reconciliation_holds_lease_and_never_runs_input_path(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'intent.json'
            identity = 'mumu:9:android:abc123'
            generation = set_intent(identity, True, path=path)['generation']
            events = []
            class Lease:
                def release(self): events.append('released')
            def identify(account):
                events.append('identified')
                return account
            def reconcile(account, token):
                self.assertEqual((account, token), (identity, generation))
                events.append('reconciled')
            supervisor = ManagedBeastSupervisor(lambda _: Lease(), identify, lambda _: True,
                                                lambda *_: self.fail('must never run'),
                                                path=path, reconcile=reconcile)
            supervisor._run_one(identity, generation)
            self.assertEqual(events, ['identified', 'reconciled', 'released'])
            events.clear()
            supervisor.identify = lambda _: 'wrong-account'
            supervisor._run_one(identity, generation)
            self.assertEqual(events, ['released'])

    def test_stop_serializes_with_input_and_revokes_future_input(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "intent.json"
            identity = "mumu:5:android:abc123"
            generation = set_intent(identity, True, path=path)["generation"]
            entered, release, stopped = threading.Event(), threading.Event(), threading.Event()
            effects = []
            def action():
                entered.set()
                self.assertTrue(release.wait(1))
                effects.append("sent")
            worker = threading.Thread(target=lambda: perform_if_current(identity, generation, action, path=path))
            stopper = threading.Thread(target=lambda: (set_intent(identity, False, path=path), stopped.set()))
            worker.start()
            self.assertTrue(entered.wait(1))
            stopper.start()
            self.assertFalse(stopped.wait(.05))
            release.set()
            worker.join(1)
            stopper.join(1)
            self.assertTrue(stopped.is_set())
            with self.assertRaises(InterruptedError):
                perform_if_current(identity, generation, lambda: effects.append("replayed"), path=path)
            self.assertEqual(effects, ["sent"])

    def test_uncertain_input_is_not_replayed(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "intent.json"
            identity = "mumu:5:android:abc123"
            generation = set_intent(identity, True, path=path)["generation"]
            effects = []
            def unknown():
                effects.append("sent")
                raise TimeoutError("acknowledgement unknown")
            with self.assertRaises(TimeoutError):
                perform_if_current(identity, generation, unknown, path=path)
            self.assertEqual(effects, ["sent"])
    def test_stop_revokes_prior_run_and_other_account_is_isolated(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "intent.json"
            first, second = "mumu:5:android:abc123", "mumu:9:android:abc123"
            self.assertIsNone(read_intent(first, path=path))
            started = set_intent(first, True, path=path)
            set_intent(second, True, path=path)
            self.assertTrue(token_matches(read_intent(first, path=path), started["generation"]))
            stopped = set_intent(first, False, path=path)
            self.assertGreater(stopped["generation"], started["generation"])
            self.assertFalse(token_matches(read_intent(first, path=path), started["generation"]))
            self.assertTrue(token_matches(read_intent(second, path=path), 1))
            restarted = set_intent(first, True, path=path)
            self.assertFalse(token_matches(restarted, started["generation"]))
            self.assertTrue(token_matches(restarted, restarted["generation"]))

    def test_unknown_partial_identity_and_corrupt_data_fail_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "intent.json"
            self.assertFalse(token_matches(None, 1))
            for identity in ("adb:127.0.0.1:16544", "mumu:5", "android:abc123"):
                with self.assertRaises(ValueError):
                    set_intent(identity, True, path=path)
            path.write_text('{"version":1,"accounts":{"mumu:5:android:abc123":{"generation":1,"run":1}}}', encoding="utf-8")
            with self.assertRaises(ValueError):
                read_intent("mumu:5:android:abc123", path=path)
            with self.assertRaises(ValueError):
                set_intent("mumu:5:android:abc123", True, path=path)

    def test_start_setup_cannot_overwrite_a_new_stop_or_other_start(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "intent.json"
            identity = "mumu:5:android:abc123"
            stopped = set_intent(identity, False, path=path)
            self.assertIsNone(start_if_unchanged(identity, None, path=path))
            started = start_if_unchanged(identity, stopped["generation"], path=path)
            self.assertTrue(token_matches(started, started["generation"]))
            set_intent(identity, False, path=path)
            self.assertIsNone(start_if_unchanged(identity, started["generation"], path=path))
            self.assertFalse(read_intent(identity, path=path)["run"])


if __name__ == "__main__":
    unittest.main()
