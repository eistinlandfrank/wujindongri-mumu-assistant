"""All automation polling uses device pacing capped at 1.5 seconds."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    source = (ROOT / "wjdr_mumu_assistant_qt.py").read_text(encoding="utf-8")
    assert "MAX_SINGLE_WAIT_SECONDS = 1.5" in source
    assert "self.interval_spin.setRange(0.12, MAX_SINGLE_WAIT_SECONDS)" in source
    assert "self.red_packet_interval_spin.setRange(0.12, MAX_SINGLE_WAIT_SECONDS)" in source
    assert "self.daily_interval_spin.setRange(0.0, MAX_SINGLE_WAIT_SECONDS)" in source
    assert "self.daily_interval_spin.setValue(0.0)" in source
    assert "capture_latency_ewma" in source
    assert "capture_latency_ewma * 0.75 + sample * 0.25" in source
    assert "device_cushion = min(0.45, 0.12 + capture_latency_ewma * 0.10)" in source
    assert source.count("max(0.0, min(configured_daily_interval, device_cushion))") >= 2
    assert "def adaptive_operation_wait(" in source
    assert "bounded_maximum = min(MAX_SINGLE_WAIT_SECONDS" in source
    assert "self.stop_event.wait(min(MAX_SINGLE_WAIT_SECONDS, remaining))" in source
    assert "self.stop_event.wait(2)" not in source
    assert "min(3.0, remaining)" not in source
    assert "max(interval, 8.0)" not in source
    assert "max(5.0, min(30.0, interval))" not in source
    assert "max(2.5, interval)" not in source
    assert "min(30.0, max(interval, 1.0)" not in source

    print("adaptive device pacing: PASS")


if __name__ == "__main__":
    main()
