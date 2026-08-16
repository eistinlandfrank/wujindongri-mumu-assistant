from __future__ import annotations

import unittest
from pathlib import Path


class ManualMiningBypassContractTests(unittest.TestCase):
    def test_manual_profile_sets_level_before_auto_overview_guard(self):
        source = (
            Path(__file__).resolve().parents[1] / "wjdr_mumu_assistant_qt.py"
        ).read_text(encoding="utf-8")

        load_index = source.index(
            "resource_level = initial_mining_resource_level(mining_level_profile)"
        )
        guard_index = source.index("if resource_level is None:", load_index)
        auto_call_index = source.index("establish_world_resource_level()", guard_index)

        self.assertLess(load_index, guard_index)
        self.assertLess(guard_index, auto_call_index)
        self.assertIn("完全跳过地球、小房子和绿色城堡识图", source[load_index:guard_index])

    def test_castle_gate_keeps_manual_level_message_truthful(self):
        source = (
            Path(__file__).resolve().parents[1] / "wjdr_mumu_assistant_qt.py"
        ).read_text(encoding="utf-8")
        gate = source[source.index("if not level_verified:") :]

        self.assertIn('if mining_level_profile.mode == "manual":', gate)
        self.assertIn("本账号采矿固定 Lv.{resource_level}，不执行自动区域判定", gate)

    def test_profile_return_has_a_route_specific_passive_deadline(self):
        source = (
            Path(__file__).resolve().parents[1] / "wjdr_mumu_assistant_qt.py"
        ).read_text(encoding="utf-8")
        gate = source[source.index("if not level_verified:") : source.index("blocked_state =", source.index("if not level_verified:"))]
        profile_return = gate[gate.index("profile_back_point =") : gate.index("if mining_level_profile.mode")]

        self.assertIn("DAILY_PROFILE_RETURN_PASSIVE_CAP_SECONDS = 16.0", source)
        self.assertIn("+ DAILY_PROFILE_RETURN_PASSIVE_CAP_SECONDS", profile_return)
        self.assertNotIn("time.sleep", profile_return)
        self.assertIn("(75, 75)", profile_return)
        self.assertIn("target.tap(*profile_back_point)", profile_return)
        self.assertNotIn("target.back()", profile_return)


if __name__ == "__main__":
    unittest.main()
