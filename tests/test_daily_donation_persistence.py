"""Donation totals and the 25-click availability window survive restarts."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    source = (ROOT / "wjdr_mumu_assistant_qt.py").read_text(encoding="utf-8")
    assert "target.device_identity()" in source
    assert 'daily_donation_{donation_identity}.json' in source
    assert 'state.get("date") == donation_day' in source
    assert "DAILY_DONATION_TASK_TARGET = 40" in source
    assert "DAILY_DONATION_WINDOW_CAP = 25" in source
    assert "DAILY_DONATION_WINDOW_RETRY_SECONDS = DAILY_RETRY_LOCK_MAX_SECONDS" in source
    assert "donation_retry_cap = time.time() + DAILY_RETRY_LOCK_MAX_SECONDS" in source
    assert 'state.get("window_confirmed", confirmed)' in source
    assert 'state.get("retry_at", 0.0)' in source
    assert '"window_confirmed": max(' in source
    assert '"retry_at": max(' in source
    assert "temporary.replace(donation_state_path)" in source
    assert "alliance_donation_confirmed_clicks >= DAILY_DONATION_TASK_TARGET" in source
    assert "alliance_donation_window_clicks = 0" in source
    assert "daily_donation_is_deferred()" in source
    assert "alliance_donation_batches" not in source
    hold = source.index('"1200",')
    disabled = source.index("disabled_streak >= 2", hold)
    exhausted = source.index(
        "alliance_donation_window_clicks = DAILY_DONATION_WINDOW_CAP", disabled
    )
    defer = source.index("defer_daily_donation(DAILY_DONATION_WINDOW_RETRY_SECONDS)", exhausted)
    assert hold < disabled < exhausted < defer
    assert '"10000",' not in source
    assert "本轮不允许第二段，30 秒后仅复查可用性" in source
    print("daily donation persistence: PASS")


if __name__ == "__main__":
    main()
