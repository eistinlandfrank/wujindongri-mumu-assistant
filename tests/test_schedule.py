import multiprocessing
import tempfile
import unittest
from pathlib import Path
import wjdr_schedule as s

A = "mumu:0:android:test-a"
B = "mumu:2:android:test-b"


def claim_process(path):
    s.claim_due(A, now=100, path=Path(path))


class ScheduleTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / "schedule.json"

    def tearDown(self):
        self.temp.cleanup()

    def add(self, identity=A, at=100):
        return s.add_job(identity, "adb-test", "测试手机", at, now=1, path=self.path)

    def test_future_only_and_stable_identity(self):
        for identity, at in ((A, 0), ("adb:port", 100)):
            with self.assertRaises(ValueError):
                self.add(identity, at)

    def test_due_not_early_and_exactly_once_after_reload(self):
        self.add()
        self.assertIsNone(s.claim_due(A, now=99.99, path=self.path))
        claimed = s.claim_due(A, now=100, path=self.path)
        self.assertIsNotNone(claimed)
        self.assertIsNone(s.claim_due(A, now=100, path=self.path))
        self.assertEqual(s.read_jobs(self.path)[0]["state"], "claimed")

    def test_separate_account_not_wrong_port(self):
        self.add()
        self.assertIsNone(s.claim_due(B, now=100, path=self.path))
        self.assertIsNotNone(s.claim_due(A, now=100, path=self.path))

    def test_busy_skips_without_interrupting(self):
        self.add()
        self.assertIsNone(s.claim_due(A, busy=True, now=100, path=self.path))
        self.assertEqual(s.read_jobs(self.path)[0]["state"], "skipped")

    def test_sleep_or_late_restart_does_not_catch_up(self):
        self.add()
        self.assertIsNone(s.claim_due(A, now=131, path=self.path))
        self.assertEqual(s.read_jobs(self.path)[0]["state"], "missed")

    def test_crashed_claim_is_not_replayed(self):
        self.add()
        s.claim_due(A, now=100, path=self.path)
        self.assertIsNone(s.claim_due(A, now=131, path=self.path))
        self.assertEqual(s.read_jobs(self.path)[0]["state"], "failed")

    def test_cancel_during_verification_blocks_start(self):
        self.add()
        job = s.claim_due(A, now=100, path=self.path)
        self.assertTrue(s.cancel_job(job["id"], path=self.path))
        self.assertFalse(s.transition(job["id"], job["token"], "running", "", path=self.path))

    def test_tokens_and_terminal_states(self):
        self.add()
        job = s.claim_due(A, now=100, path=self.path)
        self.assertFalse(s.transition(job["id"], "wrong", "running", "", path=self.path))
        self.assertTrue(s.transition(job["id"], job["token"], "running", "", path=self.path))
        self.assertFalse(s.cancel_job(job["id"], path=self.path))
        self.assertTrue(s.transition(job["id"], job["token"], "finished", "", path=self.path))
        self.assertFalse(s.transition(job["id"], job["token"], "running", "", path=self.path))

    def test_duplicate_job_rejected(self):
        self.add()
        with self.assertRaises(ValueError):
            self.add(at=101)

    def test_clear_preserves_pending_and_running(self):
        self.add()
        self.add(B)
        job = s.claim_due(A, now=100, path=self.path)
        s.transition(job["id"], job["token"], "running", "", path=self.path)
        s.clear_history(path=self.path)
        self.assertEqual(len(s.read_jobs(self.path)), 2)

    def test_four_windows_can_only_claim_once(self):
        self.add()
        processes = [multiprocessing.Process(target=claim_process, args=(str(self.path),)) for _ in range(4)]
        try:
            for p in processes:
                p.start()
            for p in processes:
                p.join(4)
                self.assertEqual(p.exitcode, 0)
            job = s.read_jobs(self.path)[0]
            token = job["token"]
            self.assertEqual(job["state"], "claimed")
            self.assertIsNone(s.claim_due(A, now=100, path=self.path))
            self.assertEqual(s.read_jobs(self.path)[0]["token"], token)
        finally:
            for p in processes:
                if p.is_alive():
                    p.kill()
                p.join(1)

    def test_corrupt_file_fails_closed(self):
        self.path.write_text("bad", encoding="utf-8")
        with self.assertRaises(ValueError):
            s.claim_due(A, now=100, path=self.path)

    def test_global_emergency_cancels_all_unstarted_jobs(self):
        self.add()
        self.add(B)
        job = s.claim_due(A, now=100, path=self.path)
        s.cancel_waiting(path=self.path)
        self.assertTrue(all(j["state"] == "cancelled" for j in s.read_jobs(self.path)))
        self.assertFalse(s.transition(job["id"], job["token"], "running", "", path=self.path))


if __name__ == "__main__":
    unittest.main()
