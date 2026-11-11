"""Daily 325 workflow controller, invoked by the desktop window."""

from __future__ import annotations
from PIL import Image
import json
import time
from pathlib import (
    Path,
)
from PIL import (
    ImageChops,
    ImageStat,
)
from wjdr_daily_visuals import (
    intel_coloured_candidates,
    intel_expert,
    intel_expert_maybe_visible,
    intel_station_expert,
    recommended_tech,
)
from wjdr_daily_expedition import (
    ExpeditionClaimLedger,
    run_expedition_claim,
)
from wjdr_daily_intel import (
    IntelExpertLedger,
    match_hero_preview_any_level,
    match_hero_victory,
    match_selected_hero_battle,
)
from PySide6.QtWidgets import (
    QMessageBox,
)
from wjdr_backend import (
    AdbError,
    APP_NAME,
    AlliancePage,
    BUILTIN_DAILY_TASK_REFERENCE_SIZE,
    CONFIG_DIR,
    CastleLevelGate,
    DAILY_BUILTIN_TEMPLATES,
    DAILY_GATHER_FULL_NODE_MIN_RETURN_SECONDS,
    DAILY_GATHER_PASSIVE_WAIT_CAP_SECONDS,
    DAILY_TASK_LIST_BOUNDARY_CONFIRMATIONS,
    DAILY_TASK_LIST_BOUNDARY_MAX_MEAN_CHANGE,
    DAILY_TASK_LIST_FAST_TOP_MAX_GESTURES,
    DAILY_TASK_LIST_FAST_TOP_SWIPE,
    DAILY_TASK_LIST_GESTURE_X,
    DAILY_TASK_LIST_MAX_SCAN_SWIPES,
    DAILY_GATHER_REQUIRED_AMOUNTS,
    DailyAbnormalExitKind,
    DailyMissionKind,
    DailyTaskState,
    clean_name,
    load_mining_level_profile,
    initial_mining_resource_level,
    prune_runtime_evidence,
    content_viewport,
    alliance_tech_tree_viewport_mean_change,
    detect_alliance_page,
    detect_castle_level_gate,
    detect_daily_task_state,
    diagnose_daily_abnormal_exit,
    detect_world_resource_level,
    daily_activity_chest_points,
    daily_task_list_viewport_mean_change,
    match_daily_activity_chest_open,
    match_daily_task_completed_check,
    match_daily_task_header,
    match_daily_task_refresh_label,
    match_daily_task_selected_tab,
    daily_gather_resource_tab_point,
    daily_gather_search_point,
    daily_gather_level_minus_point,
    daily_gather_level_plus_point,
    daily_gather_full_resources_filter_is_enabled,
    daily_gather_remaining_time_crop,
    daily_gather_route_meets_required_amount,
    read_daily_gather_formation_capacity,
    read_daily_march_capacity,
    daily_world_overview_resource_is_enabled,
    daily_alliance_tech_entry_point,
    daily_alliance_sustain_node_point,
    daily_training_back_point,
    daily_training_quantity_is_maxed,
    daily_training_quantity_slider_points,
    daily_training_remaining_time_crop,
    daily_intel_active_countdown_crop,
    daily_intel_map_back_point,
    daily_warehouse_result_exit_point,
    daily_task_close_point,
    daily_hero_recruit_back_point,
    daily_hero_recruit_page_is_visible,
    match_daily_hero_recruit_duplicate_result,
    match_daily_hero_recruit_summary_exit,
    daily_chest_result_exit_point,
    match_daily_city_entry,
    match_daily_city_wilderness_entry,
    match_daily_city_alliance_entry,
    read_daily_activity_score,
    match_daily_gather_collect_button,
    match_daily_gather_dispatch_button,
    match_daily_gather_full_resources_filter_off,
    daily_gather_march_is_active,
    daily_network_dialog_is_visible,
    match_daily_welcome_back_confirm,
    match_daily_regular_activity_back,
    match_daily_gather_missions,
    match_daily_gather_world_search,
    match_daily_world_overview_entry,
    match_daily_world_overview_home_button,
    match_daily_world_overview_home_button_fast,
    match_daily_world_overview_resource_off,
    match_daily_world_overview_search_entry,
    match_daily_world_town_entry,
    match_daily_carnival_sale_close,
    match_daily_relocate_prompt_close,
    match_daily_sustain_prerequisite_go,
    match_daily_deep_tech_locked_close,
    match_daily_arena_mission,
    match_daily_arena_claim,
    match_arena_home,
    match_arena_opponent_list,
    match_arena_list_close,
    match_arena_result_exit,
    match_arena_reviewed_victory_exit,
    match_arena_setup,
    match_daily_intel_map_entry,
    match_daily_intel_map_page,
    match_daily_intel_mission,
    match_daily_pet_treasure_mission,
    run_pet_treasure_cycle,
    PetDispatchLedger,
    match_daily_intel_rescue_active,
    match_daily_intel_rescue_pin,
    match_daily_intel_rescue_preview,
    match_daily_intel_rescue_target,
    match_daily_intel_hero_pin,
    match_daily_intel_hero_preview,
    match_daily_intel_hero_detail,
    match_daily_intel_hero_setup,
    match_daily_intel_hero_ready_battle,
    match_daily_intel_completed_check,
    match_daily_intel_station_bubble,
    match_daily_intel_tutorial_station,
    match_daily_warehouse_result,
    match_daily_warehouse_city_supply_bubble,
    match_daily_warehouse_supply_mission,
    match_daily_alliance_donate_mission,
    match_daily_alliance_food_donation,
    daily_alliance_donation_page_is_visible,
    match_daily_alliance_tech_entry,
    match_daily_alliance_tech_battle_tab_strip,
    match_daily_alliance_tech_development_tab_strip,
    match_daily_alliance_tech_territory_tab_strip,
    match_daily_alliance_sustain_node,
    match_daily_building_upgrade_mission,
    match_daily_building_active_upgrading,
    match_daily_normal_build_action,
    match_daily_hero_free_recruit,
    match_daily_hero_recruit_mission,
    match_daily_training_active,
    match_daily_training_collect_tutorial,
    match_daily_training_entry,
    match_daily_training_archer_tutorial_entry,
    match_daily_training_spear_tutorial_entry,
    match_daily_training_missions,
    read_daily_training_progress,
    match_daily_training_normal_button,
    match_daily_training_unlock_continue,
    map_content_point,
    resource_path,
    daily_gather_selector_is_valid,
    daily_gather_meat_is_selected,
    match_daily_gather_meat_visible_tab,
)

from wjdr_runtime_config import (
    AUTOMATION_STEP_TIMEOUT_SECONDS,
    DAILY_DONATION_TASK_TARGET,
    DAILY_DONATION_UNAVAILABLE_RETRY_SECONDS,
    DAILY_DONATION_WINDOW_CAP,
    DAILY_DONATION_WINDOW_RETRY_SECONDS,
    DAILY_HERO_FREE_RECRUIT_RETRY_SECONDS,
    DAILY_IDLE_FALLBACK_RETRY_SECONDS,
    DAILY_IDLE_STATIC_REFRESH_RETRY_SECONDS,
    DAILY_PROFILE_RETURN_PASSIVE_CAP_SECONDS,
    DAILY_RETRY_LOCK_MAX_SECONDS,
    DAILY_TOWN_RENDER_PASSIVE_CAP_SECONDS,
    DAILY_WAREHOUSE_SUPPLY_FAILURE_RETRY_SECONDS,
    DAILY_WAREHOUSE_SUPPLY_RETRY_SECONDS,
    MAX_SINGLE_WAIT_SECONDS,
    bounded_step_timeout,
)


class DailyController:
    def _start_daily_rewards_flow(self) -> None:
        """Collect every visible, verified Daily Tasks reward in one safe pass.

        This is the collection half of the Daily 325 workflow.  It is broader
        than the retained login-only compatibility flow above, but deliberately
        remains input-conservative: only the confirmed city-task entry and a
        green ``领取`` in the verified Daily Tasks action column are clickable.
        After such a click it may dismiss the separately verified full-screen
        reward result, and only while that result is correlated to the click
        it just made.  It may also collect a reached activity milestone chest
        once per run, then dismiss only its two-frame-verified contents sheet.
        It never clicks ``前往``, shops, diamonds, keys, speed-ups,
        prerequisite prompts, or an arbitrary popup close control.
        """
        if not self.adb:
            QMessageBox.warning(self, APP_NAME, "尚未连接 MuMu。")
            return
        required = [resource_path(asset) for asset, _name in DAILY_BUILTIN_TEMPLATES]
        missing = [path for path in required if not path.is_file()]
        if missing:
            names = "、".join(path.name for path in missing)
            QMessageBox.warning(self, APP_NAME, f"每日任务识别素材缺失：{names}\n请重新解压完整程序包。")
            return

        target = self.adb.clone_for_device()
        configured_daily_interval = min(
            MAX_SINGLE_WAIT_SECONDS,
            max(0.0, self.daily_interval_spin.value()),
        )
        duration = self.daily_duration_spin.value()
        guard = self.daily_guard_check.isChecked()
        threshold = 0.90

        def job() -> None:
            interval = configured_daily_interval
            capture_latency_ewma = 0.0
            fast_capture_ok = True
            _fast_retry_counter = 0

            def daily_screenshot() -> Image.Image:
                nonlocal fast_capture_ok, _fast_retry_counter
                if fast_capture_ok or _fast_retry_counter % 20 == 0:
                    try:
                        result = target.fast_window_screenshot(BUILTIN_DAILY_TASK_REFERENCE_SIZE)
                        fast_capture_ok = True
                        _fast_retry_counter = 0
                        return result
                    except AdbError:
                        fast_capture_ok = False
                _fast_retry_counter += 1
                return target.screenshot()

            def capture_daily_image() -> Image.Image:
                nonlocal interval, capture_latency_ewma
                capture_started = time.monotonic()
                image = daily_screenshot()
                sample = max(0.0, time.monotonic() - capture_started)
                capture_latency_ewma = (
                    sample
                    if capture_latency_ewma <= 0.0
                    else capture_latency_ewma * 0.75 + sample * 0.25
                )
                floor = 0.03 if sample < 0.10 else 0.12
                device_cushion = min(0.45, floor + capture_latency_ewma * 0.10)
                interval = min(
                    MAX_SINGLE_WAIT_SECONDS,
                    max(0.0, min(configured_daily_interval, device_cushion)),
                )
                return image

            _fg_cache_until = 0.0
            _fg_cache_value = True

            def cached_foreground_is_game(*, ttl: float = 2.0) -> bool:
                nonlocal _fg_cache_until, _fg_cache_value
                now = time.monotonic()
                if now < _fg_cache_until:
                    return _fg_cache_value
                result = target.foreground_is_game()
                _fg_cache_value = result
                _fg_cache_until = now + ttl
                return result

            def adaptive_operation_wait(
                minimum: float = 0.03,
                maximum: float = 1.2,
            ) -> bool:
                effective_minimum = max(minimum, 0.03)
                bounded_maximum = min(MAX_SINGLE_WAIT_SECONDS, max(effective_minimum, maximum))
                delay = min(bounded_maximum, max(effective_minimum, interval))
                return self.stop_event.wait(delay)

            started = time.monotonic()
            city_entry_tapped = False
            daily_tab_tapped = False
            world_town_returns = 0
            claims = 0
            pending_claim = False
            # A task claim can briefly render the daily page before its result
            # sheet.  Keep the postcondition correlation for a bounded period.
            pending_claim_deadline = 0.0
            # Claims always drain before any Go/task scan.  The exact clicked
            # point and pre-click activity strip let a following verified
            # Daily frame prove that the prior row settled without idling for
            # the old fixed 12-second window.  Two fresh frames are still
            # mandatory before another claim can be clicked.
            pending_claim_point: tuple[int, int] | None = None
            pending_claim_activity_before = 0.0
            pending_claim_activity_confidence = 0.0
            pending_claim_settle_streak = 0
            pending_claim_settle_point: tuple[int, int] | None = None
            # The Daily sheet can render twice after a successful claim and
            # only then raise that same claim's full-screen reward sheet.  A
            # proved button disappearance therefore leaves a very short
            # lineage window for that exact reviewed result page.  It grants
            # no authority to any other popup or to a result seen later.
            recent_claim_result_deadline = 0.0
            # One claim can open several consecutive reward-result sheets.
            # Keep their exact claim lineage, but cap it so a persistent or
            # unrelated overlay can never become an unbounded tap loop.
            claim_result_exit_count = 0
            claim_result_exit_cap = 4
            # Unknown-page recovery is classification-first.  The controller
            # must see the same page-specific exit semantics in two fresh
            # frames before it may use that page's exact X/Back/Town point.
            # There is deliberately no generic Android Back or corner tap.
            abnormal_exit_kind = DailyAbnormalExitKind.UNKNOWN
            abnormal_exit_point: tuple[int, int] | None = None
            abnormal_exit_streak = 0
            attempted_chests: set[int] = set()
            # A reset/relaunch must not reopen the contents sheets for chest
            # art already visibly open on the activity bar.  It takes two
            # passive recognitions to record that skip; a miss falls back to
            # the existing claim-and-result flow.
            open_chest_streaks: dict[int, int] = {}
            pending_chest: int | None = None
            activity_goal_streak = 0
            activity_goal_confirmed = False
            activity_goal_claim_drain_announced = False
            activity_goal_claim_scan_started = False
            daily_scrolls = 0
            # A bounded scan ends at the bottom of the task list. Every retry
            # must first return within this verified list viewport to scan
            # from the first task rather than silently re-reading bottom rows.
            daily_list_reset_pending = True
            daily_list_reset_swipes = 0
            daily_list_reset_before_image: Image.Image | None = None
            daily_list_reset_settle_image: Image.Image | None = None
            daily_list_reset_boundary_streak = 0
            daily_list_fast_anchor_miss_streak = 0
            daily_list_scan_before_image: Image.Image | None = None
            daily_list_bottom_boundary_streak = 0
            daily_completed_zone_streak = 0
            # The user's current client sorts the first green-check row into
            # the completed tail.  Once that tail is proved, return to the
            # top immediately and wait there; never keep walking downward.
            daily_completed_zone_wait_after_top = False
            world_town_tapped = False
            selector_recovery_streak = 0
            # MuMu's resource route may leave two reviewed selector layers
            # after a guarded stop. Each Android Back is allowed only after
            # two fresh selector frames with no march panel, and no more than
            # two such returns are ever sent in one Daily run.
            selector_recovery_back_attempts = 0
            # An active expedition can coexist with the resource selector
            # after a guarded stop. This is a distinct state from a returned,
            # no-march selector: one constrained Back closes the selector so
            # the verified world-map→town path can resume independent tasks.
            active_selector_recovery_streak = 0
            active_selector_back_sent = False
            level_verified = False
            profile_requested = False
            profile_deadline = 0.0
            profile_level_streak = 0
            profile_level_result = CastleLevelGate.UNKNOWN
            preflight_daily_close_sent = False
            # A prior, safely stopped Daily run can leave the game on the
            # exact empty Mutual Help page.  Keep this recovery constrained
            # to that reviewed page and the reviewed Alliance Home only; it
            # sends at most one Android Back from each page before the normal
            # city/profile proof resumes.
            startup_alliance_return_stage = 0
            startup_alliance_return_streak = 0
            startup_alliance_help_point: tuple[int, int] | None = None
            startup_alliance_help_streak = 0
            startup_alliance_help_clicks = 0
            startup_alliance_help_cap_back_sent = False
            # A user or earlier guarded run may leave the game on one of the
            # three Alliance Technology tabs.  Startup may return only after
            # the *full selected tab strip* is stable for two fresh frames.
            # It never clicks a technology node during recovery; one Back
            # returns to Alliance Home, where the existing exact-page return
            # completes the path to the city and today's Daily card can
            # establish a fresh task correlation.
            startup_alliance_tech_state: str | None = None
            startup_alliance_tech_return_streak = 0
            startup_alliance_tech_back_sent = False
            startup_intel_map_streak = 0
            startup_intel_map_back_sent = False
            # A guarded stop can leave the exact Hero Recruitment page open.
            # Startup may leave that reviewed page only after two fresh
            # matches.  If neither reviewed green-free control is present,
            # remember that outcome for this process so the same Daily card
            # cannot cause a no-op navigation loop.
            startup_hero_recruit_return_streak = 0
            startup_hero_recruit_back_sent = False
            # The ordinary Alliance donation can become grey/disabled while
            # the yellow diamond sibling remains enabled.  Startup recovery
            # may only leave that exact reviewed dual-control page after two
            # passive frames; it never taps either donation control.
            startup_alliance_donation_return_streak = 0
            startup_alliance_donation_back_sent = False
            # A failed count adjustment can leave a *non-active* ordinary
            # troop panel open.  It has no task state itself, so recover only
            # from two matched normal panels with no active-queue evidence.
            # The sole recovery input is Android Back; it never touches either
            # the yellow immediate-complete or the blue normal-train control.
            startup_training_return_streak = 0
            startup_active_training_streak = 0
            startup_training_back_sent = False
            startup_training_unlock_point: tuple[int, int] | None = None
            startup_training_unlock_streak = 0
            startup_training_unlock_continue_sent = False
            # The newest Word guide requires the castle's current resource
            # band before the first gather. It is learned only through the
            # exact world-map globe + Resource-layer route and then cached for
            # this process; no fixed selector level is assumed.
            resource_level: int | None = None
            alliance_help_checked = False
            # The Daily task needs forty donations, but one availability
            # window exposes only twenty-five normal resource donations.  A
            # fresh same-card match authorises at most one five-click batch;
            # every click still needs an Alliance-Coin counter delta.  The
            # per-account/date state survives a restart and prevents both a
            # false 25/40 completion and repeated cooldown-page visits.
            target_identity = target.device_identity()
            donation_identity = target_identity.replace(":", "_").replace("/", "_")
            mining_level_profile = load_mining_level_profile(target_identity)
            resource_level = initial_mining_resource_level(mining_level_profile)
            if mining_level_profile.mode == "manual":
                self._log_for_device(
                    target.device,
                    f"采矿等级：本账号使用手动 Lv.{resource_level}；"
                    "直接进入普通采矿流程，完全跳过地球、小房子和绿色城堡识图。",
                )
            else:
                self._log_for_device(
                    target.device,
                    "采矿等级：本账号使用自动识别；仅在首次采矿前执行地球/小房子/绿色城堡判级。",
                )
            donation_state_path = CONFIG_DIR / f"daily_donation_{donation_identity}.json"
            donation_day = time.strftime("%Y-%m-%d")
            try:
                pet_dispatch_ledger: PetDispatchLedger | None = PetDispatchLedger(target_identity, donation_day)
                expedition_ledger: ExpeditionClaimLedger | None = ExpeditionClaimLedger(target_identity, donation_day)
                intel_expert_ledger: IntelExpertLedger | None = IntelExpertLedger(target_identity, donation_day)
            except ValueError:
                pet_dispatch_ledger = None
                expedition_ledger = None
                intel_expert_ledger = None
                self._log_for_device(target.device, "宠物寻宝未取得完整账号身份；本轮不自动派遣。")
            expedition_attempted = False
            pet_failed_scan = False
            pet_retry_at = 0.0

            def load_daily_donation_state() -> tuple[int, int, float]:
                try:
                    state = json.loads(donation_state_path.read_text(encoding="utf-8"))
                    if state.get("date") == donation_day:
                        confirmed = max(
                            0,
                            min(DAILY_DONATION_TASK_TARGET, int(state.get("confirmed", 0))),
                        )
                        # Old files contained only `confirmed`; treating that
                        # value as the current-window count is fail-closed.
                        window_confirmed = max(
                            0,
                            min(
                                DAILY_DONATION_WINDOW_CAP,
                                int(state.get("window_confirmed", confirmed)),
                            ),
                        )
                        retry_at = max(0.0, float(state.get("retry_at", 0.0)))
                        return confirmed, window_confirmed, retry_at
                except (OSError, ValueError, TypeError, json.JSONDecodeError):
                    pass
                return 0, 0, 0.0

            def save_daily_donation_state() -> None:
                CONFIG_DIR.mkdir(parents=True, exist_ok=True)
                payload = json.dumps(
                    {
                        "date": donation_day,
                        "confirmed": max(
                            0,
                            min(
                                DAILY_DONATION_TASK_TARGET,
                                int(alliance_donation_confirmed_clicks),
                            ),
                        ),
                        "window_confirmed": max(
                            0,
                            min(
                                DAILY_DONATION_WINDOW_CAP,
                                int(alliance_donation_window_clicks),
                            ),
                        ),
                        "retry_at": max(0.0, float(alliance_donation_retry_at)),
                        "prerequisite_blocked": alliance_donation_prerequisite_blocked,
                    },
                    ensure_ascii=False,
                    indent=2,
                )
                temporary = donation_state_path.with_suffix(".tmp")
                temporary.write_text(payload + "\n", encoding="utf-8")
                temporary.replace(donation_state_path)

            (
                alliance_donation_confirmed_clicks,
                alliance_donation_window_clicks,
                alliance_donation_retry_at,
            ) = load_daily_donation_state()
            try:
                _saved_donation = json.loads(donation_state_path.read_text(encoding="utf-8"))
                alliance_donation_prerequisite_blocked = bool(
                    _saved_donation.get("date") == donation_day and _saved_donation.get("prerequisite_blocked")
                )
            except (OSError, ValueError, TypeError, json.JSONDecodeError):
                alliance_donation_prerequisite_blocked = False
            alliance_donation_unavailable = alliance_donation_prerequisite_blocked

            # Migrate historical 30-minute/two-hour retry epochs immediately;
            # repeated restarts must not roll an old failure lock forward.
            donation_retry_cap = time.time() + DAILY_RETRY_LOCK_MAX_SECONDS
            if alliance_donation_retry_at > donation_retry_cap:
                alliance_donation_retry_at = donation_retry_cap
                save_daily_donation_state()

            def defer_daily_donation(seconds: float) -> None:
                nonlocal alliance_donation_retry_at
                delay = min(
                    DAILY_RETRY_LOCK_MAX_SECONDS,
                    max(0.0, float(seconds)),
                )
                alliance_donation_retry_at = time.time() + delay
                save_daily_donation_state()

            def daily_donation_is_deferred() -> bool:
                """Refresh an expired window, otherwise suppress only donation."""

                nonlocal alliance_donation_retry_at
                nonlocal alliance_donation_window_clicks
                nonlocal alliance_donation_unavailable
                if alliance_donation_prerequisite_blocked:
                    return True
                if alliance_donation_confirmed_clicks >= DAILY_DONATION_TASK_TARGET:
                    return True
                now = time.time()
                if alliance_donation_retry_at > now:
                    return True
                if alliance_donation_retry_at > 0.0:
                    # A deadline merely authorises a fresh availability probe;
                    # it never assumes that twenty-five clicks replenished.
                    alliance_donation_retry_at = 0.0
                    alliance_donation_window_clicks = 0
                    alliance_donation_unavailable = False
                    save_daily_donation_state()
                    self._log_for_device(
                        target.device,
                        "联盟捐献等待期限已到；仅恢复一次普通粮食可用性复查，"
                        "仍要求精确蓝色普通捐献按钮和最终灰色状态。",
                    )
                    return False
                if alliance_donation_window_clicks >= DAILY_DONATION_WINDOW_CAP:
                    alliance_donation_unavailable = True
                    defer_daily_donation(DAILY_DONATION_WINDOW_RETRY_SECONDS)
                    return True
                return alliance_donation_unavailable
            building_upgrade_started = False
            # A verified Building Go can legitimately settle on the ordinary
            # city while another natural construction is already active.  In
            # that case the surface exposes only countdown/speed-up controls,
            # never the normal Build button.  Skip only this mission for this
            # process after two fresh city frames so lower Daily items are not
            # starved and no diamond/speed-up control is touched.
            building_upgrade_unavailable = False
            building_upgrade_retry_at = 0.0
            building_failed_scan = False
            # Word-guide tasks are intentionally isolated from generic Daily
            # routing. Warehouse uses its own immediately correlated result
            # chain and an account-scoped three-minute recheck deadline. Intel
            # may execute only its reviewed routes. Arena requires its exact
            # title+same-row-Go plus the complete free-attempt, weakest-lower
            # opponent, five-hero and result-countdown proof chain.
            warehouse_supply_state_path = (
                CONFIG_DIR / f"daily_warehouse_supply_{donation_identity}.json"
            )

            def load_warehouse_supply_recheck_at() -> float:
                try:
                    state = json.loads(
                        warehouse_supply_state_path.read_text(encoding="utf-8")
                    )
                    return max(0.0, float(state.get("recheck_at", 0.0)))
                except (OSError, ValueError, TypeError, json.JSONDecodeError):
                    return 0.0

            warehouse_supply_recheck_at = load_warehouse_supply_recheck_at()

            def defer_warehouse_supply(
                seconds: float = DAILY_WAREHOUSE_SUPPLY_RETRY_SECONDS,
            ) -> None:
                nonlocal warehouse_supply_recheck_at
                warehouse_supply_recheck_at = time.time() + max(0.0, float(seconds))
                CONFIG_DIR.mkdir(parents=True, exist_ok=True)
                temporary = warehouse_supply_state_path.with_suffix(".tmp")
                temporary.write_text(
                    json.dumps(
                        {"recheck_at": warehouse_supply_recheck_at},
                        ensure_ascii=False,
                        indent=2,
                    )
                    + "\n",
                    encoding="utf-8",
                )
                temporary.replace(warehouse_supply_state_path)

            def clear_warehouse_supply_defer() -> None:
                """Clear only a proven failed Warehouse probe for this account."""

                nonlocal warehouse_supply_recheck_at
                warehouse_supply_recheck_at = 0.0
                try:
                    warehouse_supply_state_path.unlink(missing_ok=True)
                except OSError:
                    pass

            def warehouse_supply_is_deferred() -> bool:
                """Re-authorise one exact Warehouse probe after three minutes."""

                nonlocal warehouse_supply_recheck_at
                if time.time() < warehouse_supply_recheck_at:
                    return True
                if warehouse_supply_recheck_at:
                    warehouse_supply_recheck_at = 0.0
                    try:
                        warehouse_supply_state_path.unlink(missing_ok=True)
                    except OSError:
                        pass
                    self._log_for_device(
                        target.device,
                        "仓库补给三分钟复查期限已到；仅在当前每日任务安全边界重新检查一次。",
                    )
                return False

            intel_route_attempted = False
            intel_failed_scan = False
            intel_route_retry_at = 0.0
            arena_route_retry_at = 0.0
            arena_route_done = False
            # A missing green-free control is a five-minute cooldown, not a
            # process-lifetime ban.  The deadline is account-scoped and is
            # revisited only when the scanner is already back at the Daily
            # task boundary after completing another independent item.
            hero_recruit_unavailable = False
            hero_recruit_state_path = (
                CONFIG_DIR / f"daily_hero_recruit_{donation_identity}.json"
            )

            def load_hero_recruit_recheck_at() -> float:
                try:
                    state = json.loads(
                        hero_recruit_state_path.read_text(encoding="utf-8")
                    )
                    return max(0.0, float(state.get("recheck_at", 0.0)))
                except (OSError, ValueError, TypeError, json.JSONDecodeError):
                    return 0.0

            hero_recruit_recheck_at = load_hero_recruit_recheck_at()

            def defer_hero_recruit(seconds: float = DAILY_HERO_FREE_RECRUIT_RETRY_SECONDS) -> None:
                nonlocal hero_recruit_recheck_at, hero_recruit_unavailable
                hero_recruit_recheck_at = time.time() + max(0.0, float(seconds))
                hero_recruit_unavailable = True
                CONFIG_DIR.mkdir(parents=True, exist_ok=True)
                temporary = hero_recruit_state_path.with_suffix(".tmp")
                temporary.write_text(
                    json.dumps(
                        {"recheck_at": hero_recruit_recheck_at},
                        ensure_ascii=False,
                        indent=2,
                    )
                    + "\n",
                    encoding="utf-8",
                )
                temporary.replace(hero_recruit_state_path)

            def hero_recruit_is_deferred() -> bool:
                """Suppress recruitment until its account deadline at a Daily boundary."""

                nonlocal hero_recruit_recheck_at, hero_recruit_unavailable
                if time.time() < hero_recruit_recheck_at:
                    hero_recruit_unavailable = True
                    return True
                if hero_recruit_unavailable or hero_recruit_recheck_at:
                    hero_recruit_unavailable = False
                    hero_recruit_recheck_at = 0.0
                    try:
                        hero_recruit_state_path.unlink(missing_ok=True)
                    except OSError:
                        pass
                    self._log_for_device(
                        target.device,
                        "绿色免费高级招募五分钟冷却已结束；在当前每日任务安全边界重新检查。",
                    )
                return False
            # A verified training card can occasionally leave the Daily page
            # unchanged after its Go tap.  Only that freshly double-confirmed
            # no-navigation outcome suppresses all training cards for this
            # process.  A successful queue start, or a reviewed tutorial that
            # safely yields back to Daily, defers only its own troop kind so
            # the other camps can still use their independent normal queues.
            training_route_attempted = False
            training_route_retry_at = 0.0
            deferred_auxiliary_training: set[DailyMissionKind] = set()
            deferred_training_recheck_at: dict[DailyMissionKind, float] = {}
            reported_training_progress: set[DailyMissionKind] = set()
            training_skip_state_path = CONFIG_DIR / f"daily_training_skip_{donation_identity}.json"
            training_queue_state_path = CONFIG_DIR / f"daily_training_queue_{donation_identity}.json"
            successful_training_retry_epoch: dict[DailyMissionKind, float] = {}
            failed_training_retry_epoch = 0.0

            def load_failed_training_kinds() -> set[DailyMissionKind]:
                nonlocal failed_training_retry_epoch
                try:
                    state = json.loads(training_skip_state_path.read_text(encoding="utf-8"))
                    retry_at = float(state.get("retry_at", 0.0))
                    failed_training_retry_epoch = retry_at
                    if state.get("date") == donation_day and retry_at > time.time():
                        saved = {str(value) for value in state.get("kinds", ())}
                        return {
                            kind
                            for kind in (
                                DailyMissionKind.TRAIN_SHIELD,
                                DailyMissionKind.TRAIN_SPEAR,
                                DailyMissionKind.TRAIN_ARCHER,
                            )
                            if kind.value in saved
                        }
                except (OSError, ValueError, TypeError, json.JSONDecodeError):
                    pass
                return set()

            def save_failed_training_kinds() -> None:
                nonlocal failed_training_retry_epoch
                CONFIG_DIR.mkdir(parents=True, exist_ok=True)
                failed_training_retry_epoch = (
                    time.time() + DAILY_RETRY_LOCK_MAX_SECONDS
                )
                payload = json.dumps(
                    {
                        "date": donation_day,
                        "kinds": sorted(kind.value for kind in failed_training_kinds),
                        # A reviewed navigation/tutorial failure is not proof
                        # that the camp is unavailable all day.  Suppress
                        # immediate loops, then permit one fresh Daily-card
                        # retry after at most thirty seconds. Every retry needs
                        # the full exact Go, camp, quantity=10 and blue Train
                        # proof chain.
                        "retry_at": failed_training_retry_epoch,
                    },
                    ensure_ascii=False,
                    indent=2,
                )
                temporary = training_skip_state_path.with_suffix(".tmp")
                temporary.write_text(payload + "\n", encoding="utf-8")
                temporary.replace(training_skip_state_path)

            failed_training_kinds = load_failed_training_kinds()
            # A failed card must not starve items farther down the list. A
            # ten-second deadline authorises rechecking only after this scan
            # reaches its known completed zone or confirmed lower boundary.
            training_failed_scan_kinds = set(failed_training_kinds)
            training_failure_retry_cap = (
                time.time() + DAILY_RETRY_LOCK_MAX_SECONDS
            )
            if (
                failed_training_kinds
                and failed_training_retry_epoch > training_failure_retry_cap
            ):
                # Rewrite old persisted 30-minute epochs once; do not merely
                # cap them in memory and accidentally renew them on restart.
                failed_training_retry_epoch = training_failure_retry_cap
                CONFIG_DIR.mkdir(parents=True, exist_ok=True)
                temporary = training_skip_state_path.with_suffix(".tmp")
                temporary.write_text(
                    json.dumps(
                        {
                            "date": donation_day,
                            "kinds": sorted(
                                kind.value for kind in failed_training_kinds
                            ),
                            "retry_at": failed_training_retry_epoch,
                        },
                        ensure_ascii=False,
                        indent=2,
                    )
                    + "\n",
                    encoding="utf-8",
                )
                temporary.replace(training_skip_state_path)

            def refresh_failed_training_kinds() -> None:
                """Release an expired camp-failure backoff in the same process."""

                nonlocal failed_training_retry_epoch
                if not failed_training_kinds:
                    return
                if failed_training_retry_epoch > time.time():
                    return
                failed_training_kinds.clear()
                failed_training_retry_epoch = 0.0
                try:
                    training_skip_state_path.unlink(missing_ok=True)
                except OSError:
                    pass
                self._log_for_device(
                    target.device,
                    "训练路线三十秒失败让行已到期；在当前每日任务安全边界"
                    "重新启用对应训练卡，仍从双帧前往重新验证。",
                )

            def load_active_training_deferrals() -> None:
                """Restore only previously proved natural training queues.

                The saved state never authorises a Train tap.  It merely keeps
                a just-started camp out of candidate selection across a safe
                process upgrade so another unfinished troop kind can proceed.
                """
                try:
                    state = json.loads(training_queue_state_path.read_text(encoding="utf-8"))
                    if state.get("date") != donation_day:
                        return
                    saved = state.get("retry_at", {})
                    if not isinstance(saved, dict):
                        return
                    epoch_now = time.time()
                    monotonic_now = time.monotonic()
                    for kind in (
                        DailyMissionKind.TRAIN_SHIELD,
                        DailyMissionKind.TRAIN_SPEAR,
                        DailyMissionKind.TRAIN_ARCHER,
                    ):
                        retry_epoch = float(saved.get(kind.value, 0.0))
                        if retry_epoch <= epoch_now:
                            continue
                        successful_training_retry_epoch[kind] = retry_epoch
                        deferred_auxiliary_training.add(kind)
                        deferred_training_recheck_at[kind] = (
                            monotonic_now + retry_epoch - epoch_now
                        )
                except (OSError, ValueError, TypeError, json.JSONDecodeError):
                    return

            def save_active_training_deferrals() -> None:
                CONFIG_DIR.mkdir(parents=True, exist_ok=True)
                payload = json.dumps(
                    {
                        "date": donation_day,
                        "retry_at": {
                            kind.value: retry_epoch
                            for kind, retry_epoch in sorted(
                                successful_training_retry_epoch.items(),
                                key=lambda item: item[0].value,
                            )
                            if retry_epoch > time.time()
                        },
                    },
                    ensure_ascii=False,
                    indent=2,
                )
                temporary = training_queue_state_path.with_suffix(".tmp")
                temporary.write_text(payload + "\n", encoding="utf-8")
                temporary.replace(training_queue_state_path)

            load_active_training_deferrals()
            active_gather_kind: DailyMissionKind | None = None
            active_gather_observed_at = 0.0
            active_gather_recheck_at = 0.0
            # A direct full-capacity proof suppresses every gather card for a
            # short passive interval while claims/training/other Daily items
            # continue.  It is not a global multi-march assumption: accounts
            # with a proved free slot never enter this state.
            gather_cards_suppressed_until = 0.0
            # A resource search can legitimately return no reviewed node in
            # the current map refresh.  Defer only that resource kind and
            # keep scanning later Daily items instead of retrying the same
            # card immediately.
            deferred_gather_recheck_at: dict[DailyMissionKind, float] = {}
            gather_deferral_state_path = CONFIG_DIR / f"daily_gather_defer_{donation_identity}.json"
            active_gather_retry_epoch: dict[DailyMissionKind, float] = {}
            natural_gather_queue_kinds: set[DailyMissionKind] = set()
            daily_gather_sent_kinds: set[DailyMissionKind] = set()

            def load_active_gather_deferrals() -> None:
                """Restore reviewed per-resource yields across safe restarts.

                This state never authorises a map, node, or Dispatch input. It
                only prevents a just-proved unavailable/under-capacity card
                from starving lower Daily items after a package restart.
                """

                try:
                    state = json.loads(
                        gather_deferral_state_path.read_text(encoding="utf-8")
                    )
                    same_day = state.get("date") == donation_day
                    saved = state.get("retry_at", {})
                    if not isinstance(saved, dict):
                        return
                    saved_natural_queues = {
                        str(value) for value in state.get("natural_queue_kinds", ())
                    }
                    if same_day:
                        saved_sent = set(state.get("sent_kinds", ())) | saved_natural_queues
                        daily_gather_sent_kinds.update(
                            kind for kind in DAILY_GATHER_REQUIRED_AMOUNTS if kind.value in saved_sent
                        )
                    epoch_now = time.time()
                    monotonic_now = time.monotonic()
                    restored: list[str] = []
                    migrated_failure_lock = False
                    for kind in DAILY_GATHER_REQUIRED_AMOUNTS:
                        retry_epoch = float(saved.get(kind.value, 0.0))
                        if retry_epoch <= epoch_now and kind.value not in saved_natural_queues:
                            continue
                        if kind.value in saved_natural_queues:
                            natural_gather_queue_kinds.add(kind)
                        else:
                            if not same_day:
                                continue
                            retry_cap = epoch_now + DAILY_RETRY_LOCK_MAX_SECONDS
                            if retry_epoch > retry_cap:
                                retry_epoch = retry_cap
                                migrated_failure_lock = True
                        active_gather_retry_epoch[kind] = retry_epoch
                        deferred_gather_recheck_at[kind] = (
                            monotonic_now + retry_epoch - epoch_now
                        )
                        # ``mission_label`` is defined later with the routing
                        # helpers.  Persisted-state loading happens first, so
                        # log the stable enum value here and avoid a startup
                        # dependency on a not-yet-bound local function.
                        restored.append(kind.value)
                    if restored:
                        self._log_for_device(
                            target.device,
                            "已恢复本账号仍有效的采集让行："
                            + "、".join(restored)
                            + "；只跳过对应任务卡，不授权任何地图或出征输入。",
                        )
                    if migrated_failure_lock:
                        save_active_gather_deferrals()
                except (OSError, ValueError, TypeError, json.JSONDecodeError):
                    return

            def save_active_gather_deferrals() -> None:
                CONFIG_DIR.mkdir(parents=True, exist_ok=True)
                payload = json.dumps(
                    {
                        "date": donation_day,
                        "retry_at": {
                            kind.value: retry_epoch
                            for kind, retry_epoch in sorted(
                                active_gather_retry_epoch.items(),
                                key=lambda item: item[0].value,
                            )
                            if retry_epoch > time.time() or kind in natural_gather_queue_kinds
                        },
                        "natural_queue_kinds": sorted(
                            kind.value
                            for kind in natural_gather_queue_kinds
                        ),
                        "sent_kinds": sorted(kind.value for kind in daily_gather_sent_kinds),
                    },
                    ensure_ascii=False,
                    indent=2,
                )
                temporary = gather_deferral_state_path.with_suffix(".tmp")
                temporary.write_text(payload + "\n", encoding="utf-8")
                temporary.replace(gather_deferral_state_path)

            def defer_gather_kind(
                kind: DailyMissionKind,
                seconds: float,
                *,
                natural_queue: bool = False,
            ) -> None:
                delay = max(0.0, float(seconds))
                # A failed observation cannot erase an outstanding owned march.
                natural_queue = natural_queue or kind in natural_gather_queue_kinds
                if natural_queue:
                    natural_gather_queue_kinds.add(kind)
                else:
                    natural_gather_queue_kinds.discard(kind)
                    delay = min(delay, DAILY_RETRY_LOCK_MAX_SECONDS)
                active_gather_retry_epoch[kind] = time.time() + delay
                deferred_gather_recheck_at[kind] = time.monotonic() + delay
                save_active_gather_deferrals()

            load_active_gather_deferrals()
            # Multi-march accounts are handled per dispatch.  A kind already
            # sent by this process is not duplicated while its natural queue
            # is outstanding, but a different gather card may use another
            # freshly proved free slot when the formation still proves troops
            # and enough carrying capacity.
            dispatched_gather_kinds: set[DailyMissionKind] = set(daily_gather_sent_kinds) | set(natural_gather_queue_kinds)
            known_march_total: int | None = None
            bootstrap_dispatch_used = False
            # A previous safe launch can already occupy a march slot.  The
            # resource kind cannot be inferred from the compact timer, so this
            # remains passive evidence only and never becomes a global lock;
            # every new route must independently prove fresh free capacity.
            inherited_gather_slot_active = False
            inherited_gather_recheck_at = 0.0
            # The exact capacity sheet contains research, activation, and
            # purchase routes. Android Back is permitted only after two
            # consecutive recognitions of that one reviewed sheet, and only
            # once, so the worker can observe the already-active expedition.
            march_capacity_back_streak = 0
            carnival_close_streak = 0
            carnival_close_sent = False
            relocate_close_streak = 0
            relocate_close_sent = False
            sustain_prerequisite_streak = 0
            sustain_prerequisite_sent: set[str] = set()
            sustain_prerequisite_kind = ""
            deep_tech_streak = 0
            deep_tech_close_sent = False
            startup_arena_list_streak = 0
            startup_arena_list_closed = False
            startup_arena_home_streak = 0
            startup_arena_home_closed = False
            startup_arena_result_streak = 0
            startup_arena_result_closed = False
            march_capacity_back_sent = False
            welcome_back_streak = 0
            welcome_back_confirm_sent = False
            regular_activity_back_streak = 0
            regular_activity_back_sent = False
            last_state: DailyTaskState | None = None
            last_point: tuple[int, int] | None = None
            state_streak = 0
            last_ui_state = ""
            last_loop_diagnostic_at = 0.0
            idle_no_input_until = 0.0
            idle_no_input_label = ""
            # An instance may be launched directly from the world map.  Give
            # UNKNOWN states a defined, already-expired transition window
            # until this worker itself taps a reviewed city or task-tab entry.
            transition_deadline = 0.0

            def set_state(text: str) -> None:
                nonlocal last_ui_state
                if text != last_ui_state:
                    last_ui_state = text
                    self.signals.daily_task_state.emit(text)

            def stable(first: tuple[int, int] | None, second: tuple[int, int] | None) -> bool:
                if first is None or second is None:
                    return first is second
                return abs(first[0] - second[0]) <= 16 and abs(first[1] - second[1]) <= 16

            def match_reviewed_gather_search(
                image: Image.Image,
            ) -> tuple[tuple[int, int] | None, float]:
                """Keep local-map and resource-overview search proofs separate."""

                point, score = match_daily_gather_world_search(image, threshold)
                if point is not None:
                    return point, score
                overview_point, overview_score = match_daily_world_overview_search_entry(
                    image, threshold
                )
                if overview_point is not None:
                    return overview_point, overview_score
                return None, max(score, overview_score)

            def match_reviewed_world_town_entry(
                image: Image.Image,
            ) -> tuple[tuple[int, int] | None, float]:
                """Accept Town only from a reviewed local or overview map."""

                point, score = match_daily_world_town_entry(image, threshold)
                if point is not None:
                    return point, score
                overview_point, overview_score = match_daily_world_overview_search_entry(
                    image, threshold
                )
                if overview_point is not None:
                    return map_content_point((1330, 2395), (1440, 2560), image), overview_score
                return None, max(score, overview_score)

            def match_reviewed_city_daily_entry(
                image: Image.Image,
            ) -> tuple[tuple[int, int] | None, float]:
                """Accept the Daily entry only with the same-frame city side.

                The left task icon alone is not enough after a gather route:
                overview/map artwork can transiently resemble that small
                crop.  The exact right-side Wilderness icon independently
                proves the main city before the Daily coordinate is exposed.
                """

                daily_point, daily_score = match_daily_city_entry(image, threshold)
                wilderness_point, wilderness_score = match_daily_city_wilderness_entry(
                    image, threshold
                )
                if daily_point is None or wilderness_point is None:
                    return None, max(daily_score, wilderness_score)
                return daily_point, min(daily_score, wilderness_score)

            def observe(state: DailyTaskState, point: tuple[int, int] | None) -> int:
                nonlocal last_state, last_point, state_streak
                if state is last_state and stable(point, last_point):
                    state_streak += 1
                else:
                    last_state, state_streak = state, 1
                last_point = point
                return state_streak

            def observe_abnormal_exit(
                kind: DailyAbnormalExitKind,
                point: tuple[int, int] | None,
            ) -> int:
                nonlocal abnormal_exit_kind, abnormal_exit_point, abnormal_exit_streak
                if kind is abnormal_exit_kind and stable(point, abnormal_exit_point):
                    abnormal_exit_streak += 1
                else:
                    abnormal_exit_kind = kind
                    abnormal_exit_point = point
                    abnormal_exit_streak = 1
                return abnormal_exit_streak

            def restart_daily_list_scan() -> None:
                """Require a freshly proven top boundary before another scan."""
                nonlocal daily_scrolls
                nonlocal daily_list_reset_pending, daily_list_reset_swipes
                nonlocal daily_list_reset_before_image, daily_list_reset_boundary_streak
                nonlocal daily_list_reset_settle_image
                nonlocal daily_list_fast_anchor_miss_streak
                nonlocal daily_list_scan_before_image, daily_list_bottom_boundary_streak
                nonlocal daily_completed_zone_streak
                daily_scrolls = 0
                daily_list_reset_pending = True
                daily_list_reset_swipes = 0
                daily_list_reset_before_image = None
                daily_list_reset_settle_image = None
                daily_list_reset_boundary_streak = 0
                daily_list_fast_anchor_miss_streak = 0
                daily_list_scan_before_image = None
                daily_list_bottom_boundary_streak = 0
                daily_completed_zone_streak = 0

            def send_daily_fast_top_gesture(image: Image.Image) -> bool:
                """Send one inertial list-only fling and retain its exact before frame."""

                nonlocal daily_list_reset_before_image, daily_list_reset_settle_image
                nonlocal daily_list_reset_swipes
                if daily_list_reset_swipes >= DAILY_TASK_LIST_FAST_TOP_MAX_GESTURES:
                    return False
                fast_x1, fast_y1, fast_x2, fast_y2, fast_duration = (
                    DAILY_TASK_LIST_FAST_TOP_SWIPE
                )
                start_point = map_content_point((fast_x1, fast_y1), (1440, 2560), image)
                end_point = map_content_point((fast_x2, fast_y2), (1440, 2560), image)
                daily_list_reset_before_image = image.copy()
                daily_list_reset_settle_image = None
                target.shell(
                    [
                        "input",
                        "swipe",
                        str(start_point[0]),
                        str(start_point[1]),
                        str(end_point[0]),
                        str(end_point[1]),
                        str(fast_duration),
                    ]
                )
                daily_list_reset_swipes += 1
                last = daily_list_reset_swipes
                set_state(
                    "每日任务列表已在验证通道高速回顶，检查是否真实移动"
                    f"（{last}/{DAILY_TASK_LIST_FAST_TOP_MAX_GESTURES}）"
                )
                self._log_for_device(
                    target.device,
                    "每日任务重新扫描前已在 x=900 列表通道执行一次 90ms 高速长滑回顶；"
                    f"等待轻量像素复核（{last}/{DAILY_TASK_LIST_FAST_TOP_MAX_GESTURES}）。",
                )
                return True

            def mission_label(kind: DailyMissionKind) -> str:
                return {
                    DailyMissionKind.GATHER_MEAT: "生肉",
                    DailyMissionKind.GATHER_WOOD: "木材",
                    DailyMissionKind.GATHER_COAL: "煤炭",
                    DailyMissionKind.GATHER_IRON: "铁矿",
                    DailyMissionKind.TRAIN_SHIELD: "盾兵",
                    DailyMissionKind.TRAIN_SPEAR: "矛兵",
                    DailyMissionKind.TRAIN_ARCHER: "射手",
                    DailyMissionKind.UPGRADE_BUILDING: "建筑升级",
                    DailyMissionKind.PROCESS_INTEL: "情报线索",
                    DailyMissionKind.WAREHOUSE_SUPPLY: "仓库补给",
                    DailyMissionKind.HERO_RECRUIT: "英雄招募",
                    DailyMissionKind.ALLIANCE_DONATE: "联盟捐献",
                }[kind]

            def daily_idle_wait_plan(
                image: Image.Image,
                activity_points: float,
                activity_confidence: float,
            ) -> tuple[float, str, bool, str]:
                """Choose the earliest passive retry without releasing a queue lock."""
                refresh_visible, _refresh_score = match_daily_task_refresh_label(image)
                monotonic_now = time.monotonic()
                epoch_now = time.time()
                idle_wait_seconds = float(
                    DAILY_IDLE_STATIC_REFRESH_RETRY_SECONDS
                    if refresh_visible
                    else DAILY_IDLE_FALLBACK_RETRY_SECONDS
                )
                idle_wait_reason = "每日静态刷新" if refresh_visible else "保守复查"
                retry_candidates: list[tuple[float, str]] = []

                def add_monotonic_retry(deadline: float, reason: str) -> None:
                    # A deadline is a one-shot wake boundary, not a permanent
                    # zero-second retry.  Once it has elapsed the current scan
                    # is already the promised recheck; if that scan finds no
                    # actionable card, fall back to the normal <=30-second
                    # passive wait instead of rescanning the completed zone
                    # every loop interval.
                    if deadline > monotonic_now:
                        retry_candidates.append((deadline - monotonic_now, reason))

                def add_epoch_retry(deadline: float, reason: str) -> None:
                    if deadline > epoch_now:
                        retry_candidates.append((deadline - epoch_now, reason))

                add_epoch_retry(warehouse_supply_recheck_at, "仓库补给")
                add_epoch_retry(hero_recruit_recheck_at, "绿色免费招募")
                add_epoch_retry(alliance_donation_retry_at, "联盟捐献")
                add_epoch_retry(
                    failed_training_retry_epoch if failed_training_kinds else 0.0,
                    "训练失败复查",
                )
                for deadline in deferred_training_recheck_at.values():
                    add_monotonic_retry(deadline, "自然练兵")
                add_monotonic_retry(gather_cards_suppressed_until, "采集队列")
                add_monotonic_retry(
                    active_gather_recheck_at if active_gather_kind is not None else 0.0,
                    "当前采集",
                )
                add_monotonic_retry(
                    inherited_gather_recheck_at if inherited_gather_slot_active else 0.0,
                    "既有采集",
                )
                for deadline in deferred_gather_recheck_at.values():
                    add_monotonic_retry(deadline, "采集让行")

                if retry_candidates:
                    next_wait, next_reason = min(retry_candidates, key=lambda item: item[0])
                    if next_wait < idle_wait_seconds:
                        idle_wait_seconds = next_wait
                        idle_wait_reason = next_reason
                idle_wait_seconds = max(float(interval), idle_wait_seconds)
                if idle_wait_seconds < 60.0:
                    idle_wait_label = (
                        f"{idle_wait_reason} {max(1, round(idle_wait_seconds))} 秒"
                    )
                else:
                    idle_wait_label = (
                        f"{idle_wait_reason}约 "
                        f"{max(1, round(idle_wait_seconds / 60.0))} 分钟"
                    )
                estimated = f"{activity_points:.0f}" if activity_confidence >= 0.40 else "未可靠读取"
                return idle_wait_seconds, idle_wait_label, refresh_visible, estimated

            def wait_for_gather_step(
                label: str,
                probe: Callable[[Image.Image], tuple[tuple[int, int] | None, float]],
                timeout: float,
            ) -> tuple[Image.Image, tuple[int, int]] | None:
                """Wait for one reviewed gathering control across two frames.

                The helper deliberately owns no fallback taps.  A missed
                control, payment page, another game screen, or an expired
                route simply returns ``None`` to the caller, which stops this
                daily run without recovery input.
                """
                deadline = time.monotonic() + bounded_step_timeout(timeout)
                prior_point: tuple[int, int] | None = None
                streak = 0
                while not self.stop_event.is_set() and time.monotonic() < deadline:
                    if duration and time.monotonic() - started >= duration * 60:
                        return None
                    if guard and not cached_foreground_is_game():
                        set_state("已暂停：游戏不在模拟器前台")
                        if self.stop_event.wait(interval):
                            return None
                        continue
                    image = capture_daily_image()
                    # A payment surface wins over every gathering stage.  The
                    # existing daily blocker uses narrow, reviewed anchors and
                    # does not treat an ordinary world-map screen as payment.
                    page = detect_daily_task_state(image, threshold)
                    if page.state is getattr(DailyTaskState, "BLOCKED", None):
                        self._log_for_device(target.device, f"采集流程在{label}看到付费页面；未输入并停止。")
                        return None
                    point, _score = probe(image)
                    if point and stable(point, prior_point):
                        streak += 1
                    elif point:
                        prior_point, streak = point, 1
                    else:
                        prior_point, streak = None, 0
                    if streak >= 2 and point:
                        return image, point
                    set_state(f"等待已验证的{label}（{streak}/2）")
                    if self.stop_event.wait(interval):
                        return None
                return None

            def wait_for_gather_selector(timeout: float) -> Image.Image | None:
                """Require two selector frames after our own magnifier click."""
                deadline = time.monotonic() + bounded_step_timeout(timeout)
                streak = 0
                while not self.stop_event.is_set() and time.monotonic() < deadline:
                    if duration and time.monotonic() - started >= duration * 60:
                        return None
                    if guard and not cached_foreground_is_game():
                        set_state("已暂停：游戏不在模拟器前台")
                        if self.stop_event.wait(interval):
                            return None
                        continue
                    image = capture_daily_image()
                    page = detect_daily_task_state(image, threshold)
                    if page.state is getattr(DailyTaskState, "BLOCKED", None):
                        self._log_for_device(target.device, "资源筛选页检测到付费页面；未输入并停止。")
                        return None
                    if daily_gather_selector_is_valid(image):
                        streak += 1
                        if streak >= 2:
                            return image
                    else:
                        streak = 0
                    set_state(f"确认普通资源筛选页（{streak}/2）")
                    if self.stop_event.wait(interval):
                        return None
                return None

            def wait_for_full_resources_filter(
                timeout: float,
            ) -> tuple[str, Image.Image, tuple[int, int] | None] | None:
                """Resolve only the reviewed full-resource selector setting.

                ``off`` carries the exact visible square that may be tapped.
                ``enabled`` is only returned after two stable selector frames
                match the separately reviewed green checked state.  No generic
                checkbox logic or coordinate guessing is permitted here.
                """
                deadline = time.monotonic() + bounded_step_timeout(timeout)
                prior_off: tuple[int, int] | None = None
                off_streak = 0
                enabled_streak = 0
                while not self.stop_event.is_set() and time.monotonic() < deadline:
                    if duration and time.monotonic() - started >= duration * 60:
                        return None
                    if guard and not cached_foreground_is_game():
                        set_state("已暂停：游戏不在模拟器前台")
                        if self.stop_event.wait(interval):
                            return None
                        continue
                    image = capture_daily_image()
                    page = detect_daily_task_state(image, threshold)
                    if page.state is getattr(DailyTaskState, "BLOCKED", None):
                        self._log_for_device(target.device, "满资源筛选页检测到付费页面；未输入并停止。")
                        return None
                    off_point, _off_score = match_daily_gather_full_resources_filter_off(image, threshold)
                    if off_point and stable(off_point, prior_off):
                        off_streak += 1
                    elif off_point:
                        prior_off, off_streak = off_point, 1
                    else:
                        prior_off, off_streak = None, 0
                    if off_streak >= 2 and off_point:
                        return "off", image, off_point
                    if not off_point and daily_gather_full_resources_filter_is_enabled(image, threshold):
                        enabled_streak += 1
                        if enabled_streak >= 2:
                            return "enabled", image, None
                    else:
                        enabled_streak = 0
                    set_state(f"确认仅满资源筛选状态（未选 {off_streak}/2，已选 {enabled_streak}/2）")
                    if self.stop_event.wait(interval):
                        return None
                return None

            def wait_for_gather_formation_capacity(
                label: str,
                required_amount: int,
            ) -> tuple[str, tuple[int, int], int, int] | None:
                """Prove ordinary Dispatch, troops, and carry in two frames.

                ``ready`` permits the caller's one Dispatch tap.  An
                ``insufficient`` result authorises no dispatch; it exists so
                non-Iron resources can safely leave this exact formation page
                and let later Daily items run.  Iron keeps the user's explicit
                stop-on-shortage rule in the caller.
                """
                prior: tuple[tuple[int, int], int, int] | None = None
                streak = 0
                full_modal_streak = 0
                deadline = time.monotonic() + AUTOMATION_STEP_TIMEOUT_SECONDS
                while not self.stop_event.is_set() and time.monotonic() < deadline:
                    image = capture_daily_image()
                    page = detect_daily_task_state(image, threshold)
                    if page.state is getattr(DailyTaskState, "BLOCKED", None):
                        if any(anchor == "march_capacity_modal" for anchor, _point in page.anchors):
                            full_modal_streak += 1
                            if full_modal_streak >= 2:
                                return "queue_full", (0, 0), 0, 0
                            continue
                        self._log_for_device(
                            target.device,
                            f"{label}编队页出现付费或扩容阻断；未点击出征。",
                        )
                        return None
                    full_modal_streak = 0
                    dispatch_point, _dispatch_score = match_daily_gather_dispatch_button(
                        image, threshold
                    )
                    formation = read_daily_gather_formation_capacity(image)
                    if dispatch_point is not None and formation is not None:
                        if formation.selected_troops <= 0:
                            self._log_for_device(
                                target.device,
                                f"{label}编队复核为 0 名已选兵力；未点击出征。",
                            )
                            return None
                        current = (
                            dispatch_point,
                            formation.selected_troops,
                            formation.carrying_capacity,
                        )
                        if prior is not None and stable(dispatch_point, prior[0]) and current[1:] == prior[1:]:
                            streak += 1
                        else:
                            prior, streak = current, 1
                        if streak >= 2:
                            if formation.carrying_capacity < required_amount:
                                self._log_for_device(
                                    target.device,
                                    f"{label}编队已双帧确认负重 {formation.carrying_capacity:,} 低于任务量 "
                                    f"{required_amount:,}；未点击出征。",
                                )
                                return (
                                    "insufficient",
                                    dispatch_point,
                                    formation.selected_troops,
                                    formation.carrying_capacity,
                                )
                            self._log_for_device(
                                target.device,
                                f"{label}编队已双帧确认：选兵 {formation.selected_troops:,}，"
                                f"负重 {formation.carrying_capacity:,}，任务量 {required_amount:,}。",
                            )
                            return "ready", *current
                    else:
                        prior, streak = None, 0
                    set_state(f"{label}采集：快速复核普通出征、兵力与负重（{streak}/2）")
                    if self.stop_event.wait(max(interval, 0.15)):
                        return None
                self._log_for_device(
                    target.device,
                    f"{label}编队在 30 秒内未双帧确认普通出征、兵力和负重；未点击出征。",
                )
                return None

            def establish_world_resource_level() -> bool:
                """Follow the Word guide and cache the castle's 5/7/9 band."""

                nonlocal resource_level
                if resource_level in (5, 7, 9):
                    return True
                globe_stage = wait_for_gather_step(
                    "王国总览入口",
                    lambda image: match_daily_world_overview_entry(image, threshold),
                    12.0,
                )
                if not globe_stage:
                    self._log_for_device(
                        target.device,
                        "采矿区域预检未双帧确认王国总览入口；未打开搜索或派遣。",
                    )
                    return False
                _world_image, globe_point = globe_stage
                target.tap(*globe_point)
                self._log_for_device(
                    target.device,
                    f"采矿区域预检：点击双帧确认的王国总览入口 {globe_point}。",
                )

                # The castle-home button is transient and can appear at any
                # map edge.  Search only its tiny template in the first fresh
                # overview frames; do not wait for slower page/resource
                # classification before clicking it.
                fast_home_started = time.monotonic()
                fast_home_deadline = fast_home_started + 2.2
                fast_home_sent = False
                while (
                    not self.stop_event.is_set()
                    and time.monotonic() < fast_home_deadline
                ):
                    try:
                        first_overview = target.fast_window_screenshot(_world_image.size)
                    except AdbError as exc:
                        self._log_for_device(
                            target.device,
                            f"采矿区域预检：MuMu 快速窗口截图不可用（{exc}）；"
                            "未用过期ADB帧点击临时小房子，未搜索或派遣。",
                        )
                        return False
                    fast_home_point, fast_home_score = (
                        match_daily_world_overview_home_button_fast(first_overview, 0.76)
                    )
                    if fast_home_point:
                        target.tap(*fast_home_point)
                        fast_home_sent = True
                        elapsed_ms = round((time.monotonic() - fast_home_started) * 1000)
                        self._log_for_device(
                            target.device,
                            "采矿区域预检：地球点击后的全屏小房子快通道已命中并立即点击 "
                            f"{fast_home_point}（相似度 {fast_home_score:.3f}，{elapsed_ms}ms）；"
                            "距离文字和按钮方向均不参与判断。",
                        )
                        break
                    if self.stop_event.wait(0.03):
                        return False

                deadline = time.monotonic() + AUTOMATION_STEP_TIMEOUT_SECONDS
                prior_off: tuple[int, int] | None = None
                off_streak = 0
                resource_toggle_sent = False
                home_candidate: tuple[int, int] | None = None
                home_streak = 0
                home_sent = fast_home_sent
                level_candidate: int | None = None
                level_streak = 0
                search_candidate: tuple[int, int] | None = None
                search_streak = 0
                while not self.stop_event.is_set() and time.monotonic() < deadline:
                    image = daily_screenshot()
                    off_point, off_score = match_daily_world_overview_resource_off(
                        image, threshold
                    )
                    enabled = daily_world_overview_resource_is_enabled(
                        image, threshold
                    )
                    if enabled:
                        prior_off, off_streak = None, 0
                        home_point, home_score = match_daily_world_overview_home_button(
                            image, threshold
                        )
                        if home_point and not home_sent:
                            if stable(home_point, home_candidate):
                                home_streak += 1
                            else:
                                home_candidate, home_streak = home_point, 1
                            level_candidate, level_streak = None, 0
                            search_candidate, search_streak = None, 0
                            if home_streak >= 2:
                                target.tap(*home_point)
                                home_sent = True
                                home_candidate, home_streak = None, 0
                                self._log_for_device(
                                    target.device,
                                    "采矿区域预检：已双帧确认并点击自己的蓝色小房子 "
                                    f"{home_point}（相似度 {home_score:.3f}）；"
                                    "等待绿色城堡坐标进入主地图。",
                                )
                            if self.stop_event.wait(max(interval, 0.20)):
                                return False
                            continue
                        if home_point and home_sent:
                            level_candidate, level_streak = None, 0
                            search_candidate, search_streak = None, 0
                            if self.stop_event.wait(max(interval, 0.20)):
                                return False
                            continue
                        home_candidate, home_streak = None, 0
                        search_point, search_score = match_daily_world_overview_search_entry(
                            image, threshold
                        )
                        if search_point and stable(search_point, search_candidate):
                            search_streak += 1
                        elif search_point:
                            search_candidate, search_streak = search_point, 1
                        else:
                            search_candidate, search_streak = None, 0
                        candidate = detect_world_resource_level(image)
                        if candidate in (5, 7, 9) and candidate == level_candidate:
                            level_streak += 1
                        elif candidate in (5, 7, 9):
                            level_candidate, level_streak = candidate, 1
                        else:
                            level_candidate, level_streak = None, 0
                        if (
                            level_streak >= 2
                            and level_candidate is not None
                            and search_streak >= 2
                        ):
                            resource_level = level_candidate
                            self._log_for_device(
                                target.device,
                                "采矿区域预检：资源图层与绿色城堡坐标所在色带均已双帧确认；"
                                f"本进程使用普通 {resource_level} 级矿；"
                                "世界搜索入口也已双帧确认"
                                f"（相似度 {search_score:.3f}），直接继续且不发送返回键。",
                            )
                            return True
                    elif off_point and not resource_toggle_sent:
                        level_candidate, level_streak = None, 0
                        if stable(off_point, prior_off):
                            off_streak += 1
                        else:
                            prior_off, off_streak = off_point, 1
                        if off_streak >= 2:
                            target.tap(*off_point)
                            resource_toggle_sent = True
                            prior_off, off_streak = None, 0
                            self._log_for_device(
                                target.device,
                                "采矿区域预检：点击双帧确认的资源空框 "
                                f"{off_point}（相似度 {off_score:.3f}）；等待绿色勾选。",
                            )
                    else:
                        prior_off, off_streak = None, 0
                        level_candidate, level_streak = None, 0
                        search_candidate, search_streak = None, 0
                        home_candidate, home_streak = None, 0
                    if self.stop_event.wait(max(interval, 0.20)):
                        return False
                self._log_for_device(
                    target.device,
                    "采矿区域预检在 30 秒内未获得资源勾选、绿色城堡坐标与一致的 5/7/9；"
                    "未打开搜索或派遣。",
                )
                return False

            def confirm_daily_free_march_capacity(label: str, *, require_empty: bool = False) -> bool | None:
                """Double-confirm a free slot immediately before a gather route.

                A visible ``used/total`` header is authoritative.  When a
                completely idle map hides that header, one bootstrap dispatch
                is allowed only after two exact world-map frames prove that no
                active march panel exists; the post-dispatch header then
                teaches this process the account total.  Unknown active state,
                a full header, or inconsistent digits fails closed.
                """
                nonlocal known_march_total, bootstrap_dispatch_used
                nonlocal gather_cards_suppressed_until, active_gather_recheck_at
                prior_capacity: tuple[int, int] | None = None
                capacity_streak = 0
                idle_without_header_streak = 0
                deadline = time.monotonic() + AUTOMATION_STEP_TIMEOUT_SECONDS
                while not self.stop_event.is_set() and time.monotonic() < deadline:
                    image = daily_screenshot()
                    world_point, _world_score = match_reviewed_gather_search(image)
                    if world_point is None:
                        prior_capacity, capacity_streak = None, 0
                        idle_without_header_streak = 0
                    else:
                        capacity = read_daily_march_capacity(image)
                        if capacity is not None:
                            idle_without_header_streak = 0
                            current = (capacity.used, capacity.total)
                            if current == prior_capacity:
                                capacity_streak += 1
                            else:
                                prior_capacity, capacity_streak = current, 1
                            if capacity_streak >= 2:
                                known_march_total = capacity.total
                                if capacity.free <= 0 or (require_empty and capacity.used != 0):
                                    # Full capacity is passive business state,
                                    # but this all-gather suppression is still a
                                    # retry lock and therefore expires in <=30s.
                                    retry_seconds = 10.0 if require_empty else DAILY_RETRY_LOCK_MAX_SECONDS
                                    gather_cards_suppressed_until = time.monotonic() + retry_seconds
                                    active_gather_recheck_at = gather_cards_suppressed_until
                                    reason = "同类采集尚未证明全部返回" if require_empty else "没有空闲队列"
                                    self._log_for_device(
                                        target.device,
                                        f"{label}采集：连续两帧复核行军 {capacity.used}/{capacity.total}，"
                                        f"{reason}；未打开搜索或派遣。暂缓 {retry_seconds:g} 秒并继续独立任务。",
                                    )
                                    return None
                                self._log_for_device(
                                    target.device,
                                    f"{label}采集：连续两帧复核行军 {capacity.used}/{capacity.total}，"
                                    f"当前可用 {capacity.free} 队；允许本次普通采集继续。",
                                )
                                return True
                        else:
                            prior_capacity, capacity_streak = None, 0
                            if not require_empty and not daily_gather_march_is_active(image, threshold):
                                idle_without_header_streak += 1
                                if idle_without_header_streak >= 2:
                                    if known_march_total is not None:
                                        self._log_for_device(
                                            target.device,
                                            f"{label}采集：两帧确认地图无活动行军，"
                                            f"沿用本进程已实测总队列 {known_march_total}；允许一队。",
                                        )
                                        return True
                                    if not bootstrap_dispatch_used:
                                        self._log_for_device(
                                            target.device,
                                            f"{label}采集：两帧确认地图无活动行军且容量标题隐藏；"
                                            "仅授权本进程唯一一次引导派遣，派遣后必须读取真实总队列。",
                                        )
                                        return True
                                    self._log_for_device(
                                        target.device,
                                        f"{label}采集：容量标题仍隐藏且本进程引导额度已使用；"
                                        "未打开搜索或派遣。",
                                    )
                                    return False
                            else:
                                idle_without_header_streak = 0
                    set_state(f"{label}采集：快速复核空闲行军容量（{capacity_streak}/2）")
                    if self.stop_event.wait(max(interval, 0.15)):
                        return False
                self._log_for_device(
                    target.device,
                    f"{label}采集在 30 秒内未能双帧证明空闲行军容量；未打开搜索或派遣。",
                )
                return False

            def wait_for_natural_gather_return(label: str, round_index: int, limit: int) -> bool:
                """Passively wait for this run's reviewed ordinary march to end.

                The account used in live testing has one march slot.  The
                panel must first be seen in two frames; only then may two
                later no-panel frames prove its natural return.  A full node
                can temporarily hide that panel while harvesting, so no-panel
                frames are ignored until the conservative ten-minute passive
                observation window has elapsed.  No tap occurs in this loop,
                and an ambiguous panel state stops the run rather than
                guessing.
                """
                elapsed = time.monotonic() - started
                daily_time_remaining = duration * 60.0 - elapsed if duration else DAILY_GATHER_PASSIVE_WAIT_CAP_SECONDS
                passive_wait_limit = min(
                    AUTOMATION_STEP_TIMEOUT_SECONDS,
                    DAILY_GATHER_PASSIVE_WAIT_CAP_SECONDS,
                    max(0.0, daily_time_remaining),
                )
                if passive_wait_limit <= 0.0:
                    self._log_for_device(target.device, f"{label}采集：每日流程时长已到，不再等待或继续输入。")
                    return False
                deadline = time.monotonic() + passive_wait_limit
                seen_active = 0
                absent_after_active = 0
                active_started_at: float | None = None
                last_reported_minutes = -1
                while not self.stop_event.is_set() and time.monotonic() < deadline:
                    if duration and time.monotonic() - started >= duration * 60:
                        return False
                    image = daily_screenshot()
                    if daily_gather_march_is_active(image, threshold):
                        seen_active += 1
                        if active_started_at is None:
                            active_started_at = time.monotonic()
                        absent_after_active = 0
                        if seen_active == 2:
                            self._log_for_device(
                                target.device,
                                f"{label}采集：已确认普通队列自然运行（{round_index + 1}/{limit}）。",
                            )
                    elif (
                        seen_active >= 2
                        and active_started_at is not None
                        # The post-dispatch world map can briefly animate its
                        # side panel away while the one available march slot
                        # is still occupied.  Do not open another selector
                        # until the full-node passive observation guard has
                        # elapsed.  This protects against a transiently hidden
                        # march drawer being misread as a natural return.
                        and time.monotonic() - active_started_at
                        >= DAILY_GATHER_FULL_NODE_MIN_RETURN_SECONDS
                    ):
                        absent_after_active += 1
                        if absent_after_active >= 2:
                            self._log_for_device(
                                target.device,
                                f"{label}采集：已确认普通队列自然返回（{round_index + 1}/{limit}）。",
                            )
                            return True

                    minutes_remaining = max(0, round((deadline - time.monotonic()) / 60.0))
                    if minutes_remaining != last_reported_minutes:
                        last_reported_minutes = minutes_remaining
                        set_state(
                            f"{label}采集中：等待自然返回（{round_index + 1}/{limit}，不使用加速）"
                        )
                        self._log_for_device(
                            target.device,
                            f"{label}采集：被动等待自然返回，最多还等 {minutes_remaining} 分钟；不使用加速。",
                        )
                    if self.stop_event.wait(max(interval, 0.20)):
                        return False
                if seen_active < 2:
                    self._log_for_device(target.device, f"{label}采集未双帧确认行军队列；未继续输入。")
                else:
                    self._log_for_device(target.device, f"{label}采集等待自然返回超时；未继续输入。")
                return False

            def prune_saved_runtime_evidence(directory: Path, keep_latest: int = 24) -> None:
                """Keep runtime screenshots bounded; curated milestones are untouched.

                Recognition always consumes a fresh ADB frame and never reads
                these files.  This rolling cleanup only covers account-free
                runtime crops under LocalAppData, preventing stale screenshots
                from accumulating or being mistaken for current evidence.
                """
                try:
                    removed = prune_runtime_evidence(directory, keep_latest)
                    if removed:
                        self._log_for_device(
                            target.device,
                            f"运行时截图滚动清理：{directory.name} 已删除 {removed} 张最旧裁剪，"
                            f"仅保留最近 {max(1, keep_latest)} 张；识图仍只使用实时ADB帧。",
                        )
                except OSError as exc:
                    self._log_for_device(target.device, f"运行时截图滚动清理失败：{exc}")

            def record_active_gather_countdown(kind: DailyMissionKind) -> bool:
                """Double-check and persist the non-identifying countdown strip.

                This adds no game input.  It gives the scheduler a reviewed
                record that this march is occupied before it returns to Daily
                Tasks to work on independent items.  When the idle map hid its
                capacity title, the same passive frames must also learn the
                account's real total before another dispatch can be considered.
                """
                nonlocal active_gather_kind, active_gather_observed_at, active_gather_recheck_at
                nonlocal known_march_total
                # Dispatch has already been proved twice and tapped exactly
                # once before this helper runs.  Lock the gather immediately:
                # the animated march card may appear later than the short
                # evidence window, but that delay must never permit another
                # gather card or block independent Daily items.
                observed_at = time.monotonic()
                active_gather_kind = kind
                dispatched_gather_kinds.add(kind)
                active_gather_observed_at = observed_at
                active_gather_recheck_at = observed_at + DAILY_GATHER_FULL_NODE_MIN_RETURN_SECONDS
                # The dispatch and its formation/carry proof happened before
                # this passive countdown observation. The deadline schedules
                # an observation, not a dispatch: the durable same-kind lock
                # survives until two explicit zero-used world frames prove
                # every march has returned. The old passive wait cap remains
                # relevant to the separate natural-return monitor.
                defer_gather_kind(
                    kind,
                    DAILY_GATHER_FULL_NODE_MIN_RETURN_SECONDS,
                    natural_queue=True,
                )
                countdown: Image.Image | None = None
                # The verified dispatch control can close in the same frame
                # while MuMu is still animating the compact march strip in.
                # Observe only for a bounded settle window rather than
                # declaring the already-sent normal expedition absent. Two
                # consecutive strip matches remain mandatory before the
                # worker is allowed to return to Daily Tasks.
                if self.stop_event.wait(max(interval, 0.20)):
                    return False
                matched_frames = 0
                capacity_candidate: tuple[int, int] | None = None
                capacity_streak = 0
                deadline = time.monotonic() + 12.0
                while not self.stop_event.is_set() and time.monotonic() < deadline:
                    image = daily_screenshot()
                    capacity = read_daily_march_capacity(image)
                    if capacity is not None:
                        current_capacity = (capacity.used, capacity.total)
                        if current_capacity == capacity_candidate:
                            capacity_streak += 1
                        else:
                            capacity_candidate, capacity_streak = current_capacity, 1
                        if capacity_streak >= 2:
                            known_march_total = capacity.total
                    else:
                        capacity_candidate, capacity_streak = None, 0
                    candidate = daily_gather_remaining_time_crop(image, threshold)
                    if candidate is None:
                        matched_frames = 0
                    else:
                        countdown = candidate
                        matched_frames += 1
                        if matched_frames >= 2:
                            break
                    if self.stop_event.wait(max(interval, 0.20)):
                        return False
                if matched_frames < 2 or countdown is None:
                    self._log_for_device(
                        target.device,
                        f"{mission_label(kind)}采集在 12 秒观察窗内未能连续两帧识图记录倒计时；"
                        "已保留精确派遣后的占槽锁，时间记为未知并继续返回每日任务处理独立项目。",
                    )
                    return True
                record_path: Path | None = None
                try:
                    record_dir = CONFIG_DIR / "evidence" / "gather_countdowns"
                    record_dir.mkdir(parents=True, exist_ok=True)
                    record_path = record_dir / f"gather_countdown_{time.strftime('%Y%m%d-%H%M%S')}.png"
                    countdown.save(record_path, optimize=True)
                    prune_saved_runtime_evidence(record_dir)
                except OSError as exc:
                    self._log_for_device(target.device, f"{mission_label(kind)}采集倒计时已识图，但安全裁剪保存失败：{exc}")
                if record_path:
                    self._log_for_device(
                        target.device,
                        f"{mission_label(kind)}采集：已双帧识图记录无账号的倒计时裁剪 {record_path.name}；"
                        "现在继续处理不占行军队列的每日事项。",
                    )
                else:
                    self._log_for_device(
                        target.device,
                        f"{mission_label(kind)}采集：已双帧识图确认倒计时可见；现在继续处理不占行军队列的每日事项。",
                    )
                return True

            def record_active_training_countdown(label: str) -> Image.Image | None:
                """Double-confirm and save one account-free training timer crop."""
                countdown: Image.Image | None = None
                last_image: Image.Image | None = None
                matched_frames = 0
                deadline = time.monotonic() + 8.0
                while not self.stop_event.is_set() and time.monotonic() < deadline:
                    image = daily_screenshot()
                    candidate = daily_training_remaining_time_crop(image, threshold)
                    if candidate is None:
                        matched_frames = 0
                    else:
                        countdown = candidate
                        last_image = image
                        matched_frames += 1
                        if matched_frames >= 2:
                            break
                    if self.stop_event.wait(max(interval, 0.15)):
                        return None
                if matched_frames < 2 or countdown is None or last_image is None:
                    self._log_for_device(target.device, f"{label}训练未能双帧识图记录自然队列倒计时；未离开训练页。")
                    return None
                record_path: Path | None = None
                try:
                    record_dir = CONFIG_DIR / "evidence" / "training_countdowns"
                    record_dir.mkdir(parents=True, exist_ok=True)
                    record_path = record_dir / f"training_countdown_{time.strftime('%Y%m%d-%H%M%S')}.png"
                    countdown.save(record_path, optimize=True)
                    prune_saved_runtime_evidence(record_dir)
                except OSError as exc:
                    self._log_for_device(target.device, f"{label}训练倒计时已识图，但安全裁剪保存失败：{exc}")
                if record_path:
                    self._log_for_device(
                        target.device,
                        f"{label}训练：已双帧识图记录无账号的倒计时裁剪 {record_path.name}；"
                        "现在继续处理不占训练队列的每日事项。",
                    )
                else:
                    self._log_for_device(
                        target.device,
                        f"{label}训练：已双帧识图确认自然队列；现在继续处理不占训练队列的每日事项。",
                    )
                return last_image

            def record_documented_daily_evidence(
                image: Image.Image,
                label: str,
                note: str,
            ) -> Path | None:
                """Save one account-free central crop plus a compact note."""
                try:
                    viewport = content_viewport(image)
                    crop_box = (
                        viewport.left + round(viewport.width * 0.06),
                        viewport.top + round(viewport.height * 0.17),
                        viewport.left + round(viewport.width * 0.94),
                        viewport.top + round(viewport.height * 0.84),
                    )
                    evidence_dir = CONFIG_DIR / "evidence" / "documented_daily_tasks"
                    evidence_dir.mkdir(parents=True, exist_ok=True)
                    stamp = time.strftime("%Y%m%d-%H%M%S")
                    path = evidence_dir / f"{clean_name(label)}_{stamp}.png"
                    image.crop(crop_box).save(path, optimize=True)
                    prune_saved_runtime_evidence(evidence_dir)
                    with (evidence_dir / "run-notes.md").open("a", encoding="utf-8") as handle:
                        handle.write(f"- {time.strftime('%Y-%m-%d %H:%M:%S')} `{path.name}` — {note}\n")
                    return path
                except OSError as exc:
                    self._log_for_device(target.device, f"文档任务留证失败：{exc}")
                    return None

            def run_arena_plan() -> bool:
                """Run only reviewed free Arena attempts, then reopen Daily.

                The only entry lineage is the exact one-attempt Daily card.
                Once inside, all currently remaining free attempts are drained
                to zero without revisiting Daily between fights.  The caller
                returns once so the ordinary exact-claim loop can collect both
                completed Arena rows.  No plus, refresh, shop or paid attempt
                coordinate exists in this route.
                """

                def wait_state(label: str, probe: Callable[[Image.Image], object | None],
                               timeout: float = 12.0):
                    deadline = time.monotonic() + bounded_step_timeout(timeout)
                    prior = None
                    streak = 0
                    while not self.stop_event.is_set() and time.monotonic() < deadline:
                        image = capture_daily_image()
                        if detect_daily_task_state(image, threshold).state is DailyTaskState.BLOCKED:
                            self._log_for_device(
                                target.device, f"竞技场{label}检测到付费页面；未输入并停止。"
                            )
                            return None
                        value = probe(image)
                        signature = repr(value) if value is not None else None
                        if signature and ", score=" in signature:
                            signature = signature.rsplit(", score=", 1)[0]
                        if signature is not None and signature == prior:
                            streak += 1
                        elif signature is not None:
                            prior, streak = signature, 1
                        else:
                            prior, streak = None, 0
                        if streak >= 2:
                            return image, value
                        set_state(f"竞技场：双帧确认{label}（{streak}/2）")
                        if adaptive_operation_wait(maximum=0.25):
                            return None
                    return None

                home_step = wait_state(
                    "万国竞技场首页和免费次数",
                    lambda frame: match_arena_home(frame, threshold),
                )
                if not home_step:
                    return False
                _home_image, home = home_step
                if home.remaining <= 0 or home.challenge_point is None:
                    self._log_for_device(target.device, "竞技场没有可证明的免费挑战次数；未点击挑战。")
                    return False
                target.tap(*home.challenge_point)
                completed = 0
                list_state = None
                while not self.stop_event.is_set():
                    list_step = wait_state(
                        "挑战列表、我方战力、五名对手战力及剩余次数",
                        lambda frame: match_arena_opponent_list(frame, threshold),
                    )
                    if not list_step:
                        return False
                    _list_image, list_state = list_step
                    if list_state.remaining == 0:
                        break
                    safest = list_state.safest()
                    if safest is None:
                        self._log_for_device(
                            target.device,
                            "竞技场五名对手中没有战力严格低于我方者；未刷新、未点加号、未付费。",
                        )
                        return False
                    before_remaining = list_state.remaining
                    target.tap(*safest.fight_point)
                    setup_step = wait_state(
                        "小队设置战力优势、五英雄和绿色战斗",
                        lambda frame: match_arena_setup(frame, threshold),
                    )
                    if not setup_step:
                        return False
                    _setup_image, setup = setup_step
                    if (
                        setup.my_power <= setup.opponent_power
                        or setup.selected_heroes != 5
                        or abs(setup.opponent_power - safest.power) > 5_000
                    ):
                        self._log_for_device(
                            target.device, "竞技场阵容复核与所选最低战力对手不一致；未点击战斗。"
                        )
                        return False
                    target.tap(*setup.battle_point)
                    def match_arena_result(frame: Image.Image):
                        point, _score = match_arena_result_exit(
                            frame, threshold
                        )
                        # The result art can animate while the exact complete
                        # exit phrase stays at one reviewed safe point.
                        return (point,) if point is not None else None

                    result_step = wait_state(
                        "胜负结算的点击任意位置退出文字",
                        match_arena_result,
                        30.0,
                    )
                    if not result_step:
                        return False
                    _result_image, result = result_step
                    exit_point = result[0]
                    target.tap(*exit_point)
                    after_step = wait_state(
                        "结算后挑战列表与次数减一",
                        lambda frame: match_arena_opponent_list(frame, threshold),
                    )
                    if not after_step:
                        return False
                    _after_image, after = after_step
                    if after.remaining != before_remaining - 1:
                        self._log_for_device(
                            target.device,
                            "竞技场结算后免费次数未恰好减一；未执行下一次挑战。",
                        )
                        return False
                    completed += 1
                    list_state = after
                    self._log_for_device(
                        target.device,
                        f"竞技场免费挑战已验证完成 {completed} 次；剩余 {after.remaining}。",
                    )

                if list_state is None:
                    return False
                target.tap(*list_state.close_point)
                home_return = wait_state(
                    "返回万国竞技场首页",
                    lambda frame: match_arena_home(frame, threshold),
                )
                if not home_return:
                    return False
                home_image, _returned_home = home_return
                target.tap(*map_content_point((70, 75), (1440, 2560), home_image))

                city_step = wait_state(
                    "主城每日任务入口",
                    lambda frame: match_reviewed_city_daily_entry(frame),
                    16.0,
                )
                if not city_step:
                    return False
                _city_image, city_entry = city_step
                target.tap(*city_entry[0])
                def match_returned_daily(frame: Image.Image):
                    state = detect_daily_task_state(frame, threshold)
                    return state if state.state in (
                        DailyTaskState.DAILY_PAGE,
                        DailyTaskState.DAILY_LOGIN_COMPLETED,
                        DailyTaskState.CLAIM_READY,
                        DailyTaskState.TASK_CLAIM_READY,
                    ) else None

                daily_step = wait_state(
                    "返回每日任务页",
                    match_returned_daily,
                    16.0,
                )
                return daily_step is not None

            def run_warehouse_supply_plan() -> bool:
                """Close one immediately correlated Warehouse result quickly.

                The random countdown is never awaited.  Two fresh exact result
                frames are sampled about 0.25 seconds apart, evidence is saved,
                then one neutral upper-left tap closes the sheet.  If it expires
                between proof and tap, that coordinate is inert on Daily Tasks.
                """
                warehouse_daily_states = (
                    DailyTaskState.DAILY_PAGE,
                    DailyTaskState.DAILY_LOGIN_COMPLETED,
                    DailyTaskState.CLAIM_READY,
                    DailyTaskState.TASK_CLAIM_READY,
                )
                # Warehouse settlement timing is random.  One fresh live run
                # returned to the exact Daily page just after the former
                # 16-second boundary.  Use the full shared internal watchdog;
                # sample every 0.25 seconds and close the result as soon as it
                # appears, without ever waiting for its random countdown.
                # The supply bubble is exposed immediately after the verified
                # city transition.  Eight seconds covers the transition and
                # result animation while preventing one unrecognised pose from
                # monopolising the Daily list for nearly half a minute.
                deadline = time.monotonic() + bounded_step_timeout(8.0)
                result_streak = 0
                saw_result = False
                result_image: Image.Image | None = None
                daily_streak = 0
                prior_city: tuple[int, int] | None = None
                city_streak = 0
                city_wait_logged = False
                prior_supply_bubble: tuple[int, int] | None = None
                supply_bubble_streak = 0
                supply_bubble_tapped = False
                post_bubble_deadline: float | None = None
                while not self.stop_event.is_set() and time.monotonic() < deadline:
                    if guard and not cached_foreground_is_game():
                        set_state("已暂停：游戏不在模拟器前台")
                        if self.stop_event.wait(max(interval, 0.25)):
                            return False
                        continue
                    image = daily_screenshot()
                    matched, _score = match_daily_warehouse_result(image, threshold)
                    if matched:
                        saw_result = True
                        result_streak += 1
                        result_image = image
                    else:
                        result_streak = 0
                        if saw_result:
                            page = detect_daily_task_state(image, threshold)
                            if page.state in warehouse_daily_states:
                                self._log_for_device(
                                    target.device,
                                    "仓库补给结果页在关闭输入前自然消失；已确认回到每日任务，不补发点击。",
                                )
                                return True
                        else:
                            # A verified Warehouse ``Go`` can occasionally
                            # fail to navigate and leave us on a known Daily
                            # page or the city.  Two fresh frames may recover
                            # only those exact states; an unknown page still
                            # falls through to the safe stop below.
                            page = detect_daily_task_state(image, threshold)
                            if page.state in warehouse_daily_states:
                                daily_streak += 1
                                city_streak = 0
                                if daily_streak >= 2:
                                    self._log_for_device(
                                        target.device,
                                        "仓库补给结果页未出现；已双帧确认仍在每日任务页（含可领取态），"
                                        "交回统一领取循环并继续后续任务。",
                                    )
                                    return True
                            else:
                                daily_streak = 0
                                if page.state is DailyTaskState.BLOCKED:
                                    self._log_for_device(
                                        target.device,
                                        "仓库补给前往后检测到付费页面；未继续输入。",
                                    )
                                    return False
                                city_point, _score = match_daily_city_entry(image, threshold)
                                if city_point and stable(city_point, prior_city):
                                    city_streak += 1
                                elif city_point:
                                    prior_city, city_streak = city_point, 1
                                else:
                                    prior_city, city_streak = None, 0
                                    prior_supply_bubble, supply_bubble_streak = None, 0
                                if city_streak >= 2 and city_point:
                                    # A reviewed live Warehouse transition can
                                    # remain on the ordinary city for several
                                    # seconds before the correlated result sheet
                                    # appears.  City is therefore only a passive
                                    # fallback proof here: keep polling at 0.25s
                                    # and close the result immediately if it
                                    # arrives.  Re-open Daily only at the bounded
                                    # deadline, never after the first two city
                                    # frames.
                                    if not city_wait_logged:
                                        city_wait_logged = True
                                        self._log_for_device(
                                            target.device,
                                            "仓库补给前往后已双帧确认过渡主城；继续每0.25秒动态识图，"
                                            "结果一出现立即关闭，不把过渡画面误判为失败。",
                                        )
                                    if not supply_bubble_tapped:
                                        supply_bubble, bubble_score = (
                                            match_daily_warehouse_city_supply_bubble(
                                                image, threshold
                                            )
                                        )
                                        if supply_bubble and stable(
                                            supply_bubble, prior_supply_bubble
                                        ):
                                            supply_bubble_streak += 1
                                        elif supply_bubble:
                                            prior_supply_bubble = supply_bubble
                                            supply_bubble_streak = 1
                                        else:
                                            prior_supply_bubble = None
                                            supply_bubble_streak = 0
                                        if supply_bubble_streak >= 2 and supply_bubble:
                                            target.tap(*supply_bubble)
                                            supply_bubble_tapped = True
                                            # The Go-to-city animation may consume
                                            # most of the initial correlation
                                            # window.  Give the already-authorised
                                            # bubble tap its own short result
                                            # window instead of leaving only one
                                            # or two seconds and stopping in a
                                            # 30-second Warehouse retry loop.
                                            post_bubble_deadline = (
                                                time.monotonic()
                                                + bounded_step_timeout(8.0)
                                            )
                                            deadline = max(
                                                deadline, post_bubble_deadline
                                            )
                                            self._log_for_device(
                                                target.device,
                                                "仓库补给过渡主城已双帧确认精确宝箱气泡 "
                                                f"{supply_bubble}（{bubble_score:.4f}）；仅点击一次，"
                                                "随后继续快速识别关联结果页。",
                                            )
                    if result_streak >= 2 and result_image is not None:
                        evidence = record_documented_daily_evidence(
                            result_image,
                            "warehouse_supply_result",
                            "仓库补给结果页已双帧确认；随机倒计时未等待，立即使用固定无控件区关闭。",
                        )
                        exit_point = daily_warehouse_result_exit_point(result_image)
                        target.tap(*exit_point)
                        self._log_for_device(
                            target.device,
                            "仓库补给：已在约 0.25 秒双帧确认后立即点击固定无控件区 "
                            f"{exit_point} 关闭结果页；证据 {evidence.name if evidence else '已识别未落盘'}。",
                        )
                        break
                    set_state(f"快速复核仓库补给结果页（{result_streak}/2）")
                    if self.stop_event.wait(0.25):
                        return False
                else:
                    if (
                        not self.stop_event.is_set()
                        and prior_city is not None
                        and city_streak >= 2
                    ):
                        # No result and no return to Daily were observed during
                        # the complete bounded correlation window.  This exact
                        # Go did not collect supply.  Keep a short account-local
                        # failure backoff so the controller continues lower
                        # Daily items instead of immediately entering a
                        # Warehouse -> Daily -> Warehouse loop.  This is not a
                        # successful three-minute collection deadline.
                        if supply_bubble_tapped:
                            # The exact bubble tap itself already persisted the
                            # account-scoped three-minute Warehouse boundary.
                            # A short-lived result may disappear before two
                            # frames can prove it; two fresh city frames are a
                            # safe continuation proof, but must never downgrade
                            # that boundary to the old 30-second failure retry.
                            self._log_for_device(
                                target.device,
                                "仓库补给精确宝箱气泡已点击；结果页未形成连续双帧，"
                                "但末两帧已确认主城。保留三分钟复查期限并继续后续任务。",
                            )
                        else:
                            defer_warehouse_supply(
                                DAILY_WAREHOUSE_SUPPLY_FAILURE_RETRY_SECONDS
                            )
                        target.tap(*prior_city)
                        self._log_for_device(
                            target.device,
                            "仓库补给关联窗口结束；末两帧仍为精确主城，"
                            f"仅重开每日任务 {prior_city} 后继续。",
                        )
                        return True
                    self._log_for_device(target.device, "仓库补给前往后未在限时内双帧确认结果页；未作任意关闭点击。")
                    return False

                # The normal result overlays the Daily page.  Confirm that
                # page directly; a city-entry fallback is allowed only after
                # its own exact two-frame proof.
                deadline = time.monotonic() + 12.0
                daily_streak = 0
                prior_city: tuple[int, int] | None = None
                city_streak = 0
                while not self.stop_event.is_set() and time.monotonic() < deadline:
                    image = daily_screenshot()
                    page = detect_daily_task_state(image, threshold)
                    if page.state in warehouse_daily_states:
                        daily_streak += 1
                        city_streak = 0
                        if daily_streak >= 2:
                            return True
                    else:
                        daily_streak = 0
                        if page.state is DailyTaskState.BLOCKED:
                            self._log_for_device(target.device, "仓库补给关闭后检测到付费页面；未继续输入。")
                            return False
                        city_point, _score = match_daily_city_entry(image, threshold)
                        if city_point and stable(city_point, prior_city):
                            city_streak += 1
                        elif city_point:
                            prior_city, city_streak = city_point, 1
                        else:
                            prior_city, city_streak = None, 0
                        if city_streak >= 2 and city_point:
                            target.tap(*city_point)
                            self._log_for_device(target.device, f"仓库补给后从已验证主城重开每日任务 {city_point}。")
                            return True
                    if self.stop_event.wait(0.25):
                        return False
                self._log_for_device(target.device, "仓库补给关闭后未确认每日任务或主城入口；未执行恢复点击。")
                return False

            def run_intel_rescue_plan(batch_count: int = 0) -> bool:
                nonlocal intel_failed_scan
                """Drain reviewed Intel clues as one bounded batch.

                Green/grey tents use ordinary Rescue. Crossed swords uses the
                live-proved Hero Journey chain. Every action is independently
                double-confirmed and the batch is capped at five items. Wolves
                still have no inherited matcher or action coordinate.
                """

                daily_states = (
                    DailyTaskState.DAILY_PAGE,
                    DailyTaskState.DAILY_LOGIN_COMPLETED,
                    DailyTaskState.CLAIM_READY,
                    DailyTaskState.TASK_CLAIM_READY,
                )

                def reopen_daily() -> bool:
                    deadline = time.monotonic() + bounded_step_timeout(16.0)
                    daily_streak = city_streak = town_streak = 0
                    prior_city: tuple[int, int] | None = None
                    prior_town: tuple[int, int] | None = None
                    town_sent = False
                    while not self.stop_event.is_set() and time.monotonic() < deadline:
                        image = capture_daily_image()
                        page = detect_daily_task_state(image, threshold)
                        if page.state in daily_states:
                            daily_streak += 1
                            if daily_streak >= 2:
                                return True
                        else:
                            daily_streak = 0
                        city_point, _city_score = match_daily_city_entry(image, threshold)
                        if city_point and stable(city_point, prior_city):
                            city_streak += 1
                        elif city_point:
                            prior_city, city_streak = city_point, 1
                        else:
                            prior_city, city_streak = None, 0
                        if city_streak >= 2 and city_point:
                            target.tap(*city_point)
                            self._log_for_device(
                                target.device,
                                f"情报营救：已从双帧主城重开任务入口 {city_point}。",
                            )
                            return True
                        if not town_sent:
                            town_point, _town_score = match_daily_world_town_entry(
                                image, threshold
                            )
                            if town_point and stable(town_point, prior_town):
                                town_streak += 1
                            elif town_point:
                                prior_town, town_streak = town_point, 1
                            else:
                                prior_town, town_streak = None, 0
                            if town_streak >= 2 and town_point:
                                target.tap(*town_point)
                                town_sent = True
                                city_streak = 0
                                self._log_for_device(
                                    target.device,
                                    f"情报营救：已点击双帧确认的城镇返回 {town_point}。",
                                )
                        if adaptive_operation_wait(maximum=0.45):
                            return False
                    self._log_for_device(
                        target.device,
                        "情报营救结束后未双帧确认城镇、主城入口或每日页；未执行恢复点击。",
                    )
                    return False

                if batch_count >= 5:
                    self._log_for_device(
                        target.device,
                        "情报批次已达到五个已审核线索的安全上限；返回每日任务。",
                    )
                    return reopen_daily()

                def run_intel_hero_plan(swords_point: tuple[int, int]) -> bool:
                    """Execute one exact Hero Journey and stay in this batch."""

                    target.tap(*swords_point)
                    self._log_for_device(
                        target.device,
                        f"情报英雄之旅：点击双帧确认的交叉双剑 {swords_point}。",
                    )
                    preview = wait_for_gather_step(
                        "情报英雄之旅预览与前往查看",
                        lambda frame: (match_daily_intel_hero_preview(frame, threshold)
                                       if match_daily_intel_hero_preview(frame, threshold)[0]
                                       else match_hero_preview_any_level(frame, threshold)),
                        8.0,
                    )
                    if not preview:
                        self._log_for_device(target.device, "双剑后未确认英雄之旅预览；未继续输入。")
                        return False
                    _preview_image, preview_point = preview
                    target.tap(*preview_point)

                    detail = wait_for_gather_step(
                        "情报英雄之旅详情与普通体力探险",
                        lambda frame: match_daily_intel_hero_detail(frame, threshold),
                        8.0,
                    )
                    if not detail:
                        self._log_for_device(target.device, "英雄之旅预览后未确认普通探险；未继续输入。")
                        return False
                    _detail_image, explore_point = detail
                    target.tap(*explore_point)
                    self._log_for_device(
                        target.device,
                        f"情报英雄之旅：点击双帧确认的普通体力探险 {explore_point}；不购买体力。",
                    )

                    setup_deadline = time.monotonic() + bounded_step_timeout(10.0)
                    setup_streak = 0
                    prior_auto: tuple[int, int] | None = None
                    prior_battle: tuple[int, int] | None = None
                    setup_image: Image.Image | None = None
                    auto_point: tuple[int, int] | None = None
                    while not self.stop_event.is_set() and time.monotonic() < setup_deadline:
                        frame = capture_daily_image()
                        current_auto, current_battle, _score = match_daily_intel_hero_setup(
                            frame, threshold
                        )
                        if (
                            current_auto
                            and current_battle
                            and stable(current_auto, prior_auto)
                            and stable(current_battle, prior_battle)
                        ):
                            setup_streak += 1
                        elif current_auto and current_battle:
                            prior_auto, prior_battle = current_auto, current_battle
                            setup_streak = 1
                        else:
                            prior_auto = prior_battle = None
                            setup_streak = 0
                        if setup_streak >= 2 and current_auto:
                            setup_image = frame
                            auto_point = current_auto
                            break
                        if adaptive_operation_wait(maximum=0.35):
                            return False
                    if setup_image is None or auto_point is None:
                        self._log_for_device(target.device, "英雄之旅未双帧确认小队设置与一键上阵；未继续输入。")
                        return False

                    # Existing selected heroes can be used without changing them.
                    # Both frames must prove all five selection checks and the
                    # exact setup page before accepting the battle button.
                    ready_battle: tuple[int, int] | None = None
                    selected_first, _ = match_selected_hero_battle(setup_image, threshold)
                    if selected_first:
                        selected_frame = capture_daily_image()
                        selected_second, _ = match_selected_hero_battle(selected_frame, threshold)
                        if selected_second and stable(selected_first, selected_second):
                            ready_battle = selected_second
                    if ready_battle is None:
                        target.tap(*auto_point)
                        self._log_for_device(
                            target.device,
                            f"情报英雄之旅：点击双帧确认的一键上阵 {auto_point}；等待阵容像素变化。",
                        )
                        ready_deadline = time.monotonic() + bounded_step_timeout(8.0)
                        ready_streak = 0
                        prior_ready: tuple[int, int] | None = None
                        while not self.stop_event.is_set() and time.monotonic() < ready_deadline:
                            frame = capture_daily_image()
                            current_battle, _score = match_daily_intel_hero_ready_battle(
                                frame, threshold
                            )
                            x1, y1 = 0, int(frame.height * 0.12)
                            x2, y2 = frame.width, int(frame.height * 0.62)
                            difference = ImageChops.difference(
                                setup_image.crop((x1, y1, x2, y2)),
                                frame.crop((x1, y1, x2, y2)),
                            )
                            mean_change = sum(ImageStat.Stat(difference).mean) / 3.0
                            if (
                                current_battle
                                and mean_change >= 2.0
                                and stable(current_battle, prior_ready)
                            ):
                                ready_streak += 1
                            elif current_battle and mean_change >= 2.0:
                                prior_ready, ready_streak = current_battle, 1
                            else:
                                prior_ready, ready_streak = None, 0
                            if ready_streak >= 2 and current_battle:
                                ready_battle = current_battle
                                break
                            if adaptive_operation_wait(maximum=0.35):
                                return False
                        if ready_battle is None:
                            self._log_for_device(
                                target.device,
                                "一键上阵后未同时确认阵容像素变化与绿色战斗按钮；未开战。",
                            )
                            return False

                    target.tap(*ready_battle)
                    self._log_for_device(
                        target.device,
                        f"情报英雄之旅：阵容变化已确认，点击普通绿色战斗 {ready_battle}。",
                    )
                    victory_deadline = time.monotonic() + bounded_step_timeout(24.0)
                    victory_streak = 0
                    prior_exit: tuple[int, int] | None = None
                    exit_point: tuple[int, int] | None = None
                    while not self.stop_event.is_set() and time.monotonic() < victory_deadline:
                        frame = capture_daily_image()
                        current_exit, _score = match_hero_victory(
                            frame, threshold
                        )
                        if current_exit and stable(current_exit, prior_exit):
                            victory_streak += 1
                        elif current_exit:
                            prior_exit, victory_streak = current_exit, 1
                        else:
                            prior_exit, victory_streak = None, 0
                        if victory_streak >= 2 and current_exit:
                            exit_point = current_exit
                            break
                        if adaptive_operation_wait(maximum=0.35):
                            return False
                    if exit_point is None:
                        self._log_for_device(
                            target.device,
                            "英雄之旅战斗后未双帧确认胜利与完整退出文字；未执行结果页点击。",
                        )
                        return False
                    target.tap(*exit_point)
                    self._log_for_device(
                        target.device,
                        f"情报英雄之旅：胜利与完整退出文字已双帧确认，点击安全侧边 {exit_point}；继续本批情报。",
                    )
                    return reopen_daily()

                # Daily Go can land on the station bubble or, on another UI
                # revision, directly on the Intel map.  Observe both without
                # guessing a generic building coordinate.
                deadline = time.monotonic() + bounded_step_timeout(12.0)
                prior_station: tuple[int, int] | None = None
                station_streak = map_streak = daily_streak = 0
                map_image: Image.Image | None = None
                image: Image.Image | None = None
                station_sent = False
                while not self.stop_event.is_set() and time.monotonic() < deadline:
                    image = capture_daily_image()
                    page = detect_daily_task_state(image, threshold)
                    if page.state is DailyTaskState.BLOCKED:
                        self._log_for_device(target.device, "情报前往后出现付费页面；未继续输入。")
                        return False
                    map_visible, _map_score = match_daily_intel_map_page(image, threshold)
                    if map_visible:
                        map_streak += 1
                        if map_streak >= 2:
                            map_image = image
                            break
                    else:
                        map_streak = 0
                    station_point, station_score = match_daily_intel_station_bubble(
                        image, threshold
                    )
                    if station_point is None and batch_count == 0:
                        # Only the city reached from Intel's verified Go can
                        # authorize this expert portrait as a station entry.
                        city_entry, _city_score = match_daily_city_entry(image, threshold)
                        if city_entry:
                            station_point, station_score = intel_station_expert(image)
                    if station_point is None:
                        station_point, station_score = match_daily_intel_map_entry(
                            image, threshold
                        )
                    if station_point is None and batch_count == 0:
                        station_point = match_daily_intel_tutorial_station(image)
                        if station_point is not None:
                            station_score = 1.0
                    if station_point and stable(station_point, prior_station):
                        station_streak += 1
                    elif station_point:
                        prior_station, station_streak = station_point, 1
                    else:
                        prior_station, station_streak = None, 0
                    if station_streak >= 2 and station_point and not station_sent:
                        target.tap(*station_point)
                        station_sent = True
                        station_streak = 0
                        deadline = time.monotonic() + bounded_step_timeout(12.0)
                        self._log_for_device(
                            target.device,
                            f"情报营救：点击双帧确认的情报站入口 {station_point}（{station_score:.4f}）。",
                        )
                    if page.state in daily_states and not station_sent:
                        daily_streak += 1
                        if daily_streak >= 2:
                            self._log_for_device(
                                target.device,
                                "情报前往未跳转且仍双帧确认每日页；情报让行 10 秒并继续独立任务。",
                            )
                            return True
                    else:
                        daily_streak = 0
                    if adaptive_operation_wait(maximum=0.45):
                        return False
                if map_image is None:
                    # If the task Go left us on a proved city rather than a
                    # reviewed Intel page, return to Daily and let later cards
                    # run. No generic building or recovery input is allowed.
                    if not self.stop_event.is_set() and image is not None and not station_sent and batch_count == 0:
                        first_city, _ = match_reviewed_city_daily_entry(image)
                        verify_city_image = capture_daily_image()
                        second_city, _ = match_reviewed_city_daily_entry(verify_city_image)
                        if first_city and second_city and stable(first_city, second_city):
                            intel_failed_scan = True
                            target.tap(*second_city)
                            self._log_for_device(target.device, "情报入口未确认；从双帧确认的主城重开每日任务，本轮先扫描其他任务。")
                            return True
                    self._log_for_device(target.device, "情报站入口后未双帧确认情报地图；未点击任何线索。")
                    return False

                # The expert creates more Intel. Reserve before its one input;
                # an unknown acknowledgement stays blocked across restarts.
                if not intel_expert_ledger or not intel_expert_ledger.available():
                    self._log_for_device(target.device, "情报专家上次点击状态未确认；停止以避免重复输入。")
                    return False
                first_expert, _ = intel_expert(map_image)
                if first_expert:
                    expert_verify = capture_daily_image()
                    expert_map, _ = match_daily_intel_map_page(expert_verify, threshold)
                    second_expert, _ = intel_expert(expert_verify)
                    if not expert_map or not stable(first_expert, second_expert):
                        self._log_for_device(target.device, "情报专家未双帧确认；未点击。")
                        return False
                    if not intel_expert_ledger.reserve():
                        return False
                    target.tap(*second_expert)
                    self._log_for_device(target.device, "情报专家已点击一次，等待确认头像消失。")
                    expert_deadline = time.monotonic() + bounded_step_timeout(8.0)
                    expert_clear = 0
                    while not self.stop_event.is_set() and time.monotonic() < expert_deadline:
                        expert_frame = capture_daily_image()
                        expert_map, _ = match_daily_intel_map_page(expert_frame, threshold)
                        if expert_map and not intel_expert_maybe_visible(expert_frame):
                            expert_clear += 1
                            if expert_clear >= 2:
                                if not intel_expert_ledger.confirm():
                                    return False
                                map_image = expert_frame
                                break
                        else:
                            expert_clear = 0
                        if adaptive_operation_wait(maximum=0.2):
                            return False
                    else:
                        self._log_for_device(target.device, "情报专家结果未确认；停止且不重复点击。")
                        return False

                # The already-verified map frame is the first passive proof;
                # do not throw it away and then wait to recapture two more.
                # Two frames of one exact reviewed clue authorise one click.
                # Prefer tents, then crossed swords. Wolves are never a
                # fallback solely because they are green.
                map_deadline = time.monotonic() + bounded_step_timeout(3.0)
                initial_tent, _initial_tent_score = match_daily_intel_rescue_pin(
                    map_image, threshold
                )
                initial_swords, _initial_swords_score = match_daily_intel_hero_pin(
                    map_image, threshold
                )
                if not initial_swords:
                    initial_swords = next((p for colour, kind, p, _ in intel_coloured_candidates(map_image)
                                           if (colour, kind) == ("purple", "axes")), None)
                initial_check, _initial_check_score = match_daily_intel_completed_check(
                    map_image, threshold
                )
                prior_clue_kind = (
                    "check"
                    if initial_check
                    else ("tent" if initial_tent else ("swords" if initial_swords else ""))
                )
                prior_clue = initial_check or initial_tent or initial_swords
                clue_streak = 1 if prior_clue else 0
                page_streak = 1
                last_map_image = map_image
                clue_kind = ""
                clue_point: tuple[int, int] | None = None
                while not self.stop_event.is_set() and time.monotonic() < map_deadline:
                    image = capture_daily_image()
                    map_visible, _map_score = match_daily_intel_map_page(image, threshold)
                    if not map_visible:
                        page_streak = 0
                        if adaptive_operation_wait(maximum=0.35):
                            return False
                        continue
                    page_streak += 1
                    last_map_image = image
                    tent_candidate, _tent_score = match_daily_intel_rescue_pin(
                        image, threshold
                    )
                    swords_candidate, _swords_score = match_daily_intel_hero_pin(
                        image, threshold
                    )
                    if not swords_candidate:
                        swords_candidate = next((p for colour, kind, p, _ in intel_coloured_candidates(image)
                                                  if (colour, kind) == ("purple", "axes")), None)
                    check_candidate, _check_score = match_daily_intel_completed_check(
                        image, threshold
                    )
                    current_kind = (
                        "check"
                        if check_candidate
                        else ("tent" if tent_candidate else ("swords" if swords_candidate else ""))
                    )
                    candidate = check_candidate or tent_candidate or swords_candidate
                    if (
                        candidate
                        and current_kind == prior_clue_kind
                        and stable(candidate, prior_clue)
                    ):
                        clue_streak += 1
                    elif candidate:
                        prior_clue_kind, prior_clue, clue_streak = current_kind, candidate, 1
                    else:
                        prior_clue_kind, prior_clue, clue_streak = "", None, 0
                    if clue_streak >= 2 and candidate:
                        clue_kind, clue_point = current_kind, candidate
                        break
                    if adaptive_operation_wait(maximum=0.35):
                        return False
                if clue_point is None:
                    if page_streak < 2:
                        self._log_for_device(target.device, "情报地图未保持双帧稳定；未点击线索或返回。")
                        return False
                    # Do not immediately re-enter the same exhausted map at
                    # the top of this scan and starve lower independent cards.
                    intel_failed_scan = True
                    back_point = daily_intel_map_back_point(last_map_image)
                    target.tap(*back_point)
                    self._log_for_device(
                        target.device,
                        f"情报地图已无精确帐篷或双剑；点击已双帧证明地图的左上返回 {back_point}，"
                        "未审核狼点保持零点击。",
                    )
                    return reopen_daily()

                if clue_kind == "check":
                    target.tap(*clue_point)
                    self._log_for_device(
                        target.device,
                        f"情报批次：点击双帧确认的绿色完成勾 {clue_point} 领取关联奖励。",
                    )
                    # A completed Intel marker opens its own correlated reward
                    # result before returning to the map.  Keep this authority
                    # local to the exact checked marker we just tapped: require
                    # two fresh frames of the complete tap-anywhere phrase,
                    # dismiss only its safe side point, then prove that the
                    # original check disappeared on two fresh Intel-map frames.
                    # This prevents the first reward sheet from aborting the
                    # whole checked-marker batch.
                    clear_deadline = time.monotonic() + bounded_step_timeout(12.0)
                    clear_streak = 0
                    reward_prior: tuple[int, int] | None = None
                    reward_streak = 0
                    reward_exit_count = 0
                    while not self.stop_event.is_set() and time.monotonic() < clear_deadline:
                        frame = capture_daily_image()
                        map_visible, _map_score = match_daily_intel_map_page(
                            frame, threshold
                        )
                        current_check, _current_score = match_daily_intel_completed_check(
                            frame, threshold
                        )
                        if map_visible and not (
                            current_check and stable(current_check, clue_point)
                        ):
                            clear_streak += 1
                            if clear_streak >= 2:
                                self._log_for_device(
                                    target.device,
                                    "情报绿色完成勾已从原位置连续两帧消失；继续本批领取或处理下一点。",
                                )
                                return run_intel_rescue_plan(batch_count)
                        else:
                            clear_streak = 0

                        abnormal = diagnose_daily_abnormal_exit(frame, threshold)
                        if abnormal.kind is DailyAbnormalExitKind.PAID_STOP:
                            self._log_for_device(
                                target.device,
                                "情报完成勾关联结果出现付费危险页；未执行退出或其他输入。",
                            )
                            return False
                        if (
                            abnormal.kind is DailyAbnormalExitKind.REWARD_TAP_ANYWHERE
                            and abnormal.point is not None
                        ):
                            if stable(abnormal.point, reward_prior):
                                reward_streak += 1
                            else:
                                reward_prior = abnormal.point
                                reward_streak = 1
                            if reward_streak >= 2:
                                if reward_exit_count >= 2:
                                    self._log_for_device(
                                        target.device,
                                        "同一情报完成勾已退出两层关联奖励页；达到安全上限，未继续点击。",
                                    )
                                    return False
                                reward_point = abnormal.point
                                target.tap(*reward_point)
                                reward_exit_count += 1
                                reward_prior = None
                                reward_streak = 0
                                clear_streak = 0
                                self._log_for_device(
                                    target.device,
                                    f"情报完成勾关联奖励页已由完整退出文字双帧确认；"
                                    f"点击安全侧边 {reward_point}（{reward_exit_count}/2），"
                                    "继续确认回到地图并领取下一完成点。",
                                )
                        else:
                            reward_prior = None
                            reward_streak = 0
                        if adaptive_operation_wait(maximum=0.30):
                            return False
                    self._log_for_device(
                        target.device,
                        "情报绿色完成勾点击后未在十二秒内完成关联奖励退出并确认原位置消失；"
                        "停止且不点击未知页面。",
                    )
                    return False

                if clue_kind == "swords":
                    return run_intel_hero_plan(clue_point)

                target.tap(*clue_point)
                self._log_for_device(
                    target.device,
                    f"情报营救：点击双帧确认的已审核帐篷 {clue_point}；未点击未知狼点。",
                )
                preview = wait_for_gather_step(
                    "情报营救幸存者预览与蓝色前往查看",
                    lambda image: match_daily_intel_rescue_preview(image, threshold),
                    8.0,
                )
                if not preview:
                    self._log_for_device(target.device, "绿色帐篷后未确认营救预览；未继续输入。")
                    return False
                _preview_image, preview_point = preview
                target.tap(*preview_point)
                self._log_for_device(
                    target.device,
                    f"情报营救：点击同页双证据的蓝色前往查看 {preview_point}。",
                )

                target_stage = wait_for_gather_step(
                    "情报营救目标与绿色普通营救",
                    lambda image: match_daily_intel_rescue_target(image, threshold),
                    8.0,
                )
                if not target_stage:
                    self._log_for_device(target.device, "前往查看后未确认绿色普通营救；未继续输入。")
                    return False
                _target_image, rescue_point = target_stage
                target.tap(*rescue_point)
                self._log_for_device(
                    target.device,
                    f"情报营救：点击双帧确认的绿色普通营救 {rescue_point}；不使用钻石或加速。",
                )

                active_deadline = time.monotonic() + bounded_step_timeout(10.0)
                active_streak = 0
                active_image: Image.Image | None = None
                while not self.stop_event.is_set() and time.monotonic() < active_deadline:
                    image = capture_daily_image()
                    active, _active_score = match_daily_intel_rescue_active(
                        image, threshold
                    )
                    if active:
                        active_streak += 1
                        active_image = image
                        if active_streak >= 2:
                            break
                    else:
                        active_streak = 0
                    if adaptive_operation_wait(maximum=0.40):
                        return False
                if active_streak < 2 or active_image is None:
                    self._log_for_device(target.device, "营救后未双帧确认自然倒计时；未作返回或加速点击。")
                    return False
                try:
                    evidence_dir = CONFIG_DIR / "evidence" / "intel_countdowns"
                    evidence_dir.mkdir(parents=True, exist_ok=True)
                    evidence_path = evidence_dir / f"intel_countdown_{time.strftime('%Y%m%d-%H%M%S')}.png"
                    daily_intel_active_countdown_crop(active_image).save(
                        evidence_path, optimize=True
                    )
                    prune_saved_runtime_evidence(evidence_dir)
                    self._log_for_device(
                        target.device,
                        f"情报营救自然倒计时已双帧确认并保存无账号裁剪 {evidence_path.name}；继续本批下一线索。",
                    )
                except OSError as exc:
                    self._log_for_device(target.device, f"情报营救倒计时已确认但裁剪保存失败：{exc}")
                return run_intel_rescue_plan(batch_count + 1)

            def defer_active_training_and_reopen_daily(
                label: str,
                kind: DailyMissionKind,
            ) -> bool:
                """Leave a proved natural queue untouched and resume Daily Tasks."""
                active_image = record_active_training_countdown(label)
                if active_image is None:
                    return False
                back_point = daily_training_back_point(active_image)
                target.tap(*back_point)
                deferred_auxiliary_training.add(kind)
                deferred_training_recheck_at[kind] = time.monotonic() + 8 * 60.0
                successful_training_retry_epoch[kind] = time.time() + 8 * 60.0
                save_active_training_deferrals()
                self._log_for_device(
                    target.device,
                    f"{label}自然训练队列保持运行；已从受证训练页返回兵营 {back_point}，"
                    "不加速、不重复训练，继续其他每日事项。",
                )
                city_stage = wait_for_gather_step(
                    f"{label}训练等待期的每日任务入口",
                    lambda image: match_daily_city_entry(image, threshold),
                    30.0,
                )
                if not city_stage:
                    self._log_for_device(target.device, f"{label}训练等待期未确认每日任务入口；未继续输入。")
                    return False
                _city_image, city_point = city_stage
                target.tap(*city_point)
                self._log_for_device(target.device, f"{label}训练等待期已重开每日任务入口 {city_point}。")
                return True

            def recover_failed_training_from_proven_city(
                kind: DailyMissionKind,
                label: str,
                first_image: Image.Image,
                second_image: Image.Image,
            ) -> bool:
                """Skip only one failed camp and resume later Daily tasks.

                This recovery is deliberately narrower than a generic Back:
                both passive frames must expose the same exact city Daily-entry
                control, and that verified control is the sole input.
                """

                first_point, _first_score = match_daily_city_entry(first_image, threshold)
                second_point, _second_score = match_daily_city_entry(second_image, threshold)
                if not (first_point and second_point and stable(first_point, second_point)):
                    return False
                failed_training_kinds.add(kind)
                training_failed_scan_kinds.add(kind)
                save_failed_training_kinds()
                target.tap(*second_point)
                self._log_for_device(
                    target.device,
                    f"{label}训练入口未确认，但已连续两帧证明返回主城；"
                            f"点击精确每日任务入口 {second_point}，仅让行{label} 30 秒并继续后续任务。",
                )
                return True

            def reopen_daily_tasks_from_gather_world(phase: str) -> bool:
                """Return from the reviewed gather map to Daily Tasks.

                This deliberately reuses the established city/world proof
                chain.  It is valid both immediately after a normal dispatch
                and after a confirmed natural return, and never uses Android
                Back, Recall, speed-up, or a generic close.
                """
                # Evaluate the mutually exclusive city and world states on
                # every same fresh frame.  The old serial 15-second city wait
                # delayed even an already-visible Town control and starved
                # later Daily items.  Neither match alone is actionable; each
                # branch still needs two consecutive stable frames.
                state_deadline = (
                    time.monotonic() + AUTOMATION_STEP_TIMEOUT_SECONDS
                )
                city_point: tuple[int, int] | None = None
                city_prior: tuple[int, int] | None = None
                city_streak = 0
                town_point: tuple[int, int] | None = None
                town_prior: tuple[int, int] | None = None
                town_streak = 0
                reference_size: tuple[int, int] | None = None
                while (
                    not self.stop_event.is_set()
                    and time.monotonic() < state_deadline
                ):
                    image = capture_daily_image()
                    reference_size = image.size
                    city_point, _city_score = match_reviewed_city_daily_entry(image)
                    town_point, _town_score = match_reviewed_world_town_entry(image)
                    if city_point and stable(city_point, city_prior):
                        city_streak += 1
                    elif city_point:
                        city_prior, city_streak = city_point, 1
                    else:
                        city_prior, city_streak = None, 0
                    if town_point and stable(town_point, town_prior):
                        town_streak += 1
                    elif town_point:
                        town_prior, town_streak = town_point, 1
                    else:
                        town_prior, town_streak = None, 0
                    if city_streak >= 2 and city_point:
                        target.tap(*city_point)
                        self._log_for_device(
                            target.device,
                            f"{phase}后已直接重开每日任务 {city_point}。",
                        )
                        return True
                    if town_streak >= 2 and town_point:
                        break
                    if self.stop_event.wait(interval):
                        return False
                if town_streak < 2 or not town_point or reference_size is None:
                    self._log_for_device(
                        target.device,
                        f"{phase}后未双帧确认主城或世界地图；未尝试返回主城。",
                    )
                    return False
                target.tap(*town_point)
                self._log_for_device(target.device, f"{phase}后点击经地图验证后的城镇入口 {town_point}。")

                # MuMu can finish the reviewed Town transition just after the
                # usual 24-second operation cap. Keep this one passive proof
                # bounded below the user's hard 30-second ceiling. No extra
                # input is sent while the city renders.
                deadline = (
                    time.monotonic() + DAILY_TOWN_RENDER_PASSIVE_CAP_SECONDS
                )
                city_point: tuple[int, int] | None = None
                prior_point: tuple[int, int] | None = None
                city_streak = 0
                regular_back_prior: tuple[int, int] | None = None
                regular_back_streak = 0
                regular_back_sent = False
                while not self.stop_event.is_set() and time.monotonic() < deadline:
                    # This is a persistent city render, not the transient
                    # overview house.  One live instance returned a valid but
                    # stale/wrong PrintWindow surface for all 29 seconds while
                    # native ADB already proved the city at 0.9914.  Use only
                    # authoritative native pixels here; two city frames remain
                    # mandatory and no new action coordinate is introduced.
                    image = capture_daily_image()
                    page = detect_daily_task_state(image, threshold)
                    if page.state is getattr(DailyTaskState, "BLOCKED", None):
                        self._log_for_device(
                            target.device,
                            f"{phase}后出现付费或遮挡页面；未执行返回或其他输入。",
                        )
                        return False
                    regular_back, _regular_score = (
                        match_daily_regular_activity_back(image, threshold)
                    )
                    if regular_back:
                        city_point, prior_point, city_streak = None, None, 0
                        if regular_back_sent:
                            continue
                        if stable(regular_back, regular_back_prior):
                            regular_back_streak += 1
                        else:
                            regular_back_prior, regular_back_streak = regular_back, 1
                        if regular_back_streak >= 2:
                            target.tap(*regular_back)
                            regular_back_sent = True
                            regular_back_streak = 0
                            self._log_for_device(
                                target.device,
                                f"{phase}后双帧确认自动弹出的常规活动页；"
                                f"仅点击该页左上返回 {regular_back}，未点击钻石刷新、加号、标签或活动卡。",
                            )
                        continue
                    regular_back_prior, regular_back_streak = None, 0
                    if regular_back_sent:
                        regular_back_sent = False
                    city_point, _ = match_reviewed_city_daily_entry(image)
                    if city_point and stable(city_point, prior_point):
                        city_streak += 1
                    elif city_point:
                        prior_point, city_streak = city_point, 1
                    else:
                        prior_point, city_streak = None, 0
                    if city_streak >= 2 and city_point:
                        target.tap(*city_point)
                        self._log_for_device(target.device, f"{phase}后已重新打开每日任务 {city_point}。")
                        return True
                    if self.stop_event.wait(interval):
                        return False
                self._log_for_device(target.device, f"{phase}后未确认主城每日任务入口；未继续输入。")
                return False

            def yield_gather_search_timeout(
                kind: DailyMissionKind,
                label: str,
            ) -> bool:
                """Leave only a proved resource selector and resume Daily.

                A failed node search authorises no map or node click. Two
                fresh selector frames permit one Android Back; two already-
                world frames need no Back. Every later input is still gated
                by the existing world-to-Town-to-Daily proof chain.
                """
                frames: list[Image.Image] = []
                for _ in range(2):
                    frames.append(daily_screenshot())
                    if self.stop_event.wait(max(interval, 0.15)):
                        return False
                selector_proof = all(daily_gather_selector_is_valid(image) for image in frames)
                world_points = [match_reviewed_gather_search(image)[0] for image in frames]
                world_proof = bool(
                    world_points[0]
                    and world_points[1]
                    and stable(world_points[0], world_points[1])
                )
                if selector_proof:
                    target.shell(["input", "keyevent", "4"])
                    self._log_for_device(
                        target.device,
                        f"{label}采集搜索暂未出现可验证资源点；"
                        "已从双帧确认的资源筛选页返回一次，不点击地图或节点。",
                    )
                elif not world_proof:
                    self._log_for_device(
                        target.device,
                        f"{label}采集搜索超时后页面未知；未作恢复输入。",
                    )
                    return False
                defer_gather_kind(kind, DAILY_RETRY_LOCK_MAX_SECONDS)
                if reopen_daily_tasks_from_gather_world(f"{label}采集搜索让行"):
                    self._log_for_device(
                        target.device,
                        f"{label}采集失败让行 10 秒后复查；继续后续独立任务。",
                    )
                    return True
                return False

            def yield_gather_selector_stage(
                kind: DailyMissionKind,
                label: str,
                reason: str,
            ) -> bool:
                """Leave one exact selector-only failure and scan later items.

                This is used before Search, so it cannot click a resource node
                or dispatch a team.  Two fresh frames must still prove the
                ordinary selector before the sole Android Back.  Any unknown
                page remains a fail-closed whole-run stop.
                """
                frames: list[Image.Image] = []
                for _ in range(2):
                    frames.append(daily_screenshot())
                    if self.stop_event.wait(max(interval, 0.15)):
                        return False
                if not all(daily_gather_selector_is_valid(image) for image in frames):
                    self._log_for_device(
                        target.device,
                        f"{label}{reason}后页面未知；未作恢复输入。",
                    )
                    return False
                target.shell(["input", "keyevent", "4"])
                defer_gather_kind(kind, DAILY_RETRY_LOCK_MAX_SECONDS)
                self._log_for_device(
                    target.device,
                    f"{label}{reason}；已从双帧确认的普通资源筛选页返回一次，"
                    "未点击搜索、地图、节点或出征。",
                )
                if reopen_daily_tasks_from_gather_world(f"{label}{reason}让行"):
                    self._log_for_device(
                        target.device,
                        f"{label}采集失败让行 10 秒后复查；立即继续后续独立任务。",
                    )
                    return True
                return False

            def recover_gather_world_from_task_hub(label: str) -> bool:
                """Recover a delayed gather Go that settles on a task hub.

                The current low-level account can briefly expose world-map
                anchors after a Daily ``Go`` tap, then settle on the reviewed
                Growth/Chapter task hub.  Only an exact two-frame hub-to-Daily
                tab permits recovery.  From there the helper double-confirms
                the Daily sheet, closes its reviewed X, and enters Wilderness
                from a separately proved city-only control.
                """

                def task_hub_daily_tab(image: Image.Image) -> tuple[tuple[int, int] | None, float]:
                    page = detect_daily_task_state(image, threshold)
                    anchors = {name for name, _point in page.anchors}
                    if page.state is DailyTaskState.DAILY_TAB_READY and anchors.intersection(
                        {"daily_growth_task_daily_tab", "daily_chapter_header"}
                    ):
                        return page.point, page.score
                    return None, page.score

                hub_stage = wait_for_gather_step(
                    f"{label}采集误导航后的任务中心每日标签",
                    task_hub_daily_tab,
                    5.0,
                )
                if not hub_stage:
                    return False
                _hub_image, daily_tab_point = hub_stage
                target.tap(*daily_tab_point)
                self._log_for_device(
                    target.device,
                    f"{label}采集前往延迟落到任务中心；已点击双帧确认的每日任务标签 {daily_tab_point}。",
                )

                safe_daily_states = {
                    DailyTaskState.DAILY_PAGE,
                    DailyTaskState.DAILY_LOGIN_COMPLETED,
                    DailyTaskState.CLAIM_READY,
                    DailyTaskState.TASK_CLAIM_READY,
                }

                def reviewed_daily_close(image: Image.Image) -> tuple[tuple[int, int] | None, float]:
                    page = detect_daily_task_state(image, threshold)
                    if page.state in safe_daily_states:
                        return daily_task_close_point(image), page.score
                    return None, page.score

                daily_stage = wait_for_gather_step(
                    f"{label}采集任务中心恢复后的每日页关闭",
                    reviewed_daily_close,
                    8.0,
                )
                if not daily_stage:
                    return False
                daily_image, close_point = daily_stage
                target.tap(*close_point)
                self._log_for_device(
                    target.device,
                    f"{label}采集：已关闭双帧确认的每日页 {close_point}，准备从主城进入荒野。",
                )

                wilderness_stage = wait_for_gather_step(
                    f"{label}采集主城荒野入口",
                    lambda image: match_daily_city_wilderness_entry(image, threshold),
                    8.0,
                )
                if not wilderness_stage:
                    return False
                _city_image, wilderness_point = wilderness_stage
                target.tap(*wilderness_point)
                self._log_for_device(
                    target.device,
                    f"{label}采集：已点击双帧确认的主城荒野入口 {wilderness_point}。",
                )
                return bool(
                    wait_for_gather_step(
                        f"{label}采集任务中心恢复后的世界地图",
                        lambda image: match_daily_gather_world_search(image, threshold),
                        10.0,
                    )
                )

            def recover_gather_world_from_proven_city(label: str) -> bool:
                """Enter Wilderness when a gather ``Go`` settles in the city.

                The low-level account's live transition remains on the main
                city for more than twenty seconds.  Waiting for a world-map
                anchor there wastes the whole bounded step.  This helper
                requires the exact city Daily-entry anchor in two fresh
                frames, rejects the paid/blocking state, and then uses only
                the Word-reviewed fixed Wilderness control.  It never taps a
                resource, node, search, dispatch, purchase, or generic Back.
                """

                def reviewed_city_wilderness(
                    image: Image.Image,
                ) -> tuple[tuple[int, int] | None, float]:
                    page = detect_daily_task_state(image, threshold)
                    if page.state is DailyTaskState.BLOCKED:
                        return None, page.score
                    city_point, city_score = match_daily_city_entry(image, threshold)
                    if not city_point:
                        return None, city_score
                    wilderness_point, wilderness_score = match_daily_city_wilderness_entry(
                        image, threshold
                    )
                    if not wilderness_point:
                        return None, max(city_score, wilderness_score)
                    return wilderness_point, min(city_score, wilderness_score)

                city_stage = wait_for_gather_step(
                    f"{label}采集前往后的主城荒野入口",
                    reviewed_city_wilderness,
                    6.0,
                )
                if not city_stage:
                    return False
                city_image, wilderness_point = city_stage
                evidence = record_documented_daily_evidence(
                    city_image,
                    "gather_go_city_settle",
                    "采集前往后连续两帧确认停在主城；仅点击文档已验证的荒野入口。",
                )
                target.tap(*wilderness_point)
                self._log_for_device(
                    target.device,
                    f"{label}采集前往稳定落在主城；已点击双帧主城证明下的荒野入口 "
                    f"{wilderness_point}；证据 {evidence.name if evidence else '已识别未落盘'}。",
                )
                return bool(
                    wait_for_gather_step(
                        f"{label}采集主城转荒野后的世界地图",
                        lambda image: match_daily_gather_world_search(image, threshold),
                        10.0,
                    )
                )

            def run_gather_plan(kinds: tuple[DailyMissionKind, ...]) -> bool:
                """Execute a bounded ordinary-resource plan, then reopen Daily Tasks.

                One trip per currently visible unfinished mission is made in
                each pass.  The task page is then reopened and read again;
                only a mission that still exposes its exact unfinished title
                and same-card Go control can schedule another trip.  This
                replaces the old fixed 4,212-capacity batch and stops at the
                task's minimum completion boundary for upgraded accounts.
                """
                limits = {
                    DailyMissionKind.GATHER_MEAT: 1,
                    DailyMissionKind.GATHER_WOOD: 1,
                    DailyMissionKind.GATHER_COAL: 1,
                    DailyMissionKind.GATHER_IRON: 1,
                }
                completed_dispatches = 0
                for kind in kinds:
                    for round_index in range(limits[kind]):
                        label = mission_label(kind)
                        # The low-level account's gather Go can briefly show
                        # world anchors, then settle on the task hub around
                        # five seconds later. Observe that stable window
                        # before accepting any world/preflight proof.
                        if self.stop_event.wait(max(interval, 0.20)):
                            return False
                        if recover_gather_world_from_proven_city(label):
                            self._log_for_device(
                                target.device,
                                f"{label}采集：前往后已从双帧确认的主城进入荒野。",
                            )
                        elif recover_gather_world_from_task_hub(label):
                            self._log_for_device(
                                target.device,
                                f"{label}采集：已在前往后的稳定窗口恢复任务中心误导航。",
                            )
                        stage = wait_for_gather_step(
                            "世界地图搜索入口",
                            lambda image: match_daily_gather_world_search(image, threshold),
                            6 * 60.0,
                        )
                        if not stage:
                            defer_gather_kind(kind, DAILY_RETRY_LOCK_MAX_SECONDS)
                            if reopen_daily_tasks_from_gather_world(
                                f"{label}采集前往转场失败让行"
                            ):
                                self._log_for_device(
                                    target.device,
                                    f"{label}采集未确认世界搜索入口；失败让行 10 秒并继续后续独立任务。",
                                )
                                return True
                            self._log_for_device(
                                target.device,
                                f"{label}采集未确认世界搜索入口，且未证明安全返回路线；未继续输入。",
                            )
                            return False
                        if resource_level is None:
                            if not establish_world_resource_level():
                                recovered_world = recover_gather_world_from_task_hub(label)
                                if recovered_world and establish_world_resource_level():
                                    stage = wait_for_gather_step(
                                        "任务中心恢复及区域预检后的世界地图搜索入口",
                                        match_reviewed_gather_search,
                                        12.0,
                                    )
                                    if stage:
                                        self._log_for_device(
                                            target.device,
                                            f"{label}采集：任务中心误导航已恢复，继续已验证的普通采集路线。",
                                        )
                                        # Continue with the normal capacity
                                        # proof below; no stale point is used.
                                    else:
                                        recovered_world = False
                                if recovered_world and resource_level in (5, 7, 9) and stage:
                                    pass
                                else:
                                    defer_gather_kind(kind, DAILY_RETRY_LOCK_MAX_SECONDS)
                                    if reopen_daily_tasks_from_gather_world(
                                        f"{label}采矿区域预检让行"
                                    ):
                                        self._log_for_device(
                                            target.device,
                                            f"{label}采矿区域预检未确认；失败让行 10 秒并继续后续独立项目。",
                                        )
                                        return True
                                    return False
                            stage = wait_for_gather_step(
                                "区域预检后的世界地图搜索入口",
                                match_reviewed_gather_search,
                                12.0,
                            )
                            if not stage:
                                self._log_for_device(
                                    target.device,
                                    f"{label}采集在区域预检后未复核世界搜索入口；未继续输入。",
                                )
                                return False
                        # The game reports a full queue at collection time;
                        # no march-capacity precheck is required here.
                        stage = wait_for_gather_step(
                            "空闲队列复核后的世界地图搜索入口",
                            match_reviewed_gather_search,
                            5.0,
                        )
                        if not stage:
                            self._log_for_device(
                                target.device,
                                f"{label}采集在容量复核后未重新确认世界搜索入口；未继续输入。",
                            )
                            return False
                        _image, world_search = stage
                        target.tap(*world_search)
                        self._log_for_device(target.device, f"{label}采集：已点击经双帧确认的世界搜索入口 {world_search}。")

                        selector = wait_for_gather_selector(30.0)
                        if selector is None:
                            self._log_for_device(target.device, f"{label}采集未确认资源筛选页；未继续输入。")
                            return False
                        if kind is DailyMissionKind.GATHER_MEAT:
                            # The exact Daily card normally pre-selects 生肉.
                            # A kingdom-overview round-trip can instead leave
                            # the carousel on 野兽, with the reviewed 生肉 tab
                            # partially visible at the far right.  Recover
                            # only through that exact tab, then independently
                            # double-confirm the central 生肉 label.
                            if not daily_gather_meat_is_selected(selector, threshold):
                                meat_tab = wait_for_gather_step(
                                    "资源筛选页右侧生肉标签",
                                    lambda image: match_daily_gather_meat_visible_tab(image, threshold),
                                    8.0,
                                )
                                if not meat_tab:
                                    self._log_for_device(
                                        target.device,
                                        "生肉采集未确认预选状态或精确右侧生肉标签；未触碰轮播、未点击搜索。",
                                    )
                                    return False
                                _tab_image, meat_tab_point = meat_tab
                                target.tap(*meat_tab_point)
                                self._log_for_device(
                                    target.device,
                                    f"生肉采集：点击双帧确认的右侧生肉资源标签 {meat_tab_point}。",
                                )
                                selected_stage = wait_for_gather_step(
                                    "生肉资源标签选中状态",
                                    lambda image: (
                                        (map_content_point((720, 1840), (1440, 2560), image), 1.0)
                                        if daily_gather_meat_is_selected(image, threshold)
                                        else (None, 0.0)
                                    ),
                                    10.0,
                                )
                                if not selected_stage:
                                    self._log_for_device(
                                        target.device,
                                        "生肉资源标签点击后未双帧确认中央生肉选中态；未点击搜索。",
                                    )
                                    return False
                                selector = selected_stage[0]
                                self._log_for_device(target.device, "生肉采集：已双帧确认中央生肉选中态。")
                            else:
                                self._log_for_device(target.device, "生肉采集：确认每日任务已预选生肉，未触碰资源轮播。")
                        else:
                            resource_point = daily_gather_resource_tab_point(kind, selector)
                            target.tap(*resource_point)
                            self._log_for_device(target.device, f"{label}采集：已选择普通资源分类 {resource_point}。")

                            selector = wait_for_gather_selector(20.0)
                            if selector is None:
                                self._log_for_device(target.device, f"{label}分类选择后页面未复核；未点击搜索。")
                                return False
                        # Start from the selector's hard lower bound, then
                        # Start at the reviewed, fixed ordinary-resource level.
                        # Resetting first makes the operation independent of a
                        # remembered selector value and never enters the
                        # kingdom-overview/Intel route.
                        target_level = resource_level
                        minus_point = daily_gather_level_minus_point(selector)
                        plus_point = daily_gather_level_plus_point(selector)
                        for _ in range(10):
                            target.tap(*minus_point)
                            if self.stop_event.wait(0.08):
                                return False
                        for _ in range(target_level - 1):
                            target.tap(*plus_point)
                            if self.stop_event.wait(0.08):
                                return False
                        selector = wait_for_gather_selector(20.0)
                        if selector is None:
                            self._log_for_device(target.device, f"{label}资源等级设置后未通过双帧复核；未点击搜索。")
                            return False
                        self._log_for_device(
                            target.device,
                            f"{label}采集：按安全策略固定普通资源 {target_level} 级，已从最低档复位后设为 {target_level} 级。",
                        )
                        filter_stage = wait_for_full_resources_filter(20.0)
                        if not filter_stage:
                            self._log_for_device(target.device, f"{label}采集未确认仅满资源筛选状态；未点击搜索。")
                            return yield_gather_selector_stage(
                                kind,
                                label,
                                "采集未确认仅满资源筛选状态",
                            )
                        filter_state, _filter_image, filter_point = filter_stage
                        if filter_state == "off":
                            assert filter_point is not None
                            target.tap(*filter_point)
                            self._log_for_device(
                                target.device,
                                f"{label}采集：已点击双帧确认的仅搜索满资源筛选 {filter_point}。",
                            )
                            filter_stage = wait_for_full_resources_filter(20.0)
                            if not filter_stage or filter_stage[0] != "enabled":
                                self._log_for_device(target.device, f"{label}采集未确认满资源筛选已切换；未点击搜索。")
                                return yield_gather_selector_stage(
                                    kind,
                                    label,
                                    "采集未确认满资源筛选已切换",
                                )
                            self._log_for_device(target.device, f"{label}采集：已双帧确认仅搜索满资源筛选生效。")
                        else:
                            self._log_for_device(target.device, f"{label}采集：已双帧确认仅搜索满资源筛选原本生效。")
                        full_filter_enabled = bool(
                            filter_stage
                            and filter_stage[0] == "enabled"
                            and daily_gather_full_resources_filter_is_enabled(filter_stage[1], threshold)
                        )
                        if not daily_gather_route_meets_required_amount(
                            kind,
                            target_level,
                            full_filter_enabled,
                        ):
                            required_amount = DAILY_GATHER_REQUIRED_AMOUNTS.get(kind, 0)
                            self._log_for_device(
                                target.device,
                                f"{label}采集无法证明资源点不少于任务所需 {required_amount:,}；已暂停，未点击搜索。",
                            )
                            return False
                        search_point = daily_gather_search_point(selector)
                        target.tap(*search_point)
                        self._log_for_device(target.device, f"{label}采集：已点击普通资源搜索 {search_point}。")

                        stage = wait_for_gather_step(
                            "资源点采集按钮",
                            lambda image: match_daily_gather_collect_button(image, threshold),
                            50.0,
                        )
                        if not stage:
                            return yield_gather_search_timeout(kind, label)
                        _image, collect_point = stage
                        target.tap(*collect_point)
                        self._log_for_device(target.device, f"{label}采集：已点击已验证的普通采集 {collect_point}。")

                        required_amount = DAILY_GATHER_REQUIRED_AMOUNTS[kind]
                        formation_stage = wait_for_gather_formation_capacity(
                            label,
                            required_amount,
                        )
                        if not formation_stage:
                            self._log_for_device(
                                target.device,
                                f"{label}采集未通过普通出征、兵力及负重复核；未继续输入。",
                            )
                            return False
                        formation_status, dispatch_point, selected_troops, carrying_capacity = formation_stage
                        if formation_status == "queue_full":
                            target.shell(["input", "keyevent", "4"])
                            defer_gather_kind(kind, 10.0)
                            return reopen_daily_tasks_from_gather_world(f"{label}采集队列满")
                        if formation_status == "insufficient":
                            if kind is DailyMissionKind.GATHER_IRON:
                                self._log_for_device(
                                    target.device,
                                    f"铁矿编队负重 {carrying_capacity:,} 低于任务量 {required_amount:,}；"
                                    "按用户规则立即暂停，未点击出征。",
                                )
                                return False
                            # The formation page itself was just proved twice
                            # with the exact ordinary Dispatch button and equal
                            # troop/carry readings. One Android Back is therefore
                            # narrowly authorised; it cannot click Dispatch.
                            target.shell(["input", "keyevent", "4"])
                            defer_gather_kind(
                                kind,
                                DAILY_RETRY_LOCK_MAX_SECONDS,
                            )
                            self._log_for_device(
                                target.device,
                                f"{label}编队负重 {carrying_capacity:,}/{required_amount:,}，"
                                f"选兵 {selected_troops:,}；已从双帧确认的编队页返回，"
                                "本次负重不足只让行 10 秒并继续后续任务。",
                            )
                            if reopen_daily_tasks_from_gather_world(
                                f"{label}编队负重不足让行"
                            ):
                                return True
                            return False
                        if formation_status != "ready":
                            return False
                        # Record before input; an unknown acknowledgement must
                        # not trigger a second cart of the same resource.
                        daily_gather_sent_kinds.add(kind)
                        dispatched_gather_kinds.add(kind)
                        defer_gather_kind(kind, DAILY_GATHER_FULL_NODE_MIN_RETURN_SECONDS, natural_queue=True)
                        target.tap(*dispatch_point)
                        if known_march_total is None:
                            # Consume the one no-header bootstrap only when a
                            # real Dispatch input occurs. A selector/node
                            # timeout before this point must not poison later
                            # resource kinds in the same process.
                            bootstrap_dispatch_used = True
                        completed_dispatches += 1
                        self.signals.clicks.emit(claims + completed_dispatches)
                        self._log_for_device(
                            target.device,
                            f"{label}采集：已派遣第 {round_index + 1}/{limits[kind]} 队普通采集 {dispatch_point}。",
                        )

                        # The one-cart record was persisted before input.
                        # Return via the recognised world route without waiting
                        # for or reading a march-queue countdown.
                        return reopen_daily_tasks_from_gather_world(f"{label}采集已派遣")

                self._log_for_device(target.device, "普通采集计划没有完成任何派遣；未继续输入。")
                return False

            def set_daily_training_quantity_to_max(label: str) -> tuple[int, int] | None:
                """Drag the reviewed ordinary-training slider to its maximum.

                The number is account-dependent and can change with resources
                and camp level, so no literal is typed.  Both the ordinary
                blue Train control and all three quantity-lane controls must
                be stationary for two fresh frames before one bounded slider
                gesture.  The right-end handle position is then proved twice
                before the ordinary Train button is returned to the caller.
                """
                prior_normal: tuple[int, int] | None = None
                prior_slider: tuple[tuple[int, int], tuple[int, int]] | None = None
                panel_streak = 0
                max_streak = 0
                normal_train_point: tuple[int, int] | None = None
                slider_points: tuple[tuple[int, int], tuple[int, int]] | None = None
                deadline = time.monotonic() + 8.0

                while not self.stop_event.is_set() and time.monotonic() < deadline:
                    image = daily_screenshot()
                    page = detect_daily_task_state(image, threshold)
                    if page.state is getattr(DailyTaskState, "BLOCKED", None):
                        self._log_for_device(target.device, f"{label}训练数量页出现付费页面；未输入并停止。")
                        return None
                    fresh_normal, _score = match_daily_training_normal_button(image, threshold)
                    fresh_slider = daily_training_quantity_slider_points(image)
                    if not fresh_normal or not fresh_slider:
                        self._log_for_device(target.device, f"{label}训练数量滑条未与普通训练页同帧复核；未输入。")
                        return None
                    if stable(fresh_normal, prior_normal) and fresh_slider == prior_slider:
                        panel_streak += 1
                    else:
                        prior_normal, prior_slider = fresh_normal, fresh_slider
                        panel_streak = 1
                    normal_train_point = fresh_normal
                    slider_points = fresh_slider
                    if daily_training_quantity_is_maxed(image):
                        max_streak += 1
                        if max_streak >= 2 and panel_streak >= 2:
                            self._log_for_device(target.device, f"{label}训练数量原本已双帧确认拉满；无需重复滑动。")
                            return normal_train_point
                    else:
                        max_streak = 0
                    if panel_streak >= 2:
                        break
                    if self.stop_event.wait(0.18):
                        return None

                if panel_streak < 2 or not slider_points:
                    self._log_for_device(target.device, f"{label}训练数量滑条未完成双帧确认；未输入。")
                    return None

                handle, endpoint = slider_points
                target.shell(
                    ["input", "swipe", str(handle[0]), str(handle[1]), str(endpoint[0]), str(endpoint[1]), "140"],
                    timeout=5.0,
                )
                self._log_for_device(
                    target.device,
                    f"{label}任务：已将双帧确认的普通训练滑条从 {handle} 一步拉到最大端点 {endpoint}。",
                )
                if self.stop_event.wait(0.20):
                    return None

                prior_normal = None
                prior_slider = None
                max_streak = 0
                verify_deadline = time.monotonic() + 6.0
                while not self.stop_event.is_set() and time.monotonic() < verify_deadline:
                    image = daily_screenshot()
                    page = detect_daily_task_state(image, threshold)
                    if page.state is getattr(DailyTaskState, "BLOCKED", None):
                        self._log_for_device(target.device, f"{label}训练数量拉满后出现付费页面；未点击训练。")
                        return None
                    fresh_normal, _score = match_daily_training_normal_button(image, threshold)
                    fresh_slider = daily_training_quantity_slider_points(image)
                    if fresh_normal and fresh_slider and daily_training_quantity_is_maxed(image):
                        if stable(fresh_normal, prior_normal) and fresh_slider == prior_slider:
                            max_streak += 1
                        else:
                            prior_normal, prior_slider, max_streak = fresh_normal, fresh_slider, 1
                        if max_streak >= 2:
                            self._log_for_device(target.device, f"{label}训练数量已在滑动后双帧确认拉满。")
                            return fresh_normal
                    else:
                        prior_normal, prior_slider, max_streak = None, None, 0
                    if self.stop_event.wait(0.22):
                        return None
                self._log_for_device(target.device, f"{label}训练数量滑动后未能双帧确认拉满；未点击训练。")
                return None

            def reviewed_fixed_training_camp_point(
                kind: DailyMissionKind,
                screenshot: Image.Image,
            ) -> tuple[int, int] | None:
                """Map a troop-specific, live-reviewed camp point.

                This helper is deliberately not a recogniser and must never
                be used as a page recovery.  Its callers are the immediate
                transition windows entered by an exact, double-confirmed
                Daily troop ``Go``; they expose this point only after two
                fresh frames prove the fixed city layout.
                """
                reference_points = {
                    DailyMissionKind.TRAIN_SHIELD: (720, 1200),
                    DailyMissionKind.TRAIN_SPEAR: (720, 1095),
                    DailyMissionKind.TRAIN_ARCHER: (720, 1130),
                }
                reference = reference_points.get(kind)
                if reference is None:
                    return None
                return map_content_point(reference, (1440, 2560), screenshot)

            def finish_training_camp_double_enter(
                label: str,
                kind: DailyMissionKind,
                reviewed_camp_point: tuple[int, int],
                tutorial_probe: Callable[[Image.Image, float], tuple[tuple[int, int] | None, float]],
                *,
                require_ordinary_entry: bool = False,
            ) -> str | None:
                """After collection, enter the same proved camp a second time.

                The first camp tap can merely collect yesterday's completed
                soldiers and return to the city.  We therefore watch only for
                the same troop-specific tutorial target, the exact city Daily
                entry (which proves the fixed city layout), or the reviewed
                ordinary training entry.  At most one additional camp tap and
                one ordinary-entry tap are allowed; every one needs two fresh
                stable frames, and paid/unknown surfaces fail closed.
                """
                deadline = time.monotonic() + bounded_step_timeout(30.0)
                second_camp_tapped = False
                entry_tapped = False
                prior_panel: tuple[int, int] | None = None
                panel_streak = 0
                prior_tutorial: tuple[int, int] | None = None
                tutorial_streak = 0
                prior_city: tuple[int, int] | None = None
                city_streak = 0
                prior_entry: tuple[int, int] | None = None
                entry_streak = 0
                prior_active: tuple[int, int] | None = None
                active_streak = 0
                while not self.stop_event.is_set() and time.monotonic() < deadline:
                    image = daily_screenshot()
                    page = detect_daily_task_state(image, threshold)
                    if page.state is getattr(DailyTaskState, "BLOCKED", None):
                        self._log_for_device(target.device, f"{label}兵营二次进入时出现付费页面；未输入并停止。")
                        return False

                    panel_point, _panel_score = match_daily_training_normal_button(image, threshold)
                    if panel_point and stable(panel_point, prior_panel):
                        panel_streak += 1
                    elif panel_point:
                        prior_panel, panel_streak = panel_point, 1
                    else:
                        prior_panel, panel_streak = None, 0
                    if panel_streak >= 2 and (entry_tapped or not require_ordinary_entry):
                        self._log_for_device(target.device, f"{label}兵营已进入普通训练面板；继续拉满数量。")
                        return "normal_panel"

                    active_point, _active_score = match_daily_training_active(
                        image, threshold
                    )
                    if active_point and stable(active_point, prior_active):
                        active_streak += 1
                    elif active_point:
                        prior_active, active_streak = active_point, 1
                    else:
                        prior_active, active_streak = None, 0
                    if active_streak >= 2:
                        self._log_for_device(
                            target.device,
                            f"{label}兵营二次进入后已双帧确认现有自然训练队列；"
                            "立即保留队列并返回每日任务，不等待完整转场窗口。",
                        )
                        if defer_active_training_and_reopen_daily(label, kind):
                            return "active_queue"
                        return None

                    entry_point, _entry_score = match_daily_training_entry(image, threshold)
                    if entry_point and stable(entry_point, prior_entry):
                        entry_streak += 1
                    elif entry_point:
                        prior_entry, entry_streak = entry_point, 1
                    else:
                        prior_entry, entry_streak = None, 0

                    tutorial_point, _tutorial_score = tutorial_probe(image, threshold)
                    if tutorial_point and stable(tutorial_point, prior_tutorial):
                        tutorial_streak += 1
                    elif tutorial_point:
                        prior_tutorial, tutorial_streak = tutorial_point, 1
                    else:
                        prior_tutorial, tutorial_streak = None, 0

                    city_point, _city_score = match_daily_city_entry(image, threshold)
                    if city_point and stable(city_point, prior_city):
                        city_streak += 1
                    elif city_point:
                        prior_city, city_streak = city_point, 1
                    else:
                        prior_city, city_streak = None, 0

                    if entry_streak >= 2 and entry_point and not entry_tapped:
                        target.tap(*entry_point)
                        entry_tapped = True
                        prior_entry, entry_streak = None, 0
                        self._log_for_device(
                            target.device,
                            f"{label}兵营：点击双帧确认的普通训练入口 {entry_point}（收兵后的进入动作）。",
                        )
                    elif not second_camp_tapped and tutorial_streak >= 2 and tutorial_point:
                        target.tap(*tutorial_point)
                        second_camp_tapped = True
                        prior_tutorial, tutorial_streak = None, 0
                        self._log_for_device(
                            target.device,
                            f"{label}兵营：第一次只完成收兵；已再次点击同兵种的精确兵营目标 {tutorial_point}。",
                        )
                    elif not second_camp_tapped and city_streak >= 2:
                        # The exact city Daily-entry anchor proves that the
                        # collection returned to the same fixed city layout.
                        # Reuse only the troop-specific point authorised by
                        # the immediately preceding double-confirmed target.
                        target.tap(*reviewed_camp_point)
                        second_camp_tapped = True
                        prior_city, city_streak = None, 0
                        self._log_for_device(
                            target.device,
                            f"{label}兵营：收兵后已双帧回到主城；第二次点击刚才受证的兵营 {reviewed_camp_point}。",
                        )
                    if self.stop_event.wait(0.20):
                        return False
                self._log_for_device(target.device, f"{label}兵营在30秒内未完成受证二次进入；未继续输入。")
                return None

            def run_shield_training_plan() -> bool:
                """Fill the Shield camp's ordinary queue using the normal blue route.

                The entry is reached only from a double-confirmed Daily Task
                card.  The yellow diamond completion and the blue speed-up
                are never candidates: the sole actionable control is the
                panel's normal blue ``Train`` label after the quantity slider
                has been observed at its maximum in two fresh frames.
                """
                # The task-directed transition can lead either to the usual
                # training entry or, after a natural completion, to the
                # shield-camp tutorial.  Observe both reviewed targets in
                # one window so a delayed tutorial cannot be mistaken for a
                # missing ordinary entry.  Each target has its own stable
                # two-frame streak; this adds no fallback tap.
                def wait_for_shield_transition() -> tuple[str, Image.Image, tuple[int, int]] | None:
                    deadline = time.monotonic() + AUTOMATION_STEP_TIMEOUT_SECONDS
                    prior_tutorial: tuple[int, int] | None = None
                    tutorial_streak = 0
                    prior_entry: tuple[int, int] | None = None
                    entry_streak = 0
                    prior_city: tuple[int, int] | None = None
                    city_streak = 0
                    while not self.stop_event.is_set() and time.monotonic() < deadline:
                        if duration and time.monotonic() - started >= duration * 60:
                            return None
                        if guard and not cached_foreground_is_game():
                            set_state("已暂停：游戏不在模拟器前台")
                            if self.stop_event.wait(interval):
                                return None
                            continue
                        image = daily_screenshot()
                        page = detect_daily_task_state(image, threshold)
                        if page.state is getattr(DailyTaskState, "BLOCKED", None):
                            self._log_for_device(target.device, "盾兵任务转场出现付费页面；未输入并停止。")
                            return None
                        tutorial_point, _tutorial_score = match_daily_training_collect_tutorial(image, threshold)
                        entry_point, _entry_score = match_daily_training_entry(image, threshold)
                        city_point, _city_score = match_daily_city_entry(image, threshold)
                        if tutorial_point and stable(tutorial_point, prior_tutorial):
                            tutorial_streak += 1
                        elif tutorial_point:
                            prior_tutorial, tutorial_streak = tutorial_point, 1
                        else:
                            prior_tutorial, tutorial_streak = None, 0
                        if entry_point and stable(entry_point, prior_entry):
                            entry_streak += 1
                        elif entry_point:
                            prior_entry, entry_streak = entry_point, 1
                        else:
                            prior_entry, entry_streak = None, 0
                        if city_point and stable(city_point, prior_city):
                            city_streak += 1
                        elif city_point:
                            prior_city, city_streak = city_point, 1
                        else:
                            prior_city, city_streak = None, 0
                        if tutorial_streak >= 2 and tutorial_point:
                            return "completed_tutorial", image, tutorial_point
                        if entry_streak >= 2 and entry_point:
                            return "normal_entry", image, entry_point
                        if city_streak >= 2:
                            reviewed_point = reviewed_fixed_training_camp_point(
                                DailyMissionKind.TRAIN_SHIELD,
                                image,
                            )
                            if reviewed_point:
                                return "reviewed_city_camp", image, reviewed_point
                        set_state(
                            "等待盾兵普通入口、完成教程或主城固定布局"
                            f"（入口 {entry_streak}/2；教程 {tutorial_streak}/2；主城 {city_streak}/2）"
                        )
                        if self.stop_event.wait(interval):
                            return None
                    return None

                transition = wait_for_shield_transition()
                if not transition:
                    self._log_for_device(target.device, "盾兵任务未确认普通训练入口或完成队列教程；未继续输入。")
                    return False
                transition_kind, _transition_image, transition_point = transition
                if transition_kind in ("completed_tutorial", "reviewed_city_camp"):
                    tutorial_point = transition_point
                    target.tap(*tutorial_point)
                    if transition_kind == "completed_tutorial":
                        self._log_for_device(target.device, f"盾兵任务：点击双帧确认的完成队列教程目标 {tutorial_point}。")
                    else:
                        self._log_for_device(
                            target.device,
                            "盾兵任务：精确前往血缘内已双帧确认主城；"
                            f"点击实机审核固定兵营 {tutorial_point}，后续仍强制双帧普通训练入口。",
                        )
                    double_enter_result = finish_training_camp_double_enter(
                        "盾兵",
                        DailyMissionKind.TRAIN_SHIELD,
                        tutorial_point,
                        match_daily_training_collect_tutorial,
                        require_ordinary_entry=transition_kind == "reviewed_city_camp",
                    )
                    if double_enter_result == "active_queue":
                        return True
                    if double_enter_result != "normal_panel":
                        return False
                entry_point = transition_point
                if transition_kind == "normal_entry":
                    target.tap(*entry_point)
                    self._log_for_device(target.device, f"盾兵任务：点击已验证的普通训练入口 {entry_point}。")

                def wait_for_shield_normal_panel(
                ) -> tuple[Image.Image, tuple[int, int]] | None:
                    """Handle one reviewed unlock reveal inside the same 30s step."""
                    deadline = time.monotonic() + AUTOMATION_STEP_TIMEOUT_SECONDS
                    prior_normal: tuple[int, int] | None = None
                    normal_streak = 0
                    prior_unlock: tuple[int, int] | None = None
                    unlock_streak = 0
                    unlock_continue_sent = False
                    while not self.stop_event.is_set() and time.monotonic() < deadline:
                        if duration and time.monotonic() - started >= duration * 60:
                            return None
                        if guard and not cached_foreground_is_game():
                            set_state("已暂停：游戏不在模拟器前台")
                            if self.stop_event.wait(interval):
                                return None
                            continue
                        image = daily_screenshot()
                        page = detect_daily_task_state(image, threshold)
                        if page.state is getattr(DailyTaskState, "BLOCKED", None):
                            self._log_for_device(
                                target.device,
                                "盾兵新兵种解锁转场出现付费页面；未输入并停止。",
                            )
                            return None

                        normal_point, _normal_score = (
                            match_daily_training_normal_button(image, threshold)
                        )
                        if normal_point and stable(normal_point, prior_normal):
                            normal_streak += 1
                        elif normal_point:
                            prior_normal, normal_streak = normal_point, 1
                        else:
                            prior_normal, normal_streak = None, 0
                        if normal_streak >= 2 and normal_point:
                            return image, normal_point

                        unlock_point: tuple[int, int] | None = None
                        if not unlock_continue_sent:
                            unlock_point, _unlock_score = (
                                match_daily_training_unlock_continue(image, threshold)
                            )
                            if unlock_point and stable(unlock_point, prior_unlock):
                                unlock_streak += 1
                            elif unlock_point:
                                prior_unlock, unlock_streak = unlock_point, 1
                            else:
                                prior_unlock, unlock_streak = None, 0
                            if unlock_streak >= 2 and unlock_point:
                                target.tap(*unlock_point)
                                unlock_continue_sent = True
                                prior_unlock, unlock_streak = None, 0
                                prior_normal, normal_streak = None, 0
                                self._log_for_device(
                                    target.device,
                                    "盾兵兵营：已在同一30秒转场窗口内点击双帧确认的"
                                    f"‘点击任意位置继续’ {unlock_point}；"
                                    "只继续等待蓝色普通训练面板。",
                                )
                                continue
                        else:
                            prior_unlock, unlock_streak = None, 0

                        set_state(
                            "等待盾兵普通训练面板"
                            f"（面板 {normal_streak}/2；解锁继续 {unlock_streak}/2）"
                        )
                        if self.stop_event.wait(interval):
                            return None
                    return None

                stage = wait_for_shield_normal_panel()
                if not stage:
                    self._log_for_device(target.device, "盾兵任务未确认蓝色普通训练面板；未继续输入。")
                    return False
                _panel_image, _normal_train_point = stage
                # The Shield route can also enter an already-running queue
                # after a natural completion/collection transition.  Detect
                # that exact queue before touching the quantity slider, just
                # like Spear/Archer; leave through the reviewed Back control
                # and never click Complete Now, Speed Up, Cancel, or Train.
                active_stage = wait_for_gather_step(
                    "盾兵营已有训练队列",
                    lambda image: match_daily_training_active(image, threshold),
                    5.0,
                )
                if active_stage:
                    return defer_active_training_and_reopen_daily(
                        "盾兵",
                        DailyMissionKind.TRAIN_SHIELD,
                    )
                normal_train_point = set_daily_training_quantity_to_max("盾兵")
                if not normal_train_point:
                    return False

                target.tap(*normal_train_point)
                self._log_for_device(target.device, f"盾兵任务：点击已复核的蓝色普通训练 {normal_train_point}（数量已拉满）。")

                stage = wait_for_gather_step(
                    "盾兵普通训练队列",
                    lambda image: match_daily_training_active(image, threshold),
                    20.0,
                )
                if not stage:
                    self._log_for_device(target.device, "盾兵训练启动后未确认普通训练队列；未作恢复输入。")
                    return False
                return defer_active_training_and_reopen_daily(
                    "盾兵",
                    DailyMissionKind.TRAIN_SHIELD,
                )

            def run_auxiliary_training_plan(kind: DailyMissionKind) -> bool:
                """Fill the Spear or Archer ordinary queue without speed-ups.

                These two task cards share the reviewed normal training panel
                with Shield.  Their exact tutorial assets remain the preferred
                route.  If a higher-level building skin misses that asset, the
                immediate exact-Go lineage may use the troop-specific reviewed
                fixed point only after two fresh city-layout frames.  That tap
                still cannot authorise training: two fresh ordinary-entry
                frames are mandatory before the route can reach the panel.
                """
                if kind not in (DailyMissionKind.TRAIN_SPEAR, DailyMissionKind.TRAIN_ARCHER):
                    return False
                label = mission_label(kind)
                tutorial_camp_clicked = False
                tutorial_probe = (
                    match_daily_training_spear_tutorial_entry
                    if kind is DailyMissionKind.TRAIN_SPEAR
                    else match_daily_training_archer_tutorial_entry
                )

                def wait_for_auxiliary_transition(
                ) -> tuple[str, Image.Image, tuple[int, int]] | None:
                    """Observe ordinary entry and troop tutorial in one <=30s window."""
                    deadline = time.monotonic() + AUTOMATION_STEP_TIMEOUT_SECONDS
                    prior_entry: tuple[int, int] | None = None
                    entry_streak = 0
                    prior_tutorial: tuple[int, int] | None = None
                    tutorial_streak = 0
                    prior_city: tuple[int, int] | None = None
                    city_streak = 0
                    while not self.stop_event.is_set() and time.monotonic() < deadline:
                        if duration and time.monotonic() - started >= duration * 60:
                            return None
                        if guard and not cached_foreground_is_game():
                            set_state("已暂停：游戏不在模拟器前台")
                            if self.stop_event.wait(interval):
                                return None
                            continue
                        image = daily_screenshot()
                        page = detect_daily_task_state(image, threshold)
                        if page.state is getattr(DailyTaskState, "BLOCKED", None):
                            self._log_for_device(
                                target.device,
                                f"{label}任务转场出现付费页面；未输入并停止。",
                            )
                            return None
                        entry_point, _entry_score = match_daily_training_entry(
                            image, threshold
                        )
                        tutorial_point, _tutorial_score = tutorial_probe(
                            image, threshold
                        )
                        city_point, _city_score = match_daily_city_entry(image, threshold)
                        if entry_point and stable(entry_point, prior_entry):
                            entry_streak += 1
                        elif entry_point:
                            prior_entry, entry_streak = entry_point, 1
                        else:
                            prior_entry, entry_streak = None, 0
                        if tutorial_point and stable(tutorial_point, prior_tutorial):
                            tutorial_streak += 1
                        elif tutorial_point:
                            prior_tutorial, tutorial_streak = tutorial_point, 1
                        else:
                            prior_tutorial, tutorial_streak = None, 0
                        if city_point and stable(city_point, prior_city):
                            city_streak += 1
                        elif city_point:
                            prior_city, city_streak = city_point, 1
                        else:
                            prior_city, city_streak = None, 0
                        if entry_streak >= 2 and entry_point:
                            return "normal_entry", image, entry_point
                        if tutorial_streak >= 2 and tutorial_point:
                            return "completed_tutorial", image, tutorial_point
                        if city_streak >= 2:
                            reviewed_point = reviewed_fixed_training_camp_point(kind, image)
                            if reviewed_point:
                                return "reviewed_city_camp", image, reviewed_point
                        set_state(
                            f"等待{label}普通入口、专属教程或主城固定布局"
                            f"（入口 {entry_streak}/2；教程 {tutorial_streak}/2；主城 {city_streak}/2）"
                        )
                        if self.stop_event.wait(interval):
                            return None
                    return None

                transition = wait_for_auxiliary_transition()
                if not transition:
                    self._log_for_device(
                        target.device,
                        f"{label}任务未在30秒统一窗口确认普通训练入口或专属教程目标；"
                        "未继续输入。",
                    )
                    return False
                transition_kind, _transition_image, transition_point = transition
                if transition_kind == "normal_entry":
                    entry_point = transition_point
                    target.tap(*entry_point)
                    self._log_for_device(target.device, f"{label}任务：点击已验证的普通训练入口 {entry_point}。")
                else:
                    tutorial_point = transition_point
                    target.tap(*tutorial_point)
                    tutorial_camp_clicked = True
                    if transition_kind == "completed_tutorial":
                        self._log_for_device(
                            target.device,
                            f"{label}任务：点击已双帧确认的专属教程兵营目标 {tutorial_point}。",
                        )
                    else:
                        self._log_for_device(
                            target.device,
                            f"{label}任务：精确前往血缘内已双帧确认主城；"
                            f"点击实机审核固定兵营 {tutorial_point}，后续仍强制双帧普通训练入口。",
                        )
                    double_enter_result = finish_training_camp_double_enter(
                        label,
                        kind,
                        tutorial_point,
                        tutorial_probe,
                        require_ordinary_entry=transition_kind == "reviewed_city_camp",
                    )
                    if double_enter_result == "active_queue":
                        return True
                    if double_enter_result != "normal_panel":
                        return False

                def wait_for_auxiliary_normal_panel(
                ) -> tuple[Image.Image, tuple[int, int]] | None:
                    """Handle one reviewed unlock reveal inside the same 30s step."""
                    deadline = time.monotonic() + AUTOMATION_STEP_TIMEOUT_SECONDS
                    prior_normal: tuple[int, int] | None = None
                    normal_streak = 0
                    prior_unlock: tuple[int, int] | None = None
                    unlock_streak = 0
                    unlock_continue_sent = False
                    while not self.stop_event.is_set() and time.monotonic() < deadline:
                        if duration and time.monotonic() - started >= duration * 60:
                            return None
                        if guard and not cached_foreground_is_game():
                            set_state("已暂停：游戏不在模拟器前台")
                            if self.stop_event.wait(interval):
                                return None
                            continue
                        image = daily_screenshot()
                        page = detect_daily_task_state(image, threshold)
                        if page.state is getattr(DailyTaskState, "BLOCKED", None):
                            self._log_for_device(
                                target.device,
                                f"{label}新兵种解锁转场出现付费页面；未输入并停止。",
                            )
                            return None

                        normal_point, _normal_score = (
                            match_daily_training_normal_button(image, threshold)
                        )
                        if normal_point and stable(normal_point, prior_normal):
                            normal_streak += 1
                        elif normal_point:
                            prior_normal, normal_streak = normal_point, 1
                        else:
                            prior_normal, normal_streak = None, 0
                        if normal_streak >= 2 and normal_point:
                            return image, normal_point

                        unlock_point: tuple[int, int] | None = None
                        if not unlock_continue_sent:
                            unlock_point, _unlock_score = (
                                match_daily_training_unlock_continue(image, threshold)
                            )
                            if unlock_point and stable(unlock_point, prior_unlock):
                                unlock_streak += 1
                            elif unlock_point:
                                prior_unlock, unlock_streak = unlock_point, 1
                            else:
                                prior_unlock, unlock_streak = None, 0
                            if unlock_streak >= 2 and unlock_point:
                                target.tap(*unlock_point)
                                unlock_continue_sent = True
                                prior_unlock, unlock_streak = None, 0
                                prior_normal, normal_streak = None, 0
                                self._log_for_device(
                                    target.device,
                                    f"{label}兵营：已在同一30秒转场窗口内点击双帧确认的"
                                    f"‘点击任意位置继续’ {unlock_point}；"
                                    "只继续等待蓝色普通训练面板。",
                                )
                                continue
                        else:
                            prior_unlock, unlock_streak = None, 0

                        set_state(
                            f"等待{label}普通训练面板"
                            f"（面板 {normal_streak}/2；解锁继续 {unlock_streak}/2）"
                        )
                        if self.stop_event.wait(interval):
                            return None
                    return None

                stage = wait_for_auxiliary_normal_panel()
                if not stage:
                    if tutorial_camp_clicked:
                        city_stage = wait_for_gather_step(
                            f"{label}教程让行后的每日任务入口",
                            lambda image: match_daily_city_entry(image, threshold),
                            15.0,
                        )
                        if city_stage:
                            _city_image, city_point = city_stage
                            target.tap(*city_point)
                            self._log_for_device(
                                target.device,
                                f"{label}教程兵营点击后已双帧返回主城；已重开每日任务 {city_point}。"
                                "不写入训练失败或等待锁；只由刷新后的精确进度卡决定是否开始下一批。",
                            )
                            return True
                    self._log_for_device(target.device, f"{label}任务未确认蓝色普通训练面板；未继续输入。")
                    return False
                _panel_image, normal_train_point = stage

                # A player-initiated queue can already occupy this camp.  It
                # shares the panel's blue action lane, so it must be detected
                # before attempting to locate the quantity-minus control.  We
                # only leave the verified active panel through its reviewed
                # back affordance, then continue unrelated Daily Tasks; no
                # speed-up, instant finish, cancel, or train input is allowed.
                active_stage = wait_for_gather_step(
                    f"{label}营已有训练队列",
                    lambda image: match_daily_training_active(image, threshold),
                    5.0,
                )
                if active_stage:
                    return defer_active_training_and_reopen_daily(label, kind)

                normal_train_point = set_daily_training_quantity_to_max(label)
                if not normal_train_point:
                    return False

                target.tap(*normal_train_point)
                self._log_for_device(target.device, f"{label}任务：点击已复核的蓝色普通训练 {normal_train_point}（数量已拉满）。")
                stage = wait_for_gather_step(
                    f"{label}普通训练队列",
                    lambda image: match_daily_training_active(image, threshold),
                    20.0,
                )
                if not stage:
                    self._log_for_device(target.device, f"{label}训练启动后未确认普通训练队列；未作恢复输入。")
                    return False
                return defer_active_training_and_reopen_daily(label, kind)

            def run_daily_building_upgrade_plan() -> bool:
                """Start only the ordinary building action routed by Daily Tasks.

                The task card's own ``Go`` control is validated by the caller.
                Here a separate ``建筑信息`` heading and a large blue normal
                action are required twice before one tap.  The yellow diamond
                completion control never occurs in this route and is not a
                candidate.  Once natural construction is visibly underway,
                return to Daily Tasks without touching its timer or speed-up.
                """
                nonlocal building_upgrade_unavailable, building_upgrade_retry_at, building_failed_scan
                started_wait = time.monotonic()
                deadline = started_wait + 6.0
                prior_build: tuple[int, int] | None = None
                build_streak = 0
                prior_city: tuple[int, int] | None = None
                city_streak = 0
                prior_active_detail: tuple[int, int] | None = None
                active_detail_streak = 0
                active_detail_back_sent = False
                build_point: tuple[int, int] | None = None
                while not self.stop_event.is_set() and time.monotonic() < deadline:
                    image = daily_screenshot()
                    page = detect_daily_task_state(image, threshold)
                    if page.state is DailyTaskState.BLOCKED:
                        self._log_for_device(target.device, "每日建筑任务转场出现付费页面；未继续输入。")
                        return False
                    current_build, _build_score = match_daily_normal_build_action(image, threshold)
                    if current_build and stable(current_build, prior_build):
                        build_streak += 1
                    elif current_build:
                        prior_build, build_streak = current_build, 1
                    else:
                        prior_build, build_streak = None, 0
                    if build_streak >= 2 and current_build:
                        build_point = current_build
                        break

                    current_active_detail, _active_detail_score = (
                        match_daily_building_active_upgrading(image, threshold)
                    )
                    if current_active_detail and stable(
                        current_active_detail, prior_active_detail
                    ):
                        active_detail_streak += 1
                    elif current_active_detail:
                        prior_active_detail, active_detail_streak = (
                            current_active_detail,
                            1,
                        )
                    else:
                        prior_active_detail, active_detail_streak = None, 0
                    if active_detail_streak >= 2 and not active_detail_back_sent:
                        active_detail_back_sent = True
                        building_upgrade_unavailable = True
                        building_failed_scan = True
                        building_upgrade_retry_at = (
                            time.monotonic() + DAILY_RETRY_LOCK_MAX_SECONDS
                        )
                        target.shell(["input", "keyevent", "4"])
                        self._log_for_device(
                            target.device,
                            "Active construction detail was double-confirmed; sent "
                            "one system Back and yielded only this building mission. "
                            "No instant completion, diamonds or speed-up were used.",
                        )
                        continue

                    city_point, _city_score = match_daily_city_entry(image, threshold)
                    if city_point and stable(city_point, prior_city):
                        city_streak += 1
                    elif city_point:
                        prior_city, city_streak = city_point, 1
                    else:
                        prior_city, city_streak = None, 0
                    # Let the routed screen render for at least one second,
                    # then two unchanged city frames prove that no normal
                    # build surface replaced it.  The city Daily coordinate
                    # is independently reviewed and is not a generic Back.
                    if (
                        time.monotonic() - started_wait >= 1.0
                        and city_streak >= 2
                        and city_point
                    ):
                        building_upgrade_unavailable = True
                        building_failed_scan = True
                        building_upgrade_retry_at = (
                            time.monotonic() + DAILY_RETRY_LOCK_MAX_SECONDS
                        )
                        target.tap(*city_point)
                        self._log_for_device(
                            target.device,
                            "每日建筑任务前往后两帧仍为主城，当前没有普通建造入口；"
                            f"仅重开每日任务 {city_point}，建筑项让行 10 秒并继续后续任务，"
                            "未点击立即完成、钻石或加速。",
                        )
                        return True

                if not build_point:
                    self._log_for_device(target.device, "每日建筑任务未复核到普通建造按钮；未继续输入。")
                    return False
                target.tap(*build_point)
                self._log_for_device(
                    target.device,
                    f"每日建筑任务：已点击双帧确认的普通建造按钮 {build_point}；不使用钻石或加速。",
                )

                # A started build returns to the ordinary city scene.  Reuse
                # the city task-strip proof and make no construction-related
                # input while waiting for the natural timer to finish.
                deadline = time.monotonic() + AUTOMATION_STEP_TIMEOUT_SECONDS
                prior_city: tuple[int, int] | None = None
                city_streak = 0
                while not self.stop_event.is_set() and time.monotonic() < deadline:
                    image = daily_screenshot()
                    page = detect_daily_task_state(image, threshold)
                    if page.state is DailyTaskState.BLOCKED:
                        self._log_for_device(target.device, "建筑任务启动后出现付费页面；未继续输入。")
                        return False
                    city_point, _score = match_daily_city_entry(image, threshold)
                    if city_point and stable(city_point, prior_city):
                        city_streak += 1
                    elif city_point:
                        prior_city, city_streak = city_point, 1
                    else:
                        prior_city, city_streak = None, 0
                    if city_streak >= 2 and city_point:
                        target.tap(*city_point)
                        self._log_for_device(target.device, f"建筑任务已启动，重新打开每日任务 {city_point} 并等待自然完成。")
                        return True
                    if self.stop_event.wait(interval):
                        return False
                self._log_for_device(target.device, "建筑任务启动后未复核到每日任务入口；未继续输入。")
                return False

            def run_alliance_help_cycle(daily_image: Image.Image) -> bool:
                """Clear available alliance help, then reopen Daily Tasks.

                This is a bounded navigation loop made of the independently
                reviewed city/alliance/mutual-help states already used by the
                dedicated Help page.  It never uses the small single-help
                fallback, donation buttons, diamonds, or any generic dialog
                close.  The Daily Tasks X is used only while this same worker
                has a verified Daily page in hand.
                """
                target.tap(*daily_task_close_point(daily_image))
                self._log_for_device(target.device, "每日流程：关闭已验证的每日任务页，开始检查联盟全部帮助。")
                # Each exact all-help action is double-frame checked before
                # the next one.  A busy alliance can therefore legitimately
                # take longer than the old 110-second window to drain.  Keep
                # the route bounded, but leave enough time to recognise the
                # verified empty Mutual Help page and take its single safe
                # return path instead of abandoning the Daily flow there.
                deadline = time.monotonic() + AUTOMATION_STEP_TIMEOUT_SECONDS
                help_clicks = 0
                help_cap_back_sent = False
                prior_help: tuple[int, int] | None = None
                help_streak = 0
                prior_city: tuple[int, int] | None = None
                city_streak = 0
                back_from_mutual = False
                back_from_home = False
                home_exit_attempts = 0
                prior_home_exit: tuple[int, int] | None = None
                home_exit_streak = 0
                city_to_alliance = False
                mutual_entry_tapped = False
                prior_alliance_entry: tuple[int, int] | None = None
                alliance_entry_streak = 0
                prior_mutual_entry: tuple[int, int] | None = None
                mutual_entry_streak = 0
                unknown_frames = 0
                relocate_streak = 0
                relocation_closed = False
                daily_still_open_streak = 0
                close_settle_deadline = time.monotonic() + 1.5
                while not self.stop_event.is_set() and time.monotonic() < deadline:
                    if duration and time.monotonic() - started >= duration * 60:
                        return False
                    if guard and not cached_foreground_is_game():
                        set_state("已暂停：游戏不在模拟器前台")
                        if self.stop_event.wait(interval):
                            return False
                        continue
                    image = daily_screenshot()
                    page = detect_alliance_page(image, threshold)
                    # The close can be consumed by the preceding reward
                    # animation.  Do not repeat an input with an unknown
                    # acknowledgement: if Daily itself remains visible in
                    # two fresh frames after settling, skip this help attempt
                    # and continue scanning the already-open task list.
                    if page.page is AlliancePage.UNKNOWN and time.monotonic() >= close_settle_deadline:
                        daily_state = detect_daily_task_state(image, threshold).state
                        if daily_state in (DailyTaskState.DAILY_PAGE, DailyTaskState.DAILY_LOGIN_COMPLETED,
                                           DailyTaskState.CLAIM_READY, DailyTaskState.TASK_CLAIM_READY):
                            daily_still_open_streak += 1
                            if daily_still_open_streak >= 2:
                                self._log_for_device(target.device, "联盟帮助入口未跳转；双帧确认仍在每日任务页，本轮跳过帮助并继续其他任务。")
                                return True
                            continue
                    daily_still_open_streak = 0
                    relocate_point = match_daily_relocate_prompt_close(image)
                    if relocate_point is not None:
                        relocate_streak += 1
                        if relocate_streak >= 2 and not relocation_closed:
                            target.tap(*relocate_point)
                            relocation_closed = True
                            mutual_entry_tapped = True
                            back_from_home = True
                            city_to_alliance = True
                            self._log_for_device(target.device, "联盟帮助：关闭已确认的迁城提示，跳过互助；未点击迁城。")
                        continue
                    relocate_streak = 0
                    city_alliance_point: tuple[int, int] | None = None
                    if page.page is AlliancePage.UNKNOWN:
                        city_alliance_point, _ = match_daily_city_alliance_entry(image, threshold)
                    # Unknown frames are a safety stop only when they are
                    # consecutive.  A verified page during a normal
                    # transition (help -> alliance -> city) resets the
                    # counter so transient loading frames cannot compound
                    # into a false stop later in the same route.
                    if page.page is not AlliancePage.UNKNOWN or city_alliance_point:
                        unknown_frames = 0
                    if page.page is AlliancePage.ALL_HELP_READY and page.point:
                        if help_clicks >= 25:
                            if not help_cap_back_sent:
                                target.shell(["input", "keyevent", "4"])
                                help_cap_back_sent = True
                                back_from_mutual = True
                                self._log_for_device(
                                    target.device,
                                    "联盟全部帮助达到25次上限，已从双帧确认互助页返回联盟主页以继续每日流程。",
                                )
                            continue
                        if stable(page.point, prior_help):
                            help_streak += 1
                        else:
                            prior_help, help_streak = page.point, 1
                        if help_streak >= 2:
                            target.tap(*page.point)
                            help_clicks += 1
                            prior_help, help_streak = None, 0
                            self.signals.clicks.emit(claims + help_clicks)
                            self._log_for_device(target.device, f"每日流程：点击已验证的联盟全部帮助 {page.point}（{help_clicks}/25）。")
                        else:
                            set_state(f"复核联盟全部帮助按钮（{help_streak}/2）")
                    elif page.page is AlliancePage.MUTUAL_HELP:
                        # Mutual Help has no all-help batch button now.  A
                        # system Back is safe only after the exact page header
                        # was recognised, and it returns to Alliance Home.
                        if not back_from_mutual:
                            target.shell(["input", "keyevent", "4"])
                            back_from_mutual = True
                            self._log_for_device(target.device, "联盟互助页无全部帮助，已从已验证页面返回联盟主页。")
                    elif page.page is AlliancePage.ALLIANCE_HOME:
                        if not mutual_entry_tapped and page.point:
                            if stable(page.point, prior_mutual_entry):
                                mutual_entry_streak += 1
                            else:
                                prior_mutual_entry, mutual_entry_streak = page.point, 1
                            if mutual_entry_streak >= 2:
                                target.tap(*page.point)
                                mutual_entry_tapped = True
                                prior_mutual_entry, mutual_entry_streak = None, 0
                                self._log_for_device(target.device, f"每日流程：从已验证联盟主页进入联盟互助 {page.point}。")
                        elif mutual_entry_tapped and page.point:
                            # A toast/transition can consume the first system
                            # Back while leaving the exact Alliance Home page
                            # visible.  Re-authorise at most one retry, and only
                            # after two fresh stable Home detections.  Never use
                            # a generic click or send more than two Back inputs.
                            if stable(page.point, prior_home_exit):
                                home_exit_streak += 1
                            else:
                                prior_home_exit, home_exit_streak = page.point, 1
                            if home_exit_streak >= 2 and home_exit_attempts < 2:
                                target.shell(["input", "keyevent", "4"])
                                home_exit_attempts += 1
                                back_from_home = True
                                prior_home_exit, home_exit_streak = None, 0
                                self._log_for_device(
                                    target.device,
                                    "联盟互助已检查；双帧确认联盟主页后发送返回主城 "
                                    f"（{home_exit_attempts}/2）。",
                                )
                    elif page.page is AlliancePage.CITY or city_alliance_point:
                        if not city_to_alliance:
                            entry_point = page.point if page.page is AlliancePage.CITY else city_alliance_point
                            if entry_point and stable(entry_point, prior_alliance_entry):
                                alliance_entry_streak += 1
                            elif entry_point:
                                prior_alliance_entry, alliance_entry_streak = entry_point, 1
                            else:
                                prior_alliance_entry, alliance_entry_streak = None, 0
                            if alliance_entry_streak >= 2 and entry_point:
                                target.tap(*entry_point)
                                city_to_alliance = True
                                prior_alliance_entry, alliance_entry_streak = None, 0
                                self._log_for_device(target.device, f"每日流程：从已验证主城进入联盟 {entry_point}。")
                            if adaptive_operation_wait(maximum=0.50):
                                return False
                            continue
                        # Returning to city is allowed only after the worker
                        # has first visited Alliance Home and backed out from
                        # the checked Mutual Help page.
                        if not back_from_home:
                            if adaptive_operation_wait(maximum=0.50):
                                return False
                            continue
                        city_point, _ = match_daily_city_entry(image, threshold)
                        if city_point and stable(city_point, prior_city):
                            city_streak += 1
                        elif city_point:
                            prior_city, city_streak = city_point, 1
                        else:
                            prior_city, city_streak = None, 0
                        if city_streak >= 2 and city_point:
                            target.tap(*city_point)
                            self._log_for_device(target.device, f"联盟帮助检查完成，已重开每日任务入口 {city_point}。")
                            return True
                    else:
                        unknown_frames += 1
                        if unknown_frames >= 8:
                            self._log_for_device(target.device, "联盟帮助导航出现未识别页面；未执行额外输入。")
                            return False
                    if adaptive_operation_wait(maximum=0.50):
                        return False
                self._log_for_device(target.device, "联盟帮助检查超时；未执行恢复输入。")
                return False

            def run_alliance_food_donation_plan() -> bool:
                """Spend only normal food donations, then reopen Daily Tasks.

                Each short hold is enabled only by two fresh frames of the
                paired blue-food and yellow-diamond layout.  The yellow
                control is proof only and never contributes a tap coordinate.
                This source has no reliable Alliance-Coin numeric reader, so
                it deliberately performs at most one 1200-ms segment: a still
                blue button cannot authorise another segment without a proved
                coin delta.  Two immediate post-segment frames decide grey
                exhaustion versus a 30-second fail-closed recheck.  Daily Tasks
                remains the only authority for the completed-count increase.
                """
                city_stage = wait_for_gather_step(
                    "联盟捐献任务的主城联盟入口",
                    lambda image: match_daily_city_alliance_entry(image, threshold),
                    30.0,
                )
                if not city_stage:
                    self._log_for_device(target.device, "联盟捐献任务未确认主城联盟入口；未继续输入。")
                    return False
                _city_image, alliance_entry = city_stage
                target.tap(*alliance_entry)
                self._log_for_device(target.device, f"联盟捐献任务：点击已验证的主城联盟入口 {alliance_entry}。")

                def alliance_tech_probe(image: Image.Image) -> tuple[tuple[int, int] | None, float]:
                    page = detect_alliance_page(image, threshold)
                    icon_point, icon_score = match_daily_alliance_tech_entry(image, threshold)
                    if page.page is AlliancePage.ALLIANCE_HOME and icon_point:
                        return daily_alliance_tech_entry_point(image), min(page.score, icon_score)
                    return None, min(page.score, icon_score)

                tech_stage = wait_for_gather_step("联盟科技显微镜入口", alliance_tech_probe, 30.0)
                if not tech_stage:
                    self._log_for_device(target.device, "联盟捐献任务未确认联盟科技入口；未继续输入。")
                    return False
                tech_image, tech_point = tech_stage
                target.tap(*tech_point)
                self._log_for_device(target.device, f"联盟捐献任务：点击已验证的联盟科技入口 {tech_point}。")

                battle_evidence_dir = (
                    Path.home()
                    / "Documents"
                    / "WJDR"
                    / "evidence"
                    / "milestone-10-battle-sustain-v476"
                )
                battle_evidence_counter = 0

                def record_battle_evidence(image: Image.Image, label: str, note: str) -> None:
                    """Persist only the de-identified tech-tree viewport and a short note."""
                    nonlocal battle_evidence_counter
                    battle_evidence_counter += 1
                    safe_label = "".join(ch if ch.isalnum() or ch in "-_" else "-" for ch in label)
                    try:
                        battle_evidence_dir.mkdir(parents=True, exist_ok=True)
                        left, top = map_content_point((40, 650), (1440, 2560), image)
                        right, bottom = map_content_point((1400, 2240), (1440, 2560), image)
                        crop = image.convert("RGB").crop((left, top, right, bottom))
                        stamp = (
                            time.strftime("%Y%m%d-%H%M%S")
                            + f"-{time.time_ns() % 1_000_000_000:09d}"
                        )
                        filename = (
                            f"{stamp}-{battle_evidence_counter:02d}-{safe_label}-safe.png"
                        )
                        crop.save(battle_evidence_dir / filename, optimize=True)
                        with (battle_evidence_dir / "run-notes.md").open(
                            "a", encoding="utf-8"
                        ) as handle:
                            handle.write(
                                f"- {time.strftime('%Y-%m-%d %H:%M:%S')} `{filename}`：{note}\n"
                            )
                    except OSError as exc:
                        self._log_for_device(
                            target.device,
                            f"联盟科技脱敏证据保存失败：{exc}；识别流程按安全规则继续。",
                        )

                def battle_selected_probe(
                    image: Image.Image,
                ) -> tuple[tuple[int, int] | None, float]:
                    return match_daily_alliance_tech_battle_tab_strip(image, threshold)

                def battle_tab_from_other_selected_probe(
                    image: Image.Image,
                ) -> tuple[tuple[int, int] | None, float]:
                    development_point, development_score = (
                        match_daily_alliance_tech_development_tab_strip(image, threshold)
                    )
                    if development_point:
                        return map_content_point((1175, 535), (1440, 2560), image), development_score
                    territory_point, territory_score = match_daily_alliance_tech_territory_tab_strip(
                        image, threshold
                    )
                    if territory_point:
                        return map_content_point((1175, 535), (1440, 2560), image), territory_score
                    return None, max(development_score, territory_score)

                def scan_battle_for_sustain_node() -> tuple[Image.Image, tuple[int, int]] | None:
                    """Reset and scan Battle only; every gesture needs tab and pixel proof."""
                    selected_stage = wait_for_gather_step(
                        "联盟科技战斗页完整标签栏",
                        battle_selected_probe,
                        5.0,
                    )
                    if not selected_stage:
                        switch_stage = wait_for_gather_step(
                            "联盟科技发展或领地页完整标签栏",
                            battle_tab_from_other_selected_probe,
                            12.0,
                        )
                        if not switch_stage:
                            self._log_for_device(
                                target.device,
                                "联盟捐献任务未双帧确认战斗、发展或领地完整标签栏；未继续输入。",
                            )
                            return None
                        switch_image, battle_tab = switch_stage
                        record_battle_evidence(
                            switch_image,
                            "before-battle-switch",
                            "完整标签栏已连续两帧确认；只允许切换到战斗标签。",
                        )
                        target.tap(*battle_tab)
                        self._log_for_device(
                            target.device,
                            f"联盟捐献任务：非战斗完整标签栏已双帧精确确认，仅切换到战斗标签 {battle_tab}。",
                        )
                        selected_stage = wait_for_gather_step(
                            "切换后的联盟科技战斗页完整标签栏",
                            battle_selected_probe,
                            12.0,
                        )
                        if not selected_stage:
                            self._log_for_device(
                                target.device,
                                "联盟捐献任务切换战斗标签后未获双帧精确确认；未继续输入。",
                            )
                            return None

                    current_image, _selected_point = selected_stage
                    record_battle_evidence(
                        current_image,
                        "battle-selected",
                        "战斗选中态已连续两帧精确确认；目标仅为用户指定的联盟永续标题。",
                    )
                    max_swipes = 12

                    def exact_node(image: Image.Image) -> tuple[tuple[int, int] | None, float, float]:
                        battle_point, battle_score = battle_selected_probe(image)
                        node_match, node_score = match_daily_alliance_sustain_node(
                            image, threshold
                        )
                        if not battle_point or not node_match:
                            return None, battle_score, node_score
                        return daily_alliance_sustain_node_point(image), battle_score, node_score

                    def checked_gesture(
                        direction: str,
                        index: int,
                    ) -> tuple[Image.Image, float] | None:
                        before_stage = wait_for_gather_step(
                            "联盟科技战斗页滑动前完整标签栏",
                            battle_selected_probe,
                            8.0,
                        )
                        if not before_stage:
                            self._log_for_device(
                                target.device,
                                "联盟科技战斗树滑动前未获双帧标签证据；未继续输入。",
                            )
                            return None
                        before_image, _before_point = before_stage
                        if direction == "reset-up":
                            start_reference, end_reference = (720, 900), (720, 1900)
                        else:
                            start_reference, end_reference = (720, 1900), (720, 900)
                        start_point = map_content_point(start_reference, (1440, 2560), before_image)
                        end_point = map_content_point(end_reference, (1440, 2560), before_image)
                        target.shell(
                            [
                                "input",
                                "swipe",
                                str(start_point[0]),
                                str(start_point[1]),
                                str(end_point[0]),
                                str(end_point[1]),
                                "900",
                            ]
                        )
                        after_stage = wait_for_gather_step(
                            "联盟科技战斗页滑动后完整标签栏",
                            battle_selected_probe,
                            10.0,
                        )
                        if not after_stage:
                            self._log_for_device(
                                target.device,
                                "联盟科技战斗树滑动后未获双帧标签证据；未继续输入。",
                            )
                            return None
                        after_image, _after_point = after_stage
                        movement = alliance_tech_tree_viewport_mean_change(
                            before_image, after_image
                        )
                        record_battle_evidence(
                            after_image,
                            f"battle-{direction}-{index:02d}",
                            f"战斗树滑动后像素平均变化 {movement:.3f}；本视口已检查联盟永续。",
                        )
                        return after_image, movement

                    node_point, battle_score, node_score = exact_node(current_image)
                    if node_point:
                        record_battle_evidence(
                            current_image,
                            "alliance-sustain-found",
                            "战斗标签与用户指定的联盟永续标题同帧成立，允许点击精确节点。",
                        )
                        self._log_for_device(
                            target.device,
                            "联盟科技战斗树已确认联盟永续节点："
                            f"标签 {battle_score:.6f}，节点 {node_score:.6f}。",
                        )
                        return current_image, node_point

                    # First prove the real top.  This avoids missing the node
                    # when the game restores an old scroll position.
                    top_stationary_streak = 0
                    for reset_index in range(1, max_swipes + 1):
                        gesture_result = checked_gesture("reset-up", reset_index)
                        if not gesture_result:
                            return None
                        current_image, movement = gesture_result
                        node_point, battle_score, node_score = exact_node(current_image)
                        if node_point:
                            record_battle_evidence(
                                current_image,
                                "alliance-sustain-found",
                                "回到战斗树顶部途中发现用户指定的联盟永续标题。",
                            )
                            return current_image, node_point
                        top_stationary_streak = (
                            top_stationary_streak + 1 if movement <= 0.7 else 0
                        )
                        self._log_for_device(
                            target.device,
                            "联盟科技战斗树顶部复位后的视口平均变化为 "
                            f"{movement:.3f}；顶部静止确认 {top_stationary_streak}/2；"
                            f"滑动 {reset_index}/{max_swipes}。",
                        )
                        if top_stationary_streak >= 2:
                            break
                    if top_stationary_streak < 2:
                        self._log_for_device(
                            target.device,
                            "联盟科技战斗树达到 12 次顶部复位上限但没有边界证明；未继续输入。",
                        )
                        return None

                    bottom_stationary_streak = 0
                    for scan_index in range(1, max_swipes + 1):
                        node_point, battle_score, node_score = exact_node(current_image)
                        if node_point:
                            record_battle_evidence(
                                current_image,
                                "alliance-sustain-found",
                                "战斗树向下扫描中发现用户指定的联盟永续标题。",
                            )
                            return current_image, node_point
                        gesture_result = checked_gesture("scan-down", scan_index)
                        if not gesture_result:
                            return None
                        current_image, movement = gesture_result
                        node_point, battle_score, node_score = exact_node(current_image)
                        if node_point:
                            record_battle_evidence(
                                current_image,
                                "alliance-sustain-found",
                                "战斗树向下扫描中发现用户指定的联盟永续标题。",
                            )
                            self._log_for_device(
                                target.device,
                                "联盟科技战斗树已确认联盟永续节点："
                                f"标签 {battle_score:.6f}，节点 {node_score:.6f}。",
                            )
                            return current_image, node_point
                        bottom_stationary_streak = (
                            bottom_stationary_streak + 1 if movement <= 0.7 else 0
                        )
                        self._log_for_device(
                            target.device,
                            "联盟科技战斗树向下扫描后的视口平均变化为 "
                            f"{movement:.3f}；底部静止确认 {bottom_stationary_streak}/2；"
                            f"滑动 {scan_index}/{max_swipes}。",
                        )
                        if bottom_stationary_streak >= 2:
                            self._log_for_device(
                                target.device,
                                "联盟科技战斗树已由连续两次无位移确认到底，"
                                "完整扫描未找到联盟永续；未继续输入。",
                            )
                            return None
                    self._log_for_device(
                        target.device,
                        "联盟科技战斗树达到 12 次向下扫描上限但没有边界证明；未继续输入。",
                    )
                    return None

                def visible_recommended_tech_probe(image: Image.Image) -> tuple[tuple[int, int] | None, float]:
                    # A green shape elsewhere must never authorise a tap.  The
                    # current tech tree and the marker are proved together;
                    # wait_for_gather_step requires two fresh stable frames.
                    tabs = (
                        match_daily_alliance_tech_development_tab_strip(image, threshold),
                        match_daily_alliance_tech_territory_tab_strip(image, threshold),
                        match_daily_alliance_tech_battle_tab_strip(image, threshold),
                    )
                    tab_score = max((score for point, score in tabs if point), default=0.0)
                    if not tab_score:
                        return None, 0.0
                    marker, marker_score = recommended_tech(image)
                    return marker, min(tab_score, marker_score)

                node_stage = wait_for_gather_step("当前科技树绿色推荐", visible_recommended_tech_probe, 3.0)
                recommended_node = node_stage is not None
                if not node_stage:
                    node_stage = scan_battle_for_sustain_node()
                if not node_stage:
                    self._log_for_device(
                        target.device,
                        "联盟捐献任务未在安全战斗树扫描中确认用户指定的联盟永续节点；未继续输入。",
                    )
                    return False
                node_image, node_point = node_stage
                target.tap(*node_point)
                node_label = "绿色推荐" if recommended_node else "联盟永续"
                self._log_for_device(target.device, f"联盟捐献任务：点击双帧确认的{node_label}节点 {node_point}。")

                nonlocal alliance_donation_unavailable
                nonlocal alliance_donation_retry_at
                nonlocal alliance_donation_prerequisite_blocked
                nonlocal alliance_donation_confirmed_clicks
                nonlocal alliance_donation_window_clicks

                # From the reviewed node tap through donation-page proof,
                # the exact ten-second hold, its two post frames, and the reviewed
                # return, this correlated route shares one <=30-second wall.
                donation_route_deadline = time.monotonic() + min(
                    AUTOMATION_STEP_TIMEOUT_SECONDS,
                    30.0,
                )
                # Classify the two reviewed donation states concurrently.
                # Waiting the whole route only for the blue control starved a
                # page that was already stably grey, then left no deadline
                # headroom for the reviewed Back route.  Two immediate frames
                # now prove either blue+yellow (one hold allowed) or the exact
                # grey exhausted page (no donation input, return at once).
                stage: tuple[Image.Image, tuple[int, int]] | None = None
                image: Image.Image | None = None
                food_streak = 0
                grey_streak = 0
                previous_food: tuple[int, int] | None = None
                prerequisite_streak = 0
                prerequisite_sent: set[str] = set()
                prerequisite_kind = ""
                locked_streak = 0
                locked_skipped = False
                availability_deadline = min(
                    donation_route_deadline,
                    time.monotonic() + 3.0,
                )
                while (
                    not self.stop_event.is_set()
                    and time.monotonic() < availability_deadline
                ):
                    candidate = capture_daily_image()
                    locked_close = match_daily_deep_tech_locked_close(candidate)
                    if locked_close is not None:
                        locked_streak += 1
                        if locked_streak >= 2:
                            target.tap(*locked_close)
                            locked_skipped = True
                            alliance_donation_unavailable = True
                            alliance_donation_retry_at = 0.0
                            alliance_donation_prerequisite_blocked = True
                            save_daily_donation_state()
                            self._log_for_device(target.device, "前置科技仍未解锁，关闭已确认页面，本次跳过联盟捐献并继续日常。")
                            break
                        continue
                    locked_streak = 0
                    candidate_food, _ = match_daily_alliance_food_donation(
                        candidate, threshold
                    )
                    candidate_page = daily_alliance_donation_page_is_visible(
                        candidate, threshold
                    )
                    prerequisite = match_daily_sustain_prerequisite_go(candidate)
                    candidate_kind = "sustain"
                    if prerequisite is None:
                        prerequisite = match_daily_sustain_prerequisite_go(candidate, troop_life=True)
                        candidate_kind = "troop"
                    if prerequisite is not None and candidate_kind not in prerequisite_sent:
                        prerequisite_streak = prerequisite_streak + 1 if prerequisite_kind == candidate_kind else 1
                        prerequisite_kind = candidate_kind
                        if prerequisite_streak >= 2:
                            target.tap(*prerequisite)
                            prerequisite_sent.add(candidate_kind)
                            availability_deadline = min(donation_route_deadline, time.monotonic() + 5.0)
                            self._log_for_device(target.device, "联盟永续未解锁：已进入双帧确认的部队生命值前置科技；尚未捐献。")
                        continue
                    if prerequisite is None:
                        prerequisite_streak = 0
                    if candidate_food:
                        food_streak = (
                            food_streak + 1
                            if previous_food and stable(previous_food, candidate_food)
                            else 1
                        )
                        previous_food = candidate_food
                        grey_streak = 0
                        if food_streak >= 2:
                            stage = (candidate, candidate_food)
                            image = candidate
                            break
                    elif candidate_page:
                        grey_streak += 1
                        food_streak = 0
                        previous_food = None
                        if grey_streak >= 2:
                            image = candidate
                            alliance_donation_unavailable = True
                            defer_daily_donation(
                                DAILY_DONATION_UNAVAILABLE_RETRY_SECONDS
                            )
                            self._log_for_device(
                                target.device,
                                "联盟捐献任务：连续两帧确认普通粮食按钮已灰；"
                                "未等待蓝色按钮、未再次长按，立即返回并继续后续任务；"
                                "黄色钻石捐献未触碰。",
                            )
                            break
                    else:
                        food_streak = 0
                        grey_streak = 0
                        previous_food = None

                if stage is None and image is None and not locked_skipped:
                    self._log_for_device(
                        target.device,
                        "联盟捐献任务在3秒内未双帧确认蓝色普通按钮或灰色耗尽页；未继续输入。",
                    )
                    return False

                if stage:
                    _before, food_point = stage
                    image = _before
                    # ``stage`` is already a two-fresh-frame proof of this
                    # exact blue control and its yellow sibling.  The game
                    # consumes the available ordinary donations while this
                    # button is held and automatically greys it at the cap,
                    # so one exact ten-second hold is both the fastest and
                    # safest reviewed action.  A blue post-state still cannot
                    # authorise a second hold without fresh task-page proof.
                    target.shell(
                        [
                            "input",
                            "swipe",
                            str(food_point[0]),
                            str(food_point[1]),
                            str(food_point[0]),
                            str(food_point[1]),
                            "10000",
                        ],
                        timeout=12,
                    )
                    self._log_for_device(
                        target.device,
                        "联盟捐献任务：已对双帧确认的蓝色普通肉类捐献按钮执行一次完整 10000ms 长按；"
                        "立即连续取两帧，不点击黄色钻石。",
                    )
                    post_blue_streak = 0
                    disabled_streak = 0
                    post_image: Image.Image | None = None
                    # Consecutive recognition starts immediately: processing
                    # time is not padded by an intentional delay.  Exactly two
                    # frames are enough for this single reviewed hold.
                    for _post_index in range(2):
                        if (
                            self.stop_event.is_set()
                            or time.monotonic() >= donation_route_deadline
                        ):
                            break
                        candidate = capture_daily_image()
                        candidate_food, _ = match_daily_alliance_food_donation(
                            candidate, threshold
                        )
                        disabled = (
                            candidate_food is None
                            and daily_alliance_donation_page_is_visible(candidate, threshold)
                        )
                        post_blue_streak = post_blue_streak + 1 if candidate_food else 0
                        disabled_streak = disabled_streak + 1 if disabled else 0
                        post_image = candidate
                    if disabled_streak >= 2:
                        alliance_donation_window_clicks = DAILY_DONATION_WINDOW_CAP
                        alliance_donation_unavailable = True
                        defer_daily_donation(DAILY_DONATION_WINDOW_RETRY_SECONDS)
                        self._log_for_device(
                            target.device,
                            "联盟捐献任务：10000ms 长按后连续两帧确认普通捐献按钮变灰，"
                            "当前可用窗口耗尽；不按时长推断次数，具体增长由每日任务页复核，"
                            "10 秒后仅复查下一窗口。",
                        )
                    elif post_blue_streak >= 2:
                        alliance_donation_unavailable = True
                        defer_daily_donation(DAILY_DONATION_UNAVAILABLE_RETRY_SECONDS)
                        self._log_for_device(
                            target.device,
                            "联盟捐献任务：10000ms 长按后按钮仍连续两帧为蓝色；"
                            "本轮不允许第二次长按，10 秒后返回每日任务页重新验证进度。",
                        )
                    else:
                        alliance_donation_unavailable = True
                        defer_daily_donation(DAILY_DONATION_UNAVAILABLE_RETRY_SECONDS)
                        self._log_for_device(
                            target.device,
                            "联盟捐献任务：10000ms 长按后的两帧状态不一致或总路线达到30秒上限；"
                            "未再次长按或点击，10 秒后仅复查可用性。",
                        )

                    if post_image is not None:
                        image = post_image

                assert image is not None or locked_skipped
                if time.monotonic() >= donation_route_deadline:
                    self._log_for_device(
                        target.device,
                        "联盟捐献关联路线已达到30秒总上限；未再发送返回或恢复输入。",
                    )
                    return False
                if not locked_skipped and not daily_alliance_donation_page_is_visible(image, threshold):
                    self._log_for_device(target.device, "联盟捐献结束时未复核到捐献页；未执行返回输入。")
                    return False
                # Android Back is permitted only after the dual donation
                # layout has been reconfirmed.  It closes this exact modal to
                # Alliance Home without choosing either donation option.
                if not locked_skipped:
                    target.shell(["input", "keyevent", "4"])
                deadline = donation_route_deadline
                back_from_tech = False
                back_from_home = False
                city_point: tuple[int, int] | None = None
                city_streak = 0
                unknown_frames = 0
                while not self.stop_event.is_set() and time.monotonic() < deadline:
                    if adaptive_operation_wait(maximum=0.50):
                        return False
                    image = daily_screenshot()
                    page = detect_alliance_page(image, threshold)
                    sustain_node, _ = match_daily_alliance_sustain_node(image, threshold)
                    if sustain_node:
                        unknown_frames = 0
                        if not back_from_tech:
                            target.shell(["input", "keyevent", "4"])
                            back_from_tech = True
                            self._log_for_device(target.device, "联盟捐献任务：已从已验证联盟科技页返回联盟主页。")
                        continue
                    if page.page is AlliancePage.ALLIANCE_HOME:
                        unknown_frames = 0
                        if not back_from_home:
                            target.shell(["input", "keyevent", "4"])
                            back_from_home = True
                            self._log_for_device(target.device, "联盟捐献任务：已从联盟主页返回主城。")
                        continue
                    if page.page is AlliancePage.CITY:
                        unknown_frames = 0
                        candidate, _ = match_daily_city_entry(image, threshold)
                        if candidate and stable(candidate, city_point):
                            city_streak += 1
                        elif candidate:
                            city_point, city_streak = candidate, 1
                        else:
                            city_point, city_streak = None, 0
                        if city_streak >= 2 and city_point:
                            target.tap(*city_point)
                            self._log_for_device(target.device, f"联盟捐献任务：已重开每日任务入口 {city_point}。")
                            return True
                        continue
                    unknown_frames += 1
                    if unknown_frames >= 8:
                        self._log_for_device(target.device, "联盟捐献返回路线出现连续未知页；未执行额外输入。")
                        return False
                self._log_for_device(target.device, "联盟捐献返回每日任务超时；未执行恢复输入。")
                return False

            def run_free_hero_recruit_plan() -> bool:
                """Use exactly one verified green free hero recruit.

                A yellow key recruit, a 10x recruit, and every paid option
                fail the free-green template and consequently have no click
                path. The current Daily card requires one recruit. Its reward
                sheet is closed only with Android Back after a two-frame,
                same-run match; no coordinate on that sheet is tappable.
                """
                nonlocal hero_recruit_unavailable

                stage = wait_for_gather_step(
                    "英雄招募页面",
                    lambda image: ((720, 220) if daily_hero_recruit_page_is_visible(image, threshold) else None, 1.0),
                    30.0,
                )
                if not stage:
                    self._log_for_device(target.device, "英雄任务未确认招募页面；未继续输入。")
                    return False

                def wait_for_correlated_hero_result(
                    timeout: float,
                ) -> tuple[str, Image.Image, tuple[int, int]] | None:
                    """Classify duplicate reveal and summary concurrently.

                    Neither layout owns fallback input.  The caller reaches
                    this helper only after its own verified free-recruit tap;
                    the same result kind and point must persist for two fresh
                    frames before a page-specific exit is exposed.
                    """

                    deadline = time.monotonic() + bounded_step_timeout(timeout)
                    prior_kind = ""
                    prior_point: tuple[int, int] | None = None
                    streak = 0
                    while not self.stop_event.is_set() and time.monotonic() < deadline:
                        if duration and time.monotonic() - started >= duration * 60:
                            return None
                        if guard and not cached_foreground_is_game():
                            set_state("已暂停：游戏不在模拟器前台")
                            if self.stop_event.wait(interval):
                                return None
                            continue
                        image = capture_daily_image()
                        duplicate_point, _duplicate_score = (
                            match_daily_hero_recruit_duplicate_result(image, threshold)
                        )
                        summary_point, _summary_score = (
                            match_daily_hero_recruit_summary_exit(image, threshold)
                        )
                        if summary_point:
                            kind, point = "summary", summary_point
                        elif duplicate_point:
                            kind, point = "duplicate", duplicate_point
                        else:
                            kind, point = "", None
                        if kind and kind == prior_kind and stable(point, prior_point):
                            streak += 1
                        elif kind and point:
                            prior_kind, prior_point, streak = kind, point, 1
                        else:
                            prior_kind, prior_point, streak = "", None, 0
                        set_state(f"确认关联英雄招募结果 {kind or '转场'}（{streak}/2）")
                        if streak >= 2 and point:
                            return kind, image, point
                        if self.stop_event.wait(interval):
                            return None
                    return None

                recruits = 0
                for index in range(1):
                    stage = wait_for_gather_step(
                        "绿色免费招募按钮",
                        lambda image: match_daily_hero_free_recruit(image, threshold),
                        16.0,
                    )
                    if not stage:
                        image = daily_screenshot()
                        if daily_hero_recruit_page_is_visible(image, threshold):
                            defer_hero_recruit()
                            self._log_for_device(
                                target.device,
                                "英雄任务：当前没有已验证的绿色免费高级招募；保留钥匙/钻石按钮不点，"
                                "记录本账号五分钟冷却并继续其他每日任务。",
                            )
                            break
                        self._log_for_device(target.device, "英雄任务免费招募按钮未确认且页面变化；未继续输入。")
                        return False
                    _image, free_point = stage
                    target.tap(*free_point)
                    recruits += 1
                    defer_hero_recruit()
                    self._log_for_device(target.device, f"英雄任务：点击已验证的绿色免费招募 {free_point}（{recruits}/1）。")

                    result = wait_for_correlated_hero_result(30.0)
                    if not result:
                        self._log_for_device(target.device, "免费招募后未确认关联奖励页；未执行退出点击。")
                        return False
                    result_kind, _result_image, result_point = result
                    if result_kind == "duplicate":
                        target.shell(["input", "keyevent", "4"])
                        self._log_for_device(
                            target.device,
                            "英雄任务：双帧确认重复英雄揭示页后发送一次 Android 返回；"
                            "等待其关联奖励汇总页，未点击任何英雄、技能、钥匙或钻石。",
                        )
                        result = wait_for_correlated_hero_result(20.0)
                        if not result or result[0] != "summary":
                            self._log_for_device(
                                target.device,
                                "重复英雄揭示页返回后未双帧确认关联奖励汇总页；未继续输入。",
                            )
                            return False
                        _summary_kind, _summary_image, result_point = result
                    target.tap(*result_point)
                    self._log_for_device(
                        target.device,
                        f"英雄任务：完整‘点击任意位置退出’文字已双帧OCR确认；"
                        f"只点击侧边空白点 {result_point}，未点击黄色招募、钥匙或钻石。",
                    )
                    if adaptive_operation_wait(maximum=0.50):
                        return False

                page_stage = wait_for_gather_step(
                    "免费招募后的英雄招募页",
                    lambda image: (
                        daily_hero_recruit_back_point(image)
                        if daily_hero_recruit_page_is_visible(image, threshold)
                        else None,
                        1.0,
                    ),
                    20.0,
                )
                if not page_stage:
                    self._log_for_device(target.device, "英雄任务结束时未双帧确认招募页；未执行返回。")
                    return False
                _page_image, back_point = page_stage
                target.tap(*back_point)
                self._log_for_device(target.device, f"英雄任务：从已验证招募页返回主城 {back_point}。")

                deadline = time.monotonic() + AUTOMATION_STEP_TIMEOUT_SECONDS
                prior_city: tuple[int, int] | None = None
                city_streak = 0
                while not self.stop_event.is_set() and time.monotonic() < deadline:
                    image = daily_screenshot()
                    city_point, _ = match_daily_city_entry(image, threshold)
                    if city_point and stable(city_point, prior_city):
                        city_streak += 1
                    elif city_point:
                        prior_city, city_streak = city_point, 1
                    else:
                        prior_city, city_streak = None, 0
                    if city_streak >= 2 and city_point:
                        target.tap(*city_point)
                        self._log_for_device(target.device, f"英雄任务：已重开每日任务入口 {city_point}。")
                        return True
                    if self.stop_event.wait(interval):
                        return False
                self._log_for_device(target.device, "英雄任务结束后未确认每日任务入口；未继续输入。")
                return False

            self._log_for_device(
                target.device,
                "开始每日奖励收取：连续双帧复核不主动等待；转场等待最多 1.50 秒；"
                "仅点击已验证的绿色领取；F8 可停止。",
            )
            set_state("检查主城任务入口或已打开的每日任务页")
            while not self.stop_event.is_set():
                now = time.monotonic()
                if now < idle_no_input_until:
                    remaining = idle_no_input_until - now
                    set_state(
                        f"无输入等待中：{idle_no_input_label}；"
                        f"{max(1, round(remaining))} 秒后复核"
                    )
                    if self.stop_event.wait(min(MAX_SINGLE_WAIT_SECONDS, remaining)):
                        break
                    continue
                if duration and now - started >= duration * 60:
                    self._log_for_device(target.device, "每日奖励收取达到最长运行时间，已停止。")
                    break
                try:
                    emit_diagnostic = now - last_loop_diagnostic_at >= 30.0
                    if emit_diagnostic:
                        last_loop_diagnostic_at = now
                        self._log_for_device(target.device, "每日流程心跳：准备检查游戏前台状态。")
                    game_foreground = cached_foreground_is_game()
                    if guard and not game_foreground:
                        if emit_diagnostic:
                            self._log_for_device(target.device, "每日流程心跳：游戏不在 Android 前台，保持零输入等待。")
                        set_state("已暂停：游戏不在模拟器前台")
                    else:
                        if emit_diagnostic:
                            self._log_for_device(target.device, "每日流程心跳：游戏前台已确认，开始读取任务页面。")
                        image = capture_daily_image()
                        if daily_network_dialog_is_visible(image, threshold):
                            set_state(
                                "游戏显示网络/账号离线：保持零输入并被动复查；不点击重新连接或联系客服"
                            )
                            if emit_diagnostic:
                                self._log_for_device(
                                    target.device,
                                    "检测到精确无网络或强制下线文字；主每日进程保持运行且未点击重新连接、联系客服、关闭或返回。",
                                )
                            if adaptive_operation_wait(minimum=0.5, maximum=3.0):
                                break
                            continue
                        welcome_back_point = match_daily_welcome_back_confirm(
                            image,
                            threshold,
                        )
                        if welcome_back_point is not None:
                            if welcome_back_confirm_sent:
                                set_state(
                                    "已点击一次双帧确认的欢迎回来结算；等待页面自然离开，不重复输入"
                                )
                                if self.stop_event.wait(min(MAX_SINGLE_WAIT_SECONDS, max(0.03, interval))):
                                    break
                                continue
                            welcome_back_streak += 1
                            set_state(
                                "确认欢迎回来离线结算"
                                f"（{welcome_back_streak}/2）：仅允许普通绿色确定"
                            )
                            if welcome_back_streak < 2:
                                if self.stop_event.wait(min(MAX_SINGLE_WAIT_SECONDS, max(0.03, interval))):
                                    break
                                continue
                            target.tap(*welcome_back_point)
                            welcome_back_confirm_sent = True
                            welcome_back_streak = 0
                            transition_deadline = time.monotonic() + 8.0
                            last_state = None
                            self._log_for_device(
                                target.device,
                                "每日启动恢复：点击一次双帧确认的欢迎回来离线结算普通绿色确定；"
                                "未点击关闭、购买、钻石或任意奖励页，立即恢复后续每日任务。",
                            )
                            continue
                        welcome_back_streak = 0

                        # A top reset is already correlated to a verified
                        # Daily page and its exact pre-gesture frame.  Do not
                        # rerun the expensive whole-page classifier between
                        # list-only gestures: prove the two immutable Daily
                        # anchors, compare only the task viewport, and either
                        # finish or issue the next inertial confirmation.
                        if daily_list_reset_pending and daily_list_reset_before_image is not None:
                            fast_header, fast_header_score = match_daily_task_header(
                                image, threshold
                            )
                            fast_tab, fast_tab_score = match_daily_task_selected_tab(
                                image, threshold
                            )
                            if not fast_header or not fast_tab:
                                daily_list_fast_anchor_miss_streak += 1
                                set_state(
                                    "高速回顶后等待每日页轻量锚点"
                                    f"（{daily_list_fast_anchor_miss_streak}/2）"
                                )
                                if daily_list_fast_anchor_miss_streak >= 2:
                                    self._log_for_device(
                                        target.device,
                                        "高速回顶后连续两帧未确认每日标题和已选标签；"
                                        "未继续滑动或点击；已丢弃本次手势关联并回退到完整页面分类。",
                                    )
                                    daily_list_reset_before_image = None
                                    daily_list_reset_settle_image = None
                                    daily_list_fast_anchor_miss_streak = 0
                                    last_state = None
                                    continue
                                if adaptive_operation_wait(maximum=0.20):
                                    break
                                continue
                            daily_list_fast_anchor_miss_streak = 0
                            # A fast fling can briefly overscroll and bounce
                            # even at the true top.  Never stack another input
                            # on that transient frame.  First require two
                            # passive post-gesture frames to settle, then
                            # compare the settled result with the stable
                            # pre-gesture frame.  A normal mid-list settle is
                            # stable too, but it differs from the origin and
                            # therefore cannot prove the top.
                            if daily_list_reset_settle_image is None:
                                daily_list_reset_settle_image = image.copy()
                                set_state("高速回顶后等待列表回弹稳定（1/2）")
                                if adaptive_operation_wait(maximum=0.20):
                                    break
                                continue
                            settle_movement = daily_task_list_viewport_mean_change(
                                daily_list_reset_settle_image, image
                            )
                            if settle_movement > DAILY_TASK_LIST_BOUNDARY_MAX_MEAN_CHANGE:
                                daily_list_reset_settle_image = image.copy()
                                set_state("高速回顶后列表仍在回弹，继续无输入复核")
                                self._log_for_device(
                                    target.device,
                                    "高速回顶后的相邻被动帧平均变化为 "
                                    f"{settle_movement:.3f}；未叠加下一次手势。",
                                )
                                if adaptive_operation_wait(maximum=0.20):
                                    break
                                continue
                            movement = daily_task_list_viewport_mean_change(
                                daily_list_reset_before_image, image
                            )
                            daily_list_reset_before_image = None
                            daily_list_reset_settle_image = None
                            if movement <= DAILY_TASK_LIST_BOUNDARY_MAX_MEAN_CHANGE:
                                daily_list_reset_boundary_streak += 1
                            else:
                                daily_list_reset_boundary_streak = 0
                            self._log_for_device(
                                target.device,
                                "高速回顶回弹稳定后，起点/终点列表平均变化为 "
                                f"{movement:.3f}（被动稳定 {settle_movement:.3f}）；顶部静止确认 "
                                f"{daily_list_reset_boundary_streak}/"
                                f"{DAILY_TASK_LIST_BOUNDARY_CONFIRMATIONS}；"
                                f"每日锚点 {fast_header_score:.3f}/{fast_tab_score:.3f}。",
                            )
                            if (
                                daily_list_reset_boundary_streak
                                >= DAILY_TASK_LIST_BOUNDARY_CONFIRMATIONS
                            ):
                                daily_list_reset_pending = False
                                daily_scrolls = 0
                                daily_list_scan_before_image = None
                                daily_list_bottom_boundary_streak = 0
                                last_state = None
                                if daily_completed_zone_wait_after_top:
                                    daily_completed_zone_wait_after_top = False
                                    (
                                        idle_wait_seconds,
                                        idle_no_input_label,
                                        _refresh_visible,
                                        _estimated,
                                    ) = daily_idle_wait_plan(image, 0.0, 0.0)
                                    idle_no_input_until = (
                                        time.monotonic() + idle_wait_seconds
                                    )
                                    set_state(
                                        "已确认回到任务顶部；"
                                        f"{idle_no_input_label}后重新领取并检查"
                                    )
                                    self._log_for_device(
                                        target.device,
                                        "绿色打勾区以下已全部跳过；列表已由轻量像素双确认回到顶部，"
                                        f"保持零输入到{idle_no_input_label}边界后再领取并检查。",
                                    )
                                    continue
                                set_state("已用两次轻量像素比对确认列表顶部，立即扫描首项")
                                self._log_for_device(
                                    target.device,
                                    "每日任务列表顶部已由连续两次滑动前后近似图确认；"
                                    "不再执行全页面复位循环，立即从首项扫描。",
                                )
                                continue
                            if not send_daily_fast_top_gesture(image):
                                set_state("高速回顶未在限次内确认每日任务列表顶部：不输入并停止")
                                self._log_for_device(
                                    target.device,
                                    "每日任务高速回顶已达到十二次逐帧比对安全上限，"
                                    "但没有连续两次近似图；"
                                    "未把当前位置当作顶部，已停止。",
                                )
                                break
                            if adaptive_operation_wait(maximum=0.20):
                                break
                            continue

                        page = detect_daily_task_state(image, threshold)
                        if emit_diagnostic:
                            self._log_for_device(target.device, f"每日流程心跳：页面识别为 {page.state.value}。")

                        carnival_close = (
                            match_daily_carnival_sale_close(image)
                            if page.state is DailyTaskState.UNKNOWN else None
                        )
                        if carnival_close is not None:
                            carnival_close_streak += 1
                            if carnival_close_streak >= 2 and not carnival_close_sent:
                                target.tap(*carnival_close)
                                carnival_close_sent = True
                                self._log_for_device(target.device, "已关闭双帧确认的狂欢大促弹窗；未触碰商品或领取按钮。")
                            continue
                        carnival_close_streak = 0
                        relocate_close = (
                            match_daily_relocate_prompt_close(image)
                            if page.state is DailyTaskState.UNKNOWN else None
                        )
                        if relocate_close is not None:
                            relocate_close_streak += 1
                            if relocate_close_streak >= 2 and not relocate_close_sent:
                                target.tap(*relocate_close)
                                relocate_close_sent = True
                                alliance_help_checked = True
                                startup_alliance_return_stage = 1
                                startup_alliance_return_streak = 0
                                self._log_for_device(target.device, "已关闭双帧确认的迁城提示；未点击迁城，跳过本轮联盟帮助。")
                            continue
                        relocate_close_streak = 0
                        deep_tech_close = (
                            match_daily_deep_tech_locked_close(image)
                            if page.state is DailyTaskState.UNKNOWN else None
                        )
                        if deep_tech_close is not None:
                            deep_tech_streak += 1
                            if deep_tech_streak >= 2 and not deep_tech_close_sent:
                                target.tap(*deep_tech_close)
                                deep_tech_close_sent = True
                                alliance_donation_unavailable = True
                                alliance_donation_retry_at = 0.0
                                alliance_donation_prerequisite_blocked = True
                                save_daily_donation_state()
                                self._log_for_device(target.device, "已关闭未解锁的前置科技，跳过本次联盟捐献。")
                            continue
                        deep_tech_streak = 0
                        prerequisite_go = (
                            match_daily_sustain_prerequisite_go(image)
                            if page.state is DailyTaskState.UNKNOWN else None
                        )
                        prerequisite_kind = "sustain"
                        if prerequisite_go is None and page.state is DailyTaskState.UNKNOWN:
                            prerequisite_go = match_daily_sustain_prerequisite_go(image, troop_life=True)
                            prerequisite_kind = "troop"
                        if prerequisite_go is not None:
                            sustain_prerequisite_streak = sustain_prerequisite_streak + 1 if sustain_prerequisite_kind == prerequisite_kind else 1
                            sustain_prerequisite_kind = prerequisite_kind
                            if sustain_prerequisite_streak >= 2 and prerequisite_kind not in sustain_prerequisite_sent:
                                target.tap(*prerequisite_go)
                                sustain_prerequisite_sent.add(prerequisite_kind)
                                self._log_for_device(target.device, "已从双帧确认的联盟永续前置条件进入科技详情；未点击捐献。")
                            continue
                        sustain_prerequisite_streak = 0

                        # A stopped Daily run may leave a verified Arena list
                        # or home open. Close only these exact reviewed pages;
                        # a new fight must start from a fresh Daily-card Go.
                        if page.state is DailyTaskState.UNKNOWN and not level_verified:
                            startup_result = match_arena_reviewed_victory_exit(image)
                            if startup_result and not startup_arena_result_closed:
                                startup_arena_result_streak += 1
                                if startup_arena_result_streak >= 2:
                                    target.tap(*startup_result)
                                    startup_arena_result_closed = True
                                    self._log_for_device(target.device, "启动恢复：退出双帧确认的竞技场排名胜利结果；未开始新挑战。")
                                continue
                            startup_arena_result_streak = 0
                            startup_list = match_arena_list_close(image, threshold)
                            if startup_list and not startup_arena_list_closed:
                                startup_arena_list_streak += 1
                                if startup_arena_list_streak >= 2:
                                    target.tap(*startup_list)
                                    startup_arena_list_closed = True
                                    self._log_for_device(target.device, "启动恢复：关闭双帧确认的竞技场挑战列表，未发起挑战。")
                                continue
                            startup_arena_list_streak = 0
                            startup_home = match_arena_home(image, threshold)
                            if startup_home and not startup_arena_home_closed:
                                startup_arena_home_streak += 1
                                if startup_arena_home_streak >= 2:
                                    target.shell(["input", "keyevent", "4"])
                                    startup_arena_home_closed = True
                                    self._log_for_device(target.device, "启动恢复：从双帧确认的竞技场首页返回主城。")
                                continue
                            startup_arena_home_streak = 0

                        if page.state not in (
                            DailyTaskState.UNKNOWN,
                            DailyTaskState.REWARD_RESULT_READY,
                        ):
                            abnormal_exit_kind = DailyAbnormalExitKind.UNKNOWN
                            abnormal_exit_point = None
                            abnormal_exit_streak = 0

                        # This recovery must also run before the castle-level
                        # preflight: a restarted controller has not yet set
                        # ``level_verified``, but it may inherit either an
                        # active ordinary march or its already-returned
                        # resource selector from an earlier safe run.
                        blocked_state = getattr(DailyTaskState, "BLOCKED", None)
                        if blocked_state is not None and page.state is blocked_state:
                            is_march_capacity_modal = any(
                                anchor == "march_capacity_modal" for anchor, _point in page.anchors
                            )
                            if is_march_capacity_modal and not march_capacity_back_sent:
                                march_capacity_back_streak += 1
                                set_state(
                                    f"启动恢复：确认行军队列已满扩容页（{march_capacity_back_streak}/2）；"
                                    "仅返回，不研究、激活或购买"
                                )
                                if march_capacity_back_streak >= 2:
                                    target.shell(["input", "keyevent", "4"])
                                    march_capacity_back_sent = True
                                    march_capacity_back_streak = 0
                                    transition_deadline = time.monotonic() + 8.0
                                    last_state = None
                                    self._log_for_device(
                                        target.device,
                                        "每日启动恢复：已从双帧确认的行军队列已满扩容页返回；"
                                        "未研究、未激活、未购买，准备被动确认现有采集队列。",
                                    )
                                continue
                            set_state("检测到付费或遮挡页面：不输入并停止")
                            self._log_for_device(target.device, "每日启动恢复检测到付费/遮挡页面；未执行输入。")
                            break
                        march_capacity_back_streak = 0

                        regular_activity_back_point, _regular_activity_score = (
                            match_daily_regular_activity_back(image, threshold)
                        )
                        if regular_activity_back_point is not None:
                            if regular_activity_back_sent:
                                set_state(
                                    "已从双帧确认的常规活动页点击一次专用返回；等待页面自然离开"
                                )
                                continue
                            regular_activity_back_streak += 1
                            set_state(
                                "确认自动弹出的常规活动页"
                                f"（{regular_activity_back_streak}/2）：仅允许该页左上返回"
                            )
                            if regular_activity_back_streak < 2:
                                continue
                            target.tap(*regular_activity_back_point)
                            regular_activity_back_sent = True
                            regular_activity_back_streak = 0
                            transition_deadline = time.monotonic() + 8.0
                            last_state = None
                            self._log_for_device(
                                target.device,
                                "每日异常恢复：双帧确认常规活动返回箭头与完整标题，"
                                f"仅点击左上返回 {regular_activity_back_point}；"
                                "未点击钻石刷新、加号、标签或活动卡。",
                            )
                            continue
                        regular_activity_back_streak = 0
                        if regular_activity_back_sent:
                            regular_activity_back_sent = False

                        active_march_visible = (
                            page.state is DailyTaskState.UNKNOWN
                            and daily_gather_march_is_active(image, threshold)
                        )
                        if active_march_visible:
                            if active_gather_kind is None:
                                inherited_gather_slot_active = True
                                inherited_gather_recheck_at = max(
                                    inherited_gather_recheck_at,
                                    time.monotonic() + DAILY_GATHER_FULL_NODE_MIN_RETURN_SECONDS,
                                )
                            set_state(
                                "检测到正在自然行军的队列：等待返回，不输入；"
                                "先继续不占行军队列的每日任务"
                            )
                            if daily_gather_selector_is_valid(image):
                                if not active_selector_back_sent:
                                    active_selector_recovery_streak += 1
                                    set_state(
                                        "确认正在行军的资源筛选页"
                                        f"（{active_selector_recovery_streak}/2）：仅关闭筛选器"
                                    )
                                    if active_selector_recovery_streak >= 2:
                                        target.shell(["input", "keyevent", "4"])
                                        active_selector_back_sent = True
                                        active_selector_recovery_streak = 0
                                        transition_deadline = time.monotonic() + 8.0
                                        last_state = None
                                        self._log_for_device(
                                            target.device,
                                            "每日启动恢复：已从双帧确认的行军中资源筛选页返回世界地图；"
                                            "未召回、未加速、未派新队，准备继续非行军每日项目。",
                                        )
                                continue
                            active_selector_recovery_streak = 0
                        if (
                            page.state is DailyTaskState.UNKNOWN
                            and not active_march_visible
                            and selector_recovery_back_attempts < 2
                        ):
                            if daily_gather_selector_is_valid(image):
                                selector_recovery_streak += 1
                                set_state(
                                    f"确认已返回的资源筛选页（{selector_recovery_streak}/2，"
                                    f"返回 {selector_recovery_back_attempts + 1}/2）"
                                )
                                if selector_recovery_streak >= 2:
                                    target.shell(["input", "keyevent", "4"])
                                    selector_recovery_back_attempts += 1
                                    selector_recovery_streak = 0
                                    transition_deadline = time.monotonic() + 8.0
                                    last_state = None
                                    self._log_for_device(
                                        target.device,
                                        "每日流程：已从双帧确认、无行军的资源筛选页发送受限返回 "
                                        f"({selector_recovery_back_attempts}/2)。",
                                    )
                                continue
                            selector_recovery_streak = 0

                        if page.state is DailyTaskState.UNKNOWN and not level_verified and not startup_training_back_sent:
                            normal_training_point, _normal_training_score = match_daily_training_normal_button(image, threshold)
                            active_training_point, _active_training_score = match_daily_training_active(image, threshold)
                            if normal_training_point and active_training_point:
                                startup_active_training_streak += 1
                                set_state(f"启动恢复：复核继承的自然训练队列（{startup_active_training_streak}/2）")
                                if startup_active_training_streak >= 2:
                                    active_image = record_active_training_countdown("继承的普通")
                                    if active_image is None:
                                        set_state("继承训练队列未能保存倒计时证据：不输入并停止")
                                        break
                                    back_point = daily_training_back_point(active_image)
                                    target.tap(*back_point)
                                    startup_training_back_sent = True
                                    startup_active_training_streak = 0
                                    recheck_at = time.monotonic() + 8 * 60.0
                                    for training_kind in (
                                        DailyMissionKind.TRAIN_SHIELD,
                                        DailyMissionKind.TRAIN_SPEAR,
                                        DailyMissionKind.TRAIN_ARCHER,
                                    ):
                                        deferred_auxiliary_training.add(training_kind)
                                        deferred_training_recheck_at[training_kind] = recheck_at
                                    transition_deadline = time.monotonic() + 8.0
                                    last_state = None
                                    self._log_for_device(
                                        target.device,
                                        f"每日启动恢复：已记录继承训练倒计时并从受证训练页返回兵营 {back_point}；"
                                        "不加速、不追加训练，继续独立每日事项。",
                                    )
                                continue
                            startup_active_training_streak = 0
                            if normal_training_point and not active_training_point:
                                startup_training_return_streak += 1
                                set_state(f"启动恢复：复核未开始的普通训练面板（{startup_training_return_streak}/2）")
                                if startup_training_return_streak >= 2:
                                    target.shell(["input", "keyevent", "4"])
                                    startup_training_back_sent = True
                                    startup_training_return_streak = 0
                                    transition_deadline = time.monotonic() + 8.0
                                    last_state = None
                                    self._log_for_device(
                                        target.device,
                                        "每日启动恢复：已从双帧确认、无训练队列的普通训练面板返回兵营场景。",
                                    )
                                continue
                            startup_training_return_streak = 0

                        if page.state is DailyTaskState.UNKNOWN and not level_verified and not startup_training_unlock_continue_sent:
                            unlock_point, _unlock_score = match_daily_training_unlock_continue(image, threshold)
                            if unlock_point and stable(unlock_point, startup_training_unlock_point):
                                startup_training_unlock_streak += 1
                            elif unlock_point:
                                startup_training_unlock_point = unlock_point
                                startup_training_unlock_streak = 1
                            else:
                                startup_training_unlock_point = None
                                startup_training_unlock_streak = 0
                            if unlock_point:
                                set_state(f"启动恢复：复核已验证训练解锁提示（{startup_training_unlock_streak}/2）")
                                if startup_training_unlock_streak >= 2:
                                    target.tap(*unlock_point)
                                    startup_training_unlock_continue_sent = True
                                    startup_training_unlock_point = None
                                    startup_training_unlock_streak = 0
                                    transition_deadline = time.monotonic() + 8.0
                                    last_state = None
                                    self._log_for_device(
                                        target.device,
                                        f"每日启动恢复：点击已双帧确认的训练解锁继续提示 {unlock_point}。",
                                    )
                                continue

                        if (
                            page.state is DailyTaskState.UNKNOWN
                            and not level_verified
                            and not startup_intel_map_back_sent
                        ):
                            intel_map, _intel_score = match_daily_intel_map_page(image, threshold)
                            startup_intel_map_streak = startup_intel_map_streak + 1 if intel_map else 0
                            if intel_map:
                                set_state(f"启动恢复：复核情报地图（{startup_intel_map_streak}/2）")
                                if startup_intel_map_streak >= 2:
                                    back_point = daily_intel_map_back_point(image)
                                    target.tap(*back_point)
                                    startup_intel_map_back_sent = True
                                    transition_deadline = time.monotonic() + 8.0
                                    last_state = None
                                    self._log_for_device(target.device, f"启动恢复：从双帧确认的情报地图返回 {back_point}，未点击线索。")
                                continue

                        if (
                            page.state is DailyTaskState.UNKNOWN
                            and not level_verified
                            and not startup_alliance_tech_back_sent
                        ):
                            battle_tabs, _battle_score = match_daily_alliance_tech_battle_tab_strip(
                                image, threshold
                            )
                            development_tabs, _development_score = (
                                match_daily_alliance_tech_development_tab_strip(image, threshold)
                            )
                            territory_tabs, _territory_score = (
                                match_daily_alliance_tech_territory_tab_strip(image, threshold)
                            )
                            tech_state = (
                                "战斗"
                                if battle_tabs
                                else "发展"
                                if development_tabs
                                else "领地"
                                if territory_tabs
                                else None
                            )
                            if tech_state and tech_state == startup_alliance_tech_state:
                                startup_alliance_tech_return_streak += 1
                            elif tech_state:
                                startup_alliance_tech_state = tech_state
                                startup_alliance_tech_return_streak = 1
                            else:
                                startup_alliance_tech_state = None
                                startup_alliance_tech_return_streak = 0
                            if tech_state:
                                set_state(
                                    "启动恢复：复核联盟科技"
                                    f"{tech_state}完整标签栏（{startup_alliance_tech_return_streak}/2）"
                                )
                                if startup_alliance_tech_return_streak >= 2:
                                    target.shell(["input", "keyevent", "4"])
                                    startup_alliance_tech_back_sent = True
                                    startup_alliance_tech_state = None
                                    startup_alliance_tech_return_streak = 0
                                    startup_alliance_return_stage = 1
                                    transition_deadline = time.monotonic() + 8.0
                                    last_state = None
                                    self._log_for_device(
                                        target.device,
                                        "每日启动恢复：已从双帧确认的联盟科技"
                                        f"{tech_state}页返回联盟主页；未点击任何科技节点。",
                                    )
                                continue

                        if (
                            page.state is DailyTaskState.UNKNOWN
                            and not level_verified
                            and not startup_hero_recruit_back_sent
                        ):
                            if daily_hero_recruit_page_is_visible(image, threshold):
                                startup_hero_recruit_return_streak += 1
                                set_state(
                                    "启动恢复：复核英雄招募页面"
                                    f"（{startup_hero_recruit_return_streak}/2）"
                                )
                                if startup_hero_recruit_return_streak >= 2:
                                    free_point, _free_score = match_daily_hero_free_recruit(
                                        image, threshold
                                    )
                                    back_point = daily_hero_recruit_back_point(image)
                                    target.tap(*back_point)
                                    startup_hero_recruit_back_sent = True
                                    startup_hero_recruit_return_streak = 0
                                    if not free_point:
                                        defer_hero_recruit()
                                    transition_deadline = time.monotonic() + 8.0
                                    last_state = None
                                    self._log_for_device(
                                        target.device,
                                        "每日启动恢复：已从双帧确认的英雄招募页返回主城；"
                                        + (
                                            "已记录本账号五分钟免费招募冷却并继续后续任务。"
                                            if not free_point
                                            else "未在无任务关联状态下点击免费招募。"
                                        ),
                                    )
                                continue
                            startup_hero_recruit_return_streak = 0

                        if (
                            page.state is DailyTaskState.UNKNOWN
                            and not level_verified
                            and not startup_alliance_donation_back_sent
                        ):
                            if daily_alliance_donation_page_is_visible(image, threshold):
                                startup_alliance_donation_return_streak += 1
                                set_state(
                                    "启动恢复：复核联盟捐献页面"
                                    f"（{startup_alliance_donation_return_streak}/2）"
                                )
                                if startup_alliance_donation_return_streak >= 2:
                                    active_food_point, _active_food_score = (
                                        match_daily_alliance_food_donation(image, threshold)
                                    )
                                    target.shell(["input", "keyevent", "4"])
                                    startup_alliance_donation_back_sent = True
                                    startup_alliance_donation_return_streak = 0
                                    if not active_food_point:
                                        alliance_donation_unavailable = True
                                        defer_daily_donation(
                                            DAILY_RETRY_LOCK_MAX_SECONDS
                                        )
                                    transition_deadline = time.monotonic() + 8.0
                                    last_state = None
                                    self._log_for_device(
                                        target.device,
                                        "每日启动恢复：已从双帧确认的联盟捐献页返回科技树；"
                                        + (
                                            "普通粮食捐献不可用，仅让行 10 秒；"
                                            if not active_food_point
                                            else "未在无任务关联状态下点击普通粮食捐献；"
                                        )
                                        + "黄色钻石捐献未触碰。",
                                    )
                                continue
                            startup_alliance_donation_return_streak = 0

                        # Do not leave a new --auto-daily launch stranded on
                        # the known empty Mutual Help page after a previous
                        # guarded run exhausted its navigation window.  These
                        # are neither generic close actions nor paid-card
                        # interactions: the first Back requires the exact
                        # Mutual Help header with no all-help control, and
                        # the second requires the exact Alliance Home page.
                        if page.state is DailyTaskState.UNKNOWN and not level_verified and startup_alliance_return_stage < 2:
                            alliance_page = detect_alliance_page(image, threshold)
                            if alliance_page.page is AlliancePage.ALL_HELP_READY and alliance_page.point:
                                if startup_alliance_help_clicks >= 25:
                                    if not startup_alliance_help_cap_back_sent:
                                        target.shell(["input", "keyevent", "4"])
                                        startup_alliance_help_cap_back_sent = True
                                        startup_alliance_return_stage = 1
                                        startup_alliance_help_point = None
                                        startup_alliance_help_streak = 0
                                        self._log_for_device(
                                            target.device,
                                            "每日启动恢复：联盟全部帮助达到25次上限，已从双帧确认互助页返回联盟主页以继续每日流程。",
                                        )
                                    continue
                                if stable(alliance_page.point, startup_alliance_help_point):
                                    startup_alliance_help_streak += 1
                                else:
                                    startup_alliance_help_point = alliance_page.point
                                    startup_alliance_help_streak = 1
                                set_state(f"启动恢复：复核联盟全部帮助（{startup_alliance_help_streak}/2）")
                                if startup_alliance_help_streak >= 2:
                                    target.tap(*alliance_page.point)
                                    startup_alliance_help_clicks += 1
                                    startup_alliance_help_point = None
                                    startup_alliance_help_streak = 0
                                    self.signals.clicks.emit(claims + startup_alliance_help_clicks)
                                    self._log_for_device(
                                        target.device,
                                        f"每日启动恢复：点击双帧确认的联盟全部帮助 {alliance_page.point}（{startup_alliance_help_clicks}/25）。",
                                    )
                                continue
                            if startup_alliance_return_stage == 0 and alliance_page.page is AlliancePage.ALLIANCE_HOME:
                                # The worker can also start on the exact home
                                # page, for example after a dismissed prompt.
                                # The existing two-frame gate below still owns
                                # the one permitted Back input.
                                startup_alliance_return_stage = 1
                                startup_alliance_return_streak = 0
                            expected_page = (
                                AlliancePage.MUTUAL_HELP
                                if startup_alliance_return_stage == 0
                                else AlliancePage.ALLIANCE_HOME
                            )
                            if alliance_page.page is expected_page:
                                startup_alliance_help_point = None
                                startup_alliance_help_streak = 0
                                startup_alliance_return_streak += 1
                                set_state(
                                    "启动恢复：复核联盟互助空页"
                                    if startup_alliance_return_stage == 0
                                    else "启动恢复：复核联盟主页"
                                )
                                if startup_alliance_return_streak >= 2:
                                    target.shell(["input", "keyevent", "4"])
                                    startup_alliance_return_stage += 1
                                    startup_alliance_return_streak = 0
                                    transition_deadline = time.monotonic() + 8.0
                                    last_state = None
                                    self._log_for_device(
                                        target.device,
                                        "每日启动恢复：已从双帧确认的联盟互助空页返回联盟主页。"
                                        if startup_alliance_return_stage == 1
                                        else "每日启动恢复：已从双帧确认的联盟主页返回主城。",
                                    )
                                continue
                            startup_alliance_return_streak = 0

                        # Every instance owns its own preflight.  The Lord
                        # Profile exposes the castle level without entering a
                        # task or spending anything.  Do not let the normal
                        # Daily Tasks state machine run until level >= 10 has
                        # been proved in two consecutive frames.
                        if not level_verified:
                            if profile_requested:
                                level_result = detect_castle_level_gate(image)
                                if level_result is profile_level_result and level_result is not CastleLevelGate.UNKNOWN:
                                    profile_level_streak += 1
                                elif level_result is not CastleLevelGate.UNKNOWN:
                                    profile_level_result = level_result
                                    profile_level_streak = 1
                                else:
                                    profile_level_streak = 0
                                set_state(f"正在读取城堡等级（{profile_level_streak}/2）")
                                if profile_level_streak >= 2:
                                    if profile_level_result is CastleLevelGate.BELOW_10:
                                        message = f"{target.device} 城堡等级低于 10 级，已跳过该实例。"
                                        set_state("等级过低：已跳过，不执行每日任务")
                                        self._log_for_device(target.device, message)
                                        self.signals.alert.emit(APP_NAME, message)
                                        break
                                    # System Back is intermittently ignored on
                                    # the Lord Profile.  The castle gate itself
                                    # has just been proved in two fresh frames,
                                    # so use that page's reviewed dedicated
                                    # upper-left arrow instead of a generic
                                    # recovery click.
                                    profile_back_point = map_content_point(
                                        (75, 75), (1440, 2560), image
                                    )
                                    target.tap(*profile_back_point)
                                    level_verified = True
                                    transition_deadline = (
                                        time.monotonic()
                                        + DAILY_PROFILE_RETURN_PASSIVE_CAP_SECONDS
                                    )
                                    last_state = None
                                    if mining_level_profile.mode == "manual":
                                        set_state(
                                            f"城堡等级已达到 10 级，继续执行（采矿固定 Lv.{resource_level}）"
                                        )
                                        self._log_for_device(
                                            target.device,
                                            f"城堡等级门槛已双帧确认：达到 10 级；本账号采矿固定 Lv.{resource_level}，不执行自动区域判定。",
                                        )
                                    else:
                                        set_state("城堡等级已达到 10 级，继续执行（采集前识别 5/7/9 资源带）")
                                        self._log_for_device(
                                            target.device,
                                            "城堡等级门槛已双帧确认：达到 10 级；每日采集前将按 Word 流程识别 5/7/9 资源带。",
                                        )
                                    if adaptive_operation_wait(maximum=0.50):
                                        break
                                    continue
                                if time.monotonic() >= profile_deadline:
                                    set_state("无法可靠读取城堡等级：已停止且未执行任务")
                                    self._log_for_device(target.device, "城堡等级读取超时；为避免低等级账号误运行，已停止。")
                                    break
                                if self.stop_event.wait(interval):
                                    break
                                continue

                            # A task sheet can be open on an unselected Daily
                            # tab when this worker starts.  Switch only the
                            # exact, independently recognised tab (including
                            # the reviewed Growth Tasks variant) so the normal
                            # verified-Daily-page close below can resume the
                            # city/profile preflight.  No task-list action is
                            # considered here.
                            if page.state is DailyTaskState.DAILY_TAB_READY:
                                if daily_tab_tapped and time.monotonic() < transition_deadline:
                                    set_state("等级预检：等待已点击的每日标签切换，不重复输入")
                                    continue
                                if daily_tab_tapped or not page.point:
                                    set_state("等级预检中的每日任务标签未按预期切换：不再输入")
                                    self._log_for_device(target.device, "等级预检发现每日任务标签已尝试切换或坐标缺失；未重复点击。")
                                    break
                                streak = observe(page.state, page.point)
                                set_state(f"等级预检前确认每日任务标签入口（{streak}/2）")
                                if streak >= 2:
                                    target.tap(*page.point)
                                    daily_tab_tapped = True
                                    transition_deadline = time.monotonic() + 8.0
                                    last_state = None
                                    self._log_for_device(target.device, f"等级预检：点击已双帧确认的每日任务标签 {page.point}。")
                                continue

                            # The documented entry point is often the Daily
                            # Tasks sheet itself.  Before the level preflight
                            # can open the Lord Profile, close only this
                            # already-verified sheet.  This is deliberately
                            # narrower than a generic Back/close action.
                            if page.state in (
                                DailyTaskState.DAILY_PAGE,
                                DailyTaskState.DAILY_LOGIN_COMPLETED,
                                DailyTaskState.CLAIM_READY,
                                DailyTaskState.TASK_CLAIM_READY,
                            ):
                                if preflight_daily_close_sent:
                                    if time.monotonic() >= transition_deadline:
                                        set_state("每日页关闭后未确认主城：未继续输入")
                                        self._log_for_device(
                                            target.device,
                                            "等级预检关闭每日任务页后未确认主城；未执行额外输入。",
                                        )
                                        break
                                    set_state("等待已验证的每日任务页关闭")
                                    if self.stop_event.wait(interval):
                                        break
                                    continue
                                close_point = daily_task_close_point(image)
                                streak = observe(page.state, close_point)
                                set_state(f"等级预检前确认每日任务页关闭按钮（{streak}/2）")
                                if streak >= 2:
                                    target.tap(*close_point)
                                    preflight_daily_close_sent = True
                                    # This tab switch belonged solely to the
                                    # level preflight.  The later normal flow
                                    # may legitimately return to the Growth
                                    # Tasks sheet and must be able to prove and
                                    # switch its Daily tab once for itself.
                                    daily_tab_tapped = False
                                    transition_deadline = time.monotonic() + 8.0
                                    last_state = None
                                    self._log_for_device(
                                        target.device,
                                        f"等级预检：已关闭双帧确认的每日任务页 {close_point}，准备读取城堡等级。",
                                    )
                                continue

                            if page.state is DailyTaskState.UNKNOWN and not world_town_tapped:
                                world_town_point, _world_town_score = match_reviewed_world_town_entry(image)
                                if world_town_point:
                                    streak = observe(DailyTaskState.CITY_ENTRY, world_town_point)
                                    set_state(f"等级检查前确认世界地图城镇入口（{streak}/2）")
                                    if streak >= 2:
                                        target.tap(*world_town_point)
                                        world_town_tapped = True
                                        transition_deadline = time.monotonic() + 8.0
                                        last_state = None
                                    continue

                            if page.state is DailyTaskState.CITY_ENTRY:
                                city_point, _ = match_daily_city_entry(image, threshold)
                                streak = observe(page.state, city_point)
                                set_state(f"等级检查前确认主城（{streak}/2）")
                                if streak >= 2 and city_point:
                                    avatar_point = map_content_point((82, 82), (1440, 2560), image)
                                    target.tap(*avatar_point)
                                    profile_requested = True
                                    profile_deadline = time.monotonic() + AUTOMATION_STEP_TIMEOUT_SECONDS
                                    profile_level_streak = 0
                                    profile_level_result = CastleLevelGate.UNKNOWN
                                    last_state = None
                                    self._log_for_device(target.device, "已从双帧确认的主城打开领主档案，准备读取城堡等级。")
                                continue

                            set_state("等待可验证的主城画面以检查城堡等级")
                            if self.stop_event.wait(interval):
                                break
                            continue

                        blocked_state = getattr(DailyTaskState, "BLOCKED", None)
                        if blocked_state is not None and page.state is blocked_state:
                            is_march_capacity_modal = any(
                                anchor == "march_capacity_modal" for anchor, _point in page.anchors
                            )
                            if is_march_capacity_modal and not march_capacity_back_sent:
                                march_capacity_back_streak += 1
                                set_state(
                                    f"确认行军队列已满扩容页（{march_capacity_back_streak}/2）："
                                    "仅返回，不研究、激活或购买"
                                )
                                if march_capacity_back_streak >= 2:
                                    target.shell(["input", "keyevent", "4"])
                                    march_capacity_back_sent = True
                                    march_capacity_back_streak = 0
                                    transition_deadline = time.monotonic() + 8.0
                                    last_state = None
                                    self._log_for_device(
                                        target.device,
                                        "每日流程：已从双帧确认的行军队列已满扩容页返回；"
                                        "未研究、未激活、未购买，准备被动确认现有采集队列。",
                                    )
                                continue
                            set_state("检测到付费或遮挡页面：不输入并停止")
                            self._log_for_device(target.device, "每日奖励流程检测到付费/遮挡页面；未执行输入。")
                            break
                        march_capacity_back_streak = 0

                        # If an ordinary resource march was already active
                        # when this daily flow started, leave it completely
                        # untouched. The same passive one-slot panel blocks
                        # every new gather dispatch, but does not block the
                        # reviewed return-to-town path or independent Daily
                        # Tasks such as claims, alliance help, and training.
                        active_march_visible = (
                            page.state is DailyTaskState.UNKNOWN
                            and daily_gather_march_is_active(image, threshold)
                        )
                        if active_march_visible:
                            if active_gather_kind is None:
                                inherited_gather_slot_active = True
                                inherited_gather_recheck_at = max(
                                    inherited_gather_recheck_at,
                                    time.monotonic() + DAILY_GATHER_FULL_NODE_MIN_RETURN_SECONDS,
                                )
                            set_state(
                                "检测到正在自然行军的队列：等待返回，不输入；"
                                "先继续不占行军队列的每日任务"
                            )
                            if daily_gather_selector_is_valid(image):
                                if not active_selector_back_sent:
                                    active_selector_recovery_streak += 1
                                    set_state(
                                        "确认正在行军的资源筛选页"
                                        f"（{active_selector_recovery_streak}/2）：仅关闭筛选器"
                                    )
                                    if active_selector_recovery_streak >= 2:
                                        target.shell(["input", "keyevent", "4"])
                                        active_selector_back_sent = True
                                        active_selector_recovery_streak = 0
                                        transition_deadline = time.monotonic() + 8.0
                                        last_state = None
                                        self._log_for_device(
                                            target.device,
                                            "每日流程：已从双帧确认的行军中资源筛选页返回世界地图；"
                                            "未召回、未加速、未派新队，准备继续非行军每日项目。",
                                        )
                                continue
                            active_selector_recovery_streak = 0

                        # A previous safe run can stop while the ordinary
                        # resource selector is still open after a march has
                        # naturally returned.  Do not search, choose a node,
                        # or touch the + queue control from that stale page.
                        # Two selector frames with no active one-slot panel
                        # authorize exactly one Android Back to the world map;
                        # normal city-entry proof still gates every later tap.
                        if (
                            page.state is DailyTaskState.UNKNOWN
                            and not active_march_visible
                            and selector_recovery_back_attempts < 2
                        ):
                            if daily_gather_selector_is_valid(image):
                                selector_recovery_streak += 1
                                set_state(
                                    f"确认已返回的资源筛选页（{selector_recovery_streak}/2，"
                                    f"返回 {selector_recovery_back_attempts + 1}/2）"
                                )
                                if selector_recovery_streak >= 2:
                                    target.shell(["input", "keyevent", "4"])
                                    selector_recovery_back_attempts += 1
                                    selector_recovery_streak = 0
                                    transition_deadline = time.monotonic() + 8.0
                                    last_state = None
                                    self._log_for_device(
                                        target.device,
                                        "每日流程：已从双帧确认、无行军的资源筛选页发送受限返回 "
                                        f"({selector_recovery_back_attempts}/2)。",
                                    )
                                continue
                            selector_recovery_streak = 0

                        # A resource route can naturally return to the world
                        # map before a later --auto-daily launch.  The Town
                        # control is accepted only when paired with the
                        # lower-left world-search lens, in two frames, and at
                        # most once before the ordinary city Daily-Tasks entry
                        # flow resumes.  It never serves as a generic close.
                        if page.state is DailyTaskState.UNKNOWN and not world_town_tapped:
                            world_town_point, _world_town_score = match_reviewed_world_town_entry(image)
                            if world_town_point:
                                streak = observe(DailyTaskState.CITY_ENTRY, world_town_point)
                                set_state(f"确认世界地图城镇入口（{streak}/2）")
                                if streak >= 2:
                                    target.tap(*world_town_point)
                                    world_town_tapped = True
                                    transition_deadline = time.monotonic() + 8.0
                                    last_state = None
                                    self._log_for_device(
                                        target.device,
                                        f"每日流程：从已双帧确认的世界地图返回城镇 {world_town_point}。",
                                    )
                                continue

                        city_point: tuple[int, int] | None = None
                        if not city_entry_tapped and page.state is DailyTaskState.CITY_ENTRY:
                            city_point, _ = match_daily_city_entry(image, threshold)
                        point = city_point if page.state is DailyTaskState.CITY_ENTRY else page.point
                        streak = observe(page.state, point)

                        if page.state is DailyTaskState.REWARD_RESULT_READY:
                            abnormal = diagnose_daily_abnormal_exit(image, threshold)
                            abnormal_streak = observe_abnormal_exit(
                                abnormal.kind,
                                abnormal.point,
                            )
                            if abnormal.kind is not DailyAbnormalExitKind.REWARD_TAP_ANYWHERE:
                                set_state("奖励页未识别到完整的任意位置退出文字：不输入并停止")
                                self._log_for_device(
                                    target.device,
                                    "奖励结算标题可见，但未识别到完整的‘点击任意位置退出’文字；未把它猜成返回或X，已停止。",
                                )
                                break
                            if claim_result_exit_count >= claim_result_exit_cap:
                                set_state("同一次领取的连续奖励页已达到安全上限：不再输入")
                                self._log_for_device(
                                    target.device,
                                    f"同一次领取已退出 {claim_result_exit_count} 层奖励页，达到上限；未继续点击。",
                                )
                                break
                            set_state(
                                f"双图OCR确认奖励页显示点击任意位置退出（{abnormal_streak}/2）"
                            )
                            if abnormal_streak >= 2 and abnormal.point is not None:
                                exit_point = abnormal.point
                                target.tap(*exit_point)
                                claim_result_exit_count += 1
                                pending_claim = False
                                pending_claim_deadline = 0.0
                                pending_claim_point = None
                                pending_claim_settle_streak = 0
                                pending_claim_settle_point = None
                                recent_claim_result_deadline = time.monotonic() + 12.0
                                abnormal_exit_kind = DailyAbnormalExitKind.UNKNOWN
                                abnormal_exit_point = None
                                abnormal_exit_streak = 0
                                last_state = None
                                self._log_for_device(
                                    target.device,
                                    f"已按双图文字识别点击侧边空白退出奖励页 {exit_point} "
                                    f"（{claim_result_exit_count}/{claim_result_exit_cap}）；"
                                    "保留12秒只用于同一次领取的连续奖励页。",
                                )
                            continue

                        if page.state is DailyTaskState.CHEST_RESULT_READY:
                            # Exactly as with task rewards, a chest-contents
                            # sheet has no standalone dismissal authority.  A
                            # chest milestone must have been tapped by this
                            # worker immediately beforehand.
                            if pending_chest is None:
                                set_state("检测到未关联的宝箱内容页：不输入并停止")
                                self._log_for_device(
                                    target.device,
                                    "每日奖励收取看到了未关联的活跃度宝箱内容页；没有点击，已停止。",
                                )
                                break
                            set_state(f"确认 {pending_chest} 活跃度宝箱内容（{streak}/2）")
                            if streak >= 2:
                                exit_point = daily_chest_result_exit_point(image)
                                target.tap(*exit_point)
                                attempted_chests.add(pending_chest)
                                self._log_for_device(
                                    target.device,
                                    f"已退出 {pending_chest} 活跃度宝箱内容页 {exit_point}。",
                                )
                                pending_chest = None
                                last_state = None
                            continue

                        if page.state is DailyTaskState.DAILY_TAB_READY:
                            # The exact Chapter title plus the unselected
                            # Daily Tasks tab is the only permitted tab
                            # switch.  It is never a generic bottom-tab tap.
                            if daily_tab_tapped and time.monotonic() < transition_deadline:
                                set_state("等待已点击的每日标签切换，不重复输入")
                                continue
                            if daily_tab_tapped or not page.point:
                                set_state("每日任务标签未按预期切换：不再输入")
                                self._log_for_device(target.device, "每日任务标签已尝试切换或坐标缺失；未重复点击。")
                                break
                            set_state(f"确认每日任务标签入口（{streak}/2）")
                            if streak >= 2:
                                target.tap(*page.point)
                                daily_tab_tapped = True
                                transition_deadline = time.monotonic() + 8.0
                                last_state = None
                                self._log_for_device(target.device, f"点击已确认的每日任务标签 {page.point}。")
                            continue

                        if page.state is DailyTaskState.UNKNOWN:
                            abnormal = diagnose_daily_abnormal_exit(image, threshold)
                            abnormal_streak = observe_abnormal_exit(
                                abnormal.kind,
                                abnormal.point,
                            )

                            if abnormal.kind is DailyAbnormalExitKind.NETWORK_WAIT:
                                set_state("网络异常页：不输入，等待恢复后重新识图")
                                continue
                            if abnormal.kind is DailyAbnormalExitKind.PAID_STOP:
                                set_state("检测到付费危险页：不输入并停止")
                                self._log_for_device(
                                    target.device,
                                    "异常分类器识别为付费页；未执行返回、X或任意位置点击，已停止。",
                                )
                                break

                            if abnormal.kind is DailyAbnormalExitKind.REWARD_TAP_ANYWHERE:
                                if claim_result_exit_count >= claim_result_exit_cap:
                                    set_state("连续奖励页达到安全上限：不再输入")
                                    break
                                set_state(
                                    f"双图OCR确认异常页显示点击任意位置退出（{abnormal_streak}/2）"
                                )
                                if abnormal_streak >= 2 and abnormal.point is not None:
                                    target.tap(*abnormal.point)
                                    claim_result_exit_count += 1
                                    pending_claim = False
                                    pending_claim_deadline = 0.0
                                    pending_claim_point = None
                                    pending_claim_settle_streak = 0
                                    pending_claim_settle_point = None
                                    recent_claim_result_deadline = time.monotonic() + 12.0
                                    self._log_for_device(
                                        target.device,
                                        f"异常页完整退出文字已确认；已点击侧边空白点 {abnormal.point} "
                                        f"（{claim_result_exit_count}/{claim_result_exit_cap}）。",
                                    )
                                    abnormal_exit_kind = DailyAbnormalExitKind.UNKNOWN
                                    abnormal_exit_point = None
                                    abnormal_exit_streak = 0
                                    last_state = None
                                continue

                            # A verified claim animation remains passive while
                            # waiting for either the classified result or a
                            # recognisable Daily page.
                            if pending_claim and time.monotonic() < pending_claim_deadline:
                                set_state("等待关联奖励页或已知每日页稳定显示")
                                continue
                            if time.monotonic() < recent_claim_result_deadline:
                                set_state("同链连续奖励页正在转场：保持被动多图分类")
                                continue

                            # Page-specific X/Back/Town controls are allowed
                            # only inside an exact route transition and after
                            # two equal classifications.  UNKNOWN has no
                            # fallback input at all.
                            classified_route_exits = {
                                DailyAbnormalExitKind.DAILY_CLOSE_X: "X关闭",
                                DailyAbnormalExitKind.INTEL_MAP_BACK: "情报页返回",
                                DailyAbnormalExitKind.WORLD_TOWN: "世界地图回城",
                            }
                            if (
                                (
                                    time.monotonic() < transition_deadline
                                    or (
                                        abnormal.kind
                                        is DailyAbnormalExitKind.WORLD_TOWN
                                        and world_town_returns < 3
                                    )
                                )
                                and abnormal.kind in classified_route_exits
                                and abnormal.point is not None
                            ):
                                set_state(
                                    f"双图确认异常页应执行{classified_route_exits[abnormal.kind]}"
                                    f"（{abnormal_streak}/2）"
                                )
                                if abnormal_streak >= 2:
                                    target.tap(*abnormal.point)
                                    if (
                                        abnormal.kind
                                        is DailyAbnormalExitKind.WORLD_TOWN
                                    ):
                                        world_town_returns += 1
                                    self._log_for_device(
                                        target.device,
                                        f"异常分类为 {abnormal.kind.value}；只点击其专用坐标 "
                                        f"{abnormal.point}，随后重新识图。",
                                    )
                                    abnormal_exit_kind = DailyAbnormalExitKind.UNKNOWN
                                    abnormal_exit_point = None
                                    abnormal_exit_streak = 0
                                    transition_deadline = time.monotonic() + 6.0
                                    last_state = None
                                continue

                            if time.monotonic() < transition_deadline:
                                set_state("异常转场尚未分类：保持被动识图，不盲目返回或点击")
                                continue
                            set_state("检测到未知页面或弹窗：不输入并停止")
                            self._log_for_device(
                                target.device,
                                "异常页未能归类为任意位置退出、专用返回、专用X、网络或付费页；"
                                "未执行通用返回、左上角或页面中心点击。",
                            )
                            break

                        if page.state is DailyTaskState.CITY_ENTRY:
                            if city_entry_tapped and time.monotonic() < transition_deadline:
                                # A reviewed task-strip tap can need more than
                                # one immediate ADB frame to replace the city.
                                # Stay passive inside the already-bounded
                                # transition window; never send a second tap.
                                set_state(
                                    "已点击主城任务入口；被动等待任务页转场，不重复输入"
                                )
                                continue
                            if city_entry_tapped or not city_point:
                                set_state("主城任务入口未按预期切换：不再输入")
                                self._log_for_device(target.device, "主城任务入口未按预期切换；未重复点击。")
                                break
                            set_state(f"确认主城每日任务入口（{streak}/2）")
                            if streak >= 2:
                                if not expedition_attempted and expedition_ledger and expedition_ledger.available():
                                    expedition_attempted = True
                                    def expedition_reward_exit(frame: Image.Image) -> tuple[int, int] | None:
                                        result = diagnose_daily_abnormal_exit(frame, threshold)
                                        return result.point if result.kind is DailyAbnormalExitKind.REWARD_TAP_ANYWHERE else None
                                    outcome = run_expedition_claim(
                                        lambda: target.screenshot(timeout=2),
                                        lambda x, y: target.shell(["input", "tap", str(x), str(y)], timeout=2),
                                        self.stop_event.is_set, self.stop_event.wait,
                                        lambda frame: match_daily_city_entry(frame, threshold)[0] is not None,
                                        expedition_reward_exit, expedition_ledger.reserve, expedition_ledger.confirm,
                                        lambda message: self._log_for_device(target.device, message),
                                    )
                                    if outcome != "claimed":
                                        set_state("探险收益状态未完整确认，已停止且未重复输入")
                                        break
                                    last_state = None
                                    continue
                                target.tap(*city_point)
                                city_entry_tapped = True
                                transition_deadline = time.monotonic() + 8.0
                                last_state = None
                                self._log_for_device(target.device, f"点击已确认的每日任务入口 {city_point}。")
                            continue

                        actionable = (DailyTaskState.CLAIM_READY, DailyTaskState.TASK_CLAIM_READY)
                        if page.state in actionable:
                            # A one-key or row claim is authorized only once.
                            # While its immediately-correlated settlement is
                            # pending, a still-visible button is observational
                            # evidence, never authority for another click.
                            if pending_claim:
                                ocr_result = read_daily_activity_score(image)
                                if ocr_result is None:
                                    current_activity_points = 0.0
                                    current_activity_confidence = 0.0
                                else:
                                    current_activity_points = float(ocr_result[0])
                                    current_activity_confidence = ocr_result[1]
                                claim_point_moved = bool(
                                    page.point
                                    and pending_claim_point
                                    and not stable(page.point, pending_claim_point)
                                )
                                activity_increased = bool(
                                    current_activity_confidence >= 0.40
                                    and pending_claim_activity_confidence >= 0.40
                                    and current_activity_points
                                    >= pending_claim_activity_before + 3.0
                                )
                                if claim_point_moved or activity_increased:
                                    if stable(page.point, pending_claim_settle_point):
                                        pending_claim_settle_streak += 1
                                    else:
                                        pending_claim_settle_point = page.point
                                        pending_claim_settle_streak = 1
                                    set_state(
                                        "领取已变化，极速复核下一领取按钮"
                                        f"（{pending_claim_settle_streak}/2）"
                                    )
                                    if pending_claim_settle_streak >= 2:
                                        pending_claim = False
                                        pending_claim_deadline = 0.0
                                        pending_claim_point = None
                                        pending_claim_settle_streak = 0
                                        pending_claim_settle_point = None
                                        recent_claim_result_deadline = time.monotonic() + 12.0
                                        last_state = None
                                        self._log_for_device(
                                            target.device,
                                            "前一项领取已由连续两帧任务位移/活跃度变化确认结算；"
                                            "立即继续排空领取，不复位列表、不进入任务前往。",
                                        )
                                    continue
                                pending_claim_settle_streak = 0
                                pending_claim_settle_point = None
                                if time.monotonic() < pending_claim_deadline:
                                    set_state("极速等待前一领取产生可验证变化；不重复点击")
                                    continue
                                set_state("领取按钮仍显示且结算未确认：不重复点击并停止")
                                self._log_for_device(
                                    target.device,
                                    "每日领取结算超时后按钮仍可见；未重复点击，已安全停止。",
                                )
                                break
                            if not page.point:
                                set_state("领取坐标未复核：不输入并停止")
                                break
                            authorized_claim_point = page.point
                            arena_claim = match_daily_arena_claim(image, threshold)
                            if (
                                arena_claim is not None
                                and stable(arena_claim.claim_point, page.point)
                            ):
                                authorized_claim_point = arena_claim.claim_point
                                set_state(
                                    f"确认竞技场{arena_claim.target_count}次档精确领取"
                                    f"（{streak}/2）"
                                )
                            set_state(f"确认每日奖励领取按钮（{streak}/2）")
                            if streak >= 2:
                                before_ocr = read_daily_activity_score(image)
                                if before_ocr is None:
                                    before_activity_points = 0.0
                                    before_activity_confidence = 0.0
                                else:
                                    before_activity_points = float(before_ocr[0])
                                    before_activity_confidence = before_ocr[1]
                                target.tap(*authorized_claim_point)
                                claims += 1
                                pending_claim = True
                                pending_claim_deadline = time.monotonic() + 8.0
                                pending_claim_point = authorized_claim_point
                                pending_claim_activity_before = before_activity_points
                                pending_claim_activity_confidence = before_activity_confidence
                                pending_claim_settle_streak = 0
                                pending_claim_settle_point = None
                                recent_claim_result_deadline = 0.0
                                claim_result_exit_count = 0
                                abnormal_exit_kind = DailyAbnormalExitKind.UNKNOWN
                                abnormal_exit_point = None
                                abnormal_exit_streak = 0
                                last_state = None
                                self.signals.clicks.emit(claims)
                                self._log_for_device(
                                    target.device,
                                    f"点击已验证的每日领取按钮 {authorized_claim_point}"
                                    f"（累计 {claims} 次）；达到325后仍允许排空当前已完成奖励，"
                                    "但不会为未完成项新增操作。",
                                )
                            continue

                        if page.state in (DailyTaskState.DAILY_PAGE, DailyTaskState.DAILY_LOGIN_COMPLETED):
                            if pending_claim:
                                # No verified claim button in two fresh Daily
                                # frames is a direct postcondition that the
                                # clicked row disappeared.  Accept it
                                # immediately instead of waiting for the
                                # deadline; only then may the normal task scan
                                # resume.
                                if stable(page.point, pending_claim_settle_point):
                                    pending_claim_settle_streak += 1
                                else:
                                    pending_claim_settle_point = page.point
                                    pending_claim_settle_streak = 1
                                if pending_claim_settle_streak >= 2:
                                    pending_claim = False
                                    pending_claim_deadline = 0.0
                                    pending_claim_point = None
                                    pending_claim_settle_streak = 0
                                    pending_claim_settle_point = None
                                    recent_claim_result_deadline = time.monotonic() + 12.0
                                    last_state = None
                                    self._log_for_device(
                                        target.device,
                                        "任务领取未出现结算页，但已连续两帧确认领取按钮消失；"
                                        "立即继续排空领取，完成后才扫描任务。",
                                    )
                                    set_state("领取已快速结算，立即检查下一项领取")
                                    continue
                                if time.monotonic() >= pending_claim_deadline:
                                    set_state("领取结算未在限时内双帧确认：不输入并停止")
                                    self._log_for_device(
                                        target.device,
                                        "每日领取未在8秒内双帧确认按钮消失或奖励页；"
                                        "未重复点击，已安全停止。",
                                    )
                                    break
                                set_state(
                                    "极速复核领取按钮已消失"
                                    f"（{pending_claim_settle_streak}/2）"
                                )
                                continue
                            if pending_chest is not None:
                                # A chest may have been collected earlier in
                                # the day.  It then stays visually open but
                                # does not always show its contents panel.  A
                                # second plain Daily-page observation ends
                                # this one bounded attempt without another tap.
                                if streak >= 2:
                                    attempted_chests.add(pending_chest)
                                    self._log_for_device(
                                        target.device,
                                        f"{pending_chest} 活跃度宝箱点击后未出现内容页；本轮不再重复点击。",
                                    )
                                    pending_chest = None
                                    last_state = None
                                else:
                                    set_state(f"复核 {pending_chest} 活跃度宝箱点击结果（1/2）")
                                continue
                            activity_ocr = read_daily_activity_score(image)
                            if activity_ocr is None:
                                activity_points = 0.0
                                activity_confidence = 0.0
                            else:
                                activity_points = float(activity_ocr[0])
                                activity_confidence = activity_ocr[1]
                            # Check if target reached: score >= 325 with high confidence
                            if (
                                activity_confidence >= 0.70
                                and activity_points >= 325.0
                            ):
                                activity_goal_streak += 1
                                if activity_goal_streak >= 2:
                                    activity_goal_confirmed = True
                            else:
                                activity_goal_streak = 0

                            # A single full-bar frame freezes new task routes
                            # while the second frame is checked.  Once confirmed,
                            # 325 is a minimum target rather than a reward ceiling:
                            # completed claims and reached chests may still drain,
                            # but no Go/training/gather/donation/build route may
                            # begin.  The claim-only list scan below starts from a
                            # freshly proven top boundary.
                            if activity_goal_streak and not activity_goal_confirmed:
                                set_state(
                                    f"复核每日活跃度满格 325/325（{activity_goal_streak}/2）；暂不执行新任务"
                                )
                                if self.stop_event.wait(interval):
                                    break
                                continue
                            if activity_goal_confirmed:
                                if not activity_goal_claim_scan_started:
                                    activity_goal_claim_scan_started = True
                                    daily_completed_zone_wait_after_top = False
                                    restart_daily_list_scan()
                                    last_state = None
                                if not activity_goal_claim_drain_announced:
                                    activity_goal_claim_drain_announced = True
                                    self._log_for_device(
                                        target.device,
                                        "每日活跃度已连续两帧可靠确认达到至少 325；"
                                        "停止全部新增进度路线，改为从列表顶部只排空当前已完成奖励，"
                                        "允许最终活跃度超过 325。",
                                    )
                                set_state("已达到至少325：仅排空已完成奖励，不执行任何前往")
                            elif not alliance_help_checked:
                                alliance_help_checked = True
                                set_state("每日流程：检查联盟全部帮助")
                                if not run_alliance_help_cycle(image):
                                    set_state("联盟帮助步骤未完整确认，已停止且未作恢复输入")
                                    break
                                city_entry_tapped = True
                                # The helper has just tapped the verified
                                # city entry itself.  Treat the following
                                # task-sheet animation exactly like a direct
                                # city-entry tap; it can otherwise produce a
                                # single unknown frame before the daily page
                                # is fully rendered.
                                # One live high-level transition settled just
                                # after the old eight-second boundary.  This
                                # remains an absolute passive deadline, never
                                # one long sleep or authority for a new input.
                                transition_deadline = time.monotonic() + 16.0
                                daily_tab_tapped = False
                                restart_daily_list_scan()
                                last_state = None
                                continue
                            # The bar estimator has a 1--2 point rendering
                            # tolerance at a milestone edge.  It is never used
                            # outside the fully verified Daily-page state.
                            open_chest_pending = False
                            for milestone in sorted(daily_activity_chest_points(image)):
                                if milestone in attempted_chests:
                                    continue
                                if activity_confidence < 0.40 or activity_points + 2.0 < milestone:
                                    open_chest_streaks[milestone] = 0
                                    continue
                                chest_open, _open_score = match_daily_activity_chest_open(image, milestone)
                                if not chest_open:
                                    open_chest_streaks[milestone] = 0
                                    continue
                                open_chest_streaks[milestone] = open_chest_streaks.get(milestone, 0) + 1
                                if open_chest_streaks[milestone] < 2:
                                    open_chest_pending = True
                                    continue
                                attempted_chests.add(milestone)
                                self._log_for_device(
                                    target.device,
                                    f"{milestone} 活跃度宝箱已双帧识图为打开状态；跳过重复打开内容页。",
                                )
                            if open_chest_pending:
                                set_state("复核已打开的活跃度宝箱；暂不点击")
                                continue

                            reachable = [
                                milestone
                                for milestone in sorted(daily_activity_chest_points(image))
                                if milestone not in attempted_chests
                                and activity_confidence >= 0.40
                                and activity_points + 2.0 >= milestone
                            ]
                            if reachable:
                                milestone = reachable[0]
                                point = daily_activity_chest_points(image)[milestone]
                                set_state(
                                    f"确认活跃度约 {activity_points:.0f}，准备收取 {milestone} 宝箱（{streak}/2）"
                                )
                                if streak >= 2:
                                    target.tap(*point)
                                    pending_chest = milestone
                                    last_state = None
                                    self._log_for_device(
                                        target.device,
                                        f"点击已达到的 {milestone} 活跃度宝箱 {point}（估算 {activity_points:.1f}）。",
                                    )
                                continue

                            if daily_list_reset_pending:
                                # The old fixed four-swipe reset silently
                                # failed because x=720 was not scrollable in
                                # the live client.  Every gesture now starts
                                # in the empirically verified x=900 lane and
                                # its result is measured before another input.
                                if daily_list_reset_before_image is not None:
                                    movement = daily_task_list_viewport_mean_change(
                                        daily_list_reset_before_image, image
                                    )
                                    daily_list_reset_before_image = None
                                    if movement <= DAILY_TASK_LIST_BOUNDARY_MAX_MEAN_CHANGE:
                                        daily_list_reset_boundary_streak += 1
                                    else:
                                        daily_list_reset_boundary_streak = 0
                                    self._log_for_device(
                                        target.device,
                                        "每日任务顶部复位滑动后的列表平均变化为 "
                                        f"{movement:.3f}；静止确认 "
                                        f"{daily_list_reset_boundary_streak}/"
                                        f"{DAILY_TASK_LIST_BOUNDARY_CONFIRMATIONS}。",
                                    )
                                    if (
                                        daily_list_reset_boundary_streak
                                        >= DAILY_TASK_LIST_BOUNDARY_CONFIRMATIONS
                                    ):
                                        daily_list_reset_pending = False
                                        daily_scrolls = 0
                                        daily_list_scan_before_image = None
                                        daily_list_bottom_boundary_streak = 0
                                        last_state = None
                                        if daily_completed_zone_wait_after_top:
                                            daily_completed_zone_wait_after_top = False
                                            (
                                                idle_wait_seconds,
                                                idle_no_input_label,
                                                _refresh_visible,
                                                _estimated,
                                            ) = daily_idle_wait_plan(image, 0.0, 0.0)
                                            idle_no_input_until = (
                                                time.monotonic() + idle_wait_seconds
                                            )
                                            set_state(
                                                "已确认回到任务顶部；"
                                                f"{idle_no_input_label}后重新领取并检查"
                                            )
                                            self._log_for_device(
                                                target.device,
                                                "绿色打勾区以下已全部跳过；列表已双确认回到顶部，"
                                                f"保持零输入到{idle_no_input_label}边界后再领取并检查。",
                                            )
                                            continue
                                        set_state("已用画面位移双重确认列表顶部，开始从首项扫描")
                                        self._log_for_device(
                                            target.device,
                                            "每日任务列表顶部已由连续两次无位移滑动确认；本轮从首项重新扫描。",
                                        )
                                        continue
                                if daily_list_reset_swipes >= DAILY_TASK_LIST_FAST_TOP_MAX_GESTURES:
                                    set_state("高速回顶未在限次内确认每日任务列表顶部：不输入并停止")
                                    self._log_for_device(
                                        target.device,
                                        "每日任务高速回顶已达到十二次逐帧比对安全上限，"
                                        "但没有连续两次静止证据；"
                                        "未把当前位置当作顶部，已停止。",
                                    )
                                    break
                                if streak >= 2:
                                    if not send_daily_fast_top_gesture(image):
                                        set_state("高速回顶手势额度已用尽：不输入并停止")
                                        break
                                    last_state = None
                                    if adaptive_operation_wait(maximum=0.20):
                                        break
                                    continue
                                set_state("复核每日任务页以安全回到列表顶部（1/2）")
                                continue

                            if activity_goal_confirmed:
                                # Claim-only terminal scan.  Claim-ready page
                                # states were handled before this branch, so
                                # every frame here is observational evidence.
                                # Starting from the proven top, stop as soon as
                                # the sorted list reaches the completed-check
                                # zone, or after two stationary bottom gestures.
                                # No task matcher or Go coordinate is evaluated.
                                completed_check, completed_check_score = (
                                    match_daily_task_completed_check(image, threshold)
                                )
                                if completed_check:
                                    daily_completed_zone_streak += 1
                                else:
                                    daily_completed_zone_streak = 0
                                if daily_completed_zone_streak == 1:
                                    set_state(
                                        "达标后只领取扫描：复核已完成打勾区（1/2）"
                                    )
                                    continue
                                if daily_completed_zone_streak >= 2:
                                    set_state(
                                        f"已排空当前完成奖励，最终活跃度约 {activity_points:.0f}"
                                    )
                                    self._log_for_device(
                                        target.device,
                                        "达标后已从双重确认顶部扫描到绿色打勾区，"
                                        "期间无剩余领取按钮；"
                                        f"最终活跃度约 {activity_points:.0f}，"
                                        f"打勾模板 {completed_check_score:.4f}。"
                                        "未点击任何前往或未完成任务。",
                                    )
                                    break

                                if daily_list_scan_before_image is not None:
                                    movement = daily_task_list_viewport_mean_change(
                                        daily_list_scan_before_image, image
                                    )
                                    daily_list_scan_before_image = None
                                    if (
                                        movement
                                        <= DAILY_TASK_LIST_BOUNDARY_MAX_MEAN_CHANGE
                                    ):
                                        daily_list_bottom_boundary_streak += 1
                                    else:
                                        daily_list_bottom_boundary_streak = 0
                                    self._log_for_device(
                                        target.device,
                                        "达标后只领取扫描的列表平均变化为 "
                                        f"{movement:.3f}；底部静止确认 "
                                        f"{daily_list_bottom_boundary_streak}/"
                                        f"{DAILY_TASK_LIST_BOUNDARY_CONFIRMATIONS}。",
                                    )

                                bottom_boundary_confirmed = (
                                    daily_list_bottom_boundary_streak
                                    >= DAILY_TASK_LIST_BOUNDARY_CONFIRMATIONS
                                )
                                if bottom_boundary_confirmed:
                                    set_state(
                                        f"已排空当前完成奖励，最终活跃度约 {activity_points:.0f}"
                                    )
                                    self._log_for_device(
                                        target.device,
                                        "达标后已从双重确认顶部扫描到双重确认底部，"
                                        "期间无剩余领取按钮；"
                                        f"最终活跃度约 {activity_points:.0f}。"
                                        "未点击任何前往或未完成任务。",
                                    )
                                    break
                                if daily_scrolls >= DAILY_TASK_LIST_MAX_SCAN_SWIPES:
                                    set_state(
                                        "达标后只领取扫描未在限次内确认边界：不输入并停止"
                                    )
                                    self._log_for_device(
                                        target.device,
                                        "达标后只领取扫描达到十二次手势上限，"
                                        "但未证明绿色打勾区或列表底部；"
                                        "没有点击前往，已安全停止。",
                                    )
                                    break
                                if streak >= 2:
                                    viewport = (
                                        DAILY_TASK_LIST_GESTURE_X,
                                        1750,
                                        DAILY_TASK_LIST_GESTURE_X,
                                        1000,
                                    )
                                    start_point = map_content_point(
                                        (viewport[0], viewport[1]),
                                        (1440, 2560),
                                        image,
                                    )
                                    end_point = map_content_point(
                                        (viewport[2], viewport[3]),
                                        (1440, 2560),
                                        image,
                                    )
                                    daily_list_scan_before_image = image.copy()
                                    target.shell(
                                        [
                                            "input",
                                            "swipe",
                                            str(start_point[0]),
                                            str(start_point[1]),
                                            str(end_point[0]),
                                            str(end_point[1]),
                                            "900",
                                        ]
                                    )
                                    daily_scrolls += 1
                                    last_state = None
                                    set_state(
                                        "达标后只领取扫描：检查下一视口"
                                        f"（{daily_scrolls}/"
                                        f"{DAILY_TASK_LIST_MAX_SCAN_SWIPES}）"
                                    )
                                    if adaptive_operation_wait(maximum=0.50):
                                        break
                                    continue
                                set_state("达标后只领取扫描：复核每日任务页（1/2）")
                                continue

                            warehouse_mission = (
                                None
                                if warehouse_supply_is_deferred()
                                else match_daily_warehouse_supply_mission(image, threshold)
                            )
                            if warehouse_mission:
                                set_state(f"发现已验证的仓库补给任务（{streak}/2，效率优先）")
                                if streak >= 2:
                                    verify_image = daily_screenshot()
                                    verify_page = detect_daily_task_state(verify_image, threshold)
                                    verified_warehouse = match_daily_warehouse_supply_mission(
                                        verify_image, threshold
                                    )
                                    if not (
                                        verify_page.state
                                        in (DailyTaskState.DAILY_PAGE, DailyTaskState.DAILY_LOGIN_COMPLETED)
                                        and verified_warehouse
                                        and stable(
                                            verified_warehouse.go_point,
                                            warehouse_mission.go_point,
                                        )
                                    ):
                                        set_state("仓库补给任务二次复核未通过：不输入并停止")
                                        self._log_for_device(
                                            target.device,
                                            "仓库补给任务在二次复核中变化；未点击前往。",
                                        )
                                        break
                                    target.tap(*verified_warehouse.go_point)
                                    # The tap itself starts the cooldown.  Persist it
                                    # before reading the result so a restart cannot
                                    # duplicate the same Warehouse availability.
                                    defer_warehouse_supply()
                                    self._log_for_device(
                                        target.device,
                                        f"点击已双帧确认的仓库补给前往 {verified_warehouse.go_point}；"
                                        "结果页采用 0.25 秒双帧确认后立即关闭，不等待随机倒计时。",
                                    )
                                    last_state = None
                                    set_state("仓库补给已触发，快速识别并立即关闭结果页")
                                    if not run_warehouse_supply_plan():
                                        set_state("仓库补给结果路线未完整确认，已停止且未作泛化点击")
                                        break
                                    city_entry_tapped = True
                                    transition_deadline = time.monotonic() + 8.0
                                    daily_tab_tapped = False
                                    restart_daily_list_scan()
                                    last_state = None
                                    continue

                            pet_mission = (
                                match_daily_pet_treasure_mission(image, threshold)
                                if pet_dispatch_ledger is not None
                                and pet_dispatch_ledger.available()
                                and not pet_failed_scan
                                and time.monotonic() >= pet_retry_at
                                else None
                            )
                            if pet_mission:
                                set_state(f"发现宠物寻宝任务，复核前往（{streak}/2）")
                                if streak >= 2:
                                    verify_image = daily_screenshot()
                                    verify_page = detect_daily_task_state(verify_image, threshold)
                                    verified_pet = match_daily_pet_treasure_mission(verify_image, threshold)
                                    if not (
                                        verify_page.state in (DailyTaskState.DAILY_PAGE, DailyTaskState.DAILY_LOGIN_COMPLETED)
                                        and verified_pet and stable(verified_pet.go_point, pet_mission.go_point)
                                    ):
                                        pet_failed_scan = True
                                        pet_retry_at = time.monotonic() + DAILY_RETRY_LOCK_MAX_SECONDS
                                        self._log_for_device(target.device, "宠物任务卡复核变化；本轮跳过，未输入。")
                                        last_state = None
                                        continue
                                    target.tap(*verified_pet.go_point)
                                    self._log_for_device(target.device, "已进入宠物寻宝；仅允许已验证的普通 10 体力派遣。")

                                    def pet_capture() -> Image.Image:
                                        try:
                                            return target.fast_window_screenshot(BUILTIN_DAILY_TASK_REFERENCE_SIZE)
                                        except AdbError:
                                            return target.screenshot(timeout=2)

                                    def pet_tap(x: int, y: int) -> None:
                                        target.shell(["input", "tap", str(x), str(y)], timeout=2)

                                    outcome = run_pet_treasure_cycle(
                                        pet_capture, pet_tap, self.stop_event.is_set, self.stop_event.wait,
                                        pet_dispatch_ledger.reserve, pet_dispatch_ledger.confirm,
                                        lambda message: self._log_for_device(target.device, message),
                                    )
                                    pet_failed_scan = True
                                    pet_retry_at = time.monotonic() + DAILY_RETRY_LOCK_MAX_SECONDS
                                    if outcome not in ("dispatched", "skipped"):
                                        set_state("宠物寻宝状态未完整确认，已停止且未重复输入")
                                        self._log_for_device(target.device, f"宠物寻宝路线结果：{outcome}；未对未知状态追加输入。")
                                        break
                                    if outcome == "dispatched":
                                        self._log_for_device(target.device, "宠物寻宝已确认进入自然倒计时；继续处理其他日常。")
                                    city_entry_tapped = True
                                    transition_deadline = time.monotonic() + 8.0
                                    daily_tab_tapped = False
                                    restart_daily_list_scan()
                                    last_state = None
                                    continue

                            if (
                                intel_route_attempted
                                and time.monotonic() >= intel_route_retry_at
                            ):
                                intel_route_attempted = False
                                intel_route_retry_at = 0.0
                            intel_mission = (
                                None
                                if intel_route_attempted or intel_failed_scan
                                else match_daily_intel_mission(image, threshold)
                            )
                            if intel_mission:
                                set_state(f"发现已验证的非战斗情报营救任务（{streak}/2）")
                                if streak >= 2:
                                    verify_image = daily_screenshot()
                                    verify_page = detect_daily_task_state(
                                        verify_image, threshold
                                    )
                                    verified_intel = match_daily_intel_mission(
                                        verify_image, threshold
                                    )
                                    if not (
                                        verify_page.state
                                        in (
                                            DailyTaskState.DAILY_PAGE,
                                            DailyTaskState.DAILY_LOGIN_COMPLETED,
                                        )
                                        and verified_intel
                                        and stable(
                                            verified_intel.go_point,
                                            intel_mission.go_point,
                                        )
                                    ):
                                        set_state("情报任务二次复核未通过：不输入并停止")
                                        self._log_for_device(
                                            target.device,
                                            "情报任务在二次复核中变化；未点击前往。",
                                        )
                                        break
                                    intel_route_attempted = True
                                    intel_route_retry_at = (
                                        time.monotonic()
                                        + DAILY_RETRY_LOCK_MAX_SECONDS
                                    )
                                    evidence = record_documented_daily_evidence(
                                        verify_image,
                                        "intel_rescue_card",
                                        "情报卡与同排蓝色前往已双帧确认；后续只允许绿色帐篷营救。",
                                    )
                                    target.tap(*verified_intel.go_point)
                                    self._log_for_device(
                                        target.device,
                                        f"点击双帧确认的情报前往 {verified_intel.go_point}；"
                                        f"证据 {evidence.name if evidence else '已识别未落盘'}。",
                                    )
                                    last_state = None
                                    set_state("已进入绿色帐篷情报营救路线")
                                    if not run_intel_rescue_plan():
                                        set_state("情报营救路线未完整确认，已停止且未作泛化点击")
                                        break
                                    city_entry_tapped = True
                                    transition_deadline = time.monotonic() + 8.0
                                    daily_tab_tapped = False
                                    restart_daily_list_scan()
                                    last_state = None
                                    continue

                            if (
                                arena_route_retry_at
                                and time.monotonic() >= arena_route_retry_at
                            ):
                                arena_route_retry_at = 0.0
                            arena_candidate = (
                                None
                                if arena_route_retry_at
                                else match_daily_arena_mission(image, threshold)
                            )
                            if arena_candidate:
                                expected_phase = (
                                    arena_candidate.target_count == 1
                                    and not arena_route_done
                                )
                                if expected_phase:
                                    set_state(
                                        "发现已验证竞技场"
                                        f"{arena_candidate.target_count}次任务（{streak}/2）"
                                    )
                                    if streak >= 2:
                                        verify_image = capture_daily_image()
                                        verify_page = detect_daily_task_state(
                                            verify_image, threshold
                                        )
                                        verified_arena = match_daily_arena_mission(
                                            verify_image, threshold
                                        )
                                        if not (
                                            verify_page.state in (
                                                DailyTaskState.DAILY_PAGE,
                                                DailyTaskState.DAILY_LOGIN_COMPLETED,
                                            )
                                            and verified_arena
                                            and verified_arena.target_count
                                            == arena_candidate.target_count
                                            and stable(
                                                verified_arena.go_point,
                                                arena_candidate.go_point,
                                            )
                                        ):
                                            set_state("竞技场任务二次复核未通过：不输入并停止")
                                            break
                                        evidence = record_documented_daily_evidence(
                                            verify_image,
                                            f"arena_{verified_arena.target_count}_card",
                                            "竞技场精确标题与同排前往已双帧确认；"
                                            "后续只允许免费次数和最低弱敌路线。",
                                        )
                                        target.tap(*verified_arena.go_point)
                                        arena_route_retry_at = (
                                            time.monotonic()
                                            + DAILY_RETRY_LOCK_MAX_SECONDS
                                        )
                                        self._log_for_device(
                                            target.device,
                                            "点击已双帧确认的竞技场"
                                            f"{verified_arena.target_count}次任务前往；"
                                            f"证据 {evidence.name if evidence else '已识别未落盘'}。",
                                        )
                                        last_state = None
                                        if not run_arena_plan():
                                            set_state(
                                                "竞技场路线未完整确认；10秒内不重试且未触碰付费控件"
                                            )
                                            break
                                        arena_route_done = True
                                        city_entry_tapped = True
                                        transition_deadline = time.monotonic() + 8.0
                                        daily_tab_tapped = False
                                        restart_daily_list_scan()
                                        last_state = None
                                        continue

                            donation_mission = (
                                None
                                if alliance_donation_confirmed_clicks >= DAILY_DONATION_TASK_TARGET
                                or daily_donation_is_deferred()
                                else match_daily_alliance_donate_mission(image, threshold)
                            )
                            if donation_mission:
                                set_state(f"发现已验证的联盟普通捐献任务（{streak}/2）")
                                if streak >= 2:
                                    verify_image = daily_screenshot()
                                    verify_page = detect_daily_task_state(verify_image, threshold)
                                    verified_donation = match_daily_alliance_donate_mission(verify_image, threshold)
                                    if not (
                                        verify_page.state in (DailyTaskState.DAILY_PAGE, DailyTaskState.DAILY_LOGIN_COMPLETED)
                                        and verified_donation
                                        and stable(verified_donation.go_point, donation_mission.go_point)
                                    ):
                                        set_state("联盟捐献任务二次复核未通过：不输入并停止")
                                        self._log_for_device(target.device, "联盟捐献任务在二次复核中变化；未点击前往。")
                                        break
                                    target.tap(*verified_donation.go_point)
                                    self._log_for_device(
                                        target.device,
                                        f"点击已双帧确认的联盟捐献任务前往 {verified_donation.go_point}；"
                                        "后续只允许对双帧蓝色普通肉类捐献按钮执行一次10000ms长按，"
                                        "长按后立即双帧确认灰色状态且绝不连按"
                                        f"（持久化今日 "
                                        f"{alliance_donation_confirmed_clicks}/{DAILY_DONATION_TASK_TARGET}）。",
                                    )
                                    last_state = None
                                    set_state("已进入联盟普通肉类捐献路线")
                                    if not run_alliance_food_donation_plan():
                                        set_state("联盟普通肉类捐献路线未完整确认，已停止且未作恢复输入")
                                        break
                                    city_entry_tapped = True
                                    transition_deadline = time.monotonic() + 8.0
                                    daily_tab_tapped = False
                                    restart_daily_list_scan()
                                    last_state = None
                                    continue
                            if (
                                building_upgrade_unavailable
                                and time.monotonic() >= building_upgrade_retry_at
                            ):
                                building_upgrade_unavailable = False
                                building_upgrade_retry_at = 0.0
                            building_mission = (
                                None
                                if building_upgrade_unavailable or building_failed_scan
                                else match_daily_building_upgrade_mission(image, threshold)
                            )
                            if building_mission:
                                if building_upgrade_started:
                                    # The exact unfinished task remains visible
                                    # until its natural construction timer ends.
                                    # Keep observing it rather than re-entering
                                    # the building or touching any speed-up.
                                    restart_daily_list_scan()
                                    set_state("普通建筑升级进行中：等待自然完成，不使用加速")
                                    if adaptive_operation_wait(maximum=1.0):
                                        break
                                    last_state = None
                                    continue
                                set_state(f"发现已验证的建筑升级任务（{streak}/2）")
                                if streak >= 2:
                                    verify_image = daily_screenshot()
                                    verify_page = detect_daily_task_state(verify_image, threshold)
                                    verified_building = match_daily_building_upgrade_mission(verify_image, threshold)
                                    if not (
                                        verify_page.state in (DailyTaskState.DAILY_PAGE, DailyTaskState.DAILY_LOGIN_COMPLETED)
                                        and verified_building
                                        and stable(verified_building.go_point, building_mission.go_point)
                                    ):
                                        # The list may still be settling after a fast swipe.  A
                                        # changed candidate is not authority for any tap, but it
                                        # also must not terminate the whole Daily run.  Discard
                                        # this viewport and prove the top boundary again.
                                        set_state("建筑升级任务二次复核未通过：不输入并快速重扫")
                                        self._log_for_device(
                                            target.device,
                                            "每日建筑升级任务在二次复核中变化；未点击前往，改为零输入回顶重扫。",
                                        )
                                        restart_daily_list_scan()
                                        last_state = None
                                        continue
                                    target.tap(*verified_building.go_point)
                                    self._log_for_device(
                                        target.device,
                                        f"点击已双帧确认的建筑升级任务前往 {verified_building.go_point}；后续只使用普通建造。",
                                    )
                                    last_state = None
                                    set_state("已进入每日建筑任务的普通建造路线")
                                    if not run_daily_building_upgrade_plan():
                                        set_state("每日建筑升级路线未完整确认，已停止且未作恢复输入")
                                        break
                                    if not building_upgrade_unavailable:
                                        building_upgrade_started = True
                                    city_entry_tapped = True
                                    transition_deadline = time.monotonic() + 8.0
                                    daily_tab_tapped = False
                                    restart_daily_list_scan()
                                    last_state = None
                                    continue
                            hero_mission = (
                                None
                                if hero_recruit_is_deferred()
                                else match_daily_hero_recruit_mission(image, threshold)
                            )
                            if hero_mission:
                                set_state(f"发现已验证的英雄招募任务（{streak}/2）")
                                if streak >= 2:
                                    verify_image = daily_screenshot()
                                    verify_page = detect_daily_task_state(verify_image, threshold)
                                    verified_hero = match_daily_hero_recruit_mission(verify_image, threshold)
                                    if not (
                                        verify_page.state in (DailyTaskState.DAILY_PAGE, DailyTaskState.DAILY_LOGIN_COMPLETED)
                                        and verified_hero
                                        and stable(verified_hero.go_point, hero_mission.go_point)
                                    ):
                                        set_state("英雄招募任务二次复核未通过：不输入并停止")
                                        self._log_for_device(target.device, "每日英雄招募任务在二次复核中变化；未点击前往。")
                                        break
                                    target.tap(*verified_hero.go_point)
                                    self._log_for_device(
                                        target.device,
                                        f"点击已双帧确认的英雄招募任务前往 {verified_hero.go_point}；后续只点绿色免费招募。",
                                    )
                                    last_state = None
                                    set_state("已进入英雄免费招募路线")
                                    if not run_free_hero_recruit_plan():
                                        failure_image = daily_screenshot()
                                        if adaptive_operation_wait(maximum=0.50):
                                            break
                                        failure_verify_image = daily_screenshot()
                                        failure_city, _failure_city_score = match_daily_city_entry(
                                            failure_image,
                                            threshold,
                                        )
                                        verify_city, _verify_city_score = match_daily_city_entry(
                                            failure_verify_image,
                                            threshold,
                                        )
                                        if (
                                            failure_city
                                            and verify_city
                                            and stable(failure_city, verify_city)
                                        ):
                                            defer_hero_recruit()
                                            target.tap(*verify_city)
                                            self._log_for_device(
                                                target.device,
                                                "英雄招募前往未确认招募页，但已连续两帧证明返回主城；"
                                                f"点击精确每日任务入口 {verify_city}，五分钟后在安全边界复查并继续后续任务。",
                                            )
                                            city_entry_tapped = True
                                            transition_deadline = time.monotonic() + 8.0
                                            daily_tab_tapped = False
                                            restart_daily_list_scan()
                                            last_state = None
                                            continue
                                        set_state("英雄免费招募路线未完整确认，已停止且未作恢复输入")
                                        break
                                    city_entry_tapped = True
                                    transition_deadline = time.monotonic() + 8.0
                                    daily_tab_tapped = False
                                    restart_daily_list_scan()
                                    last_state = None
                                    continue

                            # A natural training queue may run while claims,
                            # alliance help, and gathering-independent Daily
                            # items continue.  Re-enable its card only after a
                            # conservative eight-minute passive window so the
                            # worker can later collect a finished tutorial but
                            # can never start a duplicate queue immediately.
                            now = time.monotonic()
                            for deferred_kind, recheck_at in list(deferred_training_recheck_at.items()):
                                if now >= recheck_at:
                                    deferred_auxiliary_training.discard(deferred_kind)
                                    deferred_training_recheck_at.pop(deferred_kind, None)
                                    successful_training_retry_epoch.pop(deferred_kind, None)
                                    save_active_training_deferrals()
                            refresh_failed_training_kinds()
                            if (
                                training_route_attempted
                                and now >= training_route_retry_at
                            ):
                                training_route_attempted = False
                                training_route_retry_at = 0.0
                            training_missions = (
                                ()
                                if training_route_attempted
                                else match_daily_training_missions(image, threshold)
                            )
                            # Starting a full queue is intentionally work for
                            # the next collection cycle.  On the first fresh
                            # Daily viewport after returning, reread and save
                            # the exact task count instead of assuming that
                            # today's progress changed when Train was tapped.
                            for visible_training in training_missions:
                                if (
                                    visible_training.kind in deferred_auxiliary_training
                                    and visible_training.kind not in reported_training_progress
                                ):
                                    progress = read_daily_training_progress(
                                        image,
                                        visible_training.kind,
                                        threshold,
                                    )
                                    if progress is not None:
                                        current, required = progress
                                        progress_label = mission_label(visible_training.kind)
                                        evidence = record_documented_daily_evidence(
                                            image,
                                            f"training_{visible_training.kind.value}_post_queue",
                                            f"普通训练队列已拉满启动；返回每日任务后复读为 {current}/{required}，"
                                            "不把当天新队列误计为已结算进度。",
                                        )
                                        reported_training_progress.add(visible_training.kind)
                                        self._log_for_device(
                                            target.device,
                                            f"{progress_label}拉满训练后已返回每日任务复读进度 {current}/{required}；"
                                            f"该队列留给下次收兵使用，证据 {evidence.name if evidence else '已识别未落盘'}。",
                                        )
                            shield_mission = next(
                                (
                                    item
                                    for item in training_missions
                                    if item.kind is DailyMissionKind.TRAIN_SHIELD
                                    and item.kind not in deferred_auxiliary_training
                                    and item.kind not in failed_training_kinds
                                    and item.kind not in training_failed_scan_kinds
                                ),
                                None,
                            )
                            if shield_mission:
                                set_state(f"发现已验证的盾兵训练任务（{streak}/2）")
                                if streak >= 2:
                                    verify_image = daily_screenshot()
                                    verify_page = detect_daily_task_state(verify_image, threshold)
                                    verify_missions = match_daily_training_missions(verify_image, threshold)
                                    verified_shield = next(
                                        (item for item in verify_missions if item.kind is DailyMissionKind.TRAIN_SHIELD),
                                        None,
                                    )
                                    if not (
                                        verify_page.state in (DailyTaskState.DAILY_PAGE, DailyTaskState.DAILY_LOGIN_COMPLETED)
                                        and verified_shield
                                        and stable(verified_shield.go_point, shield_mission.go_point)
                                    ):
                                        set_state("盾兵训练任务二次复核未通过：不输入并停止")
                                        self._log_for_device(target.device, "每日盾兵训练任务在二次复核中变化；未点击前往。")
                                        break
                                    target.tap(*verified_shield.go_point)
                                    self._log_for_device(
                                        target.device,
                                        f"点击已双帧确认的盾兵训练任务前往 {verified_shield.go_point}；后续只使用普通训练。",
                                    )
                                    last_state = None
                                    set_state("已进入盾兵普通训练路线")
                                    if not run_shield_training_plan():
                                        failure_image = daily_screenshot()
                                        failure_page = detect_daily_task_state(failure_image, threshold)
                                        if adaptive_operation_wait(maximum=0.50):
                                            break
                                        failure_verify_image = daily_screenshot()
                                        failure_verify_page = detect_daily_task_state(
                                            failure_verify_image, threshold
                                        )
                                        daily_failure_states = (
                                            DailyTaskState.DAILY_PAGE,
                                            DailyTaskState.DAILY_LOGIN_COMPLETED,
                                        )
                                        if (
                                            failure_page.state in daily_failure_states
                                            and failure_verify_page.state in daily_failure_states
                                        ):
                                            training_route_attempted = True
                                            training_route_retry_at = (
                                                time.monotonic()
                                                + DAILY_RETRY_LOCK_MAX_SECONDS
                                            )
                                            self._log_for_device(
                                                target.device,
                                                "盾兵任务前往后仍双重确认在每日任务页；"
                                                "训练卡片仅让行 10 秒并继续独立任务，未作恢复点击。",
                                            )
                                            restart_daily_list_scan()
                                            last_state = None
                                            continue
                                        if recover_failed_training_from_proven_city(
                                            DailyMissionKind.TRAIN_SHIELD,
                                            "盾兵",
                                            failure_image,
                                            failure_verify_image,
                                        ):
                                            city_entry_tapped = True
                                            transition_deadline = time.monotonic() + 8.0
                                            daily_tab_tapped = False
                                            restart_daily_list_scan()
                                            last_state = None
                                            continue
                                        set_state("盾兵普通训练路线未完整确认，已停止且未作恢复输入")
                                        break
                                    city_entry_tapped = True
                                    transition_deadline = time.monotonic() + 8.0
                                    daily_tab_tapped = False
                                    restart_daily_list_scan()
                                    last_state = None
                                    continue

                            auxiliary_training = next(
                                (
                                    item
                                    for item in training_missions
                                    if item.kind in (DailyMissionKind.TRAIN_SPEAR, DailyMissionKind.TRAIN_ARCHER)
                                    and item.kind not in deferred_auxiliary_training
                                    and item.kind not in failed_training_kinds
                                    and item.kind not in training_failed_scan_kinds
                                ),
                                None,
                            )
                            if auxiliary_training:
                                label = mission_label(auxiliary_training.kind)
                                set_state(f"发现已验证的{label}训练任务（{streak}/2）")
                                if streak >= 2:
                                    verify_image = daily_screenshot()
                                    verify_page = detect_daily_task_state(verify_image, threshold)
                                    verify_missions = match_daily_training_missions(verify_image, threshold)
                                    verified_auxiliary = next(
                                        (item for item in verify_missions if item.kind is auxiliary_training.kind),
                                        None,
                                    )
                                    if not (
                                        verify_page.state in (DailyTaskState.DAILY_PAGE, DailyTaskState.DAILY_LOGIN_COMPLETED)
                                        and verified_auxiliary
                                        and stable(verified_auxiliary.go_point, auxiliary_training.go_point)
                                    ):
                                        set_state(f"{label}训练任务二次复核未通过：不输入并停止")
                                        self._log_for_device(target.device, f"每日{label}训练任务在二次复核中变化；未点击前往。")
                                        break
                                    target.tap(*verified_auxiliary.go_point)
                                    self._log_for_device(
                                        target.device,
                                        f"点击已双帧确认的{label}训练任务前往 {verified_auxiliary.go_point}；后续只使用普通训练。",
                                    )
                                    last_state = None
                                    set_state(f"已进入{label}普通训练路线")
                                    if not run_auxiliary_training_plan(verified_auxiliary.kind):
                                        failure_image = daily_screenshot()
                                        failure_page = detect_daily_task_state(failure_image, threshold)
                                        if adaptive_operation_wait(maximum=0.50):
                                            break
                                        failure_verify_image = daily_screenshot()
                                        failure_verify_page = detect_daily_task_state(
                                            failure_verify_image, threshold
                                        )
                                        daily_failure_states = (
                                            DailyTaskState.DAILY_PAGE,
                                            DailyTaskState.DAILY_LOGIN_COMPLETED,
                                        )
                                        if (
                                            failure_page.state in daily_failure_states
                                            and failure_verify_page.state in daily_failure_states
                                        ):
                                            training_route_attempted = True
                                            training_route_retry_at = (
                                                time.monotonic()
                                                + DAILY_RETRY_LOCK_MAX_SECONDS
                                            )
                                            self._log_for_device(
                                                target.device,
                                                f"{label}任务前往后仍双重确认在每日任务页；"
                                                "训练卡片仅让行 10 秒并继续独立任务，未作恢复点击。",
                                            )
                                            restart_daily_list_scan()
                                            last_state = None
                                            continue
                                        if recover_failed_training_from_proven_city(
                                            verified_auxiliary.kind,
                                            label,
                                            failure_image,
                                            failure_verify_image,
                                        ):
                                            city_entry_tapped = True
                                            transition_deadline = time.monotonic() + 8.0
                                            daily_tab_tapped = False
                                            restart_daily_list_scan()
                                            last_state = None
                                            continue
                                        set_state(f"{label}普通训练路线未完整确认，已停止且未作恢复输入")
                                        break
                                    city_entry_tapped = True
                                    transition_deadline = time.monotonic() + 8.0
                                    daily_tab_tapped = False
                                    restart_daily_list_scan()
                                    last_state = None
                                    continue

                            if time.monotonic() < gather_cards_suppressed_until:
                                missions = ()
                                set_state("行军队列已双帧确认占满：暂时屏蔽全部采集卡，继续后续独立任务")
                            else:
                                missions = match_daily_gather_missions(image, threshold)
                            if active_gather_kind is not None:
                                active_label = mission_label(active_gather_kind)
                                set_state(
                                    f"{active_label}倒计时已记录：同类不重复；"
                                    "其他采集卡在逐次复核空闲队列、兵力和负重后可继续"
                                )
                            if inherited_gather_slot_active:
                                set_state(
                                    "已看到继承采集队列：不推断占满；"
                                    "任何新采集都必须先返回地图双帧读取 used/total"
                                )
                            # One full, carry-proved trip per resource kind is
                            # sufficient for the matching Daily amount.  Avoid
                            # duplicating that kind while still allowing other
                            # visible gather cards to use independently proved
                            # free marches.
                            missions = tuple(
                                item
                                for item in missions
                                if item.kind not in dispatched_gather_kinds
                                and deferred_gather_recheck_at.get(item.kind, 0.0) <= time.monotonic()
                            )
                            if missions:
                                mission_amounts = ", ".join(
                                    f"{mission_label(item.kind)} {DAILY_GATHER_REQUIRED_AMOUNTS[item.kind]:,}"
                                    for item in missions
                                )
                                mission_names = "、".join(mission_label(item.kind) for item in missions)
                                set_state(f"发现已验证的普通采集任务：{mission_names}（{streak}/2）")
                                if streak >= 2:
                                    # Page evidence and a title/button pair
                                    # must both survive a fresh second frame;
                                    # never use a previous frame's Go target.
                                    verify_image = daily_screenshot()
                                    verify_page = detect_daily_task_state(verify_image, threshold)
                                    verify_missions = tuple(
                                        item
                                        for item in match_daily_gather_missions(
                                            verify_image, threshold
                                        )
                                        if item.kind not in dispatched_gather_kinds
                                        and deferred_gather_recheck_at.get(item.kind, 0.0) <= time.monotonic()
                                    )
                                    same_plan = (
                                        verify_page.state in (DailyTaskState.DAILY_PAGE, DailyTaskState.DAILY_LOGIN_COMPLETED)
                                        and tuple(item.kind for item in verify_missions)
                                        == tuple(item.kind for item in missions)
                                        and bool(verify_missions)
                                        and stable(verify_missions[0].go_point, missions[0].go_point)
                                    )
                                    if not same_plan:
                                        set_state("采集任务二次复核发生瞬态变化：未输入，重新从顶部扫描")
                                        self._log_for_device(
                                            target.device,
                                            "每日采集任务在二次复核中变化；未点击前往，已重新从顶部扫描后续任务。",
                                        )
                                        restart_daily_list_scan()
                                        last_state = None
                                        continue
                                    first = verify_missions[0]
                                    self._log_for_device(
                                        target.device,
                                        f"已读取采集任务最低要求：{mission_amounts}；本轮每项只派 1 队，返回后重新读取任务状态。",
                                    )
                                    target.tap(*first.go_point)
                                    self._log_for_device(
                                        target.device,
                                        f"点击已双帧确认的{mission_label(first.kind)}任务前往 {first.go_point}；"
                                        f"后续仅执行普通采集。",
                                    )
                                    last_state = None
                                    set_state(f"已进入{mission_label(first.kind)}普通采集路线")
                                    if not run_gather_plan(tuple(item.kind for item in verify_missions)):
                                        set_state("普通采集路线未完整确认，已停止且未作恢复输入")
                                        break
                                    city_entry_tapped = True
                                    transition_deadline = time.monotonic() + 8.0
                                    daily_tab_tapped = False
                                    restart_daily_list_scan()
                                    last_state = None
                                    continue
                            completed_check, completed_check_score = match_daily_task_completed_check(
                                image,
                                threshold,
                            )
                            if completed_check:
                                daily_completed_zone_streak += 1
                            else:
                                daily_completed_zone_streak = 0
                            if daily_completed_zone_streak == 1:
                                set_state("复核绿色打勾的已完成任务卡（1/2）；不点击该卡")
                                continue
                            if daily_completed_zone_streak >= 2:
                                training_failed_scan_kinds.clear()
                                intel_failed_scan = False
                                pet_failed_scan = False
                                building_failed_scan = False
                                if alliance_donation_prerequisite_blocked:
                                    alliance_donation_prerequisite_blocked = False
                                    alliance_donation_unavailable = True
                                    defer_daily_donation(10.0)
                                self._log_for_device(
                                    target.device,
                                    "每日任务列表已连续两帧确认当前视口含绿色打勾的已完成卡"
                                    f"（模板 {completed_check_score:.4f}）；"
                                    "已进入打勾区，立即高速回到列表顶部；不再扫描其下方。",
                                )
                                daily_completed_zone_wait_after_top = True
                                restart_daily_list_scan()
                                if not send_daily_fast_top_gesture(image):
                                    set_state("打勾区回顶手势额度已用尽：不输入并停止")
                                    self._log_for_device(
                                        target.device,
                                        "打勾区已确认，但高速回顶手势额度不可用；"
                                        "未继续向下或点击任务，已安全停止。",
                                    )
                                    break
                                last_state = None
                                if adaptive_operation_wait(maximum=0.20):
                                    break
                                continue
                            if daily_list_scan_before_image is not None:
                                movement = daily_task_list_viewport_mean_change(
                                    daily_list_scan_before_image, image
                                )
                                daily_list_scan_before_image = None
                                if movement <= DAILY_TASK_LIST_BOUNDARY_MAX_MEAN_CHANGE:
                                    daily_list_bottom_boundary_streak += 1
                                else:
                                    daily_list_bottom_boundary_streak = 0
                                self._log_for_device(
                                    target.device,
                                    "每日任务向下扫描滑动后的列表平均变化为 "
                                    f"{movement:.3f}；底部静止确认 "
                                    f"{daily_list_bottom_boundary_streak}/"
                                    f"{DAILY_TASK_LIST_BOUNDARY_CONFIRMATIONS}。",
                                )

                            bottom_boundary_confirmed = (
                                daily_list_bottom_boundary_streak
                                >= DAILY_TASK_LIST_BOUNDARY_CONFIRMATIONS
                            )
                            if bottom_boundary_confirmed:
                                training_failed_scan_kinds.clear()
                                intel_failed_scan = False
                                pet_failed_scan = False
                                building_failed_scan = False
                                if alliance_donation_prerequisite_blocked:
                                    alliance_donation_prerequisite_blocked = False
                                    alliance_donation_unavailable = True
                                    defer_daily_donation(10.0)
                            if (
                                not bottom_boundary_confirmed
                                and daily_scrolls >= DAILY_TASK_LIST_MAX_SCAN_SWIPES
                            ):
                                set_state("无法在限次内确认每日任务列表底部：不输入并停止")
                                self._log_for_device(
                                    target.device,
                                    "每日任务向下扫描达到滑动上限，但没有连续两次静止证据；"
                                    "未宣称完整扫描，已停止。",
                                )
                                break
                            if not bottom_boundary_confirmed and streak >= 2:
                                # x=900 is a measured scrollable lane in the
                                # Daily list.  Each new viewport is inspected
                                # by all task matchers above before this branch
                                # is allowed to issue the next gesture.
                                viewport = (
                                    DAILY_TASK_LIST_GESTURE_X,
                                    1750,
                                    DAILY_TASK_LIST_GESTURE_X,
                                    1000,
                                )
                                start_point = map_content_point(
                                    (viewport[0], viewport[1]), (1440, 2560), image
                                )
                                end_point = map_content_point(
                                    (viewport[2], viewport[3]), (1440, 2560), image
                                )
                                daily_list_scan_before_image = image.copy()
                                target.shell(
                                    [
                                        "input",
                                        "swipe",
                                        str(start_point[0]),
                                        str(start_point[1]),
                                        str(end_point[0]),
                                        str(end_point[1]),
                                        "900",
                                    ]
                                )
                                daily_scrolls += 1
                                last_state = None
                                set_state(
                                    "每日任务列表已在验证通道上滑，检查新任务与真实位移"
                                    f"（{daily_scrolls}/{DAILY_TASK_LIST_MAX_SCAN_SWIPES}）"
                                )
                                self._log_for_device(
                                    target.device,
                                    "每日任务页当前视口无已验证执行项，已在 x=900 列表通道上滑一次；"
                                    f"等待像素位移复核（{daily_scrolls}/"
                                    f"{DAILY_TASK_LIST_MAX_SCAN_SWIPES}）。",
                                )
                                if adaptive_operation_wait(maximum=0.50):
                                    break
                                continue
                            if bottom_boundary_confirmed:
                                # A fully scanned list below the requested
                                # target is not a completion condition.  Some
                                # Daily tasks settle on a timer or are exposed
                                # only after refresh; keep the worker alive
                                # and rescan later instead of declaring success
                                # at (for example) 185/325.
                                (
                                    idle_wait_seconds,
                                    idle_wait_label,
                                    refresh_visible,
                                    estimated,
                                ) = daily_idle_wait_plan(
                                    image,
                                    activity_points,
                                    activity_confidence,
                                )
                                restart_daily_list_scan()
                                last_state = None
                                set_state(
                                    f"每日活跃度 {estimated}/325，未找到已验证路线；{idle_wait_label}后重新扫描"
                                )
                                self._log_for_device(
                                    target.device,
                                    (
                                        f"每日任务已从双重确认顶部扫描到双重确认底部但未到 325（估算 {estimated}）；"
                                        f"{'检测到刷新倒计时，' if refresh_visible else ''}保留运行并在 {idle_wait_label}后重扫。"
                                    ),
                                )
                                # This absolute no-input deadline is the
                                # earliest persisted task boundary (Warehouse,
                                # recruit, training, gathering, donation) or
                                # the conservative/static-refresh fallback.
                                # It is consumed in <=1.5-second stop-aware
                                # slices by the loop above.
                                idle_no_input_until = (
                                    time.monotonic()
                                    + max(idle_wait_seconds, interval)
                                )
                                idle_no_input_label = idle_wait_label
                                continue
                            set_state("复核每日任务页（1/2）")
                            continue

                        set_state("检测到未允许的每日状态：不输入并停止")
                        self._log_for_device(target.device, "每日奖励流程遇到未允许状态；未执行输入。")
                        break
                except Exception as exc:
                    set_state("每日奖励识别异常：不输入并停止")
                    self._log_for_device(target.device, f"每日奖励流程异常；未执行恢复输入：{exc}")
                    break
                if self.stop_event.wait(interval):
                    break

            set_state(f"已停止：领取 {claims} 项奖励")
            self._log_for_device(target.device, f"每日奖励收取已停止（领取 {claims} 项）。")

        self._start_worker(target.device, job)


start_daily_rewards_flow = DailyController._start_daily_rewards_flow
