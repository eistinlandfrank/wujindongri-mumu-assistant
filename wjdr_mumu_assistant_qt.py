# -*- coding: utf-8 -*-
"""Release-grade PySide6 desktop UI for the MuMu alliance-help assistant."""

from __future__ import annotations

import argparse
import ctypes
import hashlib
import json
import os
import subprocess
import sys
import threading
import time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Callable

from PIL import Image, ImageChops, ImageStat
from wjdr_daily_visuals import intel_coloured_candidates, intel_expert, intel_expert_maybe_visible, intel_station_expert, recommended_tech
from wjdr_daily_expedition import ExpeditionClaimLedger, run_expedition_claim
from wjdr_daily_intel import IntelExpertLedger, match_hero_preview_any_level, match_hero_victory, match_selected_hero_battle
from PySide6.QtCore import QObject, QPoint, QRect, Qt, QTimer, Signal, QDateTime, QTime
from PySide6.QtGui import QColor, QFont, QIcon, QImage, QPainter, QPainterPath, QPalette, QPen, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDateTimeEdit,
    QDoubleSpinBox,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QAbstractItemView,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QRadioButton,
    QScrollArea,
    QSizePolicy,
    QSlider,
    QSpinBox,
    QStackedWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
    QInputDialog,
)

from wjdr_backend import (
    AdbError,
    APP_NAME,
    APP_VERSION,
    AlliancePage,
    BEAST_RALLY_BUILTIN_ASSETS,
    BUILTIN_DAILY_TASK_REFERENCE_SIZE,
    BeastRallyProfile,
    BeastRallyState,
    BUILTIN_ALL_HELP_TEMPLATE_NAME,
    BUILTIN_CITY_ALLIANCE_TEMPLATE_ASSET,
    BUILTIN_HELP_TEMPLATE_NAME,
    BUILTIN_MUTUAL_ENTRY_TEMPLATE_ASSET,
    BUILTIN_MUTUAL_PAGE_TEMPLATE_ASSET,
    CONFIG_DIR,
    CREATE_NO_WINDOW,
    CastleLevelGate,
    DAILY_BUILTIN_TEMPLATES,
    DAILY_GATHER_FULL_NODE_MIN_RETURN_SECONDS,
    DAILY_GATHER_PASSIVE_WAIT_CAP_SECONDS,
    DAILY_GATHER_SAFE_RESOURCE_LEVEL,
    DAILY_TASK_LIST_BOUNDARY_CONFIRMATIONS,
    DAILY_TASK_LIST_BOUNDARY_MAX_MEAN_CHANGE,
    DAILY_TASK_LIST_FAST_TOP_MAX_GESTURES,
    DAILY_TASK_LIST_FAST_TOP_SWIPE,
    DAILY_TASK_LIST_GESTURE_X,
    DAILY_TASK_LIST_MAX_SCAN_SWIPES,
    DAILY_GATHER_REQUIRED_AMOUNTS,
    DEFAULT_TASKS,
    DailyAbnormalExitKind,
    DailyMissionKind,
    DailyTaskState,
    DeviceLease,
    LOG_FILE,
    MiningLevelProfile,
    MuMuADB,
    RED_PACKET_BUILTIN_TEMPLATES,
    RedPacketState,
    TASK_FILE,
    TEMPLATE_DIR,
    clean_name,
    beast_rally_level_field_point,
    beast_rally_level_is_configured,
    beast_rally_selector_search_point,
    beast_rally_first_formation_point,
    beast_rally_three_minutes_point,
    beast_rally_stamina_limit_allows,
    beast_rally_new_busy_queue_indexes,
    beast_rally_expanded_capacity_baseline,
    load_beast_rally_profile,
    load_beast_rally_stamina_spent,
    load_beast_rally_stamina_reserved,
    load_beast_rally_stamina_reserved_any_day,
    load_beast_rally_stamina_uncertain,
    begin_beast_stamina_item_use,
    begin_beast_stamina_item_batch,
    begin_beast_stamina_fast_batch,
    archive_beast_stamina_fast_batch_uncertain,
    archive_beast_rally_unconfirmed_reservation,
    reconcile_beast_overlapping_dispatches,
    load_beast_rally_submitted_pending,
    clear_beast_rally_submitted_pending,
    update_beast_stamina_fast_batch,
    load_beast_stamina_item_pending,
    confirm_beast_stamina_item_use,
    record_beast_stamina_batch_partial,
    read_beast_stamina_item_observation,
    reconcile_beast_rally_idle_reservation,
    reconcile_beast_rally_gathering_reservation,
    load_mining_level_profile,
    initial_mining_resource_level,
    prune_runtime_evidence,
    content_frame_mean_change,
    content_viewport,
    alliance_tech_tree_viewport_mean_change,
    detect_alliance_page,
    detect_castle_level_gate,
    detect_daily_task_state,
    diagnose_daily_abnormal_exit,
    detect_red_packet_state,
    detect_world_resource_level,
    daily_activity_chest_points,
    daily_task_list_viewport_mean_change,
    match_daily_activity_chest_open,
    match_daily_task_completed_check,
    match_beast_rally_progress_sidebar_collapsed,
    match_beast_rally_progress_sidebar_expanded,
    match_beast_rally_progress_wilderness_tab,
    read_beast_rally_collapsed_march_capacity,
    read_beast_rally_expanded_march_capacity,
    read_beast_rally_wilderness_queue_states,
    match_beast_rally_world_search,
    match_beast_rally_selector,
    match_beast_rally_search_drawer,
    match_beast_rally_search_drawer_without_level,
    match_beast_exception_exploration_header,
    beast_rally_beast_target_point,
    match_beast_rally_open_button,
    match_beast_rally_sheet,
    match_beast_rally_sheet_controls,
    match_beast_rally_formation,
    match_beast_rally_formation_controls,
    read_beast_rally_dispatch_stamina,
    read_beast_rally_dispatch_stamina_shortfall,
    match_beast_rally_stamina_more,
    match_beast_rally_stamina_more_controls,
    read_beast_rally_selector_level,
    record_beast_rally_stamina_spent,
    reserve_beast_rally_stamina,
    confirm_beast_rally_stamina_reservation,
    match_daily_task_header,
    match_daily_task_refresh_label,
    match_daily_task_selected_tab,
    daily_activity_target_reached,
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
    daily_hero_recruit_result_is_visible,
    match_daily_hero_recruit_duplicate_result,
    match_daily_hero_recruit_summary_exit,
    daily_chest_result_exit_point,
    match_daily_city_entry,
    match_daily_city_wilderness_entry,
    match_daily_city_alliance_entry,
    daily_reward_result_exit_point,
    estimate_daily_activity_progress,
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
    match_daily_tap_anywhere_exit_text,
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
    match_daily_intel_hero_victory,
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
    daily_training_input_focus_is_proven,
    match_daily_training_unlock_continue,
    match_daily_training_shield_camp,
    match_red_packet_marker,
    match_template,
    map_content_point,
    prepare_storage,
    resource_path,
    save_beast_rally_profile,
    save_mining_level_profile,
    daily_gather_selector_is_valid,
    daily_gather_meat_is_selected,
    match_daily_gather_meat_visible_tab,
    scale_recorded_point,
    template_reference_size,
)


from wjdr_frontend_layout import FrontendLayout
from wjdr_daily_controller import start_daily_rewards_flow
from wjdr_schedule_ui import ScheduleUI
import wjdr_schedule as schedules

from wjdr_ui_components import COLORS, UiSignals, Card, ScreenshotView, LightSettingsDialog, MiningLevelSettingsDialog, BeastRallySettingsDialog


# A single automation action must never monopolise the worker for minutes.
# Longer passive policies are kept as absolute no-input timestamps and revisited
# in <=30-second slices.
# Leave enough wall-clock headroom for one final ADB capture and classifier
# pass so a nominal watchdog can never spill beyond the user's 30-second
# per-step ceiling on this machine.
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


def beast_wait_for_natural_stamina(wait, check, stopped, *, segments=10, seconds=30):
    """Wait in interruptible bounded segments without inferring a stamina value."""
    if type(segments) is not int or segments < 1 or not 0 < seconds <= 30:
        raise ValueError('invalid stamina wait')
    for _ in range(segments):
        if stopped() or wait(seconds) or stopped() or not check():
            return False
    return True


def beast_close_paid_stamina_overlay(first, second, *, paid, close_point, stable, network,
                                    pending, reserved, check_active, tap, capture,
                                    match_world, match_formation, archive, stopped):
    """Close a positively identified paid-only page once; never tap its paid control."""
    first_paid, second_paid = paid(first), paid(second)
    if not first_paid and not second_paid:
        return None
    if (not first_paid or not second_paid or stopped() or reserved()
            or network(first) or network(second)):
        return False
    entry = pending()
    if entry and (entry.get('mode') != 'fast' or entry.get('phase') != 'sent'):
        return False
    close_a, close_b = close_point(first), close_point(second)
    if not stable(close_a, close_b):
        return False
    check_active()
    if stopped():
        return False
    tap(close_b)
    for _ in range(4):
        after_a, after_b = capture(), capture()
        if stopped() or reserved() or network(after_a) or network(after_b):
            return False
        world = stable(match_world(after_a), match_world(after_b))
        formation = stable(match_formation(after_a), match_formation(after_b))
        if world or formation:
            break
    else:
        return False
    check_active()
    if stopped() or reserved() or pending() != entry:
        return False
    if entry:
        archive(entry['id'])
    return 'world' if world else 'formation'


def beast_stamina_close_point(image, threshold=0.90):
    """Recognize the reviewed close control only on the full stamina page."""
    from wjdr_backend import beast_stamina_paid_only_page
    page = match_beast_rally_stamina_more(image, threshold)
    if page.state is not BeastRallyState.STAMINA_MORE:
        # A toast can cover the description; title and the ordinary green use
        # control still identify this page without reading stamina digits.
        controls = match_beast_rally_stamina_more_controls(image, threshold)
        viewport = content_viewport(image)
        icon, _ = match_template(
            image, resource_path('assets/beast_rally_stamina_item10_icon_live.png'),
            0.985, (1440, 2560),
            (viewport.left + int(viewport.width * .09), viewport.top + int(viewport.height * .36),
             viewport.left + int(viewport.width * .21), viewport.top + int(viewport.height * .43)))
        if not ((controls.state is BeastRallyState.STAMINA_MORE and icon)
                or beast_stamina_paid_only_page(image, threshold)):
            return None
    viewport = content_viewport(image)
    if (viewport.width, viewport.height) != (1440, 2560):
        return None
    region = (viewport.left + 1250, viewport.top + 200,
              viewport.left + 1400, viewport.top + 340)
    point, _ = match_template(image, resource_path('assets/beast_stamina_close_live.png'),
                              0.985, (1440, 2560), region)
    return point


def beast_replenish_items(required, read_pair, begin, confirm, tap, stopped):
    """Use at most three restore-10 items, one durable transaction at a time.

    read_pair waits for two independently recognised identical observations;
    after an unacknowledged tap this function never issues another input.
    """
    current = read_pair(lambda observation: True)
    for _ in range(3):
        if stopped() or current is None:
            return False
        point, observation = current
        inventory, stamina = observation
        if stamina >= required:
            return True
        if inventory < 1:
            return False
        token = begin(observation, observation)
        if stopped():
            return False
        tap(point)
        current = read_pair(lambda value: value[0] == inventory - 1 and value[1] >= stamina + 10, receipt=True)
        if current is None or stopped():
            return False
        receipt = current[1]
        if not confirm(token, receipt, receipt):
            return False
        if receipt[1] >= required:
            return True
        # The same fresh receipt frames establish title, unique green Use,
        # exact +10 item icon and inventory. Reuse their point/observations for
        # the next transaction without a redundant screenshot or OCR pass.
    return bool(current and not stopped() and current[1][1] >= required)


def beast_replenish_batch(required, read_pair, begin, confirm, tap, stopped):
    """Journal once, tap the freshly verified normal +10 button three times."""
    current = read_pair(lambda observation: True)
    if stopped() or current is None:
        return False
    point, observation = current
    inventory, stamina = observation
    if stamina >= required:
        return True
    if inventory < 3 or stamina > 170:
        return False
    token = begin(observation, observation)
    for _ in range(3):
        if stopped():
            return False
        tap(point)
    if stopped():
        return False
    receipt = read_pair(lambda value: value[0] == inventory - 3 and value[1] >= stamina + 30,
                        receipt=True)
    if stopped() or receipt is None:
        return False
    result = receipt[1]
    return confirm(token, result, result) and result[1] >= required


def beast_replenish_fast_batch(point, begin, mark_sent, tap, stopped, confirm_use, *, uses=1,
                               on_use=lambda count: None, wait_between=lambda: False):
    """Use the item up to the requested count, checking the button is still free."""
    if not point or stopped():
        return None
    token = begin()
    for index in range(uses):
        if stopped() or not confirm_use(point) or stopped():
            return token if index else None
        tap(point)
        if index == 0:
            mark_sent(token)
        on_use(index + 1)
        if index + 1 < uses and wait_between():
            return token
    return token


def beast_fast_batch_receipt(before, first, second):
    """Accept exactly four proven uses; any lesser/unknown effect stays pending."""
    if not before or not first or first != second:
        return False
    consumed = before[0] - first[0]
    return consumed == 4 and first[1] == before[1] + consumed * 10


def beast_unconfirmed_world_free(first, second, a, b, limit, match_world, network, stable):
    """A current free queue permits a new search, not replay of the old target."""
    return bool(a is not None and a == b and a.total > 0
                and 0 <= a.used < min(a.total, limit)
                and not network(first) and not network(second)
                and stable(match_world(first), match_world(second)))


def beast_reconcile_sent_item_overlay(first, second, entry, *, match_item,
                                      close_point, match_formation, network,
                                      stable, reserved, check_active, tap,
                                      capture, archive, stopped):
    """Archive an old sent batch as unknown without sending any use again.

    The caller holds the account lease and uses fresh frames for this account.
    Never use this for a prepared batch or while a dispatch reservation exists.
    """
    if (not entry or entry.get('mode') != 'fast' or entry.get('phase') != 'sent'
            or stopped() or reserved() or network(first) or network(second)):
        return False
    p1, p2 = match_item(first), match_item(second)
    c1, c2 = close_point(first), close_point(second)
    if not stable(p1, p2) or not stable(c1, c2):
        return False
    check_active()
    if stopped() or reserved():
        return False
    tap(c2)
    after1, after2 = capture(), capture()
    if (stopped() or reserved() or network(after1) or network(after2)
            or not stable(match_formation(after1), match_formation(after2))):
        return False
    check_active()
    if stopped() or reserved():
        return False
    archive(entry['id'])
    return True


def beast_reconcile_fast_item_world(first, second, entry, *, match_world, network,
                                    conflict, stable, reserved, pending_submission,
                                    check_active, archive_prepared, archive_sent, stopped):
    """Archive an interrupted batch after fresh world proof, without replaying it."""
    if (not entry or entry.get('mode') != 'fast'
            or entry.get('phase') not in ('prepared', 'sent')
            or stopped() or reserved() or pending_submission()
            or network(first) or network(second) or conflict(first) or conflict(second)
            or not stable(match_world(first), match_world(second))):
        return False
    check_active()
    if stopped() or reserved() or pending_submission():
        return False
    (archive_sent if entry['phase'] == 'sent' else archive_prepared)(entry['id'])
    return True


def beast_tap_stamina_four(target, point):
    """Send four taps in one shell invocation, 100 ms apart."""
    x, y = int(point[0]), int(point[1])
    command = f'input tap {x} {y}; sleep 0.1; input tap {x} {y}; sleep 0.1; input tap {x} {y}; sleep 0.1; input tap {x} {y}'
    target.shell([command], timeout=10)


def beast_recover_receipt_stamina(first, second, *, match_item, observation, network,
                                   stable, reserved, pending, check_active, begin,
                                   mark_sent, complete, tap, capture, close_point,
                                   match_world, match_formation, stopped,
                                   diagnose=lambda reason: None, uses=1,
                                   on_use=lambda count: None, wait_between=lambda: False,
                                   fast_batch_tap=None):
    """Handle a verified item overlay without ever retrying the dispatch.

    None means no recognizable overlay; False means stop; True resumes receipt
    observation. A durable item guard survives any interrupted/unknown action.
    """
    p1, p2 = match_item(first), match_item(second)
    if not p1 and not p2:
        return None
    # The first pair can straddle the transition into the overlay.  Only
    # reacquire evidence before beginning the durable item transaction; once
    # any input is possible, every uncertain acknowledgement remains final.
    for attempt in range(4):
        if stopped():
            diagnose('停止信号')
            return False
        if network(first) or network(second):
            diagnose('网络弹窗')
            return False
        if not reserved() or pending():
            diagnose('出征预留或道具未决状态不符')
            return False
        if stable(p1, p2):
            break
        if attempt == 3:
            diagnose('体力页位置双帧不一致')
            return False
        first, second = capture(), capture()
        p1, p2 = match_item(first), match_item(second)
    if stopped() or not reserved() or pending():
        diagnose('输入前停止或账本状态改变')
        return False
    check_active()
    def confirm_green_use(point):
        # A use animation can briefly cover the item button. Recheck fresh
        # frames without replaying any input while that animation settles.
        for attempt in range(4):
            frame = capture()
            if frame is not None and not network(frame) and stable(match_item(frame), point):
                return True
            if stopped() or (attempt < 3 and wait_between()):
                break
        diagnose('体力使用按钮未恢复；不重复已发送的点击')
        return False
    if fast_batch_tap is not None:
        # The initial pair already proved the item button. Persist a sent guard
        # before the one ADB batch so a lost response cannot replay the taps.
        token = begin()
        mark_sent(token)
        check_active()
        if stopped():
            diagnose('补体输入中断，保留道具未决')
            return False
        fast_batch_tap(p2)
        on_use(4)
    else:
        token = beast_replenish_fast_batch(
            p2, begin, mark_sent,
            lambda point: (check_active(), tap(point)), stopped, confirm_green_use, uses=uses,
            on_use=on_use, wait_between=wait_between)
    if not token or stopped():
        diagnose('补体输入中断，保留道具未决')
        return False
    # The use animation can temporarily obscure the close control. Read a
    # bounded number of fresh pairs before the one allowed close input; never
    # repeat any of the four already-sent item uses.
    c2 = None
    for _ in range(4):
        if stopped():
            diagnose('补体后停止，保留道具未决')
            return False
        first_close, second_close = capture(), capture()
        if network(first_close) or network(second_close):
            diagnose('补体后网络弹窗，保留道具未决')
            return False
        c1, c2 = close_point(first_close), close_point(second_close)
        if stable(c1, c2):
            break
    else:
        diagnose('补体后关闭按钮未就绪，保留道具未决')
        return False
    check_active()
    if stopped():
        return False
    tap(c2)
    # Closing is also sent once only. A stale animation frame must not force
    # a worker restart or a repeated close, so retry reads rather than input.
    for _ in range(4):
        if stopped():
            diagnose('关闭后停止，保留道具未决')
            return False
        after1, after2 = capture(), capture()
        if network(after1) or network(after2):
            diagnose('关闭后网络弹窗，保留道具未决')
            return False
        world = stable(match_world(after1), match_world(after2))
        formation = stable(match_formation(after1), match_formation(after2))
        if world or formation:
            break
    else:
        diagnose('关闭后页面未就绪，保留道具未决')
        return False
    if not reserved():
        diagnose('关闭后出征记录发生变化，保留道具未决')
        return False
    check_active()
    if stopped():
        return False
    complete(token)
    # The caller may continue from a formation only in the same live dispatch
    # episode that just opened this verified insufficient-stamina overlay.
    # Recovery of a pre-existing reservation must never replay that input.
    return True if world else 'formation_after_stamina'


def beast_resume_dispatch_after_stamina(point, *, stopped, check_active, reserve, tap, archive):
    """Resume the same live formation after its verified stamina dialog closes."""
    if not point or stopped():
        return False
    check_active()
    if stopped():
        return False
    reserve()
    tap(point)
    archive()
    return True


def beast_shield_plus_marker(identity: str) -> Path:
    digest = hashlib.sha256(identity.encode("utf-8")).hexdigest()
    return CONFIG_DIR / f"beast_single_shield_plus_pending_{digest}.marker"


def beast_shield_plus_pending(identity: str) -> bool:
    try:
        beast_shield_plus_marker(identity).stat()
        return True
    except FileNotFoundError:
        return False


def beast_shield_plus_claim(identity: str) -> bool:
    """Durably record an input before sending it; existing records fail closed."""
    path = beast_shield_plus_marker(identity)
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        return False
    with os.fdopen(fd, "wb") as marker:
        marker.write(b"single-shield-plus-pending-v1\n")
        marker.flush()
        os.fsync(marker.fileno())
    return True


def beast_shield_plus_confirm(identity: str) -> None:
    beast_shield_plus_marker(identity).unlink()


def beast_should_use_cached_six_route(completed_cycles, loaded_route, limit, mode, troops, race_pause, *, fast_mode=False):
    """Use the cache after the current world frame, even following recovery."""
    return bool((completed_cycles or loaded_route) and (limit == 6 or fast_mode) and mode != 'formation'
                and troops == (1, 0, 0) and not race_pause)


def beast_account2_route_trace(identity, report, *, clock=time.monotonic):
    """Collect timing only for MuMu 2 without recording its Android identity."""
    parts = identity.split(':') if isinstance(identity, str) else ()
    if len(parts) != 4 or parts[:3] != ['mumu', '2', 'android'] or not parts[3]:
        return None
    started = clock()
    marks = []

    def mark(stage):
        try:
            marks.append((stage, clock() - started))
        except Exception:
            pass  # Diagnostics must not interrupt the game flow.

    def finish():
        if marks:
            try:
                report('快速链耗时：' + ' '.join(f'{stage}={elapsed:.3f}s' for stage, elapsed in marks))
            except Exception:
                pass  # Diagnostics cannot mask an input failure.

    return mark, finish


def beast_cached_six_navigation(image, positions, target, stop_event, *, select_three=False,
                                page_wait_seconds=1.0, trace=None):
    """Navigate once with first-cycle coordinates; never replay an input."""
    if page_wait_seconds not in (0.1, 1.0, 2.0, 3.0, 4.0):
        raise ValueError('unsupported Beast page transition delay')
    names = ['world_search', 'beast_card', 'selector_search', 'rally_button']
    if select_three:
        names.append('three_minutes')
    names.append('launch')
    points = [(name, positions.cached_point(name, image)) for name in names]
    if any(point is None for _, point in points):
        return None  # No input was sent; the normal recognition path may run.
    for name, point in points:
        if stop_event.is_set():
            return False
        target.check_active()
        if trace:
            trace(name + ':before')
        target.tap(*point)
        if trace:
            trace(name + ':returned')
        # Give each navigation transition time to render; this is not proof
        # that the target page has loaded, and stopping interrupts the wait.
        if stop_event.wait(page_wait_seconds):
            return False
    return True


def beast_fast_single_shield_dispatch(identity: str, cost: int, plus: tuple[int, int],
                                      dispatch: tuple[int, int], target: Any, stop_event: Any,
                                      *, clear: tuple[int, int] | None = None,
                                      estimated: bool = False, trace=None) -> bool:
    """Record both possible inputs before sending either; never retry on ambiguity."""
    target.check_active()
    if not beast_shield_plus_claim(identity):
        return False
    if estimated:
        reserve_beast_rally_stamina(identity, cost, estimated=True)
    else:
        reserve_beast_rally_stamina(identity, cost)
    target.check_active()
    if clear:
        if trace:
            trace('withdraw:before')
        target.tap(*clear)
        if trace:
            trace('withdraw:returned')
        if stop_event.is_set():
            return False
    if trace:
        trace('shield_plus:before')
    target.tap(*plus)
    if trace:
        trace('shield_plus:returned')
    if stop_event.wait(0.05):
        return False
    if trace:
        trace('dispatch:before')
    target.tap(*dispatch)
    if trace:
        trace('dispatch:returned')
    return True


def beast_shield_plus_receipt(first: Image.Image, second: Image.Image, read_state: Callable,
                               read_controls: Callable, network_visible: Callable) -> bool:
    """Only a fresh, unobscured matching pair may settle an interrupted click."""
    if network_visible(first) or network_visible(second):
        return False
    a, b = read_state(first), read_state(second)
    if not a or not b or a[:2] != (1, 1) or b[:2] != (1, 1):
        return False
    first_control, second_control = read_controls(first), read_controls(second)
    return bool(first_control and first_control == second_control)


def beast_cleared_first_shield_plus(image: Image.Image, read_state: Callable) -> tuple[int, int] | None:
    """Prove the cleared shield row and its visible blue plus before one tap."""
    state = read_state(image)
    if not state or state[:2] != (0, 0):
        return None
    from wjdr_beast_hunt import beast_first_visible_shield_row
    row_index = beast_first_visible_shield_row(image)
    if row_index is None:
        return None
    row_offset = row_index * 280
    viewport = content_viewport(image)
    frame = image.crop((viewport.left, viewport.top, viewport.right, viewport.bottom)).resize((1440, 2560)).convert("RGB")

    def sample(x: int, y: int) -> tuple[float, ...]:
        return tuple(ImageStat.Stat(frame.crop((x - 2, y - 2, x + 3, y + 3))).mean)

    for x, y in ((1317, 1434), (1317, 1414), (1297, 1434), (1337, 1434), (1317, 1454)):
        if min(sample(x, y + row_offset)) < 225:
            return None
    for x, y in ((1285, 1400), (1350, 1400), (1285, 1467), (1350, 1467)):
        red, green, blue = sample(x, y + row_offset)
        if not (red < 120 and green > 115 and blue > 200 and blue > green + 40 and green > red + 35):
            return None
    return map_content_point((1317, 1434 + row_offset), (1440, 2560), image)






from wjdr_scoreboard_ui import ScoreboardUI


class MainWindow(FrontendLayout, ScoreboardUI, ScheduleUI, QMainWindow):
    def __init__(
        self,
        preferred_device: str | None,
        auto_help: bool,
        all_auto_help: bool,
        auto_red_packet: bool,
        all_auto_red_packet: bool,
        auto_daily: bool = False,
        all_auto_daily: bool = False,
        auto_beast_rally: bool = False,
        all_auto_beast_rally: bool = False,
        interval_override: float | None = None,
    ) -> None:
        super().__init__()
        prepare_storage()
        self.preferred_device = preferred_device
        self.auto_help_requested = auto_help
        self.all_auto_help_requested = all_auto_help
        self.auto_red_packet_requested = auto_red_packet
        self.all_auto_red_packet_requested = all_auto_red_packet
        self.auto_daily_requested = auto_daily
        self.all_auto_daily_requested = all_auto_daily
        self.auto_beast_rally_requested = auto_beast_rally
        from wjdr_beast_hunt import consume_beast_test_cycle_limit
        self._initial_beast_test_cycles = consume_beast_test_cycle_limit(os.environ, auto_beast_rally)
        from wjdr_beast_hunt import consume_beast_search_race_pause
        self._initial_beast_search_pause = consume_beast_search_race_pause(os.environ, auto_beast_rally)
        self.all_auto_beast_rally_requested = all_auto_beast_rally
        self.adb: MuMuADB | None = None
        self.devices: list[str] = []
        self.current_image: Image.Image | None = None
        self.selected_point: tuple[int, int] | None = None
        self.selected_source_size: tuple[int, int] | None = None
        self.selected_region: tuple[int, int, int, int] | None = None
        self.stop_event = threading.Event()
        self.closing = threading.Event()
        self.worker: threading.Thread | None = None
        self.started_at = 0.0
        self.tasks = self._load_tasks()
        self.active_steps: list[dict[str, Any]] = []
        self.schedule_path = schedules.SCHEDULE_FILE
        self._schedule_checking = False
        self.signals = UiSignals()
        self._connect_signals()
        self.setWindowTitle(f"{APP_NAME} {APP_VERSION}")
        icon = resource_path("app_icon.svg")
        if icon.is_file():
            self.setWindowIcon(QIcon(str(icon)))
        self.resize(1280, 840)
        self.setMinimumSize(1080, 720)
        self._build_ui()
        if interval_override is not None:
            self.interval_spin.setValue(max(self.interval_spin.minimum(), min(interval_override, self.interval_spin.maximum())))
            self.red_packet_interval_spin.setValue(
                max(self.red_packet_interval_spin.minimum(), min(interval_override, self.red_packet_interval_spin.maximum()))
            )
            self.daily_interval_spin.setValue(
                max(self.daily_interval_spin.minimum(), min(interval_override, self.daily_interval_spin.maximum()))
            )
        self._apply_style()
        self._refresh_templates()
        self._refresh_tasks()
        self._load_log_tail()
        threading.Thread(target=self._hotkey_loop, daemon=True).start()
        self._run_async(self._connect_job)
        self.schedule_timer = QTimer(self)
        self.schedule_timer.timeout.connect(self._schedule_tick)
        self.schedule_timer.start(200)

    def _connect_signals(self) -> None:
        self.signals.schedule_verified.connect(self._schedule_verified)
        self.signals.log.connect(self._append_log)
        self.signals.status.connect(self._set_status)
        self.signals.devices.connect(self._apply_devices)
        self.signals.image.connect(self._apply_image)
        self.signals.running.connect(self._set_running)
        self.signals.clicks.connect(lambda count: self.click_count.setText(str(count)))
        self.signals.red_packet_state.connect(lambda text: self.red_packet_state_label.setText(text))
        self.signals.daily_task_state.connect(lambda text: self.daily_task_state_label.setText(text))
        self.signals.beast_rally_state.connect(lambda text: self.beast_rally_state_label.setText(text))
        self.signals.score_ocr.connect(self._score_show_ocr)
        self.signals.alert.connect(self._show_alert)


    def _run_async(self, callback: Callable[[], None]) -> None:
        threading.Thread(target=callback, daemon=True).start()

    def log(self, message: str) -> None:
        device = self.adb.device if self.adb and self.adb.device else "未绑定"
        self._log_for_device(device, message)

    def _log_for_device(self, device: str, message: str) -> None:
        stamp = time.strftime("%H:%M:%S")
        self.signals.log.emit(f"[{stamp}] [{device}] {message}")

    @staticmethod
    def _page_label(page: AlliancePage) -> str:
        return {
            AlliancePage.ALL_HELP_READY: "联盟互助 · 可全部帮助",
            AlliancePage.MUTUAL_HELP: "联盟互助 · 空页",
            AlliancePage.ALLIANCE_HOME: "联盟主页",
            AlliancePage.CITY: "主城 / 世界地图",
            AlliancePage.UNKNOWN: "未知页面",
        }[page]

    @staticmethod
    def _red_packet_page_label(state: RedPacketState) -> str:
        return {
            RedPacketState.MARKER: "红包浮标",
            RedPacketState.CHAT_ENTRY: "主城聊天入口",
            RedPacketState.CHAT_PANEL: "聊天面板",
            RedPacketState.ALLIANCE_CHAT: "联盟频道",
            RedPacketState.FURNACE_PACKET: "熔炉升级红包卡",
            RedPacketState.FURNACE_PACKET_CLAIMED: "熔炉升级红包（已领取）",
            RedPacketState.FURNACE_DETAIL: "熔炉红包详情",
            RedPacketState.DETAIL_OPEN_READY: "熔炉红包可开启",
            RedPacketState.CLAIM_RESULT_READY: "红包领取结果",
            RedPacketState.UNKNOWN: "未知页面",
        }[state]

    @staticmethod
    def _daily_task_page_label(state: DailyTaskState) -> str:
        labels = {
            DailyTaskState.CITY_ENTRY: "主城每日任务入口",
            DailyTaskState.DAILY_TAB_READY: "任务页已打开，可切换到每日任务标签",
            DailyTaskState.DAILY_PAGE: "每日任务页",
            DailyTaskState.DAILY_LOGIN_COMPLETED: "每日登录已领取或无可领按钮",
            DailyTaskState.CLAIM_READY: "每日登录 (1/1) 可领取",
            DailyTaskState.TASK_CLAIM_READY: "每日任务奖励可领取",
            DailyTaskState.REWARD_RESULT_READY: "每日任务奖励结算页",
            DailyTaskState.CHEST_RESULT_READY: "活跃度宝箱内容页",
            DailyTaskState.UNKNOWN: "未知页面 / 弹窗",
        }
        # The backend can add this safety state independently of a desktop
        # release.  ``getattr`` keeps an older backend importable while still
        # rendering the stricter state as soon as it is available.
        blocked_state = getattr(DailyTaskState, "BLOCKED", None)
        if blocked_state is not None:
            labels[blocked_state] = "付费 / 遮挡页面"
        return labels.get(state, "未允许的页面")

    def _append_log(self, line: str) -> None:
        device = self.adb.device if self.adb else None
        if not device or f"[{device}]" in line or "[未绑定]" in line:
            self.log_edit.append(line)
        try:
            with LOG_FILE.open("a", encoding="utf-8") as handle:
                handle.write(line + "\n")
        except OSError:
            pass

    def _load_log_tail(self) -> None:
        try:
            device = self.adb.device if self.adb else None
            # Read only a bounded tail; a long-running multi-device installation
            # must not load the complete shared log into each window.
            with LOG_FILE.open("rb") as handle:
                handle.seek(0, 2)
                handle.seek(max(0, handle.tell() - 256_000))
                lines = handle.read().decode("utf-8", errors="replace").splitlines()
            lines = [line for line in lines if not device or f"[{device}]" in line][-200:]
            self.log_edit.setPlainText("\n".join(lines))
        except OSError:
            pass

    def _set_status(self, text: str, kind: str) -> None:
        self.status_pill.setText(text)
        colors = {
            "ready": ("#E7F8F1", "#11865B"),
            "busy": ("#EAF1FF", "#275FBF"),
            "error": ("#FDECEE", "#B63B4A"),
            "idle": ("#F1F4F8", "#65738A"),
        }
        bg, fg = colors.get(kind, colors["idle"])
        self.status_pill.setStyleSheet(f"background:{bg};color:{fg};border-radius:15px;padding:8px 12px;font-weight:700;")

    def _set_running(self, running: bool, text: str) -> None:
        self.scan_button.setEnabled(not running)
        self.start_button.setEnabled(not running)
        self.red_packet_start_button.setEnabled(not running)
        self.daily_task_start_button.setEnabled(not running)
        self.beast_rally_start_button.setEnabled(not running)
        self.signals.status.emit(f"●  {text}", "busy" if running else "ready")
        if running:
            self.started_at = time.monotonic()
            self.runtime_timer.start(1000)
        else:
            self.runtime_timer.stop()

    def _show_alert(self, title: str, message: str) -> None:
        QMessageBox.warning(self, title, message)

    def _connect_job(self) -> None:
        if self.worker and self.worker.is_alive():
            self.log("当前手机正在运行，保持绑定连接；可用多手机窗口打开其他设备。")
            return
        if getattr(self, "_connecting", False):
            return
        self._connecting = True
        try:
            self.signals.status.emit("●  正在扫描", "busy")
            adb = MuMuADB()
            preferred = self.adb.device if self.adb and self.adb.device else self.preferred_device
            devices = adb.connect(preferred, allow_unavailable=True)
            if devices:
                with ThreadPoolExecutor(max_workers=min(8, len(devices))) as executor:
                    summaries = list(executor.map(adb.device_summary, devices))
            else:
                summaries = []
            self._discovery_adb = adb
            self.adb = adb if adb.device else None
            self.signals.devices.emit(summaries, adb.device)
            if adb.device:
                self.log(f"MuMu 连接成功，共发现 {len(devices)} 个运行中实例。")
                self._capture_job()
            else:
                self.log(f"原绑定实例 {preferred} 已离线；发现 {len(devices)} 个在线实例，请手动选择。")
        except Exception as exc:
            self.signals.status.emit("●  连接失败", "error")
            self.log(str(exc))
            self.signals.alert.emit(APP_NAME, str(exc))
        finally:
            self._connecting = False

    def _apply_devices(self, summaries: list[dict[str, Any]], selected: str) -> None:
        self.devices = [item["device"] for item in summaries]
        self.device_combo.blockSignals(True)
        self.device_combo.clear()
        selected_index = 0
        if not selected:
            self.device_combo.addItem("原绑定实例已离线，请选择在线实例", None)
        for index, item in enumerate(summaries):
            label = f"#{item['index']}  {item['name']}   ·   {item['device']}"
            self.device_combo.addItem(label, item)
            if item["device"] == selected:
                selected_index = index + (0 if selected else 1)
        self.device_combo.setCurrentIndex(selected_index)
        self.device_combo.blockSignals(False)
        self._show_device_info(self.device_combo.currentData())
        self._load_log_tail()
        if not selected:
            self.current_image = None
            self.selected_point = self.selected_region = self.selected_source_size = None
            self.screenshot.set_pil_image(Image.new("RGB", (720, 1280), "#E8EDF5"))
            self.signals.status.emit("●  请选择在线实例", "error")
            return
        self.signals.status.emit("●  已就绪", "ready")
        if self.all_auto_daily_requested:
            self.all_auto_daily_requested = False
            QTimer.singleShot(250, lambda: self._start_all_instances("daily"))
        elif self.all_auto_beast_rally_requested:
            self.all_auto_beast_rally_requested = False
            QTimer.singleShot(250, lambda: self._start_all_instances("beast_rally"))
        elif self.all_auto_red_packet_requested:
            self.all_auto_red_packet_requested = False
            QTimer.singleShot(250, lambda: self._start_all_instances("red_packet"))
        elif self.all_auto_help_requested:
            self.all_auto_help_requested = False
            QTimer.singleShot(250, self._start_all_instances)
        elif self.auto_daily_requested:
            self.auto_daily_requested = False
            QTimer.singleShot(250, self._start_daily_rewards_flow)
        elif self.auto_beast_rally_requested:
            self.auto_beast_rally_requested = False
            QTimer.singleShot(250, self._start_beast_rally_flow)
        elif self.auto_red_packet_requested:
            self.auto_red_packet_requested = False
            QTimer.singleShot(250, self._start_red_packet_flow)
        elif self.auto_help_requested:
            self.auto_help_requested = False
            QTimer.singleShot(250, self._start_help_preset)

    def _show_device_info(self, item: dict[str, Any] | None) -> None:
        if not item:
            self.instance_name.setText("未选择在线实例")
            self.instance_meta.setText("请从上方列表选择")
            self.instance_state.setText("未连接")
            self.setWindowTitle(f"{APP_NAME} {APP_VERSION} · 未绑定")
            self._update_mining_level_button(None)
            self._update_beast_rally_settings(None)
            return
        self.instance_name.setText(f"#{item['index']}  {item['name']}")
        self.instance_meta.setText(f"ADB {item['device']}   ·   {item['resolution']}")
        self.instance_state.setText(item["state"])
        self.setWindowTitle(f"{APP_NAME} {APP_VERSION} · #{item['index']} · {item['device']}")
        self._update_mining_level_button(item)
        self._update_beast_rally_settings(item)

    def _mining_identity_for_item(self, item: dict[str, Any] | None) -> str | None:
        if not item:
            return None
        identity = str(item.get("identity") or "").strip()
        if identity:
            return identity
        if self.adb and item.get("device"):
            return self.adb.device_identity(str(item["device"]))
        return None

    @staticmethod
    def _masked_account_label(identity: str) -> str:
        suffix = identity.rsplit(":", 1)[-1][-6:]
        return f"账号 …{suffix}"

    def _update_mining_level_button(self, item: dict[str, Any] | None) -> None:
        identity = self._mining_identity_for_item(item)
        if not identity:
            self.mining_level_button.setText("设置采矿策略")
            self.mining_level_button.setToolTip("")
            self.mining_level_button.setEnabled(False)
            self.mining_profile_context.setText("选择在线 MuMu 账号后可配置")
            return
        profile = load_mining_level_profile(identity)
        if profile.mode == "manual":
            summary = f"手动采矿 Lv.{profile.manual_level}"
        else:
            summary = "自动识别采矿等级"
        self.mining_level_button.setText(summary)
        self.mining_profile_context.setText(
            f"{self._masked_account_label(identity)} · 设置仅作用于当前账号"
        )
        self.mining_level_button.setToolTip(
            f"{self._masked_account_label(identity)}；点击修改该账号的独立采矿设置"
        )
        self.mining_level_button.setEnabled(True)

    def _open_mining_level_settings(self) -> None:
        item = self.device_combo.currentData()
        identity = self._mining_identity_for_item(item)
        if not item or not identity:
            QMessageBox.information(self, APP_NAME, "请先选择一个在线的 MuMu 账号。")
            return
        dialog = MiningLevelSettingsDialog(
            self._masked_account_label(identity),
            str(item["device"]),
            load_mining_level_profile(identity),
            self,
        )
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        profile = dialog.profile()
        save_mining_level_profile(identity, profile)
        self._update_mining_level_button(item)
        if profile.mode == "manual":
            self.log(
                f"{self._masked_account_label(identity)} 已保存手动采矿 Lv.{profile.manual_level}；"
                "每日任务将跳过地球识图。"
            )
        else:
            self.log(
                f"{self._masked_account_label(identity)} 已保存自动采矿识别；"
                "每日任务将使用地球/小房子/绿色城堡判级。"
            )

    def _update_beast_rally_settings(self, item: dict[str, Any] | None) -> None:
        identity = self._mining_identity_for_item(item)
        if not identity:
            self.beast_rally_settings_button.setText("设置巨兽参数")
            self.beast_rally_settings_button.setToolTip("")
            self.beast_rally_settings_button.setEnabled(False)
            self.beast_rally_profile_context.setText("选择在线 MuMu 账号后可配置")
            if hasattr(self, "beast_rally_profile_summary"):
                self.beast_rally_profile_summary.setText("等级 8 · 体力不限 · 今日 0")
            return
        profile = load_beast_rally_profile(identity)
        spent = load_beast_rally_stamina_spent(identity)
        limit = "不限" if profile.run_mode == 'fast' or profile.stamina_limit == 0 else str(profile.stamina_limit)
        self.beast_rally_settings_button.setText("修改巨兽参数")
        self.beast_rally_profile_context.setText(
            f"{self._masked_account_label(identity)} · 设置仅作用于当前账号"
        )
        self.beast_rally_settings_button.setToolTip(
            f"{self._masked_account_label(identity)}；点击修改该账号的等级、兵力、编组和体力上限"
        )
        self.beast_rally_settings_button.setEnabled(True)
        if hasattr(self, "beast_rally_profile_summary"):
            self.beast_rally_profile_summary.setText(
                f"{profile.beast_level}级 · " + (f"兵力 {profile.shield_count}/{profile.spear_count}/{profile.bow_count}" if profile.troop_mode == 'manual' else f"编组 {profile.formation_name}") + f" · 同时集结 {profile.max_concurrent_rallies} · {'极速' if profile.run_mode == 'fast' else '普通'}模式 · 体力上限 {limit} · " + ("不记体力账" if profile.run_mode == 'fast' else f"今日 {spent}")
            )

    def _open_beast_rally_settings(self) -> None:
        item = self.device_combo.currentData()
        identity = self._mining_identity_for_item(item)
        if not item or not identity:
            QMessageBox.information(self, APP_NAME, "请先选择一个在线的 MuMu 账号。")
            return
        dialog = BeastRallySettingsDialog(
            self._masked_account_label(identity),
            str(item["device"]),
            load_beast_rally_profile(identity),
            load_beast_rally_stamina_spent(identity),
            self,
            uncertain_today=load_beast_rally_stamina_uncertain(identity),
        )
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        profile = dialog.profile()
        save_beast_rally_profile(identity, profile)
        self._update_beast_rally_settings(item)
        limit = "不限" if profile.stamina_limit == 0 else str(profile.stamina_limit)
        self.log(
            f"{self._masked_account_label(identity)} 已保存冰原巨兽 Lv.{profile.beast_level}；"
            f"每日体力消耗上限 {limit}。"
        )
    def _device_changed(self, index: int) -> None:
        if index < 0:
            return
        item = self.device_combo.itemData(index)
        if not item:
            if self.adb:
                current = next((i for i in range(self.device_combo.count())
                                if (self.device_combo.itemData(i) or {}).get("device") == self.adb.device), 0)
                self.device_combo.blockSignals(True)
                self.device_combo.setCurrentIndex(current)
                self.device_combo.blockSignals(False)
            return
        if not self.adb:
            if getattr(self, "_connecting", False) or not getattr(self, "_discovery_adb", None):
                self.device_combo.blockSignals(True)
                self.device_combo.setCurrentIndex(0)
                self.device_combo.blockSignals(False)
                return
            self.adb = self._discovery_adb
        if getattr(self, "_connecting", False):
            current = next((i for i in range(self.device_combo.count())
                            if (self.device_combo.itemData(i) or {}).get("device") == self.adb.device), 0)
            self.device_combo.blockSignals(True)
            self.device_combo.setCurrentIndex(current)
            self.device_combo.blockSignals(False)
            return
        if self.worker and self.worker.is_alive():
            current = next((i for i in range(self.device_combo.count()) if (self.device_combo.itemData(i) or {}).get("device") == self.adb.device), 0)
            self.device_combo.blockSignals(True)
            self.device_combo.setCurrentIndex(current)
            self.device_combo.blockSignals(False)
            QMessageBox.information(self, APP_NAME, "当前任务正在运行。请用“独立窗口”控制另一实例。")
            return
        self.adb.set_device(item["device"])
        self.preferred_device = item["device"]
        self._show_device_info(item)
        self.current_image = None
        self.selected_point = self.selected_region = self.selected_source_size = None
        self.screenshot.set_pil_image(Image.new("RGB", (720, 1280), "#E8EDF5"))
        self.point_label.setText("正在读取当前手机…")
        self.click_count.setText("0")
        self.runtime_label.setText("00:00:00")
        self._load_log_tail()
        self.log(f"当前窗口已绑定 {item['device']}。")
        self._run_async(self._capture_job)

    def _capture_job(self) -> None:
        try:
            if not self.adb:
                return
            device = self.adb.device
            image = self.adb.screenshot(device=device)
            self.signals.image.emit((device, image))
        except Exception as exc:
            self.log(f"截图失败：{exc}")

    def _apply_image(self, image: Image.Image) -> None:
        if isinstance(image, tuple):
            device, image = image
            if not self.adb or self.adb.device != device:
                return
        self.current_image = image
        self.screenshot.set_pil_image(image)

    def _launch_game_job(self) -> None:
        try:
            if not self.adb:
                raise RuntimeError("尚未连接 MuMu。")
            self.adb.launch_game()
            self.log("已启动或切回《无尽冬日》。")
            time.sleep(1.2)
            self._capture_job()
        except Exception as exc:
            self.log(str(exc))

    def _point_selected(self, x: int, y: int) -> None:
        if not self.current_image:
            return
        self.selected_point = (x, y)
        self.selected_source_size = self.current_image.size
        self.selected_region = None
        self.point_label.setText(f"已选坐标  {x}, {y}")
        self.fixed_label.setText(f"当前坐标：({x}, {y})  ·  {self.current_image.width}×{self.current_image.height}")

    def _region_selected(self, region: tuple[int, int, int, int]) -> None:
        if not self.current_image:
            return
        self.selected_region = region
        self.selected_point = ((region[0] + region[2]) // 2, (region[1] + region[3]) // 2)
        self.selected_source_size = self.current_image.size
        self.point_label.setText(f"已框选  {region[2] - region[0]}×{region[3] - region[1]}")

    def _save_template(self) -> None:
        if not self.current_image or not self.selected_region:
            QMessageBox.information(self, APP_NAME, "请先在实时画面上拖动框选一个按钮。")
            return
        name, ok = QInputDialog.getText(self, APP_NAME, "模板名称：")
        if not ok or not name.strip():
            return
        path = TEMPLATE_DIR / f"{clean_name(name)}.png"
        self.current_image.crop(self.selected_region).save(path, "PNG")
        path.with_suffix(".json").write_text(
            json.dumps({"screen_width": self.current_image.width, "screen_height": self.current_image.height}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        self._refresh_templates()
        self.template_combo.setCurrentText(path.name)
        self.log(f"已保存模板：{path.name}")

    def _refresh_templates(self) -> None:
        names = sorted(path.name for path in TEMPLATE_DIR.glob("*.png"))
        current = self.template_combo.currentText() if hasattr(self, "template_combo") else ""
        if hasattr(self, "template_combo"):
            self.template_combo.clear()
            self.template_combo.addItems(names)
            if current in names:
                self.template_combo.setCurrentText(current)
            elif BUILTIN_ALL_HELP_TEMPLATE_NAME in names:
                self.template_combo.setCurrentText(BUILTIN_ALL_HELP_TEMPLATE_NAME)
            elif BUILTIN_HELP_TEMPLATE_NAME in names:
                self.template_combo.setCurrentText(BUILTIN_HELP_TEMPLATE_NAME)

    def _start_help_preset(self) -> None:
        self.mode_combo.setCurrentIndex(0)
        self.template_combo.setCurrentText(BUILTIN_ALL_HELP_TEMPLATE_NAME)
        self.threshold_slider.setValue(max(88, self.threshold_slider.value()))
        self.guard_check.setChecked(True)
        self._start_alliance_help_flow()

    def _start_alliance_help_flow(self) -> None:
        """Start the guarded page-flow used by the one-click alliance preset."""
        if not self.adb:
            QMessageBox.warning(self, APP_NAME, "尚未连接 MuMu。")
            return
        required = [
            TEMPLATE_DIR / BUILTIN_ALL_HELP_TEMPLATE_NAME,
            resource_path(BUILTIN_MUTUAL_PAGE_TEMPLATE_ASSET),
            resource_path(BUILTIN_MUTUAL_ENTRY_TEMPLATE_ASSET),
            resource_path(BUILTIN_CITY_ALLIANCE_TEMPLATE_ASSET),
        ]
        if any(not path.is_file() for path in required):
            QMessageBox.warning(self, APP_NAME, "自动导航模板缺失，请重新解压或重新下载完整程序包。")
            return
        target = self.adb.clone_for_device()
        interval = self.interval_spin.value()
        duration = self.duration_spin.value()
        max_clicks = self.max_clicks_spin.value()
        threshold = max(0.88, self.threshold_slider.value() / 100)
        guard = self.guard_check.isChecked()

        def job() -> None:
            clicks, failures = 0, 0
            started = time.monotonic()
            last_tap_at = float("-inf")
            cached_point: tuple[int, int] | None = None
            cached_size: tuple[int, int] | None = None
            last_page: AlliancePage | None = None
            last_notice_key = ""
            last_notice_at = -30.0
            navigation_page: AlliancePage | None = None
            navigation_attempts = 0
            next_navigation_at = 0.0

            def notice(key: str, message: str, minimum_gap: float = 30.0) -> None:
                nonlocal last_notice_key, last_notice_at
                now = time.monotonic()
                if key != last_notice_key or now - last_notice_at >= minimum_gap:
                    self._log_for_device(target.device, message)
                    last_notice_key, last_notice_at = key, now

            self._log_for_device(
                target.device,
                f"开始自动导航 + 全部帮助：点击间隔 {interval:.1f} 秒；F8 可全局停止。",
            )
            while not self.stop_event.is_set():
                now = time.monotonic()
                if duration and now - started >= duration * 60:
                    self._log_for_device(target.device, "已达到运行时长。")
                    break
                if max_clicks and clicks >= max_clicks:
                    self._log_for_device(target.device, "已达到最多点击次数。")
                    break
                try:
                    if guard and not target.foreground_is_game():
                        cached_point = cached_size = None
                        notice("not-foreground", "游戏不在前台，本轮暂停。")
                    else:
                        image = target.screenshot()
                        page = detect_alliance_page(image, threshold)
                        if page.page != last_page:
                            self._log_for_device(target.device, f"页面识别：{self._page_label(page.page)}（分数 {page.score:.3f}）。")
                            last_page = page.page
                            navigation_page = None
                            navigation_attempts = 0
                        if page.page is AlliancePage.ALL_HELP_READY:
                            assert page.point is not None
                            if (
                                cached_point is None
                                or cached_size != image.size
                                or abs(cached_point[0] - page.point[0]) > 18
                                or abs(cached_point[1] - page.point[1]) > 18
                            ):
                                cached_point, cached_size = page.point, image.size
                                self._log_for_device(target.device, f"已记录全部帮助坐标 {cached_point}，分数 {page.score:.3f}。")
                            # The current screenshot has re-verified both the page title and
                            # the green button. Never tap a stale cache after either disappears.
                            if now - last_tap_at >= interval:
                                target.tap(*cached_point)
                                last_tap_at = time.monotonic()
                                clicks += 1
                                self.signals.clicks.emit(clicks)
                                if clicks == 1 or clicks % 20 == 0:
                                    self._log_for_device(target.device, f"已点击全部帮助 {cached_point}，累计 {clicks} 次。")
                        elif page.page is AlliancePage.MUTUAL_HELP:
                            cached_point = cached_size = None
                            notice("mutual-empty", "已在联盟互助页；当前没有“全部帮助”，原地等待。")
                        elif page.page in (AlliancePage.ALLIANCE_HOME, AlliancePage.CITY):
                            cached_point = cached_size = None
                            assert page.point is not None
                            if navigation_page is not page.page:
                                navigation_page, navigation_attempts, next_navigation_at = page.page, 0, 0.0
                            if now >= next_navigation_at:
                                if navigation_attempts < 3:
                                    destination = "联盟互助" if page.page is AlliancePage.ALLIANCE_HOME else "联盟"
                                    target.tap(*page.point)
                                    navigation_attempts += 1
                                    next_navigation_at = now + max(MAX_SINGLE_WAIT_SECONDS, interval)
                                    self._log_for_device(
                                        target.device,
                                        f"导航：点击{destination}入口 {page.point}（第 {navigation_attempts}/3 次）。",
                                    )
                                else:
                                    next_navigation_at = now + 30.0
                                    notice(
                                        f"navigation-stalled-{page.page.value}",
                                        "导航页面没有按预期切换，已暂停输入 30 秒；请检查游戏是否有弹窗或未加入联盟。",
                                        30.0,
                                    )
                        else:
                            cached_point = cached_size = None
                            notice("unknown", f"未识别为主城、联盟或联盟互助页（最高分 {page.score:.3f}），不执行点击。")
                    failures = 0
                except Exception as exc:
                    failures += 1
                    backoff = min(MAX_SINGLE_WAIT_SECONDS, max(interval, 0.25) * (2 ** min(failures, 4)))
                    self._log_for_device(target.device, f"本轮识别失败（{failures}）：{exc}；{backoff:.1f} 秒后安全重试。")
                    if self.stop_event.wait(backoff):
                        break
                    continue
                if self.stop_event.wait(interval):
                    break
            self._log_for_device(target.device, f"自动导航帮助已停止，共点击 {clicks} 次。")

        self._start_worker(target.device, job)

    def _start_beast_rally_flow(self) -> None:
        """Run the selected level with the account's chosen troop mode."""
        from wjdr_beast_hunt import beast_soldier_rows, beast_mixed_single_shield, match_hunt_formation, SingleBeastCycle, read_compact_rally_rows, GuardedBeastADB, CycleActionPositions
        from wjdr_beast_hunt import read_compact_capacity as read_beast_rally_collapsed_march_capacity
        from wjdr_beast_hunt import read_compact_marching_rows, only_joined_rallies, blue_pair_free, gathering_pair_free
        from wjdr_beast_hunt import match_same_target_conflict
        from wjdr_beast_hunt import read_concurrent_snapshot, confirms_new_concurrent_rally, concurrent_dispatch_allowed, ConcurrentLineTracker, ConcurrentRallySnapshot, read_compact_numeric_capacity
        from wjdr_beast_hunt import save_beast_route_coordinates, load_beast_route_coordinates
        from wjdr_backend import cancel_beast_rally_conflict_reservation
        if not self.adb:
            QMessageBox.warning(self, APP_NAME, "尚未连接 MuMu。")
            return
        beast_assets = (*BEAST_RALLY_BUILTIN_ASSETS, "assets/beast_rally_compact_march_title.png",
                        "assets/beast_rally_hunt_name_large.png", "assets/beast_rally_compact_marching_icon.png",
                        "assets/beast_same_target_warning.png", "assets/beast_same_target_cancel.png",
                        "assets/beast_soldier_types.png", "assets/beast_gathering_title.png",
                        "assets/beast_stamina_close_live.png")
        missing = [resource_path(asset) for asset in beast_assets if not resource_path(asset).is_file()]
        if missing:
            names = "、".join(path.name for path in missing)
            QMessageBox.warning(self, APP_NAME, f"巨兽集结识别素材缺失：{names}\n请重新解压完整程序包。")
            return

        target = self.adb.clone_for_device()
        identity = target.device_identity()
        from wjdr_beast_supervision import read_intent, InitialRecognitionTimeout
        try:
            previous_intent = read_intent(identity)
        except (OSError, ValueError) as exc:
            self.log(f"巨兽运行意图无法读取，未启动：{exc}")
            return
        previous_generation = previous_intent["generation"] if previous_intent else None
        try:
            profile = load_beast_rally_profile(identity, strict=True)
        except ValueError:
            QMessageBox.warning(self, APP_NAME, "巨兽出征配置无法读取或无效，请检查账号配置；未开始出征。")
            return
        wanted_troops = (profile.shield_count, profile.spear_count, profile.bow_count)
        troop_label = f"手动兵力 {wanted_troops}" if profile.troop_mode == "manual" else f"编组 {profile.formation_name}"
        threshold = 0.90
        target = GuardedBeastADB(target, self.stop_event,
                                 lambda text: self._log_for_device(target.device, text))
        initial_test_cycles = self._initial_beast_test_cycles
        self._initial_beast_test_cycles = 0
        initial_search_pause = self._initial_beast_search_pause
        self._initial_beast_search_pause = 0.0

        def job() -> None:
            # This callback starts only after _start_worker acquires the device
            # lease. An old dispatch may have crossed midnight; inspect the
            # account's complete persisted reservation before any game input.
            try:
                from wjdr_beast_supervision import has_unresolved_actions
                reconciliation_only = has_unresolved_actions(identity)
                old_reservation = load_beast_rally_stamina_reserved_any_day(identity)
                pending_submission_token = load_beast_rally_submitted_pending(identity)
            except (OSError, ValueError) as exc:
                self._log_for_device(target.device, f"体力账本无法确认，未执行游戏操作：{exc}")
                return
            if old_reservation and not reconciliation_only:
                self._log_for_device(target.device, f"存在未决出征体力 {old_reservation}（含跨日记录）；未执行游戏操作，保留预留。")
                return
            if old_reservation and pending_submission_token:
                try:
                    if self.stop_event.is_set() or load_beast_stamina_item_pending(identity) or not target.foreground_is_game():
                        raise ValueError('存在其他未决操作或游戏不在前台')
                    first, second = target.screenshot(), target.screenshot()
                    points = [match_beast_rally_world_search(frame, threshold)[0] for frame in (first, second)]
                    if (self.stop_event.is_set() or not all(points)
                            or abs(points[0][0] - points[1][0]) > 16 or abs(points[0][1] - points[1][1]) > 16
                            or any(daily_network_dialog_is_visible(frame, threshold) or match_same_target_conflict(frame)
                                   for frame in (first, second))):
                        raise ValueError('未确认稳定野外页面')
                    target.check_active()
                    if self.stop_event.is_set() or load_beast_stamina_item_pending(identity):
                        raise ValueError('操作状态已变化')
                    reconcile_beast_overlapping_dispatches(identity, old_reservation, pending_submission_token)
                    self._log_for_device(target.device, '两条旧出征均按结果未知归档；不重发，继续读取当前队列。')
                    old_reservation = 0
                    pending_submission_token = None
                    reconciliation_only = has_unresolved_actions(identity)
                except (OSError, ValueError) as exc:
                    self._log_for_device(target.device, f'两条旧出征暂不能安全恢复：{exc}；保留记录。')
                    return
            capture_latency = 0.0
            poll_interval = 0.10
            last_state_text = ""
            action_count = 0
            baseline_queue_states: tuple[bool, ...] | None = None
            baseline_march_capacity: tuple[int, int] | None = None
            search_race_pause = initial_search_pause
            race_evidence_frames = 0
            retry_target_requested = False
            target_conflicts = 0
            fast_select_three = False
            cached_route_checked = False
            recent_unconfirmed_dispatch = pending_submission_token is not None
            action_positions = CycleActionPositions()
            baseline_concurrent = None
            confirmed_dispatches = 0
            tracked_green = 0
            tracked_rallies = 0
            line_tracker = ConcurrentLineTracker()
            def archive_dispatch(cost: int, *, charge_session: bool = True) -> None:
                archive_beast_rally_unconfirmed_reservation(
                    identity, cost, record_uncertain=profile.run_mode != 'fast')

            def finish_item_batch(token: str) -> None:
                if profile.run_mode == 'fast':
                    update_beast_stamina_fast_batch(identity, token, complete=True)
                else:
                    archive_beast_stamina_fast_batch_uncertain(identity, token)

            def cycle_position(name: str, image: Image.Image, point: tuple[int, int]) -> tuple[int, int] | None:
                if completed_cycles == 0:
                    return action_positions.remember(name, image, point)
                cached = action_positions.reuse(name, image, point)
                # A worker may restart on the stamina overlay, finish that
                # dispatch, and only then see its first recognized world page.
                if not cached and name == 'world_search' and name not in action_positions.positions:
                    cached = action_positions.remember(name, image, point)
                # The freshly matched three-minute sheet can shift between cycles.
                if not cached and name == 'launch':
                    cached = action_positions.refresh_recognized(name, image, point)
                if not cached:
                    self._log_for_device(target.device, f"首轮位置 {name} 与当前页面不一致；零输入停止。")
                return cached

            def set_state(text: str) -> None:
                nonlocal last_state_text
                if text != last_state_text:
                    last_state_text = text
                    self.signals.beast_rally_state.emit(text)

            def capture() -> Image.Image:
                nonlocal capture_latency, poll_interval, race_evidence_frames
                started = time.monotonic()
                image = target.screenshot()
                if race_evidence_frames > 0:
                    race_evidence_frames -= 1
                    # Temporary user-coordinated race probe: central message
                    # band only, excludes account HUD and chat. Never recognition input.
                    folder = Path('evidence/milestone-180-target-race')
                    folder.mkdir(parents=True, exist_ok=True)
                    viewport = content_viewport(image)
                    normalized = image.crop((viewport.left,viewport.top,viewport.right,viewport.bottom)).resize((1440,2560))
                    normalized.crop((240,1000,1200,1420)).save(folder / f'race-{time.strftime("%H%M%S")}-{race_evidence_frames:02}.png')
                sample = time.monotonic() - started
                capture_latency = sample if capture_latency <= 0 else capture_latency * 0.75 + sample * 0.25
                poll_interval = min(MAX_SINGLE_WAIT_SECONDS, max(0.05, 0.06 + capture_latency * 0.08))
                return image

            def pause() -> bool:
                return self.stop_event.wait(poll_interval)

            def stable(first: tuple[int, int] | None, second: tuple[int, int] | None) -> bool:
                return bool(first and second) and abs(first[0] - second[0]) <= 16 and abs(first[1] - second[1]) <= 16

            def save_evidence(image: Image.Image, point: tuple[int, int] | None, label: str, note: str) -> None:
                """Persist only a tight account-free control/state crop."""
                try:
                    viewport = content_viewport(image)
                    x, y = point or (
                        viewport.left + viewport.width // 2,
                        viewport.top + viewport.height // 2,
                    )
                    half_width = min(260, max(100, viewport.width // 6))
                    half_height = min(100, max(55, viewport.height // 24))
                    box = (
                        max(viewport.left, x - half_width),
                        max(viewport.top, y - half_height),
                        min(viewport.right, x + half_width),
                        min(viewport.bottom, y + half_height),
                    )
                    directory = CONFIG_DIR / "evidence" / "beast_rally"
                    directory.mkdir(parents=True, exist_ok=True)
                    stamp = time.strftime("%Y%m%d-%H%M%S")
                    path = directory / f"{clean_name(label)}_{stamp}_{os.getpid()}_{time.time_ns()}.png"
                    image.crop(box).save(path, optimize=True)
                    prune_runtime_evidence(directory, 24)
                    with (directory / "run-notes.md").open("a", encoding="utf-8") as handle:
                        handle.write(f"- {time.strftime('%Y-%m-%d %H:%M:%S')} `{path.name}` — {note}\n")
                except OSError as exc:
                    self._log_for_device(target.device, f"巨兽集结留证失败：{exc}")

            def wait_for_double(
                label: str,
                matcher: Callable[[Image.Image], tuple[tuple[int, int] | None, Any]],
                timeout: float = AUTOMATION_STEP_TIMEOUT_SECONDS,
            ) -> tuple[Image.Image, tuple[int, int], Any] | None:
                """Use one fresh frame for routine cached navigation after cycle one."""
                deadline = time.monotonic() + bounded_step_timeout(timeout)
                routine = label in {
                    "确认橙色集结按钮", "确认发起集结页面", "确认3分钟已选中", "确认出征编组页面",
                    "确认搜索页", "确认冰原巨兽搜索页", "复核冰原巨兽卡片与搜索按钮", "确认手动兵力",
                    "复核出征配置与普通出征",
                } or label.startswith(("确认等级为 ", "确认等级已改为 ")) or (
                    label.startswith("确认第 ") and " 行兵力为 " in label
                )
                required = 1 if completed_cycles and routine else 2
                previous: tuple[int, int] | None = None
                streak = 0
                while not self.stop_event.is_set() and time.monotonic() < deadline:
                    image = capture()
                    if daily_network_dialog_is_visible(image, threshold):
                        set_state("ADB在线但游戏网络离线：零输入停止")
                        self._log_for_device(target.device, "巨兽集结检测到游戏网络/账号离线；未执行输入。")
                        return None
                    point, payload = matcher(image)
                    if point:
                        streak = streak + 1 if stable(point, previous) else 1
                        previous = point
                        set_state(f"{label}（{min(streak, required)}/{required}）")
                        if streak >= required:
                            return image, point, payload
                        # A positive first frame should be followed immediately
                        # by the second; poll delay is only for failed matches.
                        continue
                    else:
                        previous, streak = None, 0
                    if pause():
                        return None
                self._log_for_device(target.device, f"{label}未在 {bounded_step_timeout(timeout):.0f} 秒内完成{required}帧确认；零输入停止。")
                return None

            def match_world(image: Image.Image) -> tuple[tuple[int, int] | None, float]:
                return match_beast_rally_world_search(image, threshold)

            def match_wilderness_context(image: Image.Image) -> tuple[tuple[int, int] | None, float]:
                """Prove wilderness from the exact Town control even if Search is covered."""
                if match_daily_city_wilderness_entry(image, threshold)[0]:
                    return None, 0.0
                return match_daily_world_town_entry(image, threshold)

            def ensure_wilderness() -> tuple[Image.Image, tuple[int, int]] | None:
                """Recover from a reviewed target card or search drawer, then resume."""
                deadline = time.monotonic() + AUTOMATION_STEP_TIMEOUT_SECONDS
                prior_world = prior_city = None
                world_streak = city_streak = 0
                city_tapped = False
                backed_pages = set()
                world_required = 1 if completed_cycles else 2
                while not self.stop_event.is_set() and time.monotonic() < deadline:
                    image = capture()
                    if daily_network_dialog_is_visible(image, threshold):
                        set_state("游戏网络离线：零输入停止")
                        return None
                    world, _ = match_world(image)
                    city, _ = match_daily_city_wilderness_entry(image, threshold)
                    if world:
                        world_streak = world_streak + 1 if stable(world, prior_world) else 1
                        prior_world = world
                        city_streak = 0
                        required = 2 if city_tapped else world_required
                        set_state(f"确认野外与搜索按钮（{min(world_streak, required)}/{required}）")
                        if world_streak >= required:
                            return image, world
                    elif city and not city_tapped:
                        city_streak = city_streak + 1 if stable(city, prior_city) else 1
                        prior_city = city
                        world_streak = 0
                        set_state(f"确认城镇的野外入口（{min(city_streak, 2)}/2）")
                        if city_streak >= 2:
                            target.tap(*city)
                            city_tapped = True
                            self._log_for_device(target.device, f"点击双帧确认的野外入口 {city}。")
                            save_evidence(image, city, "enter_wilderness", "城镇页双帧确认后点击唯一野外入口。")
                    else:
                        prior_world = prior_city = None
                        world_streak = city_streak = 0
                        # Recovery is exception-only. A known target card can
                        # leave the drawer underneath, so send at most one
                        # Back per recognized page and require a fresh frame
                        # after each input. Never retry a possibly lost Back.
                        if not match_same_target_conflict(image):
                            card = match_beast_rally_open_button(image, threshold)[0]
                            drawer = None if card else match_beast_rally_search_drawer_without_level(image)
                            # The account has just left the Beast route; use a
                            # stricter threshold for this exceptional Back.
                            exploration = not card and not drawer and match_beast_exception_exploration_header(image)
                            alliance = None if card or drawer or exploration else detect_alliance_page(image, max(threshold, 0.98))
                            page = ('target_card' if card else ('search_drawer' if drawer else
                                    ('exploration' if exploration else
                                     ('alliance_home' if alliance and alliance.page is AlliancePage.ALLIANCE_HOME else None))))
                            if page and page not in backed_pages:
                                if self.stop_event.is_set():
                                    return None
                                target.check_active()
                                target.back()
                                # This GuardedBeastADB is local to the current
                                # account worker. Count each recovery episode
                                # once even if both card and drawer need Back.
                                if not backed_pages:
                                    previous_delay = getattr(target, 'beast_navigation_page_delay', 1.0)
                                    if previous_delay not in (1.0, 2.0, 3.0, 4.0):
                                        previous_delay = 1.0
                                    target.beast_navigation_page_delay = min(4.0, previous_delay + 1.0)
                                backed_pages.add(page)
                                label = {'target_card': '目标卡', 'search_drawer': '搜索抽屉',
                                          'alliance_home': '联盟主页', 'exploration': '探险地图'}[page]
                                self._log_for_device(target.device, f"异常恢复：退出已识别的{label}。")
                    if pause():
                        return None
                if not self.stop_event.is_set() and not city_tapped and not target.input_attempted:
                    raise InitialRecognitionTimeout("初始城镇或野外页面识别超时")
                self._log_for_device(target.device, "未能在单步时限内确认城镇野外入口或野外搜索按钮；已停止。")
                return None

            def selector_match(image: Image.Image) -> tuple[tuple[int, int] | None, BeastRallyState]:
                match = match_beast_rally_selector(image, threshold)
                return match.point, match.state

            def sheet_controls_match(image: Image.Image) -> tuple[tuple[int, int] | None, Any]:
                match = match_beast_rally_sheet_controls(image, threshold)
                return match.point, match

            def exact_sheet_match(image: Image.Image) -> tuple[tuple[int, int] | None, Any]:
                match = match_beast_rally_sheet(image, threshold)
                return match.point, match

            def formation_controls_match(image: Image.Image) -> tuple[tuple[int, int] | None, Any]:
                match = (match_hunt_formation(image) if profile.troop_mode == "formation"
                         else match_beast_rally_formation_controls(image, threshold))
                return match.point, match

            def exact_formation_match(image: Image.Image) -> tuple[tuple[int, int] | None, Any]:
                if profile.troop_mode == "formation":
                    match = match_hunt_formation(image, selected=True)
                    return match.point, match
                match = match_beast_rally_formation_controls(image, threshold)
                rows = beast_soldier_rows(image)
                if wanted_troops == (1, 0, 0):
                    single = beast_mixed_single_shield(image)
                    return (match.point if single and single[:2] == (1, 1) else None), match
                return (match.point if rows == wanted_troops else None), match

            def configure_single_shield() -> bool | tuple:
                """Edit proven troop rows once each; never touch saved formations."""
                if beast_shield_plus_pending(identity):
                    self._log_for_device(target.device, "盾兵加号存在未确认操作，停止以避免重复点击。")
                    return False
                initial = capture()
                if wanted_troops == (1, 0, 0):
                    second = capture() if not completed_cycles else initial
                    first_state = beast_mixed_single_shield(initial)
                    second_state = beast_mixed_single_shield(second)
                    if not first_state or first_state != second_state:
                        self._log_for_device(target.device, "多等级盾兵页面未能确认；未修改兵力、未出征。")
                        return False
                    # Cache only the first recognized layout. Later cycles use
                    # these account-local coordinates without OCR or pixel tests.
                    control = match_beast_rally_formation_controls(second, threshold)
                    dispatch_point = control.point
                    if not dispatch_point and second_state[:2] == (0, 0):
                        # The dispatch button is disabled and grey when all
                        # troops have been withdrawn, so the active-button
                        # template cannot recognize it yet. Its layout is fixed
                        # within this already recognized mixed-shield editor.
                        dispatch_point = map_content_point((1087, 2391), (1440, 2560), second)
                    if not dispatch_point or not action_positions.remember('dispatch', second, dispatch_point):
                        return False
                    if not action_positions.remember('withdraw_all', second, second_state[2]):
                        return False
                    if second_state[0] != 0:
                        target.check_active()
                        target.tap(*second_state[2])
                    def empty_mixed(image: Image.Image) -> tuple[tuple[int, int] | None, Any]:
                        return beast_cleared_first_shield_plus(image, beast_mixed_single_shield), None
                    cleared = wait_for_double("确认全部撤回及首盾加号", empty_mixed)
                    if not cleared:
                        self._log_for_device(target.device, "全部撤回或首盾加号未确认；未添加、未出征。")
                        return False
                    if not action_positions.remember('shield_plus', cleared[0], cleared[1]):
                        return False
                    dispatch = action_positions.cached_point('dispatch', cleared[0])
                    if not dispatch:
                        return False
                    return (cleared[1], dispatch, 25)
                for index, wanted in enumerate(wanted_troops):
                    first = capture()
                    second = capture() if not completed_cycles else first
                    first_control = match_beast_rally_formation_controls(first, threshold)
                    second_control = match_beast_rally_formation_controls(second, threshold)
                    first_rows, second_rows = beast_soldier_rows(first), beast_soldier_rows(second)
                    if (not stable(first_control.point, second_control.point)
                            or first_rows is None or first_rows != second_rows):
                        self._log_for_device(target.device, "兵种行未能确认；未修改兵力、未出征。")
                        return False
                    if second_rows[index] == wanted:
                        continue
                    field = map_content_point((950, (1318, 1598, 1878)[index]), (1440, 2560), second)
                    target.tap(*field)
                    deadline = time.monotonic() + 3.0
                    focused = False
                    while time.monotonic() < deadline and not self.stop_event.is_set():
                        if daily_training_input_focus_is_proven(target.shell(["dumpsys", "input_method"], timeout=5)):
                            focused = True
                            break
                        if self.stop_event.wait(0.10):
                            return False
                    if not focused:
                        self._log_for_device(target.device, "兵力输入框未取得焦点；未继续输入或出征。")
                        return False
                    target.shell(["input", "keyevent", "123"], timeout=5)
                    for _ in range(12):
                        target.check_active()
                        target.shell(["input", "keyevent", "67"], timeout=5)
                    target.shell(["input", "text", str(wanted)], timeout=5)
                    target.shell(["input", "keyevent", "66"], timeout=5)
                    def row_matches(image: Image.Image) -> tuple[tuple[int, int] | None, Any]:
                        control = match_beast_rally_formation_controls(image, threshold)
                        rows = beast_soldier_rows(image)
                        return (control.point if rows is not None and rows[index] == wanted else None), control
                    if not wait_for_double(f"确认第 {index + 1} 行兵力为 {wanted}", row_matches):
                        return False
                return bool(wait_for_double("确认手动兵力", exact_formation_match))

            def stamina_more_match(image: Image.Image) -> tuple[tuple[int, int] | None, Any]:
                match = match_beast_rally_stamina_more(image, threshold)
                return match.point, match

            def stamina_more_controls_match(image: Image.Image) -> tuple[tuple[int, int] | None, Any]:
                match = match_beast_rally_stamina_more_controls(image, threshold)
                return match.point, match

            # Worker-local: the worker is bound to one account and ADB device.
            # Recheck page anchors and size before reusing the coordinate.
            stamina_button_cache = {}

            def verified_stamina_button():
                frame_size = None

                def match_same_size(image):
                    nonlocal frame_size
                    point, payload = stamina_more_match(image)
                    if point is None:
                        frame_size = None
                        return None, payload
                    if frame_size is not None and frame_size != image.size:
                        frame_size = None
                        return None, payload
                    frame_size = image.size
                    return point, payload

                result = wait_for_double("确认普通体力按钮", match_same_size)
                if not result:
                    return None
                image, b, _ = result
                key = (identity, target.device, image.size)
                cached = stamina_button_cache.get(key)
                if cached is not None and not stable(cached, b):
                    return None
                stamina_button_cache[key] = b
                return cached or b

            def read_stamina_item_pair(accept: Callable[[tuple[int, int]], bool], *, receipt: bool = False) -> tuple[tuple[int, int], tuple[int, int]] | None:
                """Use full-page verification before input; allow toast-covered receipts."""
                deadline = time.monotonic() + bounded_step_timeout(AUTOMATION_STEP_TIMEOUT_SECONDS)
                previous = None
                while not self.stop_event.is_set() and time.monotonic() < deadline:
                    image = capture()
                    if daily_network_dialog_is_visible(image, threshold):
                        return None
                    point, _ = (stamina_more_controls_match(image) if receipt else stamina_more_match(image))
                    observation = read_beast_stamina_item_observation(image) if point else None
                    if point and observation is not None and accept(observation):
                        if previous and previous[1] == observation and stable(previous[0], point):
                            return point, observation
                        previous = (point, observation)
                        continue
                    previous = None
                    if pause():
                        return None
                return None

            def queue_panel_snapshot() -> tuple[str, tuple[int, int] | None, tuple[bool, ...] | None]:
                """Classify two immediate frames of the per-account march panel."""
                first = capture()
                second = capture()
                first_states = read_beast_rally_wilderness_queue_states(first, threshold)
                second_states = read_beast_rally_wilderness_queue_states(second, threshold)
                if first_states and first_states == second_states:
                    point, _ = match_beast_rally_progress_sidebar_expanded(second, threshold)
                    if point:
                        return "states", point, second_states
                first_point, _ = match_beast_rally_progress_sidebar_collapsed(first, threshold)
                second_point, _ = match_beast_rally_progress_sidebar_collapsed(second, threshold)
                if stable(first_point, second_point):
                    return "collapsed", second_point, None
                first_point, _ = match_beast_rally_progress_wilderness_tab(first, threshold)
                second_point, _ = match_beast_rally_progress_wilderness_tab(second, threshold)
                if stable(first_point, second_point):
                    return "wilderness_tab", second_point, None
                return "unknown", None, None

            def open_wilderness_queue_panel(
                label: str,
                timeout: float = AUTOMATION_STEP_TIMEOUT_SECONDS,
            ) -> tuple[bool, ...] | None:
                """Open only reviewed panel controls and return stable per-row states."""
                deadline = time.monotonic() + bounded_step_timeout(timeout)
                expanded_once = False
                selected_once = False
                while not self.stop_event.is_set() and time.monotonic() < deadline:
                    kind, point, states = queue_panel_snapshot()
                    if kind == "states" and states:
                        set_state(f"{label}：队列 {sum(states)}/{len(states)} 空闲")
                        return states
                    if kind == "collapsed" and point and not expanded_once:
                        target.tap(*point)
                        expanded_once = True
                        self._log_for_device(target.device, f"双帧确认后展开行军队列面板 {point}。")
                        continue
                    if kind == "wilderness_tab" and point and not selected_once:
                        target.tap(*point)
                        selected_once = True
                        self._log_for_device(target.device, f"双帧确认后切换行军队列面板到野外 {point}。")
                        continue
                    if pause():
                        return None
                self._log_for_device(target.device, f"{label}未在单步时限内读出稳定的野外队列数；零输入停止。")
                return None

            def collapse_wilderness_queue_panel() -> bool:
                """Collapse the reviewed panel so it cannot cover Search next cycle."""
                result = wait_for_double(
                    "确认收起行军队列面板",
                    lambda image: match_beast_rally_progress_sidebar_expanded(image, threshold),
                    timeout=6,
                )
                if not result:
                    return False
                _image, point, _ = result
                target.tap(*point)
                closed = wait_for_double(
                    "确认行军队列面板已收起",
                    lambda image: match_beast_rally_progress_sidebar_collapsed(image, threshold),
                    timeout=6,
                )
                return bool(closed)

            def monitor_dispatched_queue() -> bool:
                """Correlate one newly busy row, then wait only for that row to return."""
                nonlocal baseline_march_capacity
                if baseline_march_capacity is not None:
                    baseline_used, baseline_total = baseline_march_capacity
                    # Expedition returns to the wilderness with the march
                    # panel collapsed.  Expanded used/total is lifecycle
                    # authority only after the exact collapsed arrow and the
                    # Wilderness tab have been handled by the reviewed panel
                    # opener.  Without this step the old loop passively read
                    # ``None`` forever and could never settle its reservation.
                    post_dispatch_states = open_wilderness_queue_panel(
                        "出征后复核野外容量"
                    )
                    if post_dispatch_states is None:
                        self._log_for_device(
                            target.device,
                            "出征后未在单步时限内展开野外容量面板；保留体力预留并停止。",
                        )
                        return False
                    new_busy_proofs = 0
                    returned_proofs = 0
                    reservation_confirmed = False
                    all_idle_proofs = 0
                    while not self.stop_event.is_set():
                        first = capture()
                        second = capture()
                        first_states = read_beast_rally_wilderness_queue_states(first, threshold)
                        second_states = read_beast_rally_wilderness_queue_states(second, threshold)
                        if (
                            reservation_confirmed
                            and first_states is not None
                            and second_states is not None
                            and first_states == second_states
                            and len(first_states) == baseline_total
                            and all(first_states)
                        ):
                            all_idle_proofs += 1
                            if all_idle_proofs >= 2:
                                self._log_for_device(
                                    target.device,
                                    f"野外面板连续两次证明 {baseline_total} 行全部空闲；本号巨兽已回兵。",
                                )
                                return collapse_wilderness_queue_panel()
                        else:
                            all_idle_proofs = 0
                        first_capacity = read_beast_rally_expanded_march_capacity(first, threshold)
                        second_capacity = read_beast_rally_expanded_march_capacity(second, threshold)
                        if (
                            first_capacity is None
                            or second_capacity is None
                            or (first_capacity.used, first_capacity.total)
                            != (second_capacity.used, second_capacity.total)
                            or first_capacity.total != baseline_total
                        ):
                            new_busy_proofs = returned_proofs = 0
                            if pause():
                                return False
                            continue
                        if first_capacity.used == baseline_used + 1:
                            new_busy_proofs += 1
                            returned_proofs = 0
                            if new_busy_proofs >= 1 and not reservation_confirmed:
                                reserved = load_beast_rally_stamina_reserved(identity)
                                spent = confirm_beast_rally_stamina_reservation(identity) if reserved else load_beast_rally_stamina_spent(identity)
                                reservation_confirmed = True
                                self._log_for_device(
                                    target.device,
                                    f"行军标题由 {baseline_used}/{baseline_total} 变为 "
                                    f"{first_capacity.used}/{first_capacity.total}；预留 {reserved} 已结算，今日确认消耗 {spent}（估算计入待核实）。",
                                )
                            set_state(
                                f"本号巨兽队伍占用：{first_capacity.used}/{first_capacity.total}"
                            )
                        elif reservation_confirmed and first_capacity.used <= baseline_used:
                            returned_proofs += 1
                            if returned_proofs >= 2:
                                self._log_for_device(
                                    target.device,
                                    f"行军标题连续双帧恢复 {first_capacity.used}/{first_capacity.total}；本号巨兽已回兵。",
                                )
                                return collapse_wilderness_queue_panel()
                        else:
                            new_busy_proofs = returned_proofs = 0
                        if pause():
                            return False
                if baseline_queue_states is None:
                    return False
                states = open_wilderness_queue_panel("出征后复核野外队列")
                if not states or len(states) != len(baseline_queue_states):
                    return False
                deadline = time.monotonic() + 24
                tracked_index: int | None = None
                idle_proofs = 0
                while not self.stop_event.is_set():
                    if tracked_index is None:
                        new_busy = beast_rally_new_busy_queue_indexes(
                            baseline_queue_states,
                            states,
                        )
                        if len(new_busy) == 1:
                            tracked_index = new_busy[0]
                            reserved = load_beast_rally_stamina_reserved(identity)
                            if reserved:
                                spent = confirm_beast_rally_stamina_reservation(identity)
                                self._log_for_device(
                                    target.device,
                                    f"第 {tracked_index + 1} 行由空闲变占用；预留 {reserved} 已结算，今日确认消耗 {spent}（估算计入待核实）。",
                                )
                        elif len(new_busy) > 1:
                            self._log_for_device(target.device, "出征后有多个队列同时由空闲变占用，无法关联本轮；安全停止。")
                            return False
                        elif time.monotonic() >= deadline:
                            self._log_for_device(target.device, "出征后24秒内未证明唯一新增占用队列；保留体力预留并停止。")
                            return False
                    elif states[tracked_index]:
                        idle_proofs += 1
                        set_state(f"第 {tracked_index + 1} 行已回兵：复核 {min(idle_proofs, 2)}/2")
                        if idle_proofs >= 2:
                            evidence_image = capture()
                            evidence_point, _ = match_beast_rally_progress_sidebar_expanded(
                                evidence_image,
                                threshold,
                            )
                            save_evidence(
                                evidence_image,
                                evidence_point,
                                "beast_queue_returned",
                                f"第 {tracked_index + 1} 行连续两次恢复空闲；其他队列未参与本轮判断。",
                            )
                            return collapse_wilderness_queue_panel()
                    else:
                        idle_proofs = 0
                        set_state(f"第 {tracked_index + 1} 行巨兽队伍仍占用")
                    if pause():
                        return False
                    kind, _point, next_states = queue_panel_snapshot()
                    if kind != "states" or not next_states:
                        idle_proofs = 0
                        continue
                    if len(next_states) != len(baseline_queue_states):
                        self._log_for_device(target.device, "监控期间野外队列总数变化；安全停止。")
                        return False
                    states = next_states
                return False

            def configure_level() -> tuple[Image.Image, tuple[int, int]] | None:
                drawer = wait_for_double("确认搜索页", match_beast_rally_search_drawer)
                if not drawer:
                    return None
                image, _, _ = drawer
                if not beast_rally_beast_target_point(image):
                    # The drawer is known, but the carousel may be scrolled away.
                    # One gesture per entry: never repeat an unacknowledged input.
                    start = map_content_point((1100, 1780), (1440, 2560), image)
                    end = map_content_point((400, 1780), (1440, 2560), image)
                    if self.stop_event.is_set():
                        return None
                    self._log_for_device(target.device, "搜索页未识别到巨兽，向左滑动一次后重新检测。")
                    target.shell(["input", "swipe", str(start[0]), str(start[1]), str(end[0]), str(end[1]), "350"], timeout=5)
                    # A left swipe cannot reveal a card already off the left
                    # edge. Reconfirm this exact drawer and inspect a fresh
                    # frame before one bounded return toward its first cards.
                    after_left = wait_for_double("左划后确认搜索页", match_beast_rally_search_drawer)
                    if not after_left:
                        return None
                    image = after_left[0]
                    if not beast_rally_beast_target_point(image):
                        start = map_content_point((150, 1780), (1440, 2560), image)
                        end = map_content_point((1280, 1780), (1440, 2560), image)
                        if self.stop_event.is_set():
                            return None
                        self._log_for_device(target.device, "左划重检仍未发现巨兽；确认搜索页后向右滑动一次恢复卡片。")
                        target.shell(["input", "swipe", str(start[0]), str(start[1]), str(end[0]), str(end[1]), "350"], timeout=5)
                selected = wait_for_double("确认冰原巨兽搜索页", selector_match)
                if not selected:
                    return None
                image, search_point, _ = selected
                # Selector has already proved the card on this fresh frame.
                # Reuse this job's image-anchored first-cycle location when valid.
                beast_point = action_positions.reuse('beast_card', image) if completed_cycles else None
                if not beast_point:
                    beast_point = beast_rally_beast_target_point(image)
                if not beast_point:
                    return None
                beast_point = cycle_position('beast_card', image, beast_point)
                if not beast_point:
                    return None
                target.tap(*beast_point)
                self._log_for_device(target.device, f"点击精确冰原巨兽卡片 {beast_point}。")
                selected = wait_for_double("复核冰原巨兽卡片与搜索按钮", selector_match)
                if not selected:
                    return None
                image, search_point, _ = selected
                def configured(image: Image.Image) -> tuple[tuple[int, int] | None, int | None]:
                    point = beast_rally_selector_search_point(image)
                    value = read_beast_rally_selector_level(image) if point else None
                    return (point if value == profile.beast_level else None), value

                current = read_beast_rally_selector_level(image)
                if current == profile.beast_level:
                    # The post-card selector frame is already fresh and verified.
                    # Later cycles require one routine frame, not another capture.
                    if completed_cycles:
                        return image, search_point
                    result = wait_for_double(f"确认等级为 {profile.beast_level}", configured)
                    return (result[0], result[1]) if result else None
                field = beast_rally_level_field_point(image)
                if not field:
                    self._log_for_device(target.device, "等级输入框未与冰原巨兽页同帧确认；未输入。")
                    return None
                target.tap(*field)
                focus_deadline = time.monotonic() + 3.0
                focused = False
                while time.monotonic() < focus_deadline and not self.stop_event.is_set():
                    input_state = target.shell(["dumpsys", "input_method"], timeout=5)
                    if daily_training_input_focus_is_proven(input_state):
                        focused = True
                        break
                    if self.stop_event.wait(0.10):
                        return None
                if not focused:
                    self._log_for_device(target.device, "等级输入框没有取得可编辑Unity焦点；未清除文字、未搜索。")
                    return None
                target.shell(["input", "keyevent", "123"], timeout=5)
                for _ in range(3):
                    target.shell(["input", "keyevent", "67"], timeout=5)
                target.shell(["input", "text", str(profile.beast_level)], timeout=5)
                target.shell(["input", "keyevent", "66"], timeout=5)

                result = wait_for_double(f"确认等级已改为 {profile.beast_level}", configured)
                if result:
                    image, search_point, _ = result
                    save_evidence(image, search_point, "level_ready", f"冰原巨兽等级{'单' if completed_cycles else '双'}帧确认为 {profile.beast_level}。")
                    return image, search_point
                return None

            def wait_existing_progress() -> bool:
                """Record every row; unrelated busy queues do not block a free slot."""
                nonlocal baseline_queue_states, baseline_march_capacity
                # The collapsed header is authoritative for free capacity.
                # A visible blue allied rally row may have a green countdown
                # bar, but it does not belong to this account and therefore
                # must not enter our baseline or stamina ledger.
                first = capture()
                second = capture()
                first_capacity = read_beast_rally_collapsed_march_capacity(first, threshold)
                second_capacity = read_beast_rally_collapsed_march_capacity(second, threshold)
                if (
                    first_capacity is not None
                    and second_capacity is not None
                    and (first_capacity.used, first_capacity.total)
                    == (second_capacity.used, second_capacity.total)
                    and first_capacity.free > 0
                ):
                    baseline_queue_states = tuple(True for _ in range(first_capacity.total))
                    baseline_march_capacity = (first_capacity.used, first_capacity.total)
                    self._log_for_device(
                        target.device,
                        f"折叠行军标题双帧确认 {first_capacity.used}/{first_capacity.total}，"
                        f"可用 {first_capacity.free} 队；蓝色盟军状态行不计入本号巨兽锁或体力账本。",
                    )
                    return True
                states = open_wilderness_queue_panel("启动前复核野外队列")
                if not states:
                    return False
                baseline_queue_states = states
                reserved = load_beast_rally_stamina_reserved(identity)
                if reserved:
                    self._log_for_device(target.device, f"存在无法与具体队列关联的未决体力 {reserved}；未发起新集结。")
                    return False
                first_expanded = capture()
                second_expanded = capture()
                expanded_baseline = beast_rally_expanded_capacity_baseline(
                    states,
                    read_beast_rally_expanded_march_capacity(first_expanded, threshold),
                    read_beast_rally_expanded_march_capacity(second_expanded, threshold),
                )
                if expanded_baseline is not None:
                    baseline_march_capacity = expanded_baseline
                    used, total = expanded_baseline
                    self._log_for_device(
                        target.device,
                        f"展开行军标题双帧确认 {used}/{total}，可用 {total - used} 队；"
                        "后续只用本号容量变化关联巨兽，蓝色盟军行不计入。",
                    )
                    return collapse_wilderness_queue_panel()
                if not any(states):
                    set_state("野外行军队列已满：没有空闲行")
                    self._log_for_device(target.device, "所有野外行军队列都被占用；未发起新集结。")
                    return False
                return collapse_wilderness_queue_panel()

            def ensure_compact_march_panel() -> bool:
                """Never open the side panel at startup; close it if left open."""
                first, second = capture(), capture()
                p = match_beast_rally_progress_sidebar_expanded(first, threshold)[0]
                q = match_beast_rally_progress_sidebar_expanded(second, threshold)[0]
                if stable(p, q):
                    self._log_for_device(target.device, "已有野外面板遮住顶部列表：只收起，不展开。")
                    return collapse_wilderness_queue_panel()
                if p or q:
                    return False
                return True

            def recover_pending_reservation() -> bool:
                """A previous unknown dispatch cannot be cleared by idle frames."""
                reserved = load_beast_rally_stamina_reserved(identity)
                if not reserved:
                    return True
                set_state("等待旧出征回执：保留预留，不重复输入")
                if not ensure_compact_march_panel():
                    return False
                heartbeat_at = 0.0
                while not self.stop_event.is_set():
                    first, second = capture(), capture()
                    if any(frame is not None and daily_network_dialog_is_visible(frame, threshold) for frame in (first, second)):
                        set_state("游戏网络离线：保留预留并停止输入")
                        self._log_for_device(target.device, "等待旧出征回执时检测到游戏网络离线；保留预留并停止。")
                        return False
                    if stable(match_same_target_conflict(first), match_same_target_conflict(second)):
                        self._log_for_device(target.device, "旧出征存在同目标冲突提示；保留预留并停止输入。")
                        return False
                    now = time.monotonic()
                    if now >= heartbeat_at:
                        self._log_for_device(target.device, "旧出征回执未知；保留预留并被动复查。空闲不能证明未出征，不重复输入。")
                        heartbeat_at = now + 25.0
                    if pause():
                        return False
                return False

            def single_team_baseline() -> bool:
                nonlocal baseline_march_capacity
                if not ensure_compact_march_panel():
                    return False
                deadline = time.monotonic() + 24.0
                diagnostic_logged = False
                while not self.stop_event.is_set() and time.monotonic() < deadline:
                    first, second = capture(), capture()
                    owners = read_compact_rally_rows(first) + read_compact_rally_rows(second)
                    cap1 = read_beast_rally_collapsed_march_capacity(first, threshold)
                    cap2 = read_beast_rally_collapsed_march_capacity(second, threshold)
                    joined_only = (only_joined_rallies(cap1, read_compact_rally_rows(first))
                                   and only_joined_rallies(cap2, read_compact_rally_rows(second))
                                   and (cap1.used,cap1.total)==(cap2.used,cap2.total))
                    gatherers_safe = gathering_pair_free(first,second,cap1,cap2)
                    if joined_only or blue_pair_free(first,second,cap1,cap2) or gatherers_safe:
                        baseline_march_capacity = (cap2.used, cap2.total)
                        self._log_for_device(target.device, "完整列表双帧确认仅有蓝色队伍或明确采集中的队伍且有空槽；保留现有队伍，下一步核验出征配置。")
                        return True
                    if (not any(r.owner == 'own' for r in owners) and cap1 and cap2
                            and cap1.used == cap2.used == 0
                            and (cap1.total, cap1.evidence) == (cap2.total, cap2.evidence)):
                        baseline_march_capacity = (0, cap1.total)
                        self._log_for_device(target.device, "双帧确认空闲：" + ("野外列表已消失" if cap1.evidence == 'hidden_idle' else f"0/{cap1.total}") + "；未展开野外面板。")
                        return True
                    if not diagnostic_logged:
                        diagnostic_logged = True
                        self._log_for_device(target.device, f"空闲诊断：首帧 {cap1}；次帧 {cap2}；集结行 {[(r.owner,r.phase) for r in owners]}。")
                    set_state("自动复核顶部列表：等待双帧空闲证据，不展开、不出征")
                    if pause():
                        return False
                self._log_for_device(target.device, "顶部列表24秒内未证明空闲；保留记录，不把缺失数字当0。")
                return False

            def resolve_target_conflict(first, second) -> bool:
                nonlocal retry_target_requested, target_conflicts
                p,q=match_same_target_conflict(first),match_same_target_conflict(second)
                if not stable(p,q):
                    # A modal often appears between the first two captures.
                    # Keep a sliding fresh pair instead of treating that timing
                    # gap as a failed cancellation. Never click a single match.
                    self._log_for_device(target.device, "目标冲突提示正在出现：立即补取新帧确认，不点击、不重发出征。")
                    deadline = time.monotonic() + 4.0
                    for _ in range(4):
                        if self.stop_event.is_set() or time.monotonic() >= deadline:
                            break
                        first, second = second, capture()
                        p,q=match_same_target_conflict(first),match_same_target_conflict(second)
                        if stable(p,q):
                            break
                if self.stop_event.is_set():
                    return False
                if not stable(p,q):
                    self._log_for_device(target.device, "目标冲突未形成连续双帧确认；保留出征记录，未点击取消或确定。")
                    return False
                if target_conflicts>=3:
                    self._log_for_device(target.device, "连续目标冲突达到3次，停止重试；未点击确定或增加队伍。")
                    return False
                target.tap(*q)
                self._log_for_device(target.device, "双帧确认目标冲突：点击橙色取消，绝不点击确定继续发兵。")
                save_evidence(second,q,"same_target_cancel","精确同目标警告后取消出征。")
                restored=wait_for_double("冲突取消后确认出征配置",exact_formation_match)
                if not restored:
                    self._log_for_device(target.device, "冲突取消后未确认出征配置；保留体力预留，未重新搜索。")
                    return False
                reserved=load_beast_rally_stamina_reserved(identity)
                if reserved:
                    cancel_beast_rally_conflict_reservation(identity,reserved,cancelled_and_formation_restored=True)
                    if (profile.troop_mode != "formation" and wanted_troops == (1, 0, 0)
                            and beast_shield_plus_pending(identity)):
                        beast_shield_plus_confirm(identity)
                        self._log_for_device(target.device, "同目标取消后已双帧确认单盾配置，清除本次加号未决标记。")
                    self._log_for_device(target.device,f"目标冲突已取消且编组恢复：解除本次未出征体力预留 {reserved}，不计成功消耗。")
                target.back()
                first,second=capture(),capture()
                # A target card may remain after formation Back. Only this
                # reviewed Beast card may authorize one more Back.
                p=match_beast_rally_open_button(first,threshold)[0]
                q=match_beast_rally_open_button(second,threshold)[0]
                if stable(p,q):
                    target.back()
                if not ensure_wilderness():
                    return False
                target_conflicts+=1
                retry_target_requested=True
                self._log_for_device(target.device,f"已退出冲突目标，重新搜索{profile.beast_level}级巨兽（换目标 {target_conflicts}/3）；不把冲突计作完成。")
                return True

            def concurrent_baseline() -> bool:
                nonlocal baseline_concurrent, baseline_march_capacity, tracked_green, tracked_rallies
                if not ensure_compact_march_panel():
                    return False
                unknown_since = time.monotonic()
                heartbeat_at = 0.0
                previous = None
                while not self.stop_event.is_set():
                    first, second = capture(), capture()
                    if any(frame is not None and daily_network_dialog_is_visible(frame, threshold) for frame in (first, second)):
                        set_state("游戏网络离线：停止输入")
                        self._log_for_device(target.device, "等待队列时检测到游戏网络离线；停止输入。")
                        return False
                    if stable(match_same_target_conflict(first), match_same_target_conflict(second)):
                        self._log_for_device(target.device, "检查队列发现同目标冲突提示，停止以保留现场。")
                        return False
                    now = time.monotonic()
                    # In six-team mode, stable physical capacity decides whether
                    # there is room. Row classification is useful only to help
                    # establish the later receipt, not to veto a free slot.
                    if profile.max_concurrent_rallies == 6:
                        cap1 = read_compact_numeric_capacity(first)
                        cap2 = read_compact_numeric_capacity(second)
                        if (match_world(first)[0] and match_world(second)[0]
                                and cap1 and cap2 and cap1.evidence == cap2.evidence == 'numeric'
                                and (cap1.used, cap1.total) == (cap2.used, cap2.total)
                                and 0 < cap1.used < cap1.total <= 6):
                            a, b = read_concurrent_snapshot(first), read_concurrent_snapshot(second)
                            if (a is not None and a == b and a.evidence == 'numeric'
                                    and (a.used, a.total) == (cap1.used, cap1.total)):
                                baseline_concurrent = a
                            else:
                                baseline_concurrent = ConcurrentRallySnapshot(
                                    cap1.used, cap1.total, 'numeric', ('unknown',) * cap1.used)
                            baseline_march_capacity = (cap1.used, cap1.total)
                            self._log_for_device(target.device, f"左侧数字双帧 {cap1.used}/{cap1.total}，有空位；继续搜索新目标。")
                            return True
                    a, b = read_concurrent_snapshot(first), read_concurrent_snapshot(second)
                    if (a is not None and a == b
                            and (profile.max_concurrent_rallies == 6
                                 or (a.green <= tracked_green and a.rallies <= tracked_rallies))):
                        # At the user's six-team cap the physical free-slot
                        # count is authoritative. Stale ambiguous row matches
                        # must not reserve imaginary slots after they vanish.
                        if profile.max_concurrent_rallies != 6 and not line_tracker.observe(a):
                            self._log_for_device(target.device, "左侧队伍阶段无法安全追踪，停止自动补位。")
                            return False
                        tracked_green, tracked_rallies = a.green, a.rallies
                        unknown_since = now
                        if a != previous:
                            self._log_for_device(target.device, f"完整队列双帧：自建集结 {a.rallies}，绿色行军 {a.green-a.rallies}，占用 {a.used}/{a.total if a.total else '未知'}，上限 {profile.max_concurrent_rallies}；保留采集队。")
                            previous = a
                        if (concurrent_dispatch_allowed(a, profile.max_concurrent_rallies)
                                and (profile.max_concurrent_rallies == 6
                                     or line_tracker.has_room(profile.max_concurrent_rallies))):
                            baseline_concurrent = a
                            baseline_march_capacity = (a.used, a.total)
                            return True
                        set_state(f"等待队伍行军结束并释放空位：占用 {a.used}/{a.total}，上限 {profile.max_concurrent_rallies}")
                        if now >= heartbeat_at:
                            self._log_for_device(target.device, "队伍仍占用或没有空位，持续观察；队伍行军结束离开左侧队列后补开。")
                            heartbeat_at = now + 25.0
                    elif now - unknown_since >= 24.0:
                        self._log_for_device(target.device, "队列归属或完整性暂无法双帧确认；继续被动复查，不新增出征。")
                        set_state("队列暂不可识别：被动复查，不新增出征")
                        unknown_since = now
                    if pause():
                        return False
                return False

            def wait_queue_capacity_frame(seed=None):
                """Reuse one fresh world frame for capacity, user limit and Search."""
                nonlocal baseline_concurrent, baseline_march_capacity
                frame = seed
                while not self.stop_event.is_set():
                    if frame is None:
                        frame = capture()
                    if daily_network_dialog_is_visible(frame, threshold):
                        self._log_for_device(target.device, "等待队列时游戏网络离线，停止输入。")
                        return None
                    if match_beast_rally_progress_sidebar_expanded(frame, threshold)[0]:
                        # A panel close changes the page; never reuse this frame.
                        if not ensure_compact_march_panel():
                            return None
                        frame = None
                        continue
                    search = match_world(frame)[0]
                    # Search and the non-expanded panel were already checked on
                    # this same fresh frame; reuse that context for capacity.
                    cap = read_beast_rally_collapsed_march_capacity(frame, threshold, world_proven=True) if search else None
                    valid_numeric = bool(cap and cap.evidence == 'numeric'
                                         and 0 <= cap.used <= cap.total and cap.total > 0)
                    hidden_idle = bool(cap and cap.evidence == 'hidden_idle'
                                       and cap.used == 0 and cap.total == 0)
                    if valid_numeric or hidden_idle:
                        if hidden_idle or cap.used < min(cap.total, profile.max_concurrent_rallies):
                            baseline_concurrent = ConcurrentRallySnapshot(
                                cap.used, cap.total, cap.evidence, ('unknown',) * cap.used)
                            baseline_march_capacity = (cap.used, cap.total)
                            return frame, search
                        set_state(f"队列已满：{cap.used}/{cap.total}，上限 {profile.max_concurrent_rallies}，等待空位")
                    frame = None
                    if pause():
                        return None
                return None

            idle_reconcile_failure_reported = False

            def reconcile_unconfirmed_hidden_idle(first, second) -> bool:
                nonlocal idle_reconcile_failure_reported
                # Current idle is not a dispatch receipt; retain an uncertain debit.
                if first is None or second is None or self.stop_event.is_set():
                    return False
                cap1 = read_beast_rally_collapsed_march_capacity(first, threshold)
                cap2 = read_beast_rally_collapsed_march_capacity(second, threshold)
                if not (cap1 and cap2 and cap1.used == cap2.used == 0
                        and cap1.total == cap2.total == 0
                        and cap1.evidence == cap2.evidence == 'hidden_idle'):
                    return False
                target.check_active()
                if self.stop_event.is_set():
                    return False
                amount = reconcile_beast_rally_idle_reservation(
                    identity, None, None, first_capacity=cap1, second_capacity=cap2)
                if not amount:
                    if not idle_reconcile_failure_reported:
                        self._log_for_device(target.device, "空闲已确认，但预留无法对账（可能跨日）；继续保留并观察。")
                        idle_reconcile_failure_reported = True
                    return False
                self._log_for_device(target.device, f"出征回执仍未知；双帧野外空闲，预留 {amount} 计入不确定体力，不重发旧操作。")
                set_state("旧回执未知：已保守记账，继续观察")
                return True

            def recover_receipt_stamina(first, second):
                result = beast_recover_receipt_stamina(
                    first, second,
                    match_item=lambda image: stamina_more_match(image)[0],
                    observation=read_beast_stamina_item_observation,
                    network=lambda image: daily_network_dialog_is_visible(image, threshold),
                    stable=stable,
                    reserved=lambda: load_beast_rally_stamina_reserved_any_day(identity),
                    pending=lambda: load_beast_stamina_item_pending(identity),
                    check_active=target.check_active,
                    begin=lambda: begin_beast_stamina_fast_batch(identity, count=4 if profile.run_mode == 'fast' else 1),
                    mark_sent=lambda token: update_beast_stamina_fast_batch(identity, token),
                    complete=finish_item_batch,
                    tap=lambda point: target.tap(*point), capture=capture,
                    close_point=lambda image: beast_stamina_close_point(image, threshold),
                    match_world=lambda image: match_world(image)[0],
                    match_formation=lambda image: formation_controls_match(image)[0],
                    uses=4 if profile.run_mode == 'fast' else 1,
                    fast_batch_tap=(lambda point: beast_tap_stamina_four(target, point)) if profile.run_mode == 'fast' else None,
                    on_use=lambda count: self._log_for_device(target.device, f'已提交体力道具使用操作（{count} 次）。'),
                    wait_between=lambda: False,
                    stopped=self.stop_event.is_set,
                    diagnose=lambda reason: self._log_for_device(target.device, f'体力页处理停止：{reason}。'))
                if result is not None:
                    self._log_for_device(target.device,
                        ("体力页已处理，返回出征配置。" if result == 'formation_after_stamina' else
                         "体力页已处理，继续观察旧出征回执，不重复出征。") if result else
                        "体力页恢复未进入世界页；保留旧出征预留并停止，不重复出征，具体原因见上方日志。")
                return result

            def resume_after_stamina_overlay(frame):
                # This is called only in the active episode immediately after
                # its own input opened the known stamina overlay. A restarted
                # worker never uses it for a pre-existing reservation.
                point = action_positions.cached_point('dispatch', frame)
                if not point or self.stop_event.is_set() or not load_beast_rally_stamina_reserved_any_day(identity):
                    return False
                target.check_active()
                target.tap(*point)
                self._log_for_device(target.device, "体力不足弹窗补给完成；沿用原预留和出征坐标继续。")
                return True

            def monitor_new_concurrent_rally() -> bool:
                nonlocal confirmed_dispatches, tracked_green, tracked_rallies
                before = baseline_concurrent
                if before is None:
                    return False
                unknown_release_after = time.monotonic() + 1.0
                heartbeat_at = time.monotonic() + 24.0
                idle_recovery_after = heartbeat_at
                a = b = None
                stamina_recovery_attempted = False
                while not self.stop_event.is_set():
                    first, second = capture(), capture()
                    if any(frame is not None and daily_network_dialog_is_visible(frame, threshold) for frame in (first, second)):
                        set_state("游戏网络离线：保留预留并停止输入")
                        self._log_for_device(target.device, "等待出征回执时检测到游戏网络离线；保留预留并停止。")
                        return False
                    if match_same_target_conflict(first) or match_same_target_conflict(second):
                        resolve_target_conflict(first, second)
                        return False
                    if stamina_recovery_attempted and (stamina_more_match(first)[0] or stamina_more_match(second)[0]):
                        self._log_for_device(target.device, "同一出征的体力页再次出现；保留出征预留并停止，不重复补给。")
                        return False
                    recovery = recover_receipt_stamina(first, second)
                    if recovery is not None:
                        stamina_recovery_attempted = True
                        if not recovery:
                            return False
                        if recovery == 'formation_after_stamina' and not resume_after_stamina_overlay(second):
                            return False
                        continue
                    a, b = read_concurrent_snapshot(first), read_concurrent_snapshot(second)
                    if a is not None and a == b and confirms_new_concurrent_rally(before, a):
                        if profile.max_concurrent_rallies != 6 and not line_tracker.observe(a, new_rally=True):
                            self._log_for_device(target.device, "新集结已出现，但左侧队伍阶段无法安全追踪；保留预留并停止。")
                            return False
                        spent = confirm_beast_rally_stamina_reservation(identity)
                        confirmed_dispatches += 1
                        tracked_green, tracked_rallies = a.green, a.rallies
                        self._log_for_device(target.device, f"双帧确认新增自建集结：{before.rallies} → {a.rallies}，占用 {a.used}/{a.total}，今日确认消耗 {spent}（估算计入待核实）。")
                        save_evidence(second, (70, 545), "concurrent_own_rally", "双帧确认新增一个自建集结及占用；其余队伍保留。")
                        return True
                    if (time.monotonic() >= unknown_release_after
                            and beast_unconfirmed_world_free(first, second, a, b,
                                profile.max_concurrent_rallies,
                                lambda frame: match_world(frame)[0],
                                lambda frame: daily_network_dialog_is_visible(frame, threshold), stable)):
                        target.check_active()
                        if self.stop_event.is_set():
                            return False
                        amount = load_beast_rally_stamina_reserved_any_day(identity)
                        if amount:
                            archive_beast_rally_unconfirmed_reservation(identity, amount)
                            self._log_for_device(target.device, f"旧出征回执未知，{amount}点记入不确定支出；队列有空位，搜索新目标，不重发旧操作。")
                            return 'uncertain_reconciled'
                    if time.monotonic() >= idle_recovery_after and reconcile_unconfirmed_hidden_idle(first, second):
                        return 'idle_reconciled'
                    if time.monotonic() >= heartbeat_at:
                        self._log_for_device(target.device, f"出征回执尚未双帧确认：出征前 {before}，最新双帧 {a} / {b}；保留预留，被动复查，不重复输入。")
                        set_state("等待出征回执：被动复查，不重复出征")
                        heartbeat_at = time.monotonic() + 24.0
                    if pause():
                        return False
                return False

            def monitor_single_team() -> bool:
                if baseline_march_capacity is None:
                    return False
                total = baseline_march_capacity[1]
                cycle = SingleBeastCycle(total, require_owner=True)
                cycle.dispatch()
                proof_deadline = time.monotonic() + 24.0
                idle_recovery_after = proof_deadline
                unknown_since = time.monotonic()
                heartbeat_at = 0.0
                accounted = False
                marched = False
                last_phase = 'rallying'
                overlay_recovery_used = False
                stamina_recovery_attempted = False
                while not self.stop_event.is_set():
                    first, second = capture(), capture()
                    if not cycle.seen_busy and (match_same_target_conflict(first) or match_same_target_conflict(second)):
                        resolve_target_conflict(first,second)
                        return False
                    if not cycle.seen_busy:
                        if stamina_recovery_attempted and (stamina_more_match(first)[0] or stamina_more_match(second)[0]):
                            self._log_for_device(target.device, "同一出征的体力页再次出现；保留出征预留并停止，不重复补给。")
                            return False
                        recovery = recover_receipt_stamina(first, second)
                        if recovery is not None:
                            stamina_recovery_attempted = True
                            if not recovery:
                                return False
                            if recovery == 'formation_after_stamina' and not resume_after_stamina_overlay(second):
                                return False
                            continue
                    owners1 = [r for r in read_compact_rally_rows(first) if r.owner == 'own']
                    owners2 = [r for r in read_compact_rally_rows(second) if r.owner == 'own']
                    if len(owners1) == len(owners2) == 1 and stable(owners1[0].point, owners2[0].point):
                        cycle.confirm_owned_rally()
                        if not accounted:
                            spent = confirm_beast_rally_stamina_reservation(identity)
                            accounted = True
                            self._log_for_device(target.device, f"出征后双帧确认绿色图标＋集结中：这是本轮自建集结，今日确认消耗 {spent}（估算计入待核实）；蓝色行不计入自建证明。")
                            save_evidence(second, owners2[0].point, "own_green_rally", "绿色图标与同一行集结中文字确认自建归属；不是绿色进度条。")
                        t1, t2 = owners1[0].seconds, owners2[0].seconds
                        timer_text = "时间识别中"
                        if t1 is not None and t2 is not None and 0 <= t1-t2 <= 3:
                            timer_text = f"{t2//3600:02}:{t2//60%60:02}:{t2%60:02}"
                        set_state(f"我的自建集结 · {troop_label} · {timer_text} · 不新增队伍")
                        now = time.monotonic()
                        unknown_since = now
                        if now >= heartbeat_at:
                            self._log_for_device(target.device, f"绿色自建集结仍在等待：{timer_text}；直接读取上方列表，无需展开野外面板。")
                            heartbeat_at = now + 25.0
                        if pause():
                            return False
                        continue
                    marches1 = read_compact_marching_rows(first) if cycle.seen_busy else ()
                    marches2 = read_compact_marching_rows(second) if cycle.seen_busy else ()
                    if (len(marches1)==len(marches2)==1
                            and stable(marches1[0].point,marches2[0].point)
                            and 0<=marches1[0].seconds-marches2[0].seconds<=3):
                        marched = True
                        seconds = marches2[0].seconds
                        timer_text = f"{seconds//3600:02}:{seconds//60%60:02}:{seconds%60:02}"
                        set_state(f"我的绿色行军 · {troop_label} · {timer_text} · 不新增队伍")
                        unknown_since = time.monotonic()
                        if last_phase != 'marching':
                            last_phase = 'marching'
                            self._log_for_device(target.device, f"本轮绿色自建集结已进入绿色行军：{timer_text}；按左侧图标识别，不使用绿色进度条判断归属。")
                            save_evidence(second, marches2[0].point, "own_green_marching", "关联本轮集结后的绿色行军图标和同一行倒计时；未判定回城。")
                        continue
                    if not cycle.seen_busy:
                        now = time.monotonic()
                        if (now >= idle_recovery_after
                                and not any(frame is not None and daily_network_dialog_is_visible(frame, threshold) for frame in (first, second))
                                and reconcile_unconfirmed_hidden_idle(first, second)):
                            return 'idle_reconciled'
                        if now >= proof_deadline:
                            if any(frame is not None and daily_network_dialog_is_visible(frame, threshold) for frame in (first, second)):
                                self._log_for_device(target.device, "等待出征回执时检测到游戏网络离线；保留预留并停止。")
                                return False
                            self._log_for_device(target.device, "出征回执尚未双帧确认；保留预留并继续识别自建集结，不重复输入。")
                            set_state("等待出征回执：继续识别，不重复输入")
                            proof_deadline = time.monotonic() + 24.0
                        if pause():
                            return False
                        continue
                    # Keep reading the compact list throughout phase changes.
                    # No return claim: a complete blue-only list permits next
                    # search under the user's revised no-green-phase rule.
                    cap1 = read_beast_rally_collapsed_march_capacity(first, threshold)
                    cap2 = read_beast_rally_collapsed_march_capacity(second, threshold)
                    if gathering_pair_free(first,second,cap1,cap2):
                        self._log_for_device(target.device, "本轮绿色自建阶段已结束：双帧完整列表仅剩明确采集中的队伍或蓝色队伍且有空槽；保留采集队。")
                        return True
                    if blue_pair_free(first,second,cap1,cap2):
                        self._log_for_device(target.device, "本轮绿色自建阶段已结束：完整列表双帧只有蓝色图标且有空槽；立即进入下一轮，不等蓝色行军/回兵清空。")
                        save_evidence(second, (70,545), "hunt_no_green_blue_remaining", "完整蓝色图标列表与空槽双帧确认；允许下一轮搜索，不宣称所有部队已回城。")
                        return True
                    if (marched and only_joined_rallies(cap1, read_compact_rally_rows(first))
                            and only_joined_rallies(cap2, read_compact_rally_rows(second))
                            and (cap1.used,cap1.total)==(cap2.used,cap2.total)):
                        self._log_for_device(target.device, "本轮已证明绿色集结和行军；完整列表双帧仅剩蓝色盟友集结，本轮队伍已离开占用列表，允许下一轮。")
                        save_evidence(second, (435,450), "hunt_done_allied_remaining", "已见本轮绿色行军，完整列表仅剩蓝色集结；不是单凭总数量减少或绿色消失。")
                        return True
                    used = None
                    if cap1 and cap2 and (cap1.used, cap1.total, cap1.evidence) == (cap2.used, cap2.total, cap2.evidence):
                        if cap1.total and not total:
                            total = cap1.total
                            cycle.total = total
                        if cap1.total == total or cap1.evidence == 'hidden_idle':
                            used = cap1.used
                    now = time.monotonic()
                    if used is None:
                        if not overlay_recovery_used:
                            overlay_recovery_used = True
                            if not ensure_compact_march_panel():
                                return False
                            set_state("顶部列表暂时不可读：复核遮挡并获取新帧，保留本轮队伍")
                        if now - unknown_since >= 24.0:
                            if match_world(first)[0] and match_world(second)[0]:
                                self._log_for_device(target.device, "野外页面仍可确认，队列暂时不可读：保留本轮队伍继续被动恢复，不新增出征。")
                                set_state("本轮队伍仍受保护：被动复查队列，不重复出征")
                                unknown_since = now
                            else:
                                self._log_for_device(target.device, "页面连续24秒无法确认，保留单队记录并停止输入；需要核对当前页面。")
                                return False
                        continue
                    unknown_since = now
                    try:
                        state = cycle.observe(used, total)
                    except ValueError:
                        self._log_for_device(target.device, "侧栏容量变化或数字无效，单队模式停止新增出征。")
                        return False
                    if state == "returned":
                        idle_label = f"0/{total}" if total else "列表已消失（总容量未知）"
                        self._log_for_device(target.device, f"本号顶部列表双帧确认空闲：{idle_label}，允许下一队。")
                        save_evidence(second, (435, 450), "hunt_returned", "顶部列表双帧确认队伍实际回兵，下一轮可开始。")
                        return True
                    if not cycle.seen_busy and now >= proof_deadline:
                        self._log_for_device(target.device, "出征后24秒未证明单队占用，保留体力预留并停止。")
                        return False
                    # Expanded-row coordinates are not a timer source while
                    # monitoring the compact list. Missing time is not return.
                    seconds1 = seconds2 = None
                    timer_text = "时间识别中"
                    if seconds1 is not None and seconds2 is not None and 0 <= seconds1-seconds2 <= 3:
                        timer_text = f"{seconds2//3600:02}:{seconds2//60%60:02}:{seconds2%60:02}"
                    set_state(f"Lv.{profile.beast_level} · {troop_label} · 本号队伍 {used}/{total} · {timer_text}")
                    if now >= heartbeat_at:
                        self._log_for_device(target.device, f"巨兽侧栏监控：本号 {used}/{total}，{timer_text}，等待集结/行军/回兵，未发第二队。")
                        heartbeat_at = now + 25.0
                    if pause():
                        return False
                return False

            def run_one_cycle(*, reconciliation_only: bool = False) -> bool:
                nonlocal action_count, search_race_pause, race_evidence_frames, recent_unconfirmed_dispatch, pending_submission_token, fast_select_three, cached_route_checked
                from wjdr_backend import cancel_beast_rally_submitted_conflict
                first_context = capture()
                first_context_point, _ = match_wilderness_context(first_context)
                item_pending = load_beast_stamina_item_pending(identity)
                fast_world_context = bool(
                    not reconciliation_only and completed_cycles and not item_pending
                    and match_world(first_context)[0]
                    and not daily_network_dialog_is_visible(first_context, threshold)
                    and not match_same_target_conflict(first_context))
                # Routine queue checks use one new world/queue frame.
                # Unknown pages, dialogs and old item guards retain recovery's
                # independently captured pair.
                second_context = first_context if fast_world_context else capture()
                from wjdr_backend import beast_stamina_paid_only_page
                if recent_unconfirmed_dispatch or item_pending:
                    paid_result = beast_close_paid_stamina_overlay(
                        first_context, second_context,
                        paid=lambda frame: beast_stamina_paid_only_page(frame, threshold),
                        close_point=lambda frame: beast_stamina_close_point(frame, threshold),
                        stable=stable, network=lambda frame: daily_network_dialog_is_visible(frame, threshold),
                        pending=lambda: load_beast_stamina_item_pending(identity),
                        reserved=lambda: load_beast_rally_stamina_reserved_any_day(identity),
                        check_active=target.check_active, tap=lambda point: target.tap(*point),
                        capture=capture, match_world=lambda frame: match_world(frame)[0],
                        match_formation=lambda frame: formation_controls_match(frame)[0],
                        archive=lambda token: archive_beast_stamina_fast_batch_uncertain(identity, token),
                        stopped=self.stop_event.is_set)
                    if paid_result is False:
                        self._log_for_device(target.device, '付费体力页或旧账本状态未知，保留记录并停止，未点击购买。')
                        return False
                    if paid_result:
                        if pending_submission_token:
                            clear_beast_rally_submitted_pending(identity, pending_submission_token)
                            pending_submission_token = None
                        if paid_result == 'formation':
                            target.back()
                            card_a, card_b = capture(), capture()
                            if stable(match_beast_rally_open_button(card_a, threshold)[0],
                                      match_beast_rally_open_button(card_b, threshold)[0]):
                                target.check_active()
                                target.back()
                            if not ensure_wilderness():
                                return False
                        if beast_shield_plus_pending(identity):
                            beast_shield_plus_confirm(identity)
                        recent_unconfirmed_dispatch = False
                        item_pending = None
                        reconciliation_only = False
                        set_state('普通体力道具不可用，等待自然恢复')
                        self._log_for_device(target.device, '普通道具不可用；未点击购买，等待自然恢复后搜索新目标。')
                        def paid_wait_world_ready():
                            target.check_active()
                            frame = capture()
                            return bool(target.foreground_is_game()
                                        and not daily_network_dialog_is_visible(frame, threshold)
                                        and match_world(frame)[0])
                        if not beast_wait_for_natural_stamina(
                                self.stop_event.wait, paid_wait_world_ready, self.stop_event.is_set):
                            self._log_for_device(target.device, '等待期间页面或连接变化，保留状态并停止输入。')
                            return False
                        first_context, second_context = capture(), capture()
                        first_context_point, _ = match_wilderness_context(first_context)
                if not reconciliation_only and recent_unconfirmed_dispatch and not item_pending:
                    if match_same_target_conflict(first_context) or match_same_target_conflict(second_context):
                        if not resolve_target_conflict(first_context, second_context):
                            return False
                        if pending_submission_token:
                            if self.stop_event.is_set():
                                return False
                            target.check_active()
                            if self.stop_event.is_set():
                                return False
                            cancelled_cost = cancel_beast_rally_submitted_conflict(
                                identity, pending_submission_token, cancelled_and_formation_restored=True)
                            if cancelled_cost is not None:
                                pending_submission_token = None
                                recent_unconfirmed_dispatch = False
                                self._log_for_device(target.device, f'同目标冲突已取消，核销本次未出征的 {cancelled_cost} 点不确定体力。')
                            elif profile.run_mode == 'fast':
                                clear_beast_rally_submitted_pending(identity, pending_submission_token)
                                pending_submission_token = None
                                recent_unconfirmed_dispatch = False
                        first_context, second_context = capture(), capture()
                        first_context_point, _ = match_wilderness_context(first_context)
                    # The durable submission token identifies the latest input;
                    # it is not a claim that the dispatch succeeded.
                    def begin_submitted_item_batch():
                        nonlocal pending_submission_token
                        token = begin_beast_stamina_fast_batch(identity, count=4 if profile.run_mode == 'fast' else 1)
                        # Write the item guard before consuming the submission
                        # marker: a crash between them cannot repeat item use.
                        clear_beast_rally_submitted_pending(identity, pending_submission_token)
                        pending_submission_token = None
                        return token
                    overlay = beast_recover_receipt_stamina(
                        first_context, second_context,
                        match_item=lambda frame: stamina_more_match(frame)[0],
                        observation=read_beast_stamina_item_observation,
                        network=lambda frame: daily_network_dialog_is_visible(frame, threshold),
                        stable=stable, reserved=lambda: recent_unconfirmed_dispatch,
                        pending=lambda: load_beast_stamina_item_pending(identity),
                        check_active=target.check_active,
                        begin=begin_submitted_item_batch,
                        mark_sent=lambda token: update_beast_stamina_fast_batch(identity, token),
                        complete=finish_item_batch,
                        tap=lambda point: target.tap(*point), capture=capture,
                        close_point=lambda frame: beast_stamina_close_point(frame, threshold),
                        match_world=lambda frame: match_world(frame)[0],
                        match_formation=lambda frame: formation_controls_match(frame)[0],
                        stopped=self.stop_event.is_set, uses=4 if profile.run_mode == 'fast' else 1,
                        fast_batch_tap=(lambda point: beast_tap_stamina_four(target, point)) if profile.run_mode == 'fast' else None,
                        on_use=lambda count: self._log_for_device(target.device, f'已提交体力道具使用操作（{count} 次）。'),
                        wait_between=lambda: False,
                        diagnose=lambda reason: self._log_for_device(target.device, f'体力页处理停止：{reason}。'))
                    if overlay is False:
                        return False
                    if overlay is True:
                        first_context, second_context = capture(), capture()
                        first_context_point, _ = match_wilderness_context(first_context)
                    if overlay == 'formation_after_stamina':
                        # The current live attempt opened the insufficient-stamina
                        # overlay; closing it returned to the same formation.
                        resumed_frame = capture()
                        point, _ = formation_controls_match(resumed_frame)
                        if not beast_resume_dispatch_after_stamina(
                                point, stopped=self.stop_event.is_set, check_active=target.check_active,
                                reserve=lambda: reserve_beast_rally_stamina(identity, 25, estimated=True),
                                tap=lambda p: target.tap(*p),
                                archive=lambda: archive_dispatch(25, charge_session=False)):
                            self._log_for_device(target.device, '体力补充后无法定位出征按钮，未点击。')
                            return False
                        pending_submission_token = load_beast_rally_submitted_pending(identity)
                        recent_unconfirmed_dispatch = True
                        self._log_for_device(target.device, '体力弹窗关闭，已直接点击出征。')
                        return True
                    if (overlay is None and not stable(match_world(first_context)[0], match_world(second_context)[0])):
                        if not ensure_wilderness():
                            return False
                        first_context, second_context = capture(), capture()
                        first_context_point, _ = match_wilderness_context(first_context)
                    if stable(match_world(first_context)[0], match_world(second_context)[0]):
                        if pending_submission_token:
                            clear_beast_rally_submitted_pending(identity, pending_submission_token)
                            pending_submission_token = None
                        if beast_shield_plus_pending(identity):
                            beast_shield_plus_confirm(identity)
                        recent_unconfirmed_dispatch = False
                item_pending = load_beast_stamina_item_pending(identity)
                if item_pending:
                    # A prior prepared item input may have ended on the world
                    # before its acknowledgement was recorded. Archive it as
                    # unknown, never replay it, and start a new target afresh.
                    from wjdr_backend import archive_beast_prepared_item_world_uncertain
                    if beast_reconcile_fast_item_world(
                            first_context, second_context, item_pending,
                            match_world=lambda frame: match_world(frame)[0],
                            network=lambda frame: daily_network_dialog_is_visible(frame, threshold),
                            conflict=match_same_target_conflict, stable=stable,
                            reserved=lambda: load_beast_rally_stamina_reserved_any_day(identity),
                            pending_submission=lambda: pending_submission_token,
                            check_active=target.check_active,
                            archive_prepared=lambda token: archive_beast_prepared_item_world_uncertain(identity, token),
                            archive_sent=lambda token: archive_beast_stamina_fast_batch_uncertain(identity, token),
                            stopped=self.stop_event.is_set):
                        if beast_shield_plus_pending(identity):
                            beast_shield_plus_confirm(identity)
                        self._log_for_device(target.device, "旧体力操作结果未知，已归档且不重放；从野外开始新目标。")
                        item_pending = None
                        reconciliation_only = False
                        recent_unconfirmed_dispatch = False
                if item_pending:
                    if item_pending.get("mode") == "fast":
                        recovered = beast_reconcile_sent_item_overlay(
                            first_context, second_context, item_pending,
                            match_item=lambda frame: stamina_more_controls_match(frame)[0],
                            close_point=lambda frame: beast_stamina_close_point(frame, threshold),
                            match_formation=lambda frame: formation_controls_match(frame)[0],
                            network=lambda frame: daily_network_dialog_is_visible(frame, threshold),
                            stable=stable,
                            reserved=lambda: load_beast_rally_stamina_reserved_any_day(identity),
                            check_active=target.check_active, tap=lambda point: target.tap(*point),
                            capture=capture,
                            archive=lambda token: archive_beast_stamina_fast_batch_uncertain(identity, token),
                            stopped=self.stop_event.is_set)
                        if not recovered:
                            self._log_for_device(target.device, "快速体力批次回执未知，保留记录并停止，未重复点击。")
                            return False
                        self._log_for_device(target.device, "旧体力批次已按未知归档；未重复使用道具或出征。")
                        # The old editor's queue baseline is unavailable. Return
                        # to the world before searching for a fresh target.
                        target.check_active()
                        target.back()
                        card_first, card_second = capture(), capture()
                        card_a = match_beast_rally_open_button(card_first, threshold)[0]
                        card_b = match_beast_rally_open_button(card_second, threshold)[0]
                        if stable(card_a, card_b):
                            target.check_active()
                            target.back()
                        if not ensure_wilderness():
                            self._log_for_device(target.device, "旧编队页返回后未能确认野外，未出征。")
                            return False
                        if pending_submission_token:
                            clear_beast_rally_submitted_pending(identity, pending_submission_token)
                            pending_submission_token = None
                        if beast_shield_plus_pending(identity):
                            beast_shield_plus_confirm(identity)
                        recent_unconfirmed_dispatch = False
                        first_context, second_context = capture(), capture()
                        first_context_point, _ = match_wilderness_context(first_context)
                        reconciliation_only = False
                        item_pending = None
                if item_pending:
                    self._log_for_device(target.device, '旧体力道具使用回执未知，保留记录并停止，未重复点击。')
                    return False
                # Restart reconciliation is read-only. A fresh hidden-idle world
                # proves the previous formation editor is gone, not that the old
                # plus/dispatch succeeded. Account for a reservation first; a
                # crash between accounting and marker removal remains recoverable.
                if reconciliation_only and not self.stop_event.is_set():
                    # An interrupted dispatch has no reconstructible queue
                    # baseline. Handle only the authorized stamina overlay,
                    # then stop with the old dispatch reservation untouched.
                    if old_reservation:
                        recovery = recover_receipt_stamina(first_context, second_context)
                        if recovery is not None:
                            return False
                    cap1 = read_beast_rally_collapsed_march_capacity(first_context, threshold)
                    cap2 = read_beast_rally_collapsed_march_capacity(second_context, threshold)
                    clean_idle = (stable(match_world(first_context)[0], match_world(second_context)[0])
                        and not any(daily_network_dialog_is_visible(frame, threshold)
                                    or match_same_target_conflict(frame)
                                    for frame in (first_context, second_context))
                        and cap1 and cap2 and cap1.used == cap2.used == 0
                        and cap1.total == cap2.total == 0
                        and cap1.evidence == cap2.evidence == 'hidden_idle')
                    if clean_idle:
                        target.check_active()
                        if self.stop_event.is_set():
                            return False
                        reserved = load_beast_rally_stamina_reserved_any_day(identity)
                        if reserved and not reconcile_unconfirmed_hidden_idle(first_context, second_context):
                            return False
                        if beast_shield_plus_pending(identity):
                            target.check_active()
                            if self.stop_event.is_set():
                                return False
                            beast_shield_plus_confirm(identity)
                        self._log_for_device(target.device, "双帧野外空闲：旧加号不再重放；旧出征结果仍未知，预留按不确定体力保守记账。请重新启动任务。")
                        return False
                if beast_shield_plus_pending(identity):
                    receipt = beast_shield_plus_receipt(
                        first_context, second_context, beast_mixed_single_shield,
                        lambda image: match_beast_rally_formation_controls(image, threshold).point,
                        lambda image: daily_network_dialog_is_visible(image, threshold),
                    )
                    if receipt:
                        beast_shield_plus_confirm(identity)
                        self._log_for_device(target.device, "已双帧确认此前盾兵加号生效；当前编队页保留，请重新启动任务。")
                    else:
                        self._log_for_device(target.device, "此前盾兵加号回执未知，保留未决记录，停止以避免重复操作。")
                    return False
                if reconciliation_only:
                    self._log_for_device(target.device, "未决记录尚未完成对账；本次只读取画面，不执行游戏操作。")
                    return False
                if match_same_target_conflict(first_context) or match_same_target_conflict(second_context):
                    resolve_target_conflict(first_context,second_context)
                    return False
                # A previous interrupted mixed-shield setup may have left an
                # empty, disabled formation page.  Do not resume dispatch from
                # it: the queue baseline, target and duration must be proved
                # again.  The guarded target is already bound to this account.
                first_empty = beast_mixed_single_shield(first_context) if (
                    completed_cycles == 0 and profile.troop_mode != "formation"
                    and wanted_troops == (1, 0, 0)
                ) else None
                second_empty = beast_mixed_single_shield(second_context) if first_empty else None
                if (first_empty and first_empty == second_empty and first_empty[:2] == (0, 0)
                        and not daily_network_dialog_is_visible(first_context, threshold)
                        and not daily_network_dialog_is_visible(second_context, threshold)):
                    self._log_for_device(target.device, "双帧确认上次遗留的空编队页，返回野外重新核对队列、目标和集结时长。")
                    target.back()
                    card_first, card_second = capture(), capture()
                    card_a = match_beast_rally_open_button(card_first, threshold)[0]
                    card_b = match_beast_rally_open_button(card_second, threshold)[0]
                    if stable(card_a, card_b):
                        target.back()
                    if not ensure_wilderness():
                        self._log_for_device(target.device, "空编队页返回后未能确认野外，已停止，未出征。")
                        return False
                    first_context, second_context = capture(), capture()
                    first_context_point, _ = match_wilderness_context(first_context)
                if (match_world(second_context)[0]
                        or match_beast_rally_progress_sidebar_expanded(second_context, threshold)[0]):
                    queue_seed = second_context
                else:
                    world = ensure_wilderness()
                    if not world:
                        return False
                    queue_seed = None  # page may have changed during recovery
                if not recover_pending_reservation():
                    return False
                world = wait_queue_capacity_frame(queue_seed)
                if not world:
                    return False
                image, search = world
                loaded_route = False
                if (not cached_route_checked and not completed_cycles and (profile.max_concurrent_rallies == 6 or profile.run_mode == 'fast')
                        and profile.troop_mode != 'formation' and wanted_troops == (1, 0, 0)):
                    cached_route_checked = True
                    saved_three = load_beast_route_coordinates(identity, profile.beast_level, image, action_positions)
                    if saved_three is not None:
                        fast_select_three = saved_three
                        loaded_route = True
                        self._log_for_device(target.device, "已加载本账号相同分辨率和配置的已识别坐标。")
                # A 100 ms blind route can outrun game transitions and tap a
                # different page. Fast mode reuses recognized coordinates, but
                # waits for each corresponding page before the next input.
                if profile.run_mode != 'fast' and beast_should_use_cached_six_route(completed_cycles, loaded_route,
                                                      profile.max_concurrent_rallies, profile.troop_mode,
                                                      wanted_troops, search_race_pause,
                                                      fast_mode=profile.run_mode == 'fast'):
                    clear = action_positions.cached_point('withdraw_all', image)
                    plus = action_positions.cached_point('shield_plus', image)
                    dispatch = action_positions.cached_point('dispatch', image)
                    if not (clear and plus and dispatch):
                        self._log_for_device(target.device, "已识别坐标与当前画面几何不符；未输入，等待重新定位。")
                        return False
                    if clear and plus and dispatch:
                        spent = load_beast_rally_stamina_spent(identity)
                        reserved = load_beast_rally_stamina_reserved(identity)
                        uncertain = load_beast_rally_stamina_uncertain(identity)
                        if not beast_rally_stamina_limit_allows(spent + reserved + uncertain, 25, 0 if profile.run_mode == 'fast' else profile.stamina_limit):
                            self._log_for_device(target.device, "体力上限不足下一次25点保守估算，未操作编队。")
                            return False
                        trace_bundle = (beast_account2_route_trace(
                            identity, lambda message: self._log_for_device(target.device, message))
                            if identity.startswith('mumu:2:android:') else None)
                        trace = trace_bundle[0] if trace_bundle else None
                        try:
                            routed = beast_cached_six_navigation(
                                image, action_positions, target, self.stop_event,
                                select_three=fast_select_three,
                                page_wait_seconds=(0.1 if profile.run_mode == 'fast' else getattr(target, 'beast_navigation_page_delay', 1.0)),
                                trace=trace)
                            if routed is False:
                                return False  # A submitted navigation input is never replayed.
                            if routed is None:
                                self._log_for_device(target.device, "已识别路线坐标缺失或画面几何变化；未输入，等待重新定位。")
                                return False
                            if not beast_fast_single_shield_dispatch(
                                    identity, 25, plus, dispatch, target, self.stop_event,
                                    clear=clear, estimated=True, trace=trace):
                                self._log_for_device(target.device, "单盾快速出征中断，保留未决记录。")
                                return False
                        finally:
                            if trace_bundle:
                                trace_bundle[1]()
                        if routed:
                            action_count += 1
                            self.signals.clicks.emit(action_count)
                            archive_dispatch(25)
                            pending_submission_token = load_beast_rally_submitted_pending(identity)
                            recent_unconfirmed_dispatch = True
                            self._log_for_device(target.device, "按首轮坐标搜索、发起集结并提交1盾；" + ("保留防重标记。" if profile.run_mode == 'fast' else "25点按不确定记账。"))
                            return True
                search = cycle_position('world_search', image, search)
                if not search:
                    return False
                target.tap(*search)
                frame_label = "单帧复核" if completed_cycles else "双帧确认"
                self._log_for_device(target.device, f"点击{frame_label}的野外搜索按钮 {search}。")
                save_evidence(image, search, "world_search", f"野外页{frame_label}后点击唯一搜索按钮。")

                selector = configure_level()
                if not selector:
                    return False
                image, search_button = selector
                search_button = cycle_position('selector_search', image, search_button)
                if not search_button:
                    return False
                target.tap(*search_button)
                self._log_for_device(target.device, f"点击冰原巨兽搜索 {search_button}，等级 {profile.beast_level}。")
                if search_race_pause:
                    delay, search_race_pause = search_race_pause, 0.0
                    self._log_for_device(target.device, "RACE_TEST_READY：搜索完成，按用户要求暂停20秒，请现在抢先集结该巨兽；本次之外不加延迟。")
                    set_state("冲突验收：搜索后暂停20秒，请抢先集结；停止按钮可取消")
                    if self.stop_event.wait(delay):
                        return False
                    target.check_active()
                    race_evidence_frames = 12
                    self._log_for_device(target.device, "RACE_TEST_RESUME：20秒结束，重新取新帧识别目标，不沿用暂停前坐标。")

                opened = wait_for_double(
                    "确认橙色集结按钮",
                    (lambda image: (action_positions.reuse('rally_button', image), None))
                    if completed_cycles else
                    (lambda image: match_beast_rally_open_button(image, threshold)),
                )
                if not opened:
                    return False
                image, rally_button, _ = opened
                rally_button = cycle_position('rally_button', image, rally_button)
                if not rally_button:
                    return False
                target.tap(*rally_button)
                save_evidence(image, rally_button, "rally_button", f"点击{'单' if completed_cycles else '双'}帧确认的橙色冰原巨兽集结按钮。")

                sheet_controls = wait_for_double(
                    "确认发起集结页面",
                    sheet_controls_match,
                )
                if not sheet_controls:
                    return False
                image, _, controls = sheet_controls
                exact_sheet = match_beast_rally_sheet(image, threshold)
                if exact_sheet.state is not BeastRallyState.RALLY_SHEET:
                    three = beast_rally_three_minutes_point(image)
                    if not three:
                        return False
                    if not completed_cycles:
                        fast_select_three = True
                        action_positions.remember('three_minutes', image, three)
                    target.tap(*three)
                    self._log_for_device(target.device, f"点击精确3分钟选项 {three}。")
                # Confirm the exact selected state separately from the broader
                # sheet controls, with the cycle-specific frame count.
                if (completed_cycles and exact_sheet.state is BeastRallyState.RALLY_SHEET
                        and exact_sheet.point and not self.stop_event.is_set()):
                    # Already proved on the fresh post-click controls frame.
                    sheet = (image, exact_sheet.point, exact_sheet)
                else:
                    sheet = wait_for_double(
                        "确认3分钟已选中",
                        exact_sheet_match,
                    )
                if not sheet:
                    return False
                image, launch, _ = sheet
                launch = cycle_position('launch', image, launch)
                if not launch:
                    return False
                target.tap(*launch)
                self._log_for_device(target.device, f"点击3分钟页的发起集结 {launch}。")
                save_evidence(image, launch, "launch_three_minutes", f"3分钟选中并{'单' if completed_cycles else '双'}帧确认后发起集结。")

                if completed_cycles and profile.troop_mode != "formation" and wanted_troops == (1, 0, 0):
                    # Allow the launch animation to settle before cached taps.
                    # This fixed delay is not proof that the page has loaded.
                    if self.stop_event.wait(0.1 if profile.run_mode == 'fast' else 1.0):
                        return False
                    clear = action_positions.cached_point('withdraw_all', image)
                    plus = action_positions.cached_point('shield_plus', image)
                    dispatch = action_positions.cached_point('dispatch', image)
                    if clear and plus and dispatch:
                        spent = load_beast_rally_stamina_spent(identity)
                        reserved = load_beast_rally_stamina_reserved(identity)
                        uncertain = load_beast_rally_stamina_uncertain(identity)
                        if not beast_rally_stamina_limit_allows(spent + reserved + uncertain, 25, 0 if profile.run_mode == 'fast' else profile.stamina_limit):
                            self._log_for_device(target.device, "体力上限不足下一次25点保守估算，未操作编队。")
                            return False
                        if not beast_fast_single_shield_dispatch(identity, 25, plus, dispatch, target,
                                                                  self.stop_event, clear=clear, estimated=True):
                            self._log_for_device(target.device, "单盾快速出征中断，保留未决记录。")
                            return False
                        action_count += 1
                        self.signals.clicks.emit(action_count)
                        archive_dispatch(25)
                        pending_submission_token = load_beast_rally_submitted_pending(identity)
                        recent_unconfirmed_dispatch = True
                        self._log_for_device(target.device, "使用首轮坐标撤回、添加1盾并提交出征；" + ("保留防重标记，" if profile.run_mode == 'fast' else "25点按不确定记账，") + "继续查看队列。")
                        return True

                formation_controls = wait_for_double(
                    "确认出征编组页面",
                    formation_controls_match,
                )
                if not formation_controls:
                    if profile.troop_mode == "formation":
                        self.signals.alert.emit(APP_NAME, "未确认已保存的‘打野’编组，请在游戏中保存并显示该编组；未出征。")
                    return False
                if profile.troop_mode == "formation":
                    image, _, controls = formation_controls
                    point = next ( (p for n, p in controls.anchors if n == "hunt"), None )
                    if not point:
                        return False
                    target.tap(*point)
                    self._log_for_device(target.device, f"点击名称已确认的打野编组 {point}。")
                else:
                    configured = configure_single_shield()
                    if not configured:
                        return False
                    if isinstance(configured, tuple):
                        plus, dispatch, cost = configured
                        spent = load_beast_rally_stamina_spent(identity)
                        reserved = load_beast_rally_stamina_reserved(identity)
                        uncertain = load_beast_rally_stamina_uncertain(identity)
                        if not beast_rally_stamina_limit_allows(spent + reserved + uncertain, cost, 0 if profile.run_mode == 'fast' else profile.stamina_limit):
                            self._log_for_device(target.device, f"体力上限不足下一次 {cost} 消耗，未点击加号或出征。")
                            return False
                        if not beast_fast_single_shield_dispatch(identity, cost, plus, dispatch, target,
                                                                self.stop_event, estimated=True):
                            self._log_for_device(target.device, "单盾快速出征未完成；保留未决记录，不重复输入。")
                            return False
                        action_count += 1
                        self.signals.clicks.emit(action_count)
                        archive_dispatch(cost)
                        pending_submission_token = load_beast_rally_submitted_pending(identity)
                        recent_unconfirmed_dispatch = True
                        if (not completed_cycles and (profile.max_concurrent_rallies == 6 or profile.run_mode == 'fast')
                                and profile.troop_mode != 'formation' and wanted_troops == (1, 0, 0)):
                            try:
                                if save_beast_route_coordinates(identity, profile.beast_level,
                                                                action_positions, fast_select_three):
                                    self._log_for_device(target.device, "已保存本账号首轮识别坐标，供同分辨率重启使用。")
                            except (OSError, ValueError) as exc:
                                self._log_for_device(target.device, f"坐标缓存保存失败，继续运行：{exc}")
                        self._log_for_device(target.device, f"提交单盾出征 {dispatch}；" + ("保留防重标记，" if profile.run_mode == 'fast' else f"{cost}点按不确定记账，") + "继续查看队列。")
                        return True

                # Formation selection or custom troop setup has already run.
                # Reuse its known control; no stamina OCR or final image check.
                setup_image, dispatch, _ = formation_controls
                dispatch = cycle_position('dispatch', setup_image, dispatch)
                if not dispatch:
                    return False
                cost = 25  # conservative estimate; never recorded as actual spend
                spent = load_beast_rally_stamina_spent(identity)
                reserved = load_beast_rally_stamina_reserved(identity)
                uncertain = load_beast_rally_stamina_uncertain(identity)
                if not beast_rally_stamina_limit_allows(spent + reserved + uncertain, cost, 0 if profile.run_mode == 'fast' else profile.stamina_limit):
                    self._log_for_device(target.device, "体力上限不足下一次25点保守估算，未出征。")
                    return False
                target.check_active()
                reserve_beast_rally_stamina(identity, cost, estimated=True)
                target.tap(*dispatch)
                action_count += 1
                self.signals.clicks.emit(action_count)
                archive_dispatch(cost)
                pending_submission_token = load_beast_rally_submitted_pending(identity)
                recent_unconfirmed_dispatch = True
                self._log_for_device(target.device, f"提交{troop_label}出征 {dispatch}；" + ("保留防重标记，" if profile.run_mode == 'fast' else "25点按不确定记账，") + "继续查看队列。")
                return True

            # The reconciliation-only branch also calls run_one_cycle(), which
            # reads this value when handling an interrupted item transaction.
            completed_cycles = 0
            if reconciliation_only and not pending_submission_token:
                if (self.stop_event.is_set() or not target.foreground_is_game()
                        or not run_one_cycle(reconciliation_only=True)):
                    return
                # A recovered item overlay can complete a new cycle. Continue
                # the normal loop instead of ending after that one submission.
                completed_cycles = 1
                if ((initial_test_cycles and completed_cycles >= initial_test_cycles)
                        or self.stop_event.wait(0.1 if profile.run_mode == 'fast' else 1.0)):
                    return

            self._log_for_device(
                target.device,
                f"开始冰原巨兽自动集结：Lv.{profile.beast_level}，"
                f"体力上限 {'不限' if profile.run_mode == 'fast' or profile.stamina_limit == 0 else profile.stamina_limit}；"
                f"同时集结上限 {profile.max_concurrent_rallies}；"
                f"{'极速模式' if profile.run_mode == 'fast' else '普通模式'}；"
                "首轮定位，出征后不等待回执；6队模式按左侧容量调度。",
            )
            set_state("启动：确认野外与既有队列")
            # Optional bounded live acceptance; normal UI runs remain continuous.
            max_cycles = initial_test_cycles
            self._log_for_device(target.device, f"仅本次自动验收：最多 {max_cycles} 轮；之后手动开始不受此限制。" if max_cycles else "连续运行模式：无轮数上限；按体力设置或用户停止结束。")
            while not self.stop_event.is_set():
                if not target.foreground_is_game():
                    set_state("游戏不在前台：零输入停止")
                    self._log_for_device(target.device, "游戏不在前台；巨兽集结未输入并停止。")
                    break
                if not run_one_cycle():
                    if retry_target_requested and not self.stop_event.is_set():
                        retry_target_requested=False
                        continue
                    break
                completed_cycles += 1
                target_conflicts = 0
                if max_cycles and completed_cycles >= max_cycles:
                    set_state(f"已完成 {completed_cycles} 轮验证；其他行军状态以游戏为准")
                    break
                # Wait once between submitted teams; stopping interrupts the delay.
                if self.stop_event.wait(0.1 if profile.run_mode == 'fast' else 1.0):
                    break
            if self.stop_event.is_set():
                set_state("已停止")
            self._log_for_device(target.device, "冰原巨兽自动集结已停止。")

        def supervised_job() -> None:
            from wjdr_beast_supervision import (start_if_unchanged, stop_if_current,
                perform_if_current, verify_bound_identity, run_preinput_recovery)
            if self.stop_event.is_set():
                return
            intent = start_if_unchanged(identity, previous_generation)
            if not intent:
                self.log("巨兽运行意图在启动期间发生变化，未执行游戏操作。")
                return
            generation = intent["generation"]
            self._managed_beast = (identity, generation)
            target.input_gate = lambda action: perform_if_current(identity, generation, action)
            try:
                if self.stop_event.is_set():
                    return
                run_preinput_recovery(
                    job, target, self.stop_event, identity, generation,
                    lambda: verify_bound_identity(self.adb, target.device, identity),
                    lambda message: self._log_for_device(target.device, message),
                )
            finally:
                try:
                    stop_if_current(identity, generation)
                except Exception as exc:
                    self.log(f"巨兽停止意图写入失败，未安排自动重启：{exc}")
                if getattr(self, "_managed_beast", None) == (identity, generation):
                    self._managed_beast = None

        self._start_worker(target.device, supervised_job, expected_identity=identity)

    def _start_daily_task_flow(self) -> None:
        """Collect exactly one verified ``每日登录 (1/1)`` reward, if present.

        This controller intentionally has no generic navigation, close, back,
        scroll, chest, shop, ``前往`` or acceleration action.  It can send at
        most two input events in a run: a confirmed main-city Daily Tasks
        entry tap and the confirmed target-row green ``领取`` tap.
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
            # The configured value is an upper preference, not a fixed sleep.
            # MuMu screenshot latency is sampled continuously: fast devices
            # poll at roughly 0.12--0.20 s, while slower devices receive a
            # small adaptive cushion. No single passive wait exceeds 1.5 s.
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
            claim_tapped = False
            claims = 0
            last_state: DailyTaskState | None = None
            last_point: tuple[int, int] | None = None
            state_streak = 0
            last_ui_state = ""
            transition_deadline = 0.0

            def set_state(text: str) -> None:
                nonlocal last_ui_state
                if text != last_ui_state:
                    last_ui_state = text
                    self.signals.daily_task_state.emit(text)

            def points_are_stable(
                first: tuple[int, int] | None,
                second: tuple[int, int] | None,
            ) -> bool:
                if first is None or second is None:
                    return first is second
                # Template centres can move by a few pixels between captures;
                # a large move is a different control and restarts the proof.
                return abs(first[0] - second[0]) <= 16 and abs(first[1] - second[1]) <= 16

            def observe(state: DailyTaskState, point: tuple[int, int] | None) -> int:
                nonlocal last_state, last_point, state_streak
                if state is last_state and points_are_stable(point, last_point):
                    state_streak += 1
                else:
                    last_state, state_streak = state, 1
                last_point = point
                return state_streak

            self._log_for_device(
                target.device,
                f"开始每日登录领取：检查间隔 {interval:.1f} 秒；每次运行最多领取一次；F8 可全局停止。",
            )
            set_state("监听中：等待主城任务入口或已打开的每日任务页")

            while not self.stop_event.is_set():
                now = time.monotonic()
                if duration and now - started >= duration * 60:
                    self._log_for_device(target.device, "已达到每日任务最长等待时间；未执行额外输入。")
                    break
                try:
                    if guard and not target.foreground_is_game():
                        set_state("已暂停：游戏不在模拟器前台")
                    else:
                        image = capture_daily_image()
                        if daily_network_dialog_is_visible(image, threshold):
                            set_state(
                                "游戏显示网络/账号离线：保持零输入并被动复查；不点击重新连接或联系客服"
                            )
                            if adaptive_operation_wait(minimum=0.5, maximum=3.0):
                                break
                            continue
                        page = detect_daily_task_state(image, threshold)

                        # A reviewed blocker is not an unknown page to
                        # dismiss: it can be a payment, purchase, or other
                        # obscuring layer.  Stop before matching any
                        # navigation anchor, and never attempt a close/back
                        # recovery.
                        blocked_state = getattr(DailyTaskState, "BLOCKED", None)
                        if blocked_state is not None and page.state is blocked_state:
                            set_state("检测到付费或遮挡页面：不输入并停止")
                            self._log_for_device(
                                target.device,
                                f"每日任务流程检测到付费/遮挡页面（分数 {page.score:.3f}）；未执行输入，已停止。",
                            )
                            break

                        # The city-entry matcher is deliberately invoked only
                        # before this worker has sent its one permitted city
                        # navigation tap.  It is never used as a generic UI
                        # coordinate source after navigation has begun.
                        city_point: tuple[int, int] | None = None
                        if not city_entry_tapped and page.state is DailyTaskState.CITY_ENTRY:
                            city_point, _city_score = match_daily_city_entry(image, threshold)

                        stable_point = city_point if page.state is DailyTaskState.CITY_ENTRY else page.point
                        streak = observe(page.state, stable_point)
                        if streak == 1:
                            self._log_for_device(
                                target.device,
                                f"每日任务页面识别：{self._daily_task_page_label(page.state)}（分数 {page.score:.3f}）。",
                            )

                        # An unknown state includes any popup or page that is
                        # outside the very small reviewed workflow.  Do not
                        # try to dismiss it or recover through a blind tap.
                        if page.state is DailyTaskState.UNKNOWN:
                            set_state("检测到未知页面或弹窗：不输入并停止")
                            self._log_for_device(target.device, "每日任务流程遇到未知页面/弹窗；未执行输入，已停止。")
                            break

                        if claim_tapped:
                            # A claim is counted only after two fresh frames
                            # prove we are still on a reviewed Daily Tasks
                            # page and the actionable CLAIM_READY state has
                            # disappeared.  No second claim attempt is ever
                            # made, even if the old button remains visible.
                            if page.state in (
                                DailyTaskState.DAILY_PAGE,
                                DailyTaskState.DAILY_LOGIN_COMPLETED,
                            ):
                                set_state("已点击领取：复核每日页与领取状态消失")
                                if streak >= 2:
                                    claims = 1
                                    self.signals.clicks.emit(claims)
                                    set_state("每日登录领取已确认：本次流程已停止")
                                    self._log_for_device(target.device, "每日登录领取状态已在同一每日任务页消失；已计数并停止。")
                                    break
                                continue
                            if page.state is DailyTaskState.CLAIM_READY:
                                set_state("领取后按钮仍存在：不再输入并停止")
                                self._log_for_device(target.device, "领取后仍识别到原领取状态；未再次点击，已停止。")
                                break
                            set_state("领取后页面未按预期切换：不输入并停止")
                            self._log_for_device(target.device, "领取后未回到已验证每日页；未执行任何恢复操作，已停止。")
                            break

                        if page.state is DailyTaskState.CITY_ENTRY:
                            if city_entry_tapped:
                                set_state("任务入口点击后页面未切换：不再输入并停止")
                                self._log_for_device(target.device, "主城任务入口点击后仍是原入口；未重复点击，已停止。")
                                break
                            if not city_point:
                                set_state("主城任务入口坐标未复核：不输入并停止")
                                self._log_for_device(target.device, "主城任务入口缺少二次坐标证明；未执行输入，已停止。")
                                break
                            set_state(f"已确认主城任务入口（{streak}/2）")
                            if streak >= 2:
                                target.tap(*city_point)
                                city_entry_tapped = True
                                self._log_for_device(target.device, f"点击已确认的主城每日任务入口 {city_point}（仅此一次）。")
                            continue

                        if page.state is DailyTaskState.DAILY_PAGE:
                            # This state is a safe waiting state.  It can be
                            # the initial page (direct start) or the page that
                            # follows the one permitted city-entry tap.  It is
                            # not a tap target.  A daily run is a bounded
                            # scan, not an idle monitor: once two fresh frames
                            # prove this page has no reviewed login-claim
                            # state, stop instead of waiting or searching for
                            # a different green control.
                            if streak >= 2:
                                set_state("已确认每日任务页：未见可验证的每日登录领取，停止")
                                self._log_for_device(
                                    target.device,
                                    "每日任务页已复核但未见已验证的每日登录领取按钮；未执行输入，已停止。",
                                )
                                break
                            else:
                                set_state("正在复核每日任务页（1/2）")
                            continue

                        if page.state is DailyTaskState.DAILY_LOGIN_COMPLETED:
                            # Before our own claim this means the intended row
                            # has no verified green button (usually already
                            # claimed).  It is explicitly terminal rather
                            # than an opportunity to tap a nearby control.
                            set_state("每日登录无可领取按钮：不输入并停止")
                            self._log_for_device(target.device, "每日登录已完成或无有效领取按钮；未执行输入，已停止。")
                            break

                        if page.state is DailyTaskState.CLAIM_READY:
                            # CLAIM_READY itself contains the independently
                            # verified Daily Tasks header and selected tab, so
                            # direct starts on the page remain safe even if
                            # the loading state skipped a standalone
                            # DAILY_PAGE screenshot.
                            if not page.point:
                                set_state("领取按钮坐标未复核：不输入并停止")
                                self._log_for_device(target.device, "领取状态缺少安全坐标；未执行输入，已停止。")
                                break
                            set_state(f"已确认每日登录 (1/1) 领取按钮（{streak}/2）")
                            if streak >= 2:
                                target.tap(*page.point)
                                claim_tapped = True
                                self._log_for_device(target.device, f"点击已验证的每日登录领取按钮 {page.point}（仅此一次）。")
                            continue

                        # A future backend enum value must fail closed until
                        # it has explicit controller review.
                        set_state("检测到未允许的每日任务状态：不输入并停止")
                        self._log_for_device(target.device, "每日任务流程检测到未允许的状态；未执行输入，已停止。")
                        break
                except Exception as exc:
                    set_state("每日任务识别异常：不输入并停止")
                    self._log_for_device(target.device, f"每日任务识别异常；未执行恢复输入，已停止：{exc}")
                    break

                if self.stop_event.wait(interval):
                    break

            result = "领取 1 次" if claims else "未领取"
            set_state(f"已停止：{result}")
            self._log_for_device(target.device, f"每日登录自动领取已停止（{result}）。")

        self._start_worker(target.device, job)

    def _start_daily_rewards_flow(self) -> None:
        start_daily_rewards_flow(self)

    def _start_red_packet_flow(self) -> None:
        """Start the visual, one-claim-at-a-time alliance red-packet workflow.

        The small envelope marker never authorizes a claim by itself.  It only
        arms a bounded page-flow; every subsequent tap uses a fresh screenshot
        and a more specific visual state from :func:`detect_red_packet_state`.
        """
        if not self.adb:
            QMessageBox.warning(self, APP_NAME, "尚未连接 MuMu。")
            return
        required = [resource_path(asset) for asset, _name in RED_PACKET_BUILTIN_TEMPLATES]
        missing = [path for path in required if not path.is_file()]
        if missing:
            names = "、".join(path.name for path in missing)
            QMessageBox.warning(self, APP_NAME, f"红包识别素材缺失：{names}\n请重新解压完整程序包。")
            return

        target = self.adb.clone_for_device()
        interval = self.red_packet_interval_spin.value()
        duration = self.red_packet_duration_spin.value()
        max_claims = self.red_packet_max_claims_spin.value()
        guard = self.red_packet_guard_check.isChecked()
        threshold = 0.90

        def job() -> None:
            claims, failures = 0, 0
            started = time.monotonic()
            armed = False
            marker_streak = 0
            marker_clear_streak = 0
            # These are deliberately separate: a pre-existing chat panel
            # must never look like a successful click by this worker.
            chat_entry_tapped = False
            chat_entry_established = False
            waiting_for_clear = False
            opened_at: float | None = None
            result_closed_at: float | None = None
            back_sent = False
            last_state: RedPacketState | None = None
            state_streak = 0
            action_attempts: dict[str, int] = {}
            # Counts belong to the whole *armed marker cycle*, rather than a
            # visual state.  A transient UNKNOWN frame must never buy another
            # set of taps for the same notification.
            cycle_locked = False
            next_input_at = 0.0
            hold_until = 0.0
            last_notice_key = ""
            last_notice_at = -30.0
            last_ui_state = ""

            def set_state(text: str) -> None:
                nonlocal last_ui_state
                if text != last_ui_state:
                    last_ui_state = text
                    self.signals.red_packet_state.emit(text)

            def notice(key: str, message: str, minimum_gap: float = 20.0) -> None:
                nonlocal last_notice_key, last_notice_at
                now = time.monotonic()
                if key != last_notice_key or now - last_notice_at >= minimum_gap:
                    self._log_for_device(target.device, message)
                    last_notice_key, last_notice_at = key, now

            def reset_to_marker_listener(reason: str) -> None:
                """End the current armed cycle without sending any input.

                The notification can disappear because it was withdrawn,
                expired, or belongs to a different chat event.  In all of
                those cases this worker must be passive until a *new* marker
                is confirmed twice.
                """
                nonlocal armed, marker_streak, marker_clear_streak
                nonlocal chat_entry_tapped, chat_entry_established
                nonlocal waiting_for_clear, opened_at, result_closed_at, back_sent
                nonlocal last_state, state_streak, cycle_locked, next_input_at, hold_until
                armed = False
                marker_streak = 0
                marker_clear_streak = 0
                chat_entry_tapped = False
                chat_entry_established = False
                waiting_for_clear = False
                opened_at = result_closed_at = None
                back_sent = False
                last_state = None
                state_streak = 0
                action_attempts.clear()
                cycle_locked = False
                next_input_at = 0.0
                hold_until = 0.0
                self._log_for_device(target.device, reason)
                set_state("监听中：等待右下角红包浮标")

            def tap_for_state(
                action: str,
                point: tuple[int, int],
                description: str,
                limit: int = 3,
            ) -> bool:
                nonlocal next_input_at, hold_until, cycle_locked, chat_entry_tapped
                now = time.monotonic()
                if cycle_locked or now < next_input_at or now < hold_until:
                    return False
                count = action_attempts.get(action, 0)
                if count >= limit:
                    # Do not let a different classifier result or an UNKNOWN
                    # frame reset this failure.  The marker must first
                    # disappear, then a later new marker may arm a new cycle.
                    cycle_locked = True
                    hold_until = float("inf")
                    set_state(f"{description}已连续尝试 {limit} 次：等待红包浮标消失后再解锁")
                    notice(
                        f"stalled-{action}",
                        f"{description}连续 {limit} 次未发生预期页面切换；本轮已锁定，等待红包浮标消失后才会重新监听。",
                        30.0,
                    )
                    return False
                target.tap(*point)
                action_attempts[action] = count + 1
                if action == "chat-entry":
                    # This means an ADB tap was successfully sent.  It still
                    # does not establish the chain until CHAT_PANEL is seen
                    # on a following screenshot.
                    chat_entry_tapped = True
                next_input_at = now + max(0.8, min(2.5, interval))
                self._log_for_device(target.device, f"{description} {point}（第 {count + 1}/{limit} 次）。")
                return True

            self._log_for_device(
                target.device,
                f"开始自动抢熔炉升级红包：检查间隔 {interval:.1f} 秒；F8 可全局停止。",
            )
            set_state("监听中：等待右下角红包浮标")
            while not self.stop_event.is_set():
                now = time.monotonic()
                if duration and now - started >= duration * 60:
                    self._log_for_device(target.device, "已达到红包运行时长。")
                    break
                if max_claims and claims >= max_claims:
                    self._log_for_device(target.device, "已达到最多领取次数。")
                    break
                try:
                    if guard and not target.foreground_is_game():
                        marker_streak = 0
                        set_state("已暂停：游戏不在模拟器前台")
                        notice("not-foreground", "游戏不在前台，本轮不截图、不点击。")
                    else:
                        image = target.screenshot()

                        # At rest, the notification marker is the only thing
                        # examined.  A city chat launcher by itself can never
                        # cause navigation.
                        if not armed:
                            marker, marker_score = match_red_packet_marker(image, 0.84)
                            if marker:
                                marker_streak += 1
                                set_state(f"发现红包浮标，正在复核（{marker_streak}/2）")
                                if marker_streak >= 2:
                                    armed = True
                                    marker_streak = 0
                                    action_attempts.clear()
                                    cycle_locked = False
                                    chat_entry_tapped = False
                                    chat_entry_established = False
                                    last_state = None
                                    self._log_for_device(
                                        target.device,
                                        f"红包浮标已连续确认，分数 {marker_score:.3f}；开始检查联盟频道。",
                                    )
                                    set_state("已确认浮标：正在打开聊天")
                            else:
                                marker_streak = 0
                                set_state("监听中：等待右下角红包浮标")
                        else:
                            # Until this worker itself has sent the city chat
                            # tap, a current marker match is required.  A
                            # pre-existing chat/Alliance/red-packet page is
                            # never accepted as proof of that action.
                            # A capped action ends the established chain.  It
                            # is then passive again and only unlocks after the
                            # original marker has cleared (or after the user
                            # returns to a page where that clear is visible).
                            if not chat_entry_tapped or cycle_locked:
                                marker_live, _marker_live_score = match_red_packet_marker(image, 0.84)
                                if not marker_live:
                                    reset_to_marker_listener("已武装但尚未确认聊天打开，或本轮动作已锁定时红包浮标消失：安全复位为监听，本帧未执行任何输入。")
                                    continue

                            page = detect_red_packet_state(image, threshold)
                            if page.state is last_state:
                                state_streak += 1
                            else:
                                last_state = page.state
                                state_streak = 1
                                self._log_for_device(
                                    target.device,
                                    f"红包页面识别：{self._red_packet_page_label(page.state)}（分数 {page.score:.3f}）。",
                                )

                            if chat_entry_tapped and page.state is RedPacketState.CHAT_PANEL:
                                chat_entry_established = True

                            if not chat_entry_tapped:
                                # The only actionable pre-tap page is the
                                # verified city chat entry.  Do not turn a
                                # manually opened panel or an arbitrary game
                                # overlay into a route to Alliance.
                                if page.state not in (RedPacketState.CHAT_ENTRY, RedPacketState.MARKER, RedPacketState.UNKNOWN):
                                    set_state("已确认浮标：等待主城聊天入口，不接管当前聊天/联盟页面")
                                    notice(
                                        "pre-chat-entry-unexpected-page",
                                        f"尚未由本流程点击聊天入口，却识别到{self._red_packet_page_label(page.state)}；不执行导航。",
                                    )
                                    continue
                            elif not chat_entry_established:
                                # A sent tap is not enough.  The next route
                                # step becomes eligible only after the chat
                                # panel itself is independently observed.
                                set_state("已点击主城聊天入口：等待聊天面板确认")
                                if page.state is not RedPacketState.CHAT_PANEL:
                                    notice(
                                        "chat-entry-not-established",
                                        f"聊天入口点击后尚未确认聊天面板（当前{self._red_packet_page_label(page.state)}）；不执行后续导航。",
                                    )
                                    continue

                            # After a verified result has been closed, the
                            # only permitted inputs are a guarded back from a
                            # confirmed chat and then passive marker-clear
                            # observation in the city.  This prevents a second
                            # tap on the same card.
                            if waiting_for_clear:
                                if page.state in (
                                    RedPacketState.ALLIANCE_CHAT,
                                    RedPacketState.FURNACE_PACKET,
                                    RedPacketState.FURNACE_PACKET_CLAIMED,
                                ):
                                    set_state("领取已确认：正在返回主城继续监听")
                                    if result_closed_at and not back_sent and now - result_closed_at >= 0.7:
                                        target.back()
                                        back_sent = True
                                        next_input_at = now + max(0.8, min(2.5, interval))
                                        self._log_for_device(target.device, "已确认联盟聊天页，安全返回主城。")
                                elif page.state is RedPacketState.CHAT_ENTRY:
                                    marker, _score = match_red_packet_marker(image, 0.84)
                                    if marker:
                                        marker_clear_streak = 0
                                        set_state("领取已确认：等待红包浮标消失")
                                    else:
                                        marker_clear_streak += 1
                                        set_state(f"领取已确认：复核浮标已消失（{marker_clear_streak}/2）")
                                        if marker_clear_streak >= 2:
                                            reset_to_marker_listener("红包浮标已消失，恢复监听下一次红包。")
                                elif page.state is RedPacketState.CLAIM_RESULT_READY:
                                    set_state("领取已确认：正在关闭结果页")
                                    if result_closed_at and now - result_closed_at >= 12.0:
                                        notice("result-close-stalled", "结果页关闭后仍未切回聊天，已停止后续输入，请手动检查。", 30.0)
                                else:
                                    set_state("领取已确认：等待页面回到主城")
                            elif page.state is RedPacketState.CLAIM_RESULT_READY:
                                # A reward result is counted only when it
                                # immediately follows this worker's own
                                # exactly-once “开启” tap.
                                if opened_at and now - opened_at <= 12.0 and page.point:
                                    claims += 1
                                    self.signals.clicks.emit(claims)
                                    waiting_for_clear = True
                                    result_closed_at = now
                                    set_state("已确认领取结果：正在安全关闭")
                                    target.tap(*page.point)
                                    next_input_at = now + max(0.8, min(2.5, interval))
                                    self._log_for_device(
                                        target.device,
                                        f"已确认红包领取结果，累计领取 {claims} 次；关闭结果页 {page.point}。",
                                    )
                                else:
                                    set_state("发现结果页，但未关联本次开启：不点击")
                                    notice("unlinked-result", "结果页未与本窗口刚刚的开启操作关联，不关闭、不计数。")
                            elif opened_at:
                                # Never press “开启” twice.  If the result is
                                # not positively observed soon afterwards,
                                # leave the page untouched for the user.
                                if now - opened_at >= 12.0:
                                    set_state("开启后未确认结果：已停止输入，请手动检查")
                                    notice("open-result-timeout", "开启后 12 秒未识别到红包结果页，已停止后续输入。", 30.0)
                                    hold_until = max(hold_until, now + 30.0)
                            elif page.state is RedPacketState.CHAT_ENTRY:
                                set_state("已确认浮标：正在打开聊天")
                                if state_streak >= 2 and page.point:
                                    tap_for_state("chat-entry", page.point, "点击主城聊天入口")
                            elif page.state is RedPacketState.CHAT_PANEL:
                                set_state("聊天已打开：正在切换联盟频道")
                                if state_streak >= 2:
                                    # The tab point was measured in the game
                                    # content area.  Map it through the
                                    # backend's letterbox-aware viewport
                                    # helper instead of scaling against an
                                    # entire ADB capture.
                                    alliance_tab = map_content_point((720, 228), (1440, 2560), image)
                                    tap_for_state("alliance-tab", alliance_tab, "点击联盟频道", limit=3)
                            elif page.state is RedPacketState.ALLIANCE_CHAT:
                                set_state("已在联盟频道：等待熔炉升级红包")
                                notice("alliance-wait", "已确认联盟频道，当前未见“熔炉升级红包”卡片，原地等待。")
                            elif page.state is RedPacketState.FURNACE_PACKET_CLAIMED:
                                set_state("熔炉升级红包已领取：不点击，等待红包浮标消失")
                                notice(
                                    "furnace-packet-claimed",
                                    "已识别熔炉升级红包的已领取状态；不打开、不领取，等待红包浮标消失后再解锁。",
                                )
                                # A claimed card is a terminal state for this
                                # notification.  After two visual frames,
                                # leave the confirmed Alliance chat once and
                                # return to passive city-marker monitoring.
                                # This is deliberately a Back action only;
                                # the card itself is never tapped.
                                if state_streak >= 2 and not back_sent:
                                    waiting_for_clear = True
                                    result_closed_at = now
                                    target.back()
                                    back_sent = True
                                    next_input_at = now + max(0.8, min(2.5, interval))
                                    self._log_for_device(target.device, "已领取红包已复核，安全返回主城继续监听。")
                            elif page.state is RedPacketState.FURNACE_PACKET:
                                set_state("已确认熔炉升级红包：正在打开")
                                if state_streak >= 2 and page.point:
                                    tap_for_state("furnace-card", page.point, "点击熔炉升级红包卡", limit=2)
                            elif page.state is RedPacketState.DETAIL_OPEN_READY:
                                set_state("已确认红包详情与开启按钮：正在开启")
                                if state_streak >= 2 and page.point:
                                    if tap_for_state("open", page.point, "点击红包开启按钮", limit=1):
                                        opened_at = time.monotonic()
                            elif page.state is RedPacketState.FURNACE_DETAIL:
                                set_state("已打开熔炉红包详情：未见可用开启按钮")
                                notice("detail-not-ready", "已打开熔炉升级红包详情，但未同时识别到可用“开启”按钮，不点击。")
                            elif page.state is RedPacketState.MARKER:
                                set_state("已确认浮标：未识别主城聊天入口")
                                notice("no-chat-entry", "已看到红包浮标，但未确认主城聊天入口，不执行坐标点击。")
                            else:
                                set_state("已确认浮标：未知页面，等待安全识别")
                                notice("unknown-page", f"红包流程未识别当前页面（最高分 {page.score:.3f}），不执行点击。")
                    failures = 0
                except Exception as exc:
                    failures += 1
                    backoff = min(MAX_SINGLE_WAIT_SECONDS, max(interval, 0.25) * (2 ** min(failures, 4)))
                    self._log_for_device(target.device, f"红包识别失败（{failures}）：{exc}；{backoff:.1f} 秒后安全重试。")
                    set_state("识别异常：正在安全重试")
                    if self.stop_event.wait(backoff):
                        break
                    continue
                if self.stop_event.wait(interval):
                    break
            set_state("已停止")
            self._log_for_device(target.device, f"自动抢熔炉升级红包已停止，累计领取 {claims} 次。")

        self._start_worker(target.device, job)

    def _start_custom_clicker(self) -> None:
        self._start_clicker("template" if self.mode_combo.currentIndex() == 0 else "fixed")

    def _start_clicker(self, mode: str) -> None:
        if not self.adb:
            QMessageBox.warning(self, APP_NAME, "尚未连接 MuMu。")
            return
        template = TEMPLATE_DIR / self.template_combo.currentText()
        if mode == "template" and not template.is_file():
            QMessageBox.warning(self, APP_NAME, "请选择有效的按钮模板。")
            return
        if mode == "fixed" and (not self.selected_point or not self.selected_source_size):
            QMessageBox.warning(self, APP_NAME, "请先在设备中心的实时画面上单击要连点的位置。")
            return
        fixed_point = self.selected_point
        fixed_source_size = self.selected_source_size
        target = self.adb.clone_for_device()
        interval = self.interval_spin.value()
        duration = self.duration_spin.value()
        max_clicks = self.max_clicks_spin.value()
        threshold = self.threshold_slider.value() / 100
        guard = self.guard_check.isChecked()

        def job() -> None:
            clicks, failures = 0, 0
            started, last_idle = time.monotonic(), -30.0
            label = "识图运行" if mode == "template" else "固定坐标连点"
            self.log(f"开始{label}，F8 可全局停止。")
            while not self.stop_event.is_set():
                if duration and time.monotonic() - started >= duration * 60:
                    self.log("已达到运行时长。")
                    break
                if max_clicks and clicks >= max_clicks:
                    self.log("已达到最多点击次数。")
                    break
                try:
                    if guard and not target.foreground_is_game():
                        elapsed = time.monotonic() - started
                        if elapsed - last_idle >= 30:
                            self.log("游戏不在前台，本轮暂停。")
                            last_idle = elapsed
                    elif mode == "fixed":
                        assert fixed_point is not None and fixed_source_size is not None
                        point = scale_recorded_point(fixed_point, fixed_source_size, target.screen_size())
                        target.tap(*point)
                        clicks += 1
                        self.signals.clicks.emit(clicks)
                        if clicks == 1 or clicks % 20 == 0:
                            self.log(f"已点击 {clicks} 次，坐标 {point}。")
                    else:
                        image = target.screenshot()
                        point, score = match_template(image, template, threshold, template_reference_size(template))
                        matched_name = template.stem
                        if point:
                            target.tap(*point)
                            clicks += 1
                            self.signals.clicks.emit(clicks)
                            self.log(f"识别成功并点击 {matched_name} {point}，相似度 {score:.3f}，累计 {clicks} 次。")
                        else:
                            elapsed = time.monotonic() - started
                            if elapsed - last_idle >= 30:
                                self.log(f"等待按钮出现，当前最高相似度 {score:.3f}。")
                                last_idle = elapsed
                    failures = 0
                except Exception as exc:
                    failures += 1
                    self.log(f"本轮失败（{failures}/3）：{exc}")
                    if failures >= 3:
                        break
                if self.stop_event.wait(interval):
                    break
            self.log(f"运行结束，共点击 {clicks} 次。")

        self._start_worker(target.device, job)

    def _start_worker(self, device: str, callback: Callable[[], None], *, expected_identity: str | None = None) -> None:
        scheduled = getattr(self, "_launching_schedule", None)
        def schedule_state(state: str, note: str) -> bool:
            if not scheduled:
                return True
            return schedules.transition(scheduled["id"], scheduled["token"], state, note, path=self.schedule_path)
        if self.worker and self.worker.is_alive():
            QMessageBox.information(self, APP_NAME, "当前窗口已有任务正在运行。")
            return
        self.stop_event.clear()
        self.signals.clicks.emit(0)

        # Do not use the raw ADB serial as the lock key: MuMu may report one
        # Android instance through more than one serial.  ``connect`` has
        # already cached Android IDs; the defensive fallback keeps a worker
        # usable if a device disappears between scanning and start.
        try:
            lease_key = (expected_identity if expected_identity is not None else
                         self.adb.device_identity(device) if self.adb else f"adb:{device.lower()}")
        except Exception:
            lease_key = f"adb:{device.lower()}"

        def protected() -> None:
            lease = DeviceLease(lease_key)
            if not lease.acquire():
                if scheduled:
                    schedule_state("failed", "该手机已被另一个窗口占用，未启动重复任务")
                self.log(f"实例 {device} 已被另一个窗口占用，本窗口未启动任务。")
                self.signals.alert.emit(APP_NAME, f"{device} 已在另一个助手窗口运行。\n为防止重复点击，本窗口未启动任务。")
                return
            try:
                if expected_identity is not None:
                    from wjdr_beast_supervision import verify_bound_identity
                    if not self.adb or not verify_bound_identity(self.adb, device, expected_identity):
                        self.log(f"实例 {device} 实时身份与启动账号不符或无法确认；未执行游戏操作。")
                        return
                if self.stop_event.is_set():
                    return
                if not schedule_state("running", "已核验手机并取得独占权限；仅触发一次"):
                    return
                self.signals.running.emit(True, "运行中")
                callback()
            except InterruptedError:
                self.log("任务已取消；未重试或重放后续输入。")
            except Exception as exc:
                if scheduled:
                    try:
                        schedule_state("failed", f"流程异常结束：{type(exc).__name__}: {exc}")
                    except Exception:
                        pass
                self.log(f"任务线程异常：{type(exc).__name__}: {exc}")
                self.signals.alert.emit(
                    APP_NAME,
                    f"任务线程已安全停止。\n{type(exc).__name__}: {exc}",
                )
            finally:
                lease.release()
                self.stop_event.set()
                self.signals.running.emit(False, "已停止")
                if scheduled:
                    try:
                        schedule_state("finished", "任务流程已结束或用户停止；不会再次自动启动")
                    except Exception as exc:
                        self.log(f"定时任务结束记录写入失败：{exc}；不会重放启动")

        self.worker = threading.Thread(target=protected, daemon=True)
        self.worker.start()

    def stop_all(self) -> None:
        self.stop_event.set()
        self._cancel_managed_beast()
        try:
            if self.adb and hasattr(self, "schedule_path"):
                schedules.cancel_waiting(self.adb.device_identity(), claimed_only=True, path=self.schedule_path)
        except Exception as exc:
            self.log(f"取消正在核验的预约失败：{exc}")
        self.log("已发出停止指令。")

    def _cancel_managed_beast(self) -> None:
        current = getattr(self, "_managed_beast", None)
        if current:
            try:
                from wjdr_beast_supervision import stop_if_current
                stop_if_current(*current)
            except Exception as exc:
                self.log(f"巨兽停止意图写入失败，当前线程已停止且不会安排自动重启：{exc}")

    def _update_runtime(self) -> None:
        seconds = max(0, int(time.monotonic() - self.started_at))
        self.runtime_label.setText(f"{seconds // 3600:02d}:{seconds // 60 % 60:02d}:{seconds % 60:02d}")

    def _assistant_command(self, device: str, startup_mode: str | None = None) -> list[str]:
        if getattr(sys, "frozen", False):
            command = [sys.executable]
        else:
            command = [sys.executable, str(Path(__file__).resolve())]
        command += ["--device", device]
        if startup_mode == "help":
            command += ["--auto-help", "--interval", str(self.interval_spin.value())]
        elif startup_mode == "red_packet":
            command += ["--auto-red-packet", "--interval", str(self.red_packet_interval_spin.value())]
        elif startup_mode == "daily":
            command += ["--auto-daily", "--interval", str(self.daily_interval_spin.value())]
        elif startup_mode == "beast_rally":
            command += ["--auto-beast-rally"]
        return command

    def _spawn_instance(self, device: str, startup_mode: str | None = None) -> None:
        try:
            children = getattr(self, "_child_windows", {})
            existing = children.get(device)
            if existing is not None and existing.poll() is None:
                self.log(f"{device} 的独立窗口已打开，请在该窗口操作。")
                return
            env = {key: value for key, value in os.environ.items()
                   if not key.startswith("WJDR_QA_") and key not in
                   {"WJDR_BEAST_MAX_CYCLES", "WJDR_BEAST_SEARCH_RACE_PAUSE"}}
            children[device] = subprocess.Popen(
                self._assistant_command(device, startup_mode),
                cwd=str(Path(sys.executable).resolve().parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parent),
                creationflags=CREATE_NO_WINDOW,
                env=env,
            )
            self._child_windows = children
            mode_text = {
                "help": "并开始联盟帮助",
                "red_packet": "并开始抢红包",
                "daily": "并开始每日任务自动化",
                "beast_rally": "并开始冰原巨兽自动集结",
            }.get(startup_mode, "")
            self.log(f"已为 {device} 打开独立窗口{mode_text}。")
        except OSError as exc:
            QMessageBox.warning(self, APP_NAME, f"无法打开独立窗口：{exc}")

    def _open_device_manager(self) -> None:
        dialog = LightSettingsDialog(self)
        dialog.setWindowTitle("多手机窗口 · 每台设备独立运行")
        dialog.resize(680, 400)
        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(24, 22, 24, 22)
        title = QLabel("为不同手机打开独立窗口")
        title.setStyleSheet("font-size:20px;font-weight:700")
        layout.addWidget(title)
        hint = QLabel("打开窗口不会启动游戏任务。各窗口独立设置、开始和停止，F8 可统一急停。")
        hint.setWordWrap(True)
        layout.addWidget(hint)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        body = QWidget()
        self._set_window_background(scroll.viewport())
        self._set_window_background(body)
        rows = QVBoxLayout(body)
        items = [self.device_combo.itemData(i) for i in range(self.device_combo.count())]
        for item in items:
            row = QHBoxLayout()
            label = QLabel(f"#{item['index']}  {item['name']}\n{item['device']} · {item.get('resolution', '—')}")
            label.setWordWrap(True)
            row.addWidget(label, 1)
            button = QPushButton("打开独立窗口")
            button.setAccessibleName(f"打开手机 {item['device']}")
            button.clicked.connect(lambda _checked=False, device=item['device']: self._spawn_instance(device))
            row.addWidget(button)
            rows.addLayout(row)
        if not items:
            rows.addWidget(QLabel("未发现在线手机，请启动 MuMu 后点击顶部“扫描”。"))
        rows.addStretch()
        scroll.setWidget(body)
        layout.addWidget(scroll, 1)
        all_windows = QPushButton("打开其他所有手机（不启动任务）")
        all_windows.setEnabled(bool(items))
        all_windows.clicked.connect(lambda: self._open_other_windows())
        layout.addWidget(all_windows)
        close = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        close.button(QDialogButtonBox.StandardButton.Close).setText("关闭")
        close.rejected.connect(dialog.reject)
        layout.addWidget(close)
        dialog.exec()

    def _open_other_windows(self) -> None:
        current = self.adb.device if self.adb else None
        for device in self.devices:
            if device != current:
                self._spawn_instance(device)

    def _open_selected_window(self) -> None:
        if self.adb:
            self._spawn_instance(self.adb.device)

    def _start_all_instances(self, startup_mode: str = "help") -> None:
        if not self.devices:
            QMessageBox.warning(self, APP_NAME, "没有发现运行中的 MuMu 实例。")
            return
        for device in self.devices:
            self._spawn_instance(device, startup_mode)
        mode_text = {
            "help": "联盟帮助",
            "red_packet": "联盟红包",
            "daily": "每日任务自动化",
            "beast_rally": "冰原巨兽自动集结",
        }.get(startup_mode, "自动化")
        self.log(f"已为 {len(self.devices)} 个实例分别启动{mode_text}窗口。")

    def _load_tasks(self) -> dict[str, list[dict[str, Any]]]:
        try:
            data = json.loads(TASK_FILE.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                return {str(key): list(value) for key, value in data.items() if isinstance(value, list)}
        except (OSError, json.JSONDecodeError, TypeError):
            pass
        return {name: [dict(step) for step in steps] for name, steps in DEFAULT_TASKS.items()}

    def _refresh_tasks(self) -> None:
        current = self.task_combo.currentText() if hasattr(self, "task_combo") else ""
        self.task_combo.blockSignals(True)
        self.task_combo.clear()
        self.task_combo.addItems(sorted(self.tasks))
        if current in self.tasks:
            self.task_combo.setCurrentText(current)
        self.task_combo.blockSignals(False)
        self._load_selected_task()

    def _load_selected_task(self) -> None:
        self.active_steps = [dict(step) for step in self.tasks.get(self.task_combo.currentText(), [])]
        self._render_steps()

    def _step_text(self, index: int, step: dict[str, Any]) -> str:
        action = step.get("action")
        if action == "tap":
            detail = f"点击 ({step['x']}, {step['y']})"
        elif action == "wait":
            detail = f"等待 {step['seconds']} 秒"
        elif action == "back":
            detail = "Android 返回键"
        else:
            detail = f"识图 {step.get('template')} · 超时 {step.get('timeout', 15)} 秒"
        return f"{index + 1:02d}    {detail}"

    def _render_steps(self) -> None:
        self.step_list.clear()
        self.step_list.addItems([self._step_text(i, step) for i, step in enumerate(self.active_steps)])

    def _new_task(self) -> None:
        name, ok = QInputDialog.getText(self, APP_NAME, "新任务名称：")
        if ok and name.strip():
            self.tasks[name.strip()] = []
            self._refresh_tasks()
            self.task_combo.setCurrentText(name.strip())

    def _task_add_point(self) -> None:
        if not self.selected_point or not self.selected_source_size:
            QMessageBox.information(self, APP_NAME, "请先在设备中心画面上选择一个坐标。")
            return
        self.active_steps.append({"action": "tap", "x": self.selected_point[0], "y": self.selected_point[1], "width": self.selected_source_size[0], "height": self.selected_source_size[1]})
        self._render_steps()

    def _task_add_wait(self) -> None:
        value, ok = QInputDialog.getDouble(self, APP_NAME, "等待秒数：", 2.0, 0, 86400, 1)
        if ok:
            self.active_steps.append({"action": "wait", "seconds": value})
            self._render_steps()

    def _task_add_back(self) -> None:
        self.active_steps.append({"action": "back"})
        self._render_steps()

    def _task_add_template(self) -> None:
        names = [self.template_combo.itemText(i) for i in range(self.template_combo.count())]
        if not names:
            return
        name, ok = QInputDialog.getItem(self, APP_NAME, "选择模板：", names, 0, False)
        if ok:
            timeout, accepted = QInputDialog.getDouble(self, APP_NAME, "等待超时（秒）：", 15, 1, 86400, 1)
            if accepted:
                self.active_steps.append({"action": "template", "template": name, "timeout": timeout, "threshold": self.threshold_slider.value() / 100})
                self._render_steps()

    def _delete_task_step(self) -> None:
        row = self.step_list.currentRow()
        if 0 <= row < len(self.active_steps):
            self.active_steps.pop(row)
            self._render_steps()

    def _save_task(self) -> None:
        name = self.task_combo.currentText().strip()
        if not name:
            return
        self.tasks[name] = [dict(step) for step in self.active_steps]
        TASK_FILE.write_text(json.dumps(self.tasks, ensure_ascii=False, indent=2), encoding="utf-8")
        self.log(f"已保存任务：{name}")

    def _delete_task(self) -> None:
        name = self.task_combo.currentText()
        if name and QMessageBox.question(self, APP_NAME, f"删除任务“{name}”？") == QMessageBox.StandardButton.Yes:
            self.tasks.pop(name, None)
            TASK_FILE.write_text(json.dumps(self.tasks, ensure_ascii=False, indent=2), encoding="utf-8")
            self._refresh_tasks()

    def _run_task(self) -> None:
        if not self.adb or not self.active_steps:
            QMessageBox.information(self, APP_NAME, "请先连接实例并准备任务步骤。")
            return
        target = self.adb.clone_for_device()
        steps = [dict(step) for step in self.active_steps]
        repeat, repeat_wait = self.repeat_check.isChecked(), self.repeat_wait.value()

        def job() -> None:
            round_number = 0
            self.log("开始执行任务序列。")
            while not self.stop_event.is_set():
                round_number += 1
                for index, step in enumerate(steps):
                    if self.stop_event.is_set():
                        break
                    action = step.get("action")
                    try:
                        if action in {"tap", "back", "template"} and not target.foreground_is_game():
                            self.log(f"步骤 {index + 1} 暂停：游戏不在前台。")
                            foreground_deadline = (
                                time.monotonic() + AUTOMATION_STEP_TIMEOUT_SECONDS
                            )
                            while (
                                time.monotonic() < foreground_deadline
                                and not self.stop_event.wait(MAX_SINGLE_WAIT_SECONDS)
                            ):
                                if target.foreground_is_game():
                                    break
                            if not target.foreground_is_game():
                                self.log(
                                    f"步骤 {index + 1} 在 30 秒内未回到游戏前台；本轮停止。"
                                )
                                self.stop_event.set()
                                break
                        if action == "tap":
                            point = scale_recorded_point((int(step["x"]), int(step["y"])), (int(step["width"]), int(step["height"])), target.screen_size())
                            target.tap(*point)
                            self.log(f"步骤 {index + 1}：点击 {point}。")
                        elif action == "wait":
                            if self.stop_event.wait(
                                min(
                                    MAX_SINGLE_WAIT_SECONDS,
                                    bounded_step_timeout(float(step["seconds"])),
                                )
                            ):
                                break
                        elif action == "back":
                            target.back()
                        elif action == "template":
                            deadline = time.monotonic() + bounded_step_timeout(
                                float(step.get("timeout", 15))
                            )
                            while time.monotonic() < deadline and not self.stop_event.is_set():
                                path = TEMPLATE_DIR / str(step["template"])
                                point, score = match_template(target.screenshot(), path, float(step.get("threshold", 0.88)), template_reference_size(path))
                                if point:
                                    target.tap(*point)
                                    self.log(f"步骤 {index + 1}：识图点击 {point}，相似度 {score:.3f}。")
                                    break
                                self.stop_event.wait(1)
                    except Exception as exc:
                        self.log(f"步骤 {index + 1} 失败：{exc}")
                        self.stop_event.set()
                        break
                if not repeat or self.stop_event.is_set():
                    break
                if self.stop_event.wait(
                    min(MAX_SINGLE_WAIT_SECONDS, bounded_step_timeout(repeat_wait))
                ):
                    break
            self.log("任务序列已结束。")

        self._start_worker(target.device, job)

    def _hotkey_loop(self) -> None:
        if os.name != "nt":
            return
        user32 = ctypes.windll.user32
        was_down = False
        while not self.closing.is_set():
            down = bool(user32.GetAsyncKeyState(0x77) & 0x8000)
            if down and not was_down:
                self.stop_event.set()
                self._cancel_managed_beast()
                try:
                    schedules.cancel_waiting(path=self.schedule_path)
                except Exception as exc:
                    self.log(f"F8取消预约记录失败：{exc}")
                self.log("检测到全局 F8，正在停止。")
            was_down = down
            time.sleep(0.08)

    def closeEvent(self, event: Any) -> None:
        self.closing.set()
        self.stop_event.set()
        self._cancel_managed_beast()
        event.accept()


def main() -> None:
    parser = argparse.ArgumentParser(description=APP_NAME)
    parser.add_argument("--device")
    parser.add_argument("--auto-help", action="store_true")
    parser.add_argument("--all-auto-help", action="store_true")
    parser.add_argument("--auto-red-packet", action="store_true")
    parser.add_argument("--all-auto-red-packet", action="store_true")
    parser.add_argument("--auto-daily", action="store_true")
    parser.add_argument("--all-auto-daily", action="store_true")
    parser.add_argument("--auto-beast-rally", action="store_true")
    parser.add_argument("--all-auto-beast-rally", action="store_true")
    parser.add_argument("--interval", type=float, help="自动流程的点击 / 识别间隔（秒）")
    args = parser.parse_args()
    if hasattr(Qt.ApplicationAttribute, "AA_EnableHighDpiScaling"):
        QApplication.setAttribute(Qt.ApplicationAttribute.AA_EnableHighDpiScaling, True)
    app = QApplication(sys.argv[:1])
    app.setApplicationName(APP_NAME)
    app.setApplicationVersion(APP_VERSION)
    app.setOrganizationName("WJDR Tools")
    app.setStyle("Fusion")
    window = MainWindow(
        args.device,
        args.auto_help,
        args.all_auto_help,
        args.auto_red_packet,
        args.all_auto_red_packet,
        args.auto_daily,
        args.all_auto_daily,
        args.auto_beast_rally,
        args.all_auto_beast_rally,
        args.interval,
    )
    window.show()
    qa_page = os.environ.get("WJDR_QA_PAGE")
    if qa_page and qa_page.isdigit():
        window._show_page(min(int(qa_page), window.stack.count() - 1))
    qa_screenshot = os.environ.get("WJDR_QA_SCREENSHOT")
    if qa_screenshot:
        def save_qa_screenshot() -> None:
            saved = window.grab().save(qa_screenshot, "PNG")
            window.log(f"UI 验收截图{'已保存' if saved else '保存失败'}：{qa_screenshot}")

        QTimer.singleShot(3500, save_qa_screenshot)
    raise SystemExit(app.exec())


if __name__ == "__main__":
    main()
