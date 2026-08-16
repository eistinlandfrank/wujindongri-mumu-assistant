from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = (ROOT / "wjdr_mumu_assistant_qt.py").read_text(encoding="utf-8")


def test_failed_training_backoff_expires_inside_the_same_process() -> None:
    state = SOURCE[
        SOURCE.index("failed_training_retry_epoch = 0.0") : SOURCE.index(
            "def load_active_training_deferrals"
        )
    ]
    assert "failed_training_retry_epoch = retry_at" in state
    assert "training_failure_retry_cap" in state
    assert "DAILY_RETRY_LOCK_MAX_SECONDS" in state
    assert "def refresh_failed_training_kinds" in state
    refresh = state[state.index("def refresh_failed_training_kinds") :]
    assert "failed_training_retry_epoch > time.time()" in refresh
    assert "failed_training_kinds.clear()" in refresh
    assert "training_skip_state_path.unlink(missing_ok=True)" in refresh

    scan = SOURCE[
        SOURCE.index("# A natural training queue may run") : SOURCE.index(
            "shield_mission = next("
        )
    ]
    assert scan.index("refresh_failed_training_kinds()") < scan.index(
        "training_missions ="
    )


def test_idle_scheduler_wakes_at_failed_training_retry() -> None:
    idle = SOURCE[
        SOURCE.index("def daily_idle_wait_plan") : SOURCE.index(
            "def wait_for_gather_step"
        )
    ]
    assert "failed_training_retry_epoch if failed_training_kinds else 0.0" in idle
    assert '"训练失败复查"' in idle
