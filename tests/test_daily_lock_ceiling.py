"""Daily failure/yield/retry locks must never hide work for over 30 seconds."""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = (ROOT / "wjdr_mumu_assistant_qt.py").read_text(encoding="utf-8")


def test_one_shared_thirty_second_lock_ceiling_covers_retry_policies() -> None:
    assert "DAILY_RETRY_LOCK_MAX_SECONDS = 30.0" in SOURCE
    for assignment in (
        "DAILY_DONATION_WINDOW_RETRY_SECONDS = DAILY_RETRY_LOCK_MAX_SECONDS",
        "DAILY_DONATION_UNAVAILABLE_RETRY_SECONDS = DAILY_RETRY_LOCK_MAX_SECONDS",
        "DAILY_IDLE_FALLBACK_RETRY_SECONDS = DAILY_RETRY_LOCK_MAX_SECONDS",
        "DAILY_IDLE_STATIC_REFRESH_RETRY_SECONDS = DAILY_RETRY_LOCK_MAX_SECONDS",
    ):
        assert assignment in SOURCE

    assert "failed_training_retry_epoch = (\n                    time.time() + DAILY_RETRY_LOCK_MAX_SECONDS" in SOURCE
    assert "failed_training_retry_epoch = time.time() + 30 * 60.0" not in SOURCE
    assert "gather_cards_suppressed_until = time.monotonic() + 5 * 60.0" not in SOURCE
    assert "defer_gather_kind(kind, 5 * 60.0)" not in SOURCE

    donation_helper = SOURCE[
        SOURCE.index("def defer_daily_donation") : SOURCE.index(
            "def daily_donation_is_deferred"
        )
    ]
    assert "min(" in donation_helper
    assert "DAILY_RETRY_LOCK_MAX_SECONDS" in donation_helper

    gather_helper = SOURCE[
        SOURCE.index("def defer_gather_kind") : SOURCE.index(
            "load_active_gather_deferrals()", SOURCE.index("def defer_gather_kind")
        )
    ]
    assert "if natural_queue:" in gather_helper
    assert "delay = min(delay, DAILY_RETRY_LOCK_MAX_SECONDS)" in gather_helper


def test_process_lifetime_failure_flags_have_expiring_deadlines() -> None:
    contracts = (
        ("intel_route_attempted", "intel_route_retry_at"),
        ("building_upgrade_unavailable", "building_upgrade_retry_at"),
        ("training_route_attempted", "training_route_retry_at"),
    )
    for flag, deadline in contracts:
        assert f"{deadline} = 0.0" in SOURCE
        assert f"time.monotonic() >= {deadline}" in SOURCE or f"now >= {deadline}" in SOURCE
        assert f"{deadline} = (" in SOURCE
        assert "DAILY_RETRY_LOCK_MAX_SECONDS" in SOURCE[
            SOURCE.index(f"{deadline} = (") : SOURCE.index(f"{deadline} = (") + 180
        ]

    startup_donation = SOURCE[
        SOURCE.index("if not active_food_point:") : SOURCE.index(
            "transition_deadline = time.monotonic() + 8.0",
            SOURCE.index("if not active_food_point:"),
        )
    ]
    assert "alliance_donation_unavailable = True" in startup_donation
    assert "defer_daily_donation(" in startup_donation
    assert "DAILY_RETRY_LOCK_MAX_SECONDS" in startup_donation


def test_persisted_legacy_failure_epochs_are_migrated_not_renewed() -> None:
    assert "donation_retry_cap = time.time() + DAILY_RETRY_LOCK_MAX_SECONDS" in SOURCE
    assert "alliance_donation_retry_at = donation_retry_cap" in SOURCE
    assert "training_failure_retry_cap = (" in SOURCE
    assert "temporary.replace(training_skip_state_path)" in SOURCE

    gather_state = SOURCE[
        SOURCE.index("natural_gather_queue_kinds:") : SOURCE.index(
            "dispatched_gather_kinds:", SOURCE.index("natural_gather_queue_kinds:")
        )
    ]
    assert 'state.get("natural_queue_kinds", ())' in gather_state
    assert "retry_cap = epoch_now + DAILY_RETRY_LOCK_MAX_SECONDS" in gather_state
    assert '"natural_queue_kinds": sorted(' in gather_state
    assert "save_active_gather_deferrals()" in gather_state


def test_business_expiry_deadlines_remain_distinct_from_failure_locks() -> None:
    assert "DAILY_WAREHOUSE_SUPPLY_RETRY_SECONDS = 3 * 60" in SOURCE
    assert "DAILY_HERO_FREE_RECRUIT_RETRY_SECONDS = 5 * 60" in SOURCE
    assert "successful_training_retry_epoch[kind] = time.time() + 8 * 60.0" in SOURCE

    countdown = SOURCE[
        SOURCE.index("def record_active_gather_countdown") : SOURCE.index(
            "def record_active_training_countdown"
        )
    ]
    assert "DAILY_GATHER_PASSIVE_WAIT_CAP_SECONDS" in countdown
    assert "natural_queue=True" in countdown

    insufficient = SOURCE[
        SOURCE.index('formation_status == "insufficient"') : SOURCE.index(
            'formation_status != "ready"'
        )
    ]
    assert "DAILY_RETRY_LOCK_MAX_SECONDS" in insufficient
    assert "DAILY_GATHER_PASSIVE_WAIT_CAP_SECONDS" not in insufficient


def main() -> None:
    test_one_shared_thirty_second_lock_ceiling_covers_retry_policies()
    test_process_lifetime_failure_flags_have_expiring_deadlines()
    test_persisted_legacy_failure_epochs_are_migrated_not_renewed()
    test_business_expiry_deadlines_remain_distinct_from_failure_locks()
    print("daily lock ceiling regression checks: PASS")


if __name__ == "__main__":
    main()
