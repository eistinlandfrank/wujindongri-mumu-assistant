from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = (ROOT / "wjdr_mumu_assistant_qt.py").read_text(encoding="utf-8")


def test_gather_yield_is_account_scoped_and_survives_a_safe_restart() -> None:
    start = SOURCE.index("deferred_gather_recheck_at: dict")
    end = SOURCE.index("dispatched_gather_kinds:", start)
    state = SOURCE[start:end]

    assert 'daily_gather_defer_{donation_identity}.json' in state
    assert 'state.get("date") != donation_day' in state
    assert "retry_epoch <= epoch_now" in state
    assert "monotonic_now + retry_epoch - epoch_now" in state
    assert "temporary.replace(gather_deferral_state_path)" in state
    assert "def defer_gather_kind" in state
    assert "load_active_gather_deferrals()" in state
    assert "不授权任何地图或出征输入" in state
    assert "restored.append(kind.value)" in state
    assert "restored.append(mission_label(kind))" not in state
    assert SOURCE.index("load_active_gather_deferrals()", start) < SOURCE.index(
        "def mission_label", start
    )

    # Every former in-memory-only assignment now goes through the same
    # account-scoped atomic persistence helper.
    assert "deferred_gather_recheck_at[kind] = time.monotonic() + 5 * 60.0" not in SOURCE
    assert "defer_gather_kind(kind, DAILY_RETRY_LOCK_MAX_SECONDS)" in SOURCE
    assert "DAILY_GATHER_PASSIVE_WAIT_CAP_SECONDS" in SOURCE
    assert 'state.get("natural_queue_kinds", ())' in state
    assert "retry_cap = epoch_now + DAILY_RETRY_LOCK_MAX_SECONDS" in state

    countdown_start = SOURCE.index("def record_active_gather_countdown")
    countdown_end = SOURCE.index("def record_active_training_countdown", countdown_start)
    countdown = SOURCE[countdown_start:countdown_end]
    assert "dispatched_gather_kinds.add(kind)" in countdown
    assert "DAILY_GATHER_PASSIVE_WAIT_CAP_SECONDS" in countdown
    assert "natural_queue=True" in countdown
    assert countdown.index("defer_gather_kind") < countdown.index(
        "daily_gather_remaining_time_crop"
    )


def test_town_render_wait_is_passive_two_frame_and_under_thirty_seconds() -> None:
    assert "DAILY_TOWN_RENDER_PASSIVE_CAP_SECONDS = 29.0" in SOURCE
    start = SOURCE.index("def reopen_daily_tasks_from_gather_world")
    end = SOURCE.index("def yield_gather_search_timeout", start)
    route = SOURCE[start:end]

    assert "deadline = (" in route
    assert "DAILY_TOWN_RENDER_PASSIVE_CAP_SECONDS" in route
    assert 'wait_for_gather_step(\n                    f"{phase}后的每日任务入口"' not in route
    assert route.index("match_reviewed_city_daily_entry(image)") < route.index(
        "match_reviewed_world_town_entry(image)"
    )
    assert "city_streak >= 2" in route
    assert "town_streak >= 2" in route
    assert "reference_size = image.size" in route
    town_wait = route[route.index("DAILY_TOWN_RENDER_PASSIVE_CAP_SECONDS") :]
    assert "city_streak >= 2" in town_wait
    assert "target.fast_window_screenshot(reference_size)" not in town_wait
    assert "image = capture_daily_image()" in town_wait
    assert "MuMu 快速窗口只读失败，改用被动 ADB 复核" not in town_wait
    assert town_wait.index("city_streak >= 2") < town_wait.index(
        "target.tap(*city_point)"
    )
    assert 'target.shell(["input", "keyevent", "4"])' not in town_wait
    assert "Recall" in route
    assert "speed-up" in route


def main() -> None:
    test_gather_yield_is_account_scoped_and_survives_a_safe_restart()
    test_town_render_wait_is_passive_two_frame_and_under_thirty_seconds()
    print("gather deferral persistence regression checks passed")


if __name__ == "__main__":
    main()
