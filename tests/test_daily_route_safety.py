"""Regression checks for the reviewed, task-driven Daily gathering route."""

import sys
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from wjdr_backend import (  # noqa: E402
    AlliancePage,
    DAILY_GATHER_FULL_NODE_MIN_RETURN_SECONDS,
    DAILY_GATHER_PASSIVE_WAIT_CAP_SECONDS,
    DAILY_GATHER_SAFE_RESOURCE_LEVEL,
    DAILY_TASK_LIST_BOUNDARY_CONFIRMATIONS,
    DAILY_TASK_LIST_BOUNDARY_MAX_MEAN_CHANGE,
    DAILY_TASK_LIST_GESTURE_X,
    DAILY_TASK_LIST_MAX_SCAN_SWIPES,
    DailyMissionKind,
    DailyTaskState,
    alliance_tech_tree_viewport_mean_change,
    daily_gather_full_resources_filter_is_enabled,
    daily_gather_remaining_time_crop,
    daily_gather_route_meets_required_amount,
    daily_gather_march_is_active,
    daily_task_list_viewport_mean_change,
    daily_hero_recruit_result_is_visible,
    match_daily_activity_chest_open,
    match_daily_task_refresh_label,
    match_daily_alliance_donate_mission,
    match_daily_alliance_tech_battle_tab_strip,
    match_daily_alliance_tech_development_tab_strip,
    match_daily_alliance_tech_territory_tab_strip,
    match_daily_hero_recruit_mission,
    match_daily_research_tech_mission,
    match_daily_gather_full_resources_filter_off,
    detect_alliance_page,
    detect_daily_task_state,
    match_daily_city_entry,
    match_daily_gather_world_search,
    match_daily_growth_task_daily_tab,
    match_daily_world_town_entry,
    match_daily_training_active,
    match_daily_training_missions,
    match_daily_training_spear_tutorial_entry,
)


def main() -> None:
    source = Path("wjdr_mumu_assistant_qt.py").read_text(encoding="utf-8")
    backend_source = Path("wjdr_backend.py").read_text(encoding="utf-8")
    assert DAILY_GATHER_SAFE_RESOURCE_LEVEL == 5
    assert DAILY_TASK_LIST_MAX_SCAN_SWIPES == 12
    assert DAILY_TASK_LIST_BOUNDARY_CONFIRMATIONS == 2
    assert DAILY_TASK_LIST_BOUNDARY_MAX_MEAN_CHANGE == 0.7
    assert DAILY_TASK_LIST_GESTURE_X == 900
    inventory = ROOT / "evidence" / "milestone-07-task-inventory"
    moving_before = Image.open(inventory / "inventory-00-private.png")
    moving_after = Image.open(inventory / "inventory-01-private.png")
    bottom_before = Image.open(inventory / "scroll-00-private.png")
    bottom_after = Image.open(inventory / "inventory-06-private.png")
    assert (
        daily_task_list_viewport_mean_change(moving_before, moving_after)
        > DAILY_TASK_LIST_BOUNDARY_MAX_MEAN_CHANGE
    )
    assert (
        daily_task_list_viewport_mean_change(bottom_before, bottom_after)
        <= DAILY_TASK_LIST_BOUNDARY_MAX_MEAN_CHANGE
    )
    assert DAILY_GATHER_PASSIVE_WAIT_CAP_SECONDS == 3 * 60 * 60
    assert DAILY_GATHER_FULL_NODE_MIN_RETURN_SECONDS == 10 * 60
    assert daily_gather_route_meets_required_amount(DailyMissionKind.GATHER_IRON, 5, True)
    assert daily_gather_route_meets_required_amount(DailyMissionKind.GATHER_IRON, 7, True)
    assert daily_gather_route_meets_required_amount(DailyMissionKind.GATHER_IRON, 9, True)
    assert not daily_gather_route_meets_required_amount(DailyMissionKind.GATHER_IRON, 5, False)
    assert not daily_gather_route_meets_required_amount(DailyMissionKind.GATHER_IRON, 4, True)
    assert "resource_level: int | None = None" in source
    assert "def establish_world_resource_level()" in source
    assert "match_daily_world_overview_entry" in source
    assert "match_daily_world_overview_resource_off" in source
    assert "daily_world_overview_resource_is_enabled" in source
    assert "detect_world_resource_level" in source
    assert "DAILY_GATHER_PASSIVE_WAIT_CAP_SECONDS" in source
    assert "DAILY_GATHER_FULL_NODE_MIN_RETURN_SECONDS" in source
    assert "采集无法证明资源点不少于任务所需" in source
    assert "deadline = time.monotonic() + 20 * 60.0" not in source
    assert "区域预检在 30 秒内未获得资源勾选、绿色城堡坐标与一致的 5/7/9" in source
    overview_section = source.split("def establish_world_resource_level()", 1)[1].split(
        "def confirm_daily_free_march_capacity", 1
    )[0]
    assert "match_daily_world_overview_search_entry" in overview_section
    assert "match_daily_world_overview_home_button" in overview_section
    assert "等待绿色城堡坐标进入主地图" in overview_section
    assert "def match_reviewed_gather_search(" in source
    assert "world_point, _world_score = match_reviewed_gather_search(image)" in source
    assert "search_streak >= 2" in overview_section
    assert "直接继续且不发送返回键" in overview_section
    assert "target.back()" not in overview_section
    # These were fixed-coordinate kingdom-overview taps.  In the current
    # MuMu world layout the first opens Intel, so Daily Tasks must never emit
    # them outside a positively matched task route.
    assert "map_content_point((1290, 1990)" not in source
    assert "zone_probe_stage" not in source
    assert "DAILY_IDLE_FALLBACK_RETRY_SECONDS = DAILY_RETRY_LOCK_MAX_SECONDS" in source
    assert "DAILY_IDLE_STATIC_REFRESH_RETRY_SECONDS = DAILY_RETRY_LOCK_MAX_SECONDS" in source
    assert "def daily_idle_wait_plan(" in source
    assert "idle_wait_seconds = 30.0" not in source
    assert "检测到刷新倒计时" in source
    assert "daily_list_reset_pending = True" in source
    assert "daily_task_list_viewport_mean_change" in source
    assert "每日任务列表顶部已由连续两次无位移滑动确认" in source
    assert "每日任务已从双重确认顶部扫描到双重确认底部" in source
    assert "BUILTIN_DAILY_MISSION_HERO_RECRUIT_1_ASSET" in backend_source
    assert "BUILTIN_DAILY_MISSION_ALLIANCE_DONATE_5_ASSET" in backend_source
    assert "_match_daily_mission_go_control" in backend_source
    assert "DAILY_DONATION_TASK_TARGET = 40" in source
    assert "DAILY_DONATION_WINDOW_CAP = 25" in source
    assert "DAILY_DONATION_WINDOW_RETRY_SECONDS = DAILY_RETRY_LOCK_MAX_SECONDS" in source
    assert "DAILY_DONATION_UNAVAILABLE_RETRY_SECONDS = DAILY_RETRY_LOCK_MAX_SECONDS" in source
    assert '"1200",' in source
    assert '"10000",' not in source
    assert "timeout=3" in source
    assert "1200ms 长按" in source
    assert "disabled_streak >= 2" in source
    assert "post_blue_streak >= 2" in source
    assert "alliance_donation_window_clicks = DAILY_DONATION_WINDOW_CAP" in source
    assert "for index in range(batch_remaining) if stage else ():" not in source
    assert "alliance_donation_batches" not in source
    assert "段后两帧仍蓝且无法证明联盟币变化时绝不连按" in source
    assert "alliance_donation_confirmed_clicks >= DAILY_DONATION_TASK_TARGET" in source
    assert "具体增长由每日任务页复核" in source
    assert source.count("training_route_attempted = True") == 2
    assert "if training_route_attempted" in source
    assert "训练卡片仅让行 30 秒并继续独立任务，未作恢复点击" in source
    shield_start = source.index("if shield_mission:")
    shield_end = source.index("auxiliary_training = next(", shield_start)
    shield_flow = source[shield_start:shield_end]
    assert shield_flow.index("if not run_shield_training_plan():") < shield_flow.index(
        "training_route_attempted = True"
    )
    auxiliary_card_start = source.index("if auxiliary_training:")
    auxiliary_card_end = source.index("missions = match_daily_gather_missions", auxiliary_card_start)
    auxiliary_card_flow = source[auxiliary_card_start:auxiliary_card_end]
    assert auxiliary_card_flow.index("if not run_auxiliary_training_plan") < auxiliary_card_flow.index(
        "training_route_attempted = True"
    )
    assert auxiliary_card_flow.index("failure_page.state in daily_failure_states") < auxiliary_card_flow.index(
        "training_route_attempted = True"
    )
    assert "仅切换到战斗标签" in source
    assert "match_daily_alliance_tech_battle_tab_strip" in source
    assert "scan_battle_for_sustain_node" in source
    assert "顶部静止确认 {top_stationary_streak}/2" in source
    assert "底部静止确认 {bottom_stationary_streak}/2" in source
    assert "达到 12 次顶部复位上限但没有边界证明" in source
    assert "达到 12 次向下扫描上限但没有边界证明" in source
    assert "record_battle_evidence" in source
    assert "milestone-10-battle-sustain-v476" in source
    assert "仅切换到发展标签" not in source
    assert "startup_alliance_tech_return_streak" in source
    assert "已从双帧确认的联盟科技" in source
    assert "未点击任何科技节点" in source
    assert "startup_alliance_return_stage = 1" in source
    assert "hero_recruit_unavailable = False" in source
    assert "hero_recruit_unavailable = True" in source
    assert "if hero_recruit_unavailable" in source
    assert "startup_hero_recruit_return_streak" in source
    assert "hero_recruit_recheck_at = time.time() +" in source
    assert "绿色免费招募" in source
    assert "alliance_donation_unavailable = False" in source
    assert source.count("alliance_donation_unavailable = True") >= 3
    assert "startup_alliance_donation_return_streak" in source
    assert "alliance_donation_confirmed_clicks >= DAILY_DONATION_TASK_TARGET" in source
    assert "daily_donation_is_deferred()" in source
    assert "30 秒后仅复查可用性" in source
    assert "def set_daily_training_quantity_to_max" in source
    assert "daily_training_quantity_slider_points(image)" in source
    assert "daily_training_quantity_is_maxed(image)" in source
    assert '["input", "swipe", str(handle[0])' in source
    assert 'target.shell(["input", "text", "10"])' not in source
    assert source.count("set_daily_training_quantity_to_max(") == 3
    assert "def finish_training_camp_double_enter" in source
    assert source.count("finish_training_camp_double_enter(") == 3
    assert "第二次点击刚才受证的兵营" in source
    assert "At most one additional camp tap" in source
    assert "def daily_training_quantity_slider_points" in backend_source
    assert "def daily_training_quantity_is_maxed" in backend_source
    assert "map_content_point((720, 1200), BUILTIN_DAILY_TASK_REFERENCE_SIZE, screenshot)" in backend_source
    assert "def record_active_training_countdown" in source
    assert "def defer_active_training_and_reopen_daily" in source
    assert "training_countdowns" in source
    assert "不加速、不重复训练，继续其他每日事项" in source
    assert "deferred_training_recheck_at" in source
    assert "failed_training_kinds" in source
    assert "def recover_failed_training_from_proven_city" in source
    assert "仅让行{label} 30 秒并继续后续任务" in source
    assert source.count("recover_failed_training_from_proven_city(") == 3
    assert "time.monotonic() + 8 * 60.0" in source
    assert "share(quantity_lane, quantity_green) >= 0.002" in backend_source
    assert "daily_hero_recruit_result_exit_point" not in source
    assert "每日奖励扫描完成：已领取" not in source
    assert "等级预检：已关闭双帧确认的每日任务页" in source
    assert "daily_task_close_point(image)" in source
    assert "等级预检：点击已双帧确认的每日任务标签" in source
    assert "This tab switch belonged solely to the" in source
    assert "record_active_gather_countdown" in source
    assert "deadline = time.monotonic() + 12.0" in source
    assert "matched_frames >= 2" in source
    assert "active_gather_kind" in source
    assert source.count("march_capacity_back_streak") >= 3
    assert source.count("inherited_gather_slot_active") >= 3
    assert source.count("active_selector_recovery_streak") >= 3
    assert "继续处理不占行军队列的每日事项" in source
    assert "{phase}后已直接重开每日任务" in source
    assert "def confirm_daily_free_march_capacity" in source
    assert "read_daily_march_capacity" in source
    assert "read_daily_gather_formation_capacity" in source
    assert "仅授权本进程唯一一次引导派遣" in source
    assert "formation.selected_troops <= 0" in source
    assert "formation.carrying_capacity < required_amount" in source
    assert "if item.kind not in dispatched_gather_kinds" in source
    assert "gather_recheck_candidates" in source
    assert "DailyTaskState.TASK_CLAIM_READY" in source
    assert "等待关联奖励页或已知每日页稳定显示" in source
    assert "活跃度宝箱已双帧识图为打开状态；跳过重复打开内容页。" in source
    assert "每日流程心跳：准备检查游戏前台状态" in source
    assert "self.daily_duration_spin.setValue(0)" in source
    assert "确认已返回的资源筛选页" in source
    assert "selector_recovery_back_attempts < 2" in source
    assert "target.shell([\"input\", \"keyevent\", \"4\"])" in source
    assert "map_content_point((1090, 2390)" not in source
    assert "self.stop_event.wait(195.0)" not in source
    assert "双帧确认的完成队列教程目标" in source
    assert source.index("检测到正在自然行军的队列：等待返回，不输入") < source.index("if not level_verified")
    active = Image.open(ROOT / "evidence" / "milestone-06-live-run" / "v424-long-gather-wait.png")
    returning = Image.open(ROOT / "evidence" / "milestone-06-live-run" / "march-capacity-modal-closed.png")
    return_map = Image.open(ROOT / "evidence" / "milestone-06-live-run" / "v447-iron-return-unconfirmed.png")
    city = Image.open(ROOT / "evidence" / "milestone-04-live-feasibility" / "city-before-profile.png")
    visible_unfinished = Image.open(
        ROOT / "evidence" / "milestone-06-live-run" / "v472-visible-unfinished-tasks-private.png"
    )
    donation = match_daily_alliance_donate_mission(visible_unfinished, 0.90)
    hero = match_daily_hero_recruit_mission(visible_unfinished, 0.90)
    assert donation is not None and donation.go_point == (1165, 1155)
    assert hero is not None and hero.go_point == (1165, 1488)
    visible_unfinished_small = visible_unfinished.resize((864, 1536), Image.Resampling.LANCZOS)
    assert match_daily_alliance_donate_mission(visible_unfinished_small, 0.90) is not None
    assert match_daily_hero_recruit_mission(visible_unfinished_small, 0.90) is not None
    assert match_daily_alliance_donate_mission(city, 0.90) is None
    assert match_daily_hero_recruit_mission(city, 0.90) is None
    battle_tech = Image.open(
        ROOT / "evidence" / "milestone-06-live-run" / "v474-batch4-safe-stop-private.png"
    )
    development_tab, battle_score = match_daily_alliance_tech_battle_tab_strip(battle_tech, 0.90)
    assert development_tab == (265, 535)
    assert battle_score >= 0.985
    battle_tech_small = battle_tech.resize((864, 1536), Image.Resampling.LANCZOS)
    assert match_daily_alliance_tech_battle_tab_strip(battle_tech_small, 0.90)[0] == (159, 321)
    assert match_daily_alliance_tech_battle_tab_strip(city, 0.90)[0] is None
    development_tech = Image.open(
        ROOT / "evidence" / "milestone-06-live-run" / "v475-after-development-private.png"
    )
    territory_tech = Image.open(
        ROOT / "evidence" / "milestone-09-alliance-tech-scan" / "territory-00-private.png"
    )
    assert match_daily_alliance_tech_development_tab_strip(development_tech, 0.90)[0] == (
        720,
        535,
    )
    assert match_daily_alliance_tech_territory_tab_strip(territory_tech, 0.90)[0] == (
        720,
        535,
    )
    assert match_daily_alliance_tech_development_tab_strip(battle_tech, 0.90)[0] is None
    assert match_daily_alliance_tech_territory_tab_strip(battle_tech, 0.90)[0] is None
    tech_scan = ROOT / "evidence" / "milestone-09-alliance-tech-scan"
    assert alliance_tech_tree_viewport_mean_change(
        Image.open(tech_scan / "viewport-02-safe.png"),
        Image.open(tech_scan / "viewport-03-safe.png"),
    ) > 0.7
    assert alliance_tech_tree_viewport_mean_change(
        Image.open(tech_scan / "viewport-03-safe.png"),
        Image.open(tech_scan / "viewport-04-safe.png"),
    ) == 0.0
    hero_result = Image.open(
        ROOT / "evidence" / "milestone-06-live-run" / "v472-after-one-free-hero-private.png"
    )
    assert daily_hero_recruit_result_is_visible(hero_result, 0.90)
    assert not daily_hero_recruit_result_is_visible(city, 0.90)
    assert daily_gather_march_is_active(active, 0.90)
    assert daily_gather_march_is_active(returning, 0.90)
    assert not daily_gather_march_is_active(city, 0.90)
    timer_source = Image.open(
        ROOT / "evidence" / "milestone-06-live-run" / "v450-iron-dispatch-blocked-private.png"
    )
    timer_crop = daily_gather_remaining_time_crop(timer_source, 0.90)
    assert timer_crop is not None
    assert timer_crop.size == (460, 130)
    compact_timer = Image.open(
        ROOT / "evidence" / "milestone-06-live-run" / "v459-wood-dispatch-countdown-miss-private.png"
    )
    assert daily_gather_remaining_time_crop(compact_timer, 0.90) is not None
    assert daily_gather_march_is_active(compact_timer, 0.90)
    assert daily_gather_remaining_time_crop(city, 0.90) is None
    existing_training = Image.open(
        ROOT / "evidence" / "milestone-06-live-run" / "v452-spear-training-panel-private.png"
    )
    assert match_daily_training_active(existing_training, 0.90)[0] is not None
    spear_tutorial = Image.open(
        ROOT / "evidence" / "milestone-06-live-run" / "v457-aux-training-entry-private.png"
    )
    assert match_daily_training_spear_tutorial_entry(spear_tutorial, 0.90)[0] == (720, 1095)
    # The historical return frame is a wilderness map: a fresh exact Town
    # control now vetoes the clipboard-only city anchor.
    assert match_daily_world_town_entry(return_map, 0.90)[0] is not None
    assert match_daily_city_entry(return_map, 0.90)[0] is None
    capacity = Image.open(ROOT / "evidence" / "milestone-06-live-run" / "iron-dispatch-unconfirmed.png")
    assert detect_daily_task_state(capacity, 0.90).state is DailyTaskState.BLOCKED
    post_claim_reward = Image.open(
        ROOT / "evidence" / "milestone-06-live-run" / "v466-post-claim-unknown-private.png"
    )
    assert detect_daily_task_state(post_claim_reward, 0.90).state is DailyTaskState.REWARD_RESULT_READY
    growth_tasks = Image.open(
        ROOT / "evidence" / "milestone-06-live-run" / "v454-unknown-state-private.png"
    )
    growth_tab, growth_score = match_daily_growth_task_daily_tab(growth_tasks, 0.90)
    assert growth_tab == (1160, 2290)
    assert growth_score >= 0.985
    assert detect_daily_task_state(growth_tasks, 0.90).state is DailyTaskState.DAILY_TAB_READY
    chest_board = Image.open(
        ROOT / "evidence" / "milestone-06-live-run" / "v467-monitor-1124-private.png"
    )
    for milestone in (40, 80, 120, 160, 215):
        assert match_daily_activity_chest_open(chest_board, milestone)[0], milestone
    for milestone in (270, 325):
        assert not match_daily_activity_chest_open(chest_board, milestone)[0], milestone
    assert match_daily_task_refresh_label(chest_board)[0]
    no_help = Image.open(ROOT / "evidence" / "milestone-06-live-run" / "v430-alliance-help-timeout.png")
    assert detect_alliance_page(no_help, 0.90).page is AlliancePage.MUTUAL_HELP
    night_map = Image.open(ROOT / "evidence" / "milestone-06-live-run" / "v429-food-return-stall.png")
    night_lens, night_score = match_daily_gather_world_search(night_map, 0.90)
    assert night_lens == (95, 1755)
    assert night_score >= 0.845
    full_filter = Image.open(
        ROOT / "evidence" / "milestone-06-live-run" / "v448-wood-return-coal-start-private.png"
    )
    filter_point, filter_score = match_daily_gather_full_resources_filter_off(full_filter, 0.90)
    assert filter_point == (440, 2280), (filter_point, filter_score)
    assert filter_score >= 0.985
    assert match_daily_gather_full_resources_filter_off(city, 0.90)[0] is None
    enabled_filter = Image.open(
        ROOT / "evidence" / "milestone-06-live-run" / "v450-full-resource-filter-on-private.png"
    )
    assert daily_gather_full_resources_filter_is_enabled(enabled_filter, 0.90)
    assert match_daily_gather_full_resources_filter_off(enabled_filter, 0.90)[0] is None
    assert "仅搜索满资源筛选" in source
    assert source.index("仅搜索满资源筛选") < source.index("已点击普通资源搜索")
    auxiliary_start = source.index("def run_auxiliary_training_plan")
    auxiliary_end = source.index("def run_daily_building_upgrade_plan")
    auxiliary_flow = source[auxiliary_start:auxiliary_end]
    assert "return defer_active_training_and_reopen_daily(label, kind)" in auxiliary_flow
    assert auxiliary_flow.index("active_stage =") < auxiliary_flow.index("set_daily_training_quantity_to_max")
    assert "专属教程兵营目标" in auxiliary_flow
    assert auxiliary_flow.index("专属教程兵营目标") < auxiliary_flow.index("set_daily_training_quantity_to_max")
    assert "match_daily_training_archer_tutorial_entry" in auxiliary_flow
    assert "finish_training_camp_double_enter" in auxiliary_flow
    assert auxiliary_flow.index("finish_training_camp_double_enter") < auxiliary_flow.index("set_daily_training_quantity_to_max")
    assert "daily_training_minus_point" not in auxiliary_flow
    assert "deferred_auxiliary_training.add(kind)" in source
    assert "return defer_active_training_and_reopen_daily(label, kind)" in auxiliary_flow
    assert "立即完成" not in auxiliary_flow
    daily_start = source.index("def _start_daily_rewards_flow")
    daily_end = source.index("def _start_red_packet_flow")
    daily_flow = source[daily_start:daily_end]
    active_gather_start = daily_flow.index("if active_gather_kind is not None:")
    inherited_gather_start = daily_flow.index("if inherited_gather_slot_active:", active_gather_start)
    gather_mission_start = daily_flow.index("if missions:", inherited_gather_start)
    active_gather_wait_flow = daily_flow[active_gather_start:inherited_gather_start]
    inherited_gather_wait_flow = daily_flow[inherited_gather_start:gather_mission_start]
    assert "missions = ()" not in active_gather_wait_flow
    assert "missions = ()" not in inherited_gather_wait_flow
    assert "同类不重复" in active_gather_wait_flow
    assert "不推断占满" in inherited_gather_wait_flow
    assert "self.stop_event.wait(max(30.0, interval))" not in active_gather_wait_flow
    assert "self.stop_event.wait(max(60.0, interval))" not in active_gather_wait_flow
    assert "self.stop_event.wait(max(30.0, interval))" not in inherited_gather_wait_flow
    assert "self.stop_event.wait(max(60.0, interval))" not in inherited_gather_wait_flow
    assert daily_flow.index("if daily_list_reset_pending:") < daily_flow.index("donation_mission =")
    assert daily_flow.count("DAILY_TASK_LIST_GESTURE_X") >= 2
    assert "viewport = (720, 940, 720, 1980)" not in daily_flow
    assert "viewport = (720, 1980, 720, 940)" not in daily_flow
    assert '"900",' in daily_flow
    assert "daily_list_reset_swipes = 0" in daily_flow
    research_page = Image.open(
        ROOT / "evidence" / "milestone-02-task-audit" / "task-list-02.png"
    )
    research_mission = match_daily_research_tech_mission(research_page, 0.90)
    assert research_mission is not None
    assert research_mission.kind is DailyMissionKind.RESEARCH_TECH
    assert research_mission.task_point == (369, 1939)
    assert research_mission.go_point == (1165, 2070)
    assert research_mission.score >= 0.978
    assert match_daily_research_tech_mission(city, 0.90) is None
    day2_top = Image.open(
        ROOT / "evidence" / "milestone-08-live-day2-inventory" / "day2-scan-00-private.png"
    )
    day2_training = match_daily_training_missions(day2_top, 0.90)
    assert any(item.kind is DailyMissionKind.TRAIN_SHIELD for item in day2_training)
    hero_flow_start = daily_flow.index("def run_free_hero_recruit_plan")
    hero_flow_end = daily_flow.index("while not self.stop_event.is_set():", hero_flow_start)
    hero_flow = daily_flow[hero_flow_start:hero_flow_end]
    assert "for index in range(1):" in hero_flow
    assert "for index in range(3):" not in hero_flow
    assert "（{recruits}/1）" in hero_flow
    assert 'target.shell(["input", "keyevent", "4"])' in hero_flow
    assert "未点击黄色招募、钥匙或钻石" in hero_flow
    assert "deadline = time.monotonic() + AUTOMATION_STEP_TIMEOUT_SECONDS" in daily_flow
    assert "startup_alliance_return_stage" in daily_flow
    assert daily_flow.index("startup_alliance_tech_return_streak") < daily_flow.index(
        "startup_alliance_return_stage < 2"
    )
    assert "每日启动恢复：已从双帧确认的联盟互助空页返回联盟主页。" in daily_flow
    assert "每日启动恢复：点击双帧确认的联盟全部帮助" in daily_flow
    assert "联盟全部帮助达到25次上限，已从双帧确认互助页返回联盟主页以继续每日流程。" in daily_flow
    assert "启动恢复：复核未开始的普通训练面板" in daily_flow
    assert "启动恢复：复核继承的自然训练队列" in daily_flow
    assert "已记录继承训练倒计时并从受证训练页返回兵营" in daily_flow
    assert "无训练队列的普通训练面板返回兵营场景" in daily_flow
    assert "复核已验证训练解锁提示" in daily_flow
    assert "点击已双帧确认的训练解锁继续提示" in daily_flow
    assert "startup_alliance_help_clicks}/25" in daily_flow
    assert "startup_alliance_help_clicks}/60" not in daily_flow
    assert daily_flow.count("last_loop_diagnostic_at = 0.0") == 1
    print("daily route safety: PASS")


if __name__ == "__main__":
    main()
