from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from wjdr_backend import (
    MiningLevelProfile,
    initial_mining_resource_level,
    load_mining_level_profile,
    save_mining_level_profile,
)


class MiningLevelProfileTests(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.path = Path(self.temporary_directory.name) / "mining-level-profiles.json"

    def tearDown(self):
        self.temporary_directory.cleanup()

    def test_profiles_are_mutually_exclusive_and_persist_per_android_id(self):
        low = "android:low-account"
        high = "android:high-account"

        self.assertEqual(
            load_mining_level_profile(low, self.path),
            MiningLevelProfile("auto", 5),
        )

        save_mining_level_profile(low, MiningLevelProfile("manual", 7), self.path)
        save_mining_level_profile(high, MiningLevelProfile("auto", 9), self.path)

        self.assertEqual(
            load_mining_level_profile(low, self.path),
            MiningLevelProfile("manual", 7),
        )
        self.assertEqual(
            load_mining_level_profile(high, self.path),
            MiningLevelProfile("auto", 9),
        )
        self.assertEqual(
            json.loads(self.path.read_text(encoding="utf-8"))["version"],
            1,
        )

    def test_distinct_mumu_instances_with_cloned_android_id_do_not_share_profile(self):
        stable_identity_from_25600 = "mumu:0:android:a195ab448b7cd5ab"
        stable_identity_from_25664 = "mumu:2:android:a195ab448b7cd5ab"

        save_mining_level_profile(
            stable_identity_from_25600,
            MiningLevelProfile("manual", 3),
            self.path,
        )

        self.assertEqual(
            load_mining_level_profile(stable_identity_from_25600, self.path),
            MiningLevelProfile("manual", 3),
        )
        self.assertEqual(
            load_mining_level_profile(stable_identity_from_25664, self.path),
            MiningLevelProfile("auto", 5),
        )

    def test_manager_scoped_identity_reads_legacy_profile_until_saved(self):
        legacy = "android:2d003489914050ce"
        scoped = "mumu:1:android:2d003489914050ce"
        save_mining_level_profile(
            legacy,
            MiningLevelProfile("manual", 5),
            self.path,
        )
        self.assertEqual(
            load_mining_level_profile(scoped, self.path),
            MiningLevelProfile("manual", 5),
        )

        save_mining_level_profile(
            scoped,
            MiningLevelProfile("manual", 7),
            self.path,
        )
        self.assertEqual(
            load_mining_level_profile(scoped, self.path),
            MiningLevelProfile("manual", 7),
        )
        self.assertEqual(
            load_mining_level_profile(legacy, self.path),
            MiningLevelProfile("manual", 5),
        )

    def test_invalid_profile_is_rejected(self):
        for profile in (("both", 5), ("manual", 0), ("manual", 10)):
            with self.subTest(profile=profile):
                with self.assertRaises(ValueError):
                    MiningLevelProfile(*profile)

    def test_manual_level_is_immediate_while_auto_requests_recognition(self):
        for level in range(1, 10):
            with self.subTest(level=level):
                self.assertEqual(
                    initial_mining_resource_level(MiningLevelProfile("manual", level)),
                    level,
                )
        self.assertIsNone(
            initial_mining_resource_level(MiningLevelProfile("auto", 9))
        )


if __name__ == "__main__":
    unittest.main()
