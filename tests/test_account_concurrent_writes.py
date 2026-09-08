"""Real OS-process concurrency against temporary files, never live profiles."""
import json
import multiprocessing
import tempfile
import unittest
from pathlib import Path
from wjdr_backend import (BeastRallyProfile, MiningLevelProfile,
    save_beast_rally_profile, save_mining_level_profile,
    reserve_beast_rally_stamina, confirm_beast_rally_stamina_reservation)


def writer(directory, account):
    directory = Path(directory)
    for i in range(12):
        save_beast_rally_profile(account, BeastRallyProfile(stamina_limit=i), directory / "beast.json")
        save_mining_level_profile(account, MiningLevelProfile(mode="manual", manual_level=9), directory / "mining.json")
        reserve_beast_rally_stamina(account, 20, path=directory / "ledger.json")
        confirm_beast_rally_stamina_reservation(account, path=directory / "ledger.json")


class ConcurrentWritesTests(unittest.TestCase):
    def test_four_processes_preserve_all_accounts(self):
        with tempfile.TemporaryDirectory() as directory:
            workers = [multiprocessing.Process(target=writer, args=(directory, f"test-{n}")) for n in range(4)]
            try:
                for worker in workers:
                    worker.start()
                for worker in workers:
                    worker.join(5)
                    self.assertEqual(worker.exitcode, 0)
                for name, key in (("beast", "profiles"), ("mining", "profiles"), ("ledger", "accounts")):
                    data = json.loads((Path(directory) / (name + ".json")).read_text("utf-8"))[key]
                    self.assertEqual(len(data), 4)
                    if name == "ledger":
                        self.assertTrue(all(a["spent"] == 240 and a["reserved"] == 0 for a in data.values()))
                    if name == "beast":
                        self.assertTrue(all(a["stamina_limit"] == 11 for a in data.values()))
            finally:
                for worker in workers:
                    if worker.is_alive():
                        worker.kill()
                    worker.join(1)


if __name__ == "__main__":
    unittest.main()
