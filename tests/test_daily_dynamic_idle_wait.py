"""Static contract for deadline-driven Daily idle scheduling."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    source = (ROOT / "wjdr_mumu_assistant_qt.py").read_text(encoding="utf-8")
    assert "DAILY_IDLE_FALLBACK_RETRY_SECONDS = DAILY_RETRY_LOCK_MAX_SECONDS" in source
    assert "DAILY_IDLE_STATIC_REFRESH_RETRY_SECONDS = DAILY_RETRY_LOCK_MAX_SECONDS" in source

    helper = source[
        source.index("def daily_idle_wait_plan(") : source.index(
            "def wait_for_gather_step("
        )
    ]
    for deadline in (
        "warehouse_supply_recheck_at",
        "hero_recruit_recheck_at",
        "alliance_donation_retry_at",
        "deferred_training_recheck_at.values()",
        "gather_cards_suppressed_until",
        "active_gather_recheck_at",
        "inherited_gather_recheck_at",
        "deferred_gather_recheck_at.values()",
    ):
        assert deadline in helper
    assert "min(retry_candidates, key=lambda item: item[0])" in helper
    assert "if deadline > monotonic_now:" in helper
    assert "if deadline > epoch_now:" in helper
    assert "max(0.0, deadline - monotonic_now)" not in helper
    assert "max(0.0, deadline - epoch_now)" not in helper
    assert "idle_wait_seconds = 30.0" not in helper

    completed_zone = source[
        source.index("if daily_completed_zone_wait_after_top:") : source.index(
            "set_state(\"已用两次轻量像素比对确认列表顶部，立即扫描首项\")"
        )
    ]
    assert "daily_idle_wait_plan(image, 0.0, 0.0)" in completed_zone
    assert "time.monotonic() + 30.0" not in completed_zone
    assert "保持零输入 30 秒" not in source


if __name__ == "__main__":
    main()
    print("daily dynamic idle scheduling checks: PASS")
