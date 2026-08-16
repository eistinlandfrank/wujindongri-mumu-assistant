from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from wjdr_mumu_assistant_qt import (
    AUTOMATION_STEP_TIMEOUT_SECONDS,
    DAILY_TOWN_RENDER_PASSIVE_CAP_SECONDS,
    MAX_SINGLE_WAIT_SECONDS,
    bounded_step_timeout,
)


SOURCE = ROOT / "wjdr_mumu_assistant_qt.py"


def test_one_action_timeout_is_hard_capped_at_thirty_seconds() -> None:
    # The internal watchdog leaves ADB/classifier headroom so total wall time
    # still stays under the user's hard 30-second ceiling.
    assert AUTOMATION_STEP_TIMEOUT_SECONDS == 24.0
    assert bounded_step_timeout(0.8) == 0.8
    assert bounded_step_timeout(24) == 24.0
    assert bounded_step_timeout(30) == 24.0
    assert bounded_step_timeout(31) == 24.0
    assert bounded_step_timeout(6 * 60) == 24.0
    assert AUTOMATION_STEP_TIMEOUT_SECONDS < DAILY_TOWN_RENDER_PASSIVE_CAP_SECONDS < 30.0


def test_daily_idle_policy_uses_chunked_no_input_deadline() -> None:
    source = SOURCE.read_text(encoding="utf-8")
    assert MAX_SINGLE_WAIT_SECONDS == 1.5
    assert "idle_no_input_until =" in source
    assert "self.stop_event.wait(min(MAX_SINGLE_WAIT_SECONDS, remaining))" in source
    assert "min(AUTOMATION_STEP_TIMEOUT_SECONDS, remaining)" not in source
    assert "stop_event.wait(max(idle_wait_seconds" not in source


def test_route_and_manual_step_timeouts_use_the_shared_cap() -> None:
    source = SOURCE.read_text(encoding="utf-8")
    assert "time.monotonic() + bounded_step_timeout(timeout)" in source
    assert "bounded_step_timeout(float(step[\"seconds\"]))" in source
    assert re.search(
        r"bounded_step_timeout\(\s*float\(step\.get\(\"timeout\", 15\)\)\s*\)",
        source,
    )

    explicit_deadlines = [
        float(value)
        for value in re.findall(
            r"deadline\s*=\s*time\.monotonic\(\)\s*\+\s*([0-9]+(?:\.[0-9]+)?)",
            source,
        )
    ]
    assert all(value <= AUTOMATION_STEP_TIMEOUT_SECONDS for value in explicit_deadlines)


def main() -> None:
    test_one_action_timeout_is_hard_capped_at_thirty_seconds()
    test_daily_idle_policy_uses_chunked_no_input_deadline()
    test_route_and_manual_step_timeouts_use_the_shared_cap()
    print("automation step timeout regression checks passed")


if __name__ == "__main__":
    main()
