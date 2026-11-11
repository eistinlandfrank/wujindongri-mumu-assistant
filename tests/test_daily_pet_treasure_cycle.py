"""Pet dispatch must follow proved states and never repeat uncertain inputs."""
from pathlib import Path
import sys
from unittest.mock import patch

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import wjdr_backend as b

ROOT = Path(__file__).resolve().parents[1] / "tests" / "fixtures"


def run_scenario(*, stall_after_start=False, reserve_ok=True):
    names = ["checked", "completed", "reward", "completed_close", "unassigned",
             "entry", "start", "active", "back", "city"]
    frames = {name: Image.open(ROOT / f"pet_scene_{name}.png").convert("RGB")
              for name in names if name not in ("reward", "city")}
    frames["reward"] = Image.new("RGB", (1440, 2560), (40, 60, 90))
    frames["city"] = Image.new("RGB", (1440, 2560), (40, 60, 90))
    state = {"index": 0, "taps": [], "reserved": 0, "confirmed": 0}

    def capture():
        return frames[names[state["index"]]]

    def tap(x, y):
        name = names[state["index"]]
        state["taps"].append((name, x, y))
        if not (stall_after_start and name == "start"):
            state["index"] += 1

    def reserve():
        state["reserved"] += 1
        return reserve_ok

    def confirm():
        assert state["reserved"] == 1
        state["confirmed"] += 1
        return True

    def reward(frame, threshold):
        return ((720, 650), 1.0) if frame is frames["reward"] else (None, 0.0)

    def abnormal(frame, threshold):
        if frame is frames["reward"]:
            return b.DailyAbnormalExitMatch(b.DailyAbnormalExitKind.REWARD_TAP_ANYWHERE, (96, 1500), 1.0)
        return b.DailyAbnormalExitMatch(b.DailyAbnormalExitKind.UNKNOWN, None, 0.0)

    def city(frame, threshold):
        return ((74, 2110), 1.0) if frame is frames["city"] else (None, 0.0)

    with patch.object(b, "match_daily_reward_result", reward), \
         patch.object(b, "diagnose_daily_abnormal_exit", abnormal), \
         patch.object(b, "match_daily_city_entry", city):
        outcome = b.run_pet_treasure_cycle(
            capture, tap, lambda: False, lambda _seconds: True,
            reserve, confirm, lambda _message: None,
        )
    return outcome, state


def test_complete_reviewed_route():
    outcome, state = run_scenario()
    assert outcome == "dispatched"
    assert [item[0] for item in state["taps"]] == [
        "checked", "completed", "reward", "completed_close", "unassigned",
        "entry", "start", "active", "back", "city",
    ]
    assert state["reserved"] == state["confirmed"] == 1


def test_unacknowledged_start_is_not_repeated():
    outcome, state = run_scenario(stall_after_start=True)
    assert outcome == "stopped"
    assert [item[0] for item in state["taps"]].count("start") == 1
    assert state["reserved"] == 1 and state["confirmed"] == 0


def test_failed_reservation_never_sends_start():
    outcome, state = run_scenario(reserve_ok=False)
    assert outcome == "unconfirmed"
    assert "start" not in [item[0] for item in state["taps"]]
    assert state["reserved"] == 1 and state["confirmed"] == 0


if __name__ == "__main__":
    test_complete_reviewed_route()
    test_unacknowledged_start_is_not_repeated()
    test_failed_reservation_never_sends_start()
    print("pet cycle and no-repeat checks: PASS")
