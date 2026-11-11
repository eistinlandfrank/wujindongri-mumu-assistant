import tempfile
import threading
import unittest
from pathlib import Path

from wjdr_beast_hunt import GuardedBeastADB
from wjdr_beast_supervision import (perform_if_current, read_intent, set_intent,
                                    stop_if_current)


class SupervisedInputTests(unittest.TestCase):
    def test_stop_invalidates_all_old_input_and_never_cancels_new_start(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "intent.json"
            identity = "mumu:5:android:abc123"
            old = set_intent(identity, True, path=path)["generation"]
            calls = []
            class Adb:
                device = "serial"
                def tap(self, *point): calls.append(point)
            adb = GuardedBeastADB(Adb(), threading.Event(), lambda _: None)
            adb.input_gate = lambda action: perform_if_current(identity, old, action, path=path)
            adb.tap(1, 2)
            self.assertTrue(stop_if_current(identity, old, path=path))
            with self.assertRaises(InterruptedError): adb.tap(3, 4)
            self.assertEqual(calls, [(1, 2)])
            new = set_intent(identity, True, path=path)["generation"]
            self.assertFalse(stop_if_current(identity, old, path=path))
            self.assertEqual(read_intent(identity, path=path), {"generation": new, "run": True})

    def test_failed_transport_is_marked_before_input_attempt(self):
        class Adb:
            device = "serial"
            def tap(self, *point): raise RuntimeError("unknown acknowledgement")
        adb = GuardedBeastADB(Adb(), threading.Event(), lambda _: None)
        self.assertFalse(adb.input_attempted)
        with self.assertRaises(RuntimeError): adb.tap(1, 2)
        self.assertTrue(adb.input_attempted)

    def test_stop_waits_for_inflight_input_then_blocks_later_inputs(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "intent.json"
            identity = "mumu:5:android:abc123"
            generation = set_intent(identity, True, path=path)["generation"]
            entered, release, stopped = threading.Event(), threading.Event(), threading.Event()
            def operation():
                entered.set()
                self.assertTrue(release.wait(2))
            worker = threading.Thread(target=lambda: perform_if_current(identity, generation, operation, path=path))
            worker.start()
            self.assertTrue(entered.wait(2))
            stopper = threading.Thread(target=lambda: (stop_if_current(identity, generation, path=path), stopped.set()))
            stopper.start()
            self.assertFalse(stopped.wait(.1))
            release.set()
            worker.join(2)
            stopper.join(2)
            self.assertTrue(stopped.is_set())
            with self.assertRaises(InterruptedError):
                perform_if_current(identity, generation, lambda: self.fail("unexpected input"), path=path)


if __name__ == "__main__":
    unittest.main()
