"""A failed camp or exhausted donation window must not block later tasks."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    source = (ROOT / "wjdr_mumu_assistant_qt.py").read_text(encoding="utf-8")

    help_transition_start = source.index("if not alliance_help_checked:")
    help_transition_end = source.index(
        "activity = estimate_daily_activity_progress", help_transition_start
    )
    help_transition = source[help_transition_start:help_transition_end]
    assert "daily_tab_tapped = False" in help_transition
    assert "transition_deadline = time.monotonic() + 16.0" in help_transition
    assert "time.sleep(16" not in help_transition
    assert "stop_event.wait(16" not in help_transition

    helper_start = source.index("def recover_failed_training_from_proven_city")
    helper_end = source.index("def reopen_daily_tasks_from_gather_world", helper_start)
    helper = source[helper_start:helper_end]
    assert helper.count("match_daily_city_entry(") == 2
    assert "stable(first_point, second_point)" in helper
    assert "failed_training_kinds.add(kind)" in helper
    assert "save_failed_training_kinds()" in helper
    assert "target.tap(*second_point)" in helper
    assert 'target.shell(["input", "keyevent", "4"])' not in helper

    shield_start = source.index("shield_mission = next(")
    auxiliary_start = source.index("auxiliary_training = next(", shield_start)
    shield = source[shield_start:auxiliary_start]
    assert "and item.kind not in failed_training_kinds" in shield
    assert shield.index("recover_failed_training_from_proven_city(") < shield.index(
        'set_state("盾兵普通训练路线未完整确认'
    )

    gather_start = source.index("missions = match_daily_gather_missions", auxiliary_start)
    auxiliary = source[auxiliary_start:gather_start]
    auxiliary_candidate = auxiliary.split("None,", 1)[0]
    assert "and item.kind not in deferred_auxiliary_training" in auxiliary_candidate
    assert "and item.kind not in failed_training_kinds" in auxiliary_candidate
    assert "and auxiliary_training.kind not in failed_training_kinds" not in auxiliary
    assert auxiliary.index("recover_failed_training_from_proven_city(") < auxiliary.index(
        'set_state(f"{label}普通训练路线未完整确认'
    )

    donation_start = source.index("def daily_donation_is_deferred")
    donation_end = source.index("building_upgrade_started = False", donation_start)
    donation = source[donation_start:donation_end]
    assert "alliance_donation_retry_at > now" in donation
    assert "alliance_donation_window_clicks = 0" in donation
    assert "仅恢复一次普通粮食可用性复查" in donation
    assert 'daily_training_skip_{donation_identity}.json' in source
    assert 'daily_training_queue_{donation_identity}.json' in source
    assert "failed_training_kinds = load_failed_training_kinds()" in source
    assert "load_active_training_deferrals()" in source
    assert "successful_training_retry_epoch[kind] = time.time() + 8 * 60.0" in source
    assert source.index("successful_training_retry_epoch[kind] = time.time() + 8 * 60.0") < source.index(
        "save_active_training_deferrals()",
        source.index("successful_training_retry_epoch[kind] = time.time() + 8 * 60.0"),
    )
    assert "deferred_auxiliary_training.add(kind)" in source
    assert "deferred_training_recheck_at[kind] = (" in source
    assert "temporary.replace(training_queue_state_path)" in source
    assert '"kinds": sorted(kind.value for kind in failed_training_kinds)' in source
    assert 'retry_at = float(state.get("retry_at", 0.0))' in source
    assert "retry_at > time.time()" in source
    assert "time.time() + DAILY_RETRY_LOCK_MAX_SECONDS" in source
    assert "failed_training_retry_epoch = time.time() + 30 * 60.0" not in source
    assert '"retry_at": failed_training_retry_epoch' in source
    assert "temporary.replace(training_skip_state_path)" in source
    # Only a genuinely failed route that is double-confirmed back at the city
    # persists a <=30-second skip. Collecting a completed Spear/Archer queue
    # and returning to the city must not consume another-batch eligibility.
    assert source.count("save_failed_training_kinds()") >= 2
    assert "gather_cards_suppressed_until = 0.0" in source
    capacity_start = source.index("def confirm_daily_free_march_capacity")
    capacity_end = source.index("def wait_for_natural_gather_return", capacity_start)
    capacity = source[capacity_start:capacity_end]
    assert "gather_cards_suppressed_until = (" in capacity
    assert "DAILY_RETRY_LOCK_MAX_SECONDS" in capacity
    assert "本轮仅屏蔽全部采集卡 30 秒并继续后续独立任务" in capacity
    assert "本轮 60 秒屏蔽全部采集卡" not in capacity
    assert "return None" in capacity
    gather_plan_start = source.index("def run_gather_plan")
    gather_plan_end = source.index("def set_daily_training_quantity_to_max", gather_plan_start)
    gather_plan = source[gather_plan_start:gather_plan_end]
    hub_start = source.index("def recover_gather_world_from_task_hub", capacity_end)
    hub_end = source.index("def recover_gather_world_from_proven_city", hub_start)
    hub = source[hub_start:hub_end]
    assert "daily_growth_task_daily_tab" in hub
    assert "daily_chapter_header" in hub
    assert "match_daily_city_wilderness_entry" in hub
    assert hub.index("target.tap(*daily_tab_point)") < hub.index("target.tap(*close_point)")
    assert hub.index("target.tap(*close_point)") < hub.index("target.tap(*wilderness_point)")
    assert "dispatch" not in hub.lower()
    city_start = hub_end
    city_end = source.index("def run_gather_plan", city_start)
    city = source[city_start:city_end]
    assert "match_daily_city_entry(image, threshold)" in city
    assert "page.state is DailyTaskState.BLOCKED" in city
    assert "match_daily_city_wilderness_entry(" in city
    assert city.index("match_daily_city_entry(image, threshold)") < city.index(
        "match_daily_city_wilderness_entry("
    )
    assert "wait_for_gather_step(" in city
    assert "record_documented_daily_evidence(" in city
    assert city.count("target.tap(*wilderness_point)") == 1
    assert "match_daily_gather_world_search" in city
    before_wilderness_tap = city.split("target.tap(*wilderness_point)", 1)[0]
    assert "daily_gather_search_point" not in before_wilderness_tap
    assert "daily_gather_resource_tab_point" not in before_wilderness_tap
    assert "max(interval, 0.20)" in gather_plan
    assert "max(2.5, interval)" not in gather_plan
    early_city = gather_plan.index("if recover_gather_world_from_proven_city(label):")
    early_hub = gather_plan.index("elif recover_gather_world_from_task_hub(label):")
    first_world_stage = gather_plan.index('"世界地图搜索入口"')
    assert early_city < early_hub
    assert early_hub < first_world_stage
    assert "前往后已从双帧确认的主城进入荒野" in gather_plan
    first_world_failure = gather_plan[gather_plan.index('"世界地图搜索入口"') :]
    assert 'f"{label}采集前往转场失败让行"' in first_world_failure
    assert "defer_gather_kind(kind, DAILY_RETRY_LOCK_MAX_SECONDS)" in first_world_failure
    assert "失败让行 30 秒并继续后续独立任务" in first_world_failure
    assert first_world_failure.index("reopen_daily_tasks_from_gather_world") < first_world_failure.index(
        "return True"
    )
    assert "已在前往后的稳定窗口恢复任务中心误导航" in gather_plan
    resource_preflight = gather_plan[gather_plan.index("if resource_level is None:") :]
    assert "if not establish_world_resource_level():" in resource_preflight
    assert "recover_gather_world_from_task_hub(label)" in resource_preflight
    assert "任务中心误导航已恢复" in resource_preflight
    assert "defer_gather_kind(kind, DAILY_RETRY_LOCK_MAX_SECONDS)" in resource_preflight
    assert 'f"{label}采矿区域预检让行"' in resource_preflight
    assert "采矿区域预检未确认；失败让行 30 秒并继续后续独立项目" in resource_preflight
    assert "capacity_status is None" in gather_plan
    capacity_unknown = gather_plan[gather_plan.index("if not capacity_status:") :]
    assert "defer_gather_kind(kind, DAILY_RETRY_LOCK_MAX_SECONDS)" in capacity_unknown
    assert 'f"{label}采集容量未确认让行"' in capacity_unknown
    assert "失败让行 30 秒并继续后续独立项目" in capacity_unknown
    assert capacity_unknown.index("reopen_daily_tasks_from_gather_world") < capacity_unknown.index("return True")
    assert "reopen_daily_tasks_from_gather_world" in gather_plan
    assert "已回到每日任务并继续后续独立项目" in gather_plan
    formation_start = source.index("def wait_for_gather_formation_capacity")
    formation_end = source.index("def establish_world_resource_level", formation_start)
    formation = source[formation_start:formation_end]
    assert 'return (\n                                    "insufficient",' in formation
    assert formation.index("streak >= 2") < formation.index('"insufficient"')
    insufficient = gather_plan[gather_plan.index('formation_status == "insufficient"') :]
    iron_stop = insufficient.index("kind is DailyMissionKind.GATHER_IRON")
    exact_back = insufficient.index('target.shell(["input", "keyevent", "4"])')
    assert iron_stop < exact_back
    assert "按用户规则立即暂停，未点击出征" in insufficient
    assert "DAILY_RETRY_LOCK_MAX_SECONDS" in insufficient
    assert "DAILY_GATHER_PASSIVE_WAIT_CAP_SECONDS" not in insufficient
    assert "本次负重不足只让行 30 秒并继续后续任务" in insufficient
    assert insufficient.index("reopen_daily_tasks_from_gather_world") < insufficient.index(
        "return True"
    )
    gather_scan = source[source.index("if time.monotonic() < gather_cards_suppressed_until", gather_plan_end) :]
    assert "missions = ()" in gather_scan
    assert "暂时屏蔽全部采集卡，继续后续独立任务" in gather_scan
    print("continue later tasks: PASS")


if __name__ == "__main__":
    main()
