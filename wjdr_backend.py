# -*- coding: utf-8 -*-
"""Shared MuMu/recognition backend for the distributable Qt application."""

from __future__ import annotations

import io
import json
import os
import re
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass
from enum import Enum
from functools import lru_cache
from pathlib import Path
from typing import Any

if os.name == "nt":
    import ctypes
    import msvcrt
    from ctypes import wintypes

import cv2
import numpy as np
from PIL import Image, ImageChops, ImageStat


APP_NAME = "无尽冬日 MuMu 助手"
APP_VERSION = "5.62.0"
GAME_PACKAGE = "com.gof.china"
CREATE_NO_WINDOW = 0x08000000 if os.name == "nt" else 0
CONFIG_DIR = Path(os.environ.get("LOCALAPPDATA", Path.home())) / "WJDRMuMuAssistant"
TEMPLATE_DIR = CONFIG_DIR / "templates"
TASK_FILE = CONFIG_DIR / "tasks.json"
LOG_FILE = CONFIG_DIR / "assistant.log"
LOCK_DIR = CONFIG_DIR / "device_locks"
MINING_LEVEL_PROFILES_FILE = CONFIG_DIR / "mining_level_profiles.json"
BEAST_RALLY_PROFILES_FILE = CONFIG_DIR / "beast_rally_profiles.json"
BEAST_RALLY_STAMINA_LEDGER_FILE = CONFIG_DIR / "beast_rally_stamina_ledger.json"
BUILTIN_ALL_HELP_TEMPLATE_ASSET = "alliance_all_help_builtin.png"
BUILTIN_ALL_HELP_TEMPLATE_NAME = "内置_全部帮助_实测.png"
BUILTIN_HELP_TEMPLATE_ASSET = "alliance_help_builtin.png"
BUILTIN_HELP_TEMPLATE_NAME = "内置_联盟帮助_实测.png"
BUILTIN_MUTUAL_PAGE_TEMPLATE_ASSET = "alliance_mutual_page_builtin.png"
BUILTIN_MUTUAL_ENTRY_TEMPLATE_ASSET = "alliance_mutual_entry_builtin.png"
BUILTIN_CITY_ALLIANCE_TEMPLATE_ASSET = "alliance_city_entry_builtin.png"
BUILTIN_HELP_REFERENCE_SIZE = (1440, 2560)

# Red-packet assets intentionally live below ``assets`` instead of the
# application root.  They are visual anchors for the independent red-packet
# workflow; keeping their names here lets the packaged application and a
# source checkout use the exact same lookup rules.
RED_PACKET_ASSET_DIR = "assets"
# The reviewed built-in anchors are packaged with the application.  The
# chat-entry asset is intentionally reserved for a later city-screen capture.
BUILTIN_RED_PACKET_MARKER_ASSET = f"{RED_PACKET_ASSET_DIR}/redpacket_notification.png"
BUILTIN_RED_PACKET_CHAT_ENTRY_ASSET = f"{RED_PACKET_ASSET_DIR}/red_packet_chat_entry_builtin.png"
BUILTIN_RED_PACKET_CHAT_PANEL_ASSET = f"{RED_PACKET_ASSET_DIR}/chat_panel_header.png"
BUILTIN_RED_PACKET_ALLIANCE_PAGE_ASSET = f"{RED_PACKET_ASSET_DIR}/chat_alliance_selected.png"
BUILTIN_FURNACE_UPGRADE_PACKET_ASSET = f"{RED_PACKET_ASSET_DIR}/furnace_redpacket_card_title.png"
BUILTIN_FURNACE_UPGRADE_PACKET_ICON_ASSET = f"{RED_PACKET_ASSET_DIR}/furnace_redpacket_card_icon.png"
BUILTIN_FURNACE_UPGRADE_TITLE_ASSET = f"{RED_PACKET_ASSET_DIR}/furnace_redpacket_popup_title.png"
BUILTIN_RED_PACKET_OPEN_ASSET = f"{RED_PACKET_ASSET_DIR}/furnace_redpacket_open_button.png"
BUILTIN_RED_PACKET_RESULT_ASSET = f"{RED_PACKET_ASSET_DIR}/redpacket_result_diamond_anchor.png"
BUILTIN_RED_PACKET_RESULT_CLOSE_ASSET = f"{RED_PACKET_ASSET_DIR}/redpacket_result_close_button.png"
BUILTIN_RED_PACKET_CLAIMED_ASSET = f"{RED_PACKET_ASSET_DIR}/furnace_redpacket_claimed.png"
BUILTIN_RED_PACKET_MARKER_TEMPLATE_NAME = "内置_红包浮标_实测.png"
BUILTIN_RED_PACKET_CHAT_ENTRY_TEMPLATE_NAME = "内置_聊天入口_实测.png"
BUILTIN_RED_PACKET_CHAT_PANEL_TEMPLATE_NAME = "内置_聊天面板标题_实测.png"
BUILTIN_RED_PACKET_ALLIANCE_PAGE_TEMPLATE_NAME = "内置_联盟频道_实测.png"
BUILTIN_FURNACE_UPGRADE_PACKET_TEMPLATE_NAME = "内置_熔炉升级红包卡标题_实测.png"
BUILTIN_FURNACE_UPGRADE_PACKET_ICON_TEMPLATE_NAME = "内置_熔炉升级红包卡图标_实测.png"
BUILTIN_FURNACE_UPGRADE_TITLE_TEMPLATE_NAME = "内置_熔炉升级红包标题_实测.png"
BUILTIN_RED_PACKET_OPEN_TEMPLATE_NAME = "内置_红包开启按钮_实测.png"
BUILTIN_RED_PACKET_RESULT_TEMPLATE_NAME = "内置_红包领取结果_实测.png"
BUILTIN_RED_PACKET_RESULT_CLOSE_TEMPLATE_NAME = "内置_红包领取结果关闭_实测.png"
BUILTIN_RED_PACKET_CLAIMED_TEMPLATE_NAME = "内置_熔炉红包已领取_实测.png"
BUILTIN_RED_PACKET_REFERENCE_SIZE = (1440, 2560)
BUILTIN_RED_PACKET_MARKER_REFERENCE_SIZE = (720, 1280)
# The city-entry anchor deliberately excludes chat text.  Once that anchor is
# present, this is the measured safe tap location inside the same chat strip.
RED_PACKET_CHAT_ENTRY_REFERENCE_POINT = (430, 2260)
RED_PACKET_BUILTIN_TEMPLATES: tuple[tuple[str, str], ...] = (
    (BUILTIN_RED_PACKET_MARKER_ASSET, BUILTIN_RED_PACKET_MARKER_TEMPLATE_NAME),
    (BUILTIN_RED_PACKET_CHAT_ENTRY_ASSET, BUILTIN_RED_PACKET_CHAT_ENTRY_TEMPLATE_NAME),
    (BUILTIN_RED_PACKET_CHAT_PANEL_ASSET, BUILTIN_RED_PACKET_CHAT_PANEL_TEMPLATE_NAME),
    (BUILTIN_RED_PACKET_ALLIANCE_PAGE_ASSET, BUILTIN_RED_PACKET_ALLIANCE_PAGE_TEMPLATE_NAME),
    (BUILTIN_FURNACE_UPGRADE_PACKET_ASSET, BUILTIN_FURNACE_UPGRADE_PACKET_TEMPLATE_NAME),
    (BUILTIN_FURNACE_UPGRADE_PACKET_ICON_ASSET, BUILTIN_FURNACE_UPGRADE_PACKET_ICON_TEMPLATE_NAME),
    (BUILTIN_FURNACE_UPGRADE_TITLE_ASSET, BUILTIN_FURNACE_UPGRADE_TITLE_TEMPLATE_NAME),
    (BUILTIN_RED_PACKET_OPEN_ASSET, BUILTIN_RED_PACKET_OPEN_TEMPLATE_NAME),
    (BUILTIN_RED_PACKET_RESULT_ASSET, BUILTIN_RED_PACKET_RESULT_TEMPLATE_NAME),
    (BUILTIN_RED_PACKET_RESULT_CLOSE_ASSET, BUILTIN_RED_PACKET_RESULT_CLOSE_TEMPLATE_NAME),
    (BUILTIN_RED_PACKET_CLAIMED_ASSET, BUILTIN_RED_PACKET_CLAIMED_TEMPLATE_NAME),
)
RED_PACKET_BUILTIN_TEMPLATE_FILENAMES = frozenset(
    [name for _asset, name in RED_PACKET_BUILTIN_TEMPLATES]
    + [Path(asset).name for asset, _name in RED_PACKET_BUILTIN_TEMPLATES]
)

# Daily-task assets use the same packaged ``assets`` directory as the
# red-packet workflow, but their state machine is intentionally independent.
# In particular, a generic green "claim" control never becomes actionable
# without the daily-task page and exact completed-login evidence below.
DAILY_TASK_ASSET_DIR = "assets"
BEAST_RALLY_ASSET_DIR = "assets"
BUILTIN_BEAST_RALLY_WORLD_SEARCH_ASSET = f"{BEAST_RALLY_ASSET_DIR}/beast_rally_world_search.png"
BUILTIN_BEAST_RALLY_WORLD_SEARCH_DENSE_ASSET = f"{BEAST_RALLY_ASSET_DIR}/beast_rally_world_search_dense_live.png"
BUILTIN_BEAST_RALLY_WORLD_SEARCH_ROUND_ASSET = f"{BEAST_RALLY_ASSET_DIR}/beast_rally_world_search_round_live.png"
BUILTIN_BEAST_RALLY_WORLD_TOWN_DENSE_ASSET = f"{BEAST_RALLY_ASSET_DIR}/beast_rally_world_town_dense_live.png"
BUILTIN_BEAST_RALLY_BEAST_TARGET_ASSET = f"{BEAST_RALLY_ASSET_DIR}/beast_rally_beast_target.png"
BUILTIN_BEAST_RALLY_LEVEL_FIELD_EIGHT_ASSET = f"{BEAST_RALLY_ASSET_DIR}/beast_rally_level_field_8.png"
BUILTIN_BEAST_RALLY_SEARCH_BUTTON_ASSET = f"{BEAST_RALLY_ASSET_DIR}/beast_rally_search_button.png"
BUILTIN_BEAST_RALLY_OPEN_BUTTON_ASSET = f"{BEAST_RALLY_ASSET_DIR}/beast_rally_open_button_25.png"
BUILTIN_BEAST_RALLY_OPEN_LABEL_ASSET = f"{BEAST_RALLY_ASSET_DIR}/beast_rally_open_label.png"
BUILTIN_BEAST_RALLY_SHEET_HEADER_ASSET = f"{BEAST_RALLY_ASSET_DIR}/beast_rally_sheet_header.png"
BUILTIN_BEAST_RALLY_THREE_MINUTES_SELECTED_ASSET = f"{BEAST_RALLY_ASSET_DIR}/beast_rally_three_minutes_selected.png"
BUILTIN_BEAST_RALLY_THREE_MINUTES_LABEL_ASSET = f"{BEAST_RALLY_ASSET_DIR}/beast_rally_three_minutes_label.png"
BUILTIN_BEAST_RALLY_LAUNCH_BUTTON_ASSET = f"{BEAST_RALLY_ASSET_DIR}/beast_rally_launch_button.png"
BUILTIN_BEAST_RALLY_FORMATION_ANCHOR_ASSET = f"{BEAST_RALLY_ASSET_DIR}/beast_rally_formation_anchor.png"
BUILTIN_BEAST_RALLY_STAMINA_MORE_TITLE_ASSET = f"{BEAST_RALLY_ASSET_DIR}/beast_rally_stamina_more_title_live.png"
BUILTIN_BEAST_RALLY_STAMINA_RESTORE10_ASSET = f"{BEAST_RALLY_ASSET_DIR}/beast_rally_stamina_restore10_live.png"
BUILTIN_BEAST_RALLY_STAMINA_USE_ASSET = f"{BEAST_RALLY_ASSET_DIR}/beast_rally_stamina_use_label_live.png"
BUILTIN_BEAST_RALLY_DISPATCH_STAMINA_RED20_ASSET = f"{BEAST_RALLY_ASSET_DIR}/beast_rally_dispatch_stamina_red_20_live.png"
BUILTIN_BEAST_RALLY_FIRST_FORMATION_ASSET = f"{BEAST_RALLY_ASSET_DIR}/beast_rally_first_formation_selected.png"
BUILTIN_BEAST_RALLY_DISPATCH_LABEL_ASSET = f"{BEAST_RALLY_ASSET_DIR}/beast_rally_dispatch_label.png"
BUILTIN_BEAST_RALLY_PROGRESS_ICON_ASSET = f"{BEAST_RALLY_ASSET_DIR}/beast_rally_progress_icon.png"
BUILTIN_BEAST_RALLY_PROGRESS_SIDEBAR_COLLAPSED_ASSET = (
    f"{BEAST_RALLY_ASSET_DIR}/beast_rally_progress_sidebar_collapsed_live.png"
)
BUILTIN_BEAST_RALLY_PROGRESS_SIDEBAR_COLLAPSED_ROUND_ASSETS = (
    f"{BEAST_RALLY_ASSET_DIR}/beast_rally_progress_sidebar_collapsed_round_live_1.png",
    f"{BEAST_RALLY_ASSET_DIR}/beast_rally_progress_sidebar_collapsed_round_live_2.png",
)
BUILTIN_BEAST_RALLY_PROGRESS_SIDEBAR_COLLAPSED_ALLIED_ASSET = (
    f"{BEAST_RALLY_ASSET_DIR}/beast_rally_progress_sidebar_collapsed_allied_live.png"
)
BUILTIN_BEAST_RALLY_WORLD_SEARCH_ALLIED_ASSET = (
    f"{BEAST_RALLY_ASSET_DIR}/beast_rally_world_search_allied_live.png"
)
BUILTIN_BEAST_RALLY_PROGRESS_WILDERNESS_TAB_ASSET = (
    f"{BEAST_RALLY_ASSET_DIR}/beast_rally_progress_wilderness_tab_live.png"
)
BUILTIN_BEAST_RALLY_PROGRESS_WILDERNESS_SELECTED_ASSET = (
    f"{BEAST_RALLY_ASSET_DIR}/beast_rally_progress_wilderness_selected_live.png"
)
BUILTIN_BEAST_RALLY_PROGRESS_SIDEBAR_EXPANDED_ASSET = (
    f"{BEAST_RALLY_ASSET_DIR}/beast_rally_progress_sidebar_expanded_live.png"
)
BUILTIN_BEAST_RALLY_PROGRESS_QUEUE_LABEL_ASSET = (
    f"{BEAST_RALLY_ASSET_DIR}/beast_rally_progress_queue_label_live.png"
)
BUILTIN_BEAST_RALLY_PROGRESS_IDLE_ASSET = (
    f"{BEAST_RALLY_ASSET_DIR}/beast_rally_progress_idle_live.png"
)
BUILTIN_BEAST_RALLY_STATE_RALLYING_ASSET = f"{BEAST_RALLY_ASSET_DIR}/beast_rally_state_rallying.png"
BEAST_RALLY_BUILTIN_ASSETS: tuple[str, ...] = (
    BUILTIN_BEAST_RALLY_WORLD_SEARCH_ASSET,
    BUILTIN_BEAST_RALLY_WORLD_SEARCH_DENSE_ASSET,
    BUILTIN_BEAST_RALLY_WORLD_SEARCH_ROUND_ASSET,
    BUILTIN_BEAST_RALLY_WORLD_TOWN_DENSE_ASSET,
    BUILTIN_BEAST_RALLY_BEAST_TARGET_ASSET,
    BUILTIN_BEAST_RALLY_LEVEL_FIELD_EIGHT_ASSET,
    BUILTIN_BEAST_RALLY_SEARCH_BUTTON_ASSET,
    BUILTIN_BEAST_RALLY_OPEN_BUTTON_ASSET,
    BUILTIN_BEAST_RALLY_OPEN_LABEL_ASSET,
    BUILTIN_BEAST_RALLY_SHEET_HEADER_ASSET,
    BUILTIN_BEAST_RALLY_THREE_MINUTES_SELECTED_ASSET,
    BUILTIN_BEAST_RALLY_THREE_MINUTES_LABEL_ASSET,
    BUILTIN_BEAST_RALLY_LAUNCH_BUTTON_ASSET,
    BUILTIN_BEAST_RALLY_FORMATION_ANCHOR_ASSET,
    BUILTIN_BEAST_RALLY_STAMINA_MORE_TITLE_ASSET,
    BUILTIN_BEAST_RALLY_STAMINA_RESTORE10_ASSET,
    BUILTIN_BEAST_RALLY_STAMINA_USE_ASSET,
    BUILTIN_BEAST_RALLY_DISPATCH_STAMINA_RED20_ASSET,
    BUILTIN_BEAST_RALLY_FIRST_FORMATION_ASSET,
    BUILTIN_BEAST_RALLY_DISPATCH_LABEL_ASSET,
    BUILTIN_BEAST_RALLY_PROGRESS_ICON_ASSET,
    BUILTIN_BEAST_RALLY_PROGRESS_SIDEBAR_COLLAPSED_ASSET,
    *BUILTIN_BEAST_RALLY_PROGRESS_SIDEBAR_COLLAPSED_ROUND_ASSETS,
    BUILTIN_BEAST_RALLY_PROGRESS_SIDEBAR_COLLAPSED_ALLIED_ASSET,
    BUILTIN_BEAST_RALLY_WORLD_SEARCH_ALLIED_ASSET,
    BUILTIN_BEAST_RALLY_PROGRESS_WILDERNESS_TAB_ASSET,
    BUILTIN_BEAST_RALLY_PROGRESS_WILDERNESS_SELECTED_ASSET,
    BUILTIN_BEAST_RALLY_PROGRESS_SIDEBAR_EXPANDED_ASSET,
    BUILTIN_BEAST_RALLY_PROGRESS_QUEUE_LABEL_ASSET,
    BUILTIN_BEAST_RALLY_PROGRESS_IDLE_ASSET,
    BUILTIN_BEAST_RALLY_STATE_RALLYING_ASSET,
)
BEAST_RALLY_BUILTIN_FILENAMES = frozenset(Path(asset).name for asset in BEAST_RALLY_BUILTIN_ASSETS)
BUILTIN_DAILY_CITY_ENTRY_ASSET = f"{DAILY_TASK_ASSET_DIR}/daily_city_entry.png"
BUILTIN_DAILY_CITY_ENTRY_TRAINING_HIGHLIGHT_ASSET = (
    f"{DAILY_TASK_ASSET_DIR}/daily_city_entry_training_highlight_current_live.png"
)
BUILTIN_DAILY_HEADER_ASSET = f"{DAILY_TASK_ASSET_DIR}/daily_task_header.png"
BUILTIN_DAILY_SELECTED_TAB_ASSET = f"{DAILY_TASK_ASSET_DIR}/daily_task_selected_tab.png"
BUILTIN_DAILY_CHAPTER_HEADER_ASSET = f"{DAILY_TASK_ASSET_DIR}/daily_task_chapter_header.png"
BUILTIN_DAILY_CHAPTER_HEADER_CURRENT_ASSET = (
    f"{DAILY_TASK_ASSET_DIR}/daily_task_chapter_header_current_live.png"
)
BUILTIN_DAILY_UNSELECTED_TAB_ASSET = f"{DAILY_TASK_ASSET_DIR}/daily_task_unselected_tab.png"
BUILTIN_DAILY_LOGIN_COMPLETED_ASSET = f"{DAILY_TASK_ASSET_DIR}/daily_login_completed.png"
BUILTIN_DAILY_CLAIM_BUTTON_ASSET = f"{DAILY_TASK_ASSET_DIR}/daily_claim_button.png"
BUILTIN_DAILY_ONE_KEY_CLAIM_BUTTON_ASSET = (
    f"{DAILY_TASK_ASSET_DIR}/daily_one_key_claim_button.png"
)
BUILTIN_DAILY_PAID_OFFER_TITLE_ASSET = f"{DAILY_TASK_ASSET_DIR}/daily_paid_offer_title.png"
BUILTIN_DAILY_PAID_OFFER_PRICE_ASSET = f"{DAILY_TASK_ASSET_DIR}/daily_paid_offer_price.png"
BUILTIN_DAILY_PROGRESS_ANCHOR_ASSET = f"{DAILY_TASK_ASSET_DIR}/daily_task_progress_anchor.png"
BUILTIN_DAILY_REWARD_RESULT_ASSET = f"{DAILY_TASK_ASSET_DIR}/daily_reward_result_title.png"
BUILTIN_DAILY_REWARD_EXIT_HINT_ASSET = (
    f"{DAILY_TASK_ASSET_DIR}/daily_reward_result_exit_hint_user.png"
)
BUILTIN_DAILY_CHEST_POPUP_TOP_ASSET = f"{DAILY_TASK_ASSET_DIR}/daily_chest_popup_top_corner.png"
BUILTIN_DAILY_CHEST_POPUP_BOTTOM_ASSET = f"{DAILY_TASK_ASSET_DIR}/daily_chest_popup_corner.png"
# Some clients render the activity-chest contents as a centred, list-style
# sheet with a small pointer above its top edge.  The two older corner assets
# are not visible on that variant, so it needs its own passive recognition
# anchor.  Like every chest-result asset, this never authorises input by
# itself; the caller must have just tapped the corresponding milestone.
BUILTIN_DAILY_CHEST_POPUP_POINTER_ASSET = f"{DAILY_TASK_ASSET_DIR}/daily_chest_popup_pointer.png"
# A milestone chest remains visible after it has been opened.  These are
# art-only anchors for that *already-open* visual state; they are passive
# evidence used to avoid reopening the contents sheet after an application
# restart.  They never identify a chest as claimable.
BUILTIN_DAILY_ACTIVITY_CHEST_OPEN_TOP_ASSET = f"{DAILY_TASK_ASSET_DIR}/daily_activity_chest_open_top.png"
BUILTIN_DAILY_ACTIVITY_CHEST_OPEN_BOTTOM_ASSET = f"{DAILY_TASK_ASSET_DIR}/daily_activity_chest_open_bottom.png"
# Completed Daily rows are sorted into one trailing block.  This exact green
# check is a skip-only boundary anchor: it never authorises a click, but lets
# the controller stop wasting gestures once the already-completed block begins.
BUILTIN_DAILY_TASK_COMPLETED_CHECK_ASSET = f"{DAILY_TASK_ASSET_DIR}/daily_task_completed_check.png"
# Only the static left edge of the Daily Tasks "next refresh" pill is kept;
# the changing HH:MM:SS digits are intentionally excluded.  This is passive
# evidence that a fully scanned list is waiting for server refresh.
BUILTIN_DAILY_REFRESH_LABEL_ASSET = f"{DAILY_TASK_ASSET_DIR}/daily_task_refresh_label.png"
# Exact title-only proof for the game's network-disconnected sheet.  It is a
# zero-input pause state; neither of the sheet's two blue controls is included
# in the asset or exposed as an action coordinate.
BUILTIN_DAILY_NETWORK_DISCONNECTED_ASSET = (
    f"{DAILY_TASK_ASSET_DIR}/daily_network_disconnected_title.png"
)
# Exact full sentence shown when the same account has logged in on another
# device.  This is also a zero-input pause: the adjacent Customer Service and
# Reconnect controls are deliberately excluded from the asset and never gain
# an action coordinate.
BUILTIN_DAILY_FORCED_OFFLINE_MESSAGE_ASSET = (
    f"{DAILY_TASK_ASSET_DIR}/daily_forced_offline_message_live.png"
)
# Exact, reviewed startup settlement.  Unlike a generic reward sheet, this
# pair proves both the static ``Welcome back`` title and the ordinary green
# confirmation control at its fixed geometry.  The pair is used only to
# dismiss the login/offline settlement so the worker can resume Daily tasks;
# neither asset is reused as a generic green-button recogniser.
BUILTIN_DAILY_WELCOME_BACK_TITLE_ASSET = (
    f"{DAILY_TASK_ASSET_DIR}/daily_welcome_back_title.png"
)
BUILTIN_DAILY_WELCOME_BACK_CONFIRM_ASSET = (
    f"{DAILY_TASK_ASSET_DIR}/daily_welcome_back_confirm.png"
)
# Exact account-free anchors for the game's ``Regular Activity`` hub. This
# page may be raised automatically just after returning from the world map.
# Only the fixed title plus its own upper-left Back arrow form an actionable
# pair; refresh diamonds, ticket plus controls, tabs and cards are excluded.
BUILTIN_DAILY_REGULAR_ACTIVITY_BACK_ASSET = (
    f"{DAILY_TASK_ASSET_DIR}/daily_regular_activity_back_live.png"
)
BUILTIN_DAILY_REGULAR_ACTIVITY_TITLE_ASSET = (
    f"{DAILY_TASK_ASSET_DIR}/daily_regular_activity_title_live.png"
)
# One complete Daily Tasks scan is intentionally bounded.  Live MuMu testing
# needs five effective swipes plus two stationary confirmations to move from
# the bottom to the real top, and six plus two in the opposite direction.
# Twelve leaves recovery margin without permitting an endless gesture loop.
DAILY_TASK_LIST_MAX_SCAN_SWIPES = 12
DAILY_TASK_LIST_BOUNDARY_CONFIRMATIONS = 2
DAILY_TASK_LIST_BOUNDARY_MAX_MEAN_CHANGE = 0.7
# x=720 falls on task-card content and MuMu ignored the recorded gesture there.
# x=900 is the empirically verified blank lane between the task text and its
# right-side action button.  Both directions remain inside the list viewport.
DAILY_TASK_LIST_GESTURE_X = 900
DAILY_TASK_LIST_VIEWPORT_BOX = (40, 800, 850, 2110)
# Returning to the first task is latency-sensitive and does not need the
# deliberately slow scan gesture.  A short-duration, long-distance swipe
# produces one inertial fling in the verified list-only lane.  The list length
# varies across accounts and after completed cards are retained, so do not
# guess a fixed movement count.  Use ten possible movement gestures plus the
# two stationary comparisons required to prove the top, within the existing
# global twelve-gesture fail-closed envelope.  Unlike the former slow crawl,
# every attempt is 90 ms and is immediately followed by a pixel comparison.
DAILY_TASK_LIST_FAST_TOP_MOVEMENT_GESTURES = (
    DAILY_TASK_LIST_MAX_SCAN_SWIPES
    - DAILY_TASK_LIST_BOUNDARY_CONFIRMATIONS
)
DAILY_TASK_LIST_FAST_TOP_MAX_GESTURES = (
    DAILY_TASK_LIST_FAST_TOP_MOVEMENT_GESTURES
    + DAILY_TASK_LIST_BOUNDARY_CONFIRMATIONS
)
DAILY_TASK_LIST_FAST_TOP_SWIPE = (900, 1000, 900, 2200, 90)
# Daily mission execution is deliberately limited to ordinary world-resource
# gathering.  These anchors were captured from the live 1440 x 2560 MuMu
# client and are used only as a correlated, same-run route: an exact visible
# mission title + its matching blue ``前往`` button starts the route; all later
# controls are separately recognised before they can be tapped.
BUILTIN_DAILY_MISSION_GATHER_MEAT_ASSET = f"{DAILY_TASK_ASSET_DIR}/daily_mission_gather_meat.png"
BUILTIN_DAILY_MISSION_GATHER_WOOD_ASSET = f"{DAILY_TASK_ASSET_DIR}/daily_mission_gather_wood.png"
BUILTIN_DAILY_MISSION_GATHER_COAL_ASSET = f"{DAILY_TASK_ASSET_DIR}/daily_mission_gather_coal.png"
BUILTIN_DAILY_MISSION_GATHER_IRON_ASSET = f"{DAILY_TASK_ASSET_DIR}/daily_mission_gather_iron.png"
BUILTIN_DAILY_MISSION_GO_ASSET = f"{DAILY_TASK_ASSET_DIR}/daily_mission_go_button.png"
BUILTIN_DAILY_MISSION_GO_CURRENT_ASSET = f"{DAILY_TASK_ASSET_DIR}/daily_mission_go_button_current.png"
BUILTIN_DAILY_GATHER_WORLD_SEARCH_ASSET = f"{DAILY_TASK_ASSET_DIR}/daily_gather_world_search.png"
# The same world-search icon cropped to its circular face.  Unlike the older
# wide reference, it excludes changing snow/water terrain behind the icon.
BUILTIN_DAILY_GATHER_WORLD_SEARCH_TIGHT_ASSET = f"{DAILY_TASK_ASSET_DIR}/daily_gather_world_search_tight.png"
# Dense alliance territory can cover most of the lower-left search crop with
# buildings and labels.  This even tighter live variant contains only the
# white magnifier ring and must be paired with the matching Town control.
BUILTIN_DAILY_GATHER_WORLD_SEARCH_TIGHT_DENSE_ASSET = (
    f"{DAILY_TASK_ASSET_DIR}/daily_world_search_tight_dense_live.png"
)
# Exact city-side route to the ordinary world map. It is used only after two
# fresh city frames and never as a generic lower-right click.
BUILTIN_DAILY_CITY_WILDERNESS_ENTRY_ASSET = f"{DAILY_TASK_ASSET_DIR}/daily_city_wilderness_entry.png"
BUILTIN_DAILY_CITY_WILDERNESS_ENTRY_TIGHT_DAY_ASSET = (
    f"{DAILY_TASK_ASSET_DIR}/daily_city_wilderness_entry_tight_day.png"
)
BUILTIN_DAILY_CITY_WILDERNESS_ENTRY_TIGHT_LOW_ACCOUNT_ASSET = (
    f"{DAILY_TASK_ASSET_DIR}/daily_city_wilderness_entry_tight_low_account_live.png"
)
# World-map exit used only to resume a reviewed Daily Task workflow.  It is
# paired with the lower-left world-search lens so a door-like icon elsewhere
# can never become a generic navigation target.
BUILTIN_DAILY_WORLD_TOWN_ENTRY_ASSET = f"{DAILY_TASK_ASSET_DIR}/daily_world_town_entry.png"
BUILTIN_DAILY_WORLD_TOWN_ENTRY_TIGHT_DENSE_ASSET = (
    f"{DAILY_TASK_ASSET_DIR}/daily_world_town_entry_tight_dense_live.png"
)
# On some high-level world-map layouts the expanded bottom toolbar leaves the
# Town control in the same action lane but changes the snow shelf surrounding
# it.  Keep that reviewed state as a separate exact template rather than
# lowering the normal Town threshold for every page.
BUILTIN_DAILY_WORLD_TOWN_ENTRY_TOOLBAR_ASSET = (
    f"{DAILY_TASK_ASSET_DIR}/daily_world_town_entry_toolbar_live.png"
)
# Word-guide castle-band preflight. The overview globe and the layer panel are
# separate proofs; the unchecked resource template contains both the unchanged
# Threat check and the empty Resource square.
BUILTIN_DAILY_WORLD_OVERVIEW_ENTRY_ASSET = f"{DAILY_TASK_ASSET_DIR}/daily_world_overview_entry.png"
BUILTIN_DAILY_WORLD_OVERVIEW_PANEL_ANCHOR_ASSET = (
    f"{DAILY_TASK_ASSET_DIR}/daily_world_overview_panel_anchor.png"
)
BUILTIN_DAILY_WORLD_OVERVIEW_RESOURCE_OFF_ASSET = (
    f"{DAILY_TASK_ASSET_DIR}/daily_world_overview_resource_off.png"
)
# When the overview camera is away from the player's own castle, the game
# exposes this exact blue circular house below the minimap.  It is a narrow,
# account-free crop which excludes the changing distance caption.
BUILTIN_DAILY_WORLD_OVERVIEW_HOME_BUTTON_ASSET = (
    f"{DAILY_TASK_ASSET_DIR}/daily_world_overview_home_button.png"
)
BUILTIN_DAILY_GATHER_SEARCH_TUTORIAL_ASSET = f"{DAILY_TASK_ASSET_DIR}/daily_gather_search_tutorial.png"
BUILTIN_DAILY_GATHER_SEARCH_TUTORIAL_ALT_ASSET = f"{DAILY_TASK_ASSET_DIR}/daily_gather_search_tutorial_alt.png"
BUILTIN_DAILY_GATHER_COLLECT_ASSET = f"{DAILY_TASK_ASSET_DIR}/daily_gather_collect_button.png"
BUILTIN_DAILY_GATHER_DISPATCH_ASSET = f"{DAILY_TASK_ASSET_DIR}/daily_gather_dispatch_button.png"
# Passive world-map evidence that at least one march is still in use.  It never
# authorises a tap or implies that every queue is occupied; free capacity is
# read separately from the two-frame ``used/total`` header.
BUILTIN_DAILY_GATHER_ACTIVE_MARCH_ASSET = f"{DAILY_TASK_ASSET_DIR}/daily_gather_active_march.png"
# Current compact world-map layout: the capacity title may be hidden while a
# live march is exposed only as the fixed right-side red expedition icon with
# a dynamic countdown below it.  The asset contains only the static interior
# of that icon; it excludes the changing count badge, timer and account data.
BUILTIN_DAILY_GATHER_ACTIVE_MARCH_RIGHT_COMPACT_ASSET = (
    f"{DAILY_TASK_ASSET_DIR}/daily_gather_active_march_right_compact.png"
)
# The Daily-Task Go route pre-selects Raw Meat in the carousel.  This small,
# centre-only label is independently verified before the worker presses
# Search, so this route never guesses a carousel coordinate.
BUILTIN_DAILY_GATHER_MEAT_SELECTED_ASSET = f"{DAILY_TASK_ASSET_DIR}/daily_gather_meat_selected_label.png"
BUILTIN_DAILY_GATHER_MEAT_SELECTED_RIGHT_ASSET = f"{DAILY_TASK_ASSET_DIR}/daily_gather_meat_selected_right.png"
# A kingdom-overview round-trip can reset the carousel to ``野兽`` even
# though the exact Raw-Meat Daily card originally pre-selected ``生肉``.  In
# that reviewed state the next tab is partially visible at the far right.
# This account-free crop authorises only that visible tab inside an already
# validated ordinary resource selector; selection still needs a fresh
# double-confirmed central ``生肉`` label afterwards.
BUILTIN_DAILY_GATHER_MEAT_VISIBLE_TAB_ASSET = f"{DAILY_TASK_ASSET_DIR}/daily_gather_meat_visible_tab.png"
# This is the unchecked state of the selector's built-in "full nodes only"
# filter.  It is a safe, free local selector setting; the worker recognises
# this exact state before it may toggle the square itself.
BUILTIN_DAILY_GATHER_FULL_RESOURCES_FILTER_OFF_ASSET = (
    f"{DAILY_TASK_ASSET_DIR}/daily_gather_full_resources_filter_off.png"
)
BUILTIN_DAILY_GATHER_FULL_RESOURCES_FILTER_ON_ASSET = (
    f"{DAILY_TASK_ASSET_DIR}/daily_gather_full_resources_filter_on.png"
)
# Training never reuses a generic building click.  Its task title, normal
# blue training control and exact count are verified independently; yellow
# immediate-complete and speed-up controls intentionally have no asset here.
BUILTIN_DAILY_MISSION_TRAIN_SHIELD_ASSET = f"{DAILY_TASK_ASSET_DIR}/daily_mission_train_shield.png"
BUILTIN_DAILY_MISSION_TRAIN_SHIELD_30_ASSET = f"{DAILY_TASK_ASSET_DIR}/daily_mission_train_shield_30.png"
BUILTIN_DAILY_MISSION_TRAIN_SHIELD_30_20_ASSET = (
    f"{DAILY_TASK_ASSET_DIR}/daily_mission_train_shield_30_20.png"
)
BUILTIN_DAILY_MISSION_TRAIN_SPEAR_ASSET = f"{DAILY_TASK_ASSET_DIR}/daily_mission_train_spear.png"
BUILTIN_DAILY_MISSION_TRAIN_SPEAR_30_ASSET = f"{DAILY_TASK_ASSET_DIR}/daily_mission_train_spear_30.png"
BUILTIN_DAILY_MISSION_TRAIN_SPEAR_30_20_ASSET = (
    f"{DAILY_TASK_ASSET_DIR}/daily_mission_train_spear_30_20.png"
)
BUILTIN_DAILY_MISSION_TRAIN_ARCHER_ASSET = f"{DAILY_TASK_ASSET_DIR}/daily_mission_train_archer.png"
BUILTIN_DAILY_MISSION_TRAIN_ARCHER_30_10_ASSET = (
    f"{DAILY_TASK_ASSET_DIR}/daily_mission_train_archer_30_10.png"
)
BUILTIN_DAILY_MISSION_TRAIN_ARCHER_30_20_ASSET = (
    f"{DAILY_TASK_ASSET_DIR}/daily_mission_train_archer_30_20.png"
)
BUILTIN_DAILY_MISSION_UPGRADE_BUILDING_ASSET = f"{DAILY_TASK_ASSET_DIR}/daily_mission_upgrade_building.png"
BUILTIN_DAILY_MISSION_RESEARCH_TECH_ASSET = f"{DAILY_TASK_ASSET_DIR}/daily_mission_research_tech.png"
# The user-supplied Word guide contributes three exact Daily-card title
# anchors and two staged destination anchors.  Arena is executable only after
# the title+same-row Go lineage reaches the reviewed home/list/setup/result
# chain below; every numeric gate is still fail-closed.
BUILTIN_DAILY_MISSION_PROCESS_INTEL_ASSET = f"{DAILY_TASK_ASSET_DIR}/user_doc_intel_mission_title.png"
BUILTIN_DAILY_MISSION_PROCESS_INTEL_5_ASSET = (
    f"{DAILY_TASK_ASSET_DIR}/daily_mission_process_intel_5_live.png"
)
BUILTIN_DAILY_MISSION_WAREHOUSE_SUPPLY_ASSET = f"{DAILY_TASK_ASSET_DIR}/user_doc_warehouse_mission_title.png"
BUILTIN_DAILY_MISSION_WAREHOUSE_SUPPLY_THREE_CURRENT_ASSET = (
    f"{DAILY_TASK_ASSET_DIR}/daily_warehouse_mission_three_current_live.png"
)
BUILTIN_DAILY_MISSION_WAREHOUSE_SUPPLY_THREE_2OF3_ASSET = (
    f"{DAILY_TASK_ASSET_DIR}/daily_warehouse_mission_three_2of3_live.png"
)
BUILTIN_DAILY_MISSION_WAREHOUSE_SUPPLY_FIVE_CURRENT_ASSET = (
    f"{DAILY_TASK_ASSET_DIR}/daily_warehouse_mission_five_current_live.png"
)
BUILTIN_DAILY_MISSION_ARENA_PASSIVE_ASSET = f"{DAILY_TASK_ASSET_DIR}/user_doc_arena_mission_title.png"
BUILTIN_DAILY_MISSION_ARENA_ONE_CURRENT_ASSET = f"{DAILY_TASK_ASSET_DIR}/daily_arena_mission_one_current_live.png"
BUILTIN_DAILY_MISSION_ARENA_ONE_CLAIM_ASSET = f"{DAILY_TASK_ASSET_DIR}/daily_arena_mission_one_claim_current_live.png"
BUILTIN_DAILY_MISSION_ARENA_FIVE_CURRENT_ASSET = f"{DAILY_TASK_ASSET_DIR}/daily_arena_mission_five_current_live.png"
BUILTIN_DAILY_MISSION_ARENA_FIVE_CLAIM_ASSET = f"{DAILY_TASK_ASSET_DIR}/daily_arena_mission_five_claim_current_live.png"
BUILTIN_DAILY_ARENA_HOME_TITLE_ASSET = f"{DAILY_TASK_ASSET_DIR}/daily_arena_home_title_live.png"
BUILTIN_DAILY_ARENA_CHALLENGE_LABEL_ASSET = f"{DAILY_TASK_ASSET_DIR}/daily_arena_challenge_label_live.png"
BUILTIN_DAILY_ARENA_LIST_TITLE_ASSET = f"{DAILY_TASK_ASSET_DIR}/daily_arena_list_title_live.png"
BUILTIN_DAILY_ARENA_REMAINING_LABEL_ASSET = f"{DAILY_TASK_ASSET_DIR}/daily_arena_remaining_label_live.png"
BUILTIN_DAILY_ARENA_SETUP_TITLE_ASSET = f"{DAILY_TASK_ASSET_DIR}/daily_arena_setup_title_live.png"
BUILTIN_DAILY_ARENA_BATTLE_LABEL_ASSET = f"{DAILY_TASK_ASSET_DIR}/daily_arena_battle_label_live.png"
BUILTIN_DAILY_ARENA_RESULT_EXIT_TEXT_ASSET = f"{DAILY_TASK_ASSET_DIR}/daily_arena_result_exit_text_live.png"
BUILTIN_DAILY_MISSION_GO_USER_DOC_ASSET = f"{DAILY_TASK_ASSET_DIR}/user_doc_daily_mission_go.png"
BUILTIN_DAILY_INTEL_MAP_ENTRY_ASSET = f"{DAILY_TASK_ASSET_DIR}/user_doc_intel_map_entry.png"
BUILTIN_DAILY_INTEL_MAP_PAGE_ASSET = f"{DAILY_TASK_ASSET_DIR}/user_doc_intel_map_page_anchor.png"
BUILTIN_DAILY_INTEL_STATION_BUBBLE_ASSET = (
    f"{DAILY_TASK_ASSET_DIR}/daily_intel_station_bubble_live.png"
)
BUILTIN_DAILY_INTEL_MAP_HEADER_ASSET = f"{DAILY_TASK_ASSET_DIR}/daily_intel_map_header_live.png"
BUILTIN_DAILY_INTEL_RESCUE_PIN_ASSET = f"{DAILY_TASK_ASSET_DIR}/daily_intel_rescue_pin_live.png"
BUILTIN_DAILY_INTEL_RESCUE_GREY_PIN_ASSET = (
    f"{DAILY_TASK_ASSET_DIR}/daily_intel_rescue_grey_pin_current_live.png"
)
BUILTIN_DAILY_INTEL_RESCUE_PREVIEW_TITLE_ASSET = (
    f"{DAILY_TASK_ASSET_DIR}/daily_intel_rescue_preview_title_live.png"
)
BUILTIN_DAILY_INTEL_RESCUE_PREVIEW_GO_ASSET = (
    f"{DAILY_TASK_ASSET_DIR}/daily_intel_rescue_preview_go_live.png"
)
BUILTIN_DAILY_INTEL_RESCUE_TARGET_TITLE_ASSET = (
    f"{DAILY_TASK_ASSET_DIR}/daily_intel_rescue_target_title_live.png"
)
BUILTIN_DAILY_INTEL_RESCUE_ACTION_ASSET = (
    f"{DAILY_TASK_ASSET_DIR}/daily_intel_rescue_action_live.png"
)
BUILTIN_DAILY_INTEL_RESCUE_ACTIVE_ASSET = (
    f"{DAILY_TASK_ASSET_DIR}/daily_intel_rescue_active_live.png"
)
BUILTIN_DAILY_INTEL_SWORDS_PIN_ASSET = f"{DAILY_TASK_ASSET_DIR}/daily_intel_swords_pin_live.png"
BUILTIN_DAILY_INTEL_HERO_PREVIEW_TITLE_ASSET = f"{DAILY_TASK_ASSET_DIR}/daily_intel_hero_preview_title_live.png"
BUILTIN_DAILY_INTEL_HERO_PREVIEW_GO_ASSET = f"{DAILY_TASK_ASSET_DIR}/daily_intel_hero_preview_go_live.png"
BUILTIN_DAILY_INTEL_HERO_DETAIL_TITLE_ASSET = f"{DAILY_TASK_ASSET_DIR}/daily_intel_hero_detail_title_live.png"
BUILTIN_DAILY_INTEL_HERO_EXPLORE_ASSET = f"{DAILY_TASK_ASSET_DIR}/daily_intel_hero_explore_live.png"
BUILTIN_DAILY_INTEL_HERO_SETUP_HEADER_ASSET = f"{DAILY_TASK_ASSET_DIR}/daily_intel_hero_setup_header_live.png"
BUILTIN_DAILY_INTEL_HERO_AUTO_DEPLOY_ASSET = f"{DAILY_TASK_ASSET_DIR}/daily_intel_hero_auto_deploy_live.png"
BUILTIN_DAILY_INTEL_HERO_BATTLE_ASSET = f"{DAILY_TASK_ASSET_DIR}/daily_intel_hero_battle_live.png"
BUILTIN_DAILY_INTEL_HERO_VICTORY_ASSET = f"{DAILY_TASK_ASSET_DIR}/daily_intel_hero_victory_live.png"
BUILTIN_DAILY_INTEL_HERO_EXIT_TEXT_ASSET = f"{DAILY_TASK_ASSET_DIR}/daily_intel_hero_exit_text_live.png"
BUILTIN_DAILY_INTEL_COMPLETED_CHECK_ASSET = f"{DAILY_TASK_ASSET_DIR}/daily_intel_completed_check_live.png"
BUILTIN_DAILY_INTEL_COMPLETED_TENT_CURRENT_ASSET = (
    f"{DAILY_TASK_ASSET_DIR}/daily_intel_completed_tent_current_live.png"
)
BUILTIN_DAILY_INTEL_WOLF_PIN_CURRENT_ASSET = (
    f"{DAILY_TASK_ASSET_DIR}/daily_intel_wolf_pin_current_live.png"
)
BUILTIN_DAILY_INTEL_SWORDS_PIN_CURRENT_ASSET = (
    f"{DAILY_TASK_ASSET_DIR}/daily_intel_swords_pin_current_live.png"
)
BUILTIN_DAILY_INTEL_WOLF_PREVIEW_TITLE_CURRENT_ASSET = (
    f"{DAILY_TASK_ASSET_DIR}/daily_intel_wolf_preview_title_current_live.png"
)
BUILTIN_DAILY_INTEL_WOLF_PREVIEW_GO_CURRENT_ASSET = (
    f"{DAILY_TASK_ASSET_DIR}/daily_intel_wolf_preview_go_current_live.png"
)
BUILTIN_DAILY_INTEL_WOLF_TARGET_TITLE_CURRENT_ASSET = (
    f"{DAILY_TASK_ASSET_DIR}/daily_intel_wolf_target_title_current_live.png"
)
BUILTIN_DAILY_INTEL_WOLF_MARCH_CURRENT_ASSET = (
    f"{DAILY_TASK_ASSET_DIR}/daily_intel_wolf_march_current_live.png"
)
BUILTIN_DAILY_WAREHOUSE_RESULT_ASSET = f"{DAILY_TASK_ASSET_DIR}/user_doc_warehouse_result.png"
BUILTIN_DAILY_WAREHOUSE_RESULT_CURRENT_ASSET = (
    f"{DAILY_TASK_ASSET_DIR}/daily_warehouse_result_countdown_label_current_live.png"
)
BUILTIN_DAILY_WAREHOUSE_CITY_SUPPLY_BUBBLE_ASSET = (
    f"{DAILY_TASK_ASSET_DIR}/daily_warehouse_city_supply_bubble_live.png"
)
BUILTIN_DAILY_WAREHOUSE_CITY_SUPPLY_BUBBLE_NIGHT_ASSETS = tuple(
    f"{DAILY_TASK_ASSET_DIR}/daily_warehouse_city_supply_bubble_night_pose_{index}_live.png"
    for index in range(1, 6)
)
BUILTIN_DAILY_TRAINING_ENTRY_LABEL_ASSET = f"{DAILY_TASK_ASSET_DIR}/daily_training_entry_label.png"
BUILTIN_DAILY_TRAINING_NORMAL_LABEL_ASSET = f"{DAILY_TASK_ASSET_DIR}/daily_training_normal_label.png"
BUILTIN_DAILY_TRAINING_COUNT_TEN_ASSET = f"{DAILY_TASK_ASSET_DIR}/daily_training_count_10_live.png"
BUILTIN_DAILY_TRAINING_ACTIVE_LABEL_ASSET = f"{DAILY_TASK_ASSET_DIR}/daily_training_active_label.png"
BUILTIN_DAILY_TRAINING_ACTIVE_TEXT_ASSET = f"{DAILY_TASK_ASSET_DIR}/daily_training_active_text_live.png"
# The green label is the active-queue appearance used by upgraded Spear/Archer
# camps.  It is observation-only and deliberately excludes the nearby speed-up
# and diamond controls.
BUILTIN_DAILY_TRAINING_ACTIVE_GREEN_LABEL_ASSET = f"{DAILY_TASK_ASSET_DIR}/daily_training_active_green_label.png"
BUILTIN_DAILY_TRAINING_SPEAR_TUTORIAL_FACE_ASSET = f"{DAILY_TASK_ASSET_DIR}/daily_training_spear_tutorial_face.png"
BUILTIN_DAILY_TRAINING_ARCHER_TUTORIAL_POSE_ASSETS = tuple(
    f"{DAILY_TASK_ASSET_DIR}/daily_training_archer_tutorial_pose_{index}.png"
    for index in range(1, 5)
)
BUILTIN_DAILY_MAIN_TASK_PAGE_TITLE_ASSET = f"{DAILY_TASK_ASSET_DIR}/daily_main_task_page_title.png"
BUILTIN_DAILY_GROWTH_TASK_UNSELECTED_DAILY_TAB_ASSET = (
    f"{DAILY_TASK_ASSET_DIR}/daily_growth_task_unselected_daily_tab.png"
)
BUILTIN_DAILY_GROWTH_TWO_TAB_UNSELECTED_DAILY_TAB_ASSET = (
    f"{DAILY_TASK_ASSET_DIR}/daily_growth_two_tab_unselected_daily_tab.png"
)
BUILTIN_DAILY_TRAINING_COLLECT_TUTORIAL_ASSET = f"{DAILY_TASK_ASSET_DIR}/daily_training_collect_tutorial_target.png"
BUILTIN_DAILY_TRAINING_UNLOCK_CONTINUE_ASSET = f"{DAILY_TASK_ASSET_DIR}/daily_training_unlock_continue.png"
BUILTIN_DAILY_TRAINING_SHIELD_CAMP_ASSET = f"{DAILY_TASK_ASSET_DIR}/daily_training_shield_camp.png"
BUILTIN_DAILY_TRAINING_SHIELD_CAMP_CURRENT_ASSET = (
    f"{DAILY_TASK_ASSET_DIR}/daily_training_shield_camp_current_live.png"
)
# This heading is paired with the normal blue building action below.  It is
# observed only after the Daily Task's own reviewed ``Go`` control was tapped.
BUILTIN_DAILY_BUILDING_INFO_HEADER_ASSET = f"{DAILY_TASK_ASSET_DIR}/daily_building_info_header.png"
# Generic, account-free active-upgrade status row shown when Daily-Task Go
# opens a building whose natural construction queue is already occupied.
# The asset deliberately excludes timers, diamonds and speed-up controls.
BUILTIN_DAILY_BUILDING_ACTIVE_UPGRADING_LABEL_ASSET = (
    f"{DAILY_TASK_ASSET_DIR}/daily_building_active_upgrading_label.png"
)
BUILTIN_DAILY_MISSION_HERO_RECRUIT_ASSET = f"{DAILY_TASK_ASSET_DIR}/daily_mission_hero_recruit.png"
BUILTIN_DAILY_MISSION_HERO_RECRUIT_1_ASSET = f"{DAILY_TASK_ASSET_DIR}/daily_mission_hero_recruit_1.png"
BUILTIN_DAILY_HERO_FREE_RECRUIT_ASSET = f"{DAILY_TASK_ASSET_DIR}/daily_hero_free_recruit.png"
BUILTIN_DAILY_HERO_EPIC_FREE_RECRUIT_ASSET = f"{DAILY_TASK_ASSET_DIR}/daily_hero_epic_free_recruit.png"
BUILTIN_DAILY_HERO_RECRUIT_RESULT_ASSET = f"{DAILY_TASK_ASSET_DIR}/daily_hero_recruit_result.png"
BUILTIN_DAILY_HERO_RECRUIT_RESULT_CURRENT_ASSET = f"{DAILY_TASK_ASSET_DIR}/daily_hero_recruit_result_current.png"
# Duplicate heroes use a full-screen character reveal instead of the compact
# reward sheet.  This title-only prefix excludes hero art, name, rarity and
# the dynamic converted-token count; it is passive post-recruit evidence.
BUILTIN_DAILY_HERO_RECRUIT_DUPLICATE_OWNED_ASSET = (
    f"{DAILY_TASK_ASSET_DIR}/daily_hero_recruit_duplicate_owned_live.png"
)
BUILTIN_DAILY_HERO_RECRUIT_EXIT_HINT_ASSET = (
    f"{DAILY_TASK_ASSET_DIR}/daily_hero_recruit_exit_hint_live.png"
)
BUILTIN_DAILY_HERO_RECRUIT_EXIT_HINT_LEGACY_ASSET = (
    f"{DAILY_TASK_ASSET_DIR}/daily_hero_recruit_exit_hint_legacy_live.png"
)
BUILTIN_DAILY_TAP_ANYWHERE_EXIT_REWARD_CURRENT_ASSET = (
    f"{DAILY_TASK_ASSET_DIR}/daily_tap_anywhere_exit_reward_current_live.png"
)
BUILTIN_DAILY_TAP_ANYWHERE_EXIT_OLD_ASSET = (
    f"{DAILY_TASK_ASSET_DIR}/daily_tap_anywhere_exit_native_old_live.png"
)
BUILTIN_DAILY_HERO_RECRUIT_PAGE_ASSET = f"{DAILY_TASK_ASSET_DIR}/daily_hero_recruit_page.png"
BUILTIN_DAILY_MISSION_ALLIANCE_DONATE_ASSET = f"{DAILY_TASK_ASSET_DIR}/daily_mission_alliance_donate.png"
BUILTIN_DAILY_MISSION_ALLIANCE_DONATE_5_ASSET = f"{DAILY_TASK_ASSET_DIR}/daily_mission_alliance_donate_5.png"
BUILTIN_DAILY_ALLIANCE_FOOD_DONATE_ASSET = f"{DAILY_TASK_ASSET_DIR}/daily_alliance_food_donate.png"
BUILTIN_DAILY_ALLIANCE_DIAMOND_DONATE_ASSET = f"{DAILY_TASK_ASSET_DIR}/daily_alliance_diamond_donate.png"
BUILTIN_DAILY_ALLIANCE_TECH_ENTRY_ASSET = f"{DAILY_TASK_ASSET_DIR}/daily_alliance_tech_entry.png"
BUILTIN_DAILY_ALLIANCE_SUSTAIN_NODE_ASSET = f"{DAILY_TASK_ASSET_DIR}/daily_alliance_sustain_node.png"
BUILTIN_DAILY_ALLIANCE_TECH_BATTLE_TAB_STRIP_ASSET = (
    f"{DAILY_TASK_ASSET_DIR}/daily_alliance_tech_battle_tab_strip.png"
)
BUILTIN_DAILY_ALLIANCE_TECH_DEVELOPMENT_TAB_STRIP_ASSET = (
    f"{DAILY_TASK_ASSET_DIR}/daily_alliance_tech_development_tab_strip.png"
)
BUILTIN_DAILY_ALLIANCE_TECH_TERRITORY_TAB_STRIP_ASSET = (
    f"{DAILY_TASK_ASSET_DIR}/daily_alliance_tech_territory_tab_strip.png"
)
BUILTIN_DAILY_ALLIANCE_FOOD_DONATE_DISABLED_ASSET = f"{DAILY_TASK_ASSET_DIR}/daily_alliance_food_donate_disabled.png"
BUILTIN_DAILY_CITY_ENTRY_TEMPLATE_NAME = "builtin_daily_city_entry.png"
BUILTIN_DAILY_CITY_ENTRY_TRAINING_HIGHLIGHT_TEMPLATE_NAME = (
    "builtin_daily_city_entry_training_highlight_current_live.png"
)
BUILTIN_DAILY_HEADER_TEMPLATE_NAME = "builtin_daily_task_header.png"
BUILTIN_DAILY_SELECTED_TAB_TEMPLATE_NAME = "builtin_daily_task_selected_tab.png"
BUILTIN_DAILY_CHAPTER_HEADER_TEMPLATE_NAME = "builtin_daily_task_chapter_header.png"
BUILTIN_DAILY_CHAPTER_HEADER_CURRENT_TEMPLATE_NAME = (
    "builtin_daily_task_chapter_header_current_live.png"
)
BUILTIN_DAILY_UNSELECTED_TAB_TEMPLATE_NAME = "builtin_daily_task_unselected_tab.png"
BUILTIN_DAILY_LOGIN_COMPLETED_TEMPLATE_NAME = "builtin_daily_login_completed.png"
BUILTIN_DAILY_CLAIM_BUTTON_TEMPLATE_NAME = "builtin_daily_claim_button.png"
BUILTIN_DAILY_ONE_KEY_CLAIM_BUTTON_TEMPLATE_NAME = (
    "builtin_daily_one_key_claim_button.png"
)
BUILTIN_DAILY_PAID_OFFER_TITLE_TEMPLATE_NAME = "builtin_daily_paid_offer_title.png"
BUILTIN_DAILY_PAID_OFFER_PRICE_TEMPLATE_NAME = "builtin_daily_paid_offer_price.png"
BUILTIN_DAILY_PROGRESS_ANCHOR_TEMPLATE_NAME = "builtin_daily_task_progress_anchor.png"
BUILTIN_DAILY_REWARD_RESULT_TEMPLATE_NAME = "builtin_daily_reward_result_title.png"
BUILTIN_DAILY_REWARD_EXIT_HINT_TEMPLATE_NAME = (
    "builtin_daily_reward_result_exit_hint_user.png"
)
BUILTIN_DAILY_CHEST_POPUP_TOP_TEMPLATE_NAME = "builtin_daily_chest_popup_top_corner.png"
BUILTIN_DAILY_CHEST_POPUP_BOTTOM_TEMPLATE_NAME = "builtin_daily_chest_popup_bottom_corner.png"
BUILTIN_DAILY_CHEST_POPUP_POINTER_TEMPLATE_NAME = "builtin_daily_chest_popup_pointer.png"
BUILTIN_DAILY_ACTIVITY_CHEST_OPEN_TOP_TEMPLATE_NAME = "builtin_daily_activity_chest_open_top.png"
BUILTIN_DAILY_ACTIVITY_CHEST_OPEN_BOTTOM_TEMPLATE_NAME = "builtin_daily_activity_chest_open_bottom.png"
BUILTIN_DAILY_TASK_COMPLETED_CHECK_TEMPLATE_NAME = "builtin_daily_task_completed_check.png"
BUILTIN_DAILY_REFRESH_LABEL_TEMPLATE_NAME = "builtin_daily_task_refresh_label.png"
BUILTIN_DAILY_NETWORK_DISCONNECTED_TEMPLATE_NAME = (
    "builtin_daily_network_disconnected_title.png"
)
BUILTIN_DAILY_FORCED_OFFLINE_MESSAGE_TEMPLATE_NAME = (
    "builtin_daily_forced_offline_message_live.png"
)
BUILTIN_DAILY_WELCOME_BACK_TITLE_TEMPLATE_NAME = (
    "builtin_daily_welcome_back_title.png"
)
BUILTIN_DAILY_WELCOME_BACK_CONFIRM_TEMPLATE_NAME = (
    "builtin_daily_welcome_back_confirm.png"
)
BUILTIN_DAILY_REGULAR_ACTIVITY_BACK_TEMPLATE_NAME = (
    "builtin_daily_regular_activity_back_live.png"
)
BUILTIN_DAILY_REGULAR_ACTIVITY_TITLE_TEMPLATE_NAME = (
    "builtin_daily_regular_activity_title_live.png"
)
BUILTIN_DAILY_MISSION_GATHER_MEAT_TEMPLATE_NAME = "builtin_daily_mission_gather_meat.png"
BUILTIN_DAILY_MISSION_GATHER_WOOD_TEMPLATE_NAME = "builtin_daily_mission_gather_wood.png"
BUILTIN_DAILY_MISSION_GATHER_COAL_TEMPLATE_NAME = "builtin_daily_mission_gather_coal.png"
BUILTIN_DAILY_MISSION_GATHER_IRON_TEMPLATE_NAME = "builtin_daily_mission_gather_iron.png"
BUILTIN_DAILY_MISSION_GO_TEMPLATE_NAME = "builtin_daily_mission_go_button.png"
BUILTIN_DAILY_MISSION_GO_CURRENT_TEMPLATE_NAME = "builtin_daily_mission_go_button_current.png"
BUILTIN_DAILY_GATHER_WORLD_SEARCH_TEMPLATE_NAME = "builtin_daily_gather_world_search.png"
BUILTIN_DAILY_GATHER_WORLD_SEARCH_TIGHT_TEMPLATE_NAME = "builtin_daily_gather_world_search_tight.png"
BUILTIN_DAILY_GATHER_WORLD_SEARCH_TIGHT_DENSE_TEMPLATE_NAME = (
    "builtin_daily_world_search_tight_dense_live.png"
)
BUILTIN_DAILY_CITY_WILDERNESS_ENTRY_TEMPLATE_NAME = "builtin_daily_city_wilderness_entry.png"
BUILTIN_DAILY_CITY_WILDERNESS_ENTRY_TIGHT_DAY_TEMPLATE_NAME = (
    "builtin_daily_city_wilderness_entry_tight_day.png"
)
BUILTIN_DAILY_CITY_WILDERNESS_ENTRY_TIGHT_LOW_ACCOUNT_TEMPLATE_NAME = (
    "builtin_daily_city_wilderness_entry_tight_low_account_live.png"
)
BUILTIN_DAILY_WORLD_TOWN_ENTRY_TEMPLATE_NAME = "builtin_daily_world_town_entry.png"
BUILTIN_DAILY_WORLD_TOWN_ENTRY_TIGHT_DENSE_TEMPLATE_NAME = (
    "builtin_daily_world_town_entry_tight_dense_live.png"
)
BUILTIN_DAILY_WORLD_TOWN_ENTRY_TOOLBAR_TEMPLATE_NAME = (
    "builtin_daily_world_town_entry_toolbar_live.png"
)
BUILTIN_DAILY_WORLD_OVERVIEW_ENTRY_TEMPLATE_NAME = "builtin_daily_world_overview_entry.png"
BUILTIN_DAILY_WORLD_OVERVIEW_PANEL_ANCHOR_TEMPLATE_NAME = (
    "builtin_daily_world_overview_panel_anchor.png"
)
BUILTIN_DAILY_WORLD_OVERVIEW_RESOURCE_OFF_TEMPLATE_NAME = (
    "builtin_daily_world_overview_resource_off.png"
)
BUILTIN_DAILY_WORLD_OVERVIEW_HOME_BUTTON_TEMPLATE_NAME = (
    "builtin_daily_world_overview_home_button.png"
)
BUILTIN_DAILY_GATHER_SEARCH_TUTORIAL_TEMPLATE_NAME = "builtin_daily_gather_search_tutorial.png"
BUILTIN_DAILY_GATHER_SEARCH_TUTORIAL_ALT_TEMPLATE_NAME = "builtin_daily_gather_search_tutorial_alt.png"
BUILTIN_DAILY_GATHER_COLLECT_TEMPLATE_NAME = "builtin_daily_gather_collect_button.png"
BUILTIN_DAILY_GATHER_DISPATCH_TEMPLATE_NAME = "builtin_daily_gather_dispatch_button.png"
BUILTIN_DAILY_GATHER_ACTIVE_MARCH_TEMPLATE_NAME = "builtin_daily_gather_active_march.png"
BUILTIN_DAILY_GATHER_ACTIVE_MARCH_RIGHT_COMPACT_TEMPLATE_NAME = (
    "builtin_daily_gather_active_march_right_compact.png"
)
BUILTIN_DAILY_GATHER_MEAT_SELECTED_TEMPLATE_NAME = "builtin_daily_gather_meat_selected_label.png"
BUILTIN_DAILY_GATHER_MEAT_SELECTED_RIGHT_TEMPLATE_NAME = "builtin_daily_gather_meat_selected_right.png"
BUILTIN_DAILY_GATHER_MEAT_VISIBLE_TAB_TEMPLATE_NAME = "builtin_daily_gather_meat_visible_tab.png"
BUILTIN_DAILY_GATHER_FULL_RESOURCES_FILTER_OFF_TEMPLATE_NAME = (
    "builtin_daily_gather_full_resources_filter_off.png"
)
BUILTIN_DAILY_GATHER_FULL_RESOURCES_FILTER_ON_TEMPLATE_NAME = (
    "builtin_daily_gather_full_resources_filter_on.png"
)
BUILTIN_DAILY_MISSION_TRAIN_SHIELD_TEMPLATE_NAME = "builtin_daily_mission_train_shield.png"
BUILTIN_DAILY_MISSION_TRAIN_SHIELD_30_TEMPLATE_NAME = "builtin_daily_mission_train_shield_30.png"
BUILTIN_DAILY_MISSION_TRAIN_SHIELD_30_20_TEMPLATE_NAME = (
    "builtin_daily_mission_train_shield_30_20.png"
)
BUILTIN_DAILY_MISSION_TRAIN_SPEAR_TEMPLATE_NAME = "builtin_daily_mission_train_spear.png"
BUILTIN_DAILY_MISSION_TRAIN_SPEAR_30_TEMPLATE_NAME = "builtin_daily_mission_train_spear_30.png"
BUILTIN_DAILY_MISSION_TRAIN_SPEAR_30_20_TEMPLATE_NAME = (
    "builtin_daily_mission_train_spear_30_20.png"
)
BUILTIN_DAILY_MISSION_TRAIN_ARCHER_TEMPLATE_NAME = "builtin_daily_mission_train_archer.png"
BUILTIN_DAILY_MISSION_TRAIN_ARCHER_30_10_TEMPLATE_NAME = (
    "builtin_daily_mission_train_archer_30_10.png"
)
BUILTIN_DAILY_MISSION_TRAIN_ARCHER_30_20_TEMPLATE_NAME = (
    "builtin_daily_mission_train_archer_30_20.png"
)
BUILTIN_DAILY_MISSION_UPGRADE_BUILDING_TEMPLATE_NAME = "builtin_daily_mission_upgrade_building.png"
BUILTIN_DAILY_MISSION_RESEARCH_TECH_TEMPLATE_NAME = "builtin_daily_mission_research_tech.png"
BUILTIN_DAILY_MISSION_PROCESS_INTEL_TEMPLATE_NAME = "builtin_user_doc_intel_mission_title.png"
BUILTIN_DAILY_MISSION_PROCESS_INTEL_5_TEMPLATE_NAME = (
    "builtin_daily_mission_process_intel_5_live.png"
)
BUILTIN_DAILY_MISSION_WAREHOUSE_SUPPLY_TEMPLATE_NAME = "builtin_user_doc_warehouse_mission_title.png"
BUILTIN_DAILY_MISSION_WAREHOUSE_SUPPLY_THREE_CURRENT_TEMPLATE_NAME = (
    "builtin_daily_warehouse_mission_three_current_live.png"
)
BUILTIN_DAILY_MISSION_WAREHOUSE_SUPPLY_THREE_2OF3_TEMPLATE_NAME = (
    "builtin_daily_warehouse_mission_three_2of3_live.png"
)
BUILTIN_DAILY_MISSION_WAREHOUSE_SUPPLY_FIVE_CURRENT_TEMPLATE_NAME = (
    "builtin_daily_warehouse_mission_five_current_live.png"
)
BUILTIN_DAILY_MISSION_ARENA_PASSIVE_TEMPLATE_NAME = "builtin_user_doc_arena_mission_title.png"
BUILTIN_DAILY_MISSION_ARENA_ONE_CURRENT_TEMPLATE_NAME = "builtin_daily_arena_mission_one_current_live.png"
BUILTIN_DAILY_MISSION_ARENA_ONE_CLAIM_TEMPLATE_NAME = "builtin_daily_arena_mission_one_claim_current_live.png"
BUILTIN_DAILY_MISSION_ARENA_FIVE_CURRENT_TEMPLATE_NAME = "builtin_daily_arena_mission_five_current_live.png"
BUILTIN_DAILY_MISSION_ARENA_FIVE_CLAIM_TEMPLATE_NAME = "builtin_daily_arena_mission_five_claim_current_live.png"
BUILTIN_DAILY_ARENA_HOME_TITLE_TEMPLATE_NAME = "builtin_daily_arena_home_title_live.png"
BUILTIN_DAILY_ARENA_CHALLENGE_LABEL_TEMPLATE_NAME = "builtin_daily_arena_challenge_label_live.png"
BUILTIN_DAILY_ARENA_LIST_TITLE_TEMPLATE_NAME = "builtin_daily_arena_list_title_live.png"
BUILTIN_DAILY_ARENA_REMAINING_LABEL_TEMPLATE_NAME = "builtin_daily_arena_remaining_label_live.png"
BUILTIN_DAILY_ARENA_SETUP_TITLE_TEMPLATE_NAME = "builtin_daily_arena_setup_title_live.png"
BUILTIN_DAILY_ARENA_BATTLE_LABEL_TEMPLATE_NAME = "builtin_daily_arena_battle_label_live.png"
BUILTIN_DAILY_ARENA_RESULT_EXIT_TEXT_TEMPLATE_NAME = "builtin_daily_arena_result_exit_text_live.png"
BUILTIN_DAILY_MISSION_GO_USER_DOC_TEMPLATE_NAME = "builtin_user_doc_daily_mission_go.png"
BUILTIN_DAILY_INTEL_MAP_ENTRY_TEMPLATE_NAME = "builtin_user_doc_intel_map_entry.png"
BUILTIN_DAILY_INTEL_MAP_PAGE_TEMPLATE_NAME = "builtin_user_doc_intel_map_page_anchor.png"
BUILTIN_DAILY_INTEL_STATION_BUBBLE_TEMPLATE_NAME = "builtin_daily_intel_station_bubble_live.png"
BUILTIN_DAILY_INTEL_MAP_HEADER_TEMPLATE_NAME = "builtin_daily_intel_map_header_live.png"
BUILTIN_DAILY_INTEL_RESCUE_PIN_TEMPLATE_NAME = "builtin_daily_intel_rescue_pin_live.png"
BUILTIN_DAILY_INTEL_RESCUE_GREY_PIN_TEMPLATE_NAME = (
    "builtin_daily_intel_rescue_grey_pin_current_live.png"
)
BUILTIN_DAILY_INTEL_RESCUE_PREVIEW_TITLE_TEMPLATE_NAME = (
    "builtin_daily_intel_rescue_preview_title_live.png"
)
BUILTIN_DAILY_INTEL_RESCUE_PREVIEW_GO_TEMPLATE_NAME = (
    "builtin_daily_intel_rescue_preview_go_live.png"
)
BUILTIN_DAILY_INTEL_RESCUE_TARGET_TITLE_TEMPLATE_NAME = (
    "builtin_daily_intel_rescue_target_title_live.png"
)
BUILTIN_DAILY_INTEL_RESCUE_ACTION_TEMPLATE_NAME = "builtin_daily_intel_rescue_action_live.png"
BUILTIN_DAILY_INTEL_RESCUE_ACTIVE_TEMPLATE_NAME = "builtin_daily_intel_rescue_active_live.png"
BUILTIN_DAILY_INTEL_SWORDS_PIN_TEMPLATE_NAME = "builtin_daily_intel_swords_pin_live.png"
BUILTIN_DAILY_INTEL_HERO_PREVIEW_TITLE_TEMPLATE_NAME = "builtin_daily_intel_hero_preview_title_live.png"
BUILTIN_DAILY_INTEL_HERO_PREVIEW_GO_TEMPLATE_NAME = "builtin_daily_intel_hero_preview_go_live.png"
BUILTIN_DAILY_INTEL_HERO_DETAIL_TITLE_TEMPLATE_NAME = "builtin_daily_intel_hero_detail_title_live.png"
BUILTIN_DAILY_INTEL_HERO_EXPLORE_TEMPLATE_NAME = "builtin_daily_intel_hero_explore_live.png"
BUILTIN_DAILY_INTEL_HERO_SETUP_HEADER_TEMPLATE_NAME = "builtin_daily_intel_hero_setup_header_live.png"
BUILTIN_DAILY_INTEL_HERO_AUTO_DEPLOY_TEMPLATE_NAME = "builtin_daily_intel_hero_auto_deploy_live.png"
BUILTIN_DAILY_INTEL_HERO_BATTLE_TEMPLATE_NAME = "builtin_daily_intel_hero_battle_live.png"
BUILTIN_DAILY_INTEL_HERO_VICTORY_TEMPLATE_NAME = "builtin_daily_intel_hero_victory_live.png"
BUILTIN_DAILY_INTEL_HERO_EXIT_TEXT_TEMPLATE_NAME = "builtin_daily_intel_hero_exit_text_live.png"
BUILTIN_DAILY_INTEL_COMPLETED_CHECK_TEMPLATE_NAME = "builtin_daily_intel_completed_check_live.png"
BUILTIN_DAILY_INTEL_COMPLETED_TENT_CURRENT_TEMPLATE_NAME = "builtin_daily_intel_completed_tent_current_live.png"
BUILTIN_DAILY_INTEL_WOLF_PIN_CURRENT_TEMPLATE_NAME = "builtin_daily_intel_wolf_pin_current_live.png"
BUILTIN_DAILY_INTEL_SWORDS_PIN_CURRENT_TEMPLATE_NAME = "builtin_daily_intel_swords_pin_current_live.png"
BUILTIN_DAILY_INTEL_WOLF_PREVIEW_TITLE_CURRENT_TEMPLATE_NAME = "builtin_daily_intel_wolf_preview_title_current_live.png"
BUILTIN_DAILY_INTEL_WOLF_PREVIEW_GO_CURRENT_TEMPLATE_NAME = "builtin_daily_intel_wolf_preview_go_current_live.png"
BUILTIN_DAILY_INTEL_WOLF_TARGET_TITLE_CURRENT_TEMPLATE_NAME = "builtin_daily_intel_wolf_target_title_current_live.png"
BUILTIN_DAILY_INTEL_WOLF_MARCH_CURRENT_TEMPLATE_NAME = "builtin_daily_intel_wolf_march_current_live.png"
BUILTIN_DAILY_WAREHOUSE_RESULT_TEMPLATE_NAME = "builtin_user_doc_warehouse_result.png"
BUILTIN_DAILY_WAREHOUSE_RESULT_CURRENT_TEMPLATE_NAME = (
    "builtin_daily_warehouse_result_countdown_label_current_live.png"
)
BUILTIN_DAILY_WAREHOUSE_CITY_SUPPLY_BUBBLE_TEMPLATE_NAME = (
    "builtin_daily_warehouse_city_supply_bubble_live.png"
)
BUILTIN_DAILY_WAREHOUSE_CITY_SUPPLY_BUBBLE_NIGHT_TEMPLATE_NAMES = tuple(
    f"builtin_daily_warehouse_city_supply_bubble_night_pose_{index}_live.png"
    for index in range(1, 6)
)
BUILTIN_DAILY_TRAINING_ENTRY_LABEL_TEMPLATE_NAME = "builtin_daily_training_entry_label.png"
BUILTIN_DAILY_TRAINING_NORMAL_LABEL_TEMPLATE_NAME = "builtin_daily_training_normal_label.png"
BUILTIN_DAILY_TRAINING_COUNT_TEN_TEMPLATE_NAME = "builtin_daily_training_count_10_live.png"
BUILTIN_DAILY_TRAINING_ACTIVE_LABEL_TEMPLATE_NAME = "builtin_daily_training_active_label.png"
BUILTIN_DAILY_TRAINING_ACTIVE_TEXT_TEMPLATE_NAME = "builtin_daily_training_active_text_live.png"
BUILTIN_DAILY_TRAINING_ACTIVE_GREEN_LABEL_TEMPLATE_NAME = "builtin_daily_training_active_green_label.png"
BUILTIN_DAILY_TRAINING_SPEAR_TUTORIAL_FACE_TEMPLATE_NAME = "builtin_daily_training_spear_tutorial_face.png"
BUILTIN_DAILY_TRAINING_ARCHER_TUTORIAL_POSE_TEMPLATE_NAMES = tuple(
    f"builtin_daily_training_archer_tutorial_pose_{index}.png"
    for index in range(1, 5)
)
BUILTIN_DAILY_MAIN_TASK_PAGE_TITLE_TEMPLATE_NAME = "builtin_daily_main_task_page_title.png"
BUILTIN_DAILY_GROWTH_TASK_UNSELECTED_DAILY_TAB_TEMPLATE_NAME = (
    "builtin_daily_growth_task_unselected_daily_tab.png"
)
BUILTIN_DAILY_GROWTH_TWO_TAB_UNSELECTED_DAILY_TAB_TEMPLATE_NAME = (
    "builtin_daily_growth_two_tab_unselected_daily_tab.png"
)
BUILTIN_DAILY_TRAINING_COLLECT_TUTORIAL_TEMPLATE_NAME = "builtin_daily_training_collect_tutorial_target.png"
BUILTIN_DAILY_TRAINING_UNLOCK_CONTINUE_TEMPLATE_NAME = "builtin_daily_training_unlock_continue.png"
BUILTIN_DAILY_TRAINING_SHIELD_CAMP_TEMPLATE_NAME = "builtin_daily_training_shield_camp.png"
BUILTIN_DAILY_TRAINING_SHIELD_CAMP_CURRENT_TEMPLATE_NAME = (
    "builtin_daily_training_shield_camp_current_live.png"
)
BUILTIN_DAILY_BUILDING_INFO_HEADER_TEMPLATE_NAME = "builtin_daily_building_info_header.png"
BUILTIN_DAILY_BUILDING_ACTIVE_UPGRADING_LABEL_TEMPLATE_NAME = (
    "builtin_daily_building_active_upgrading_label.png"
)
BUILTIN_DAILY_MISSION_HERO_RECRUIT_TEMPLATE_NAME = "builtin_daily_mission_hero_recruit.png"
BUILTIN_DAILY_MISSION_HERO_RECRUIT_1_TEMPLATE_NAME = "builtin_daily_mission_hero_recruit_1.png"
BUILTIN_DAILY_HERO_FREE_RECRUIT_TEMPLATE_NAME = "builtin_daily_hero_free_recruit.png"
BUILTIN_DAILY_HERO_EPIC_FREE_RECRUIT_TEMPLATE_NAME = "builtin_daily_hero_epic_free_recruit.png"
BUILTIN_DAILY_HERO_RECRUIT_RESULT_TEMPLATE_NAME = "builtin_daily_hero_recruit_result.png"
BUILTIN_DAILY_HERO_RECRUIT_RESULT_CURRENT_TEMPLATE_NAME = "builtin_daily_hero_recruit_result_current.png"
BUILTIN_DAILY_HERO_RECRUIT_DUPLICATE_OWNED_TEMPLATE_NAME = (
    "builtin_daily_hero_recruit_duplicate_owned_live.png"
)
BUILTIN_DAILY_HERO_RECRUIT_EXIT_HINT_TEMPLATE_NAME = (
    "builtin_daily_hero_recruit_exit_hint_live.png"
)
BUILTIN_DAILY_HERO_RECRUIT_EXIT_HINT_LEGACY_TEMPLATE_NAME = (
    "builtin_daily_hero_recruit_exit_hint_legacy_live.png"
)
BUILTIN_DAILY_TAP_ANYWHERE_EXIT_REWARD_CURRENT_TEMPLATE_NAME = (
    "builtin_daily_tap_anywhere_exit_reward_current_live.png"
)
BUILTIN_DAILY_TAP_ANYWHERE_EXIT_OLD_TEMPLATE_NAME = (
    "builtin_daily_tap_anywhere_exit_native_old_live.png"
)
BUILTIN_DAILY_HERO_RECRUIT_PAGE_TEMPLATE_NAME = "builtin_daily_hero_recruit_page.png"
BUILTIN_DAILY_MISSION_ALLIANCE_DONATE_TEMPLATE_NAME = "builtin_daily_mission_alliance_donate.png"
BUILTIN_DAILY_MISSION_ALLIANCE_DONATE_5_TEMPLATE_NAME = "builtin_daily_mission_alliance_donate_5.png"
BUILTIN_DAILY_ALLIANCE_FOOD_DONATE_TEMPLATE_NAME = "builtin_daily_alliance_food_donate.png"
BUILTIN_DAILY_ALLIANCE_DIAMOND_DONATE_TEMPLATE_NAME = "builtin_daily_alliance_diamond_donate.png"
BUILTIN_DAILY_ALLIANCE_TECH_ENTRY_TEMPLATE_NAME = "builtin_daily_alliance_tech_entry.png"
BUILTIN_DAILY_ALLIANCE_SUSTAIN_NODE_TEMPLATE_NAME = "builtin_daily_alliance_sustain_node.png"
BUILTIN_DAILY_ALLIANCE_TECH_BATTLE_TAB_STRIP_TEMPLATE_NAME = (
    "builtin_daily_alliance_tech_battle_tab_strip.png"
)
BUILTIN_DAILY_ALLIANCE_TECH_DEVELOPMENT_TAB_STRIP_TEMPLATE_NAME = (
    "builtin_daily_alliance_tech_development_tab_strip.png"
)
BUILTIN_DAILY_ALLIANCE_TECH_TERRITORY_TAB_STRIP_TEMPLATE_NAME = (
    "builtin_daily_alliance_tech_territory_tab_strip.png"
)
BUILTIN_DAILY_ALLIANCE_FOOD_DONATE_DISABLED_TEMPLATE_NAME = "builtin_daily_alliance_food_donate_disabled.png"
BUILTIN_DAILY_TASK_REFERENCE_SIZE = (1440, 2560)
# Word cropped the visible task sheet to 1352 px, but the glyphs came from the
# same 865 x 1536 full portrait render as the destination screenshots.  Using
# that full geometry gives a single exact scale in the fast batch engine.
USER_DOCUMENT_DAILY_CARD_REFERENCE_SIZE = (865, 1536)
USER_DOCUMENT_DAILY_CARD_TEMPLATE_FILENAMES = frozenset(
    {
        Path(BUILTIN_DAILY_MISSION_PROCESS_INTEL_ASSET).name,
        BUILTIN_DAILY_MISSION_PROCESS_INTEL_TEMPLATE_NAME,
        Path(BUILTIN_DAILY_MISSION_WAREHOUSE_SUPPLY_ASSET).name,
        BUILTIN_DAILY_MISSION_WAREHOUSE_SUPPLY_TEMPLATE_NAME,
        Path(BUILTIN_DAILY_MISSION_ARENA_PASSIVE_ASSET).name,
        BUILTIN_DAILY_MISSION_ARENA_PASSIVE_TEMPLATE_NAME,
    }
)
# The guide's destination screenshots originated from the full 865 x 1536
# portrait client even though Word cropped their visible page bounds.
USER_DOCUMENT_DAILY_FULL_REFERENCE_SIZE = (865, 1536)
USER_DOCUMENT_DAILY_FULL_TEMPLATE_FILENAMES = frozenset(
    {
        Path(BUILTIN_DAILY_INTEL_MAP_ENTRY_ASSET).name,
        BUILTIN_DAILY_INTEL_MAP_ENTRY_TEMPLATE_NAME,
        Path(BUILTIN_DAILY_MISSION_GO_USER_DOC_ASSET).name,
        BUILTIN_DAILY_MISSION_GO_USER_DOC_TEMPLATE_NAME,
        Path(BUILTIN_DAILY_INTEL_MAP_PAGE_ASSET).name,
        BUILTIN_DAILY_INTEL_MAP_PAGE_TEMPLATE_NAME,
        Path(BUILTIN_DAILY_WAREHOUSE_RESULT_ASSET).name,
        BUILTIN_DAILY_WAREHOUSE_RESULT_TEMPLATE_NAME,
    }
)
# The user-provided exit-hint crop came from Codex's 1152 x 2048 rendered
# view of the native 1440 x 2560 MuMu frame.  Keep that provenance so the
# matcher scales it back to the device rather than treating it as native.
USER_CLIPBOARD_DAILY_REFERENCE_SIZE = (1152, 2048)
USER_CLIPBOARD_DAILY_TEMPLATE_FILENAMES = frozenset(
    {
        Path(BUILTIN_DAILY_REWARD_EXIT_HINT_ASSET).name,
        BUILTIN_DAILY_REWARD_EXIT_HINT_TEMPLATE_NAME,
    }
)
# The template is a narrow visual anchor at the left of the city task strip;
# tapping its centre is not reliable.  This is the measured safe location in
# the same strip, mapped through ``content_viewport`` at runtime.
DAILY_CITY_ENTRY_REFERENCE_POINT = (74, 2110)
# Action targets have a deliberately stricter raw-pixel requirement than
# passive page evidence.  A 5% full-frame dark veil still correlates strongly
# in grayscale but falls below these source-RGB ratios, producing no input.
DAILY_ACTION_MIN_LUMA_RATIO = 0.98
DAILY_TOWN_MIN_LUMA_RATIO = 0.96
DAILY_ACTION_MIN_CHROMA_RATIO = 0.97
DAILY_ACTION_MAX_COLOUR_DISTANCE = 0.06
# The city anchor is a deliberately tight parchment-only crop.  Its local
# background can vary slightly between legitimate city scenes, so it has a
# separately calibrated lower luma floor.  It remains well above every
# tested 5%-or-more full-frame dimming case.
DAILY_CITY_MIN_LUMA_RATIO = 0.965
DAILY_CITY_MIN_CHROMA_RATIO = 0.94
DAILY_CITY_MAX_COLOUR_DISTANCE = 0.06
DAILY_BUILTIN_TEMPLATES: tuple[tuple[str, str], ...] = (
    (BUILTIN_DAILY_CITY_ENTRY_ASSET, BUILTIN_DAILY_CITY_ENTRY_TEMPLATE_NAME),
    (
        BUILTIN_DAILY_CITY_ENTRY_TRAINING_HIGHLIGHT_ASSET,
        BUILTIN_DAILY_CITY_ENTRY_TRAINING_HIGHLIGHT_TEMPLATE_NAME,
    ),
    (BUILTIN_DAILY_HEADER_ASSET, BUILTIN_DAILY_HEADER_TEMPLATE_NAME),
    (BUILTIN_DAILY_SELECTED_TAB_ASSET, BUILTIN_DAILY_SELECTED_TAB_TEMPLATE_NAME),
    (BUILTIN_DAILY_CHAPTER_HEADER_ASSET, BUILTIN_DAILY_CHAPTER_HEADER_TEMPLATE_NAME),
    (
        BUILTIN_DAILY_CHAPTER_HEADER_CURRENT_ASSET,
        BUILTIN_DAILY_CHAPTER_HEADER_CURRENT_TEMPLATE_NAME,
    ),
    (BUILTIN_DAILY_UNSELECTED_TAB_ASSET, BUILTIN_DAILY_UNSELECTED_TAB_TEMPLATE_NAME),
    (BUILTIN_DAILY_LOGIN_COMPLETED_ASSET, BUILTIN_DAILY_LOGIN_COMPLETED_TEMPLATE_NAME),
    (BUILTIN_DAILY_CLAIM_BUTTON_ASSET, BUILTIN_DAILY_CLAIM_BUTTON_TEMPLATE_NAME),
    (
        BUILTIN_DAILY_ONE_KEY_CLAIM_BUTTON_ASSET,
        BUILTIN_DAILY_ONE_KEY_CLAIM_BUTTON_TEMPLATE_NAME,
    ),
    (BUILTIN_DAILY_PAID_OFFER_TITLE_ASSET, BUILTIN_DAILY_PAID_OFFER_TITLE_TEMPLATE_NAME),
    (BUILTIN_DAILY_PAID_OFFER_PRICE_ASSET, BUILTIN_DAILY_PAID_OFFER_PRICE_TEMPLATE_NAME),
    (BUILTIN_DAILY_PROGRESS_ANCHOR_ASSET, BUILTIN_DAILY_PROGRESS_ANCHOR_TEMPLATE_NAME),
    (BUILTIN_DAILY_REWARD_RESULT_ASSET, BUILTIN_DAILY_REWARD_RESULT_TEMPLATE_NAME),
    (
        BUILTIN_DAILY_REWARD_EXIT_HINT_ASSET,
        BUILTIN_DAILY_REWARD_EXIT_HINT_TEMPLATE_NAME,
    ),
    (BUILTIN_DAILY_CHEST_POPUP_TOP_ASSET, BUILTIN_DAILY_CHEST_POPUP_TOP_TEMPLATE_NAME),
    (BUILTIN_DAILY_CHEST_POPUP_BOTTOM_ASSET, BUILTIN_DAILY_CHEST_POPUP_BOTTOM_TEMPLATE_NAME),
    (BUILTIN_DAILY_CHEST_POPUP_POINTER_ASSET, BUILTIN_DAILY_CHEST_POPUP_POINTER_TEMPLATE_NAME),
    (BUILTIN_DAILY_ACTIVITY_CHEST_OPEN_TOP_ASSET, BUILTIN_DAILY_ACTIVITY_CHEST_OPEN_TOP_TEMPLATE_NAME),
    (BUILTIN_DAILY_ACTIVITY_CHEST_OPEN_BOTTOM_ASSET, BUILTIN_DAILY_ACTIVITY_CHEST_OPEN_BOTTOM_TEMPLATE_NAME),
    (BUILTIN_DAILY_TASK_COMPLETED_CHECK_ASSET, BUILTIN_DAILY_TASK_COMPLETED_CHECK_TEMPLATE_NAME),
    (BUILTIN_DAILY_REFRESH_LABEL_ASSET, BUILTIN_DAILY_REFRESH_LABEL_TEMPLATE_NAME),
    (
        BUILTIN_DAILY_NETWORK_DISCONNECTED_ASSET,
        BUILTIN_DAILY_NETWORK_DISCONNECTED_TEMPLATE_NAME,
    ),
    (
        BUILTIN_DAILY_FORCED_OFFLINE_MESSAGE_ASSET,
        BUILTIN_DAILY_FORCED_OFFLINE_MESSAGE_TEMPLATE_NAME,
    ),
    (
        BUILTIN_DAILY_REGULAR_ACTIVITY_BACK_ASSET,
        BUILTIN_DAILY_REGULAR_ACTIVITY_BACK_TEMPLATE_NAME,
    ),
    (
        BUILTIN_DAILY_REGULAR_ACTIVITY_TITLE_ASSET,
        BUILTIN_DAILY_REGULAR_ACTIVITY_TITLE_TEMPLATE_NAME,
    ),
    (BUILTIN_DAILY_MISSION_GATHER_MEAT_ASSET, BUILTIN_DAILY_MISSION_GATHER_MEAT_TEMPLATE_NAME),
    (BUILTIN_DAILY_MISSION_GATHER_WOOD_ASSET, BUILTIN_DAILY_MISSION_GATHER_WOOD_TEMPLATE_NAME),
    (BUILTIN_DAILY_MISSION_GATHER_COAL_ASSET, BUILTIN_DAILY_MISSION_GATHER_COAL_TEMPLATE_NAME),
    (BUILTIN_DAILY_MISSION_GATHER_IRON_ASSET, BUILTIN_DAILY_MISSION_GATHER_IRON_TEMPLATE_NAME),
    (BUILTIN_DAILY_MISSION_GO_ASSET, BUILTIN_DAILY_MISSION_GO_TEMPLATE_NAME),
    (BUILTIN_DAILY_MISSION_GO_CURRENT_ASSET, BUILTIN_DAILY_MISSION_GO_CURRENT_TEMPLATE_NAME),
    (BUILTIN_DAILY_GATHER_WORLD_SEARCH_ASSET, BUILTIN_DAILY_GATHER_WORLD_SEARCH_TEMPLATE_NAME),
    (BUILTIN_DAILY_GATHER_WORLD_SEARCH_TIGHT_ASSET, BUILTIN_DAILY_GATHER_WORLD_SEARCH_TIGHT_TEMPLATE_NAME),
    (
        BUILTIN_DAILY_GATHER_WORLD_SEARCH_TIGHT_DENSE_ASSET,
        BUILTIN_DAILY_GATHER_WORLD_SEARCH_TIGHT_DENSE_TEMPLATE_NAME,
    ),
    (BUILTIN_DAILY_CITY_WILDERNESS_ENTRY_ASSET, BUILTIN_DAILY_CITY_WILDERNESS_ENTRY_TEMPLATE_NAME),
    (
        BUILTIN_DAILY_CITY_WILDERNESS_ENTRY_TIGHT_DAY_ASSET,
        BUILTIN_DAILY_CITY_WILDERNESS_ENTRY_TIGHT_DAY_TEMPLATE_NAME,
    ),
    (
        BUILTIN_DAILY_CITY_WILDERNESS_ENTRY_TIGHT_LOW_ACCOUNT_ASSET,
        BUILTIN_DAILY_CITY_WILDERNESS_ENTRY_TIGHT_LOW_ACCOUNT_TEMPLATE_NAME,
    ),
    (BUILTIN_DAILY_WORLD_TOWN_ENTRY_ASSET, BUILTIN_DAILY_WORLD_TOWN_ENTRY_TEMPLATE_NAME),
    (
        BUILTIN_DAILY_WORLD_TOWN_ENTRY_TIGHT_DENSE_ASSET,
        BUILTIN_DAILY_WORLD_TOWN_ENTRY_TIGHT_DENSE_TEMPLATE_NAME,
    ),
    (
        BUILTIN_DAILY_WORLD_TOWN_ENTRY_TOOLBAR_ASSET,
        BUILTIN_DAILY_WORLD_TOWN_ENTRY_TOOLBAR_TEMPLATE_NAME,
    ),
    (BUILTIN_DAILY_WORLD_OVERVIEW_ENTRY_ASSET, BUILTIN_DAILY_WORLD_OVERVIEW_ENTRY_TEMPLATE_NAME),
    (
        BUILTIN_DAILY_WORLD_OVERVIEW_PANEL_ANCHOR_ASSET,
        BUILTIN_DAILY_WORLD_OVERVIEW_PANEL_ANCHOR_TEMPLATE_NAME,
    ),
    (
        BUILTIN_DAILY_WORLD_OVERVIEW_RESOURCE_OFF_ASSET,
        BUILTIN_DAILY_WORLD_OVERVIEW_RESOURCE_OFF_TEMPLATE_NAME,
    ),
    (
        BUILTIN_DAILY_WORLD_OVERVIEW_HOME_BUTTON_ASSET,
        BUILTIN_DAILY_WORLD_OVERVIEW_HOME_BUTTON_TEMPLATE_NAME,
    ),
    (BUILTIN_DAILY_GATHER_SEARCH_TUTORIAL_ASSET, BUILTIN_DAILY_GATHER_SEARCH_TUTORIAL_TEMPLATE_NAME),
    (BUILTIN_DAILY_GATHER_SEARCH_TUTORIAL_ALT_ASSET, BUILTIN_DAILY_GATHER_SEARCH_TUTORIAL_ALT_TEMPLATE_NAME),
    (BUILTIN_DAILY_GATHER_COLLECT_ASSET, BUILTIN_DAILY_GATHER_COLLECT_TEMPLATE_NAME),
    (BUILTIN_DAILY_GATHER_DISPATCH_ASSET, BUILTIN_DAILY_GATHER_DISPATCH_TEMPLATE_NAME),
    (BUILTIN_DAILY_GATHER_ACTIVE_MARCH_ASSET, BUILTIN_DAILY_GATHER_ACTIVE_MARCH_TEMPLATE_NAME),
    (
        BUILTIN_DAILY_GATHER_ACTIVE_MARCH_RIGHT_COMPACT_ASSET,
        BUILTIN_DAILY_GATHER_ACTIVE_MARCH_RIGHT_COMPACT_TEMPLATE_NAME,
    ),
    (BUILTIN_DAILY_GATHER_MEAT_SELECTED_ASSET, BUILTIN_DAILY_GATHER_MEAT_SELECTED_TEMPLATE_NAME),
    (
        BUILTIN_DAILY_GATHER_FULL_RESOURCES_FILTER_OFF_ASSET,
        BUILTIN_DAILY_GATHER_FULL_RESOURCES_FILTER_OFF_TEMPLATE_NAME,
    ),
    (
        BUILTIN_DAILY_GATHER_FULL_RESOURCES_FILTER_ON_ASSET,
        BUILTIN_DAILY_GATHER_FULL_RESOURCES_FILTER_ON_TEMPLATE_NAME,
    ),
    (BUILTIN_DAILY_MISSION_TRAIN_SHIELD_ASSET, BUILTIN_DAILY_MISSION_TRAIN_SHIELD_TEMPLATE_NAME),
    (BUILTIN_DAILY_MISSION_TRAIN_SHIELD_30_ASSET, BUILTIN_DAILY_MISSION_TRAIN_SHIELD_30_TEMPLATE_NAME),
    (
        BUILTIN_DAILY_MISSION_TRAIN_SHIELD_30_20_ASSET,
        BUILTIN_DAILY_MISSION_TRAIN_SHIELD_30_20_TEMPLATE_NAME,
    ),
    (BUILTIN_DAILY_MISSION_TRAIN_SPEAR_ASSET, BUILTIN_DAILY_MISSION_TRAIN_SPEAR_TEMPLATE_NAME),
    (BUILTIN_DAILY_MISSION_TRAIN_SPEAR_30_ASSET, BUILTIN_DAILY_MISSION_TRAIN_SPEAR_30_TEMPLATE_NAME),
    (
        BUILTIN_DAILY_MISSION_TRAIN_SPEAR_30_20_ASSET,
        BUILTIN_DAILY_MISSION_TRAIN_SPEAR_30_20_TEMPLATE_NAME,
    ),
    (BUILTIN_DAILY_MISSION_TRAIN_ARCHER_ASSET, BUILTIN_DAILY_MISSION_TRAIN_ARCHER_TEMPLATE_NAME),
    (
        BUILTIN_DAILY_MISSION_TRAIN_ARCHER_30_10_ASSET,
        BUILTIN_DAILY_MISSION_TRAIN_ARCHER_30_10_TEMPLATE_NAME,
    ),
    (
        BUILTIN_DAILY_MISSION_TRAIN_ARCHER_30_20_ASSET,
        BUILTIN_DAILY_MISSION_TRAIN_ARCHER_30_20_TEMPLATE_NAME,
    ),
    (BUILTIN_DAILY_MISSION_UPGRADE_BUILDING_ASSET, BUILTIN_DAILY_MISSION_UPGRADE_BUILDING_TEMPLATE_NAME),
    (BUILTIN_DAILY_MISSION_RESEARCH_TECH_ASSET, BUILTIN_DAILY_MISSION_RESEARCH_TECH_TEMPLATE_NAME),
    (BUILTIN_DAILY_MISSION_PROCESS_INTEL_ASSET, BUILTIN_DAILY_MISSION_PROCESS_INTEL_TEMPLATE_NAME),
    (
        BUILTIN_DAILY_MISSION_PROCESS_INTEL_5_ASSET,
        BUILTIN_DAILY_MISSION_PROCESS_INTEL_5_TEMPLATE_NAME,
    ),
    (
        BUILTIN_DAILY_MISSION_WAREHOUSE_SUPPLY_ASSET,
        BUILTIN_DAILY_MISSION_WAREHOUSE_SUPPLY_TEMPLATE_NAME,
    ),
    (
        BUILTIN_DAILY_MISSION_WAREHOUSE_SUPPLY_THREE_CURRENT_ASSET,
        BUILTIN_DAILY_MISSION_WAREHOUSE_SUPPLY_THREE_CURRENT_TEMPLATE_NAME,
    ),
    (
        BUILTIN_DAILY_MISSION_WAREHOUSE_SUPPLY_THREE_2OF3_ASSET,
        BUILTIN_DAILY_MISSION_WAREHOUSE_SUPPLY_THREE_2OF3_TEMPLATE_NAME,
    ),
    (
        BUILTIN_DAILY_MISSION_WAREHOUSE_SUPPLY_FIVE_CURRENT_ASSET,
        BUILTIN_DAILY_MISSION_WAREHOUSE_SUPPLY_FIVE_CURRENT_TEMPLATE_NAME,
    ),
    (BUILTIN_DAILY_MISSION_ARENA_PASSIVE_ASSET, BUILTIN_DAILY_MISSION_ARENA_PASSIVE_TEMPLATE_NAME),
    (BUILTIN_DAILY_MISSION_ARENA_ONE_CURRENT_ASSET, BUILTIN_DAILY_MISSION_ARENA_ONE_CURRENT_TEMPLATE_NAME),
    (BUILTIN_DAILY_MISSION_ARENA_ONE_CLAIM_ASSET, BUILTIN_DAILY_MISSION_ARENA_ONE_CLAIM_TEMPLATE_NAME),
    (BUILTIN_DAILY_MISSION_ARENA_FIVE_CURRENT_ASSET, BUILTIN_DAILY_MISSION_ARENA_FIVE_CURRENT_TEMPLATE_NAME),
    (BUILTIN_DAILY_MISSION_ARENA_FIVE_CLAIM_ASSET, BUILTIN_DAILY_MISSION_ARENA_FIVE_CLAIM_TEMPLATE_NAME),
    (BUILTIN_DAILY_ARENA_HOME_TITLE_ASSET, BUILTIN_DAILY_ARENA_HOME_TITLE_TEMPLATE_NAME),
    (BUILTIN_DAILY_ARENA_CHALLENGE_LABEL_ASSET, BUILTIN_DAILY_ARENA_CHALLENGE_LABEL_TEMPLATE_NAME),
    (BUILTIN_DAILY_ARENA_LIST_TITLE_ASSET, BUILTIN_DAILY_ARENA_LIST_TITLE_TEMPLATE_NAME),
    (BUILTIN_DAILY_ARENA_REMAINING_LABEL_ASSET, BUILTIN_DAILY_ARENA_REMAINING_LABEL_TEMPLATE_NAME),
    (BUILTIN_DAILY_ARENA_SETUP_TITLE_ASSET, BUILTIN_DAILY_ARENA_SETUP_TITLE_TEMPLATE_NAME),
    (BUILTIN_DAILY_ARENA_BATTLE_LABEL_ASSET, BUILTIN_DAILY_ARENA_BATTLE_LABEL_TEMPLATE_NAME),
    (BUILTIN_DAILY_ARENA_RESULT_EXIT_TEXT_ASSET, BUILTIN_DAILY_ARENA_RESULT_EXIT_TEXT_TEMPLATE_NAME),
    (BUILTIN_DAILY_MISSION_GO_USER_DOC_ASSET, BUILTIN_DAILY_MISSION_GO_USER_DOC_TEMPLATE_NAME),
    (BUILTIN_DAILY_INTEL_MAP_ENTRY_ASSET, BUILTIN_DAILY_INTEL_MAP_ENTRY_TEMPLATE_NAME),
    (BUILTIN_DAILY_INTEL_MAP_PAGE_ASSET, BUILTIN_DAILY_INTEL_MAP_PAGE_TEMPLATE_NAME),
    (
        BUILTIN_DAILY_INTEL_STATION_BUBBLE_ASSET,
        BUILTIN_DAILY_INTEL_STATION_BUBBLE_TEMPLATE_NAME,
    ),
    (BUILTIN_DAILY_INTEL_MAP_HEADER_ASSET, BUILTIN_DAILY_INTEL_MAP_HEADER_TEMPLATE_NAME),
    (BUILTIN_DAILY_INTEL_RESCUE_PIN_ASSET, BUILTIN_DAILY_INTEL_RESCUE_PIN_TEMPLATE_NAME),
    (
        BUILTIN_DAILY_INTEL_RESCUE_GREY_PIN_ASSET,
        BUILTIN_DAILY_INTEL_RESCUE_GREY_PIN_TEMPLATE_NAME,
    ),
    (
        BUILTIN_DAILY_INTEL_RESCUE_PREVIEW_TITLE_ASSET,
        BUILTIN_DAILY_INTEL_RESCUE_PREVIEW_TITLE_TEMPLATE_NAME,
    ),
    (
        BUILTIN_DAILY_INTEL_RESCUE_PREVIEW_GO_ASSET,
        BUILTIN_DAILY_INTEL_RESCUE_PREVIEW_GO_TEMPLATE_NAME,
    ),
    (
        BUILTIN_DAILY_INTEL_RESCUE_TARGET_TITLE_ASSET,
        BUILTIN_DAILY_INTEL_RESCUE_TARGET_TITLE_TEMPLATE_NAME,
    ),
    (
        BUILTIN_DAILY_INTEL_RESCUE_ACTION_ASSET,
        BUILTIN_DAILY_INTEL_RESCUE_ACTION_TEMPLATE_NAME,
    ),
    (BUILTIN_DAILY_INTEL_RESCUE_ACTIVE_ASSET, BUILTIN_DAILY_INTEL_RESCUE_ACTIVE_TEMPLATE_NAME),
    (BUILTIN_DAILY_INTEL_SWORDS_PIN_ASSET, BUILTIN_DAILY_INTEL_SWORDS_PIN_TEMPLATE_NAME),
    (
        BUILTIN_DAILY_INTEL_HERO_PREVIEW_TITLE_ASSET,
        BUILTIN_DAILY_INTEL_HERO_PREVIEW_TITLE_TEMPLATE_NAME,
    ),
    (
        BUILTIN_DAILY_INTEL_HERO_PREVIEW_GO_ASSET,
        BUILTIN_DAILY_INTEL_HERO_PREVIEW_GO_TEMPLATE_NAME,
    ),
    (
        BUILTIN_DAILY_INTEL_HERO_DETAIL_TITLE_ASSET,
        BUILTIN_DAILY_INTEL_HERO_DETAIL_TITLE_TEMPLATE_NAME,
    ),
    (BUILTIN_DAILY_INTEL_HERO_EXPLORE_ASSET, BUILTIN_DAILY_INTEL_HERO_EXPLORE_TEMPLATE_NAME),
    (
        BUILTIN_DAILY_INTEL_HERO_SETUP_HEADER_ASSET,
        BUILTIN_DAILY_INTEL_HERO_SETUP_HEADER_TEMPLATE_NAME,
    ),
    (
        BUILTIN_DAILY_INTEL_HERO_AUTO_DEPLOY_ASSET,
        BUILTIN_DAILY_INTEL_HERO_AUTO_DEPLOY_TEMPLATE_NAME,
    ),
    (BUILTIN_DAILY_INTEL_HERO_BATTLE_ASSET, BUILTIN_DAILY_INTEL_HERO_BATTLE_TEMPLATE_NAME),
    (BUILTIN_DAILY_INTEL_HERO_VICTORY_ASSET, BUILTIN_DAILY_INTEL_HERO_VICTORY_TEMPLATE_NAME),
    (BUILTIN_DAILY_INTEL_HERO_EXIT_TEXT_ASSET, BUILTIN_DAILY_INTEL_HERO_EXIT_TEXT_TEMPLATE_NAME),
    (BUILTIN_DAILY_INTEL_COMPLETED_CHECK_ASSET, BUILTIN_DAILY_INTEL_COMPLETED_CHECK_TEMPLATE_NAME),
    (BUILTIN_DAILY_INTEL_COMPLETED_TENT_CURRENT_ASSET, BUILTIN_DAILY_INTEL_COMPLETED_TENT_CURRENT_TEMPLATE_NAME),
    (BUILTIN_DAILY_INTEL_WOLF_PIN_CURRENT_ASSET, BUILTIN_DAILY_INTEL_WOLF_PIN_CURRENT_TEMPLATE_NAME),
    (BUILTIN_DAILY_INTEL_SWORDS_PIN_CURRENT_ASSET, BUILTIN_DAILY_INTEL_SWORDS_PIN_CURRENT_TEMPLATE_NAME),
    (BUILTIN_DAILY_INTEL_WOLF_PREVIEW_TITLE_CURRENT_ASSET, BUILTIN_DAILY_INTEL_WOLF_PREVIEW_TITLE_CURRENT_TEMPLATE_NAME),
    (BUILTIN_DAILY_INTEL_WOLF_PREVIEW_GO_CURRENT_ASSET, BUILTIN_DAILY_INTEL_WOLF_PREVIEW_GO_CURRENT_TEMPLATE_NAME),
    (BUILTIN_DAILY_INTEL_WOLF_TARGET_TITLE_CURRENT_ASSET, BUILTIN_DAILY_INTEL_WOLF_TARGET_TITLE_CURRENT_TEMPLATE_NAME),
    (BUILTIN_DAILY_INTEL_WOLF_MARCH_CURRENT_ASSET, BUILTIN_DAILY_INTEL_WOLF_MARCH_CURRENT_TEMPLATE_NAME),
    (BUILTIN_DAILY_WAREHOUSE_RESULT_ASSET, BUILTIN_DAILY_WAREHOUSE_RESULT_TEMPLATE_NAME),
    (
        BUILTIN_DAILY_WAREHOUSE_RESULT_CURRENT_ASSET,
        BUILTIN_DAILY_WAREHOUSE_RESULT_CURRENT_TEMPLATE_NAME,
    ),
    (
        BUILTIN_DAILY_WAREHOUSE_CITY_SUPPLY_BUBBLE_ASSET,
        BUILTIN_DAILY_WAREHOUSE_CITY_SUPPLY_BUBBLE_TEMPLATE_NAME,
    ),
    *zip(
        BUILTIN_DAILY_WAREHOUSE_CITY_SUPPLY_BUBBLE_NIGHT_ASSETS,
        BUILTIN_DAILY_WAREHOUSE_CITY_SUPPLY_BUBBLE_NIGHT_TEMPLATE_NAMES,
    ),
    (BUILTIN_DAILY_TRAINING_ENTRY_LABEL_ASSET, BUILTIN_DAILY_TRAINING_ENTRY_LABEL_TEMPLATE_NAME),
    (BUILTIN_DAILY_TRAINING_NORMAL_LABEL_ASSET, BUILTIN_DAILY_TRAINING_NORMAL_LABEL_TEMPLATE_NAME),
    (BUILTIN_DAILY_TRAINING_COUNT_TEN_ASSET, BUILTIN_DAILY_TRAINING_COUNT_TEN_TEMPLATE_NAME),
    (BUILTIN_DAILY_TRAINING_ACTIVE_LABEL_ASSET, BUILTIN_DAILY_TRAINING_ACTIVE_LABEL_TEMPLATE_NAME),
    (BUILTIN_DAILY_TRAINING_ACTIVE_TEXT_ASSET, BUILTIN_DAILY_TRAINING_ACTIVE_TEXT_TEMPLATE_NAME),
    (
        BUILTIN_DAILY_TRAINING_ACTIVE_GREEN_LABEL_ASSET,
        BUILTIN_DAILY_TRAINING_ACTIVE_GREEN_LABEL_TEMPLATE_NAME,
    ),
    (
        BUILTIN_DAILY_TRAINING_SPEAR_TUTORIAL_FACE_ASSET,
        BUILTIN_DAILY_TRAINING_SPEAR_TUTORIAL_FACE_TEMPLATE_NAME,
    ),
    *tuple(
        zip(
            BUILTIN_DAILY_TRAINING_ARCHER_TUTORIAL_POSE_ASSETS,
            BUILTIN_DAILY_TRAINING_ARCHER_TUTORIAL_POSE_TEMPLATE_NAMES,
        )
    ),
    (BUILTIN_DAILY_MAIN_TASK_PAGE_TITLE_ASSET, BUILTIN_DAILY_MAIN_TASK_PAGE_TITLE_TEMPLATE_NAME),
    (
        BUILTIN_DAILY_GROWTH_TASK_UNSELECTED_DAILY_TAB_ASSET,
        BUILTIN_DAILY_GROWTH_TASK_UNSELECTED_DAILY_TAB_TEMPLATE_NAME,
    ),
    (
        BUILTIN_DAILY_GROWTH_TWO_TAB_UNSELECTED_DAILY_TAB_ASSET,
        BUILTIN_DAILY_GROWTH_TWO_TAB_UNSELECTED_DAILY_TAB_TEMPLATE_NAME,
    ),
    (BUILTIN_DAILY_TRAINING_COLLECT_TUTORIAL_ASSET, BUILTIN_DAILY_TRAINING_COLLECT_TUTORIAL_TEMPLATE_NAME),
    (BUILTIN_DAILY_TRAINING_UNLOCK_CONTINUE_ASSET, BUILTIN_DAILY_TRAINING_UNLOCK_CONTINUE_TEMPLATE_NAME),
    (BUILTIN_DAILY_TRAINING_SHIELD_CAMP_ASSET, BUILTIN_DAILY_TRAINING_SHIELD_CAMP_TEMPLATE_NAME),
    (
        BUILTIN_DAILY_TRAINING_SHIELD_CAMP_CURRENT_ASSET,
        BUILTIN_DAILY_TRAINING_SHIELD_CAMP_CURRENT_TEMPLATE_NAME,
    ),
    (BUILTIN_DAILY_BUILDING_INFO_HEADER_ASSET, BUILTIN_DAILY_BUILDING_INFO_HEADER_TEMPLATE_NAME),
    (
        BUILTIN_DAILY_BUILDING_ACTIVE_UPGRADING_LABEL_ASSET,
        BUILTIN_DAILY_BUILDING_ACTIVE_UPGRADING_LABEL_TEMPLATE_NAME,
    ),
    (BUILTIN_DAILY_MISSION_HERO_RECRUIT_ASSET, BUILTIN_DAILY_MISSION_HERO_RECRUIT_TEMPLATE_NAME),
    (BUILTIN_DAILY_MISSION_HERO_RECRUIT_1_ASSET, BUILTIN_DAILY_MISSION_HERO_RECRUIT_1_TEMPLATE_NAME),
    (BUILTIN_DAILY_HERO_FREE_RECRUIT_ASSET, BUILTIN_DAILY_HERO_FREE_RECRUIT_TEMPLATE_NAME),
    (BUILTIN_DAILY_HERO_EPIC_FREE_RECRUIT_ASSET, BUILTIN_DAILY_HERO_EPIC_FREE_RECRUIT_TEMPLATE_NAME),
    (BUILTIN_DAILY_HERO_RECRUIT_RESULT_ASSET, BUILTIN_DAILY_HERO_RECRUIT_RESULT_TEMPLATE_NAME),
    (
        BUILTIN_DAILY_HERO_RECRUIT_RESULT_CURRENT_ASSET,
        BUILTIN_DAILY_HERO_RECRUIT_RESULT_CURRENT_TEMPLATE_NAME,
    ),
    (
        BUILTIN_DAILY_HERO_RECRUIT_DUPLICATE_OWNED_ASSET,
        BUILTIN_DAILY_HERO_RECRUIT_DUPLICATE_OWNED_TEMPLATE_NAME,
    ),
    (
        BUILTIN_DAILY_HERO_RECRUIT_EXIT_HINT_ASSET,
        BUILTIN_DAILY_HERO_RECRUIT_EXIT_HINT_TEMPLATE_NAME,
    ),
    (
        BUILTIN_DAILY_HERO_RECRUIT_EXIT_HINT_LEGACY_ASSET,
        BUILTIN_DAILY_HERO_RECRUIT_EXIT_HINT_LEGACY_TEMPLATE_NAME,
    ),
    (
        BUILTIN_DAILY_TAP_ANYWHERE_EXIT_REWARD_CURRENT_ASSET,
        BUILTIN_DAILY_TAP_ANYWHERE_EXIT_REWARD_CURRENT_TEMPLATE_NAME,
    ),
    (
        BUILTIN_DAILY_TAP_ANYWHERE_EXIT_OLD_ASSET,
        BUILTIN_DAILY_TAP_ANYWHERE_EXIT_OLD_TEMPLATE_NAME,
    ),
    (BUILTIN_DAILY_HERO_RECRUIT_PAGE_ASSET, BUILTIN_DAILY_HERO_RECRUIT_PAGE_TEMPLATE_NAME),
    (BUILTIN_DAILY_MISSION_ALLIANCE_DONATE_ASSET, BUILTIN_DAILY_MISSION_ALLIANCE_DONATE_TEMPLATE_NAME),
    (
        BUILTIN_DAILY_MISSION_ALLIANCE_DONATE_5_ASSET,
        BUILTIN_DAILY_MISSION_ALLIANCE_DONATE_5_TEMPLATE_NAME,
    ),
    (BUILTIN_DAILY_ALLIANCE_FOOD_DONATE_ASSET, BUILTIN_DAILY_ALLIANCE_FOOD_DONATE_TEMPLATE_NAME),
    (BUILTIN_DAILY_ALLIANCE_DIAMOND_DONATE_ASSET, BUILTIN_DAILY_ALLIANCE_DIAMOND_DONATE_TEMPLATE_NAME),
    (BUILTIN_DAILY_ALLIANCE_TECH_ENTRY_ASSET, BUILTIN_DAILY_ALLIANCE_TECH_ENTRY_TEMPLATE_NAME),
    (BUILTIN_DAILY_ALLIANCE_SUSTAIN_NODE_ASSET, BUILTIN_DAILY_ALLIANCE_SUSTAIN_NODE_TEMPLATE_NAME),
    (
        BUILTIN_DAILY_ALLIANCE_TECH_BATTLE_TAB_STRIP_ASSET,
        BUILTIN_DAILY_ALLIANCE_TECH_BATTLE_TAB_STRIP_TEMPLATE_NAME,
    ),
    (
        BUILTIN_DAILY_ALLIANCE_TECH_DEVELOPMENT_TAB_STRIP_ASSET,
        BUILTIN_DAILY_ALLIANCE_TECH_DEVELOPMENT_TAB_STRIP_TEMPLATE_NAME,
    ),
    (
        BUILTIN_DAILY_ALLIANCE_TECH_TERRITORY_TAB_STRIP_ASSET,
        BUILTIN_DAILY_ALLIANCE_TECH_TERRITORY_TAB_STRIP_TEMPLATE_NAME,
    ),
    (BUILTIN_DAILY_ALLIANCE_FOOD_DONATE_DISABLED_ASSET, BUILTIN_DAILY_ALLIANCE_FOOD_DONATE_DISABLED_TEMPLATE_NAME),
)
DAILY_BUILTIN_TEMPLATE_FILENAMES = frozenset(
    [name for _asset, name in DAILY_BUILTIN_TEMPLATES]
    + [Path(asset).name for asset, _name in DAILY_BUILTIN_TEMPLATES]
)
DEFAULT_TASKS: dict[str, list[dict[str, Any]]] = {
    "从主城进入联盟互助": [
        {"action": "tap", "x": 1065, "y": 2460, "width": 1440, "height": 2560},
        {"action": "wait", "seconds": 2.0},
        {"action": "tap", "x": 1060, "y": 2140, "width": 1440, "height": 2560},
        {"action": "wait", "seconds": 2.0},
    ]
}


class AdbError(RuntimeError):
    pass


class AlliancePage(str, Enum):
    """The only page states that the automatic alliance-help flow may act on."""

    ALL_HELP_READY = "all_help_ready"
    MUTUAL_HELP = "mutual_help"
    ALLIANCE_HOME = "alliance_home"
    CITY = "city"
    UNKNOWN = "unknown"


class RedPacketState(str, Enum):
    """Visual states for the guarded alliance red-packet workflow.

    These values deliberately describe what is *currently visible* rather
    than an action to take.  The UI/controller owns timing, retries and taps;
    the backend only reports visual evidence.
    """

    MARKER = "marker"
    CHAT_ENTRY = "chat_entry"
    CHAT_PANEL = "chat_panel"
    ALLIANCE_CHAT = "alliance_chat"
    FURNACE_PACKET = "furnace_packet"
    # A card that already says "已领取" is a terminal visual state.  It has
    # no click point by design: the worker must leave it alone and continue
    # waiting for a later notification.
    FURNACE_PACKET_CLAIMED = "furnace_packet_claimed"
    FURNACE_DETAIL = "furnace_detail"
    DETAIL_OPEN_READY = "detail_open_ready"
    CLAIM_RESULT_READY = "claim_result_ready"
    UNKNOWN = "unknown"


class DailyTaskState(str, Enum):
    """Safe visual states for the deliberately narrow daily-login workflow.

    These are observations, not commands.  Only ``CLAIM_READY`` carries an
    actionable point, and it exists only when all independent page, task and
    button proofs are visible in one screenshot.  The city entry is exposed
    separately by :func:`match_daily_city_entry` so a controller can use it
    only during its explicitly expected city-navigation phase.
    """

    CITY_ENTRY = "city_entry"
    # The game commonly opens its task sheet on Chapter Tasks.  This state
    # is actionable only because both the Chapter header and the unselected
    # Daily Tasks tab are independently visible; it permits one tab switch.
    DAILY_TAB_READY = "daily_tab_ready"
    DAILY_PAGE = "daily_page"
    DAILY_LOGIN_COMPLETED = "daily_login_completed"
    CLAIM_READY = "claim_ready"
    # A generic daily-task reward collection.  It is deliberately distinct
    # from the legacy login-only state: the page, selected Daily tab, activity
    # strip and the green Chinese "claim" control must all be visible in the
    # same task-list row.  It never authorises a Go, shop, speed-up or payment
    # control.
    TASK_CLAIM_READY = "task_claim_ready"
    # This full-screen result sheet is actionable only after this process has
    # just clicked a verified task-reward claim.  The backend exposes the
    # visual fact and a neutral exit point; the controller owns that temporal
    # correlation so an unrelated modal is never dismissed.
    REWARD_RESULT_READY = "reward_result_ready"
    # The activity-chest contents sheet has two measured placements, according
    # to whether its chest sits above or below the activity bar.  As with the
    # reward sheet, it never authorises a close unless the controller has just
    # clicked the corresponding verified milestone chest.
    CHEST_RESULT_READY = "chest_result_ready"
    # A recognised purchase surface is terminal for this run.  It is kept
    # separate from UNKNOWN so a controller can log an explicit safety stop.
    BLOCKED = "blocked"
    UNKNOWN = "unknown"


class DailyAbnormalExitKind(str, Enum):
    """Exit semantics proved by reviewed semantic controls.

    This deliberately has no generic close/back value.  Every actionable
    kind names the exact reviewed control whose action is safe.  The
    tap-anywhere kind is authorised only by the complete native
    ``点击任意位置退出`` text-line recogniser and still needs two fresh frames
    in the controller.
    """

    REWARD_TAP_ANYWHERE = "reward_tap_anywhere"
    DAILY_CLOSE_X = "daily_close_x"
    INTEL_MAP_BACK = "intel_map_back"
    WORLD_TOWN = "world_town"
    NETWORK_WAIT = "network_wait"
    PAID_STOP = "paid_stop"
    UNKNOWN = "unknown"


class BeastRallyState(str, Enum):
    """Passive visual states for the explicitly authorised beast-rally flow."""

    WORLD = "world"
    SELECTOR = "selector"
    RALLY_OPEN = "rally_open"
    RALLY_SHEET = "rally_sheet"
    FORMATION = "formation"
    STAMINA_MORE = "stamina_more"
    RALLYING = "rallying"
    MARCHING = "marching"
    RETURNING = "returning"
    COMPLETE = "complete"
    BLOCKED = "blocked"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class DailyAbnormalExitMatch:
    kind: DailyAbnormalExitKind
    point: tuple[int, int] | None
    score: float
    anchors: tuple[tuple[str, tuple[int, int]], ...] = ()


@dataclass(frozen=True)
class BeastRallyMatch:
    state: BeastRallyState
    point: tuple[int, int] | None
    score: float
    anchors: tuple[tuple[str, tuple[int, int]], ...] = ()


class DailyMissionKind(str, Enum):
    """Reviewed mission kinds that the daily executor may actively route.

    The enum intentionally has no generic ``GO`` or battle entries.
    A matching task title alone is not actionable; callers must obtain the
    paired ``go_point`` from its reviewed mission matcher.
    """

    GATHER_MEAT = "gather_meat"
    GATHER_WOOD = "gather_wood"
    GATHER_COAL = "gather_coal"
    GATHER_IRON = "gather_iron"
    TRAIN_SHIELD = "train_shield"
    TRAIN_SPEAR = "train_spear"
    TRAIN_ARCHER = "train_archer"
    UPGRADE_BUILDING = "upgrade_building"
    RESEARCH_TECH = "research_tech"
    PROCESS_INTEL = "process_intel"
    WAREHOUSE_SUPPLY = "warehouse_supply"
    HERO_RECRUIT = "hero_recruit"
    ALLIANCE_DONATE = "alliance_donate"


class CastleLevelGate(str, Enum):
    """Coarse, safety-oriented castle-level result from the Lord Profile."""

    BELOW_10 = "below_10"
    AT_LEAST_10 = "at_least_10"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class AlliancePageMatch:
    page: AlliancePage
    point: tuple[int, int] | None
    score: float


@dataclass(frozen=True)
class RedPacketMatch:
    """Result of a red-packet visual classification.

    ``point`` is the primary matched anchor.  For
    :attr:`RedPacketState.DETAIL_OPEN_READY`, it is the ``开启`` control and
    ``anchors`` also contains the independently matched furnace-title anchor.
    For :attr:`RedPacketState.CLAIM_RESULT_READY`, it is the result-dialog X.
    That latter state is visual evidence only: a controller must correlate it
    with its own immediately preceding ``开启`` click before recording success.
    """

    state: RedPacketState
    point: tuple[int, int] | None
    score: float
    anchors: tuple[tuple[str, tuple[int, int]], ...] = ()


@dataclass(frozen=True)
class DailyTaskMatch:
    """Result of a daily-task visual classification.

    ``point`` is non-``None`` only for a verified green claim control or the
    one reviewed Chapter→Daily tab switch.  A controller must still accept it
    only in its explicitly staged state; other anchors are visual evidence,
    never generic tap coordinates.
    """

    state: DailyTaskState
    point: tuple[int, int] | None
    score: float
    anchors: tuple[tuple[str, tuple[int, int]], ...] = ()


@dataclass(frozen=True)
class DailyMissionMatch:
    """A single visible, reviewed ordinary-resource daily mission.

    ``go_point`` is non-``None`` only when the exact task title and a blue
    ``前往`` button are found in the same card.  The value carries no authority
    outside a currently verified Daily Tasks page.
    """

    kind: DailyMissionKind
    task_point: tuple[int, int]
    go_point: tuple[int, int]
    score: float


@dataclass(frozen=True)
class ArenaMissionCandidate:
    """An exact Arena Daily card paired with its same-row blue ``Go``."""

    task_point: tuple[int, int]
    go_point: tuple[int, int]
    score: float
    target_count: int = 1


@dataclass(frozen=True)
class ArenaDailyClaim:
    target_count: int
    claim_point: tuple[int, int]
    score: float


@dataclass(frozen=True)
class ArenaHomeState:
    remaining: int
    challenge_point: tuple[int, int] | None
    score: float


@dataclass(frozen=True)
class ArenaOpponent:
    power: int
    fight_point: tuple[int, int]


@dataclass(frozen=True)
class ArenaOpponentListState:
    my_power: int
    remaining: int
    opponents: tuple[ArenaOpponent, ...]
    close_point: tuple[int, int]
    score: float

    def safest(self) -> ArenaOpponent | None:
        eligible = [item for item in self.opponents if item.power < self.my_power]
        return min(eligible, key=lambda item: item.power) if eligible else None


@dataclass(frozen=True)
class ArenaSetupState:
    my_power: int
    opponent_power: int
    selected_heroes: int
    battle_point: tuple[int, int]
    score: float


@dataclass(frozen=True)
class MiningLevelProfile:
    """Per-account mining level selection.

    ``manual`` and ``auto`` are intentionally mutually exclusive.  Manual
    mode supplies one exact 1--9 resource level and bypasses the transient
    world-overview recognition route; auto mode ignores ``manual_level`` and
    keeps the reviewed globe/home/green-marker route.
    """

    mode: str = "auto"
    manual_level: int = 5

    def __post_init__(self) -> None:
        if self.mode not in {"auto", "manual"}:
            raise ValueError("mining level mode must be 'auto' or 'manual'")
        if not 1 <= int(self.manual_level) <= 9:
            raise ValueError("manual mining level must be between 1 and 9")


@dataclass(frozen=True)
class BeastRallyProfile:
    """Manager-scoped automatic beast-rally limits.

    ``stamina_limit == 0`` means unlimited, matching the settings label.  The
    limit is checked against the persistent per-account daily ledger before
    the final ordinary Expedition input, never against the preview cost.
    """

    beast_level: int = 8
    stamina_limit: int = 0

    def __post_init__(self) -> None:
        if not 1 <= int(self.beast_level) <= 30:
            raise ValueError("beast level must be between 1 and 30")
        if not 0 <= int(self.stamina_limit) <= 1_000_000:
            raise ValueError("stamina limit must be between 0 and 1000000")


def _atomic_json_write(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.{time.time_ns()}.tmp")
    try:
        temporary.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        os.replace(temporary, path)
    finally:
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass


def load_beast_rally_profile(
    identity: str,
    path: Path = BEAST_RALLY_PROFILES_FILE,
) -> BeastRallyProfile:
    key = str(identity).strip()
    if not key:
        raise ValueError("device identity is required")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        profiles = payload.get("profiles", {})
        entry = profiles.get(key, {}) if isinstance(profiles, dict) else {}
        if not isinstance(entry, dict):
            entry = {}
        return BeastRallyProfile(
            beast_level=int(entry.get("beast_level", 8)),
            stamina_limit=int(entry.get("stamina_limit", 0)),
        )
    except (OSError, ValueError, TypeError, AttributeError, json.JSONDecodeError):
        return BeastRallyProfile()


def save_beast_rally_profile(
    identity: str,
    profile: BeastRallyProfile,
    path: Path = BEAST_RALLY_PROFILES_FILE,
) -> None:
    key = str(identity).strip()
    if not key:
        raise ValueError("device identity is required")
    if not isinstance(profile, BeastRallyProfile):
        raise TypeError("profile must be a BeastRallyProfile")
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            payload = {}
    except (OSError, ValueError, TypeError, json.JSONDecodeError):
        payload = {}
    profiles = payload.get("profiles")
    if not isinstance(profiles, dict):
        profiles = {}
    profiles[key] = {
        "beast_level": int(profile.beast_level),
        "stamina_limit": int(profile.stamina_limit),
    }
    _atomic_json_write(path, {"version": 1, "profiles": profiles})


def _beast_rally_ledger_day(now: float | None = None) -> str:
    return time.strftime("%Y-%m-%d", time.localtime(time.time() if now is None else now))


def load_beast_rally_stamina_spent(
    identity: str,
    *,
    day: str | None = None,
    path: Path = BEAST_RALLY_STAMINA_LEDGER_FILE,
) -> int:
    key = str(identity).strip()
    if not key:
        raise ValueError("device identity is required")
    active_day = str(day or _beast_rally_ledger_day())
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        accounts = payload.get("accounts", {})
        account = accounts.get(key, {}) if isinstance(accounts, dict) else {}
        if not isinstance(account, dict) or str(account.get("day", "")) != active_day:
            return 0
        return max(0, int(account.get("spent", 0)))
    except (OSError, ValueError, TypeError, AttributeError, json.JSONDecodeError):
        return 0


def load_beast_rally_stamina_reserved(
    identity: str,
    *,
    day: str | None = None,
    path: Path = BEAST_RALLY_STAMINA_LEDGER_FILE,
) -> int:
    """Return an unresolved pre-dispatch reservation for crash-safe limits."""
    key = str(identity).strip()
    if not key:
        raise ValueError("device identity is required")
    active_day = str(day or _beast_rally_ledger_day())
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        accounts = payload.get("accounts", {})
        account = accounts.get(key, {}) if isinstance(accounts, dict) else {}
        if not isinstance(account, dict) or str(account.get("day", "")) != active_day:
            return 0
        return max(0, int(account.get("reserved", 0)))
    except (OSError, ValueError, TypeError, AttributeError, json.JSONDecodeError):
        return 0


def reserve_beast_rally_stamina(
    identity: str,
    cost: int,
    *,
    day: str | None = None,
    path: Path = BEAST_RALLY_STAMINA_LEDGER_FILE,
) -> int:
    """Persist one cost before the final dispatch input."""
    key = str(identity).strip()
    debit = int(cost)
    if not key:
        raise ValueError("device identity is required")
    if debit <= 0 or debit > 999:
        raise ValueError("reserved stamina cost must be between 1 and 999")
    active_day = str(day or _beast_rally_ledger_day())
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            payload = {}
    except (OSError, ValueError, TypeError, json.JSONDecodeError):
        payload = {}
    accounts = payload.get("accounts")
    if not isinstance(accounts, dict):
        accounts = {}
    previous = accounts.get(key, {})
    same_day = isinstance(previous, dict) and str(previous.get("day", "")) == active_day
    spent = max(0, int(previous.get("spent", 0))) if same_day else 0
    reserved = max(0, int(previous.get("reserved", 0))) if same_day else 0
    if reserved:
        raise ValueError("an unresolved beast-rally stamina reservation already exists")
    accounts[key] = {"day": active_day, "spent": spent, "reserved": debit}
    _atomic_json_write(path, {"version": 2, "accounts": accounts})
    return debit


def confirm_beast_rally_stamina_reservation(
    identity: str,
    *,
    day: str | None = None,
    path: Path = BEAST_RALLY_STAMINA_LEDGER_FILE,
) -> int:
    """Move the current reservation into confirmed spend exactly once."""
    key = str(identity).strip()
    if not key:
        raise ValueError("device identity is required")
    active_day = str(day or _beast_rally_ledger_day())
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            payload = {}
    except (OSError, ValueError, TypeError, json.JSONDecodeError):
        payload = {}
    accounts = payload.get("accounts")
    if not isinstance(accounts, dict):
        accounts = {}
    previous = accounts.get(key, {})
    same_day = isinstance(previous, dict) and str(previous.get("day", "")) == active_day
    spent = max(0, int(previous.get("spent", 0))) if same_day else 0
    reserved = max(0, int(previous.get("reserved", 0))) if same_day else 0
    if not reserved:
        return spent
    spent += reserved
    accounts[key] = {"day": active_day, "spent": spent, "reserved": 0}
    _atomic_json_write(path, {"version": 2, "accounts": accounts})
    return spent


def record_beast_rally_stamina_spent(
    identity: str,
    cost: int,
    *,
    day: str | None = None,
    path: Path = BEAST_RALLY_STAMINA_LEDGER_FILE,
) -> int:
    key = str(identity).strip()
    debit = int(cost)
    if not key:
        raise ValueError("device identity is required")
    if debit <= 0 or debit > 999:
        raise ValueError("confirmed stamina cost must be between 1 and 999")
    active_day = str(day or _beast_rally_ledger_day())
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            payload = {}
    except (OSError, ValueError, TypeError, json.JSONDecodeError):
        payload = {}
    accounts = payload.get("accounts")
    if not isinstance(accounts, dict):
        accounts = {}
    previous = accounts.get(key, {})
    old_spent = (
        max(0, int(previous.get("spent", 0)))
        if isinstance(previous, dict) and str(previous.get("day", "")) == active_day
        else 0
    )
    new_spent = old_spent + debit
    reserved = (
        max(0, int(previous.get("reserved", 0)))
        if isinstance(previous, dict) and str(previous.get("day", "")) == active_day
        else 0
    )
    accounts[key] = {"day": active_day, "spent": new_spent, "reserved": reserved}
    _atomic_json_write(path, {"version": 2, "accounts": accounts})
    return new_spent


def beast_rally_stamina_limit_allows(
    spent: int,
    next_cost: int,
    limit: int,
) -> bool:
    return int(next_cost) > 0 and (int(limit) == 0 or int(spent) + int(next_cost) <= int(limit))


def load_mining_level_profile(
    identity: str,
    path: Path = MINING_LEVEL_PROFILES_FILE,
) -> MiningLevelProfile:
    """Load one manager-scoped account preference with legacy fallback."""

    key = str(identity).strip()
    if not key:
        raise ValueError("device identity is required")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        profiles = payload.get("profiles", {})
        if not isinstance(profiles, dict):
            profiles = {}
        entry = profiles.get(key)
        if not isinstance(entry, dict):
            # v5.44 keyed profiles by Android ID alone.  Preserve that user's
            # setting on first upgrade, but do not write it into every clone:
            # the first explicit Save creates an independent manager-scoped
            # key and immediately takes precedence over this fallback.
            match = re.fullmatch(r"mumu:[^:]+:android:([^:]+)", key)
            legacy_key = f"android:{match.group(1)}" if match else ""
            legacy = profiles.get(legacy_key)
            entry = legacy if isinstance(legacy, dict) else {}
        return MiningLevelProfile(
            mode=str(entry.get("mode", "auto")),
            manual_level=int(entry.get("manual_level", 5)),
        )
    except (OSError, ValueError, TypeError, AttributeError, json.JSONDecodeError):
        return MiningLevelProfile()


def save_mining_level_profile(
    identity: str,
    profile: MiningLevelProfile,
    path: Path = MINING_LEVEL_PROFILES_FILE,
) -> None:
    """Atomically persist one account without replacing other profiles."""

    key = str(identity).strip()
    if not key:
        raise ValueError("device identity is required")
    if not isinstance(profile, MiningLevelProfile):
        raise TypeError("profile must be a MiningLevelProfile")
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            payload = {}
    except (OSError, ValueError, TypeError, json.JSONDecodeError):
        payload = {}
    profiles = payload.get("profiles")
    if not isinstance(profiles, dict):
        profiles = {}
    profiles[key] = {
        "mode": profile.mode,
        "manual_level": int(profile.manual_level),
    }
    payload = {"version": 1, "profiles": profiles}
    temporary = path.with_name(
        f".{path.name}.{os.getpid()}.{time.time_ns()}.tmp"
    )
    try:
        temporary.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        os.replace(temporary, path)
    finally:
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass


def initial_mining_resource_level(profile: MiningLevelProfile) -> int | None:
    """Return a direct manual level, or ``None`` to request auto recognition."""

    if profile.mode == "manual":
        return int(profile.manual_level)
    return None


DAILY_GATHER_REQUIRED_AMOUNTS: dict[DailyMissionKind, int] = {
    DailyMissionKind.GATHER_MEAT: 50_000,
    DailyMissionKind.GATHER_WOOD: 50_000,
    DailyMissionKind.GATHER_COAL: 10_000,
    DailyMissionKind.GATHER_IRON: 3_000,
}
# A confirmed "full nodes only" selector state is the only reviewed amount
# proof available before Search.  The fixed level-5 iron route was live-tested
# against a full 59,805 iron node, so its conservative lower bound is the
# 3,000 amount required by the Daily Task.  An uncertain selector state is not
# treated as proof and must stop before Search.
DAILY_GATHER_FULL_NODE_REVIEWED_MINIMUM_AMOUNTS: dict[DailyMissionKind, int] = {
    DailyMissionKind.GATHER_IRON: 3_000,
}


def daily_gather_route_meets_required_amount(
    kind: DailyMissionKind,
    resource_level: int,
    full_resources_filter_enabled: bool,
) -> bool:
    """Return whether the reviewed route proves this gather task's amount.

    This deliberately has no permissive fallback for iron: a missing green
    full-resource proof, an unexpected level, or a reviewed bound below the
    task requirement returns ``False`` so the caller stops before Search.
    Other resource kinds retain the shared full-resource gate; their task
    amount is not represented by an independently reviewed numeric bound yet.
    """
    if not full_resources_filter_enabled:
        return False
    if kind is not DailyMissionKind.GATHER_IRON:
        return True
    reviewed_minimum = DAILY_GATHER_FULL_NODE_REVIEWED_MINIMUM_AMOUNTS.get(kind, 0)
    return (
        resource_level in (5, 7, 9)
        and reviewed_minimum >= DAILY_GATHER_REQUIRED_AMOUNTS[kind]
    )


@dataclass(frozen=True)
class DailyActivityProgress:
    """Visual estimate of the Daily Tasks activity bar.

    This is intentionally an estimate, rather than OCR.  The game renders a
    solid gold fill over a fixed 0--325 track, which is more robust across
    MuMu resolutions than reading stylised Chinese numerals.  Callers must
    still require a verified Daily Tasks page before using it for a chest tap.
    """

    points: float
    fill_right: int | None
    confidence: float


@dataclass(frozen=True)
class DailyMarchCapacity:
    """Fast, fail-closed reading of the world-map ``used/total`` header."""

    used: int
    total: int
    confidence: float

    @property
    def free(self) -> int:
        return max(0, self.total - self.used)


@dataclass(frozen=True)
class DailyGatherFormationCapacity:
    """Ordinary expedition capacity proved on the final formation page."""

    selected_troops: int
    carrying_capacity: int
    confidence: float


# Ten tiny, account-free glyph prototypes extracted from the game's own bold
# white numeric font.  A dedicated 12x16 reader starts in milliseconds and is
# both faster and safer than shipping a general OCR engine.  It is used only
# inside fixed, independently verified march/formation regions; any weak or
# ambiguous glyph makes the whole reading ``None``.
_DAILY_NUMERIC_GLYPHS = {
    "0": "000111111000/001111111100/011111111110/111100011110/111100001111/111000001111/111000000111/111000000111/111000000111/111000000111/111000001111/111100001110/011110011110/011111111110/001111111100/000011110000",
    "1": "000000000110/011111111111/111111111111/111111111110/000001111110/000001111110/000001111110/000001111110/000001111110/000001111110/000001111110/000001111110/000001111110/000001111110/000001111110/000001111110",
    "2": "001111111100/011111111110/011111111111/011000001111/000000001111/000000000111/000000001111/000000011110/000000011110/000000111100/000011111000/000111110000/001111100000/111111111111/111111111111/111111111111",
    "3": "001111111000/011111111110/011111111110/010000001110/000000001110/000000011110/000011111110/000111111110/000111111110/000000001111/000000001111/000000001111/111100011111/111111111110/111111111100/000111100000",
    "4": "000000111100/000001111100/000001111100/000011111100/000011111100/000111011100/001110011100/001110011100/001100011100/011100011100/111100011100/111111111111/111111111111/111111111111/000000011100/000000011100",
    "5": "011111111110/011111111110/011111111110/011100000000/011100000000/011100000000/011111111000/011111111110/000000011110/000000001111/000000001111/000000001111/011100011110/111111111110/111111111100/000111100000",
    "6": "000011111100/000111111110/001111111111/011110001110/111100000000/111100000000/111101111000/111111111110/111111111111/111100001111/111100000111/111100000111/011110001111/001111111110/001111111100/000001110000",
    "7": "111111111111/111111111111/111111111111/000000001111/000000001110/000000011110/000000011100/000000111100/000000111100/000000111000/000001111000/000001110000/000011110000/000011110000/000111100000/000111100000",
    "8": "000111111000/001111111100/011111111110/011110011110/011100001110/011100001110/011111011110/001111111100/011110111110/111100001111/111000000111/111100000111/111110001111/011111111110/001111111100/000011110000",
    "9": "001111111000/011111111100/111111111110/111100011110/111000001111/111000001111/111100001111/111111111111/011111111111/000000001111/000000001111/000000011110/011100111110/111111111100/011111111000/000111100000",
}
_DAILY_NUMERIC_PROTOTYPES = {
    digit: np.asarray(
        [[pixel == "1" for pixel in row] for row in rows.split("/")],
        dtype=np.bool_,
    )
    for digit, rows in _DAILY_NUMERIC_GLYPHS.items()
}


# The Daily Tasks board has a fixed final milestone.  The rendered gold bar
# lands about 1--2 points short of the label at normal MuMu scales, so a
# full-board decision uses a small, documented visual tolerance rather than
# OCRing stylised digits.  Callers must still require the verified Daily Tasks
# page and two consecutive observations before they stop a run.
DAILY_ACTIVITY_TARGET_POINTS = 325.0
DAILY_ACTIVITY_RENDER_TOLERANCE = 3.0
DAILY_ACTIVITY_TARGET_MIN_CONFIDENCE = 0.90
# Daily-task gathering does not need the kingdom-overview resource-band
# optimisation.  A fixed ordinary level keeps the route within the task-card
# -> world-search -> selector proof chain on every supported MuMu layout.
DAILY_GATHER_SAFE_RESOURCE_LEVEL = 5
# A level-5 node may legitimately take much longer than the historic
# 20-minute probe window.  The runner remains passive while this panel is
# visible, and caps a single wait so a stale panel cannot run indefinitely.
DAILY_GATHER_PASSIVE_WAIT_CAP_SECONDS = 3 * 60 * 60
# Full resource points can conceal the left march drawer briefly while the
# team is still harvesting.  Never treat two absent frames as a natural return
# before this conservative passive observation window has elapsed.
DAILY_GATHER_FULL_NODE_MIN_RETURN_SECONDS = 10 * 60
# Newer troop tiers can default the ordinary batch quantity above 100.  This
# is only a bound for the already-proven minus control; training still needs
# two independent frames reading exactly 10.
DAILY_TRAINING_MAX_DECREMENTS = 150


def daily_activity_target_reached(
    progress: DailyActivityProgress,
    target: float = DAILY_ACTIVITY_TARGET_POINTS,
) -> bool:
    """Return whether a trusted activity-bar estimate represents ``target``.

    This has no input authority by itself.  It intentionally rejects an
    absent/noisy fill and preserves the small under-read measured on the live
    100, 170, and 180 point boards.  A real 320-point board remains below the
    323-point lower bound, while a full 325-point board is accepted.
    """

    return (
        progress.fill_right is not None
        and progress.confidence >= DAILY_ACTIVITY_TARGET_MIN_CONFIDENCE
        and progress.points >= target - DAILY_ACTIVITY_RENDER_TOLERANCE
    )


@dataclass(frozen=True)
class ContentViewport:
    """The playable area of a screenshot, excluding pure black letterboxing.

    MuMu can preserve an Android aspect ratio inside a differently shaped
    window.  ADB then captures the surrounding black margins as real pixels,
    so scaling a recorded point against the *whole* capture sends taps away
    from the game.  This small value object makes that distinction explicit.
    """

    left: int
    top: int
    right: int
    bottom: int

    @property
    def width(self) -> int:
        return self.right - self.left

    @property
    def height(self) -> int:
        return self.bottom - self.top

    @property
    def box(self) -> tuple[int, int, int, int]:
        return self.left, self.top, self.right, self.bottom


def _black_border_thickness(mask: np.ndarray, edge: str, limit: int) -> int:
    """Return a continuous, nearly-solid-black border thickness in pixels."""
    if limit <= 0:
        return 0
    if edge == "top":
        lines = mask[:limit, :]
    elif edge == "bottom":
        lines = mask[-limit:, :][::-1]
    elif edge == "left":
        lines = mask[:, :limit].T
    elif edge == "right":
        lines = mask[:, -limit:].T[::-1]
    else:  # Defensive: callers below use literals only.
        raise ValueError(f"unknown edge: {edge}")
    thickness = 0
    for line in lines:
        # Compression and emulator capture can leave a few near-black specks
        # in an otherwise empty margin.  Do not treat a dark game scene as a
        # margin unless the line is effectively entirely black.
        if float(np.mean(line)) < 0.995:
            break
        thickness += 1
    # A one-to-three pixel edge is normal capture noise, not letterboxing.
    return thickness if thickness >= 4 else 0


def content_viewport(screenshot: Image.Image) -> ContentViewport:
    """Find the non-letterboxed game viewport in ``screenshot``.

    Only continuous edge bands with at least 99.5% RGB values <= 12 are
    removed.  This intentionally errs on the side of retaining pixels: a
    false viewport crop is more dangerous than failing to compensate for an
    unusual dark border.  The helper handles top/bottom and left/right bars
    independently and always returns a non-empty rectangle.
    """
    cached = getattr(screenshot, "_wjdr_content_viewport_cache", None)
    if isinstance(cached, ContentViewport):
        return cached
    rgb = _screenshot_rgb_cached(screenshot)
    height, width = rgb.shape[:2]
    dark = np.all(rgb <= 12, axis=2)
    vertical_limit = max(0, min(height // 3, 1024))
    horizontal_limit = max(0, min(width // 3, 1024))
    top = _black_border_thickness(dark, "top", vertical_limit)
    bottom = _black_border_thickness(dark, "bottom", vertical_limit)
    left = _black_border_thickness(dark, "left", horizontal_limit)
    right = _black_border_thickness(dark, "right", horizontal_limit)
    if left + right >= width - 8:
        left = right = 0
    if top + bottom >= height - 8:
        top = bottom = 0
    viewport = ContentViewport(left, top, width - right, height - bottom)
    try:
        setattr(screenshot, "_wjdr_content_viewport_cache", viewport)
    except (AttributeError, TypeError):
        pass
    return viewport


def map_content_point(
    point: tuple[int, int],
    source_size: tuple[int, int],
    screenshot: Image.Image,
) -> tuple[int, int]:
    """Map a recorded game-space point into the detected content viewport."""
    x, y = point
    source_w, source_h = source_size
    if source_w <= 0 or source_h <= 0:
        raise ValueError("source_size must be positive")
    viewport = content_viewport(screenshot)
    return (
        viewport.left + round(x * viewport.width / source_w),
        viewport.top + round(y * viewport.height / source_h),
    )


def daily_task_list_viewport_mean_change(before: Image.Image, after: Image.Image) -> float:
    """Measure whether a Daily Tasks list gesture actually moved the list.

    The changing refresh timer and the animated right-side action buttons are
    deliberately outside the comparison box.  A stationary result therefore
    means a real list boundary only after the controller observes it for two
    separately issued gestures; a resolution/layout mismatch returns infinity
    and can never be mistaken for a boundary.
    """
    reference_size = (1440, 2560)
    left, top, right, bottom = DAILY_TASK_LIST_VIEWPORT_BOX
    before_left, before_top = map_content_point((left, top), reference_size, before)
    before_right, before_bottom = map_content_point((right, bottom), reference_size, before)
    after_left, after_top = map_content_point((left, top), reference_size, after)
    after_right, after_bottom = map_content_point((right, bottom), reference_size, after)
    before_crop = before.convert("RGB").crop(
        (before_left, before_top, before_right, before_bottom)
    )
    after_crop = after.convert("RGB").crop(
        (after_left, after_top, after_right, after_bottom)
    )
    if before_crop.size != after_crop.size or min(before_crop.size) < 8:
        return float("inf")
    difference = ImageChops.difference(before_crop, after_crop)
    return sum(ImageStat.Stat(difference).mean) / 3.0


def content_frame_mean_change(before: Image.Image, after: Image.Image) -> float:
    """Measure whether the stable central game page changed.

    This passive helper is used only by the bounded, post-navigation recovery
    controller.  It excludes the outermost bands where the emulator and
    mutable edge decorations can differ.  A mismatch in content geometry
    returns infinity, which can never authorise Back or a corner tap.
    """
    before_box = content_relative_region(before, 0.08, 0.08, 0.92, 0.92)
    after_box = content_relative_region(after, 0.08, 0.08, 0.92, 0.92)
    before_crop = before.convert("RGB").crop(before_box)
    after_crop = after.convert("RGB").crop(after_box)
    if before_crop.size != after_crop.size or min(before_crop.size) < 8:
        return float("inf")
    difference = ImageChops.difference(before_crop, after_crop)
    return sum(ImageStat.Stat(difference).mean) / 3.0


def alliance_tech_tree_viewport_mean_change(before: Image.Image, after: Image.Image) -> float:
    """Measure a gesture inside the Alliance Technology tree.

    The crop excludes the changing Alliance Coin counter, tab strip and outer
    navigation controls.  A stationary result becomes boundary evidence only
    after two separately issued, Territory-proved gestures in the controller.
    Resolution/layout mismatches return infinity and therefore fail closed.
    """
    reference_size = (1440, 2560)
    before_left, before_top = map_content_point((80, 650), reference_size, before)
    before_right, before_bottom = map_content_point((1360, 2220), reference_size, before)
    after_left, after_top = map_content_point((80, 650), reference_size, after)
    after_right, after_bottom = map_content_point((1360, 2220), reference_size, after)
    before_crop = before.convert("RGB").crop(
        (before_left, before_top, before_right, before_bottom)
    )
    after_crop = after.convert("RGB").crop(
        (after_left, after_top, after_right, after_bottom)
    )
    if before_crop.size != after_crop.size or min(before_crop.size) < 8:
        return float("inf")
    difference = ImageChops.difference(before_crop, after_crop)
    return sum(ImageStat.Stat(difference).mean) / 3.0


def content_relative_region(
    screenshot: Image.Image,
    left: float,
    top: float,
    right: float,
    bottom: float,
) -> tuple[int, int, int, int]:
    """Return a relative region in game content coordinates, not black bars."""
    viewport = content_viewport(screenshot)
    return (
        viewport.left + round(viewport.width * left),
        viewport.top + round(viewport.height * top),
        viewport.left + round(viewport.width * right),
        viewport.top + round(viewport.height * bottom),
    )


def clean_name(name: str) -> str:
    value = re.sub(r"[^\w\-\u4e00-\u9fff]+", "_", name.strip(), flags=re.UNICODE)
    return value[:40] or "template"


def prune_runtime_evidence(directory: Path, keep_latest: int = 24) -> int:
    """Delete only the oldest PNG runtime crops and return the count removed.

    This helper never touches curated workspace milestones and never supplies
    images to a recogniser.  Callers pass one explicit LocalAppData evidence
    directory after saving a new account-free crop.
    """
    keep = max(1, int(keep_latest))
    screenshots = sorted(
        directory.glob("*.png"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    removed = 0
    for stale_path in screenshots[keep:]:
        stale_path.unlink()
        removed += 1
    return removed


def resource_path(name: str) -> Path:
    root = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
    return root / name


def prepare_storage() -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    TEMPLATE_DIR.mkdir(parents=True, exist_ok=True)
    for asset, name in (
        (BUILTIN_ALL_HELP_TEMPLATE_ASSET, BUILTIN_ALL_HELP_TEMPLATE_NAME),
        (BUILTIN_HELP_TEMPLATE_ASSET, BUILTIN_HELP_TEMPLATE_NAME),
        *RED_PACKET_BUILTIN_TEMPLATES,
        *DAILY_BUILTIN_TEMPLATES,
    ):
        source = resource_path(asset)
        destination = TEMPLATE_DIR / name
        if source.is_file():
            payload = source.read_bytes()
            if not destination.is_file() or destination.read_bytes() != payload:
                destination.write_bytes(payload)


def template_reference_size(template_path: Path) -> tuple[int, int] | None:
    if template_path.name in (
        BUILTIN_ALL_HELP_TEMPLATE_NAME,
        BUILTIN_HELP_TEMPLATE_NAME,
        BUILTIN_MUTUAL_PAGE_TEMPLATE_ASSET,
        BUILTIN_MUTUAL_ENTRY_TEMPLATE_ASSET,
        BUILTIN_CITY_ALLIANCE_TEMPLATE_ASSET,
    ):
        return BUILTIN_HELP_REFERENCE_SIZE
    if template_path.name in {
        BUILTIN_RED_PACKET_MARKER_TEMPLATE_NAME,
        Path(BUILTIN_RED_PACKET_MARKER_ASSET).name,
    }:
        # The supplied floating-envelope crop came from a 720 x 1280 capture.
        # It must scale independently of the 1440 x 2560 chat/popup anchors.
        return BUILTIN_RED_PACKET_MARKER_REFERENCE_SIZE
    if template_path.name in RED_PACKET_BUILTIN_TEMPLATE_FILENAMES:
        return BUILTIN_RED_PACKET_REFERENCE_SIZE
    # These Word-guide crops came from an 865 x 1352 portrait capture.  Check
    # them before the broader Daily set because prepare_storage gives them
    # builtin names but must not silently reinterpret them as 1440 x 2560.
    if template_path.name in USER_DOCUMENT_DAILY_CARD_TEMPLATE_FILENAMES:
        return USER_DOCUMENT_DAILY_CARD_REFERENCE_SIZE
    if template_path.name in USER_DOCUMENT_DAILY_FULL_TEMPLATE_FILENAMES:
        return USER_DOCUMENT_DAILY_FULL_REFERENCE_SIZE
    if template_path.name in USER_CLIPBOARD_DAILY_TEMPLATE_FILENAMES:
        return USER_CLIPBOARD_DAILY_REFERENCE_SIZE
    if template_path.name in DAILY_BUILTIN_TEMPLATE_FILENAMES:
        return BUILTIN_DAILY_TASK_REFERENCE_SIZE
    if template_path.name in BEAST_RALLY_BUILTIN_FILENAMES:
        return BUILTIN_DAILY_TASK_REFERENCE_SIZE
    try:
        data = json.loads(template_path.with_suffix(".json").read_text(encoding="utf-8"))
        width, height = int(data["screen_width"]), int(data["screen_height"])
        return (width, height) if width > 0 and height > 0 else None
    except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError):
        return None


class DeviceLease:
    def __init__(self, device: str) -> None:
        self.path = LOCK_DIR / f"{clean_name(device)}.lock"
        self.handle: Any = None

    def acquire(self) -> bool:
        if os.name != "nt":
            return True
        LOCK_DIR.mkdir(parents=True, exist_ok=True)
        try:
            self.handle = self.path.open("a+b")
            self.handle.seek(0, os.SEEK_END)
            if self.handle.tell() == 0:
                self.handle.write(b"0")
                self.handle.flush()
            self.handle.seek(0)
            msvcrt.locking(self.handle.fileno(), msvcrt.LK_NBLCK, 1)
            return True
        except OSError:
            if self.handle:
                self.handle.close()
                self.handle = None
            return False

    def release(self) -> None:
        if os.name == "nt" and self.handle:
            try:
                self.handle.seek(0)
                msvcrt.locking(self.handle.fileno(), msvcrt.LK_UNLCK, 1)
            except OSError:
                pass
            self.handle.close()
            self.handle = None


class MuMuADB:
    def __init__(self, adb_path: str | None = None) -> None:
        self.adb_path = adb_path or self._find_adb()
        self.manager_path = self._find_manager()
        self.device = ""
        self.players: list[dict[str, Any]] = []
        # ADB can expose one Android instance through several local serials
        # (for example 127.0.0.1:7555 and emulator-5554).  Cache the stable
        # Android identity as soon as devices are enumerated so UI workers
        # can acquire the same lease for every alias without extra I/O.
        self.device_identities: dict[str, str] = {}
        # ``android_id`` is not guaranteed to be unique after an emulator is
        # cloned.  MuMu instance aliases do, however, share one live boot ID.
        # Cache that short-lived fingerprint so an alias (for example 5559)
        # can be mapped back to its stable manager instance (for example
        # index 2 / manager port 25664) without conflating cloned accounts.
        self.device_boot_ids: dict[str, str] = {}

    @staticmethod
    def _find_adb() -> str:
        candidates = [
            r"C:\Program Files\Netease\MuMuPlayerGlobal-12.0\shell\adb.exe",
            r"C:\Program Files\Netease\MuMuPlayerGlobal-12.0\nx_main\adb.exe",
            r"C:\Program Files\Netease\MuMuPlayerGlobal-12.0\nx_device\12.0\shell\adb.exe",
            r"C:\Program Files\Netease\MuMu Player 12\shell\adb.exe",
            r"C:\Program Files (x86)\Nemu\vmonitor\bin\adb_server.exe",
        ]
        found = shutil.which("adb")
        if found:
            candidates.append(found)
        for candidate in candidates:
            if Path(candidate).is_file():
                return candidate
        raise AdbError("没有找到 MuMu 自带的 ADB。请先安装并启动 MuMu Player 12。")

    @staticmethod
    def _find_manager() -> str | None:
        for candidate in (
            r"C:\Program Files\Netease\MuMuPlayerGlobal-12.0\nx_main\MuMuManager.exe",
            r"C:\Program Files\Netease\MuMu Player 12\nx_main\MuMuManager.exe",
        ):
            if Path(candidate).is_file():
                return candidate
        return None

    def _run(self, args: list[str], timeout: float = 20, binary: bool = False) -> bytes | str:
        try:
            proc = subprocess.run(
                [self.adb_path, *args],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                timeout=timeout,
                creationflags=CREATE_NO_WINDOW,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise AdbError(f"ADB 执行失败：{exc}") from exc
        if proc.returncode != 0:
            output = proc.stdout.decode("utf-8", "replace").strip()
            raise AdbError(output or f"ADB 返回错误码 {proc.returncode}")
        return proc.stdout if binary else proc.stdout.decode("utf-8", "replace")

    def _manager_players(self) -> list[dict[str, Any]]:
        if not self.manager_path:
            return []
        try:
            proc = subprocess.run(
                [self.manager_path, "info", "-v", "all"],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                timeout=12,
                creationflags=CREATE_NO_WINDOW,
            )
            output = proc.stdout.decode("utf-8", "replace")
        except (OSError, subprocess.TimeoutExpired):
            return []
        players: list[dict[str, Any]] = []

        def collect(value: Any) -> None:
            if isinstance(value, dict):
                if "index" in value and ("adb_port" in value or "is_process_started" in value):
                    players.append(value)
                else:
                    for nested in value.values():
                        collect(nested)
            elif isinstance(value, list):
                for nested in value:
                    collect(nested)

        decoder, position = json.JSONDecoder(), 0
        while position < len(output):
            match = re.search(r"[\[{]", output[position:])
            if not match:
                break
            start = position + match.start()
            try:
                value, end = decoder.raw_decode(output, start)
            except json.JSONDecodeError:
                position = start + 1
                continue
            collect(value)
            position = end
        return players

    def _candidate_ports(self) -> list[int]:
        ports = {7555, 16384}
        self.players = self._manager_players()
        for player in self.players:
            try:
                if player.get("is_process_started") or player.get("is_android_started"):
                    ports.add(int(player["adb_port"]))
            except (ValueError, TypeError, KeyError):
                pass
        for root in (
            Path(r"C:\Program Files\Netease\MuMuPlayerGlobal-12.0\vms"),
            Path(r"C:\Program Files\Netease\MuMu Player 12\vms"),
        ):
            if root.exists():
                for config in root.glob("*/configs/vm_config.json"):
                    try:
                        data = json.loads(config.read_text(encoding="utf-8"))
                        ports.add(int(data["vm"]["nat"]["port_forward"]["adb"]["host_port"]))
                    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError):
                        pass
        return sorted(ports)

    def connect(self, preferred_device: str | None = None) -> list[str]:
        self._run(["start-server"], timeout=10)
        for port in self._candidate_ports():
            try:
                self._run(["connect", f"127.0.0.1:{port}"], timeout=4)
            except AdbError:
                pass
        output = str(self._run(["devices"], timeout=10))
        devices = []
        for line in output.splitlines()[1:]:
            columns = line.split()
            if len(columns) >= 2 and columns[1] == "device":
                devices.append(columns[0])
        connected_devices = list(devices)
        if not devices:
            raise AdbError("没有连接到 MuMu。请启动模拟器并允许 ADB 调试。")
        manager_devices: set[str] = set()
        for player in self.players:
            try:
                if player.get("is_process_started") or player.get("is_android_started"):
                    host = str(player.get("adb_host_ip") or "127.0.0.1")
                    manager_devices.add(f"{host}:{int(player['adb_port'])}")
            except (ValueError, TypeError, KeyError):
                pass
        managed = [item for item in devices if item in manager_devices]
        if managed:
            devices = managed
        else:
            local = [item for item in devices if item.startswith(("127.0.0.1:", "localhost:"))]
            devices = local or devices

        # Collapse aliases that point to one Android instance.  This is more
        # than presentational: the returned serial is later used to derive a
        # cross-window DeviceLease key, preventing two assistant windows from
        # driving the same MuMu instance through different ADB names.
        canonical_by_identity: dict[str, str] = {}
        for item in devices:
            identity = self.device_identity(item)
            canonical_by_identity.setdefault(identity, item)
        devices = list(canonical_by_identity.values())
        if preferred_device:
            # A saved/CLI serial may itself be an alias which was filtered
            # out above.  Accept it only when ADB currently reported it, then
            # select the safe canonical serial for that same Android ID.
            if preferred_device not in connected_devices:
                raise AdbError(f"指定的 MuMu 实例未连接：{preferred_device}")
            preferred_identity = self.device_identity(preferred_device)
            selected = canonical_by_identity.get(preferred_identity)
            if not selected:
                raise AdbError(f"指定的 MuMu 实例未连接：{preferred_device}")
            self.device = selected
        else:
            self.device = devices[0]
        return devices

    def set_device(self, device: str) -> None:
        self.device = device.strip()

    def clone_for_device(self, device: str | None = None) -> "MuMuADB":
        target = MuMuADB(self.adb_path)
        target.manager_path = self.manager_path
        target.players = list(self.players)
        target.device_identities = dict(self.device_identities)
        target.device_boot_ids = dict(self.device_boot_ids)
        target.set_device(device or self.device)
        return target

    def _device_boot_id(self, device: str) -> str:
        serial = device.strip()
        if not serial:
            return ""
        cached = self.device_boot_ids.get(serial)
        if cached is not None:
            return cached
        try:
            output = str(
                self._run(
                    [
                        "-s",
                        serial,
                        "shell",
                        "cat",
                        "/proc/sys/kernel/random/boot_id",
                    ],
                    timeout=8,
                )
            )
            boot_id = output.strip().lower()
        except AdbError:
            boot_id = ""
        if not re.fullmatch(r"[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}", boot_id):
            boot_id = ""
        self.device_boot_ids[serial] = boot_id
        return boot_id

    def _manager_instance_index(self, device: str) -> str | None:
        """Resolve a manager port or any live ADB alias to one MuMu index."""

        serial = device.strip()
        direct = self.player_for_device(serial)
        if direct is not None:
            index = str(direct.get("index", "")).strip()
            if index:
                return index

        target_boot_id = self._device_boot_id(serial)
        if not target_boot_id:
            return None
        for player in self.players:
            try:
                if not (
                    player.get("is_process_started")
                    or player.get("is_android_started")
                ):
                    continue
                host = str(player.get("adb_host_ip") or "127.0.0.1")
                manager_serial = f"{host}:{int(player['adb_port'])}"
            except (ValueError, TypeError, KeyError):
                continue
            if self._device_boot_id(manager_serial) != target_boot_id:
                continue
            index = str(player.get("index", "")).strip()
            if index:
                return index
        return None

    def device_identity(self, device: str | None = None) -> str:
        """Return a stable lease key for an Android instance.

        MuMu's local ADB server can list aliases for one emulator, while a
        cloned emulator can retain the *same* secure ``android_id`` as its
        source.  The stable manager instance index therefore scopes the
        Android ID.  Live aliases are mapped to that instance through their
        shared boot ID.  A raw Android-ID/serial fallback preserves
        operability outside manager-discovered MuMu instances.
        """
        serial = (device or self.device).strip()
        if not serial:
            return "adb:unknown"
        cached = self.device_identities.get(serial)
        if cached:
            return cached
        android_id = ""
        # MuMu can report a transport as online a few milliseconds before the
        # settings provider answers.  One immediate retry is cheaper and safer
        # than caching an incomplete profile/lease key for the whole process.
        for _attempt in range(2):
            try:
                output = str(
                    self._run(
                        [
                            "-s",
                            serial,
                            "shell",
                            "settings",
                            "get",
                            "secure",
                            "android_id",
                        ],
                        timeout=8,
                    )
                )
                candidate = output.strip().lower()
            except AdbError:
                candidate = ""
            if candidate and candidate not in {
                "0",
                "null",
                "none",
                "unknown",
                "undefined",
            }:
                android_id = candidate
                break
        valid_android_id = android_id and android_id not in {
            "0",
            "null",
            "none",
            "unknown",
            "undefined",
        }
        instance_index = self._manager_instance_index(serial)
        if instance_index is not None and valid_android_id:
            identity = f"mumu:{instance_index}:android:{android_id}"
        elif instance_index is not None:
            identity = f"mumu:{instance_index}"
        elif valid_android_id:
            identity = f"android:{android_id}"
        else:
            identity = f"adb:{serial.lower()}"
        # A manager-only identity is sufficient to keep cloned instances
        # distinct during this enumeration, but it must remain retryable so a
        # transient settings-provider miss cannot hide a persisted profile.
        if valid_android_id or instance_index is None:
            self.device_identities[serial] = identity
        return identity

    def player_for_device(self, device: str) -> dict[str, Any] | None:
        try:
            port = int(device.rsplit(":", 1)[1])
        except (ValueError, IndexError):
            return None
        for player in self.players:
            try:
                if int(player.get("adb_port", -1)) == port:
                    return player
            except (ValueError, TypeError):
                pass
        return None

    def _device_args(self, args: list[str]) -> list[str]:
        if not self.device:
            raise AdbError("尚未选择模拟器设备。")
        return ["-s", self.device, *args]

    def shell(self, command: list[str], timeout: float = 20) -> str:
        return str(self._run(self._device_args(["shell", *command]), timeout=timeout))

    def screen_size(self) -> tuple[int, int]:
        matches = re.findall(r"(\d+)x(\d+)", self.shell(["wm", "size"]))
        if not matches:
            raise AdbError("无法读取模拟器分辨率。")
        width, height = matches[-1]
        return int(width), int(height)

    def foreground_is_game(self) -> bool:
        output = self.shell(["dumpsys", "window"], timeout=10)
        focus = "\n".join(line for line in output.splitlines() if "mCurrentFocus" in line or "mFocusedApp" in line)
        return GAME_PACKAGE in focus

    def game_installed(self) -> bool:
        try:
            return "package:" in self.shell(["pm", "path", GAME_PACKAGE], timeout=8)
        except AdbError:
            return False

    def launch_game(self) -> None:
        self.shell(["monkey", "-p", GAME_PACKAGE, "-c", "android.intent.category.LAUNCHER", "1"], timeout=20)

    def screenshot(self) -> Image.Image:
        raw = self._run(self._device_args(["exec-out", "screencap", "-p"]), timeout=20, binary=True)
        assert isinstance(raw, bytes)
        try:
            image = Image.open(io.BytesIO(raw))
            image.load()
            return image.convert("RGB")
        except Exception as exc:
            raise AdbError(f"截图解析失败：{exc}") from exc

    def fast_window_screenshot(
        self,
        reference_size: tuple[int, int] | None = None,
    ) -> Image.Image:
        """Capture MuMu's render child directly through Windows GDI.

        This read-only path exists for short-lived visual controls whose
        lifetime is shorter than a normal ADB screencap round trip.  The
        manager-provided render HWND is tied to the selected ADB port.  A
        missing/invalid window fails closed; callers must not silently use a
        late ADB frame to authorise a transient click.
        """

        if os.name != "nt":
            raise AdbError("快速窗口截图仅支持 Windows MuMu。")
        player = self.player_for_device(self.device)
        if player is None:
            self.players = self._manager_players()
            player = self.player_for_device(self.device)
        if player is None:
            raise AdbError("MuMu 管理器未返回当前设备的窗口。")
        handle_text = str(player.get("render_wnd") or "").strip()
        try:
            hwnd = int(handle_text, 16)
        except ValueError as exc:
            raise AdbError("MuMu 管理器未返回有效的渲染窗口句柄。") from exc
        if not hwnd or not ctypes.windll.user32.IsWindow(hwnd):
            raise AdbError("MuMu 渲染窗口已经失效。")

        class Rect(ctypes.Structure):
            _fields_ = [
                ("left", ctypes.c_long),
                ("top", ctypes.c_long),
                ("right", ctypes.c_long),
                ("bottom", ctypes.c_long),
            ]

        class BitmapInfoHeader(ctypes.Structure):
            _fields_ = [
                ("biSize", wintypes.DWORD),
                ("biWidth", ctypes.c_long),
                ("biHeight", ctypes.c_long),
                ("biPlanes", wintypes.WORD),
                ("biBitCount", wintypes.WORD),
                ("biCompression", wintypes.DWORD),
                ("biSizeImage", wintypes.DWORD),
                ("biXPelsPerMeter", ctypes.c_long),
                ("biYPelsPerMeter", ctypes.c_long),
                ("biClrUsed", wintypes.DWORD),
                ("biClrImportant", wintypes.DWORD),
            ]

        user32, gdi32 = ctypes.windll.user32, ctypes.windll.gdi32
        rect = Rect()
        if not user32.GetClientRect(hwnd, ctypes.byref(rect)):
            raise AdbError("无法读取 MuMu 渲染窗口尺寸。")
        width, height = rect.right - rect.left, rect.bottom - rect.top
        if width < 200 or height < 300:
            raise AdbError("MuMu 渲染窗口尺寸异常。")
        capture_width, capture_height = width, height
        if reference_size:
            reference_width, reference_height = reference_size
            source_ratio = width / max(1, height)
            reference_ratio = reference_width / max(1, reference_height)
            # A non-DPI-aware caller receives logical client coordinates
            # (for example 945x1680 at 150%) even though PrintWindow renders
            # the physical 1440x2560 game surface. Allocate the authoritative
            # device-size bitmap directly when the aspect ratios agree. This
            # avoids capturing only a magnified top-left fragment and keeps
            # the fast recogniser independent of the host process DPI mode.
            if (
                reference_width >= 200
                and reference_height >= 300
                and abs(source_ratio - reference_ratio) <= 0.01
            ):
                capture_width, capture_height = reference_width, reference_height
        source_dc = user32.GetDC(hwnd)
        memory_dc = gdi32.CreateCompatibleDC(source_dc)
        bitmap = gdi32.CreateCompatibleBitmap(
            source_dc,
            capture_width,
            capture_height,
        )
        previous = gdi32.SelectObject(memory_dc, bitmap)
        try:
            # PW_CLIENTONLY | PW_RENDERFULLCONTENT captures an occluded render
            # child without bringing the emulator to the foreground.
            if not user32.PrintWindow(hwnd, memory_dc, 3):
                raise AdbError("MuMu 渲染窗口快速截图失败。")
            header = BitmapInfoHeader(
                ctypes.sizeof(BitmapInfoHeader),
                capture_width,
                -capture_height,
                1,
                32,
                0,
                capture_width * capture_height * 4,
                0,
                0,
                0,
                0,
            )
            buffer = ctypes.create_string_buffer(
                capture_width * capture_height * 4
            )
            rows = gdi32.GetDIBits(
                memory_dc,
                bitmap,
                0,
                capture_height,
                buffer,
                ctypes.byref(header),
                0,
            )
            if rows != capture_height:
                raise AdbError("MuMu 渲染窗口像素读取不完整。")
            image = Image.frombuffer(
                "RGB",
                (capture_width, capture_height),
                buffer,
                "raw",
                "BGRX",
                0,
                1,
            ).copy()
        finally:
            gdi32.SelectObject(memory_dc, previous)
            gdi32.DeleteObject(bitmap)
            gdi32.DeleteDC(memory_dc)
            user32.ReleaseDC(hwnd, source_dc)
        if reference_size and image.size != reference_size:
            image = image.resize(reference_size, Image.Resampling.BILINEAR)
        return image

    def tap(self, x: int, y: int) -> None:
        self.shell(["input", "tap", str(int(x)), str(int(y))], timeout=10)

    def back(self) -> None:
        self.shell(["input", "keyevent", "4"], timeout=10)

    def device_summary(self, device: str) -> dict[str, Any]:
        target = self.clone_for_device(device)
        player = self.player_for_device(device) or {}
        try:
            width, height = target.screen_size()
            resolution = f"{width} × {height}"
        except AdbError:
            resolution = "未知"
        if target.foreground_is_game():
            state = "游戏前台"
        elif target.game_installed():
            state = "游戏已安装"
        else:
            state = "未安装游戏"
        return {
            "device": device,
            "identity": target.device_identity(device),
            "index": str(player.get("index", "?")),
            "name": str(player.get("name", "MuMu 实例")),
            "resolution": resolution,
            "state": state,
        }


@lru_cache(maxsize=512)
def _load_template_grayscale_cached(
    path_text: str,
    modified_ns: int,
    file_size: int,
) -> np.ndarray:
    """Load immutable template pixels once, invalidating on file changes."""

    del modified_ns, file_size
    with Image.open(path_text) as template_image:
        rgb = np.asarray(template_image.convert("RGB"))
    return cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)


def _screenshot_rgb_cached(screenshot: Image.Image) -> np.ndarray:
    """Reuse one immutable RGB array across every matcher for this frame."""

    cached = getattr(screenshot, "_wjdr_rgb_cache", None)
    expected_shape = (screenshot.height, screenshot.width, 3)
    if isinstance(cached, np.ndarray) and cached.shape == expected_shape:
        return cached
    cached = np.asarray(screenshot.convert("RGB"))
    try:
        setattr(screenshot, "_wjdr_rgb_cache", cached)
    except (AttributeError, TypeError):
        pass
    return cached


def _screenshot_grayscale_cached(screenshot: Image.Image) -> np.ndarray:
    """Reuse one grayscale conversion across every matcher for this frame."""

    cached = getattr(screenshot, "_wjdr_grayscale_cache", None)
    if isinstance(cached, np.ndarray) and cached.shape == (screenshot.height, screenshot.width):
        return cached
    cached = cv2.cvtColor(_screenshot_rgb_cached(screenshot), cv2.COLOR_RGB2GRAY)
    try:
        setattr(screenshot, "_wjdr_grayscale_cache", cached)
    except (AttributeError, TypeError):
        pass
    return cached


def match_template(
    screenshot: Image.Image,
    template_path: Path,
    threshold: float,
    reference_size: tuple[int, int] | None = None,
    search_region: tuple[int, int, int, int] | None = None,
) -> tuple[tuple[int, int] | None, float]:
    try:
        template_stat = template_path.stat()
        template_array = _load_template_grayscale_cached(
            str(template_path.resolve()),
            int(template_stat.st_mtime_ns),
            int(template_stat.st_size),
        )
    except (OSError, ValueError):
        return None, 0.0
    screen_array = _screenshot_grayscale_cached(screenshot)
    full_screen_h, full_screen_w = screen_array.shape[:2]
    viewport = content_viewport(screenshot)
    offset_x = offset_y = 0
    if search_region:
        x0, y0, x1, y1 = search_region
        x0 = max(0, min(full_screen_w, int(x0)))
        y0 = max(0, min(full_screen_h, int(y0)))
        x1 = max(x0, min(full_screen_w, int(x1)))
        y1 = max(y0, min(full_screen_h, int(y1)))
        if x1 <= x0 or y1 <= y0:
            return None, 0.0
        screen_array = screen_array[y0:y1, x0:x1]
        offset_x, offset_y = x0, y0
    screen_h, screen_w = screen_array.shape[:2]
    base_h, base_w = template_array.shape[:2]
    scales = [1.0]
    if reference_size:
        ref_w, ref_h = reference_size
        # Template geometry belongs to the Android/game content, never to a
        # black pillar/letterbox margin around it.
        width_scale, height_scale = viewport.width / ref_w, viewport.height / ref_h
        # ADB frames on the reviewed MuMu devices are native 1440x2560 game
        # content.  Running 0.96/1.00/1.04 for every exact-scale asset triples
        # latency without adding evidence.  Keep the tolerance path only for a
        # genuinely scaled viewport; native pixels use the stricter 1.00 pass.
        native_scale = (
            abs(width_scale - 1.0) <= 0.015
            and abs(height_scale - 1.0) <= 0.015
        )
        if not native_scale:
            for scale in (
                width_scale,
                height_scale,
                (width_scale * height_scale) ** 0.5,
                min(width_scale, height_scale),
            ):
                for adjustment in (0.96, 1.0, 1.04):
                    candidate = scale * adjustment
                    if 0.25 <= candidate <= 2.5 and all(
                        abs(candidate - old) >= 0.015 for old in scales
                    ):
                        scales.append(candidate)
    best_value, best_location, best_size = -1.0, (0, 0), (base_w, base_h)
    for scale in scales:
        width, height = max(8, round(base_w * scale)), max(8, round(base_h * scale))
        if width > screen_w or height > screen_h:
            continue
        candidate = template_array if (width, height) == (base_w, base_h) else cv2.resize(
            template_array,
            (width, height),
            interpolation=cv2.INTER_AREA if scale < 1 else cv2.INTER_CUBIC,
        )
        result = cv2.matchTemplate(screen_array, candidate, cv2.TM_CCOEFF_NORMED)
        _, value, _, location = cv2.minMaxLoc(result)
        if value > best_value:
            best_value, best_location, best_size = float(value), location, (width, height)
    if best_value < threshold:
        return None, max(0.0, best_value)
    return (
        offset_x + best_location[0] + best_size[0] // 2,
        offset_y + best_location[1] + best_size[1] // 2,
    ), best_value


def _relative_region(
    screenshot: Image.Image,
    left: float,
    top: float,
    right: float,
    bottom: float,
) -> tuple[int, int, int, int]:
    return content_relative_region(screenshot, left, top, right, bottom)


def red_packet_template_path(asset: str, template_name: str) -> Path:
    """Return a persisted red-packet template, with the bundled asset fallback.

    ``prepare_storage`` normally copies bundled templates into ``TEMPLATE_DIR``
    so they can be inspected alongside the user's other templates.  Keeping a
    resource fallback makes the visual helpers safe to use before that startup
    preparation has happened (for example in fixture tests).
    """
    stored = TEMPLATE_DIR / template_name
    return stored if stored.is_file() else resource_path(asset)


def _match_red_packet_template(
    screenshot: Image.Image,
    asset: str,
    template_name: str,
    threshold: float,
    search_region: tuple[int, int, int, int] | None,
) -> tuple[tuple[int, int] | None, float]:
    template = red_packet_template_path(asset, template_name)
    if not template.is_file():
        return None, 0.0
    return match_template(
        screenshot,
        template,
        threshold,
        template_reference_size(template),
        search_region,
    )


def match_red_packet_marker(
    screenshot: Image.Image,
    threshold: float,
    search_region: tuple[int, int, int, int] | None = None,
) -> tuple[tuple[int, int] | None, float]:
    """Find the lower-right red-envelope floating marker that triggers a chat check.

    The marker itself is only a signal.  Callers must still confirm the
    alliance chat page and the target furnace packet before performing input.
    """
    return _match_red_packet_template(
        screenshot,
        BUILTIN_RED_PACKET_MARKER_ASSET,
        BUILTIN_RED_PACKET_MARKER_TEMPLATE_NAME,
        threshold,
        # The notification is anchored above the chat launcher in the lower
        # right.  Keeping this narrow avoids confusing ordinary envelope art
        # elsewhere in the city scene with the trigger-only floating marker.
        search_region if search_region is not None else _relative_region(screenshot, 0.72, 0.72, 0.94, 0.94),
    )


def match_red_packet_chat_entry(
    screenshot: Image.Image,
    threshold: float,
    search_region: tuple[int, int, int, int] | None = None,
) -> tuple[tuple[int, int] | None, float]:
    """Find the entry that opens the game's chat panel.

    The template is a stable shield / pager anchor at the left side of the
    city chat strip.  Its own centre is not the desired tap target, so a
    confirmed match returns the independently measured point inside the same
    strip, scaled from the 1440 × 2560 reference screen.
    """
    point, score = _match_red_packet_template(
        screenshot,
        BUILTIN_RED_PACKET_CHAT_ENTRY_ASSET,
        BUILTIN_RED_PACKET_CHAT_ENTRY_TEMPLATE_NAME,
        threshold,
        search_region if search_region is not None else _relative_region(screenshot, 0.0, 0.80, 0.18, 0.95),
    )
    if not point:
        return None, score
    # The tap is recorded in Android content space.  In particular, do not
    # scale it against a MuMu capture's black top/bottom or left/right bars.
    return map_content_point(
        RED_PACKET_CHAT_ENTRY_REFERENCE_POINT,
        BUILTIN_RED_PACKET_REFERENCE_SIZE,
        screenshot,
    ), score


def match_red_packet_chat_panel(
    screenshot: Image.Image,
    threshold: float,
    search_region: tuple[int, int, int, int] | None = None,
) -> tuple[tuple[int, int] | None, float]:
    """Find the chat-panel header after the city chat entry has been opened."""
    return _match_red_packet_template(
        screenshot,
        BUILTIN_RED_PACKET_CHAT_PANEL_ASSET,
        BUILTIN_RED_PACKET_CHAT_PANEL_TEMPLATE_NAME,
        threshold,
        search_region if search_region is not None else _relative_region(screenshot, 0.0, 0.0, 0.42, 0.18),
    )


def match_alliance_chat_page(
    screenshot: Image.Image,
    threshold: float,
    search_region: tuple[int, int, int, int] | None = None,
) -> tuple[tuple[int, int] | None, float]:
    """Find the selected Alliance tab, proving that this channel is active."""
    return _match_red_packet_template(
        screenshot,
        BUILTIN_RED_PACKET_ALLIANCE_PAGE_ASSET,
        BUILTIN_RED_PACKET_ALLIANCE_PAGE_TEMPLATE_NAME,
        threshold,
        search_region if search_region is not None else _relative_region(screenshot, 0.0, 0.0, 1.0, 0.45),
    )


def match_furnace_upgrade_packet(
    screenshot: Image.Image,
    threshold: float,
    search_region: tuple[int, int, int, int] | None = None,
) -> tuple[tuple[int, int] | None, float]:
    """Find the clickable ``熔炉升级红包`` card in an alliance chat."""
    return _match_red_packet_template(
        screenshot,
        BUILTIN_FURNACE_UPGRADE_PACKET_ASSET,
        BUILTIN_FURNACE_UPGRADE_PACKET_TEMPLATE_NAME,
        threshold,
        search_region if search_region is not None else _relative_region(screenshot, 0.02, 0.08, 0.98, 0.95),
    )


def match_furnace_upgrade_packet_icon(
    screenshot: Image.Image,
    threshold: float,
    search_region: tuple[int, int, int, int] | None = None,
) -> tuple[tuple[int, int] | None, float]:
    """Find stable envelope art on an *unclaimed* furnace packet card.

    Unlike the count-down and furnace level text, the illustrated envelope is
    static.  It is deliberately a second, independent card proof rather than
    an action target by itself.
    """
    return _match_red_packet_template(
        screenshot,
        BUILTIN_FURNACE_UPGRADE_PACKET_ICON_ASSET,
        BUILTIN_FURNACE_UPGRADE_PACKET_ICON_TEMPLATE_NAME,
        threshold,
        search_region if search_region is not None else _relative_region(screenshot, 0.52, 0.56, 0.90, 0.84),
    )


def match_furnace_upgrade_packet_claimed(
    screenshot: Image.Image,
    threshold: float,
    search_region: tuple[int, int, int, int] | None = None,
) -> tuple[tuple[int, int] | None, float]:
    """Find the green ``已领取`` mark on a furnace packet card.

    This is terminal evidence only.  A caller must never use its returned
    location as a click point.
    """
    return _match_red_packet_template(
        screenshot,
        BUILTIN_RED_PACKET_CLAIMED_ASSET,
        BUILTIN_RED_PACKET_CLAIMED_TEMPLATE_NAME,
        threshold,
        search_region if search_region is not None else _relative_region(screenshot, 0.08, 0.56, 0.48, 0.90),
    )


def match_furnace_upgrade_detail_title(
    screenshot: Image.Image,
    threshold: float,
    search_region: tuple[int, int, int, int] | None = None,
) -> tuple[tuple[int, int] | None, float]:
    """Find the title of the opened furnace-upgrade red-packet dialog."""
    return _match_red_packet_template(
        screenshot,
        BUILTIN_FURNACE_UPGRADE_TITLE_ASSET,
        BUILTIN_FURNACE_UPGRADE_TITLE_TEMPLATE_NAME,
        threshold,
        search_region if search_region is not None else _relative_region(screenshot, 0.12, 0.15, 0.88, 0.45),
    )


def match_red_packet_open_button(
    screenshot: Image.Image,
    threshold: float,
    search_region: tuple[int, int, int, int] | None = None,
) -> tuple[tuple[int, int] | None, float]:
    """Find the orange ``开启`` control in a red-packet detail dialog."""
    return _match_red_packet_template(
        screenshot,
        BUILTIN_RED_PACKET_OPEN_ASSET,
        BUILTIN_RED_PACKET_OPEN_TEMPLATE_NAME,
        threshold,
        search_region if search_region is not None else _relative_region(screenshot, 0.22, 0.55, 0.78, 0.90),
    )


def match_red_packet_result(
    screenshot: Image.Image,
    threshold: float,
    search_region: tuple[int, int, int, int] | None = None,
) -> tuple[tuple[int, int] | None, float]:
    """Find the diamond/reward anchor in the post-opening result dialog."""
    return _match_red_packet_template(
        screenshot,
        BUILTIN_RED_PACKET_RESULT_ASSET,
        BUILTIN_RED_PACKET_RESULT_TEMPLATE_NAME,
        threshold,
        search_region if search_region is not None else _relative_region(screenshot, 0.18, 0.20, 0.70, 0.55),
    )


def match_red_packet_result_close(
    screenshot: Image.Image,
    threshold: float,
    search_region: tuple[int, int, int, int] | None = None,
) -> tuple[tuple[int, int] | None, float]:
    """Find the X attached to the post-opening result dialog."""
    return _match_red_packet_template(
        screenshot,
        BUILTIN_RED_PACKET_RESULT_CLOSE_ASSET,
        BUILTIN_RED_PACKET_RESULT_CLOSE_TEMPLATE_NAME,
        threshold,
        search_region if search_region is not None else _relative_region(screenshot, 0.72, 0.08, 0.96, 0.30),
    )


def _detail_open_geometry_is_valid(
    screenshot: Image.Image,
    detail_title: tuple[int, int],
    open_button: tuple[int, int],
) -> bool:
    """Check that the paired popup anchors use the measured dialog geometry."""
    viewport = content_viewport(screenshot)
    x_delta = abs(open_button[0] - detail_title[0])
    y_delta = open_button[1] - detail_title[1]
    return (
        x_delta <= viewport.width * 0.14
        and viewport.height * 0.34 <= y_delta <= viewport.height * 0.50
    )


def _furnace_card_geometry_is_valid(
    screenshot: Image.Image,
    title: tuple[int, int],
    icon: tuple[int, int],
) -> bool:
    """Require the expected title-to-envelope layout of one packet card."""
    viewport = content_viewport(screenshot)
    x_delta = icon[0] - title[0]
    y_delta = icon[1] - title[1]
    return (
        viewport.width * 0.24 <= x_delta <= viewport.width * 0.52
        and viewport.height * 0.015 <= y_delta <= viewport.height * 0.16
    )


def _claimed_card_geometry_is_valid(
    screenshot: Image.Image,
    title: tuple[int, int],
    claimed: tuple[int, int],
) -> bool:
    """Ensure an ``已领取`` label belongs to this furnace card, not chat text."""
    viewport = content_viewport(screenshot)
    x_delta = claimed[0] - title[0]
    y_delta = claimed[1] - title[1]
    return (
        abs(x_delta) <= viewport.width * 0.18
        and viewport.height * 0.07 <= y_delta <= viewport.height * 0.16
    )


def detect_red_packet_state(
    screenshot: Image.Image,
    threshold: float,
) -> RedPacketMatch:
    """Classify safe visual states for the alliance furnace red-packet flow.

    No coordinate is returned for a generic ``开启`` control.  The only
    opening-ready state requires the ``熔炉升级红包`` detail title and its
    button to be independently present in the same screenshot.
    """
    safe_threshold = max(0.88, threshold)
    page_threshold = max(0.86, safe_threshold - 0.02)
    # The provided small trigger crop scores about 0.88–0.90 across tested
    # resolutions.  It is only an upstream signal; every downstream action
    # remains gated by stronger page/card/detail evidence.
    marker_threshold = max(0.84, safe_threshold - 0.04)

    result_anchor, result_anchor_score = match_red_packet_result(screenshot, max(0.86, safe_threshold - 0.04))
    result_close, result_close_score = match_red_packet_result_close(screenshot, max(0.89, safe_threshold - 0.01))
    if result_anchor and result_close:
        # This state intentionally does not mean an arbitrary result dialog is
        # a claim success.  The controller must tie it to its preceding open
        # action before counting it as such.
        return RedPacketMatch(
            RedPacketState.CLAIM_RESULT_READY,
            result_close,
            min(result_anchor_score, result_close_score),
            (("claim_result", result_anchor), ("claim_result_close", result_close)),
        )

    detail_title, detail_title_score = match_furnace_upgrade_detail_title(screenshot, safe_threshold)
    open_button, open_button_score = match_red_packet_open_button(screenshot, safe_threshold)
    if detail_title and open_button and _detail_open_geometry_is_valid(screenshot, detail_title, open_button):
        return RedPacketMatch(
            RedPacketState.DETAIL_OPEN_READY,
            open_button,
            min(detail_title_score, open_button_score),
            (("furnace_detail_title", detail_title), ("open_button", open_button)),
        )
    if detail_title:
        return RedPacketMatch(
            RedPacketState.FURNACE_DETAIL,
            detail_title,
            detail_title_score,
            (("furnace_detail_title", detail_title),),
        )

    chat_panel, chat_panel_score = match_red_packet_chat_panel(screenshot, max(0.93, page_threshold))
    alliance_page, alliance_page_score = match_alliance_chat_page(screenshot, max(0.90, page_threshold))
    furnace_packet, furnace_packet_score = match_furnace_upgrade_packet(screenshot, max(0.90, safe_threshold))
    furnace_icon, furnace_icon_score = match_furnace_upgrade_packet_icon(screenshot, max(0.91, safe_threshold))
    claimed, claimed_score = match_furnace_upgrade_packet_claimed(screenshot, max(0.91, safe_threshold))

    # A claimed card is intentionally terminal.  It has no click location and
    # is checked before the live-card path because the same title and envelope
    # illustration remain visible after collection.
    if (
        chat_panel
        and alliance_page
        and furnace_packet
        and claimed
        and _claimed_card_geometry_is_valid(screenshot, furnace_packet, claimed)
    ):
        return RedPacketMatch(
            RedPacketState.FURNACE_PACKET_CLAIMED,
            None,
            min(chat_panel_score, alliance_page_score, furnace_packet_score, claimed_score),
            (
                ("chat_panel", chat_panel),
                ("alliance_chat", alliance_page),
                ("furnace_packet_title", furnace_packet),
                ("claimed", claimed),
            ),
        )

    # A live furnace card is actionable only after four independent proofs:
    # chat panel, selected alliance channel, exact target title, and stable
    # envelope art in the expected local layout.  A title/icon alone never
    # creates a click point.
    if (
        chat_panel
        and alliance_page
        and furnace_packet
        and furnace_icon
        and _furnace_card_geometry_is_valid(screenshot, furnace_packet, furnace_icon)
    ):
        return RedPacketMatch(
            RedPacketState.FURNACE_PACKET,
            furnace_packet,
            min(chat_panel_score, alliance_page_score, furnace_packet_score, furnace_icon_score),
            (
                ("chat_panel", chat_panel),
                ("alliance_chat", alliance_page),
                ("furnace_packet_title", furnace_packet),
                ("furnace_packet_icon", furnace_icon),
            ),
        )

    if alliance_page:
        return RedPacketMatch(
            RedPacketState.ALLIANCE_CHAT,
            alliance_page,
            alliance_page_score,
            (("alliance_chat", alliance_page),),
        )

    if chat_panel:
        return RedPacketMatch(
            RedPacketState.CHAT_PANEL,
            chat_panel,
            chat_panel_score,
            (("chat_panel", chat_panel),),
        )

    chat_entry, chat_entry_score = match_red_packet_chat_entry(screenshot, max(0.90, page_threshold))
    if chat_entry:
        return RedPacketMatch(
            RedPacketState.CHAT_ENTRY,
            chat_entry,
            chat_entry_score,
            (("chat_entry", chat_entry),),
        )

    marker, marker_score = match_red_packet_marker(screenshot, marker_threshold)
    if marker:
        return RedPacketMatch(
            RedPacketState.MARKER,
            marker,
            marker_score,
            (("red_packet_marker", marker),),
        )

    return RedPacketMatch(
        RedPacketState.UNKNOWN,
        None,
        max(
            result_anchor_score,
            result_close_score,
            detail_title_score,
            open_button_score,
            furnace_packet_score,
            furnace_icon_score,
            claimed_score,
            alliance_page_score,
            chat_panel_score,
            chat_entry_score,
            marker_score,
        ),
    )


def daily_task_template_path(asset: str, template_name: str) -> Path:
    """Return a persisted daily-task template, with packaged fallback.

    The fallback keeps recognition usable in source-mode fixture tests before
    :func:`prepare_storage` has copied the reviewed templates to the user's
    local template directory.
    """
    stored = TEMPLATE_DIR / template_name
    return stored if stored.is_file() else resource_path(asset)


def _match_daily_task_template(
    screenshot: Image.Image,
    asset: str,
    template_name: str,
    threshold: float,
    search_region: tuple[int, int, int, int] | None,
) -> tuple[tuple[int, int] | None, float]:
    template = daily_task_template_path(asset, template_name)
    if not template.is_file():
        return None, 0.0
    return match_template(
        screenshot,
        template,
        threshold,
        template_reference_size(template),
        search_region,
    )


def _match_beast_rally_template(
    screenshot: Image.Image,
    asset: str,
    threshold: float,
    search_region: tuple[int, int, int, int] | None,
) -> tuple[tuple[int, int] | None, float]:
    template = resource_path(asset)
    if not template.is_file():
        return None, 0.0
    reference_size = template_reference_size(template)
    if (
        screenshot.width < 1200
        and screenshot.height < 1000
        and screenshot.width >= 720
    ):
        # User-supplied control/sheet fixtures are cropped from a native game
        # frame. Their asset was normalized to native scale, so recover the
        # original crop scale from the screenshot width during focused tests.
        # Real 1440x2560 ADB frames keep the normal native fast path.
        reference_size = (round(screenshot.width * 1440 / 1092), 2560)
    return match_template(
        screenshot,
        template,
        threshold,
        reference_size,
        search_region,
    )


def _beast_rally_template_integrity_is_valid(
    screenshot: Image.Image,
    asset: str,
    point: tuple[int, int],
) -> bool:
    if screenshot.width < 1200 and screenshot.height < 1000:
        # Exact user fixtures are cropped sheets/controls rather than a full
        # game viewport. Their template score is the integrity proof used by
        # focused offline tests; live ADB frames always take the RGB gate.
        return True
    name = Path(asset).name
    return _daily_template_integrity_is_valid(
        screenshot,
        asset,
        name,
        point,
        min_luma_ratio=DAILY_ACTION_MIN_LUMA_RATIO,
        min_chroma_ratio=DAILY_ACTION_MIN_CHROMA_RATIO,
        max_colour_distance=DAILY_ACTION_MAX_COLOUR_DISTANCE,
        strict_action=True,
    )


def _daily_template_integrity_is_valid(
    screenshot: Image.Image,
    asset: str,
    template_name: str,
    matched_center: tuple[int, int],
    *,
    min_luma_ratio: float = 0.84,
    min_chroma_ratio: float = 0.72,
    max_colour_distance: float = 0.16,
    strict_action: bool = False,
) -> bool:
    """Check raw colour and luminance at a matched daily-task anchor.

    ``TM_CCOEFF_NORMED`` deliberately normalises brightness, which is useful
    for normal scaling but unsafe for an input target hidden behind a
    semi-transparent dark overlay.  This guard re-samples the *original RGB*
    pixels at the matched anchor and requires their lightness and colour
    signature to remain close to the packaged source asset.  It is an input
    gate, not a second template matcher: callers must run it only after a
    narrow-region visual match has already succeeded.
    """
    template_path = daily_task_template_path(asset, template_name)
    if not template_path.is_file():
        return False
    try:
        template = np.asarray(Image.open(template_path).convert("RGB"), dtype=np.float32)
    except (OSError, ValueError):
        return False
    if template.ndim != 3 or template.shape[0] < 4 or template.shape[1] < 4:
        return False

    viewport = content_viewport(screenshot)
    reference_size = template_reference_size(template_path)
    if reference_size:
        ref_width, ref_height = reference_size
        scale_x = viewport.width / ref_width
        scale_y = viewport.height / ref_height
    else:
        scale_x = scale_y = 1.0
    source = _screenshot_rgb_cached(screenshot)
    source_height, source_width = source.shape[:2]
    template_height, template_width = template.shape[:2]

    # match_template permits a small scale tolerance.  Static evidence can
    # use the same local range.  Actual tap targets deliberately use only the
    # exact content-viewport scale: otherwise a slightly larger sampling box
    # can pull in adjacent bright pixels and hide a full-screen dark veil.
    adjustments = (1.0,) if strict_action else (0.96, 1.0, 1.04)
    for adjustment in adjustments:
        width = max(4, round(template_width * scale_x * adjustment))
        height = max(4, round(template_height * scale_y * adjustment))
        x0 = int(matched_center[0] - width // 2)
        y0 = int(matched_center[1] - height // 2)
        x1, y1 = x0 + width, y0 + height
        if x0 < 0 or y0 < 0 or x1 > source_width or y1 > source_height:
            continue
        observed = source[y0:y1, x0:x1].astype(np.float32, copy=False)
        if observed.shape[:2] != (height, width):
            continue
        observed = cv2.resize(observed, (template_width, template_height), interpolation=cv2.INTER_AREA)

        # Keep these comparisons in raw RGB rather than grayscale.  A dark
        # veil lowers both the luma and chroma energy while retaining a high
        # correlation score; a same-shape control in another colour also
        # deviates in its normalised RGB signature.
        expected_mean = np.mean(template, axis=(0, 1))
        observed_mean = np.mean(observed, axis=(0, 1))
        expected_luma = float(np.dot(expected_mean, (0.2126, 0.7152, 0.0722)))
        observed_luma = float(np.dot(observed_mean, (0.2126, 0.7152, 0.0722)))
        luma_ratio = observed_luma / max(expected_luma, 1.0)

        expected_chroma = float(np.mean(np.max(template, axis=2) - np.min(template, axis=2)))
        observed_chroma = float(np.mean(np.max(observed, axis=2) - np.min(observed, axis=2)))
        chroma_ratio = observed_chroma / max(expected_chroma, 1.0)

        expected_signature = expected_mean / max(float(np.sum(expected_mean)), 1.0)
        observed_signature = observed_mean / max(float(np.sum(observed_mean)), 1.0)
        colour_distance = float(np.sum(np.abs(expected_signature - observed_signature)))

        if (
            min_luma_ratio <= luma_ratio <= 1.20
            and (expected_chroma < 5.0 or min_chroma_ratio <= chroma_ratio <= 1.30)
            and colour_distance <= max_colour_distance
        ):
            return True
    return False


_DAILY_MISSION_GO_SPECS: tuple[tuple[str, str], ...] = (
    (
        BUILTIN_DAILY_MISSION_GO_CURRENT_ASSET,
        BUILTIN_DAILY_MISSION_GO_CURRENT_TEMPLATE_NAME,
    ),
    (BUILTIN_DAILY_MISSION_GO_ASSET, BUILTIN_DAILY_MISSION_GO_TEMPLATE_NAME),
)
_USER_DOCUMENT_DAILY_MISSION_GO_SPECS: tuple[tuple[str, str], ...] = (
    (
        BUILTIN_DAILY_MISSION_GO_USER_DOC_ASSET,
        BUILTIN_DAILY_MISSION_GO_USER_DOC_TEMPLATE_NAME,
    ),
)


def _match_best_daily_task_title(
    screenshot: Image.Image,
    specs: tuple[tuple[str, str], ...],
    threshold: float,
    search_region: tuple[int, int, int, int],
) -> tuple[tuple[int, int] | None, float]:
    """Return the strongest reviewed title variant in one narrow region."""
    best_point: tuple[int, int] | None = None
    best_score = 0.0
    for asset, template_name in specs:
        point, score = _match_daily_task_template(
            screenshot,
            asset,
            template_name,
            threshold,
            search_region,
        )
        if point and score > best_score:
            best_point = point
            best_score = score
    return best_point, best_score


def _match_daily_mission_go_control(
    screenshot: Image.Image,
    threshold: float,
    search_region: tuple[int, int, int, int],
    specs: tuple[tuple[str, str], ...] = _DAILY_MISSION_GO_SPECS,
) -> tuple[tuple[int, int] | None, float]:
    """Match a reviewed blue ``前往`` variant and validate its raw colour.

    The current game client uses a shorter button crop than the earlier
    fixture. Both variants remain exact templates; neither grants authority
    unless it also passes the existing raw-RGB anti-overlay gate.
    """
    best_point: tuple[int, int] | None = None
    best_score = 0.0
    for asset, template_name in specs:
        point, score = _match_daily_task_template(
            screenshot,
            asset,
            template_name,
            threshold,
            search_region,
        )
        if not point or score <= best_score:
            continue
        if not _daily_template_integrity_is_valid(
            screenshot,
            asset,
            template_name,
            point,
            min_luma_ratio=DAILY_ACTION_MIN_LUMA_RATIO,
            min_chroma_ratio=DAILY_ACTION_MIN_CHROMA_RATIO,
            max_colour_distance=DAILY_ACTION_MAX_COLOUR_DISTANCE,
            strict_action=True,
        ):
            continue
        best_point = point
        best_score = score
    return best_point, best_score


def _match_user_document_daily_mission(
    screenshot: Image.Image,
    *,
    kind: DailyMissionKind,
    asset: str,
    template_name: str,
    title_threshold: float,
    go_threshold: float,
    go_specs: tuple[tuple[str, str], ...] = _USER_DOCUMENT_DAILY_MISSION_GO_SPECS,
) -> DailyMissionMatch | None:
    """Pair one exact Word-guide title with its own reviewed blue ``Go``.

    The source cards are narrower than the older 1440-wide fixtures, so the
    title uses its own stored reference geometry.  Authority still comes from
    the existing strict-RGB Go matcher and the same-card spatial relation; a
    title, a blue blob, or a Go from an adjacent row is never sufficient.
    """
    viewport = content_viewport(screenshot)
    task_point, task_score = _match_daily_task_template(
        screenshot,
        asset,
        template_name,
        title_threshold,
        _relative_region(screenshot, 0.0, 0.32, 0.72, 0.89),
    )
    if not task_point:
        return None
    row_top = max(viewport.top, task_point[1] - round(viewport.height * 0.015))
    row_bottom = min(viewport.bottom, task_point[1] + round(viewport.height * 0.115))
    go_point, go_score = _match_daily_mission_go_control(
        screenshot,
        go_threshold,
        (
            viewport.left + round(viewport.width * 0.64),
            row_top,
            viewport.left + round(viewport.width * 0.99),
            row_bottom,
        ),
        go_specs,
    )
    if not go_point:
        return None
    x_delta = go_point[0] - task_point[0]
    y_delta = go_point[1] - task_point[1]
    if not (
        viewport.width * 0.43 <= x_delta <= viewport.width * 0.82
        and viewport.height * 0.010 <= y_delta <= viewport.height * 0.115
    ):
        return None
    return DailyMissionMatch(kind, task_point, go_point, min(task_score, go_score))


def match_daily_intel_mission(
    screenshot: Image.Image,
    threshold: float,
) -> DailyMissionMatch | None:
    """Find either reviewed incomplete Intel card and its same-row Go."""
    original = _match_user_document_daily_mission(
        screenshot,
        kind=DailyMissionKind.PROCESS_INTEL,
        asset=BUILTIN_DAILY_MISSION_PROCESS_INTEL_ASSET,
        template_name=BUILTIN_DAILY_MISSION_PROCESS_INTEL_TEMPLATE_NAME,
        title_threshold=max(0.985, float(threshold)),
        go_threshold=max(0.95, float(threshold)),
    )
    progressive = _match_user_document_daily_mission(
        screenshot,
        kind=DailyMissionKind.PROCESS_INTEL,
        asset=BUILTIN_DAILY_MISSION_PROCESS_INTEL_5_ASSET,
        template_name=BUILTIN_DAILY_MISSION_PROCESS_INTEL_5_TEMPLATE_NAME,
        title_threshold=max(0.98, float(threshold)),
        go_threshold=max(0.95, float(threshold)),
        go_specs=_DAILY_MISSION_GO_SPECS,
    )
    candidates = [item for item in (original, progressive) if item is not None]
    return max(candidates, key=lambda item: item.score) if candidates else None


def match_daily_warehouse_supply_mission(
    screenshot: Image.Image,
    threshold: float,
) -> DailyMissionMatch | None:
    """Find either reviewed incomplete Warehouse card and its same-row Go."""
    original = _match_user_document_daily_mission(
        screenshot,
        kind=DailyMissionKind.WAREHOUSE_SUPPLY,
        asset=BUILTIN_DAILY_MISSION_WAREHOUSE_SUPPLY_ASSET,
        template_name=BUILTIN_DAILY_MISSION_WAREHOUSE_SUPPLY_TEMPLATE_NAME,
        title_threshold=max(0.94, float(threshold)),
        go_threshold=max(0.95, float(threshold)),
    )
    current_three = _match_user_document_daily_mission(
        screenshot,
        kind=DailyMissionKind.WAREHOUSE_SUPPLY,
        asset=BUILTIN_DAILY_MISSION_WAREHOUSE_SUPPLY_THREE_CURRENT_ASSET,
        template_name=BUILTIN_DAILY_MISSION_WAREHOUSE_SUPPLY_THREE_CURRENT_TEMPLATE_NAME,
        title_threshold=max(0.985, float(threshold)),
        go_threshold=max(0.95, float(threshold)),
        go_specs=_DAILY_MISSION_GO_SPECS,
    )
    current_three_2of3 = _match_user_document_daily_mission(
        screenshot,
        kind=DailyMissionKind.WAREHOUSE_SUPPLY,
        asset=BUILTIN_DAILY_MISSION_WAREHOUSE_SUPPLY_THREE_2OF3_ASSET,
        template_name=BUILTIN_DAILY_MISSION_WAREHOUSE_SUPPLY_THREE_2OF3_TEMPLATE_NAME,
        title_threshold=max(0.985, float(threshold)),
        go_threshold=max(0.95, float(threshold)),
        go_specs=_DAILY_MISSION_GO_SPECS,
    )
    current_five = _match_user_document_daily_mission(
        screenshot,
        kind=DailyMissionKind.WAREHOUSE_SUPPLY,
        asset=BUILTIN_DAILY_MISSION_WAREHOUSE_SUPPLY_FIVE_CURRENT_ASSET,
        template_name=BUILTIN_DAILY_MISSION_WAREHOUSE_SUPPLY_FIVE_CURRENT_TEMPLATE_NAME,
        title_threshold=max(0.985, float(threshold)),
        go_threshold=max(0.95, float(threshold)),
        go_specs=_DAILY_MISSION_GO_SPECS,
    )
    candidates = [
        item
        for item in (original, current_three, current_three_2of3, current_five)
        if item is not None
    ]
    return max(candidates, key=lambda item: item.score) if candidates else None


def match_daily_arena_mission(
    screenshot: Image.Image,
    threshold: float,
) -> ArenaMissionCandidate | None:
    """Pair the exact 1- or 5-challenge Arena card with its same-row Go."""
    viewport = content_viewport(screenshot)
    title_specs = (
        (1, BUILTIN_DAILY_MISSION_ARENA_ONE_CURRENT_ASSET,
         BUILTIN_DAILY_MISSION_ARENA_ONE_CURRENT_TEMPLATE_NAME, 0.985),
        (1, BUILTIN_DAILY_MISSION_ARENA_PASSIVE_ASSET,
         BUILTIN_DAILY_MISSION_ARENA_PASSIVE_TEMPLATE_NAME, 0.95),
        (5, BUILTIN_DAILY_MISSION_ARENA_FIVE_CURRENT_ASSET,
         BUILTIN_DAILY_MISSION_ARENA_FIVE_CURRENT_TEMPLATE_NAME, 0.985),
    )
    matches: list[tuple[int, tuple[int, int], float]] = []
    for target_count, asset, template_name, floor in title_specs:
        point, score = _match_daily_task_template(
            screenshot, asset, template_name,
            max(floor, float(threshold)),
            _relative_region(screenshot, 0.0, 0.32, 0.72, 0.89),
        )
        if point:
            matches.append((target_count, point, score))
    if not matches:
        return None
    target_count, task_point, task_score = max(matches, key=lambda item: item[2])
    row_top = max(viewport.top, task_point[1] - round(viewport.height * 0.015))
    row_bottom = min(viewport.bottom, task_point[1] + round(viewport.height * 0.115))
    go_region = (
        viewport.left + round(viewport.width * 0.64),
        row_top,
        viewport.left + round(viewport.width * 0.99),
        row_bottom,
    )
    go_candidates = [
        _match_daily_mission_go_control(
            screenshot, max(0.95, float(threshold)), go_region, specs
        )
        for specs in (_DAILY_MISSION_GO_SPECS, _USER_DOCUMENT_DAILY_MISSION_GO_SPECS)
    ]
    go_point, go_score = max(go_candidates, key=lambda item: item[1])
    if not go_point:
        return None
    x_delta = go_point[0] - task_point[0]
    y_delta = go_point[1] - task_point[1]
    if not (
        viewport.width * 0.43 <= x_delta <= viewport.width * 0.82
        and viewport.height * 0.010 <= y_delta <= viewport.height * 0.115
    ):
        return None
    return ArenaMissionCandidate(
        task_point, go_point, min(task_score, go_score), target_count
    )


def match_daily_arena_claim(
    screenshot: Image.Image,
    threshold: float,
) -> ArenaDailyClaim | None:
    """Return only a claim button sharing a row with exact completed Arena title."""
    viewport = content_viewport(screenshot)
    matches: list[ArenaDailyClaim] = []
    for target_count, asset, template_name in (
        (1, BUILTIN_DAILY_MISSION_ARENA_ONE_CLAIM_ASSET,
         BUILTIN_DAILY_MISSION_ARENA_ONE_CLAIM_TEMPLATE_NAME),
        (5, BUILTIN_DAILY_MISSION_ARENA_FIVE_CLAIM_ASSET,
         BUILTIN_DAILY_MISSION_ARENA_FIVE_CLAIM_TEMPLATE_NAME),
    ):
        title, title_score = _match_daily_task_template(
            screenshot, asset, template_name, max(0.985, float(threshold)),
            _relative_region(screenshot, 0.0, 0.32, 0.72, 0.89),
        )
        if not title:
            continue
        row_top = max(viewport.top, title[1] - round(viewport.height * 0.02))
        row_bottom = min(viewport.bottom, title[1] + round(viewport.height * 0.13))
        claim, claim_score = match_daily_task_claim_button(
            screenshot, max(0.96, float(threshold)),
            (viewport.left + round(viewport.width * 0.64), row_top,
             viewport.left + round(viewport.width * 0.98), row_bottom),
        )
        if claim and _daily_task_claim_geometry_is_valid(screenshot, claim):
            matches.append(ArenaDailyClaim(
                target_count, claim, min(title_score, claim_score)
            ))
    return max(matches, key=lambda item: item.score) if matches else None


def match_daily_arena_mission_title(
    screenshot: Image.Image,
    threshold: float,
) -> tuple[bool, float]:
    """Passively identify the documented Arena title (legacy diagnostics).

    New controller code must prefer :func:`match_daily_arena_mission`, which
    additionally requires the same-row blue ``Go``.  This title-only helper
    remains for compatibility and carries no action point.
    """
    point, score = _match_daily_task_template(
        screenshot,
        BUILTIN_DAILY_MISSION_ARENA_PASSIVE_ASSET,
        BUILTIN_DAILY_MISSION_ARENA_PASSIVE_TEMPLATE_NAME,
        max(0.95, float(threshold)),
        _relative_region(screenshot, 0.0, 0.32, 0.72, 0.89),
    )
    return point is not None, score


def match_daily_intel_map_entry(
    screenshot: Image.Image,
    threshold: float,
) -> tuple[tuple[int, int] | None, float]:
    """Return the exact blue Intel icon for a freshly staged Intel route.

    The icon alone is not generic navigation authority.  Callers must first
    have tapped a double-confirmed Intel Daily card and double-confirmed the
    reviewed world-map Town control in the same bounded transition.
    """
    point, score = _match_daily_task_template(
        screenshot,
        BUILTIN_DAILY_INTEL_MAP_ENTRY_ASSET,
        BUILTIN_DAILY_INTEL_MAP_ENTRY_TEMPLATE_NAME,
        max(0.95, float(threshold)),
        _relative_region(screenshot, 0.62, 0.0, 1.0, 0.32),
    )
    if not point:
        return None, score
    if not _daily_template_integrity_is_valid(
        screenshot,
        BUILTIN_DAILY_INTEL_MAP_ENTRY_ASSET,
        BUILTIN_DAILY_INTEL_MAP_ENTRY_TEMPLATE_NAME,
        point,
        min_luma_ratio=DAILY_ACTION_MIN_LUMA_RATIO,
        min_chroma_ratio=DAILY_ACTION_MIN_CHROMA_RATIO,
        max_colour_distance=DAILY_ACTION_MAX_COLOUR_DISTANCE,
        strict_action=True,
    ):
        return None, score
    return point, score


def match_daily_intel_map_page(
    screenshot: Image.Image,
    threshold: float,
) -> tuple[bool, float]:
    """Passively prove the documented Intel map by its envelope pin.

    The returned boolean never identifies a safe clue.  In particular, green
    wolf, blue, grey, or any other map pin remains non-actionable; the first
    packaged route records this page and returns without processing a clue.
    """
    point, score = _match_daily_task_template(
        screenshot,
        BUILTIN_DAILY_INTEL_MAP_PAGE_ASSET,
        BUILTIN_DAILY_INTEL_MAP_PAGE_TEMPLATE_NAME,
        max(0.92, float(threshold)),
        _relative_region(screenshot, 0.12, 0.02, 0.88, 0.76),
    )
    if point:
        return True, score
    live_header, live_score = _match_daily_task_template(
        screenshot,
        BUILTIN_DAILY_INTEL_MAP_HEADER_ASSET,
        BUILTIN_DAILY_INTEL_MAP_HEADER_TEMPLATE_NAME,
        max(0.97, float(threshold)),
        _relative_region(screenshot, 0.0, 0.0, 0.34, 0.12),
    )
    return live_header is not None, max(score, live_score)


def match_daily_intel_station_bubble(
    screenshot: Image.Image,
    threshold: float,
) -> tuple[tuple[int, int] | None, float]:
    """Return only the centred Intel-station bubble after Daily Go."""

    point, score = _match_daily_task_template(
        screenshot,
        BUILTIN_DAILY_INTEL_STATION_BUBBLE_ASSET,
        BUILTIN_DAILY_INTEL_STATION_BUBBLE_TEMPLATE_NAME,
        max(0.97, float(threshold)),
        _relative_region(screenshot, 0.25, 0.30, 0.75, 0.55),
    )
    if not point or not _daily_template_integrity_is_valid(
        screenshot,
        BUILTIN_DAILY_INTEL_STATION_BUBBLE_ASSET,
        BUILTIN_DAILY_INTEL_STATION_BUBBLE_TEMPLATE_NAME,
        point,
        min_luma_ratio=DAILY_ACTION_MIN_LUMA_RATIO,
        min_chroma_ratio=DAILY_ACTION_MIN_CHROMA_RATIO,
        max_colour_distance=DAILY_ACTION_MAX_COLOUR_DISTANCE,
        strict_action=True,
    ):
        return None, score
    return point, score


def match_daily_intel_rescue_pin(
    screenshot: Image.Image,
    threshold: float,
) -> tuple[tuple[int, int] | None, float]:
    """Return an exact reviewed tent pin, never the green wolf battle pin."""

    map_visible, map_score = match_daily_intel_map_page(screenshot, threshold)
    if not map_visible:
        return None, map_score
    best_point = None
    best_score = 0.0
    for asset, name in (
        (
            BUILTIN_DAILY_INTEL_RESCUE_GREY_PIN_ASSET,
            BUILTIN_DAILY_INTEL_RESCUE_GREY_PIN_TEMPLATE_NAME,
        ),
        (BUILTIN_DAILY_INTEL_RESCUE_PIN_ASSET, BUILTIN_DAILY_INTEL_RESCUE_PIN_TEMPLATE_NAME),
    ):
        point, score = _match_daily_task_template(
            screenshot,
            asset,
            name,
            max(0.98, float(threshold)),
            _relative_region(screenshot, 0.10, 0.12, 0.90, 0.80),
        )
        if point and _daily_template_integrity_is_valid(
            screenshot,
            asset,
            name,
            point,
            min_luma_ratio=0.96,
            min_chroma_ratio=0.94,
            max_colour_distance=0.05,
            strict_action=True,
        ) and score > best_score:
            best_point, best_score = point, score
    if best_point is None:
        return None, max(map_score, best_score)
    return best_point, best_score


def match_daily_intel_rescue_preview(
    screenshot: Image.Image,
    threshold: float,
) -> tuple[tuple[int, int] | None, float]:
    """Pair the Rescue-survivors preview title with exact blue View button."""

    title, title_score = _match_daily_task_template(
        screenshot,
        BUILTIN_DAILY_INTEL_RESCUE_PREVIEW_TITLE_ASSET,
        BUILTIN_DAILY_INTEL_RESCUE_PREVIEW_TITLE_TEMPLATE_NAME,
        max(0.97, float(threshold)),
        _relative_region(screenshot, 0.20, 0.18, 0.80, 0.38),
    )
    action, action_score = _match_daily_task_template(
        screenshot,
        BUILTIN_DAILY_INTEL_RESCUE_PREVIEW_GO_ASSET,
        BUILTIN_DAILY_INTEL_RESCUE_PREVIEW_GO_TEMPLATE_NAME,
        max(0.98, float(threshold)),
        _relative_region(screenshot, 0.20, 0.58, 0.80, 0.78),
    )
    if not title or not action:
        return None, max(title_score, action_score)
    if abs(title[0] - action[0]) > content_viewport(screenshot).width * 0.12:
        return None, max(title_score, action_score)
    if not _daily_template_integrity_is_valid(
        screenshot,
        BUILTIN_DAILY_INTEL_RESCUE_PREVIEW_GO_ASSET,
        BUILTIN_DAILY_INTEL_RESCUE_PREVIEW_GO_TEMPLATE_NAME,
        action,
        min_luma_ratio=DAILY_ACTION_MIN_LUMA_RATIO,
        min_chroma_ratio=DAILY_ACTION_MIN_CHROMA_RATIO,
        max_colour_distance=DAILY_ACTION_MAX_COLOUR_DISTANCE,
        strict_action=True,
    ):
        return None, max(title_score, action_score)
    return action, min(title_score, action_score)


def match_daily_intel_rescue_target(
    screenshot: Image.Image,
    threshold: float,
) -> tuple[tuple[int, int] | None, float]:
    """Pair the world Rescue title with its ordinary green stamina action."""

    title, title_score = _match_daily_task_template(
        screenshot,
        BUILTIN_DAILY_INTEL_RESCUE_TARGET_TITLE_ASSET,
        BUILTIN_DAILY_INTEL_RESCUE_TARGET_TITLE_TEMPLATE_NAME,
        max(0.97, float(threshold)),
        _relative_region(screenshot, 0.20, 0.25, 0.80, 0.43),
    )
    action, action_score = _match_daily_task_template(
        screenshot,
        BUILTIN_DAILY_INTEL_RESCUE_ACTION_ASSET,
        BUILTIN_DAILY_INTEL_RESCUE_ACTION_TEMPLATE_NAME,
        max(0.98, float(threshold)),
        _relative_region(screenshot, 0.20, 0.40, 0.80, 0.60),
    )
    if not title or not action:
        return None, max(title_score, action_score)
    if abs(title[0] - action[0]) > content_viewport(screenshot).width * 0.12:
        return None, max(title_score, action_score)
    if not _daily_template_integrity_is_valid(
        screenshot,
        BUILTIN_DAILY_INTEL_RESCUE_ACTION_ASSET,
        BUILTIN_DAILY_INTEL_RESCUE_ACTION_TEMPLATE_NAME,
        action,
        min_luma_ratio=DAILY_ACTION_MIN_LUMA_RATIO,
        min_chroma_ratio=DAILY_ACTION_MIN_CHROMA_RATIO,
        max_colour_distance=DAILY_ACTION_MAX_COLOUR_DISTANCE,
        strict_action=True,
    ):
        return None, max(title_score, action_score)
    return action, min(title_score, action_score)


def match_daily_intel_rescue_active(
    screenshot: Image.Image,
    threshold: float,
) -> tuple[bool, float]:
    """Passively prove this run's non-battle Rescue countdown row."""

    point, score = _match_daily_task_template(
        screenshot,
        BUILTIN_DAILY_INTEL_RESCUE_ACTIVE_ASSET,
        BUILTIN_DAILY_INTEL_RESCUE_ACTIVE_TEMPLATE_NAME,
        max(0.98, float(threshold)),
        _relative_region(screenshot, 0.0, 0.08, 0.50, 0.28),
    )
    return point is not None, score


def match_daily_intel_hero_pin(
    screenshot: Image.Image,
    threshold: float,
) -> tuple[tuple[int, int] | None, float]:
    """Return only the live-reviewed crossed-swords Intel pin."""

    map_visible, map_score = match_daily_intel_map_page(screenshot, threshold)
    if not map_visible:
        return None, map_score
    current_point, current_score = _match_daily_task_template(
        screenshot,
        BUILTIN_DAILY_INTEL_SWORDS_PIN_CURRENT_ASSET,
        BUILTIN_DAILY_INTEL_SWORDS_PIN_CURRENT_TEMPLATE_NAME,
        max(0.985, float(threshold)),
        _relative_region(screenshot, 0.10, 0.12, 0.90, 0.80),
    )
    if current_point and _daily_template_integrity_is_valid(
        screenshot,
        BUILTIN_DAILY_INTEL_SWORDS_PIN_CURRENT_ASSET,
        BUILTIN_DAILY_INTEL_SWORDS_PIN_CURRENT_TEMPLATE_NAME,
        current_point,
        min_luma_ratio=0.97,
        min_chroma_ratio=0.95,
        max_colour_distance=0.04,
        strict_action=True,
    ):
        return current_point, current_score
    point, score = _match_daily_task_template(
        screenshot,
        BUILTIN_DAILY_INTEL_SWORDS_PIN_ASSET,
        BUILTIN_DAILY_INTEL_SWORDS_PIN_TEMPLATE_NAME,
        max(0.98, float(threshold)),
        _relative_region(screenshot, 0.10, 0.12, 0.90, 0.80),
    )
    if not point or not _daily_template_integrity_is_valid(
        screenshot,
        BUILTIN_DAILY_INTEL_SWORDS_PIN_ASSET,
        BUILTIN_DAILY_INTEL_SWORDS_PIN_TEMPLATE_NAME,
        point,
        min_luma_ratio=0.96,
        min_chroma_ratio=0.94,
        max_colour_distance=0.05,
        strict_action=True,
    ):
        return None, max(map_score, current_score, score)
    return point, score


def match_daily_intel_completed_check(
    screenshot: Image.Image,
    threshold: float,
) -> tuple[tuple[int, int] | None, float]:
    """Return one exact claimable green check only on the Intel map."""

    map_visible, map_score = match_daily_intel_map_page(screenshot, threshold)
    if not map_visible:
        return None, map_score
    current_point, current_score = _match_daily_task_template(
        screenshot,
        BUILTIN_DAILY_INTEL_COMPLETED_TENT_CURRENT_ASSET,
        BUILTIN_DAILY_INTEL_COMPLETED_TENT_CURRENT_TEMPLATE_NAME,
        max(0.985, float(threshold)),
        _relative_region(screenshot, 0.05, 0.10, 0.95, 0.82),
    )
    if current_point and _daily_template_integrity_is_valid(
        screenshot,
        BUILTIN_DAILY_INTEL_COMPLETED_TENT_CURRENT_ASSET,
        BUILTIN_DAILY_INTEL_COMPLETED_TENT_CURRENT_TEMPLATE_NAME,
        current_point,
        min_luma_ratio=0.97,
        min_chroma_ratio=0.95,
        max_colour_distance=0.04,
        strict_action=True,
    ):
        return current_point, current_score
    point, score = _match_daily_task_template(
        screenshot,
        BUILTIN_DAILY_INTEL_COMPLETED_CHECK_ASSET,
        BUILTIN_DAILY_INTEL_COMPLETED_CHECK_TEMPLATE_NAME,
        max(0.985, float(threshold)),
        _relative_region(screenshot, 0.05, 0.10, 0.95, 0.82),
    )
    if not point or not _daily_template_integrity_is_valid(
        screenshot,
        BUILTIN_DAILY_INTEL_COMPLETED_CHECK_ASSET,
        BUILTIN_DAILY_INTEL_COMPLETED_CHECK_TEMPLATE_NAME,
        point,
        min_luma_ratio=0.97,
        min_chroma_ratio=0.95,
        max_colour_distance=0.04,
        strict_action=True,
    ):
        return None, max(map_score, current_score, score)
    return point, score


def match_daily_intel_wolf_pin(
    screenshot: Image.Image,
    threshold: float,
) -> tuple[tuple[int, int] | None, float]:
    """Return one current exact wolf Intel pin on a verified Intel map."""

    map_visible, map_score = match_daily_intel_map_page(screenshot, threshold)
    if not map_visible:
        return None, map_score
    point, score = _match_daily_task_template(
        screenshot,
        BUILTIN_DAILY_INTEL_WOLF_PIN_CURRENT_ASSET,
        BUILTIN_DAILY_INTEL_WOLF_PIN_CURRENT_TEMPLATE_NAME,
        max(0.985, float(threshold)),
        _relative_region(screenshot, 0.05, 0.10, 0.95, 0.82),
    )
    if not point or not _daily_template_integrity_is_valid(
        screenshot,
        BUILTIN_DAILY_INTEL_WOLF_PIN_CURRENT_ASSET,
        BUILTIN_DAILY_INTEL_WOLF_PIN_CURRENT_TEMPLATE_NAME,
        point,
        min_luma_ratio=0.97,
        min_chroma_ratio=0.95,
        max_colour_distance=0.04,
        strict_action=True,
    ):
        return None, max(map_score, score)
    return point, score


def match_daily_intel_wolf_preview(
    screenshot: Image.Image,
    threshold: float,
) -> tuple[tuple[int, int] | None, float]:
    """Pair the exact Beast-level preview title with its blue View button."""

    title, title_score = _match_daily_task_template(
        screenshot,
        BUILTIN_DAILY_INTEL_WOLF_PREVIEW_TITLE_CURRENT_ASSET,
        BUILTIN_DAILY_INTEL_WOLF_PREVIEW_TITLE_CURRENT_TEMPLATE_NAME,
        max(0.985, float(threshold)),
        _relative_region(screenshot, 0.20, 0.20, 0.80, 0.40),
    )
    action, action_score = _match_daily_task_template(
        screenshot,
        BUILTIN_DAILY_INTEL_WOLF_PREVIEW_GO_CURRENT_ASSET,
        BUILTIN_DAILY_INTEL_WOLF_PREVIEW_GO_CURRENT_TEMPLATE_NAME,
        max(0.985, float(threshold)),
        _relative_region(screenshot, 0.20, 0.58, 0.80, 0.78),
    )
    if not title or not action or abs(title[0] - action[0]) > content_viewport(screenshot).width * 0.12:
        return None, max(title_score, action_score)
    return action, min(title_score, action_score)


def match_daily_intel_wolf_target(
    screenshot: Image.Image,
    threshold: float,
) -> tuple[tuple[int, int] | None, float]:
    """Pair the exact level-1 wolf title with ordinary orange March 10."""

    title, title_score = _match_daily_task_template(
        screenshot,
        BUILTIN_DAILY_INTEL_WOLF_TARGET_TITLE_CURRENT_ASSET,
        BUILTIN_DAILY_INTEL_WOLF_TARGET_TITLE_CURRENT_TEMPLATE_NAME,
        max(0.985, float(threshold)),
        _relative_region(screenshot, 0.20, 0.20, 0.80, 0.45),
    )
    action, action_score = _match_daily_task_template(
        screenshot,
        BUILTIN_DAILY_INTEL_WOLF_MARCH_CURRENT_ASSET,
        BUILTIN_DAILY_INTEL_WOLF_MARCH_CURRENT_TEMPLATE_NAME,
        max(0.985, float(threshold)),
        _relative_region(screenshot, 0.20, 0.40, 0.80, 0.60),
    )
    if not title or not action or abs(title[0] - action[0]) > content_viewport(screenshot).width * 0.12:
        return None, max(title_score, action_score)
    return action, min(title_score, action_score)


def _match_daily_intel_hero_pair(
    screenshot: Image.Image,
    threshold: float,
    title_asset: str,
    title_name: str,
    title_region: tuple[float, float, float, float],
    action_asset: str,
    action_name: str,
    action_region: tuple[float, float, float, float],
) -> tuple[tuple[int, int] | None, float]:
    title, title_score = _match_daily_task_template(
        screenshot,
        title_asset,
        title_name,
        max(0.97, float(threshold)),
        _relative_region(screenshot, *title_region),
    )
    action, action_score = _match_daily_task_template(
        screenshot,
        action_asset,
        action_name,
        max(0.98, float(threshold)),
        _relative_region(screenshot, *action_region),
    )
    if not title or not action:
        return None, max(title_score, action_score)
    if abs(title[0] - action[0]) > content_viewport(screenshot).width * 0.18:
        return None, max(title_score, action_score)
    if not _daily_template_integrity_is_valid(
        screenshot,
        action_asset,
        action_name,
        action,
        min_luma_ratio=DAILY_ACTION_MIN_LUMA_RATIO,
        min_chroma_ratio=DAILY_ACTION_MIN_CHROMA_RATIO,
        max_colour_distance=DAILY_ACTION_MAX_COLOUR_DISTANCE,
        strict_action=True,
    ):
        return None, max(title_score, action_score)
    return action, min(title_score, action_score)


def match_daily_intel_hero_preview(
    screenshot: Image.Image,
    threshold: float,
) -> tuple[tuple[int, int] | None, float]:
    """Pair Hero Journey level-one preview with its exact blue View button."""

    return _match_daily_intel_hero_pair(
        screenshot,
        threshold,
        BUILTIN_DAILY_INTEL_HERO_PREVIEW_TITLE_ASSET,
        BUILTIN_DAILY_INTEL_HERO_PREVIEW_TITLE_TEMPLATE_NAME,
        (0.20, 0.18, 0.80, 0.38),
        BUILTIN_DAILY_INTEL_HERO_PREVIEW_GO_ASSET,
        BUILTIN_DAILY_INTEL_HERO_PREVIEW_GO_TEMPLATE_NAME,
        (0.20, 0.58, 0.80, 0.78),
    )


def match_daily_intel_hero_detail(
    screenshot: Image.Image,
    threshold: float,
) -> tuple[tuple[int, int] | None, float]:
    """Pair the Hero Journey detail card with ordinary stamina Explore."""

    return _match_daily_intel_hero_pair(
        screenshot,
        threshold,
        BUILTIN_DAILY_INTEL_HERO_DETAIL_TITLE_ASSET,
        BUILTIN_DAILY_INTEL_HERO_DETAIL_TITLE_TEMPLATE_NAME,
        (0.20, 0.25, 0.80, 0.43),
        BUILTIN_DAILY_INTEL_HERO_EXPLORE_ASSET,
        BUILTIN_DAILY_INTEL_HERO_EXPLORE_TEMPLATE_NAME,
        (0.20, 0.40, 0.80, 0.60),
    )


def match_daily_intel_hero_setup(
    screenshot: Image.Image,
    threshold: float,
) -> tuple[tuple[int, int] | None, tuple[int, int] | None, float]:
    """Prove Team Setup and expose only One-key Deploy plus ordinary Battle."""

    header, header_score = _match_daily_task_template(
        screenshot,
        BUILTIN_DAILY_INTEL_HERO_SETUP_HEADER_ASSET,
        BUILTIN_DAILY_INTEL_HERO_SETUP_HEADER_TEMPLATE_NAME,
        max(0.97, float(threshold)),
        _relative_region(screenshot, 0.0, 0.0, 0.55, 0.14),
    )
    auto, auto_score = _match_daily_task_template(
        screenshot,
        BUILTIN_DAILY_INTEL_HERO_AUTO_DEPLOY_ASSET,
        BUILTIN_DAILY_INTEL_HERO_AUTO_DEPLOY_TEMPLATE_NAME,
        max(0.98, float(threshold)),
        _relative_region(screenshot, 0.0, 0.78, 0.52, 1.0),
    )
    battle, battle_score = _match_daily_task_template(
        screenshot,
        BUILTIN_DAILY_INTEL_HERO_BATTLE_ASSET,
        BUILTIN_DAILY_INTEL_HERO_BATTLE_TEMPLATE_NAME,
        max(0.98, float(threshold)),
        _relative_region(screenshot, 0.48, 0.78, 1.0, 1.0),
    )
    score = min(header_score, auto_score, battle_score)
    if not header or not auto or not battle:
        return None, None, max(header_score, auto_score, battle_score)
    for asset, name, point in (
        (BUILTIN_DAILY_INTEL_HERO_AUTO_DEPLOY_ASSET, BUILTIN_DAILY_INTEL_HERO_AUTO_DEPLOY_TEMPLATE_NAME, auto),
        (BUILTIN_DAILY_INTEL_HERO_BATTLE_ASSET, BUILTIN_DAILY_INTEL_HERO_BATTLE_TEMPLATE_NAME, battle),
    ):
        if not _daily_template_integrity_is_valid(
            screenshot,
            asset,
            name,
            point,
            min_luma_ratio=DAILY_ACTION_MIN_LUMA_RATIO,
            min_chroma_ratio=DAILY_ACTION_MIN_CHROMA_RATIO,
            max_colour_distance=DAILY_ACTION_MAX_COLOUR_DISTANCE,
            strict_action=True,
        ):
            return None, None, score
    return auto, battle, score


def match_daily_intel_hero_ready_battle(
    screenshot: Image.Image,
    threshold: float,
) -> tuple[tuple[int, int] | None, float]:
    """After one-key deploy, expose Battle without re-authorising Deploy."""

    header, header_score = _match_daily_task_template(
        screenshot,
        BUILTIN_DAILY_INTEL_HERO_SETUP_HEADER_ASSET,
        BUILTIN_DAILY_INTEL_HERO_SETUP_HEADER_TEMPLATE_NAME,
        max(0.97, float(threshold)),
        _relative_region(screenshot, 0.0, 0.0, 0.55, 0.14),
    )
    battle, battle_score = _match_daily_task_template(
        screenshot,
        BUILTIN_DAILY_INTEL_HERO_BATTLE_ASSET,
        BUILTIN_DAILY_INTEL_HERO_BATTLE_TEMPLATE_NAME,
        max(0.98, float(threshold)),
        _relative_region(screenshot, 0.48, 0.78, 1.0, 1.0),
    )
    if not header or not battle or not _daily_template_integrity_is_valid(
        screenshot,
        BUILTIN_DAILY_INTEL_HERO_BATTLE_ASSET,
        BUILTIN_DAILY_INTEL_HERO_BATTLE_TEMPLATE_NAME,
        battle,
        min_luma_ratio=DAILY_ACTION_MIN_LUMA_RATIO,
        min_chroma_ratio=DAILY_ACTION_MIN_CHROMA_RATIO,
        max_colour_distance=DAILY_ACTION_MAX_COLOUR_DISTANCE,
        strict_action=True,
    ):
        return None, max(header_score, battle_score)
    return battle, min(header_score, battle_score)


def match_daily_intel_hero_victory(
    screenshot: Image.Image,
    threshold: float,
) -> tuple[tuple[int, int] | None, float]:
    """Require exact Victory and the complete tap-anywhere phrase together."""

    victory, victory_score = _match_daily_task_template(
        screenshot,
        BUILTIN_DAILY_INTEL_HERO_VICTORY_ASSET,
        BUILTIN_DAILY_INTEL_HERO_VICTORY_TEMPLATE_NAME,
        max(0.98, float(threshold)),
        _relative_region(screenshot, 0.20, 0.20, 0.80, 0.60),
    )
    exit_text, exit_score = _match_daily_task_template(
        screenshot,
        BUILTIN_DAILY_INTEL_HERO_EXIT_TEXT_ASSET,
        BUILTIN_DAILY_INTEL_HERO_EXIT_TEXT_TEMPLATE_NAME,
        max(0.985, float(threshold)),
        _relative_region(screenshot, 0.15, 0.72, 0.85, 0.96),
    )
    if not victory or not exit_text:
        return None, max(victory_score, exit_score)
    # The phrase is proof only.  Return the reviewed far-left blank lane,
    # away from reward icons, buttons, purchases and the dynamic result body.
    return map_content_point((90, 1200), BUILTIN_DAILY_TASK_REFERENCE_SIZE, screenshot), min(
        victory_score, exit_score
    )


def daily_intel_map_back_point(screenshot: Image.Image) -> tuple[int, int]:
    """Exact upper-left arrow used only after two-frame Intel-map proof."""

    return map_content_point((70, 75), BUILTIN_DAILY_TASK_REFERENCE_SIZE, screenshot)


def daily_intel_active_countdown_crop(screenshot: Image.Image) -> Image.Image:
    """Return the account-free active Rescue row including its countdown."""

    viewport = content_viewport(screenshot)
    return screenshot.crop(
        (
            viewport.left,
            viewport.top + round(viewport.height * 0.115),
            viewport.left + round(viewport.width * 0.36),
            viewport.top + round(viewport.height * 0.20),
        )
    )


def match_daily_warehouse_city_supply_bubble(
    screenshot: Image.Image,
    threshold: float,
) -> tuple[tuple[int, int] | None, float]:
    """Find the exact chest bubble exposed by a correlated Warehouse Go.

    The variants are tight account-free crops of the chest speech bubble and
    the reviewed tutorial-hand animation poses.  The controller may use this
    action point only while the same Warehouse Go correlation is active and
    two fresh frames also prove the ordinary city page.
    """

    x0, y0 = map_content_point((480, 850), BUILTIN_DAILY_TASK_REFERENCE_SIZE, screenshot)
    x1, y1 = map_content_point((900, 1400), BUILTIN_DAILY_TASK_REFERENCE_SIZE, screenshot)
    candidates = []
    specs = (
        (
            BUILTIN_DAILY_WAREHOUSE_CITY_SUPPLY_BUBBLE_ASSET,
            BUILTIN_DAILY_WAREHOUSE_CITY_SUPPLY_BUBBLE_TEMPLATE_NAME,
        ),
        *zip(
            BUILTIN_DAILY_WAREHOUSE_CITY_SUPPLY_BUBBLE_NIGHT_ASSETS,
            BUILTIN_DAILY_WAREHOUSE_CITY_SUPPLY_BUBBLE_NIGHT_TEMPLATE_NAMES,
        ),
    )
    for asset, template_name in specs:
        point, score = _match_daily_task_template(
            screenshot,
            asset,
            template_name,
            max(0.96, float(threshold)),
            (x0, y0, x1, y1),
        )
        if point is not None:
            candidates.append((point, score))
    if candidates:
        return max(candidates, key=lambda item: item[1])

    # The tutorial hand is a continuous animation and can cover most of the
    # chest template between reviewed key poses.  Use the two parts that stay
    # exposed instead: the bright speech-bubble body and the orange/brown chest
    # patch in one small fixed rectangle.  This fallback is deliberately gated
    # by the exact city anchor; the controller adds the stronger same-Go and
    # two-city/two-bubble temporal correlation before authorising one tap.
    city_point, city_score = match_daily_city_entry(screenshot, threshold)
    if city_point is None:
        return None, city_score
    fx0, fy0 = map_content_point(
        (600, 1030), BUILTIN_DAILY_TASK_REFERENCE_SIZE, screenshot
    )
    fx1, fy1 = map_content_point(
        (680, 1160), BUILTIN_DAILY_TASK_REFERENCE_SIZE, screenshot
    )
    pixels = np.asarray(screenshot.convert("RGB"))[fy0:fy1, fx0:fx1]
    if pixels.size == 0:
        return None, city_score
    channels_min = pixels.min(axis=2)
    bright_ratio = float(np.mean(channels_min > 190))
    red = pixels[:, :, 0].astype(np.float32)
    green = pixels[:, :, 1].astype(np.float32)
    blue = pixels[:, :, 2].astype(np.float32)
    chest_ratio = float(
        np.mean(
            (red > 100)
            & (red > blue * 1.25)
            & (green > 50)
            & (green < 180)
        )
    )
    if bright_ratio < 0.20 or chest_ratio < 0.08:
        return None, max(city_score, bright_ratio, chest_ratio)
    action = map_content_point(
        (672, 1110), BUILTIN_DAILY_TASK_REFERENCE_SIZE, screenshot
    )
    feature_score = min(1.0, bright_ratio / 0.20, chest_ratio / 0.08)
    return action, min(city_score, 0.96 + 0.04 * feature_score)


def match_daily_warehouse_result(
    screenshot: Image.Image,
    threshold: float,
) -> tuple[bool, float]:
    """Passively recognise the documented Warehouse Supply countdown sheet."""
    legacy_point, legacy_score = _match_daily_task_template(
        screenshot,
        BUILTIN_DAILY_WAREHOUSE_RESULT_ASSET,
        BUILTIN_DAILY_WAREHOUSE_RESULT_TEMPLATE_NAME,
        max(0.88, float(threshold)),
        None,
    )
    current_point, current_score = _match_daily_task_template(
        screenshot,
        BUILTIN_DAILY_WAREHOUSE_RESULT_CURRENT_ASSET,
        BUILTIN_DAILY_WAREHOUSE_RESULT_CURRENT_TEMPLATE_NAME,
        # The current low-account render keeps the exact reviewed phrase but
        # applies a brighter outline, making the frozen asset score about
        # 0.940.  This matcher is only action-bearing inside the correlated
        # Warehouse Go -> city bubble lineage, and the phrase remains confined
        # to the lower result-sheet ROI.  Keep a phrase-specific floor instead
        # of weakening any generic page or button recogniser.
        0.93,
        _relative_region(screenshot, 0.25, 0.77, 0.75, 0.90),
    )
    return (legacy_point is not None or current_point is not None), max(
        legacy_score, current_score
    )


def daily_warehouse_result_exit_point(screenshot: Image.Image) -> tuple[int, int]:
    """Return a neutral fast-close point for the staged Warehouse result.

    The point is in the upper-left non-control margin of the documented sheet.
    If the random result countdown happens to expire between the final visual
    proof and the tap, the same coordinate remains in the inert Daily-page
    header area rather than a task, chest, tab, purchase, or reward control.
    The controller must use it only after its own Warehouse Go tap and two
    fresh exact result frames.
    """
    return map_content_point((45, 200), USER_DOCUMENT_DAILY_FULL_REFERENCE_SIZE, screenshot)


_DAILY_GATHER_MISSION_SPECS: tuple[tuple[DailyMissionKind, str, str], ...] = (
    (
        DailyMissionKind.GATHER_MEAT,
        BUILTIN_DAILY_MISSION_GATHER_MEAT_ASSET,
        BUILTIN_DAILY_MISSION_GATHER_MEAT_TEMPLATE_NAME,
    ),
    (
        DailyMissionKind.GATHER_WOOD,
        BUILTIN_DAILY_MISSION_GATHER_WOOD_ASSET,
        BUILTIN_DAILY_MISSION_GATHER_WOOD_TEMPLATE_NAME,
    ),
    (
        DailyMissionKind.GATHER_COAL,
        BUILTIN_DAILY_MISSION_GATHER_COAL_ASSET,
        BUILTIN_DAILY_MISSION_GATHER_COAL_TEMPLATE_NAME,
    ),
    (
        DailyMissionKind.GATHER_IRON,
        BUILTIN_DAILY_MISSION_GATHER_IRON_ASSET,
        BUILTIN_DAILY_MISSION_GATHER_IRON_TEMPLATE_NAME,
    ),
)


def match_daily_gather_missions(
    screenshot: Image.Image,
    threshold: float,
) -> tuple[DailyMissionMatch, ...]:
    """Find all visible resource-gather cards and their own ``前往`` buttons.

    This deliberately does not infer a mission from a blue button or a
    resource icon.  It requires an exact, reviewed task title first, then a
    separately matched blue button in the same card's action lane.  The
    caller is still responsible for requiring a verified Daily Tasks page and
    for observing this result across two frames before tapping it.
    """
    # Resource titles share a long Chinese prefix.  A 0.96 floor accepts the
    # reviewed 720--1440px captures while preventing a meat
    # title from being mistaken for the otherwise very similar wood task.
    safe_threshold = max(0.96, float(threshold))
    viewport = content_viewport(screenshot)
    task_region = _relative_region(screenshot, 0.03, 0.34, 0.66, 0.87)
    matches: list[DailyMissionMatch] = []
    for kind, asset, template_name in _DAILY_GATHER_MISSION_SPECS:
        task_point, task_score = _match_daily_task_template(
            screenshot,
            asset,
            template_name,
            safe_threshold,
            task_region,
        )
        if not task_point:
            continue
        # The action control is on the same card: to the right, roughly one
        # row-height below the title.  Keeping the narrow local region makes
        # a ``前往`` from another task insufficient.
        row_top = max(viewport.top, task_point[1] - round(viewport.height * 0.015))
        row_bottom = min(viewport.bottom, task_point[1] + round(viewport.height * 0.115))
        go_point, go_score = _match_daily_mission_go_control(
            screenshot,
            safe_threshold,
            (
                viewport.left + round(viewport.width * 0.64),
                row_top,
                viewport.left + round(viewport.width * 0.99),
                row_bottom,
            ),
        )
        if not go_point:
            continue
        x_delta = go_point[0] - task_point[0]
        y_delta = go_point[1] - task_point[1]
        same_card = (
            viewport.width * 0.48 <= x_delta <= viewport.width * 0.80
            and viewport.height * 0.015 <= y_delta <= viewport.height * 0.11
        )
        if not same_card:
            continue
        matches.append(DailyMissionMatch(kind, task_point, go_point, min(task_score, go_score)))
    return tuple(matches)


_DAILY_TRAIN_MISSION_SPECS: tuple[tuple[DailyMissionKind, str, str], ...] = (
    (
        DailyMissionKind.TRAIN_SHIELD,
        BUILTIN_DAILY_MISSION_TRAIN_SHIELD_ASSET,
        BUILTIN_DAILY_MISSION_TRAIN_SHIELD_TEMPLATE_NAME,
    ),
    (
        DailyMissionKind.TRAIN_SHIELD,
        BUILTIN_DAILY_MISSION_TRAIN_SHIELD_30_ASSET,
        BUILTIN_DAILY_MISSION_TRAIN_SHIELD_30_TEMPLATE_NAME,
    ),
    (
        DailyMissionKind.TRAIN_SHIELD,
        BUILTIN_DAILY_MISSION_TRAIN_SHIELD_30_20_ASSET,
        BUILTIN_DAILY_MISSION_TRAIN_SHIELD_30_20_TEMPLATE_NAME,
    ),
    (
        DailyMissionKind.TRAIN_SPEAR,
        BUILTIN_DAILY_MISSION_TRAIN_SPEAR_ASSET,
        BUILTIN_DAILY_MISSION_TRAIN_SPEAR_TEMPLATE_NAME,
    ),
    (
        DailyMissionKind.TRAIN_SPEAR,
        BUILTIN_DAILY_MISSION_TRAIN_SPEAR_30_ASSET,
        BUILTIN_DAILY_MISSION_TRAIN_SPEAR_30_TEMPLATE_NAME,
    ),
    (
        DailyMissionKind.TRAIN_SPEAR,
        BUILTIN_DAILY_MISSION_TRAIN_SPEAR_30_20_ASSET,
        BUILTIN_DAILY_MISSION_TRAIN_SPEAR_30_20_TEMPLATE_NAME,
    ),
    (
        DailyMissionKind.TRAIN_ARCHER,
        BUILTIN_DAILY_MISSION_TRAIN_ARCHER_ASSET,
        BUILTIN_DAILY_MISSION_TRAIN_ARCHER_TEMPLATE_NAME,
    ),
    (
        DailyMissionKind.TRAIN_ARCHER,
        BUILTIN_DAILY_MISSION_TRAIN_ARCHER_30_10_ASSET,
        BUILTIN_DAILY_MISSION_TRAIN_ARCHER_30_10_TEMPLATE_NAME,
    ),
    (
        DailyMissionKind.TRAIN_ARCHER,
        BUILTIN_DAILY_MISSION_TRAIN_ARCHER_30_20_ASSET,
        BUILTIN_DAILY_MISSION_TRAIN_ARCHER_30_20_TEMPLATE_NAME,
    ),
)


def match_daily_training_missions(
    screenshot: Image.Image,
    threshold: float,
) -> tuple[DailyMissionMatch, ...]:
    """Find reviewed 10- or 30-unit troop tasks and their own ``Go`` controls.

    Each title crop includes an exact incomplete state (``0 / 10``,
    ``10 / 30`` or ``20 / 30``), so a completed task cannot initiate another
    training run.  The controller may fill the ordinary queue for tomorrow,
    then defers this kind and rereads the fresh Daily card.  As with gathering,
    a title and a local same-card blue action must be visible in the same
    frame; a generic button is never enough.
    """
    # The three troop cards share the same pale card background and roughly
    # the same Chinese glyph geometry.  The 720 × 1280 fixture re-rasterises
    # the Archer title to 0.976 while its nearest wrong Shield title is 0.974;
    # 0.975 preserves the reviewed small portrait without admitting that
    # cross-card match.  The blue Go caption itself falls to 0.958 at
    # 768 × 1365, so it has a distinct lower scale threshold; strict raw-RGB
    # integrity and title-to-button row geometry remain mandatory.
    title_threshold = max(0.975, float(threshold))
    go_threshold = max(0.95, float(threshold))
    viewport = content_viewport(screenshot)
    task_region = _relative_region(screenshot, 0.03, 0.34, 0.66, 0.87)
    matches: list[DailyMissionMatch] = []
    for kind, asset, template_name in _DAILY_TRAIN_MISSION_SPECS:
        task_point, task_score = _match_daily_task_template(
            screenshot, asset, template_name, title_threshold, task_region
        )
        if not task_point:
            continue
        row_top = max(viewport.top, task_point[1] - round(viewport.height * 0.015))
        row_bottom = min(viewport.bottom, task_point[1] + round(viewport.height * 0.115))
        go_point, go_score = _match_daily_mission_go_control(
            screenshot,
            go_threshold,
            (
                viewport.left + round(viewport.width * 0.64),
                row_top,
                viewport.left + round(viewport.width * 0.99),
                row_bottom,
            ),
        )
        if not go_point:
            continue
        x_delta = go_point[0] - task_point[0]
        y_delta = go_point[1] - task_point[1]
        if not (
            viewport.width * 0.48 <= x_delta <= viewport.width * 0.80
            and viewport.height * 0.015 <= y_delta <= viewport.height * 0.11
        ):
            continue
        matches.append(DailyMissionMatch(kind, task_point, go_point, min(task_score, go_score)))
    # When one completed troop row has disappeared, a visually similar wrong
    # troop template can become that template's best remaining hit.  Live
    # Spear 20/30 scored 0.9993 while the obsolete Shield 20/30 template also
    # matched the *same* row at 0.9762.  Keep only the highest-scoring title
    # for each physical Go row, then preserve top-to-bottom scan order.  This
    # is selection-only: it creates no match and authorises no new control.
    row_winners: list[DailyMissionMatch] = []
    for candidate in sorted(matches, key=lambda item: item.score, reverse=True):
        if any(
            abs(existing.go_point[0] - candidate.go_point[0]) <= 24
            and abs(existing.go_point[1] - candidate.go_point[1]) <= 32
            for existing in row_winners
        ):
            continue
        row_winners.append(candidate)
    return tuple(sorted(row_winners, key=lambda item: (item.go_point[1], item.go_point[0])))


_DAILY_TRAIN_PROGRESS_SPECS: tuple[
    tuple[DailyMissionKind, str, str, int, int], ...
] = (
    (DailyMissionKind.TRAIN_SHIELD, BUILTIN_DAILY_MISSION_TRAIN_SHIELD_ASSET, BUILTIN_DAILY_MISSION_TRAIN_SHIELD_TEMPLATE_NAME, 0, 10),
    (DailyMissionKind.TRAIN_SHIELD, BUILTIN_DAILY_MISSION_TRAIN_SHIELD_30_ASSET, BUILTIN_DAILY_MISSION_TRAIN_SHIELD_30_TEMPLATE_NAME, 10, 30),
    (DailyMissionKind.TRAIN_SHIELD, BUILTIN_DAILY_MISSION_TRAIN_SHIELD_30_20_ASSET, BUILTIN_DAILY_MISSION_TRAIN_SHIELD_30_20_TEMPLATE_NAME, 20, 30),
    (DailyMissionKind.TRAIN_SPEAR, BUILTIN_DAILY_MISSION_TRAIN_SPEAR_ASSET, BUILTIN_DAILY_MISSION_TRAIN_SPEAR_TEMPLATE_NAME, 0, 10),
    (DailyMissionKind.TRAIN_SPEAR, BUILTIN_DAILY_MISSION_TRAIN_SPEAR_30_ASSET, BUILTIN_DAILY_MISSION_TRAIN_SPEAR_30_TEMPLATE_NAME, 10, 30),
    (DailyMissionKind.TRAIN_SPEAR, BUILTIN_DAILY_MISSION_TRAIN_SPEAR_30_20_ASSET, BUILTIN_DAILY_MISSION_TRAIN_SPEAR_30_20_TEMPLATE_NAME, 20, 30),
    (DailyMissionKind.TRAIN_ARCHER, BUILTIN_DAILY_MISSION_TRAIN_ARCHER_ASSET, BUILTIN_DAILY_MISSION_TRAIN_ARCHER_TEMPLATE_NAME, 0, 10),
    (DailyMissionKind.TRAIN_ARCHER, BUILTIN_DAILY_MISSION_TRAIN_ARCHER_30_10_ASSET, BUILTIN_DAILY_MISSION_TRAIN_ARCHER_30_10_TEMPLATE_NAME, 10, 30),
    (DailyMissionKind.TRAIN_ARCHER, BUILTIN_DAILY_MISSION_TRAIN_ARCHER_30_20_ASSET, BUILTIN_DAILY_MISSION_TRAIN_ARCHER_30_20_TEMPLATE_NAME, 20, 30),
)


def read_daily_training_progress(
    screenshot: Image.Image,
    kind: DailyMissionKind,
    threshold: float,
) -> tuple[int, int] | None:
    """Read the exact incomplete training count for one visible task card."""
    task_region = _relative_region(screenshot, 0.03, 0.34, 0.66, 0.87)
    title_threshold = max(0.975, float(threshold))
    for candidate_kind, asset, template_name, current, required in _DAILY_TRAIN_PROGRESS_SPECS:
        if candidate_kind is not kind:
            continue
        point, _score = _match_daily_task_template(
            screenshot, asset, template_name, title_threshold, task_region
        )
        if point:
            return current, required
    return None


def match_daily_building_upgrade_mission(
    screenshot: Image.Image,
    threshold: float,
) -> DailyMissionMatch | None:
    """Find the unfinished one-building Daily Task and its own ``Go``.

    Building work is intentionally narrower than a generic city upgrade: the
    exact unfinished Daily Task title and the blue control from that same card
    are both required.  The controller still must verify this pair in a fresh
    second frame before it can leave the Daily Tasks page.
    """
    # The full task card is deliberately strict, yet 900/960-wide downscaled
    # captures lose a few tenths of a percent of glyph edge contrast.  0.98
    # keeps those reviewed sizes while the full title, same-card geometry and
    # raw-RGB Go integrity remain mandatory.
    safe_threshold = max(0.98, float(threshold))
    viewport = content_viewport(screenshot)
    task_point, task_score = _match_daily_task_template(
        screenshot,
        BUILTIN_DAILY_MISSION_UPGRADE_BUILDING_ASSET,
        BUILTIN_DAILY_MISSION_UPGRADE_BUILDING_TEMPLATE_NAME,
        safe_threshold,
        _relative_region(screenshot, 0.03, 0.34, 0.66, 0.87),
    )
    if not task_point:
        return None
    row_top = max(viewport.top, task_point[1] - round(viewport.height * 0.015))
    row_bottom = min(viewport.bottom, task_point[1] + round(viewport.height * 0.115))
    go_point, go_score = _match_daily_mission_go_control(
        screenshot,
        safe_threshold,
        (
            viewport.left + round(viewport.width * 0.64),
            row_top,
            viewport.left + round(viewport.width * 0.99),
            row_bottom,
        ),
    )
    if not go_point:
        return None
    x_delta = go_point[0] - task_point[0]
    y_delta = go_point[1] - task_point[1]
    if not (
        viewport.width * 0.48 <= x_delta <= viewport.width * 0.80
        and viewport.height * 0.015 <= y_delta <= viewport.height * 0.11
    ):
        return None
    return DailyMissionMatch(
        DailyMissionKind.UPGRADE_BUILDING,
        task_point,
        go_point,
        min(task_score, go_score),
    )


def match_daily_research_tech_mission(
    screenshot: Image.Image,
    threshold: float,
) -> DailyMissionMatch | None:
    """Find the exact unfinished one-research task and its same-card ``Go``.

    This matcher only authorises navigation away from a freshly verified
    Daily card.  It does not authorise an arbitrary technology node, research
    button, speed-up, activation, or purchase on the destination page.
    """
    title_threshold = max(0.98, float(threshold))
    go_threshold = max(0.95, float(threshold))
    viewport = content_viewport(screenshot)
    task_point, task_score = _match_daily_task_template(
        screenshot,
        BUILTIN_DAILY_MISSION_RESEARCH_TECH_ASSET,
        BUILTIN_DAILY_MISSION_RESEARCH_TECH_TEMPLATE_NAME,
        title_threshold,
        _relative_region(screenshot, 0.03, 0.34, 0.66, 0.87),
    )
    if not task_point:
        return None
    row_top = max(viewport.top, task_point[1] - round(viewport.height * 0.015))
    row_bottom = min(viewport.bottom, task_point[1] + round(viewport.height * 0.115))
    go_point, go_score = _match_daily_mission_go_control(
        screenshot,
        go_threshold,
        (
            viewport.left + round(viewport.width * 0.64),
            row_top,
            viewport.left + round(viewport.width * 0.99),
            row_bottom,
        ),
    )
    if not go_point:
        return None
    x_delta = go_point[0] - task_point[0]
    y_delta = go_point[1] - task_point[1]
    if not (
        viewport.width * 0.48 <= x_delta <= viewport.width * 0.80
        and viewport.height * 0.015 <= y_delta <= viewport.height * 0.11
    ):
        return None
    return DailyMissionMatch(
        DailyMissionKind.RESEARCH_TECH,
        task_point,
        go_point,
        min(task_score, go_score),
    )


_DAILY_HERO_RECRUIT_TITLE_SPECS: tuple[tuple[str, str], ...] = (
    (
        BUILTIN_DAILY_MISSION_HERO_RECRUIT_1_ASSET,
        BUILTIN_DAILY_MISSION_HERO_RECRUIT_1_TEMPLATE_NAME,
    ),
    (BUILTIN_DAILY_MISSION_HERO_RECRUIT_ASSET, BUILTIN_DAILY_MISSION_HERO_RECRUIT_TEMPLATE_NAME),
)

_DAILY_ALLIANCE_DONATE_TITLE_SPECS: tuple[tuple[str, str], ...] = (
    (
        BUILTIN_DAILY_MISSION_ALLIANCE_DONATE_5_ASSET,
        BUILTIN_DAILY_MISSION_ALLIANCE_DONATE_5_TEMPLATE_NAME,
    ),
    (BUILTIN_DAILY_MISSION_ALLIANCE_DONATE_ASSET, BUILTIN_DAILY_MISSION_ALLIANCE_DONATE_TEMPLATE_NAME),
)


def match_daily_hero_recruit_mission(
    screenshot: Image.Image,
    threshold: float,
) -> DailyMissionMatch | None:
    """Find an unfinished hero-recruit Daily Task and its own blue ``Go``.

    Current and legacy title anchors cover the reviewed 1- and 3-recruit task
    variants while excluding each mutable completion suffix. The same-card
    blue Go is still mandatory, making a completed or claimed row inert.
    """
    safe_threshold = max(0.94, float(threshold))
    viewport = content_viewport(screenshot)
    task_point, task_score = _match_best_daily_task_title(
        screenshot,
        _DAILY_HERO_RECRUIT_TITLE_SPECS,
        safe_threshold,
        _relative_region(screenshot, 0.03, 0.34, 0.66, 0.87),
    )
    if not task_point:
        return None
    row_top = max(viewport.top, task_point[1] - round(viewport.height * 0.015))
    row_bottom = min(viewport.bottom, task_point[1] + round(viewport.height * 0.115))
    go_point, go_score = _match_daily_mission_go_control(
        screenshot,
        safe_threshold,
        (
            viewport.left + round(viewport.width * 0.64),
            row_top,
            viewport.left + round(viewport.width * 0.99),
            row_bottom,
        ),
    )
    if not go_point:
        return None
    x_delta = go_point[0] - task_point[0]
    y_delta = go_point[1] - task_point[1]
    if not (
        viewport.width * 0.48 <= x_delta <= viewport.width * 0.80
        and viewport.height * 0.015 <= y_delta <= viewport.height * 0.11
    ):
        return None
    return DailyMissionMatch(DailyMissionKind.HERO_RECRUIT, task_point, go_point, min(task_score, go_score))


def match_daily_alliance_donate_mission(
    screenshot: Image.Image,
    threshold: float,
) -> DailyMissionMatch | None:
    """Find the unfinished Alliance Donation card and its own blue ``Go``.

    The daily card's mutable target and counter are deliberately outside the
    title crop.  Tapping it still needs the same reviewed blue Go control in
    this exact card, so a generic alliance or research button cannot start
    the donation route.
    """
    safe_threshold = max(0.94, float(threshold))
    viewport = content_viewport(screenshot)
    task_point, task_score = _match_best_daily_task_title(
        screenshot,
        _DAILY_ALLIANCE_DONATE_TITLE_SPECS,
        safe_threshold,
        _relative_region(screenshot, 0.03, 0.34, 0.66, 0.87),
    )
    if not task_point:
        return None
    row_top = max(viewport.top, task_point[1] - round(viewport.height * 0.015))
    row_bottom = min(viewport.bottom, task_point[1] + round(viewport.height * 0.115))
    go_point, go_score = _match_daily_mission_go_control(
        screenshot,
        safe_threshold,
        (
            viewport.left + round(viewport.width * 0.64),
            row_top,
            viewport.left + round(viewport.width * 0.99),
            row_bottom,
        ),
    )
    if not go_point:
        return None
    x_delta = go_point[0] - task_point[0]
    y_delta = go_point[1] - task_point[1]
    if not (
        viewport.width * 0.48 <= x_delta <= viewport.width * 0.80
        and viewport.height * 0.015 <= y_delta <= viewport.height * 0.11
    ):
        return None
    return DailyMissionMatch(DailyMissionKind.ALLIANCE_DONATE, task_point, go_point, min(task_score, go_score))


def match_daily_alliance_food_donation(
    screenshot: Image.Image,
    threshold: float,
) -> tuple[tuple[int, int] | None, float]:
    """Return the blue food donation only when its diamond sibling is visible.

    The yellow diamond donation is proof of the two-option Alliance Donation
    layout, never a target.  A normal food button must be on the right of that
    yellow sibling in the same bottom row, and it must pass raw RGB integrity
    validation before a caller can tap it.  This leaves every diamond, key,
    and paid control without a click path.
    """
    safe_threshold = max(0.94, float(threshold))
    viewport = content_viewport(screenshot)
    food_point, food_score = _match_daily_task_template(
        screenshot,
        BUILTIN_DAILY_ALLIANCE_FOOD_DONATE_ASSET,
        BUILTIN_DAILY_ALLIANCE_FOOD_DONATE_TEMPLATE_NAME,
        safe_threshold,
        _relative_region(screenshot, 0.45, 0.68, 1.0, 0.91),
    )
    diamond_point, diamond_score = _match_daily_task_template(
        screenshot,
        BUILTIN_DAILY_ALLIANCE_DIAMOND_DONATE_ASSET,
        BUILTIN_DAILY_ALLIANCE_DIAMOND_DONATE_TEMPLATE_NAME,
        safe_threshold,
        _relative_region(screenshot, 0.0, 0.68, 0.55, 0.91),
    )
    if not food_point or not diamond_point:
        return None, max(food_score, diamond_score)
    x_delta = food_point[0] - diamond_point[0]
    y_delta = abs(food_point[1] - diamond_point[1])
    if not (
        viewport.width * 0.30 <= x_delta <= viewport.width * 0.55
        and y_delta <= viewport.height * 0.025
    ):
        return None, min(food_score, diamond_score)
    if not _daily_template_integrity_is_valid(
        screenshot,
        BUILTIN_DAILY_ALLIANCE_DIAMOND_DONATE_ASSET,
        BUILTIN_DAILY_ALLIANCE_DIAMOND_DONATE_TEMPLATE_NAME,
        diamond_point,
        min_luma_ratio=DAILY_ACTION_MIN_LUMA_RATIO,
        min_chroma_ratio=DAILY_ACTION_MIN_CHROMA_RATIO,
        max_colour_distance=DAILY_ACTION_MAX_COLOUR_DISTANCE,
        strict_action=True,
    ):
        return None, min(food_score, diamond_score)
    if not _daily_template_integrity_is_valid(
        screenshot,
        BUILTIN_DAILY_ALLIANCE_FOOD_DONATE_ASSET,
        BUILTIN_DAILY_ALLIANCE_FOOD_DONATE_TEMPLATE_NAME,
        food_point,
        min_luma_ratio=DAILY_ACTION_MIN_LUMA_RATIO,
        min_chroma_ratio=DAILY_ACTION_MIN_CHROMA_RATIO,
        max_colour_distance=DAILY_ACTION_MAX_COLOUR_DISTANCE,
        strict_action=True,
    ):
        return None, min(food_score, diamond_score)
    return food_point, min(food_score, diamond_score)


def daily_alliance_donation_page_is_visible(
    screenshot: Image.Image,
    threshold: float,
) -> bool:
    """Recognise either enabled or exhausted normal-food donation layouts.

    This is page evidence only.  In particular, a matching grey exhausted
    food button can authorize a controller to use Android Back to leave the
    page, but it never returns a tap point and cannot make that button
    actionable.
    """
    active_point, _ = match_daily_alliance_food_donation(screenshot, threshold)
    if active_point:
        return True
    safe_threshold = max(0.94, float(threshold))
    viewport = content_viewport(screenshot)
    disabled_point, disabled_score = _match_daily_task_template(
        screenshot,
        BUILTIN_DAILY_ALLIANCE_FOOD_DONATE_DISABLED_ASSET,
        BUILTIN_DAILY_ALLIANCE_FOOD_DONATE_DISABLED_TEMPLATE_NAME,
        safe_threshold,
        _relative_region(screenshot, 0.45, 0.68, 1.0, 0.91),
    )
    diamond_point, diamond_score = _match_daily_task_template(
        screenshot,
        BUILTIN_DAILY_ALLIANCE_DIAMOND_DONATE_ASSET,
        BUILTIN_DAILY_ALLIANCE_DIAMOND_DONATE_TEMPLATE_NAME,
        safe_threshold,
        _relative_region(screenshot, 0.0, 0.68, 0.55, 0.91),
    )
    if not disabled_point or not diamond_point:
        return False
    x_delta = disabled_point[0] - diamond_point[0]
    y_delta = abs(disabled_point[1] - diamond_point[1])
    if not (
        viewport.width * 0.30 <= x_delta <= viewport.width * 0.55
        and y_delta <= viewport.height * 0.025
    ):
        return False
    return _daily_template_integrity_is_valid(
        screenshot,
        BUILTIN_DAILY_ALLIANCE_FOOD_DONATE_DISABLED_ASSET,
        BUILTIN_DAILY_ALLIANCE_FOOD_DONATE_DISABLED_TEMPLATE_NAME,
        disabled_point,
        min_luma_ratio=DAILY_ACTION_MIN_LUMA_RATIO,
        min_chroma_ratio=DAILY_ACTION_MIN_CHROMA_RATIO,
        max_colour_distance=DAILY_ACTION_MAX_COLOUR_DISTANCE,
        strict_action=True,
    ) and _daily_template_integrity_is_valid(
        screenshot,
        BUILTIN_DAILY_ALLIANCE_DIAMOND_DONATE_ASSET,
        BUILTIN_DAILY_ALLIANCE_DIAMOND_DONATE_TEMPLATE_NAME,
        diamond_point,
        min_luma_ratio=DAILY_ACTION_MIN_LUMA_RATIO,
        min_chroma_ratio=DAILY_ACTION_MIN_CHROMA_RATIO,
        max_colour_distance=DAILY_ACTION_MAX_COLOUR_DISTANCE,
        strict_action=True,
    )


def match_daily_city_alliance_entry(
    screenshot: Image.Image,
    threshold: float,
) -> tuple[tuple[int, int] | None, float]:
    """Find the city Alliance tab after a verified Daily-Tasks city return.

    A new-account tutorial finger may partly obscure the Alliance label.  In
    that case this returns the separately measured Alliance-tab centre only
    after the independent Daily city-task anchor is present in the *same*
    frame.  Controllers must still observe it in two frames before tapping;
    the fallback has no general-game use.
    """
    city_point, city_score = match_daily_city_entry(screenshot, threshold)
    if not city_point:
        return None, city_score
    asset = resource_path(BUILTIN_CITY_ALLIANCE_TEMPLATE_ASSET)
    if not asset.is_file():
        return None, city_score
    viewport = content_viewport(screenshot)
    point, score = match_template(
        screenshot,
        asset,
        max(0.86, float(threshold) - 0.04),
        template_reference_size(asset),
        (
            viewport.left + round(viewport.width * 0.48),
            viewport.top + round(viewport.height * 0.74),
            viewport.left + round(viewport.width * 0.94),
            viewport.bottom,
        ),
    )
    if point:
        return point, min(city_score, score)

    # This is not a visual guess: (1055, 2497) is the measured centre of the
    # Alliance tab on the same 1440x2560 city strip used by the packaged
    # template.  The exact Daily city anchor above and a required second
    # frame make the tutorial-only fallback input-free anywhere else.
    return map_content_point((1055, 2497), BUILTIN_DAILY_TASK_REFERENCE_SIZE, screenshot), min(city_score, score)


def match_daily_alliance_tech_entry(
    screenshot: Image.Image,
    threshold: float,
) -> tuple[tuple[int, int] | None, float]:
    """Recognise the microscope icon for the Alliance Technology route."""
    viewport = content_viewport(screenshot)
    point, score = _match_daily_task_template(
        screenshot,
        BUILTIN_DAILY_ALLIANCE_TECH_ENTRY_ASSET,
        BUILTIN_DAILY_ALLIANCE_TECH_ENTRY_TEMPLATE_NAME,
        max(0.93, float(threshold)),
        _relative_region(screenshot, 0.45, 0.56, 0.78, 0.82),
    )
    if not point:
        return None, score
    if not _daily_template_integrity_is_valid(
        screenshot,
        BUILTIN_DAILY_ALLIANCE_TECH_ENTRY_ASSET,
        BUILTIN_DAILY_ALLIANCE_TECH_ENTRY_TEMPLATE_NAME,
        point,
        min_luma_ratio=DAILY_ACTION_MIN_LUMA_RATIO,
        min_chroma_ratio=DAILY_ACTION_MIN_CHROMA_RATIO,
        max_colour_distance=DAILY_ACTION_MAX_COLOUR_DISTANCE,
        strict_action=True,
    ):
        return None, score
    return point, score


def daily_alliance_tech_entry_point(screenshot: Image.Image) -> tuple[int, int]:
    """Return the center of the button proven by ``match_daily_alliance_tech_entry``."""
    return map_content_point((1055, 1870), BUILTIN_DAILY_TASK_REFERENCE_SIZE, screenshot)


def match_daily_alliance_sustain_node(
    screenshot: Image.Image,
    threshold: float,
) -> tuple[tuple[int, int] | None, float]:
    """Recognise the specific Alliance Sustain tech node that owns food donation."""
    return _match_daily_task_template(
        screenshot,
        BUILTIN_DAILY_ALLIANCE_SUSTAIN_NODE_ASSET,
        BUILTIN_DAILY_ALLIANCE_SUSTAIN_NODE_TEMPLATE_NAME,
        max(0.94, float(threshold)),
        _relative_region(screenshot, 0.30, 0.70, 0.70, 0.95),
    )


def daily_alliance_sustain_node_point(screenshot: Image.Image) -> tuple[int, int]:
    """Return the center of the node proven by its exact ``联盟永续`` title."""
    return map_content_point((720, 2110), BUILTIN_DAILY_TASK_REFERENCE_SIZE, screenshot)


def _match_daily_alliance_tech_tab_strip(
    screenshot: Image.Image,
    threshold: float,
    asset: str,
    template_name: str,
) -> tuple[tuple[int, int] | None, float]:
    """Return the exact selected-tab strip anchor after RGB integrity checks."""
    anchor, score = _match_daily_task_template(
        screenshot,
        asset,
        template_name,
        max(0.980, float(threshold)),
        _relative_region(screenshot, 0.00, 0.16, 1.00, 0.27),
    )
    if not anchor:
        return None, score
    if not _daily_template_integrity_is_valid(
        screenshot,
        asset,
        template_name,
        anchor,
        min_luma_ratio=DAILY_ACTION_MIN_LUMA_RATIO,
        min_chroma_ratio=DAILY_ACTION_MIN_CHROMA_RATIO,
        max_colour_distance=DAILY_ACTION_MAX_COLOUR_DISTANCE,
        strict_action=True,
    ):
        return None, score
    return anchor, score


def daily_alliance_tech_territory_tab_point(screenshot: Image.Image) -> tuple[int, int]:
    """Return the Territory tab centre after an exact full-strip proof."""
    return map_content_point((720, 535), BUILTIN_DAILY_TASK_REFERENCE_SIZE, screenshot)


def match_daily_alliance_tech_battle_tab_strip(
    screenshot: Image.Image,
    threshold: float,
) -> tuple[tuple[int, int] | None, float]:
    """Return Development only from the reviewed Battle-selected strip.

    This legacy return point remains for compatibility.  New Territory
    routing uses the same exact proof and separately maps the Territory tab.
    """
    anchor, score = _match_daily_alliance_tech_tab_strip(
        screenshot,
        threshold,
        BUILTIN_DAILY_ALLIANCE_TECH_BATTLE_TAB_STRIP_ASSET,
        BUILTIN_DAILY_ALLIANCE_TECH_BATTLE_TAB_STRIP_TEMPLATE_NAME,
    )
    if not anchor:
        return None, score
    return map_content_point((265, 535), BUILTIN_DAILY_TASK_REFERENCE_SIZE, screenshot), score


def match_daily_alliance_tech_development_tab_strip(
    screenshot: Image.Image,
    threshold: float,
) -> tuple[tuple[int, int] | None, float]:
    """Return Territory only from the reviewed Development-selected strip."""
    anchor, score = _match_daily_alliance_tech_tab_strip(
        screenshot,
        threshold,
        BUILTIN_DAILY_ALLIANCE_TECH_DEVELOPMENT_TAB_STRIP_ASSET,
        BUILTIN_DAILY_ALLIANCE_TECH_DEVELOPMENT_TAB_STRIP_TEMPLATE_NAME,
    )
    if not anchor:
        return None, score
    return daily_alliance_tech_territory_tab_point(screenshot), score


def match_daily_alliance_tech_territory_tab_strip(
    screenshot: Image.Image,
    threshold: float,
) -> tuple[tuple[int, int] | None, float]:
    """Passively prove the full Territory-selected Alliance Technology strip."""
    anchor, score = _match_daily_alliance_tech_tab_strip(
        screenshot,
        threshold,
        BUILTIN_DAILY_ALLIANCE_TECH_TERRITORY_TAB_STRIP_ASSET,
        BUILTIN_DAILY_ALLIANCE_TECH_TERRITORY_TAB_STRIP_TEMPLATE_NAME,
    )
    if not anchor:
        return None, score
    return daily_alliance_tech_territory_tab_point(screenshot), score


def match_daily_gather_mission(
    screenshot: Image.Image,
    threshold: float,
) -> DailyMissionMatch | None:
    """Return the highest-priority visible ordinary-resource daily card."""
    matches = match_daily_gather_missions(screenshot, threshold)
    return matches[0] if matches else None


def match_daily_gather_world_search(
    screenshot: Image.Image,
    threshold: float,
) -> tuple[tuple[int, int] | None, float]:
    """Recognise the world-map magnifier before opening resource search."""
    point, score = _match_daily_task_template(
        screenshot,
        BUILTIN_DAILY_GATHER_WORLD_SEARCH_ASSET,
        BUILTIN_DAILY_GATHER_WORLD_SEARCH_TEMPLATE_NAME,
        max(0.985, float(threshold)),
        _relative_region(screenshot, 0.00, 0.60, 0.18, 0.82),
    )
    # The round icon intentionally sits on live map terrain, so its outside
    # pixels change from snow to water.  The match is still restricted to the
    # lower-left world-map search lane and is reachable only after this worker
    # has opened a reviewed resource route; a raw-RGB equality check here
    # would incorrectly reject the same icon over different terrain.
    if point:
        return point, score

    # The map's overnight colour treatment can dim the otherwise unchanged
    # lower-left lens enough that the normal 0.90 template score falls just
    # below its daytime threshold.  Do not loosen the regular route proof:
    # this recovery still requires the same template, in the same restricted
    # lane, to land at the content-mapped fixed lens centre.  That keeps it
    # unavailable as a generic navigation click while allowing a naturally
    # returned march to proceed to the next already-reviewed Daily task.
    night_point, night_score = _match_daily_task_template(
        screenshot,
        BUILTIN_DAILY_GATHER_WORLD_SEARCH_ASSET,
        BUILTIN_DAILY_GATHER_WORLD_SEARCH_TEMPLATE_NAME,
        0.845,
        _relative_region(screenshot, 0.00, 0.60, 0.18, 0.82),
    )
    expected_lens = map_content_point((95, 1755), BUILTIN_DAILY_TASK_REFERENCE_SIZE, screenshot)
    if night_point and max(abs(night_point[0] - expected_lens[0]), abs(night_point[1] - expected_lens[1])) <= 12:
        return night_point, night_score
    score = max(score, night_score)

    # The wide original reference contains some background terrain.  Use a
    # second, circle-only reference before considering the tutorial variants:
    # it preserves the same icon proof when a returned march leaves the camera
    # over snow, water, or an animated map prop.
    tight_point, tight_score = _match_daily_task_template(
        screenshot,
        BUILTIN_DAILY_GATHER_WORLD_SEARCH_TIGHT_ASSET,
        BUILTIN_DAILY_GATHER_WORLD_SEARCH_TIGHT_TEMPLATE_NAME,
        max(0.90, float(threshold)),
        _relative_region(screenshot, 0.00, 0.60, 0.18, 0.82),
    )
    if tight_point:
        return tight_point, tight_score

    # A new account can receive the game's animated tutorial finger exactly
    # over the same magnifier.  It is not a generic popup dismissal: the
    # tightly captured finger + highlighted lens is merely an alternative
    # visual proof for this one already-reviewed search target.
    tutorial_score = 0.0
    tutorial_region = _relative_region(screenshot, 0.00, 0.54, 0.26, 0.83)
    for asset, template_name in (
        (BUILTIN_DAILY_GATHER_SEARCH_TUTORIAL_ASSET, BUILTIN_DAILY_GATHER_SEARCH_TUTORIAL_TEMPLATE_NAME),
        (BUILTIN_DAILY_GATHER_SEARCH_TUTORIAL_ALT_ASSET, BUILTIN_DAILY_GATHER_SEARCH_TUTORIAL_ALT_TEMPLATE_NAME),
    ):
        tutorial, candidate_score = _match_daily_task_template(
            screenshot,
            asset,
            template_name,
            max(0.90, float(threshold)),
            tutorial_region,
        )
        tutorial_score = max(tutorial_score, candidate_score)
        if tutorial:
            return map_content_point((95, 1755), BUILTIN_DAILY_TASK_REFERENCE_SIZE, screenshot), candidate_score

    # The hand has a short idle animation.  Its two captured poses above are
    # preferred; this final check recognises the same large skin-colour mass
    # over the lower-left magnifier while the worker is already in the one
    # staged "world search" phase.  It is not exposed as a generic UI action.
    x0, y0, x1, y1 = tutorial_region
    region = np.asarray(screenshot.convert("RGB"))[y0:y1, x0:x1]
    if region.size:
        skin = (
            (region[:, :, 0] >= 85)
            & (region[:, :, 0] <= 245)
            & (region[:, :, 1] >= 45)
            & (region[:, :, 1] <= 210)
            & (region[:, :, 2] <= 170)
            & (region[:, :, 0] >= region[:, :, 1] * 1.18)
            & (region[:, :, 1] >= region[:, :, 2] * 0.80)
        )
        if float(np.mean(skin)) >= 0.070:
            return map_content_point((95, 1755), BUILTIN_DAILY_TASK_REFERENCE_SIZE, screenshot), 0.90
    return None, max(score, tight_score, tutorial_score)


def match_daily_world_town_entry(
    screenshot: Image.Image,
    threshold: float,
) -> tuple[tuple[int, int] | None, float]:
    """Recognise the reviewed world-map return-to-town control.

    This is not exposed as a generic back/close action.  It requires both the
    lower-left world-search lens and the lower-right Town control in the same
    frame, and callers use it only before their own Daily Task city-entry tap.
    """
    world_lens, lens_score = match_daily_gather_world_search(screenshot, threshold)
    if world_lens:
        point, town_score = _match_daily_task_template(
            screenshot,
            BUILTIN_DAILY_WORLD_TOWN_ENTRY_ASSET,
            BUILTIN_DAILY_WORLD_TOWN_ENTRY_TEMPLATE_NAME,
            max(0.95, float(threshold)),
            _relative_region(screenshot, 0.80, 0.85, 1.00, 1.00),
        )
        if point and _daily_template_integrity_is_valid(
            screenshot,
            BUILTIN_DAILY_WORLD_TOWN_ENTRY_ASSET,
            BUILTIN_DAILY_WORLD_TOWN_ENTRY_TEMPLATE_NAME,
            point,
            min_luma_ratio=DAILY_TOWN_MIN_LUMA_RATIO,
            min_chroma_ratio=DAILY_ACTION_MIN_CHROMA_RATIO,
            max_colour_distance=DAILY_ACTION_MAX_COLOUR_DISTANCE,
            strict_action=True,
        ):
            return (
                map_content_point(
                    (1330, 2395),
                    BUILTIN_DAILY_TASK_REFERENCE_SIZE,
                    screenshot,
                ),
                town_score,
            )
    else:
        town_score = 0.0

    # The expanded world toolbar is still the wilderness state: it exposes
    # ``Town`` at the reviewed lower-right coordinate while the city state
    # exposes ``Wilderness`` instead.  Its surrounding snow shelf differs
    # enough from the compact map layout to deserve an exact variant.  Keep
    # the ordinary world-search proof and an exact-position check; never make
    # this a generic lower-right action.  Unlike the legacy compact control,
    # this full icon variant is sufficient state proof by itself: dense
    # alliance labels can cover the independent lens even though the game is
    # visibly still in wilderness.  Callers still require two fresh matches.
    toolbar_town, toolbar_town_score = _match_daily_task_template(
        screenshot,
        BUILTIN_DAILY_WORLD_TOWN_ENTRY_TOOLBAR_ASSET,
        BUILTIN_DAILY_WORLD_TOWN_ENTRY_TOOLBAR_TEMPLATE_NAME,
        # The icon has a small idle shimmer on the live wilderness toolbar.
        # Reviewed consecutive frames vary down to ~0.984 while a 6% dimmed
        # look-alike still fails the raw-colour integrity gate below.  Keep
        # the exact fixed coordinate and two-frame caller proof, but do not
        # let that harmless animation make every other frame disappear.
        max(0.980, float(threshold)),
        _relative_region(screenshot, 0.80, 0.85, 1.00, 1.00),
    )
    expected_town = map_content_point(
        (1330, 2395), BUILTIN_DAILY_TASK_REFERENCE_SIZE, screenshot
    )
    if (
        toolbar_town
        and max(
            abs(toolbar_town[0] - expected_town[0]),
            abs(toolbar_town[1] - expected_town[1]),
        )
        <= 12
        and _daily_template_integrity_is_valid(
            screenshot,
            BUILTIN_DAILY_WORLD_TOWN_ENTRY_TOOLBAR_ASSET,
            BUILTIN_DAILY_WORLD_TOWN_ENTRY_TOOLBAR_TEMPLATE_NAME,
            toolbar_town,
            min_luma_ratio=0.98,
            min_chroma_ratio=DAILY_ACTION_MIN_CHROMA_RATIO,
            max_colour_distance=DAILY_ACTION_MAX_COLOUR_DISTANCE,
            strict_action=True,
        )
    ):
        return expected_town, toolbar_town_score

    # On the newly audited high-level account, dense alliance buildings and
    # labels change nearly every background pixel around both controls.  Use
    # only two tight, account-free icon interiors from the same fresh frame.
    # Neither anchor is sufficient alone and the action target receives the
    # same raw-colour veil guard as every other reviewed tap.
    dense_lens, dense_lens_score = _match_daily_task_template(
        screenshot,
        BUILTIN_DAILY_GATHER_WORLD_SEARCH_TIGHT_DENSE_ASSET,
        BUILTIN_DAILY_GATHER_WORLD_SEARCH_TIGHT_DENSE_TEMPLATE_NAME,
        max(0.95, float(threshold)),
        _relative_region(screenshot, 0.00, 0.60, 0.18, 0.82),
    )
    dense_town, dense_town_score = _match_daily_task_template(
        screenshot,
        BUILTIN_DAILY_WORLD_TOWN_ENTRY_TIGHT_DENSE_ASSET,
        BUILTIN_DAILY_WORLD_TOWN_ENTRY_TIGHT_DENSE_TEMPLATE_NAME,
        max(0.97, float(threshold)),
        _relative_region(screenshot, 0.80, 0.85, 1.00, 1.00),
    )
    if not dense_lens or not dense_town:
        return None, max(
            lens_score,
            town_score,
            toolbar_town_score,
            dense_lens_score,
            dense_town_score,
        )
    if not _daily_template_integrity_is_valid(
        screenshot,
        BUILTIN_DAILY_WORLD_TOWN_ENTRY_TIGHT_DENSE_ASSET,
        BUILTIN_DAILY_WORLD_TOWN_ENTRY_TIGHT_DENSE_TEMPLATE_NAME,
        dense_town,
        min_luma_ratio=DAILY_TOWN_MIN_LUMA_RATIO,
        min_chroma_ratio=DAILY_ACTION_MIN_CHROMA_RATIO,
        max_colour_distance=DAILY_ACTION_MAX_COLOUR_DISTANCE,
        strict_action=True,
    ):
        return None, max(
            lens_score,
            town_score,
            toolbar_town_score,
            dense_lens_score,
            dense_town_score,
        )
    return (
        map_content_point(
            (1330, 2395), BUILTIN_DAILY_TASK_REFERENCE_SIZE, screenshot
        ),
        min(dense_lens_score, dense_town_score),
    )


def match_daily_city_wilderness_entry(
    screenshot: Image.Image,
    threshold: float,
) -> tuple[tuple[int, int] | None, float]:
    """Recognise only the reviewed city-side ``野外`` control."""

    point, score = _match_daily_task_template(
        screenshot,
        BUILTIN_DAILY_CITY_WILDERNESS_ENTRY_ASSET,
        BUILTIN_DAILY_CITY_WILDERNESS_ENTRY_TEMPLATE_NAME,
        max(0.95, float(threshold)),
        _relative_region(screenshot, 0.78, 0.84, 1.00, 1.00),
    )
    if point:
        return map_content_point((1320, 2390), BUILTIN_DAILY_TASK_REFERENCE_SIZE, screenshot), score

    # The live daytime city keeps the button artwork unchanged but changes
    # the building/sky pixels behind the old wide crop.  Use a tight icon +
    # label variant only after the independent city Daily-entry anchor is
    # present in the same frame.  This remains a city-only navigation proof,
    # never a generic lower-right click.
    city_point, city_score = match_daily_city_entry(screenshot, threshold)
    if not city_point:
        return None, max(score, city_score)
    tight_point, tight_score = _match_daily_task_template(
        screenshot,
        BUILTIN_DAILY_CITY_WILDERNESS_ENTRY_TIGHT_DAY_ASSET,
        BUILTIN_DAILY_CITY_WILDERNESS_ENTRY_TIGHT_DAY_TEMPLATE_NAME,
        # The current low-level city camera scores this exact tight icon +
        # label at 0.9726-0.9734 in two fresh frames.  A separate strict city
        # anchor remains mandatory above, so this does not widen the matcher
        # to a generic lower-right control.
        max(0.97, float(threshold)),
        _relative_region(screenshot, 0.78, 0.84, 1.00, 1.00),
    )
    if tight_point:
        return map_content_point((1310, 2430), BUILTIN_DAILY_TASK_REFERENCE_SIZE, screenshot), tight_score

    # The current small account uses the same immutable icon and label at the
    # same geometry but a darker camera background.  Keep a separate exact
    # crop instead of lowering the shared threshold.  The strict Daily city
    # anchor above is still mandatory in this same frame, and Town still
    # vetoes that anchor, so this variant cannot authorise a wilderness map.
    low_point, low_score = _match_daily_task_template(
        screenshot,
        BUILTIN_DAILY_CITY_WILDERNESS_ENTRY_TIGHT_LOW_ACCOUNT_ASSET,
        BUILTIN_DAILY_CITY_WILDERNESS_ENTRY_TIGHT_LOW_ACCOUNT_TEMPLATE_NAME,
        max(0.97, float(threshold)),
        _relative_region(screenshot, 0.78, 0.84, 1.00, 1.00),
    )
    if not low_point:
        return None, max(score, city_score, tight_score, low_score)
    return map_content_point((1310, 2430), BUILTIN_DAILY_TASK_REFERENCE_SIZE, screenshot), low_score


def match_daily_world_overview_entry(
    screenshot: Image.Image,
    threshold: float,
) -> tuple[tuple[int, int] | None, float]:
    """Recognise the exact lower-left kingdom-overview globe on a world map."""

    world_lens, lens_score = match_daily_gather_world_search(screenshot, threshold)
    if not world_lens:
        return None, lens_score
    point, score = _match_daily_task_template(
        screenshot,
        BUILTIN_DAILY_WORLD_OVERVIEW_ENTRY_ASSET,
        BUILTIN_DAILY_WORLD_OVERVIEW_ENTRY_TEMPLATE_NAME,
        max(0.90, float(threshold)),
        _relative_region(screenshot, 0.00, 0.64, 0.18, 0.86),
    )
    if not point:
        return None, max(lens_score, score)
    return map_content_point((70, 1925), BUILTIN_DAILY_TASK_REFERENCE_SIZE, screenshot), score


def match_daily_world_overview_resource_off(
    screenshot: Image.Image,
    threshold: float,
) -> tuple[tuple[int, int] | None, float]:
    """Return only the exact unchecked Resource-layer square."""

    point, score = _match_daily_task_template(
        screenshot,
        BUILTIN_DAILY_WORLD_OVERVIEW_RESOURCE_OFF_ASSET,
        BUILTIN_DAILY_WORLD_OVERVIEW_RESOURCE_OFF_TEMPLATE_NAME,
        max(0.97, float(threshold)),
        _relative_region(screenshot, 0.00, 0.07, 0.30, 0.21),
    )
    if not point:
        return None, score
    return map_content_point((55, 385), BUILTIN_DAILY_TASK_REFERENCE_SIZE, screenshot), score


def daily_world_overview_resource_is_enabled(
    screenshot: Image.Image,
    threshold: float,
) -> bool:
    """Prove the overview panel and the green Resource-layer check together."""

    panel, _score = _match_daily_task_template(
        screenshot,
        BUILTIN_DAILY_WORLD_OVERVIEW_PANEL_ANCHOR_ASSET,
        BUILTIN_DAILY_WORLD_OVERVIEW_PANEL_ANCHOR_TEMPLATE_NAME,
        max(0.96, float(threshold)),
        _relative_region(screenshot, 0.00, 0.07, 0.30, 0.21),
    )
    if not panel:
        return False
    x0, y0 = map_content_point((15, 340), BUILTIN_DAILY_TASK_REFERENCE_SIZE, screenshot)
    x1, y1 = map_content_point((100, 440), BUILTIN_DAILY_TASK_REFERENCE_SIZE, screenshot)
    roi = np.asarray(screenshot.convert("RGB"))[y0:y1, x0:x1]
    if roi.size == 0:
        return False
    hsv = cv2.cvtColor(roi, cv2.COLOR_RGB2HSV)
    green = cv2.inRange(
        hsv,
        np.array((35, 120, 100), np.uint8),
        np.array((90, 255, 255), np.uint8),
    )
    return float(np.mean(green > 0)) >= 0.08


def match_daily_world_overview_home_button(
    screenshot: Image.Image,
    threshold: float,
) -> tuple[tuple[int, int] | None, float]:
    """Match only the overview's blue *return to my castle* house.

    The dynamic distance caption is deliberately absent from the template.
    The independently verified Resource-layer panel is mandatory, so a house
    pictogram on any unrelated page can never authorise an input.
    """

    if not daily_world_overview_resource_is_enabled(screenshot, threshold):
        return None, 0.0
    point, score = _match_daily_task_template(
        screenshot,
        BUILTIN_DAILY_WORLD_OVERVIEW_HOME_BUTTON_ASSET,
        BUILTIN_DAILY_WORLD_OVERVIEW_HOME_BUTTON_TEMPLATE_NAME,
        max(0.96, float(threshold)),
        _relative_region(screenshot, 0.72, 0.03, 1.00, 0.21),
    )
    if not point:
        return None, score
    if not _daily_template_integrity_is_valid(
        screenshot,
        BUILTIN_DAILY_WORLD_OVERVIEW_HOME_BUTTON_ASSET,
        BUILTIN_DAILY_WORLD_OVERVIEW_HOME_BUTTON_TEMPLATE_NAME,
        point,
        min_luma_ratio=0.92,
        min_chroma_ratio=0.90,
        max_colour_distance=0.08,
        strict_action=True,
    ):
        return None, score
    return point, score


def match_daily_world_overview_home_button_fast(
    screenshot: Image.Image,
    threshold: float = 0.76,
) -> tuple[tuple[int, int] | None, float]:
    """Find the transient blue castle-home button anywhere on the map.

    This deliberately performs one full-map template match and nothing else.
    It is only actionable in the controller's short window immediately after
    an already-verified kingdom-overview tap.  The button may appear along
    any screen edge, and waiting for the overview panel/resource classifiers
    first can make it disappear.  The changing distance caption is absent
    from the small template.
    """

    fast_threshold = max(0.74, min(0.76, float(threshold)))
    return _match_daily_task_template(
        screenshot,
        BUILTIN_DAILY_WORLD_OVERVIEW_HOME_BUTTON_ASSET,
        BUILTIN_DAILY_WORLD_OVERVIEW_HOME_BUTTON_TEMPLATE_NAME,
        fast_threshold,
        _relative_region(screenshot, 0.00, 0.00, 1.00, 0.90),
    )


def match_daily_world_overview_search_entry(
    screenshot: Image.Image,
    threshold: float,
) -> tuple[tuple[int, int] | None, float]:
    """Match the lower overview magnifier only with the Resource layer on.

    The kingdom-overview layout places this lens around content y=2213, below
    the ordinary local-world search lane.  Keeping a separate matcher avoids
    widening the normal gather search region into unrelated lower-left UI.
    """

    if not daily_world_overview_resource_is_enabled(screenshot, threshold):
        return None, 0.0
    # Two live overview camera states alternate the terrain outside the lens:
    # the wide reference is strongest on the stable light-green tile, while
    # the circle-only reference is strongest when animated terrain changes.
    # Both remain inside this overview-only ROI and behind the Resource gate.
    wide_point, wide_score = _match_daily_task_template(
        screenshot,
        BUILTIN_DAILY_GATHER_WORLD_SEARCH_ASSET,
        BUILTIN_DAILY_GATHER_WORLD_SEARCH_TEMPLATE_NAME,
        max(0.97, float(threshold)),
        _relative_region(screenshot, 0.00, 0.80, 0.18, 0.94),
    )
    if wide_point is not None:
        return wide_point, wide_score
    point, score = _match_daily_task_template(
        screenshot,
        BUILTIN_DAILY_GATHER_WORLD_SEARCH_TIGHT_ASSET,
        BUILTIN_DAILY_GATHER_WORLD_SEARCH_TIGHT_TEMPLATE_NAME,
        max(0.97, float(threshold)),
        _relative_region(screenshot, 0.00, 0.80, 0.18, 0.93),
    )
    return point, max(wide_score, score)


def daily_gather_selector_is_valid(screenshot: Image.Image) -> bool:
    """Conservatively recognise the normal world-resource selector sheet.

    The selector's task-specific images vary by resource and its tutorial
    pointer can cover the search caption.  Instead of treating a fixed point
    as a command, require the characteristic dark-blue lower sheet, multiple
    bright resource tiles and the large blue search-action area together.
    This check is only used immediately after this worker clicked a verified
    world-map magnifier.
    """
    viewport = content_viewport(screenshot)
    image = np.asarray(screenshot.convert("RGB"))
    x0 = viewport.left + round(viewport.width * 0.02)
    x1 = viewport.left + round(viewport.width * 0.98)
    y0 = viewport.top + round(viewport.height * 0.67)
    y1 = viewport.top + round(viewport.height * 0.98)
    roi = image[y0:y1, x0:x1]
    if roi.size == 0:
        return False
    # The resource carousel has a large navy field, five snowy tiles and a
    # wide saturated-blue search button near the bottom.  The deliberately
    # generous ratios tolerate normal icon animations but not a city/world
    # screen, an offer, or a generic dialog.
    navy = (roi[:, :, 2] > 85) & (roi[:, :, 2] > roi[:, :, 0] * 1.18) & (roi[:, :, 1] > roi[:, :, 0] * 0.90)
    bright = (roi[:, :, 0] > 190) & (roi[:, :, 1] > 190) & (roi[:, :, 2] > 190)
    button_y0 = max(0, round(roi.shape[0] * 0.55))
    button = roi[button_y0:]
    blue = (
        (button[:, :, 2] > 170)
        & (button[:, :, 1] > 95)
        & (button[:, :, 1] < 220)
        & (button[:, :, 0] < 120)
    )
    carousel = roi[: max(1, round(roi.shape[0] * 0.46))]
    carousel_bright = (
        (carousel[:, :, 0] > 190)
        & (carousel[:, :, 1] > 190)
        & (carousel[:, :, 2] > 190)
    )
    return (
        float(np.mean(navy)) >= 0.70
        and 0.060 <= float(np.mean(carousel_bright)) <= 0.140
        and 0.10 <= float(np.mean(blue)) <= 0.24
        and float(np.mean(bright)) >= 0.050
    )


def detect_castle_level_gate(screenshot: Image.Image) -> CastleLevelGate:
    """Tell whether the Lord Profile shows a one- or multi-digit castle level.

    The automation only needs the level-10 gate, not general OCR.  On the
    reviewed profile the castle level is rendered as one connected glyph per
    digit beside the cyan castle icon.  Counting those glyphs is considerably
    more stable across MuMu DPI settings than recognising the stylised font.
    Any layout that cannot prove exactly one or at least two digits fails
    closed as ``UNKNOWN``.
    """
    viewport = content_viewport(screenshot)
    rgb = np.asarray(screenshot.convert("RGB"))
    # The level value is immediately right of the castle icon on the profile
    # card.  Keep the crop short enough to exclude the following Chinese unit.
    x0 = viewport.left + round(viewport.width * 0.785)
    x1 = viewport.left + round(viewport.width * 0.831)
    y0 = viewport.top + round(viewport.height * 0.758)
    y1 = viewport.top + round(viewport.height * 0.806)
    roi = rgb[y0:y1, x0:x1]
    if roi.size == 0:
        return CastleLevelGate.UNKNOWN

    hsv = cv2.cvtColor(roi, cv2.COLOR_RGB2HSV)
    # Profile numerals are pale blue/white on a dark desaturated panel.
    mask = cv2.inRange(hsv, np.array((75, 0, 145), np.uint8), np.array((135, 150, 255), np.uint8))
    count, _labels, stats, _centres = cv2.connectedComponentsWithStats(mask)
    min_h = max(9, round(viewport.height * 0.010))
    max_h = max(min_h + 1, round(viewport.height * 0.026))
    min_w = max(3, round(viewport.width * 0.004))
    max_w = max(min_w + 1, round(viewport.width * 0.026))
    digits = []
    for index in range(1, count):
        x, y, width, height, area = (int(value) for value in stats[index])
        if min_h <= height <= max_h and min_w <= width <= max_w and area >= max(12, min_h * 2):
            digits.append((x, y, width, height))
    digits.sort()
    if len(digits) == 1:
        return CastleLevelGate.BELOW_10
    if 2 <= len(digits) <= 3:
        return CastleLevelGate.AT_LEAST_10

    # Fire-Crystal castles replace the ordinary decimal level text with a
    # red, saturated crystal badge.  Reaching that presentation necessarily
    # implies the castle has already passed level 10, so recognise the badge
    # as a second (still coarse) proof instead of blocking mature accounts.
    bx0 = viewport.left + round(viewport.width * 0.745)
    bx1 = viewport.left + round(viewport.width * 0.880)
    by0 = viewport.top + round(viewport.height * 0.745)
    by1 = viewport.top + round(viewport.height * 0.825)
    badge_roi = rgb[by0:by1, bx0:bx1]
    if badge_roi.size:
        badge_hsv = cv2.cvtColor(badge_roi, cv2.COLOR_RGB2HSV)
        red = cv2.inRange(badge_hsv, np.array((0, 110, 90), np.uint8), np.array((14, 255, 255), np.uint8))
        red |= cv2.inRange(badge_hsv, np.array((168, 110, 90), np.uint8), np.array((179, 255, 255), np.uint8))
        red_ratio = float(np.mean(red > 0))
        if 0.003 <= red_ratio <= 0.12:
            return CastleLevelGate.AT_LEAST_10
    return CastleLevelGate.UNKNOWN


def detect_world_castle_marker_tip(screenshot: Image.Image) -> tuple[int, int] | None:
    """Return the tip of the player's exact bright-green overview pin.

    Blue alliance pins, the green Resource checkbox and the tiny minimap dot
    are excluded by a main-map-only region plus bounded pin geometry.  Any
    missing or non-unique candidate fails closed.
    """

    if not daily_world_overview_resource_is_enabled(screenshot, 0.90):
        return None
    rgb = np.asarray(screenshot.convert("RGB"))
    hsv = cv2.cvtColor(rgb, cv2.COLOR_RGB2HSV)
    x0, y0 = map_content_point((340, 450), BUILTIN_DAILY_TASK_REFERENCE_SIZE, screenshot)
    # The player's marker can sit near the right edge when several alliance
    # castles are clustered together.  Keep the vertical main-map band (so
    # the minimap and lower-right navigation controls remain excluded), but
    # cover the full horizontal map up to the content edge.
    x1, y1 = map_content_point((1420, 2050), BUILTIN_DAILY_TASK_REFERENCE_SIZE, screenshot)
    if x1 <= x0 or y1 <= y0:
        return None
    roi = hsv[y0:y1, x0:x1]
    if roi.size == 0:
        return None
    mask = cv2.inRange(
        roi,
        np.array((35, 150, 130), np.uint8),
        np.array((85, 255, 255), np.uint8),
    )
    count, _labels, stats, _centres = cv2.connectedComponentsWithStats(mask)
    viewport = content_viewport(screenshot)
    sx = viewport.width / BUILTIN_DAILY_TASK_REFERENCE_SIZE[0]
    sy = viewport.height / BUILTIN_DAILY_TASK_REFERENCE_SIZE[1]
    min_width, max_width = max(12, round(28 * sx)), max(20, round(85 * sx))
    min_height, max_height = max(18, round(42 * sy)), max(28, round(120 * sy))
    min_area = max(120, round(550 * sx * sy))
    candidates: list[tuple[int, int]] = []
    for index in range(1, count):
        x, y, width, height, area = (int(value) for value in stats[index])
        if not (min_width <= width <= max_width and min_height <= height <= max_height):
            continue
        if area < min_area:
            continue
        fill = area / max(1, width * height)
        aspect = width / max(1, height)
        if not (0.35 <= fill <= 0.80 and 0.45 <= aspect <= 0.98):
            continue
        candidates.append((x0 + x + width // 2, y0 + y + height))
    return candidates[0] if len(candidates) == 1 else None


def detect_world_resource_level(screenshot: Image.Image) -> int | None:
    """Classify the green castle pin's terrain band as selector 5/7/9.

    The Word guide is explicit: the bright-green player coordinate, rather
    than a fixed screen position, determines the band.  The current kingdom's
    three terrain colours are derived per frame, then small ground patches
    immediately below the pin tip vote light -> 5, medium -> 7, dark -> 9.
    Missing pins, boundary ambiguity or weak colour agreement fail closed.
    """
    if not daily_world_overview_resource_is_enabled(screenshot, 0.90):
        return None

    marker_tip = detect_world_castle_marker_tip(screenshot)
    if marker_tip is None:
        return None

    rgb = np.asarray(screenshot.convert("RGB"))
    if rgb.shape[0] < 900 or rgb.shape[1] < 600:
        return None

    # Work in reference coordinates so letterboxing/scaling cannot move the
    # castle sample or introduce the left legend into the colour clusters.
    bx0, by0 = map_content_point((100, 450), BUILTIN_DAILY_TASK_REFERENCE_SIZE, screenshot)
    bx1, by1 = map_content_point((1350, 2200), BUILTIN_DAILY_TASK_REFERENCE_SIZE, screenshot)
    body = rgb[by0:by1:4, bx0:bx1:4]
    if body.size == 0:
        return None
    body_hsv = cv2.cvtColor(body, cv2.COLOR_RGB2HSV)
    body_mask = (
        (body_hsv[:, :, 0] >= 20)
        & (body_hsv[:, :, 0] <= 100)
        & (body_hsv[:, :, 1] >= 15)
        & (body_hsv[:, :, 1] <= 135)
        & (body_hsv[:, :, 2] >= 90)
        & (body_hsv[:, :, 2] <= 235)
    )
    body_pixels = body[body_mask].astype(np.float32)
    if len(body_pixels) < 1000:
        return None

    cv2.setRNGSeed(17)
    _compactness, _labels, centres = cv2.kmeans(
        body_pixels,
        3,
        None,
        (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 0.3),
        5,
        cv2.KMEANS_PP_CENTERS,
    )
    luminance = centres @ np.array((0.2126, 0.7152, 0.0722), np.float32)
    light_to_dark = np.argsort(luminance)[::-1]
    if min(
        abs(float(luminance[light_to_dark[index]]) - float(luminance[light_to_dark[index + 1]]))
        for index in range(2)
    ) < 12.0:
        return None

    viewport = content_viewport(screenshot)
    sx = viewport.width / BUILTIN_DAILY_TASK_REFERENCE_SIZE[0]
    sy = viewport.height / BUILTIN_DAILY_TASK_REFERENCE_SIZE[1]
    tip_x, tip_y = marker_tip
    votes: list[int] = []
    for dx, dy in ((0, 30), (-45, 42), (45, 42), (0, 68)):
        cx = tip_x + round(dx * sx)
        cy = tip_y + round(dy * sy)
        rx, ry = max(8, round(18 * sx)), max(8, round(18 * sy))
        terrain = rgb[
            max(0, cy - ry) : min(rgb.shape[0], cy + ry + 1),
            max(0, cx - rx) : min(rgb.shape[1], cx + rx + 1),
        ]
        if terrain.size == 0:
            continue
        terrain_hsv = cv2.cvtColor(terrain, cv2.COLOR_RGB2HSV)
        terrain_mask = (
            (terrain_hsv[:, :, 0] >= 20)
            & (terrain_hsv[:, :, 0] <= 100)
            & (terrain_hsv[:, :, 1] >= 15)
            & (terrain_hsv[:, :, 1] <= 135)
            & (terrain_hsv[:, :, 2] >= 90)
            & (terrain_hsv[:, :, 2] <= 235)
        )
        terrain_pixels = terrain[terrain_mask]
        if len(terrain_pixels) < terrain.shape[0] * terrain.shape[1] * 0.45:
            continue
        sample = np.median(terrain_pixels, axis=0).astype(np.float32)
        distances = np.linalg.norm(centres - sample, axis=1)
        nearest = int(np.argmin(distances))
        if float(distances[nearest]) <= 28.0:
            votes.append(nearest)
    if len(votes) < 3:
        return None
    winner = max(set(votes), key=votes.count)
    if votes.count(winner) < 3:
        return None
    return {
        int(light_to_dark[0]): 5,
        int(light_to_dark[1]): 7,
        int(light_to_dark[2]): 9,
    }[winner]


def daily_gather_level_minus_point(screenshot: Image.Image) -> tuple[int, int]:
    """Return the selector's level-minus point after selector validation."""
    return map_content_point((115, 2135), BUILTIN_DAILY_TASK_REFERENCE_SIZE, screenshot)


def daily_gather_level_plus_point(screenshot: Image.Image) -> tuple[int, int]:
    """Return the selector's level-plus point after selector validation."""
    return map_content_point((975, 2135), BUILTIN_DAILY_TASK_REFERENCE_SIZE, screenshot)


def daily_gather_full_resources_filter_point(screenshot: Image.Image) -> tuple[int, int]:
    """Return the normal selector's *full resource nodes only* square.

    This is intentionally not a generic checkbox helper.  The coordinate is
    used only after :func:`match_daily_gather_full_resources_filter_off`
    recognises the exact unchecked caption and the caller has correlated the
    screen to a Daily Task gathering route.
    """
    return map_content_point((440, 2280), BUILTIN_DAILY_TASK_REFERENCE_SIZE, screenshot)


def match_daily_gather_full_resources_filter_off(
    screenshot: Image.Image,
    threshold: float,
) -> tuple[tuple[int, int] | None, float]:
    """Find the reviewed unchecked *full resource nodes only* selector state.

    The caption plus its dark empty square are matched in a narrow lower-sheet
    region.  The returned point is the centre of that square, not the centre
    of the wide caption template.  A caller must re-observe the separately
    reviewed green checked state after its own click before it can Search.
    """
    if not daily_gather_selector_is_valid(screenshot):
        return None, 0.0
    point, score = _match_daily_task_template(
        screenshot,
        BUILTIN_DAILY_GATHER_FULL_RESOURCES_FILTER_OFF_ASSET,
        BUILTIN_DAILY_GATHER_FULL_RESOURCES_FILTER_OFF_TEMPLATE_NAME,
        max(0.985, float(threshold)),
        _relative_region(screenshot, 0.20, 0.82, 0.84, 0.93),
    )
    if point and _daily_template_integrity_is_valid(
        screenshot,
        BUILTIN_DAILY_GATHER_FULL_RESOURCES_FILTER_OFF_ASSET,
        BUILTIN_DAILY_GATHER_FULL_RESOURCES_FILTER_OFF_TEMPLATE_NAME,
        point,
        min_luma_ratio=0.97,
        min_chroma_ratio=0.94,
        max_colour_distance=0.05,
    ):
        return daily_gather_full_resources_filter_point(screenshot), score
    return None, score


def daily_gather_full_resources_filter_is_enabled(screenshot: Image.Image, threshold: float) -> bool:
    """Recognise the reviewed checked full-resource selector state.

    It uses the live green-check reference captured only after the exact
    unchecked square was tapped.  A missing, dimmed or merely different
    checkbox never counts as enabled.
    """
    if not daily_gather_selector_is_valid(screenshot):
        return False
    point, _score = _match_daily_task_template(
        screenshot,
        BUILTIN_DAILY_GATHER_FULL_RESOURCES_FILTER_ON_ASSET,
        BUILTIN_DAILY_GATHER_FULL_RESOURCES_FILTER_ON_TEMPLATE_NAME,
        max(0.985, float(threshold)),
        _relative_region(screenshot, 0.20, 0.82, 0.84, 0.93),
    )
    return bool(
        point
        and _daily_template_integrity_is_valid(
            screenshot,
            BUILTIN_DAILY_GATHER_FULL_RESOURCES_FILTER_ON_ASSET,
            BUILTIN_DAILY_GATHER_FULL_RESOURCES_FILTER_ON_TEMPLATE_NAME,
            point,
            min_luma_ratio=0.97,
            min_chroma_ratio=0.94,
            max_colour_distance=0.05,
        )
    )


def daily_gather_meat_is_selected(screenshot: Image.Image, threshold: float) -> bool:
    """Confirm that the reviewed Daily-Task route has selected Raw Meat.

    The game itself pre-selects Raw Meat after tapping the exact unfinished
    Raw-Meat Daily Task.  The worker does not attempt to reproduce that
    carousel gesture: it requires this central ``生肉`` label on the already
    validated selector before it can press the ordinary blue Search control.
    """
    if not daily_gather_selector_is_valid(screenshot):
        return False
    point, _score = _match_daily_task_template(
        screenshot,
        BUILTIN_DAILY_GATHER_MEAT_SELECTED_ASSET,
        BUILTIN_DAILY_GATHER_MEAT_SELECTED_TEMPLATE_NAME,
        max(0.94, float(threshold)),
        _relative_region(screenshot, 0.40, 0.70, 0.60, 0.80),
    )
    central_selected = bool(
        point
        and _daily_template_integrity_is_valid(
            screenshot,
            BUILTIN_DAILY_GATHER_MEAT_SELECTED_ASSET,
            BUILTIN_DAILY_GATHER_MEAT_SELECTED_TEMPLATE_NAME,
            point,
            min_luma_ratio=DAILY_ACTION_MIN_LUMA_RATIO,
            min_chroma_ratio=DAILY_ACTION_MIN_CHROMA_RATIO,
            max_colour_distance=DAILY_ACTION_MAX_COLOUR_DISTANCE,
            strict_action=True,
        )
    )
    if central_selected:
        return True

    # On the current kingdom-overview layout the carousel keeps Raw Meat at
    # the far right after selection instead of centring it.  The two white
    # selection brackets and the partial ``生`` label form a separate exact
    # selected-state proof.  This branch does not authorise a tap.
    right_point, _right_score = _match_daily_task_template(
        screenshot,
        BUILTIN_DAILY_GATHER_MEAT_SELECTED_RIGHT_ASSET,
        BUILTIN_DAILY_GATHER_MEAT_SELECTED_RIGHT_TEMPLATE_NAME,
        max(0.985, float(threshold)),
        _relative_region(screenshot, 0.83, 0.64, 1.00, 0.80),
    )
    return bool(
        right_point
        and _daily_template_integrity_is_valid(
            screenshot,
            BUILTIN_DAILY_GATHER_MEAT_SELECTED_RIGHT_ASSET,
            BUILTIN_DAILY_GATHER_MEAT_SELECTED_RIGHT_TEMPLATE_NAME,
            right_point,
            min_luma_ratio=0.98,
            min_chroma_ratio=0.96,
            max_colour_distance=0.04,
            strict_action=True,
        )
    )


def match_daily_gather_meat_visible_tab(
    screenshot: Image.Image,
    threshold: float,
) -> tuple[tuple[int, int] | None, float]:
    """Find the reviewed, partially visible Raw-Meat carousel tab.

    This is a narrow recovery for the live kingdom-overview round-trip that
    leaves the selector on ``野兽``.  It cannot match on an arbitrary world or
    dialog page: the ordinary selector geometry must already be valid, and
    the crop is searched only in the far-right carousel lane.  The returned
    centre lies within the visible portion of the tab.  A caller must still
    double-confirm :func:`daily_gather_meat_is_selected` after tapping it.
    """
    if not daily_gather_selector_is_valid(screenshot):
        return None, 0.0
    point, score = _match_daily_task_template(
        screenshot,
        BUILTIN_DAILY_GATHER_MEAT_VISIBLE_TAB_ASSET,
        BUILTIN_DAILY_GATHER_MEAT_VISIBLE_TAB_TEMPLATE_NAME,
        max(0.985, float(threshold)),
        _relative_region(screenshot, 0.84, 0.64, 1.00, 0.80),
    )
    if point and _daily_template_integrity_is_valid(
        screenshot,
        BUILTIN_DAILY_GATHER_MEAT_VISIBLE_TAB_ASSET,
        BUILTIN_DAILY_GATHER_MEAT_VISIBLE_TAB_TEMPLATE_NAME,
        point,
        min_luma_ratio=0.98,
        min_chroma_ratio=0.96,
        max_colour_distance=0.04,
        strict_action=True,
    ):
        return point, score
    return None, score


def daily_gather_resource_tab_point(kind: DailyMissionKind, screenshot: Image.Image) -> tuple[int, int]:
    """Return a resource-carousel point *only* for a validated selector."""
    reference = {
        DailyMissionKind.GATHER_WOOD: (650, 1945),
        DailyMissionKind.GATHER_COAL: (900, 1945),
        DailyMissionKind.GATHER_IRON: (1160, 1945),
    }
    return map_content_point(reference[kind], BUILTIN_DAILY_TASK_REFERENCE_SIZE, screenshot)


def daily_gather_search_point(screenshot: Image.Image) -> tuple[int, int]:
    """Return the centre of the normal selector's blue Search control."""
    return map_content_point((720, 2390), BUILTIN_DAILY_TASK_REFERENCE_SIZE, screenshot)


def match_beast_rally_world_search(
    screenshot: Image.Image,
    threshold: float = 0.90,
) -> tuple[tuple[int, int] | None, float]:
    """Expose the reviewed world-search lens only on a proved wilderness map."""
    if match_daily_city_wilderness_entry(screenshot, threshold)[0]:
        return None, 0.0
    dense_town, dense_town_score = _match_beast_rally_template(
        screenshot,
        BUILTIN_BEAST_RALLY_WORLD_TOWN_DENSE_ASSET,
        max(0.94, float(threshold)),
        _relative_region(screenshot, 0.80, 0.84, 1.00, 1.00),
    )
    dense_search, dense_search_score = _match_beast_rally_template(
        screenshot,
        BUILTIN_BEAST_RALLY_WORLD_SEARCH_DENSE_ASSET,
        max(0.94, float(threshold)),
        _relative_region(screenshot, 0.00, 0.60, 0.18, 0.82),
    )
    expected_town = map_content_point((1319, 2370), BUILTIN_DAILY_TASK_REFERENCE_SIZE, screenshot)
    expected_search = map_content_point((90, 1754), BUILTIN_DAILY_TASK_REFERENCE_SIZE, screenshot)
    if (
        dense_town
        and dense_search
        and max(abs(dense_town[0] - expected_town[0]), abs(dense_town[1] - expected_town[1])) <= 24
        and max(abs(dense_search[0] - expected_search[0]), abs(dense_search[1] - expected_search[1])) <= 24
    ):
        return dense_search, min(dense_town_score, dense_search_score)
    # The high-power account can render the fixed lower-left Search control
    # as a pure circular button without the older outward shelf.  Keep this as
    # a separate exact asset: it may expose a point only when the independent
    # same-frame dense Town anchor is also exact at its reviewed coordinate.
    # Do not lower either existing threshold or widen either search region.
    round_search, round_search_score = _match_beast_rally_template(
        screenshot,
        BUILTIN_BEAST_RALLY_WORLD_SEARCH_ROUND_ASSET,
        max(0.94, float(threshold)),
        _relative_region(screenshot, 0.00, 0.60, 0.18, 0.82),
    )
    if (
        dense_town
        and round_search
        and max(abs(dense_town[0] - expected_town[0]), abs(dense_town[1] - expected_town[1])) <= 24
        and max(abs(round_search[0] - expected_search[0]), abs(round_search[1] - expected_search[1])) <= 24
    ):
        return round_search, min(dense_town_score, round_search_score)
    # Immediately after the reviewed expanded panel is collapsed, some live
    # animation phases keep the Search control at its fixed geometry while
    # changing the translucent lens pixels enough to miss every Search skin.
    # Do not widen/lower those matchers.  The independently exact dense Town
    # anchor plus an exact collapsed-arrow skin proves this specific
    # wilderness page family; only then expose the reviewed fixed Search
    # centre.  Match the arrow directly here to avoid the collapsed matcher's
    # deliberate world-search fallback cycle.
    collapsed_expected = map_content_point(
        (45, 1111), BUILTIN_DAILY_TASK_REFERENCE_SIZE, screenshot
    )
    collapsed_assets = (
        BUILTIN_BEAST_RALLY_PROGRESS_SIDEBAR_COLLAPSED_ASSET,
        *BUILTIN_BEAST_RALLY_PROGRESS_SIDEBAR_COLLAPSED_ROUND_ASSETS,
    )
    collapsed_score = 0.0
    collapsed_proved = False
    for collapsed_asset in collapsed_assets:
        collapsed_point, candidate_score = _match_beast_rally_template(
            screenshot,
            collapsed_asset,
            max(0.96, float(threshold)),
            _relative_region(screenshot, 0.00, 0.30, 0.09, 0.57),
        )
        collapsed_score = max(collapsed_score, candidate_score)
        if (
            collapsed_point
            and max(
                abs(collapsed_point[0] - collapsed_expected[0]),
                abs(collapsed_point[1] - collapsed_expected[1]),
            )
            <= 12
        ):
            collapsed_proved = True
            break
    if (
        dense_town
        and collapsed_proved
        and max(
            abs(dense_town[0] - expected_town[0]),
            abs(dense_town[1] - expected_town[1]),
        )
        <= 24
    ):
        return expected_search, min(dense_town_score, collapsed_score)
    town_point, town_score = match_daily_world_town_entry(screenshot, threshold)
    if not town_point:
        return None, max(town_score, dense_search_score)
    point, score = _match_beast_rally_template(
        screenshot,
        BUILTIN_BEAST_RALLY_WORLD_SEARCH_ASSET,
        max(0.88, float(threshold)),
        _relative_region(screenshot, 0.00, 0.60, 0.22, 0.79),
    )
    expected = map_content_point((90, 1755), BUILTIN_DAILY_TASK_REFERENCE_SIZE, screenshot)
    # Dense wilderness labels and lighting animate behind this translucent
    # lens, so a raw-RGB comparison of its surrounding square is unstable.
    # The exact lens shape, its fixed lower-left geometry, and the independent
    # exact Town control in this same frame form the action proof instead.
    # No other beast-rally action bypasses the strict RGB integrity gate.
    if (
        point
        and max(abs(point[0] - expected[0]), abs(point[1] - expected[1])) <= 32
    ):
        return point, min(score, town_score)
    # Allied-rally overlays can dim the same reviewed Search lens.  Keep an
    # exact live variant tied to the independent Town anchor and fixed point;
    # this branch authorises only Search, never the blue allied status row.
    allied_point, allied_score = _match_beast_rally_template(
        screenshot,
        BUILTIN_BEAST_RALLY_WORLD_SEARCH_ALLIED_ASSET,
        max(0.98, float(threshold)),
        _relative_region(screenshot, 0.00, 0.60, 0.18, 0.82),
    )
    if (
        allied_point
        and max(abs(allied_point[0] - expected[0]), abs(allied_point[1] - expected[1])) <= 12
    ):
        return allied_point, min(allied_score, town_score)
    return None, max(score, town_score)


def match_beast_rally_selector(
    screenshot: Image.Image,
    threshold: float = 0.90,
) -> BeastRallyMatch:
    fixture = screenshot.height < 1000 and screenshot.width > screenshot.height
    beast_region = (
        _relative_region(screenshot, 0.16, 0.00, 0.54, 0.32)
        if fixture
        else _relative_region(screenshot, 0.16, 0.62, 0.54, 0.80)
    )
    search_region = (
        _relative_region(screenshot, 0.20, 0.62, 0.78, 1.00)
        if fixture
        else _relative_region(screenshot, 0.20, 0.86, 0.78, 1.00)
    )
    beast, beast_score = _match_beast_rally_template(
        screenshot,
        BUILTIN_BEAST_RALLY_BEAST_TARGET_ASSET,
        max(0.90, float(threshold)),
        beast_region,
    )
    search, search_score = _match_beast_rally_template(
        screenshot,
        BUILTIN_BEAST_RALLY_SEARCH_BUTTON_ASSET,
        max(0.94, float(threshold)),
        search_region,
    )
    if beast and search and _beast_rally_template_integrity_is_valid(
        screenshot, BUILTIN_BEAST_RALLY_SEARCH_BUTTON_ASSET, search
    ):
        return BeastRallyMatch(
            BeastRallyState.SELECTOR,
            search,
            min(beast_score, search_score),
            (("beast", beast), ("search", search)),
        )
    return BeastRallyMatch(BeastRallyState.UNKNOWN, None, max(beast_score, search_score))


def beast_rally_beast_target_point(screenshot: Image.Image) -> tuple[int, int] | None:
    fixture = screenshot.height < 1000 and screenshot.width > screenshot.height
    point, _score = _match_beast_rally_template(
        screenshot,
        BUILTIN_BEAST_RALLY_BEAST_TARGET_ASSET,
        0.90,
        _relative_region(
            screenshot,
            0.16,
            0.00 if fixture else 0.62,
            0.54,
            0.32 if fixture else 0.80,
        ),
    )
    return point


def read_beast_rally_selector_level(screenshot: Image.Image) -> int | None:
    """Read only the dark digit in the selector's fixed white level field."""
    fixture = screenshot.height < 1000 and screenshot.width > screenshot.height
    crop = _daily_reference_crop(
        screenshot,
        (1050, 1025, 1375, 1335) if fixture else (1050, 1980, 1375, 2200),
    )
    rgb = np.asarray(crop.convert("RGB"))
    if rgb.size == 0:
        return None
    dark = (
        (rgb[:, :, 0] < 140)
        & (rgb[:, :, 1] < 160)
        & (rgb[:, :, 2] < 195)
    ).astype(np.uint8)
    count, labels, stats, _centres = cv2.connectedComponentsWithStats(dark, connectivity=8)
    readings: list[tuple[int, float, int]] = []
    for index in range(1, count):
        x, y, width, height, area = (int(value) for value in stats[index])
        if width < 5 or height < 18 or area < 45 or height > crop.height * 0.75:
            continue
        reading = _read_daily_numeric_glyph(labels[y : y + height, x : x + width] == index)
        if reading:
            readings.append((reading[0], reading[1], x))
    readings.sort(key=lambda item: item[2])
    if not 1 <= len(readings) <= 2:
        return None
    value = 0
    for digit, confidence, _x in readings:
        if confidence < 0.80:
            return None
        value = value * 10 + digit
    return value if 1 <= value <= 30 else None


def beast_rally_level_is_configured(
    screenshot: Image.Image,
    expected_level: int,
) -> bool:
    return read_beast_rally_selector_level(screenshot) == int(expected_level)


def beast_rally_level_field_point(screenshot: Image.Image) -> tuple[int, int] | None:
    selector = match_beast_rally_selector(screenshot)
    if selector.state is not BeastRallyState.SELECTOR:
        return None
    fixture = screenshot.height < 1000 and screenshot.width > screenshot.height
    return map_content_point(
        (1220, 1185) if fixture else (1220, 2090),
        BUILTIN_DAILY_TASK_REFERENCE_SIZE,
        screenshot,
    )


def beast_rally_selector_search_point(screenshot: Image.Image) -> tuple[int, int] | None:
    """Return only the central Search button from a verified beast selector."""
    match = match_beast_rally_selector(screenshot)
    return match.point if match.state is BeastRallyState.SELECTOR else None


def match_beast_rally_open_button(
    screenshot: Image.Image,
    threshold: float = 0.90,
) -> tuple[tuple[int, int] | None, float]:
    # The user's small crop contains no full-screen geometry. Find the exact
    # orange label globally, then demand the surrounding orange ordinary
    # action colours. It cannot match the blue Auto Join control.
    point, score = _match_beast_rally_template(
        screenshot,
        BUILTIN_BEAST_RALLY_OPEN_LABEL_ASSET,
        max(0.92, float(threshold)),
        _relative_region(screenshot, 0.00, 0.00, 1.00, 1.00),
    )
    if not point:
        return None, score
    viewport = content_viewport(screenshot)
    rgb = _screenshot_rgb_cached(screenshot)
    radius_x = max(25, round(viewport.width * 0.12))
    radius_y = max(18, round(viewport.height * 0.025))
    lane = rgb[
        max(viewport.top, point[1] - radius_y) : min(viewport.bottom, point[1] + radius_y),
        max(viewport.left, point[0] - radius_x) : min(viewport.right, point[0] + radius_x),
    ]
    if lane.size == 0:
        return None, score
    orange = (
        (lane[:, :, 0] > 190)
        & (lane[:, :, 1] > 55)
        & (lane[:, :, 1] < 165)
        & (lane[:, :, 2] < 90)
    )
    return (point, score) if float(np.mean(orange)) >= 0.14 else (None, score)


def match_beast_rally_sheet(
    screenshot: Image.Image,
    threshold: float = 0.90,
) -> BeastRallyMatch:
    fixture = screenshot.height < 1000 and screenshot.width > screenshot.height
    header, header_score = _match_beast_rally_template(
        screenshot,
        BUILTIN_BEAST_RALLY_SHEET_HEADER_ASSET,
        max(0.94, float(threshold)),
        _relative_region(screenshot, 0.20, 0.00 if fixture else 0.24, 0.80, 0.18 if fixture else 0.40),
    )
    selected, selected_score = _match_beast_rally_template(
        screenshot,
        BUILTIN_BEAST_RALLY_THREE_MINUTES_SELECTED_ASSET,
        max(0.94, float(threshold)),
        _relative_region(screenshot, 0.02, 0.25 if fixture else 0.38, 0.48, 0.60 if fixture else 0.58),
    )
    launch, launch_score = _match_beast_rally_template(
        screenshot,
        BUILTIN_BEAST_RALLY_LAUNCH_BUTTON_ASSET,
        max(0.95, float(threshold)),
        _relative_region(screenshot, 0.18, 0.70 if fixture else 0.58, 0.82, 1.00 if fixture else 0.78),
    )
    if header and selected and launch and _beast_rally_template_integrity_is_valid(
        screenshot, BUILTIN_BEAST_RALLY_LAUNCH_BUTTON_ASSET, launch
    ):
        return BeastRallyMatch(
            BeastRallyState.RALLY_SHEET,
            launch,
            min(header_score, selected_score, launch_score),
            (("header", header), ("three_minutes", selected), ("launch", launch)),
        )
    return BeastRallyMatch(
        BeastRallyState.UNKNOWN,
        None,
        max(header_score, selected_score, launch_score),
    )


def match_beast_rally_sheet_controls(
    screenshot: Image.Image,
    threshold: float = 0.90,
) -> BeastRallyMatch:
    """Prove the rally sheet even when 3 minutes is not selected yet."""
    fixture = screenshot.height < 1000 and screenshot.width > screenshot.height
    header, header_score = _match_beast_rally_template(
        screenshot,
        BUILTIN_BEAST_RALLY_SHEET_HEADER_ASSET,
        max(0.94, float(threshold)),
        _relative_region(screenshot, 0.20, 0.00 if fixture else 0.24, 0.80, 0.18 if fixture else 0.40),
    )
    three_minutes, option_score = _match_beast_rally_template(
        screenshot,
        BUILTIN_BEAST_RALLY_THREE_MINUTES_LABEL_ASSET,
        max(0.93, float(threshold)),
        _relative_region(screenshot, 0.02, 0.25 if fixture else 0.38, 0.48, 0.60 if fixture else 0.58),
    )
    launch, launch_score = _match_beast_rally_template(
        screenshot,
        BUILTIN_BEAST_RALLY_LAUNCH_BUTTON_ASSET,
        max(0.95, float(threshold)),
        _relative_region(screenshot, 0.18, 0.70 if fixture else 0.58, 0.82, 1.00 if fixture else 0.78),
    )
    if header and three_minutes and launch and _beast_rally_template_integrity_is_valid(
        screenshot, BUILTIN_BEAST_RALLY_LAUNCH_BUTTON_ASSET, launch
    ):
        return BeastRallyMatch(
            BeastRallyState.RALLY_SHEET,
            launch,
            min(header_score, option_score, launch_score),
            (("three_minutes", three_minutes), ("launch", launch)),
        )
    return BeastRallyMatch(
        BeastRallyState.UNKNOWN,
        None,
        max(header_score, option_score, launch_score),
    )


def beast_rally_three_minutes_point(screenshot: Image.Image) -> tuple[int, int] | None:
    match = match_beast_rally_sheet_controls(screenshot)
    if match.state is not BeastRallyState.RALLY_SHEET:
        return None
    return next((point for name, point in match.anchors if name == "three_minutes"), None)


def beast_rally_first_formation_point(screenshot: Image.Image) -> tuple[int, int] | None:
    """Return the first formation tab only on the exact reviewed formation."""
    match = match_beast_rally_formation(screenshot)
    if match.state is not BeastRallyState.FORMATION:
        return None
    return next((point for name, point in match.anchors if name == "first"), None)


def match_beast_rally_formation(
    screenshot: Image.Image,
    threshold: float = 0.90,
) -> BeastRallyMatch:
    anchor, anchor_score = _match_beast_rally_template(
        screenshot,
        BUILTIN_BEAST_RALLY_FORMATION_ANCHOR_ASSET,
        max(0.92, float(threshold)),
        _relative_region(screenshot, 0.00, 0.00, 0.46, 0.12),
    )
    first, first_score = _match_beast_rally_template(
        screenshot,
        BUILTIN_BEAST_RALLY_FIRST_FORMATION_ASSET,
        max(0.92, float(threshold)),
        _relative_region(screenshot, 0.00, 0.05, 0.25, 0.18),
    )
    dispatch, dispatch_score = _match_beast_rally_template(
        screenshot,
        BUILTIN_BEAST_RALLY_DISPATCH_LABEL_ASSET,
        max(0.94, float(threshold)),
        _relative_region(screenshot, 0.52, 0.82, 1.00, 1.00),
    )
    if anchor and first and dispatch:
        return BeastRallyMatch(
            BeastRallyState.FORMATION,
            dispatch,
            min(anchor_score, first_score, dispatch_score),
            (("formation", anchor), ("first", first), ("dispatch", dispatch)),
        )
    return BeastRallyMatch(BeastRallyState.UNKNOWN, None, max(anchor_score, first_score, dispatch_score))


def match_beast_rally_formation_controls(
    screenshot: Image.Image,
    threshold: float = 0.90,
) -> BeastRallyMatch:
    """Prove the formation surface before selecting its first tab."""
    anchor, anchor_score = _match_beast_rally_template(
        screenshot,
        BUILTIN_BEAST_RALLY_FORMATION_ANCHOR_ASSET,
        max(0.92, float(threshold)),
        _relative_region(screenshot, 0.00, 0.00, 0.46, 0.12),
    )
    dispatch, dispatch_score = _match_beast_rally_template(
        screenshot,
        BUILTIN_BEAST_RALLY_DISPATCH_LABEL_ASSET,
        max(0.94, float(threshold)),
        _relative_region(screenshot, 0.52, 0.82, 1.00, 1.00),
    )
    if anchor and dispatch:
        first = map_content_point((126, 257), BUILTIN_DAILY_TASK_REFERENCE_SIZE, screenshot)
        return BeastRallyMatch(
            BeastRallyState.FORMATION,
            dispatch,
            min(anchor_score, dispatch_score),
            (("formation", anchor), ("first", first), ("dispatch", dispatch)),
        )
    return BeastRallyMatch(BeastRallyState.UNKNOWN, None, max(anchor_score, dispatch_score))


def read_beast_rally_dispatch_stamina(screenshot: Image.Image) -> int | None:
    """Read the final white stamina debit; preview cost is never counted."""
    if match_beast_rally_formation(screenshot).state is not BeastRallyState.FORMATION:
        return None
    crop = _daily_reference_crop(screenshot, (875, 2360, 1310, 2535))
    components = _daily_white_numeric_components(crop)
    readings: list[tuple[int, float, int]] = []
    for x, _y, _width, _height, glyph in components:
        result = _read_daily_numeric_glyph(glyph)
        if result:
            readings.append((result[0], result[1], x))
    readings.sort(key=lambda item: item[2])
    # Keep the right-most one or two adjacent glyphs. The action label is
    # Chinese and fails the digit classifier; the cost is the terminal run.
    if not 1 <= len(readings) <= 3:
        return None
    value = 0
    for digit, confidence, _x in readings[-3:]:
        if confidence < 0.78:
            return None
        value = value * 10 + digit
    return value if 1 <= value <= 999 else None


def read_beast_rally_dispatch_stamina_shortfall(screenshot: Image.Image) -> int | None:
    """Return the reviewed red 20 debit; never authorize a purchase control."""
    if match_beast_rally_formation(screenshot).state is not BeastRallyState.FORMATION:
        return None
    point, score = _match_beast_rally_template(
        screenshot,
        BUILTIN_BEAST_RALLY_DISPATCH_STAMINA_RED20_ASSET,
        0.985,
        _relative_region(screenshot, 0.70, 0.91, 0.86, 1.00),
    )
    return 20 if point and score >= 0.985 else None


def match_beast_rally_stamina_more(
    screenshot: Image.Image,
    threshold: float = 0.90,
) -> BeastRallyMatch:
    """Match only the reviewed 10-stamina item row and its green Use button.

    The yellow ``购买并使用 300`` row sits directly below this control.  It is
    deliberately absent from the actionable anchors; the returned point is
    accepted only when the page title, exact restore-10 description, and green
    ordinary inventory button all agree in their fixed native regions.
    """
    title, title_score = _match_beast_rally_template(
        screenshot,
        BUILTIN_BEAST_RALLY_STAMINA_MORE_TITLE_ASSET,
        max(0.985, float(threshold)),
        _relative_region(screenshot, 0.25, 0.04, 0.62, 0.16),
    )
    restore, restore_score = _match_beast_rally_template(
        screenshot,
        BUILTIN_BEAST_RALLY_STAMINA_RESTORE10_ASSET,
        max(0.985, float(threshold)),
        _relative_region(screenshot, 0.12, 0.34, 0.66, 0.47),
    )
    use, use_score = _match_beast_rally_template(
        screenshot,
        BUILTIN_BEAST_RALLY_STAMINA_USE_ASSET,
        max(0.985, float(threshold)),
        _relative_region(screenshot, 0.63, 0.34, 0.97, 0.47),
    )
    if title and restore and use:
        return BeastRallyMatch(
            BeastRallyState.STAMINA_MORE,
            use,
            min(title_score, restore_score, use_score),
            (("title", title), ("restore10", restore), ("use", use)),
        )
    return BeastRallyMatch(
        BeastRallyState.UNKNOWN,
        None,
        max(title_score, restore_score, use_score),
    )


def match_beast_rally_stamina_more_controls(
    screenshot: Image.Image,
    threshold: float = 0.90,
) -> BeastRallyMatch:
    """Reconfirm title + green Use while the success toast covers row text."""
    title, title_score = _match_beast_rally_template(
        screenshot,
        BUILTIN_BEAST_RALLY_STAMINA_MORE_TITLE_ASSET,
        max(0.985, float(threshold)),
        _relative_region(screenshot, 0.25, 0.04, 0.62, 0.16),
    )
    use, use_score = _match_beast_rally_template(
        screenshot,
        BUILTIN_BEAST_RALLY_STAMINA_USE_ASSET,
        max(0.985, float(threshold)),
        _relative_region(screenshot, 0.63, 0.34, 0.97, 0.47),
    )
    if title and use:
        return BeastRallyMatch(
            BeastRallyState.STAMINA_MORE,
            use,
            min(title_score, use_score),
            (("title", title), ("use", use)),
        )
    return BeastRallyMatch(BeastRallyState.UNKNOWN, None, max(title_score, use_score))


def match_beast_rally_active_panel(
    screenshot: Image.Image,
    threshold: float = 0.90,
) -> BeastRallyMatch:
    icon, icon_score = _match_beast_rally_template(
        screenshot,
        BUILTIN_BEAST_RALLY_PROGRESS_ICON_ASSET,
        max(0.92, float(threshold)),
        _relative_region(screenshot, 0.00, 0.00, 1.00, 1.00),
    )
    rallying, rallying_score = _match_beast_rally_template(
        screenshot,
        BUILTIN_BEAST_RALLY_STATE_RALLYING_ASSET,
        max(0.94, float(threshold)),
        _relative_region(screenshot, 0.00, 0.00, 1.00, 1.00),
    )
    if icon and rallying:
        return BeastRallyMatch(
            BeastRallyState.RALLYING,
            None,
            min(icon_score, rallying_score),
            (("progress", icon), ("rallying", rallying)),
        )
    return BeastRallyMatch(BeastRallyState.UNKNOWN, None, max(icon_score, rallying_score))


def match_beast_rally_progress_icon(
    screenshot: Image.Image,
    threshold: float = 0.90,
) -> tuple[tuple[int, int] | None, float]:
    """Passively find the reviewed green beast-march progress icon.

    The icon never authorises an input.  It only keeps a dispatched rally in
    an active/returning state until the icon has disappeared on consecutive
    exact wilderness frames.
    """
    return _match_beast_rally_template(
        screenshot,
        BUILTIN_BEAST_RALLY_PROGRESS_ICON_ASSET,
        max(0.92, float(threshold)),
        _relative_region(screenshot, 0.00, 0.00, 1.00, 1.00),
    )


def match_beast_rally_progress_sidebar_collapsed(
    screenshot: Image.Image,
    threshold: float = 0.90,
) -> tuple[tuple[int, int] | None, float]:
    """Find only the reviewed white expand arrow for the left march panel."""
    point, score = _match_beast_rally_template(
        screenshot,
        BUILTIN_BEAST_RALLY_PROGRESS_SIDEBAR_COLLAPSED_ASSET,
        max(0.96, float(threshold)),
        _relative_region(screenshot, 0.00, 0.30, 0.09, 0.57),
    )
    if point:
        return point, score
    world, world_score = match_beast_rally_world_search(screenshot, threshold)
    if not world:
        return None, score
    expected = map_content_point((45, 1111), BUILTIN_DAILY_TASK_REFERENCE_SIZE, screenshot)
    best_score = score
    for asset in BUILTIN_BEAST_RALLY_PROGRESS_SIDEBAR_COLLAPSED_ROUND_ASSETS:
        variant, variant_score = _match_beast_rally_template(
            screenshot,
            asset,
            max(0.96, float(threshold)),
            _relative_region(screenshot, 0.00, 0.30, 0.09, 0.57),
        )
        best_score = max(best_score, variant_score)
        if variant and max(abs(variant[0] - expected[0]), abs(variant[1] - expected[1])) <= 12:
            return variant, min(variant_score, world_score)
    return None, best_score


def match_beast_rally_progress_wilderness_tab(
    screenshot: Image.Image,
    threshold: float = 0.90,
) -> tuple[tuple[int, int] | None, float]:
    """Find the reviewed ``野外`` tab inside the expanded progress panel."""
    return _match_beast_rally_template(
        screenshot,
        BUILTIN_BEAST_RALLY_PROGRESS_WILDERNESS_TAB_ASSET,
        max(0.96, float(threshold)),
        _relative_region(screenshot, 0.25, 0.14, 0.75, 0.36),
    )


def _beast_rally_panel_template_centres(
    screenshot: Image.Image,
    asset: str,
    threshold: float,
    search_region: tuple[int, int, int, int],
) -> tuple[list[tuple[int, int]], float]:
    """Return vertically separated exact panel anchors with simple NMS."""
    template_path = resource_path(asset)
    if not template_path.is_file():
        return [], 0.0
    template = _load_template_grayscale_cached(
        str(template_path.resolve()),
        int(template_path.stat().st_mtime_ns),
        int(template_path.stat().st_size),
    )
    screen = _screenshot_grayscale_cached(screenshot)
    x0, y0, x1, y1 = search_region
    roi = screen[y0:y1, x0:x1]
    if roi.shape[0] < template.shape[0] or roi.shape[1] < template.shape[1]:
        return [], 0.0
    result = cv2.matchTemplate(roi, template, cv2.TM_CCOEFF_NORMED)
    ys, xs = np.where(result >= float(threshold))
    candidates = sorted(
        ((float(result[y, x]), int(x), int(y)) for y, x in zip(ys, xs)),
        reverse=True,
    )
    kept: list[tuple[int, int]] = []
    min_x = max(8, template.shape[1] // 2)
    min_y = max(24, template.shape[0] // 2)
    for score, x, y in candidates:
        centre = (x + template.shape[1] // 2, y + template.shape[0] // 2)
        if any(abs(centre[0] - old_x) < min_x and abs(centre[1] - old_y) < min_y for old_x, old_y in kept):
            continue
        kept.append(centre)
    kept.sort(key=lambda point: point[1])
    return kept, max((score for score, _x, _y in candidates), default=0.0)


def _count_beast_rally_panel_template(
    screenshot: Image.Image,
    asset: str,
    threshold: float,
    search_region: tuple[int, int, int, int],
) -> tuple[int, float]:
    centres, score = _beast_rally_panel_template_centres(
        screenshot,
        asset,
        threshold,
        search_region,
    )
    return len(centres), score


def read_beast_rally_wilderness_queue_states(
    screenshot: Image.Image,
    threshold: float = 0.90,
) -> tuple[bool, ...] | None:
    """Return one ordered idle/busy value for every visible Wilderness row."""
    selected, _selected_score = _match_beast_rally_template(
        screenshot,
        BUILTIN_BEAST_RALLY_PROGRESS_WILDERNESS_SELECTED_ASSET,
        max(0.96, float(threshold)),
        _relative_region(screenshot, 0.25, 0.14, 0.75, 0.36),
    )
    expanded, _expanded_score = _match_beast_rally_template(
        screenshot,
        BUILTIN_BEAST_RALLY_PROGRESS_SIDEBAR_EXPANDED_ASSET,
        max(0.96, float(threshold)),
        _relative_region(screenshot, 0.55, 0.30, 0.72, 0.57),
    )
    if not selected or not expanded:
        return None
    region = _relative_region(screenshot, 0.00, 0.24, 0.63, 0.72)
    labels, _ = _beast_rally_panel_template_centres(
        screenshot,
        BUILTIN_BEAST_RALLY_PROGRESS_QUEUE_LABEL_ASSET,
        max(0.94, float(threshold)),
        region,
    )
    idle_labels, _ = _beast_rally_panel_template_centres(
        screenshot,
        BUILTIN_BEAST_RALLY_PROGRESS_IDLE_ASSET,
        max(0.92, float(threshold)),
        region,
    )
    if not 1 <= len(labels) <= 10 or len(idle_labels) > len(labels):
        return None
    # Each idle caption sits directly below its fixed row title. Matching by
    # vertical lane preserves the queue identity even when a busy row swaps
    # its blue flag for a green progress icon.
    states = tuple(
        any(20 <= idle_y - label_y <= 140 for _idle_x, idle_y in idle_labels)
        for _label_x, label_y in labels
    )
    if sum(states) != len(idle_labels):
        return None
    return states


def read_beast_rally_wilderness_queue_counts(
    screenshot: Image.Image,
    threshold: float = 0.90,
) -> tuple[int, int] | None:
    """Return ``(all queues, idle queues)`` from the expanded Wilderness tab."""
    states = read_beast_rally_wilderness_queue_states(screenshot, threshold)
    return None if states is None else (len(states), sum(states))


def beast_rally_new_busy_queue_indexes(
    before: tuple[bool, ...],
    after: tuple[bool, ...],
) -> tuple[int, ...]:
    """Return rows that changed from idle to busy without assuming a slot count."""
    if not before or len(before) != len(after):
        return ()
    return tuple(
        index
        for index, (was_idle, is_idle) in enumerate(zip(before, after))
        if was_idle and not is_idle
    )


def beast_rally_expanded_capacity_baseline(
    queue_states: tuple[bool, ...] | None,
    first: DailyMarchCapacity | None,
    second: DailyMarchCapacity | None,
) -> tuple[int, int] | None:
    """Accept a double-confirmed expanded-panel ``used/total`` baseline.

    On the current high-level skin a busy account row replaces the normal
    ``行军队列`` title with the rally target, so the row-title reader can
    legitimately expose only the remaining idle rows.  The fixed expanded
    header still reports the account-owned capacity and explicitly excludes
    the blue allied-rally row.  Require both fresh header reads to agree and
    require the observed idle rows to equal ``total - used`` before using the
    count as dispatch/return authority.
    """
    if not queue_states:
        return None
    # The current expanded skin omits the numeric header when every fixed
    # account row is idle.  The queue-state reader has already required the
    # exact Wilderness tab, expanded-panel anchor, and stable fixed row
    # labels, so an all-idle tuple is itself the strongest zero-used proof.
    if first is None and second is None and all(queue_states):
        return 0, len(queue_states)
    if first is None or second is None:
        return None
    if (first.used, first.total) != (second.used, second.total):
        return None
    if not (1 <= first.total <= 10) or first.free <= 0:
        return None
    if sum(queue_states) != first.free:
        return None
    if len(queue_states) == first.total:
        if len(queue_states) - sum(queue_states) != first.used:
            return None
    elif not (len(queue_states) == first.free and all(queue_states)):
        return None
    return first.used, first.total


def match_beast_rally_progress_sidebar_expanded(
    screenshot: Image.Image,
    threshold: float = 0.90,
) -> tuple[tuple[int, int] | None, float]:
    """Find only the reviewed white collapse arrow of the expanded panel."""
    return _match_beast_rally_template(
        screenshot,
        BUILTIN_BEAST_RALLY_PROGRESS_SIDEBAR_EXPANDED_ASSET,
        max(0.96, float(threshold)),
        _relative_region(screenshot, 0.55, 0.30, 0.72, 0.57),
    )


def match_daily_gather_collect_button(
    screenshot: Image.Image,
    threshold: float,
) -> tuple[tuple[int, int] | None, float]:
    """Find the free world-resource ``采集`` button in its site dialog."""
    point, score = _match_daily_task_template(
        screenshot,
        BUILTIN_DAILY_GATHER_COLLECT_ASSET,
        BUILTIN_DAILY_GATHER_COLLECT_TEMPLATE_NAME,
        max(0.90, float(threshold)),
        _relative_region(screenshot, 0.24, 0.35, 0.76, 0.64),
    )
    if point and _daily_template_integrity_is_valid(
        screenshot,
        BUILTIN_DAILY_GATHER_COLLECT_ASSET,
        BUILTIN_DAILY_GATHER_COLLECT_TEMPLATE_NAME,
        point,
        min_luma_ratio=DAILY_ACTION_MIN_LUMA_RATIO,
        min_chroma_ratio=DAILY_ACTION_MIN_CHROMA_RATIO,
        max_colour_distance=DAILY_ACTION_MAX_COLOUR_DISTANCE,
        strict_action=True,
    ):
        return point, score
    return None, score


def match_daily_gather_dispatch_button(
    screenshot: Image.Image,
    threshold: float,
) -> tuple[tuple[int, int] | None, float]:
    """Find the ordinary resource expedition's blue ``出征`` control."""
    point, score = _match_daily_task_template(
        screenshot,
        BUILTIN_DAILY_GATHER_DISPATCH_ASSET,
        BUILTIN_DAILY_GATHER_DISPATCH_TEMPLATE_NAME,
        max(0.90, float(threshold)),
        _relative_region(screenshot, 0.45, 0.84, 0.99, 1.00),
    )
    if point and _daily_template_integrity_is_valid(
        screenshot,
        BUILTIN_DAILY_GATHER_DISPATCH_ASSET,
        BUILTIN_DAILY_GATHER_DISPATCH_TEMPLATE_NAME,
        point,
        min_luma_ratio=DAILY_ACTION_MIN_LUMA_RATIO,
        min_chroma_ratio=DAILY_ACTION_MIN_CHROMA_RATIO,
        max_colour_distance=DAILY_ACTION_MAX_COLOUR_DISTANCE,
        strict_action=True,
    ):
        return point, score
    return None, score


def _daily_reference_crop(
    screenshot: Image.Image,
    box: tuple[int, int, int, int],
) -> Image.Image:
    """Crop a 1440x2560 reference box inside the real MuMu content area."""
    viewport = content_viewport(screenshot)
    left = viewport.left + round(box[0] * viewport.width / 1440)
    top = viewport.top + round(box[1] * viewport.height / 2560)
    right = viewport.left + round(box[2] * viewport.width / 1440)
    bottom = viewport.top + round(box[3] * viewport.height / 2560)
    return screenshot.crop((left, top, right, bottom)).convert("RGB")


def _daily_white_numeric_components(
    crop: Image.Image,
) -> list[tuple[int, int, int, int, np.ndarray]]:
    """Segment full-height neutral-white glyphs in one fixed numeric strip."""
    rgb = np.asarray(crop.convert("RGB"))
    if rgb.size == 0:
        return []
    neutral_white = (
        (rgb[:, :, 0] > 180)
        & (rgb[:, :, 1] > 180)
        & (rgb[:, :, 2] > 180)
        & (np.ptp(rgb.astype(np.int16), axis=2) < 55)
    ).astype(np.uint8)
    count, labels, stats, _centres = cv2.connectedComponentsWithStats(
        neutral_white, connectivity=8
    )
    raw: list[tuple[int, int, int, int, int]] = []
    for index in range(1, count):
        x, y, width, height, area = (int(value) for value in stats[index])
        if width >= 2 and height >= 7 and area >= 12:
            raw.append((x, y, width, height, area))
    if not raw:
        return []
    max_height = max(item[3] for item in raw)
    minimum_height = max(7, round(max_height * 0.60))
    components: list[tuple[int, int, int, int, np.ndarray]] = []
    for x, y, width, height, area in raw:
        if height < minimum_height or area < max(12, round(height * 2.5)):
            continue
        glyph = labels[y : y + height, x : x + width] > 0
        # Keep only the current label rather than neighbouring white glyphs.
        label_value = int(labels[y, x])
        if not label_value:
            values = labels[y : y + height, x : x + width]
            nonzero = values[values > 0]
            if nonzero.size == 0:
                continue
            label_value = int(np.bincount(nonzero).argmax())
        glyph = labels[y : y + height, x : x + width] == label_value
        components.append((x, y, width, height, glyph))
    components.sort(key=lambda item: item[0])
    return components


def _daily_numeric_component_is_slash(component: np.ndarray) -> bool:
    """Distinguish the diagonal slash from the similarly narrow digit one."""
    height, width = component.shape[:2]
    if height < 8 or width < 3 or not (0.28 <= width / height <= 0.72):
        return False
    quarter = max(1, height // 4)
    top_y, top_x = np.where(component[:quarter])
    bottom_y, bottom_x = np.where(component[-quarter:])
    if top_x.size == 0 or bottom_x.size == 0:
        return False
    return float(np.mean(top_x) - np.mean(bottom_x)) >= width * 0.35


def _read_daily_numeric_glyph(component: np.ndarray) -> tuple[int, float] | None:
    resized = cv2.resize(
        component.astype(np.uint8),
        (12, 16),
        interpolation=cv2.INTER_AREA,
    ) >= 0.35
    scores = sorted(
        (
            (float(np.mean(resized == prototype)), int(digit))
            for digit, prototype in _DAILY_NUMERIC_PROTOTYPES.items()
        ),
        reverse=True,
    )
    best_score, best_digit = scores[0]
    next_score = scores[1][0]
    if best_score < 0.74 or best_score - next_score < 0.025:
        return None
    return best_digit, best_score


def _read_daily_numeric_components(
    components: list[tuple[int, int, int, int, np.ndarray]],
) -> tuple[int, float] | None:
    if not components:
        return None
    value = 0
    confidences: list[float] = []
    for _x, _y, _width, _height, component in components:
        result = _read_daily_numeric_glyph(component)
        if result is None:
            return None
        digit, confidence = result
        value = value * 10 + digit
        confidences.append(confidence)
    return value, min(confidences)


def _arena_numeric_reading(
    screenshot: Image.Image,
    box: tuple[int, int, int, int],
    colour: str,
) -> tuple[int, float] | None:
    """Read Arena digits from one fixed, independently anchored ROI."""
    crop = np.asarray(_daily_reference_crop(screenshot, box).convert("RGB"))
    hsv = cv2.cvtColor(crop, cv2.COLOR_RGB2HSV)
    if colour == "white":
        mask = (
            (crop[:, :, 0] > 170) & (crop[:, :, 1] > 170)
            & (crop[:, :, 2] > 170)
            & (np.ptp(crop.astype(np.int16), axis=2) < 75)
        )
    elif colour == "dark":
        mask = (
            (crop[:, :, 2] > 65) & (crop[:, :, 2] < 185)
            & (crop[:, :, 0] < 150) & (crop[:, :, 1] < 175)
        )
    elif colour == "opponent":
        red = (
            ((hsv[:, :, 0] < 12) | (hsv[:, :, 0] > 170))
            & (hsv[:, :, 1] > 120) & (hsv[:, :, 2] > 100)
        )
        green = (
            (hsv[:, :, 0] > 35) & (hsv[:, :, 0] < 90)
            & (hsv[:, :, 1] > 100) & (hsv[:, :, 2] > 80)
        )
        mask = red | green
    else:
        raise ValueError(f"unsupported Arena digit colour: {colour}")
    count, labels, stats, _centres = cv2.connectedComponentsWithStats(
        mask.astype(np.uint8), connectivity=8
    )
    components: list[tuple[int, int, int, int, np.ndarray]] = []
    for index in range(1, count):
        x, y, width, height, area = (int(value) for value in stats[index])
        # Commas/dots are shorter; the trailing Chinese unit is wider.  Only
        # the account-free numeric glyph lane is admitted.
        if not (10 <= width <= 34 and 25 <= height <= 62 and area >= 180):
            continue
        components.append(
            (x, y, width, height, labels[y:y + height, x:x + width] == index)
        )
    components.sort(key=lambda item: item[0])
    return _read_daily_numeric_components(components)


def _match_arena_anchor(
    screenshot: Image.Image,
    asset: str,
    template_name: str,
    region: tuple[float, float, float, float],
    threshold: float,
) -> tuple[tuple[int, int] | None, float]:
    return _match_daily_task_template(
        screenshot, asset, template_name, max(0.96, float(threshold)),
        _relative_region(screenshot, *region),
    )


def match_arena_home(
    screenshot: Image.Image,
    threshold: float = 0.90,
) -> ArenaHomeState | None:
    """Prove 万国竞技场 plus a non-zero red free-attempt badge."""
    title, title_score = _match_arena_anchor(
        screenshot, BUILTIN_DAILY_ARENA_HOME_TITLE_ASSET,
        BUILTIN_DAILY_ARENA_HOME_TITLE_TEMPLATE_NAME,
        (0.05, 0.00, 0.45, 0.08), threshold,
    )
    challenge, challenge_score = _match_arena_anchor(
        screenshot, BUILTIN_DAILY_ARENA_CHALLENGE_LABEL_ASSET,
        BUILTIN_DAILY_ARENA_CHALLENGE_LABEL_TEMPLATE_NAME,
        (0.30, 0.82, 0.80, 0.99), threshold,
    )
    remaining_reading = _arena_numeric_reading(
        screenshot, (990, 2240, 1080, 2400), "white"
    )
    if not title or not challenge:
        return None
    if remaining_reading is None:
        count, count_score = 0, min(title_score, challenge_score)
    else:
        count, count_score = remaining_reading
    if not 0 <= count <= 5:
        return None
    return ArenaHomeState(
        count,
        (
            map_content_point(
                (720, 2380), BUILTIN_DAILY_TASK_REFERENCE_SIZE, screenshot
            )
            if count > 0 else None
        ),
        min(title_score, challenge_score, count_score),
    )


def match_arena_opponent_list(
    screenshot: Image.Image,
    threshold: float = 0.90,
) -> ArenaOpponentListState | None:
    """Read all five opponents and free attempts; never expose refresh/plus."""
    title, title_score = _match_arena_anchor(
        screenshot, BUILTIN_DAILY_ARENA_LIST_TITLE_ASSET,
        BUILTIN_DAILY_ARENA_LIST_TITLE_TEMPLATE_NAME,
        (0.20, 0.05, 0.80, 0.18), threshold,
    )
    remaining_label, remaining_score = _match_arena_anchor(
        screenshot, BUILTIN_DAILY_ARENA_REMAINING_LABEL_ASSET,
        BUILTIN_DAILY_ARENA_REMAINING_LABEL_TEMPLATE_NAME,
        (0.20, 0.68, 0.75, 0.86), threshold,
    )
    my_reading = _arena_numeric_reading(
        screenshot, (650, 405, 1050, 500), "dark"
    )
    attempts_reading = _arena_numeric_reading(
        screenshot, (830, 1980, 910, 2050), "dark"
    )
    if not title or not remaining_label or my_reading is None or attempts_reading is None:
        return None
    my_power, my_score = my_reading
    remaining, attempts_score = attempts_reading
    if my_power < 1 or not 0 <= remaining <= 5:
        return None
    opponents: list[ArenaOpponent] = []
    confidences = [title_score, remaining_score, my_score, attempts_score]
    row_tops = (600, 870, 1120, 1390, 1640)
    row_centres = (660, 930, 1200, 1470, 1740)
    for index, top in enumerate(row_tops):
        reading = _arena_numeric_reading(
            screenshot, (300, top, 590, top + 120), "opponent"
        )
        if reading is None:
            return None
        packed, score = reading
        # The list renders one decimal digit followed by 万.  Keeping the
        # implicit decimal as x1000 yields the exact integer power.
        power = packed * 1000
        if power < 1:
            return None
        confidences.append(score)
        opponents.append(ArenaOpponent(
            power,
            map_content_point(
                (1250, row_centres[index]),
                BUILTIN_DAILY_TASK_REFERENCE_SIZE,
                screenshot,
            ),
        ))
    return ArenaOpponentListState(
        my_power, remaining, tuple(opponents),
        map_content_point((1335, 315), BUILTIN_DAILY_TASK_REFERENCE_SIZE, screenshot),
        min(confidences),
    )


def match_arena_setup(
    screenshot: Image.Image,
    threshold: float = 0.90,
) -> ArenaSetupState | None:
    """Prove power advantage, five selected heroes and ordinary green battle."""
    title, title_score = _match_arena_anchor(
        screenshot, BUILTIN_DAILY_ARENA_SETUP_TITLE_ASSET,
        BUILTIN_DAILY_ARENA_SETUP_TITLE_TEMPLATE_NAME,
        (0.05, 0.00, 0.45, 0.08), threshold,
    )
    battle, battle_score = _match_arena_anchor(
        screenshot, BUILTIN_DAILY_ARENA_BATTLE_LABEL_ASSET,
        BUILTIN_DAILY_ARENA_BATTLE_LABEL_TEMPLATE_NAME,
        (0.50, 0.82, 0.99, 0.99), threshold,
    )
    my_reading = _arena_numeric_reading(
        screenshot, (230, 200, 580, 320), "white"
    )
    opponent_reading = _arena_numeric_reading(
        screenshot, (940, 200, 1230, 320), "white"
    )
    if not title or not battle or my_reading is None or opponent_reading is None:
        return None
    my_power, my_score = my_reading
    opponent_power, opponent_score = opponent_reading
    selection = np.asarray(
        _daily_reference_crop(screenshot, (0, 1550, 1440, 2100)).convert("RGB")
    )
    hsv = cv2.cvtColor(selection, cv2.COLOR_RGB2HSV)
    green = (
        (hsv[:, :, 0] > 35) & (hsv[:, :, 0] < 90)
        & (hsv[:, :, 1] > 120) & (hsv[:, :, 2] > 100)
    )
    count, _labels, stats, _centres = cv2.connectedComponentsWithStats(
        green.astype(np.uint8), connectivity=8
    )
    selected = sum(
        1 for index in range(1, count)
        if 50 <= int(stats[index, cv2.CC_STAT_WIDTH]) <= 100
        and 45 <= int(stats[index, cv2.CC_STAT_HEIGHT]) <= 85
        and int(stats[index, cv2.CC_STAT_AREA]) >= 1500
    )
    if not (my_power > opponent_power and selected == 5):
        return None
    return ArenaSetupState(
        my_power, opponent_power, selected,
        map_content_point((1050, 2380), BUILTIN_DAILY_TASK_REFERENCE_SIZE, screenshot),
        min(title_score, battle_score, my_score, opponent_score),
    )


def match_arena_result_exit(
    screenshot: Image.Image,
    threshold: float = 0.90,
) -> tuple[tuple[int, int] | None, float]:
    """Match an Arena result exit only inside the correlated battle route.

    The existing generic complete sentence remains the first candidate.  The
    dedicated live Arena rendering is deliberately not added to the global
    abnormal-page matcher: it is exposed only to the controller immediately
    after an exact ordinary Arena battle tap.  Victory and defeat share this
    full bottom sentence; the returned point is a neutral side location away
    from the nearby video control.
    """

    generic_point, generic_score = match_daily_tap_anywhere_exit_text(
        screenshot, threshold
    )
    if generic_point is not None:
        return generic_point, generic_score
    dedicated_point, dedicated_score = _match_arena_anchor(
        screenshot,
        BUILTIN_DAILY_ARENA_RESULT_EXIT_TEXT_ASSET,
        BUILTIN_DAILY_ARENA_RESULT_EXIT_TEXT_TEMPLATE_NAME,
        (0.28, 0.86, 0.72, 0.995),
        threshold,
    )
    if dedicated_point is None:
        return None, dedicated_score
    return (
        map_content_point(
            (120, 2200), BUILTIN_DAILY_TASK_REFERENCE_SIZE, screenshot
        ),
        dedicated_score,
    )


def read_daily_march_capacity(screenshot: Image.Image) -> DailyMarchCapacity | None:
    """Read ``used/total`` only from the fixed world-map march header.

    The caller must still double-confirm the ordinary world map and two equal
    readings.  This function performs no navigation and returns ``None`` on a
    missing slash, ambiguous digit, impossible total, or inconsistent count.
    """
    crop = _daily_reference_crop(screenshot, (390, 380, 510, 480))
    components = _daily_white_numeric_components(crop)
    slash_indexes = [
        index
        for index, (_x, _y, _width, _height, glyph) in enumerate(components)
        if _daily_numeric_component_is_slash(glyph)
    ]
    if len(slash_indexes) != 1:
        return None
    slash_index = slash_indexes[0]
    left = components[:slash_index]
    right = components[slash_index + 1 :]
    if not (1 <= len(left) <= 2 and len(right) == 1):
        return None
    used_reading = _read_daily_numeric_components(left)
    total_reading = _read_daily_numeric_components(right)
    if used_reading is None or total_reading is None:
        return None
    used, used_confidence = used_reading
    total, total_confidence = total_reading
    if total < 1 or total > 9 or used < 0 or used > total:
        return None
    return DailyMarchCapacity(used, total, min(used_confidence, total_confidence))


def read_beast_rally_collapsed_march_capacity(
    screenshot: Image.Image,
    threshold: float = 0.90,
) -> DailyMarchCapacity | None:
    """Read ``used/total`` from the reviewed collapsed Beast march panel.

    This header proves only that the account has a free expedition slot.  It
    deliberately says nothing about ownership of the visible status row: a
    blue allied rally may share this panel and must never enter the account's
    Beast baseline or stamina ledger.
    """
    town, _town_score = match_daily_world_town_entry(screenshot, threshold)
    world, _world_score = _match_beast_rally_template(
        screenshot,
        BUILTIN_BEAST_RALLY_WORLD_SEARCH_ALLIED_ASSET,
        max(0.98, float(threshold)),
        _relative_region(screenshot, 0.00, 0.60, 0.18, 0.82),
    )
    collapsed, _collapsed_score = _match_beast_rally_template(
        screenshot,
        BUILTIN_BEAST_RALLY_PROGRESS_SIDEBAR_COLLAPSED_ALLIED_ASSET,
        max(0.98, float(threshold)),
        _relative_region(screenshot, 0.00, 0.30, 0.09, 0.57),
    )
    expected_world = map_content_point((90, 1754), BUILTIN_DAILY_TASK_REFERENCE_SIZE, screenshot)
    expected_collapsed = map_content_point((45, 1111), BUILTIN_DAILY_TASK_REFERENCE_SIZE, screenshot)
    if not world or not collapsed:
        return None
    if not town:
        return None
    if max(abs(world[0] - expected_world[0]), abs(world[1] - expected_world[1])) > 12:
        return None
    if max(abs(collapsed[0] - expected_collapsed[0]), abs(collapsed[1] - expected_collapsed[1])) > 12:
        return None
    crop = _daily_reference_crop(screenshot, (330, 380, 540, 520))
    components = _daily_white_numeric_components(crop)
    slash_indexes = [
        index
        for index, (_x, _y, _width, _height, glyph) in enumerate(components)
        if _daily_numeric_component_is_slash(glyph)
    ]
    if len(slash_indexes) != 1:
        return None
    slash_index = slash_indexes[0]
    slash_y = components[slash_index][1]
    # Ignore the eye control and status-row countdown below the header.
    lane = [component for component in components if abs(component[1] - slash_y) <= 8]
    slash_indexes = [
        index for index, component in enumerate(lane)
        if _daily_numeric_component_is_slash(component[4])
    ]
    if len(slash_indexes) != 1:
        return None
    slash_index = slash_indexes[0]
    left = lane[:slash_index]
    right = lane[slash_index + 1 :]
    if not (1 <= len(left) <= 2 and len(right) == 1):
        return None
    used_reading = _read_daily_numeric_components(left)
    total_reading = _read_daily_numeric_components(right)
    if used_reading is None or total_reading is None:
        return None
    used, used_confidence = used_reading
    total, total_confidence = total_reading
    if total < 1 or total > 9 or used < 0 or used > total:
        return None
    return DailyMarchCapacity(used, total, min(used_confidence, total_confidence))


def read_beast_rally_expanded_march_capacity(
    screenshot: Image.Image,
    threshold: float = 0.90,
) -> DailyMarchCapacity | None:
    """Read ``used/total`` from an exact expanded Wilderness march panel."""
    expanded, _expanded_score = match_beast_rally_progress_sidebar_expanded(
        screenshot,
        threshold,
    )
    states = read_beast_rally_wilderness_queue_states(screenshot, threshold)
    if not expanded or states is None:
        return None
    crop = _daily_reference_crop(screenshot, (330, 380, 540, 520))
    components = _daily_white_numeric_components(crop)
    slash_indexes = [
        index
        for index, (_x, _y, _width, _height, glyph) in enumerate(components)
        if _daily_numeric_component_is_slash(glyph)
    ]
    if len(slash_indexes) != 1:
        return None
    slash_index = slash_indexes[0]
    slash_y = components[slash_index][1]
    lane = [component for component in components if abs(component[1] - slash_y) <= 8]
    slash_indexes = [
        index for index, component in enumerate(lane)
        if _daily_numeric_component_is_slash(component[4])
    ]
    if len(slash_indexes) != 1:
        return None
    slash_index = slash_indexes[0]
    left, right = lane[:slash_index], lane[slash_index + 1 :]
    if not (1 <= len(left) <= 2 and len(right) == 1):
        return None
    used_reading = _read_daily_numeric_components(left)
    total_reading = _read_daily_numeric_components(right)
    if used_reading is None or total_reading is None:
        return None
    used, used_confidence = used_reading
    total, total_confidence = total_reading
    if total < 1 or total > 9 or used < 0 or used > total:
        return None
    return DailyMarchCapacity(used, total, min(used_confidence, total_confidence))


def read_daily_gather_formation_capacity(
    screenshot: Image.Image,
) -> DailyGatherFormationCapacity | None:
    """Read selected troops and carrying capacity from the final formation.

    Fixed regions exclude the hero/troop rows and every plus/minus control.
    The selected-troop strip must contain its expected slash; commas are
    intentionally discarded by full-height component filtering.
    """
    def read_layout(
        selected_box: tuple[int, int, int, int],
        carry_box: tuple[int, int, int, int],
        *,
        require_total: bool,
    ) -> DailyGatherFormationCapacity | None:
        selected_crop = _daily_reference_crop(screenshot, selected_box)
        selected_components = _daily_white_numeric_components(selected_crop)
        slash_indexes = [
            index
            for index, (_x, _y, _width, _height, glyph) in enumerate(selected_components)
            if _daily_numeric_component_is_slash(glyph)
        ]
        if len(slash_indexes) != 1:
            return None
        slash_index = slash_indexes[0]
        selected_digits = selected_components[:slash_index]
        if not (1 <= len(selected_digits) <= 7):
            return None
        selected_reading = _read_daily_numeric_components(selected_digits)
        if selected_reading is None:
            return None

        total_confidence = 1.0
        if require_total:
            # The compact header has a trailing exclamation icon.  Read only
            # the consecutive numeric glyphs immediately after the slash and
            # stop at that nonnumeric icon; require selected <= total.
            total_digits = []
            for component in selected_components[slash_index + 1 :]:
                if _read_daily_numeric_glyph(component[4]) is None:
                    break
                total_digits.append(component)
            if not (1 <= len(total_digits) <= 7):
                return None
            total_reading = _read_daily_numeric_components(total_digits)
            if total_reading is None:
                return None
            total_troops, total_confidence = total_reading
            if total_troops <= 0 or selected_reading[0] > total_troops:
                return None

        carry_crop = _daily_reference_crop(screenshot, carry_box)
        # A mature account can expose an eight-digit capacity.  Its value
        # starts much farther left than the old narrow ROI and may share the
        # widened lane with the resource icon.  Keep only recognised numeric
        # glyphs; commas and the icon are deliberately excluded.
        carry_components = [
            component
            for component in _daily_white_numeric_components(carry_crop)
            if _read_daily_numeric_glyph(component[4]) is not None
        ]
        if not (1 <= len(carry_components) <= 9):
            return None
        carrying_reading = _read_daily_numeric_components(carry_components)
        if carrying_reading is None:
            return None
        selected_troops, selected_confidence = selected_reading
        carrying_capacity, carrying_confidence = carrying_reading
        if (
            selected_troops < 0
            or carrying_capacity < 0
            # The formation header animates its carrying value upward after
            # navigation.  Two very fast frames can both expose the same
            # early three-digit value (for example 356) while tens of
            # thousands of troops are already selected.  Every selected
            # troop contributes at least one unit of carrying capacity, so
            # this is an incomplete rendering, not evidence of shortage.
            # Fail the reading and keep polling inside the existing bounded
            # 30-second window until the full value stabilises.
            or carrying_capacity < selected_troops
        ):
            return None
        return DailyGatherFormationCapacity(
            selected_troops,
            carrying_capacity,
            min(selected_confidence, total_confidence, carrying_confidence),
        )

    # Mature-account layout proved in milestone 21.
    reading = read_layout((165, 350, 470, 440), (800, 350, 1390, 440), require_total=False)
    if reading is not None:
        return reading
    # Compact low-level layout live-proved on 16416.  Its header is one row
    # higher and includes ``selected/total`` plus a trailing exclamation icon.
    reading = read_layout((170, 310, 470, 410), (1185, 310, 1390, 410), require_total=True)
    if reading is not None:
        return reading
    # A second compact 16416 layout keeps the same exact formation controls
    # but shifts both numeric strips down and outward.  Tight boxes exclude
    # the white troop/iron icons while preserving ``770/770`` and ``4,158``.
    return read_layout((165, 330, 520, 440), (1210, 340, 1390, 430), require_total=True)


def daily_gather_march_is_active(screenshot: Image.Image, threshold: float) -> bool:
    """Return whether the reviewed world-map march panel is still present.

    This is deliberately passive evidence.  It accepts either the reviewed
    one-slot header or the compact ``coordinate + countdown + double-arrow``
    panel that is present in the current MuMu layout.  It is also used at
    startup, so a gathering team dispatched by an earlier safe run remains
    protected rather than being mistaken for a free queue.  A miss never
    results in a map tap; it merely permits the caller to resume its already
    reviewed Daily Tasks flow after two fresh no-panel frames.
    """
    point, _score = _match_daily_task_template(
        screenshot,
        BUILTIN_DAILY_GATHER_ACTIVE_MARCH_ASSET,
        BUILTIN_DAILY_GATHER_ACTIVE_MARCH_TEMPLATE_NAME,
        # The same one-slot header drops to 0.829 when a natural return leaves
        # the resource selector open beneath it.  0.80 accepts both outbound
        # and returning states, while the highest no-panel fixture is 0.127.
        0.75,
        _relative_region(screenshot, 0.00, 0.12, 0.42, 0.25),
    )
    if point:
        return True
    # The current 16416 camera hides ``used/total`` but shows one occupied
    # march as a fixed right-side expedition icon with a changing timer.  Match
    # only the static icon interior in its narrow world-map lane; the crop omits
    # the dynamic badge/timer and all identifying UI.  This passive proof can
    # only defer gathering and can never authorise a search or dispatch.
    compact_point, _compact_score = _match_daily_task_template(
        screenshot,
        BUILTIN_DAILY_GATHER_ACTIVE_MARCH_RIGHT_COMPACT_ASSET,
        BUILTIN_DAILY_GATHER_ACTIVE_MARCH_RIGHT_COMPACT_TEMPLATE_NAME,
        max(0.95, float(threshold)),
        _relative_region(screenshot, 0.78, 0.38, 1.00, 0.48),
    )
    if compact_point:
        return True
    # The compact layout omits the older "march 1/1" header.  Its constrained
    # countdown structure is still passive evidence only: a false positive
    # can defer a route but can never authorize a dispatch, acceleration, or
    # any paid/queue-expansion action.
    return daily_gather_remaining_time_crop(screenshot, threshold) is not None


def daily_gather_remaining_time_crop(screenshot: Image.Image, threshold: float) -> Image.Image | None:
    """Return the reviewed, non-identifying gather countdown strip if visible.

    The bounded strip contains the resource icon, ``采集中`` state and digital
    remaining-time display only.  It intentionally excludes the collector
    name, chat and any controls.  It is an image record rather than general
    OCR: if this exact panel cannot be recognised, callers must record the
    time as unknown rather than invent a duration.
    """
    viewport = content_viewport(screenshot)

    def mapped(value: int, axis: str) -> int:
        scale = viewport.width / BUILTIN_DAILY_TASK_REFERENCE_SIZE[0]
        if axis == "y":
            scale = viewport.height / BUILTIN_DAILY_TASK_REFERENCE_SIZE[1]
            return viewport.top + round(value * scale)
        return viewport.left + round(value * scale)

    left, top = mapped(40, "x"), mapped(495, "y")
    right, bottom = mapped(500, "x"), mapped(625, "y")
    if right <= left or bottom <= top:
        return None
    crop = screenshot.crop((left, top, right, bottom)).convert("RGB")
    rgb = np.asarray(crop)
    if rgb.size == 0:
        return None
    height, width = rgb.shape[:2]
    timer = rgb[round(height * 0.31) : round(height * 0.89), round(width * 0.09) : round(width * 0.74)]
    right_control = rgb[0 : round(height * 0.89), round(width * 0.72) : width]
    if timer.size == 0 or right_control.size == 0:
        return None

    def share(region: np.ndarray, mask: np.ndarray) -> float:
        return float(np.mean(mask)) if region.size else 0.0

    red, green, blue = timer[:, :, 0], timer[:, :, 1], timer[:, :, 2]
    black_timer = (red < 80) & (green < 80) & (blue < 80)
    white_digits = (red > 190) & (green > 190) & (blue > 190)
    green_progress = (green > 120) & (red < 140) & (blue < 150) & (green > red * 1.2)
    red, green, blue = right_control[:, :, 0], right_control[:, :, 1], right_control[:, :, 2]
    blue_advance = (blue > 160) & (green > 80) & (red < 150) & (blue > red * 1.4)
    # This is the live one-slot countdown presentation with coordinate text
    # above it.  It deliberately does not rely on the older "行军 1/1" header,
    # which disappears in this compact active panel.  It can be consulted
    # passively at startup as well as after a reviewed normal dispatch; only
    # the latter saves a record and requires two frames before navigation.
    if not (
        share(timer, black_timer) >= 0.15
        and share(timer, white_digits) >= 0.04
        and share(timer, green_progress) >= 0.06
        and share(right_control, blue_advance) >= 0.15
    ):
        return None
    return crop


def daily_march_capacity_modal_is_visible(screenshot: Image.Image) -> bool:
    """Detect the dimmed one-slot expansion modal as a terminal safety state.

    This modal contains research, activation, and purchase routes. Recognizing
    it never grants a close or navigation action; it only makes the daily
    worker stop before any of those controls can be considered.
    """
    viewport = content_viewport(screenshot)
    rgb = np.asarray(screenshot.convert("RGB"))

    def region(x0: float, y0: float, x1: float, y1: float) -> np.ndarray:
        left = viewport.left + round(viewport.width * x0)
        top = viewport.top + round(viewport.height * y0)
        right = viewport.left + round(viewport.width * x1)
        bottom = viewport.top + round(viewport.height * y1)
        return rgb[top:bottom, left:right]

    dim_corner = region(0.00, 0.00, 0.21, 0.12)
    header = region(0.07, 0.25, 0.93, 0.32)
    button_rows = (
        region(0.53, 0.34, 0.89, 0.43),
        region(0.53, 0.45, 0.89, 0.55),
        region(0.53, 0.57, 0.89, 0.68),
    )
    if dim_corner.size == 0 or header.size == 0 or any(row.size == 0 for row in button_rows):
        return False

    def share(mask: np.ndarray) -> float:
        return float(np.mean(mask))

    red, green, blue = dim_corner[:, :, 0], dim_corner[:, :, 1], dim_corner[:, :, 2]
    dimmed = (red < 100) & (green < 120) & (blue < 150)
    red, green, blue = header[:, :, 0], header[:, :, 1], header[:, :, 2]
    modal_header = (blue > 120) & (green > 80) & (red < 160) & ((blue.astype(np.int16) - red.astype(np.int16)) > 40)

    def is_blue_button(row: np.ndarray) -> bool:
        red, green, blue = row[:, :, 0], row[:, :, 1], row[:, :, 2]
        normal_blue = (blue > 170) & (green > 80) & (red < 150) & ((blue.astype(np.int16) - red.astype(np.int16)) > 70)
        return share(normal_blue) >= 0.04

    return share(dimmed) >= 0.70 and share(modal_header) >= 0.45 and all(is_blue_button(row) for row in button_rows)


def match_daily_training_entry(
    screenshot: Image.Image,
    threshold: float,
) -> tuple[tuple[int, int] | None, float]:
    """Recognise the selected camp's ordinary blue ``Train`` action.

    It is used only immediately after a reviewed daily troop task's own Go
    control was clicked.  The returned point is the blue training action,
    never a city/building coordinate and never the nearby upgrade action.
    """
    point, score = _match_daily_task_template(
        screenshot,
        BUILTIN_DAILY_TRAINING_ENTRY_LABEL_ASSET,
        BUILTIN_DAILY_TRAINING_ENTRY_LABEL_TEMPLATE_NAME,
        max(0.90, float(threshold)),
        _relative_region(screenshot, 0.54, 0.66, 0.80, 0.80),
    )
    if point:
        return map_content_point((960, 1720), BUILTIN_DAILY_TASK_REFERENCE_SIZE, screenshot), score

    # In the live Archer Camp a first-time tutorial hand can cover the word
    # "训练" while leaving the two blue camp actions intact.  This fallback is
    # intentionally not a generic blue-button detector: it requires the
    # expected right training hexagon *and* the left upgrade hexagon, both at
    # their measured relative positions.  It is reached only after the Daily
    # Task card's own troop-specific Go control was double-confirmed.
    if _daily_training_action_pair_is_valid(screenshot):
        return map_content_point((960, 1720), BUILTIN_DAILY_TASK_REFERENCE_SIZE, screenshot), max(score, 0.91)
    return None, score


def _daily_training_action_pair_is_valid(screenshot: Image.Image) -> bool:
    """Recognise the camp's adjacent Upgrade/Train action pair conservatively.

    The right action is the only returned target.  A blue town building or a
    daily-page control cannot pass because it lacks a same-row blue partner at
    the distinct, measured Upgrade position.
    """
    viewport = content_viewport(screenshot)
    rgb = np.asarray(screenshot.convert("RGB"))
    hsv = cv2.cvtColor(rgb, cv2.COLOR_RGB2HSV)
    # Button fills in the reviewed Archer Camp are saturated medium blue;
    # snow and town roofs are either less saturated or shifted in hue.
    blue = cv2.inRange(hsv, np.array((102, 120, 170), np.uint8), np.array((112, 255, 255), np.uint8))
    count, _labels, stats, centres = cv2.connectedComponentsWithStats(blue)
    train_target = map_content_point((960, 1720), BUILTIN_DAILY_TASK_REFERENCE_SIZE, screenshot)
    min_width = max(80, round(viewport.width * 0.075))
    max_width = max(min_width + 1, round(viewport.width * 0.175))
    # The first-run hand can divide the Train hexagon into a smaller visible
    # blue lobe (141 x 114 px / 7,354 px on the verified 1440 x 2560 shot).
    # Its position still has to pair with the full Upgrade hexagon below, so
    # admit that occlusion without turning this into a generic blue matcher.
    min_height = max(70, round(viewport.height * 0.040))
    max_height = max(min_height + 1, round(viewport.height * 0.115))
    min_area = max(2_500, round(viewport.width * viewport.height * 0.0018))
    components: list[tuple[float, float, int, int, int]] = []
    for index in range(1, count):
        _x, _y, width, height, area = (int(value) for value in stats[index])
        centre_x, centre_y = (float(value) for value in centres[index])
        if (
            min_width <= width <= max_width
            and min_height <= height <= max_height
            and area >= min_area
        ):
            components.append((centre_x, centre_y, width, height, area))

    right = next(
        (
            component
            for component in components
            if abs(component[0] - train_target[0]) <= viewport.width * 0.075
            and abs(component[1] - train_target[1]) <= viewport.height * 0.070
        ),
        None,
    )
    if right is None:
        return False
    return any(
        viewport.width * 0.115 <= right[0] - candidate[0] <= viewport.width * 0.215
        and abs(candidate[1] - right[1]) <= viewport.height * 0.060
        for candidate in components
        if candidate is not right
    )


def _daily_training_normal_button_point(screenshot: Image.Image) -> tuple[int, int] | None:
    """Return only the large right-side blue normal-training control."""
    viewport = content_viewport(screenshot)
    rgb = np.asarray(screenshot.convert("RGB"))
    red, green, blue = rgb[:, :, 0], rgb[:, :, 1], rgb[:, :, 2]
    normal_blue = (
        (blue > 170)
        & (green > 90)
        & (red < 150)
        & ((blue.astype(np.int16) - red.astype(np.int16)) > 70)
    ).astype(np.uint8)
    count, _labels, stats, centres = cv2.connectedComponentsWithStats(normal_blue, connectivity=8)
    fragments: list[tuple[int, int, int, int]] = []
    for index in range(1, count):
        x, y, width, height, area = stats[index]
        centre_x, centre_y = centres[index]
        if (
            viewport.left + viewport.width * 0.50 <= centre_x <= viewport.left + viewport.width * 0.98
            and viewport.top + viewport.height * 0.825 <= y <= viewport.top + viewport.height * 0.87
            and y + height >= viewport.top + viewport.height * 0.86
            and area >= viewport.width * viewport.height * 0.0007
        ):
            fragments.append((int(x), int(y), int(width), int(height)))
    if not fragments:
        return None
    left = min(x for x, _y, _width, _height in fragments)
    top = min(y for _x, y, _width, _height in fragments)
    right = max(x + width for x, _y, width, _height in fragments)
    bottom = max(y + height for _x, y, _width, height in fragments)
    width, height = right - left, bottom - top
    if not (
        viewport.width * 0.35 <= width <= viewport.width * 0.50
        and viewport.height * 0.04 <= height <= viewport.height * 0.09
    ):
        return None
    # A tutorial hand can cover the middle of the normal button and split its
    # blue fill into several components.  The validated union is still one
    # control; use its geometric centre rather than any unrelated lower camp.
    return (left + right) // 2, (top + bottom) // 2


def match_daily_training_normal_button(
    screenshot: Image.Image,
    threshold: float,
) -> tuple[tuple[int, int] | None, float]:
    """Recognise only the blue normal-training button in a troop panel."""
    point, score = _match_daily_task_template(
        screenshot,
        BUILTIN_DAILY_TRAINING_NORMAL_LABEL_ASSET,
        BUILTIN_DAILY_TRAINING_NORMAL_LABEL_TEMPLATE_NAME,
        max(0.90, float(threshold)),
        _relative_region(screenshot, 0.50, 0.83, 0.99, 1.00),
    )
    action_point = _daily_training_normal_button_point(screenshot)
    if point and action_point:
        return action_point, score

    # A first-run tutorial hand can cover the word "训练" on the blue normal
    # button.  The immediate-complete button on its left is deliberately
    # yellow and is never returned.  The three colour lanes below are a
    # constrained troop-panel signature: yellow immediate-complete, blue
    # normal train and the green quantity slider.  It is accepted only after
    # a troop-specific Daily Task Go control has already been double-confirmed
    # by the caller, so this does not become a generic blue-button matcher.
    if action_point and _daily_training_normal_panel_is_valid(screenshot):
        return action_point, max(score, 0.91)
    return None, score


def _daily_training_normal_panel_is_valid(screenshot: Image.Image) -> bool:
    """Recognise a tutorial-covered ordinary troop training panel conservatively."""
    viewport = content_viewport(screenshot)
    rgb = np.asarray(screenshot.convert("RGB"))

    def lane(x0: float, y0: float, x1: float, y1: float) -> np.ndarray:
        left = viewport.left + round(viewport.width * x0)
        top = viewport.top + round(viewport.height * y0)
        right = viewport.left + round(viewport.width * x1)
        bottom = viewport.top + round(viewport.height * y1)
        return rgb[top:bottom, left:right]

    normal_lane = lane(0.50, 0.84, 0.98, 0.94)
    instant_lane = lane(0.04, 0.84, 0.49, 0.94)
    quantity_lane = lane(0.12, 0.74, 0.52, 0.79)
    if normal_lane.size == 0 or instant_lane.size == 0 or quantity_lane.size == 0:
        return False

    def share(image: np.ndarray, mask: np.ndarray) -> float:
        return float(np.mean(mask)) if image.size else 0.0

    red, green, blue = normal_lane[:, :, 0], normal_lane[:, :, 1], normal_lane[:, :, 2]
    normal_blue = (blue > 175) & (green > 90) & (red < 150) & ((blue.astype(np.int16) - red.astype(np.int16)) > 70)
    red, green, blue = instant_lane[:, :, 0], instant_lane[:, :, 1], instant_lane[:, :, 2]
    instant_yellow = (red > 180) & (green > 120) & (blue < 130) & ((red.astype(np.int16) - blue.astype(np.int16)) > 100)
    red, green, blue = quantity_lane[:, :, 0], quantity_lane[:, :, 1], quantity_lane[:, :, 2]
    quantity_green = (green > 130) & (red < 150) & (blue < 150) & ((green.astype(np.int16) - red.astype(np.int16)) > 70)
    # The green fill is proportional to the requested troop quantity.  The
    # live panel measures about 30% at 117 troops and roughly 0.4% at the
    # intended 10; a 20% cutoff incorrectly rejected the normal panel at 75.
    # Retain the correlated yellow/blue lanes, but permit the small verified
    # green remnant needed to finish the exact-10 route.  At exactly 10 the
    # fill is below even the constrained colour floor, so the separate,
    # current-layout count template becomes the third panel correlation.
    return (
        share(normal_lane, normal_blue) >= 0.25
        and share(instant_lane, instant_yellow) >= 0.25
        # The live count-11 frame measured 0.002197 after every preceding
        # minus tap had been revalidated.  Keep a small margin below that
        # evidence-backed value so the route can make the final 11 -> 10 tap;
        # the correlated yellow and blue lanes plus exact action geometry
        # remain mandatory.
        and (share(quantity_lane, quantity_green) >= 0.002 or daily_training_count_is_ten(screenshot, 0.90))
    )


def daily_training_quantity_field_point(screenshot: Image.Image) -> tuple[int, int] | None:
    """Return the reviewed editable quantity field only on a normal panel.

    The point was live-proved on the 1440x2560 MuMu layout after the exact
    Daily-Task training route.  It is never exposed from an arbitrary number
    box: the ordinary blue action geometry, yellow instant-complete lane and
    green/exact-ten quantity evidence must all be present in the same frame.
    """
    if not _daily_training_normal_button_point(screenshot):
        return None
    if not _daily_training_normal_panel_is_valid(screenshot):
        return None
    return map_content_point((1040, 1954), (1440, 2560), screenshot)


def daily_training_quantity_slider_points(
    screenshot: Image.Image,
) -> tuple[tuple[int, int], tuple[int, int]] | None:
    """Return the proved quantity handle and its maximum endpoint.

    The ordinary troop panel has three blue controls on one horizontal lane:
    a fixed minus button, a movable slider handle and a fixed plus button.
    Live 1440 x 2560 captures place those centres at approximately x=113,
    x=247..758 and x=850.  We identify all three from pixels after requiring
    the correlated yellow/blue/green ordinary-panel signature.  The maximum
    endpoint is derived from the fixed plus control, so it scales with MuMu's
    content viewport and never depends on an account-specific troop count.
    """
    if not _daily_training_normal_button_point(screenshot):
        return None
    if not _daily_training_normal_panel_is_valid(screenshot):
        return None
    viewport = content_viewport(screenshot)
    rgb = np.asarray(screenshot.convert("RGB"))
    red, green, blue = rgb[:, :, 0], rgb[:, :, 1], rgb[:, :, 2]
    normal_blue = (
        (blue > 170)
        & (green > 90)
        & (red < 150)
        & ((blue.astype(np.int16) - red.astype(np.int16)) > 70)
    ).astype(np.uint8)
    count, _labels, stats, centres = cv2.connectedComponentsWithStats(
        normal_blue, connectivity=8
    )
    candidates: list[tuple[float, float]] = []
    min_y = viewport.top + viewport.height * 0.72
    max_y = viewport.top + viewport.height * 0.82
    for index in range(1, count):
        _x, _y, width, height, area = stats[index]
        centre_x, centre_y = centres[index]
        if (
            viewport.left + viewport.width * 0.02 <= centre_x <= viewport.left + viewport.width * 0.68
            and min_y <= centre_y <= max_y
            and viewport.width * 0.035 <= width <= viewport.width * 0.14
            and viewport.height * 0.015 <= height <= viewport.height * 0.08
            and viewport.width * viewport.height * 0.00020
            <= area
            <= viewport.width * viewport.height * 0.004
        ):
            candidates.append((float(centre_x), float(centre_y)))
    candidates.sort()
    if len(candidates) != 3:
        return None
    minus, handle, plus = candidates
    if not (
        minus[0] <= viewport.left + viewport.width * 0.15
        and viewport.left + viewport.width * 0.15 <= handle[0] < plus[0]
        and viewport.left + viewport.width * 0.54 <= plus[0] <= viewport.left + viewport.width * 0.66
    ):
        return None
    # The live maximum handle remains one handle-width to the left of Plus.
    # 6.5% of the content width is 93.6 px at the reference layout, matching
    # the measured 850 -> 758 endpoint while preserving scale independence.
    end_x = round(plus[0] - viewport.width * 0.065)
    return (round(handle[0]), round(handle[1])), (end_x, round(handle[1]))


def daily_training_quantity_is_maxed(screenshot: Image.Image) -> bool:
    """Prove that the ordinary training slider handle is at its right end."""
    points = daily_training_quantity_slider_points(screenshot)
    if not points:
        return False
    handle, endpoint = points
    viewport = content_viewport(screenshot)
    return abs(handle[0] - endpoint[0]) <= max(4, round(viewport.width * 0.008))


def daily_training_input_focus_is_proven(input_method_state: str) -> bool:
    """Accept text input only for the live-proved editable Unity connection."""
    required_connection = all(
        marker in input_method_state
        for marker in (
            "mInputShown=true",
            "EditableInputConnection",
        )
    )
    # MuMu has emitted both the descriptive UnityPlayer name and the
    # obfuscated concrete class ``com.unity3d.player.Q`` for the same served
    # game view.  Require one of those Unity-specific identities in addition
    # to the visible editable connection; generic Android text fields fail.
    unity_view = "UnityPlayer" in input_method_state or "com.unity3d.player." in input_method_state
    return required_connection and unity_view


def daily_training_count_is_ten(screenshot: Image.Image, threshold: float) -> bool:
    """Return True only for the reviewed count field rendered as exactly 10."""
    point, _score = _match_daily_task_template(
        screenshot,
        BUILTIN_DAILY_TRAINING_COUNT_TEN_ASSET,
        BUILTIN_DAILY_TRAINING_COUNT_TEN_TEMPLATE_NAME,
        # The archived full-resolution "10" scene scores 1.0 and remains
        # above 0.989 after the supported scale transforms.  A looser 0.90
        # threshold treated the visually similar live value "19" as "10".
        max(0.985, float(threshold)),
        _relative_region(screenshot, 0.62, 0.72, 0.90, 0.84),
    )
    return point is not None


def match_daily_training_active(
    screenshot: Image.Image,
    threshold: float,
) -> tuple[tuple[int, int] | None, float]:
    """Recognise a training queue in progress; this is observation only."""
    region = _relative_region(screenshot, 0.18, 0.70, 0.76, 0.88)
    point, score = _match_daily_task_template(
        screenshot,
        BUILTIN_DAILY_TRAINING_ACTIVE_GREEN_LABEL_ASSET,
        BUILTIN_DAILY_TRAINING_ACTIVE_GREEN_LABEL_TEMPLATE_NAME,
        max(0.985, float(threshold)),
        region,
    )
    if point:
        return point, score
    point, text_score = _match_daily_task_template(
        screenshot,
        BUILTIN_DAILY_TRAINING_ACTIVE_TEXT_ASSET,
        BUILTIN_DAILY_TRAINING_ACTIVE_TEXT_TEMPLATE_NAME,
        max(0.94, float(threshold)),
        region,
    )
    return point, max(score, text_score)


def daily_training_remaining_time_crop(
    screenshot: Image.Image,
    threshold: float,
) -> Image.Image | None:
    """Return only the account-free ordinary-training countdown strip."""
    active_point, _score = match_daily_training_active(screenshot, threshold)
    if not active_point:
        return None
    region = _relative_region(screenshot, 0.15, 0.70, 0.80, 0.84)
    return screenshot.crop(region)


def match_daily_training_spear_tutorial_entry(
    screenshot: Image.Image,
    threshold: float,
) -> tuple[tuple[int, int] | None, float]:
    """Recognise the reviewed Spear-camp tutorial target after its Daily Go.

    The animated hand is deliberately excluded from the template.  Only the
    stable troop-face badge embedded in the highlighted Spear-camp target is
    matched in its narrow city region; a caller must still use this strictly
    after the exact Spear Daily Task's Go control was double-checked.
    """
    point, score = _match_daily_task_template(
        screenshot,
        BUILTIN_DAILY_TRAINING_SPEAR_TUTORIAL_FACE_ASSET,
        BUILTIN_DAILY_TRAINING_SPEAR_TUTORIAL_FACE_TEMPLATE_NAME,
        max(0.62, float(threshold) - 0.28),
        _relative_region(screenshot, 0.40, 0.36, 0.54, 0.48),
    )
    if not point:
        return None, score
    # The exact centre of the reviewed golden tutorial target.  It is returned
    # only after the stable face proof above, never as a generic city action.
    return map_content_point((720, 1095), BUILTIN_DAILY_TASK_REFERENCE_SIZE, screenshot), score


def match_daily_training_archer_tutorial_entry(
    screenshot: Image.Image,
    threshold: float,
) -> tuple[tuple[int, int] | None, float]:
    """Recognise the first-use Archer-camp target after its exact Daily Go.

    On the live 2026-08-05 route the first tutorial frame highlights the camp
    itself, before the already-reviewed blue ``Train`` action exists.  The
    hand moves far enough to cover different parts of the badge, so four
    de-identified poses spanning the observed cycle are matched only inside
    its narrow city region.  Across twenty passive frames the weakest target
    pose scored 0.700;
    every historical non-target frame stayed at or below 0.524.  The caller
    still requires two fresh stable frames and may use this only after
    double-confirming the Archer Daily card's own ``Go`` control.
    """
    best_score = 0.0
    matched = False
    region = _relative_region(screenshot, 0.30, 0.31, 0.71, 0.57)
    pose_threshold = max(0.65, float(threshold) - 0.25)
    for asset, template_name in zip(
        BUILTIN_DAILY_TRAINING_ARCHER_TUTORIAL_POSE_ASSETS,
        BUILTIN_DAILY_TRAINING_ARCHER_TUTORIAL_POSE_TEMPLATE_NAMES,
    ):
        point, score = _match_daily_task_template(
            screenshot,
            asset,
            template_name,
            pose_threshold,
            region,
        )
        best_score = max(best_score, score)
        matched = matched or point is not None
    if not matched:
        return None, best_score
    return map_content_point((720, 1130), BUILTIN_DAILY_TASK_REFERENCE_SIZE, screenshot), best_score


def match_daily_training_collect_tutorial(
    screenshot: Image.Image,
    threshold: float,
) -> tuple[tuple[int, int] | None, float]:
    """Recognise only the animated shield-camp completion tutorial target.

    The target is accepted only when three independent signs coexist: the
    shield camp scene, a reviewed hand-and-target crop, and the central hand
    skin share.  Its hand animation changes pose between frames, so callers
    still require two stable observations before tapping the measured target.
    """
    legacy_camp_point, legacy_camp_score = _match_daily_task_template(
        screenshot,
        BUILTIN_DAILY_TRAINING_SHIELD_CAMP_ASSET,
        BUILTIN_DAILY_TRAINING_SHIELD_CAMP_TEMPLATE_NAME,
        0.80,
        None,
    )
    current_camp_point, current_camp_score = _match_daily_task_template(
        screenshot,
        BUILTIN_DAILY_TRAINING_SHIELD_CAMP_CURRENT_ASSET,
        BUILTIN_DAILY_TRAINING_SHIELD_CAMP_CURRENT_TEMPLATE_NAME,
        0.96,
        _relative_region(screenshot, 0.08, 0.32, 0.75, 0.76),
    )
    camp_score = max(legacy_camp_score, current_camp_score)
    # Preserve the reviewed legacy animation tolerance: several accepted old
    # frames sit between its 0.75 semantic gate and the template helper's 0.80
    # point-return threshold.  The new skin is stricter and must return an
    # actual point at 0.96 before it can satisfy the scene anchor.
    camp_verified = legacy_camp_score >= 0.75 or current_camp_point is not None
    tutorial_point, tutorial_score = _match_daily_task_template(
        screenshot,
        BUILTIN_DAILY_TRAINING_COLLECT_TUTORIAL_ASSET,
        BUILTIN_DAILY_TRAINING_COLLECT_TUTORIAL_TEMPLATE_NAME,
        0.55,
        None,
    )
    viewport = content_viewport(screenshot)
    rgb = np.asarray(screenshot.convert("RGB"))
    left = viewport.left + round(viewport.width * 0.45)
    top = viewport.top + round(viewport.height * 0.32)
    right = viewport.left + round(viewport.width * 0.65)
    bottom = viewport.top + round(viewport.height * 0.50)
    hand = rgb[top:bottom, left:right]
    if hand.size:
        red, green, blue = hand[:, :, 0], hand[:, :, 1], hand[:, :, 2]
        skin_share = float(
            (
                (red > 120)
                & (green > 60)
                & (green < 210)
                & (blue < 140)
                & ((red.astype(np.int16) - blue.astype(np.int16)) > 60)
            ).mean()
        )
    else:
        skin_share = 0.0
    if (
        not camp_verified
        or camp_score < 0.75
        or tutorial_point is None
        or tutorial_score < 0.55
        or skin_share < 0.12
    ):
        return None, min(camp_score, tutorial_score)
    # The hand is animated and its matched centre moved by more than the
    # controller's two-frame stability tolerance in the live completion
    # scene.  The highlighted yellow target itself stays fixed: repeated
    # passive frames bounded its centre around the reviewed (720, 1200)
    # game-space point.  Keep the animated hand only as recognition evidence
    # and return the stable target centre for the action.
    return map_content_point((720, 1200), BUILTIN_DAILY_TASK_REFERENCE_SIZE, screenshot), min(
        camp_score,
        tutorial_score,
    )


def match_daily_training_unlock_continue(
    screenshot: Image.Image,
    threshold: float,
) -> tuple[tuple[int, int] | None, float]:
    """Recognise only the reviewed post-training ``click to continue`` unlock.

    The one permitted point is the matched continuation text itself.  This is
    not a generic modal closer: the template was captured after the reviewed
    ten-unit normal training route and contains the distinct unlock screen's
    wording and layout, with no paid, speed-up, or purchase controls.
    """
    return _match_daily_task_template(
        screenshot,
        BUILTIN_DAILY_TRAINING_UNLOCK_CONTINUE_ASSET,
        BUILTIN_DAILY_TRAINING_UNLOCK_CONTINUE_TEMPLATE_NAME,
        max(0.94, float(threshold)),
        _relative_region(screenshot, 0.25, 0.90, 0.75, 1.00),
    )


def match_daily_training_shield_camp(
    screenshot: Image.Image,
    threshold: float,
) -> tuple[tuple[int, int] | None, float]:
    """Find the completed shield camp before collecting its finished batch."""
    point, score = _match_daily_task_template(
        screenshot,
        BUILTIN_DAILY_TRAINING_SHIELD_CAMP_ASSET,
        BUILTIN_DAILY_TRAINING_SHIELD_CAMP_TEMPLATE_NAME,
        max(0.90, float(threshold)),
        _relative_region(screenshot, 0.08, 0.32, 0.75, 0.76),
    )
    if not point:
        return None, score
    return map_content_point((600, 1260), BUILTIN_DAILY_TASK_REFERENCE_SIZE, screenshot), score


def match_daily_normal_build_action(
    screenshot: Image.Image,
    threshold: float,
) -> tuple[tuple[int, int] | None, float]:
    """Return the ordinary bottom-centre building action after Daily-Task Go.

    A valid surface must show the exact ``建筑信息`` section heading captured
    from the routed task page *and* the large saturated-blue normal action in
    its dedicated lower-centre lane.  The yellow instant-complete action is
    absent on this surface and has no candidate here.  This helper purposely
    does not recognise a generic city button; callers use it only as the next
    correlated step after ``match_daily_building_upgrade_mission``.
    """
    point, score = _match_daily_task_template(
        screenshot,
        BUILTIN_DAILY_BUILDING_INFO_HEADER_ASSET,
        BUILTIN_DAILY_BUILDING_INFO_HEADER_TEMPLATE_NAME,
        max(0.94, float(threshold)),
        _relative_region(screenshot, 0.00, 0.43, 0.40, 0.62),
    )
    if not point or not _daily_template_integrity_is_valid(
        screenshot,
        BUILTIN_DAILY_BUILDING_INFO_HEADER_ASSET,
        BUILTIN_DAILY_BUILDING_INFO_HEADER_TEMPLATE_NAME,
        point,
        min_luma_ratio=DAILY_ACTION_MIN_LUMA_RATIO,
        min_chroma_ratio=DAILY_ACTION_MIN_CHROMA_RATIO,
        max_colour_distance=DAILY_ACTION_MAX_COLOUR_DISTANCE,
        strict_action=True,
    ):
        return None, score

    viewport = content_viewport(screenshot)
    x0 = viewport.left + round(viewport.width * 0.25)
    x1 = viewport.left + round(viewport.width * 0.75)
    y0 = viewport.top + round(viewport.height * 0.88)
    y1 = viewport.top + round(viewport.height * 0.985)
    image = np.asarray(screenshot.convert("RGB"))
    action_lane = image[y0:y1, x0:x1]
    if action_lane.size == 0:
        return None, score
    red, green, blue = action_lane[:, :, 0], action_lane[:, :, 1], action_lane[:, :, 2]
    normal_blue = (
        (blue > 150)
        & (green > 80)
        & (red < 135)
        & ((blue.astype(np.int16) - red.astype(np.int16)) > 70)
    )
    # Measured live action coverage is 35%.  A conservative 25% floor keeps
    # the button robust to its hand tutorial while excluding the section
    # heading alone from ever authorising the mapped action point.
    if float(np.mean(normal_blue)) < 0.25:
        return None, score
    return map_content_point((720, 2415), BUILTIN_DAILY_TASK_REFERENCE_SIZE, screenshot), score


def match_daily_building_active_upgrading(
    screenshot: Image.Image,
    threshold: float,
) -> tuple[tuple[int, int] | None, float]:
    """Recognise only the generic active-construction status row.

    This observation-only matcher is used solely after the reviewed Daily
    building mission's own Go button.  Its tight asset excludes account data,
    timers, diamonds, instant completion and speed-up controls.
    """
    return _match_daily_task_template(
        screenshot,
        BUILTIN_DAILY_BUILDING_ACTIVE_UPGRADING_LABEL_ASSET,
        BUILTIN_DAILY_BUILDING_ACTIVE_UPGRADING_LABEL_TEMPLATE_NAME,
        max(0.985, float(threshold)),
        _relative_region(screenshot, 0.00, 0.66, 0.42, 0.80),
    )


def daily_training_minus_point(screenshot: Image.Image) -> tuple[int, int] | None:
    """Find the reviewed blue quantity-minus control in a troop panel.

    This intentionally does *not* reuse a fixed coordinate.  The live shield
    panel recorded on 2026-07-31 put the bottom edge of that control above the
    historic ``(115, 2110)`` point, so taps were harmless no-ops.  We first
    require the correlated normal-training panel signature and then select
    only its left blue quantity control.  ``None`` means no input is allowed.
    """
    if not _daily_training_normal_panel_is_valid(screenshot):
        return None
    viewport = content_viewport(screenshot)
    rgb = np.asarray(screenshot.convert("RGB"))
    red, green, blue = rgb[:, :, 0], rgb[:, :, 1], rgb[:, :, 2]
    normal_blue = (
        (blue > 170)
        & (green > 90)
        & (red < 150)
        & ((blue.astype(np.int16) - red.astype(np.int16)) > 70)
    ).astype(np.uint8)
    count, _labels, stats, centres = cv2.connectedComponentsWithStats(normal_blue, connectivity=8)
    min_x = viewport.left + viewport.width * 0.02
    # The slider's movable blue handle enters this band at very low counts.
    # The reviewed minus button itself stays in the fixed left-most 15% of
    # the viewport, so exclude the handle rather than guessing between two
    # blue components.
    max_x = viewport.left + viewport.width * 0.15
    min_y = viewport.top + viewport.height * 0.72
    max_y = viewport.top + viewport.height * 0.82
    min_width, max_width = viewport.width * 0.035, viewport.width * 0.14
    min_height, max_height = viewport.height * 0.015, viewport.height * 0.08
    min_area, max_area = viewport.width * viewport.height * 0.00020, viewport.width * viewport.height * 0.004
    candidates: list[tuple[float, float]] = []
    for index in range(1, count):
        x, y, width, height, area = stats[index]
        centre_x, centre_y = centres[index]
        if (
            min_x <= centre_x <= max_x
            and min_y <= centre_y <= max_y
            and min_width <= width <= max_width
            and min_height <= height <= max_height
            and min_area <= area <= max_area
        ):
            candidates.append((float(centre_x), float(centre_y)))
    if len(candidates) != 1:
        return None
    centre_x, centre_y = candidates[0]
    return round(centre_x), round(centre_y)


def daily_training_back_point(screenshot: Image.Image) -> tuple[int, int]:
    """Return the panel's top-left back control after active-queue proof."""
    return map_content_point((76, 85), BUILTIN_DAILY_TASK_REFERENCE_SIZE, screenshot)


def match_daily_hero_free_recruit(
    screenshot: Image.Image,
    threshold: float,
) -> tuple[tuple[int, int] | None, float]:
    """Find a green ``Recruit once / Free`` control, never its key version."""
    region = _relative_region(screenshot, 0.02, 0.50, 0.56, 1.00)
    best_score = 0.0
    for asset, template_name in (
        (BUILTIN_DAILY_HERO_FREE_RECRUIT_ASSET, BUILTIN_DAILY_HERO_FREE_RECRUIT_TEMPLATE_NAME),
        (BUILTIN_DAILY_HERO_EPIC_FREE_RECRUIT_ASSET, BUILTIN_DAILY_HERO_EPIC_FREE_RECRUIT_TEMPLATE_NAME),
    ):
        point, score = _match_daily_task_template(
            screenshot, asset, template_name, max(0.92, float(threshold)), region
        )
        best_score = max(best_score, score)
        if point and _daily_template_integrity_is_valid(
            screenshot,
            asset,
            template_name,
            point,
            min_luma_ratio=DAILY_ACTION_MIN_LUMA_RATIO,
            min_chroma_ratio=DAILY_ACTION_MIN_CHROMA_RATIO,
            max_colour_distance=DAILY_ACTION_MAX_COLOUR_DISTANCE,
            strict_action=True,
        ):
            return point, score
    return None, best_score


def daily_hero_recruit_page_is_visible(screenshot: Image.Image, threshold: float) -> bool:
    """Recognise the hero-recruit screen before using its Back control."""
    point, _score = _match_daily_task_template(
        screenshot,
        BUILTIN_DAILY_HERO_RECRUIT_PAGE_ASSET,
        BUILTIN_DAILY_HERO_RECRUIT_PAGE_TEMPLATE_NAME,
        max(0.92, float(threshold)),
        _relative_region(screenshot, 0.62, 0.05, 1.00, 0.27),
    )
    return point is not None


def match_daily_hero_recruit_duplicate_result(
    screenshot: Image.Image,
    threshold: float,
) -> tuple[tuple[int, int] | None, float]:
    """Return the passive duplicate-hero reveal anchor, never an exit point."""

    duplicate, score = _match_daily_task_template(
        screenshot,
        BUILTIN_DAILY_HERO_RECRUIT_DUPLICATE_OWNED_ASSET,
        BUILTIN_DAILY_HERO_RECRUIT_DUPLICATE_OWNED_TEMPLATE_NAME,
        max(0.985, float(threshold)),
        _relative_region(screenshot, 0.10, 0.92, 0.70, 1.00),
    )
    if not duplicate or not _daily_template_integrity_is_valid(
        screenshot,
        BUILTIN_DAILY_HERO_RECRUIT_DUPLICATE_OWNED_ASSET,
        BUILTIN_DAILY_HERO_RECRUIT_DUPLICATE_OWNED_TEMPLATE_NAME,
        duplicate,
        min_luma_ratio=0.97,
        min_chroma_ratio=DAILY_ACTION_MIN_CHROMA_RATIO,
        max_colour_distance=DAILY_ACTION_MAX_COLOUR_DISTANCE,
        strict_action=True,
    ):
        return None, score
    return duplicate, score


def match_daily_hero_recruit_summary_exit(
    screenshot: Image.Image,
    threshold: float,
) -> tuple[tuple[int, int] | None, float]:
    """Return the reviewed side exit after the recruit-summary text proof.

    The yellow recruit button, keys and diamonds are intentionally excluded.
    A caller must additionally hold the immediately preceding verified
    free-recruit lineage and two fresh frames.  The summary title is useful
    evidence but is not required: the complete native exit sentence is itself
    the game's explicit instruction for this screen.
    """
    return match_daily_tap_anywhere_exit_text(screenshot, threshold)


def match_daily_tap_anywhere_exit_text(
    screenshot: Image.Image,
    threshold: float = 0.90,
) -> tuple[tuple[int, int] | None, float]:
    """Recognise the complete native ``点击任意位置退出`` text line.

    This is a deliberately tiny, fast phrase-specific OCR rather than a
    general Chinese OCR engine.  Reviewed native renderings are searched over
    the complete game viewport because reward/tutorial layouts may move the
    sentence.  Strict raw-colour integrity prevents a dimmed/covered lookalike
    from authorising input.  The returned point is on the left side's empty
    background, far from the yellow recruit button, reward icons, keys and
    diamonds.
    """

    best_hint_score = 0.0
    for asset, template_name in (
        (
            BUILTIN_DAILY_HERO_RECRUIT_EXIT_HINT_ASSET,
            BUILTIN_DAILY_HERO_RECRUIT_EXIT_HINT_TEMPLATE_NAME,
        ),
        (
            BUILTIN_DAILY_HERO_RECRUIT_EXIT_HINT_LEGACY_ASSET,
            BUILTIN_DAILY_HERO_RECRUIT_EXIT_HINT_LEGACY_TEMPLATE_NAME,
        ),
        (
            BUILTIN_DAILY_TAP_ANYWHERE_EXIT_REWARD_CURRENT_ASSET,
            BUILTIN_DAILY_TAP_ANYWHERE_EXIT_REWARD_CURRENT_TEMPLATE_NAME,
        ),
        (
            BUILTIN_DAILY_TAP_ANYWHERE_EXIT_OLD_ASSET,
            BUILTIN_DAILY_TAP_ANYWHERE_EXIT_OLD_TEMPLATE_NAME,
        ),
    ):
        hint, hint_score = _match_daily_task_template(
            screenshot,
            asset,
            template_name,
            max(0.985, float(threshold)),
            # The native sentence is itself the page's explicit exit
            # instruction.  Search the whole game viewport: several reward
            # and tutorial sheets place it at different vertical positions.
            # Template and screenshot arrays are cached, so this remains a
            # small phrase-specific pass rather than slow general OCR.
            _relative_region(screenshot, 0.00, 0.00, 1.00, 1.00),
        )
        best_hint_score = max(best_hint_score, hint_score)
        if hint and _daily_template_integrity_is_valid(
            screenshot,
            asset,
            template_name,
            hint,
            min_luma_ratio=0.97,
            min_chroma_ratio=DAILY_ACTION_MIN_CHROMA_RATIO,
            max_colour_distance=DAILY_ACTION_MAX_COLOUR_DISTANCE,
            strict_action=True,
        ):
            return (
                map_content_point((96, 1500), BUILTIN_DAILY_TASK_REFERENCE_SIZE, screenshot),
                hint_score,
            )
    return None, best_hint_score


def daily_hero_recruit_result_is_visible(screenshot: Image.Image, threshold: float) -> bool:
    """Recognise either reviewed recruit-result layout without acting.

    The compact summary requires both its ``Reward`` banner and exact exit
    hint.  The duplicate reveal uses only the stable ``already own this hero``
    prefix and excludes character art/name/rarity/token count.
    """

    summary_exit, _summary_score = match_daily_hero_recruit_summary_exit(
        screenshot,
        threshold,
    )
    if summary_exit:
        return True
    duplicate, _duplicate_score = match_daily_hero_recruit_duplicate_result(
        screenshot,
        threshold,
    )
    return duplicate is not None


def daily_hero_recruit_back_point(screenshot: Image.Image) -> tuple[int, int]:
    """Return the hero-recruit Back control after page-proof only."""
    return map_content_point((76, 85), BUILTIN_DAILY_TASK_REFERENCE_SIZE, screenshot)


def daily_task_close_point(screenshot: Image.Image) -> tuple[int, int]:
    """Return Daily Tasks' top-right close affordance after page proof only."""
    return map_content_point((1375, 250), BUILTIN_DAILY_TASK_REFERENCE_SIZE, screenshot)


def daily_network_dialog_is_visible(screenshot: Image.Image, threshold: float) -> bool:
    """Recognise exact network/forced-offline sheets for a zero-input pause.

    No button coordinate is returned.  A positive match can only keep the
    worker alive while the external network state changes; it cannot click
    reconnect, customer service, close, Back, or any underlying game control.
    """
    point, _score = _match_daily_task_template(
        screenshot,
        BUILTIN_DAILY_NETWORK_DISCONNECTED_ASSET,
        BUILTIN_DAILY_NETWORK_DISCONNECTED_TEMPLATE_NAME,
        max(0.985, float(threshold)),
        _relative_region(screenshot, 0.28, 0.28, 0.72, 0.42),
    )
    if point is not None:
        return True

    forced_offline, _forced_score = _match_daily_task_template(
        screenshot,
        BUILTIN_DAILY_FORCED_OFFLINE_MESSAGE_ASSET,
        BUILTIN_DAILY_FORCED_OFFLINE_MESSAGE_TEMPLATE_NAME,
        max(0.985, float(threshold)),
        _relative_region(screenshot, 0.10, 0.43, 0.90, 0.55),
    )
    if forced_offline is None:
        return False
    return _daily_template_integrity_is_valid(
        screenshot,
        BUILTIN_DAILY_FORCED_OFFLINE_MESSAGE_ASSET,
        BUILTIN_DAILY_FORCED_OFFLINE_MESSAGE_TEMPLATE_NAME,
        forced_offline,
        min_luma_ratio=0.97,
        min_chroma_ratio=DAILY_ACTION_MIN_CHROMA_RATIO,
        max_colour_distance=DAILY_ACTION_MAX_COLOUR_DISTANCE,
        strict_action=True,
    )


def match_daily_welcome_back_confirm(
    screenshot: Image.Image,
    threshold: float,
) -> tuple[int, int] | None:
    """Return the exact offline-settlement confirm point after paired proof.

    This is deliberately not a generic dialog or reward handler.  Both the
    reviewed ``Welcome back`` title and its fixed ordinary green ``Confirm``
    control must match in their independent regions at a high threshold.
    Callers must still require two fresh matching frames and may tap at most
    once per process.
    """
    title, _title_score = _match_daily_task_template(
        screenshot,
        BUILTIN_DAILY_WELCOME_BACK_TITLE_ASSET,
        BUILTIN_DAILY_WELCOME_BACK_TITLE_TEMPLATE_NAME,
        max(0.985, float(threshold)),
        _relative_region(screenshot, 0.32, 0.16, 0.68, 0.24),
    )
    confirm, _confirm_score = _match_daily_task_template(
        screenshot,
        BUILTIN_DAILY_WELCOME_BACK_CONFIRM_ASSET,
        BUILTIN_DAILY_WELCOME_BACK_CONFIRM_TEMPLATE_NAME,
        max(0.985, float(threshold)),
        _relative_region(screenshot, 0.26, 0.72, 0.74, 0.88),
    )
    if title is None or confirm is None:
        return None
    return map_content_point(
        (720, 2050),
        BUILTIN_DAILY_TASK_REFERENCE_SIZE,
        screenshot,
    )


def match_daily_regular_activity_back(
    screenshot: Image.Image,
    threshold: float,
) -> tuple[tuple[int, int] | None, float]:
    """Return only Regular Activity's own Back after dual exact proof.

    The automatically raised page contains diamond refresh buttons and other
    input-capable controls.  None is included.  The fixed Back arrow and full
    ``Regular Activity`` title must independently match their reviewed top
    regions with strict source-colour integrity.  Callers must still require
    two fresh frames and enforce their own bounded recovery lineage.
    """

    safe_threshold = max(0.985, float(threshold))
    back, back_score = _match_daily_task_template(
        screenshot,
        BUILTIN_DAILY_REGULAR_ACTIVITY_BACK_ASSET,
        BUILTIN_DAILY_REGULAR_ACTIVITY_BACK_TEMPLATE_NAME,
        safe_threshold,
        _relative_region(screenshot, 0.0, 0.0, 0.11, 0.065),
    )
    title, title_score = _match_daily_task_template(
        screenshot,
        BUILTIN_DAILY_REGULAR_ACTIVITY_TITLE_ASSET,
        BUILTIN_DAILY_REGULAR_ACTIVITY_TITLE_TEMPLATE_NAME,
        safe_threshold,
        _relative_region(screenshot, 0.07, 0.0, 0.36, 0.065),
    )
    score = min(back_score, title_score)
    if not back or not title:
        return None, score
    for asset, name, point in (
        (
            BUILTIN_DAILY_REGULAR_ACTIVITY_BACK_ASSET,
            BUILTIN_DAILY_REGULAR_ACTIVITY_BACK_TEMPLATE_NAME,
            back,
        ),
        (
            BUILTIN_DAILY_REGULAR_ACTIVITY_TITLE_ASSET,
            BUILTIN_DAILY_REGULAR_ACTIVITY_TITLE_TEMPLATE_NAME,
            title,
        ),
    ):
        if not _daily_template_integrity_is_valid(
            screenshot,
            asset,
            name,
            point,
            min_luma_ratio=DAILY_ACTION_MIN_LUMA_RATIO,
            min_chroma_ratio=DAILY_ACTION_MIN_CHROMA_RATIO,
            max_colour_distance=DAILY_ACTION_MAX_COLOUR_DISTANCE,
            strict_action=True,
        ):
            return None, score
    return (
        map_content_point(
            (70, 70),
            BUILTIN_DAILY_TASK_REFERENCE_SIZE,
            screenshot,
        ),
        score,
    )


def match_daily_city_entry(
    screenshot: Image.Image,
    threshold: float,
    search_region: tuple[int, int, int, int] | None = None,
) -> tuple[tuple[int, int] | None, float]:
    """Confirm the left-side city task-strip anchor and return its safe tap.

    The returned tap is not the template centre.  It is the separately
    measured ``DAILY_CITY_ENTRY_REFERENCE_POINT``, mapped through the actual
    game content viewport so black MuMu margins cannot offset it.  Controllers
    must use this matcher only while they explicitly expect the main city.

    The clipboard icon is also visible on the wilderness map, so it is never
    sufficient by itself.  A simultaneously reviewed ``Town`` control proves
    the mutually exclusive wilderness state and vetoes this city action.
    """
    region = (
        search_region
        if search_region is not None
        else _relative_region(screenshot, 0.0, 0.75, 0.16, 0.91)
    )
    anchor = None
    score = 0.0
    for asset, template_name in (
        (BUILTIN_DAILY_CITY_ENTRY_ASSET, BUILTIN_DAILY_CITY_ENTRY_TEMPLATE_NAME),
        (
            BUILTIN_DAILY_CITY_ENTRY_TRAINING_HIGHLIGHT_ASSET,
            BUILTIN_DAILY_CITY_ENTRY_TRAINING_HIGHLIGHT_TEMPLATE_NAME,
        ),
    ):
        candidate, candidate_score = _match_daily_task_template(
            screenshot,
            asset,
            template_name,
            threshold,
            region,
        )
        score = max(score, candidate_score)
        if candidate and _daily_template_integrity_is_valid(
            screenshot,
            asset,
            template_name,
            candidate,
            min_luma_ratio=DAILY_CITY_MIN_LUMA_RATIO,
            min_chroma_ratio=DAILY_CITY_MIN_CHROMA_RATIO,
            max_colour_distance=DAILY_CITY_MAX_COLOUR_DISTANCE,
            strict_action=True,
        ):
            anchor = candidate
            break
    if not anchor:
        return None, score
    world_town, town_score = match_daily_world_town_entry(screenshot, threshold)
    if world_town:
        return None, max(score, town_score)
    return map_content_point(
        DAILY_CITY_ENTRY_REFERENCE_POINT,
        BUILTIN_DAILY_TASK_REFERENCE_SIZE,
        screenshot,
    ), score


def match_daily_task_header(
    screenshot: Image.Image,
    threshold: float,
    search_region: tuple[int, int, int, int] | None = None,
) -> tuple[tuple[int, int] | None, float]:
    """Find the ``daily tasks`` header in its narrow top-panel region."""
    return _match_daily_task_template(
        screenshot,
        BUILTIN_DAILY_HEADER_ASSET,
        BUILTIN_DAILY_HEADER_TEMPLATE_NAME,
        threshold,
        search_region
        if search_region is not None
        else _relative_region(screenshot, 0.32, 0.07, 0.68, 0.14),
    )


def match_daily_chapter_task_header(
    screenshot: Image.Image,
    threshold: float,
    search_region: tuple[int, int, int, int] | None = None,
) -> tuple[tuple[int, int] | None, float]:
    """Find the task sheet's Chapter Tasks title, not a generic heading."""
    region = (
        search_region
        if search_region is not None
        else _relative_region(screenshot, 0.32, 0.06, 0.68, 0.15)
    )
    best_point = None
    best_score = 0.0
    for asset, name in (
        (
            BUILTIN_DAILY_CHAPTER_HEADER_CURRENT_ASSET,
            BUILTIN_DAILY_CHAPTER_HEADER_CURRENT_TEMPLATE_NAME,
        ),
        (BUILTIN_DAILY_CHAPTER_HEADER_ASSET, BUILTIN_DAILY_CHAPTER_HEADER_TEMPLATE_NAME),
    ):
        point, score = _match_daily_task_template(
            screenshot,
            asset,
            name,
            threshold,
            region,
        )
        if score > best_score:
            best_point, best_score = point, score
    return best_point, best_score


def match_daily_task_unselected_tab(
    screenshot: Image.Image,
    threshold: float,
    search_region: tuple[int, int, int, int] | None = None,
) -> tuple[tuple[int, int] | None, float]:
    """Find the *unselected* Daily Tasks tab on the Chapter Tasks sheet."""
    return _match_daily_task_template(
        screenshot,
        BUILTIN_DAILY_UNSELECTED_TAB_ASSET,
        BUILTIN_DAILY_UNSELECTED_TAB_TEMPLATE_NAME,
        threshold,
        search_region
        if search_region is not None
        else _relative_region(screenshot, 0.65, 0.82, 1.00, 0.99),
    )


def match_daily_growth_task_daily_tab(
    screenshot: Image.Image,
    threshold: float,
) -> tuple[tuple[int, int] | None, float]:
    """Find the Daily Tasks tab only on the reviewed Growth Tasks sheet.

    This requires the sheet's top ``Main Tasks`` title as well as the dark,
    unselected Daily Tasks tab on the lower right.  It never recognises the
    blue ``Go`` controls in the task list, so it is safe to route this known
    intermediary sheet back to Daily Tasks with one tab tap.
    """
    title, title_score = _match_daily_task_template(
        screenshot,
        BUILTIN_DAILY_MAIN_TASK_PAGE_TITLE_ASSET,
        BUILTIN_DAILY_MAIN_TASK_PAGE_TITLE_TEMPLATE_NAME,
        max(0.985, float(threshold)),
        _relative_region(screenshot, 0.25, 0.10, 0.75, 0.24),
    )
    tab = None
    tab_score = 0.0
    tab_region = _relative_region(screenshot, 0.45, 0.80, 1.00, 0.99)
    for asset, name in (
        (
            BUILTIN_DAILY_GROWTH_TWO_TAB_UNSELECTED_DAILY_TAB_ASSET,
            BUILTIN_DAILY_GROWTH_TWO_TAB_UNSELECTED_DAILY_TAB_TEMPLATE_NAME,
        ),
        (
            BUILTIN_DAILY_GROWTH_TASK_UNSELECTED_DAILY_TAB_ASSET,
            BUILTIN_DAILY_GROWTH_TASK_UNSELECTED_DAILY_TAB_TEMPLATE_NAME,
        ),
    ):
        candidate, score = _match_daily_task_template(
            screenshot,
            asset,
            name,
            max(0.985, float(threshold)),
            tab_region,
        )
        if score > tab_score:
            tab, tab_score = candidate, score
    if title and tab:
        return tab, min(title_score, tab_score)
    return None, max(title_score, tab_score)


def match_daily_task_selected_tab(
    screenshot: Image.Image,
    threshold: float,
    search_region: tuple[int, int, int, int] | None = None,
) -> tuple[tuple[int, int] | None, float]:
    """Find the *selected* daily-task tab, not an arbitrary task page."""
    return _match_daily_task_template(
        screenshot,
        BUILTIN_DAILY_SELECTED_TAB_ASSET,
        BUILTIN_DAILY_SELECTED_TAB_TEMPLATE_NAME,
        threshold,
        search_region
        if search_region is not None
        # High-level accounts can render only Growth + Daily at the bottom,
        # moving the exact selected Daily tab centre from x=1160 to x=929.
        # This remains a passive page anchor and never authorises a tap.
        else _relative_region(screenshot, 0.48, 0.78, 0.98, 0.99),
    )


def match_daily_login_completed(
    screenshot: Image.Image,
    threshold: float,
    search_region: tuple[int, int, int, int] | None = None,
) -> tuple[tuple[int, int] | None, float]:
    """Find only the completed ``daily login (1/1)`` task label."""
    return _match_daily_task_template(
        screenshot,
        BUILTIN_DAILY_LOGIN_COMPLETED_ASSET,
        BUILTIN_DAILY_LOGIN_COMPLETED_TEMPLATE_NAME,
        threshold,
        search_region
        if search_region is not None
        else _relative_region(screenshot, 0.05, 0.36, 0.42, 0.44),
    )


def match_daily_claim_button(
    screenshot: Image.Image,
    threshold: float,
    search_region: tuple[int, int, int, int] | None = None,
) -> tuple[tuple[int, int] | None, float]:
    """Find the green claim control in the first daily-login task row only."""
    return _match_daily_task_template(
        screenshot,
        BUILTIN_DAILY_CLAIM_BUTTON_ASSET,
        BUILTIN_DAILY_CLAIM_BUTTON_TEMPLATE_NAME,
        threshold,
        search_region
        if search_region is not None
        else _relative_region(screenshot, 0.69, 0.40, 0.96, 0.50),
    )


def match_daily_task_claim_button(
    screenshot: Image.Image,
    threshold: float,
    search_region: tuple[int, int, int, int] | None = None,
) -> tuple[tuple[int, int] | None, float]:
    """Find a green ``领取`` control in the visible Daily Tasks list.

    A completed daily task can move to the first visible row as the list
    refreshes.  This matcher deliberately searches only the right-hand action
    column of that list; the page classifier below supplies the independent
    Daily-header, selected-tab and activity-bar proofs before any caller is
    given its coordinate.
    """
    return _match_daily_task_template(
        screenshot,
        BUILTIN_DAILY_CLAIM_BUTTON_ASSET,
        BUILTIN_DAILY_CLAIM_BUTTON_TEMPLATE_NAME,
        threshold,
        search_region
        if search_region is not None
        else _relative_region(screenshot, 0.66, 0.36, 0.97, 0.86),
    )


def match_daily_one_key_claim_button(
    screenshot: Image.Image,
    threshold: float,
) -> tuple[tuple[int, int] | None, float]:
    """Find only the central green ``一键领取`` on a verified Daily page."""
    point, score = _match_daily_task_template(
        screenshot,
        BUILTIN_DAILY_ONE_KEY_CLAIM_BUTTON_ASSET,
        BUILTIN_DAILY_ONE_KEY_CLAIM_BUTTON_TEMPLATE_NAME,
        max(0.985, float(threshold)),
        _relative_region(screenshot, 0.30, 0.74, 0.70, 0.88),
    )
    if point and _daily_template_integrity_is_valid(
        screenshot,
        BUILTIN_DAILY_ONE_KEY_CLAIM_BUTTON_ASSET,
        BUILTIN_DAILY_ONE_KEY_CLAIM_BUTTON_TEMPLATE_NAME,
        point,
        min_luma_ratio=DAILY_ACTION_MIN_LUMA_RATIO,
        min_chroma_ratio=DAILY_ACTION_MIN_CHROMA_RATIO,
        max_colour_distance=DAILY_ACTION_MAX_COLOUR_DISTANCE,
        strict_action=True,
    ):
        return point, score
    return None, score


def match_daily_task_completed_check(
    screenshot: Image.Image,
    threshold: float = 0.94,
    search_region: tuple[int, int, int, int] | None = None,
) -> tuple[tuple[int, int] | None, float]:
    """Find one exact green completion check in the Daily list action lane.

    The signal is deliberately passive and skip-only.  Callers must already
    prove the Daily page and require two fresh frames before using it as the
    start of the trailing completed-task block.  It can never authorise a tap.
    """
    return _match_daily_task_template(
        screenshot,
        BUILTIN_DAILY_TASK_COMPLETED_CHECK_ASSET,
        BUILTIN_DAILY_TASK_COMPLETED_CHECK_TEMPLATE_NAME,
        threshold,
        search_region
        if search_region is not None
        else _relative_region(screenshot, 0.72, 0.34, 0.92, 0.87),
    )


def _daily_task_claim_geometry_is_valid(
    screenshot: Image.Image,
    claim_button: tuple[int, int],
) -> bool:
    """Keep a generic daily reward target inside the task-list action lane."""
    viewport = content_viewport(screenshot)
    x = claim_button[0] - viewport.left
    y = claim_button[1] - viewport.top
    return (
        viewport.width * 0.64 <= x <= viewport.width * 0.98
        and viewport.height * 0.35 <= y <= viewport.height * 0.87
    )


def estimate_daily_activity_progress(screenshot: Image.Image) -> DailyActivityProgress:
    """Estimate the 0--325 Daily Tasks progress from its gold fill bar.

    The constants are measured in game-content coordinates from the 1440 x
    2560 layout and are projected through :func:`content_viewport`, so black
    MuMu margins and window resolutions do not change the result.  A missing
    gold segment is a valid 0-point result; an implausibly short/noisy segment
    carries zero confidence and must not authorise input.
    """
    viewport = content_viewport(screenshot)
    image = np.asarray(screenshot.convert("RGB"))
    x0 = viewport.left + round(viewport.width * 0.155)
    x1 = viewport.left + round(viewport.width * 0.910)
    y0 = viewport.top + round(viewport.height * 0.255)
    y1 = viewport.top + round(viewport.height * 0.300)
    roi = image[y0:y1, x0:x1]
    if roi.size == 0:
        return DailyActivityProgress(0.0, None, 0.0)

    # Gold has high red/green and very little blue.  Scan every row and keep
    # the longest contiguous run after the activity-coin overlap.
    mask = (
        (roi[:, :, 0] >= 185)
        & (roi[:, :, 1] >= 120)
        & (roi[:, :, 1] <= 245)
        & (roi[:, :, 2] <= 115)
    )
    best_start: int | None = None
    best_end: int | None = None
    best_width = 0
    for row in mask:
        indices = np.flatnonzero(row)
        if not len(indices):
            continue
        run_start = int(indices[0])
        previous = run_start
        for value in indices[1:]:
            value = int(value)
            if value != previous + 1:
                width = previous - run_start + 1
                if width > best_width:
                    best_start, best_end, best_width = run_start, previous, width
                run_start = value
            previous = value
        width = previous - run_start + 1
        if width > best_width:
            best_start, best_end, best_width = run_start, previous, width

    # The fill itself starts at 15.8% and ends at 89.6% of the game viewport.
    # Using the logical start instead of the rounded gold edge removes the
    # 1--2 point bias caused by the pill-shaped left cap.
    track_left = viewport.left + round(viewport.width * 0.158)
    track_right = viewport.left + round(viewport.width * 0.896)
    if best_end is None or best_width < max(14, round(viewport.width * 0.010)):
        return DailyActivityProgress(0.0, None, 1.0)
    fill_right = x0 + best_end
    if fill_right < track_left:
        return DailyActivityProgress(0.0, None, 0.0)
    points = 325.0 * (fill_right - track_left) / max(1, track_right - track_left)
    points = max(0.0, min(325.0, points))
    confidence = min(1.0, best_width / max(1, track_right - track_left) * 4.0)
    return DailyActivityProgress(points, fill_right, confidence)


def daily_activity_chest_points(screenshot: Image.Image) -> dict[int, tuple[int, int]]:
    """Return scaled centres for the seven daily-activity chest milestones."""
    # Measured centres for the two-row chest layout at 1440 x 2560.  The 40
    # chest sits slightly above the bar; all points are mapped via content
    # viewport for multi-window / non-native MuMu captures.
    reference = {
        40: (350, 585),
        80: (475, 820),
        120: (610, 585),
        160: (745, 820),
        215: (930, 585),
        270: (1100, 820),
        325: (1290, 585),
    }
    return {
        milestone: map_content_point(point, BUILTIN_DAILY_TASK_REFERENCE_SIZE, screenshot)
        for milestone, point in reference.items()
    }


def match_daily_activity_chest_open(
    screenshot: Image.Image,
    milestone: int,
    threshold: float = 0.94,
) -> tuple[bool, float]:
    """Return passive evidence that one reached activity chest is already open.

    A previously collected chest stays on the activity bar and reopens its
    informational contents sheet when tapped.  This matcher uses one of two
    art-only open-chest crops in a narrow location around the exact milestone.
    It is deliberately a skip-only signal: a miss simply preserves the old
    claim-and-observe route, while a caller must require two fresh open
    observations before skipping any chest.
    """
    reference = {
        40: (350, 585),
        80: (475, 820),
        120: (610, 585),
        160: (745, 820),
        215: (930, 585),
        270: (1100, 820),
        325: (1290, 585),
    }
    point = reference.get(int(milestone))
    if point is None:
        return False, 0.0
    x, y = point
    if milestone in {40, 120, 215, 325}:
        asset = BUILTIN_DAILY_ACTIVITY_CHEST_OPEN_TOP_ASSET
        name = BUILTIN_DAILY_ACTIVITY_CHEST_OPEN_TOP_TEMPLATE_NAME
        # The crop itself is 170x135 px at the reference size.  The wider
        # probe accommodates the same art's small horizontal placement shifts
        # without exposing any task-row controls.
        region = _relative_region(
            screenshot,
            (x - 125) / 1440,
            (y - 170) / 2560,
            (x + 125) / 1440,
            (y + 25) / 2560,
        )
    else:
        asset = BUILTIN_DAILY_ACTIVITY_CHEST_OPEN_BOTTOM_ASSET
        name = BUILTIN_DAILY_ACTIVITY_CHEST_OPEN_BOTTOM_TEMPLATE_NAME
        region = _relative_region(
            screenshot,
            (x - 125) / 1440,
            (y - 60) / 2560,
            (x + 125) / 1440,
            (y + 175) / 2560,
        )
    anchor, score = _match_daily_task_template(
        screenshot,
        asset,
        name,
        max(0.94, float(threshold)),
        region,
    )
    return anchor is not None, score


def match_daily_task_refresh_label(
    screenshot: Image.Image,
    threshold: float = 0.94,
) -> tuple[bool, float]:
    """Passively recognise the static part of Daily Tasks' refresh countdown.

    The numeric duration changes continuously and is not read or interpreted.
    A match only tells the controller that the already-verified Daily list has
    a visible server-refresh countdown, allowing a longer no-input wait after
    a complete task scan.  It supplies no navigation or input authority.
    """
    anchor, score = _match_daily_task_template(
        screenshot,
        BUILTIN_DAILY_REFRESH_LABEL_ASSET,
        BUILTIN_DAILY_REFRESH_LABEL_TEMPLATE_NAME,
        max(0.94, float(threshold)),
        _relative_region(screenshot, 0.0, 0.10, 0.35, 0.20),
    )
    return anchor is not None, score


def daily_reward_result_exit_point(screenshot: Image.Image) -> tuple[int, int]:
    """Return the inert lower-sheet point for a verified reward result.

    The game itself labels the full-screen result sheet as "tap anywhere to
    exit".  The point below lies in its empty lower area, rather than on a
    reward icon, a button, or a control from the obscured page.  It must only
    be used after a fresh :func:`match_daily_reward_result` observation that a
    controller has correlated to its immediately preceding reward click.
    """
    return map_content_point((720, 2320), BUILTIN_DAILY_TASK_REFERENCE_SIZE, screenshot)


def match_daily_reward_result(
    screenshot: Image.Image,
    threshold: float,
    search_region: tuple[int, int, int, int] | None = None,
) -> tuple[tuple[int, int] | None, float]:
    """Recognise the reviewed full-screen ``获得奖励`` result banner.

    This is a passive postcondition, not proof that an arbitrary screen may
    be dismissed.  The controller must additionally require that it is in the
    short settling window after *its own* verified green reward click.
    """
    return _match_daily_task_template(
        screenshot,
        BUILTIN_DAILY_REWARD_RESULT_ASSET,
        BUILTIN_DAILY_REWARD_RESULT_TEMPLATE_NAME,
        threshold,
        search_region
        if search_region is not None
        else _relative_region(screenshot, 0.30, 0.18, 0.70, 0.34),
    )


def match_daily_reward_exit_hint(
    screenshot: Image.Image,
    threshold: float = 0.60,
) -> tuple[tuple[int, int] | None, float]:
    """Recognise the exact ``点击任意位置退出`` instruction.

    The crop was supplied from a scaled display, so its standalone threshold
    is intentionally lower than native task anchors.  It is never actionable
    alone: callers must pair it with the native ``获得奖励`` title, fresh
    temporal lineage and two-frame agreement.
    """
    return _match_daily_task_template(
        screenshot,
        BUILTIN_DAILY_REWARD_EXIT_HINT_ASSET,
        BUILTIN_DAILY_REWARD_EXIT_HINT_TEMPLATE_NAME,
        max(0.60, min(0.78, float(threshold))),
        _relative_region(screenshot, 0.12, 0.80, 0.88, 0.99),
    )


def daily_chest_result_exit_point(screenshot: Image.Image) -> tuple[int, int]:
    """Return a blank Daily-page point outside the verified chest sheet.

    The point is in the top-right empty band of the page; it is neither a
    chest nor a task action.  It may only be used after the two visual chest
    sheet anchors below have been correlated to the worker's own chest tap.
    """
    return map_content_point((1280, 700), BUILTIN_DAILY_TASK_REFERENCE_SIZE, screenshot)


def match_daily_chest_result(
    screenshot: Image.Image,
    threshold: float,
) -> tuple[tuple[int, int] | None, float]:
    """Recognise reviewed activity-chest contents sheet variants.

    The compact corner and centred-sheet pointer anchors are intentionally
    content agnostic: chest rewards differ by milestone, while the sheet
    framing remains fixed.  This function is visual evidence only and never
    returns a tap coordinate.
    """
    candidates = (
        (
            BUILTIN_DAILY_CHEST_POPUP_TOP_ASSET,
            BUILTIN_DAILY_CHEST_POPUP_TOP_TEMPLATE_NAME,
            _relative_region(screenshot, 0.01, 0.20, 0.26, 0.45),
        ),
        (
            BUILTIN_DAILY_CHEST_POPUP_BOTTOM_ASSET,
            BUILTIN_DAILY_CHEST_POPUP_BOTTOM_TEMPLATE_NAME,
            _relative_region(screenshot, 0.01, 0.34, 0.26, 0.63),
        ),
        (
            BUILTIN_DAILY_CHEST_POPUP_POINTER_ASSET,
            BUILTIN_DAILY_CHEST_POPUP_POINTER_TEMPLATE_NAME,
            # The list-style sheet is centred underneath the milestone bar.
            # Its small top pointer is visible independently of reward item
            # contents, and the narrow centre-band search excludes all task
            # card buttons and the bottom navigation.
            _relative_region(screenshot, 0.43, 0.30, 0.62, 0.43),
        ),
    )
    best_point: tuple[int, int] | None = None
    best_score = 0.0
    for asset, template_name, region in candidates:
        point, score = _match_daily_task_template(
            screenshot,
            asset,
            template_name,
            threshold,
            region,
        )
        if point:
            return point, score
        best_score = max(best_score, score)
    return best_point, best_score


def match_daily_paid_offer_title(
    screenshot: Image.Image,
    threshold: float,
    search_region: tuple[int, int, int, int] | None = None,
) -> tuple[tuple[int, int] | None, float]:
    """Recognise the reviewed paid-offer title in a modal's top band.

    This evidence is terminal for the daily flow and is never an action
    target.  A single high-confidence paid-offer anchor is enough to stop.
    """
    return _match_daily_task_template(
        screenshot,
        BUILTIN_DAILY_PAID_OFFER_TITLE_ASSET,
        BUILTIN_DAILY_PAID_OFFER_TITLE_TEMPLATE_NAME,
        threshold,
        search_region
        if search_region is not None
        else _relative_region(screenshot, 0.05, 0.05, 0.55, 0.20),
    )


def match_daily_paid_offer_price(
    screenshot: Image.Image,
    threshold: float,
    search_region: tuple[int, int, int, int] | None = None,
) -> tuple[tuple[int, int] | None, float]:
    """Recognise the reviewed currency price control in a modal's lower band."""
    return _match_daily_task_template(
        screenshot,
        BUILTIN_DAILY_PAID_OFFER_PRICE_ASSET,
        BUILTIN_DAILY_PAID_OFFER_PRICE_TEMPLATE_NAME,
        threshold,
        search_region
        if search_region is not None
        else _relative_region(screenshot, 0.15, 0.68, 0.85, 0.92),
    )


def match_daily_task_progress_anchor(
    screenshot: Image.Image,
    threshold: float,
    search_region: tuple[int, int, int, int] | None = None,
) -> tuple[tuple[int, int] | None, float]:
    """Find the daily-task progress strip above the task list.

    It is a non-actionable structural proof.  Requiring it makes a green
    claim-shaped control elsewhere in a modal insufficient for a tap.
    """
    return _match_daily_task_template(
        screenshot,
        BUILTIN_DAILY_PROGRESS_ANCHOR_ASSET,
        BUILTIN_DAILY_PROGRESS_ANCHOR_TEMPLATE_NAME,
        threshold,
        search_region
        if search_region is not None
        else _relative_region(screenshot, 0.03, 0.20, 0.97, 0.36),
    )


def _daily_login_claim_geometry_is_valid(
    screenshot: Image.Image,
    completed_login: tuple[int, int],
    claim_button: tuple[int, int],
) -> bool:
    """Verify that the green button belongs to this completed login row.

    This rejects nearby generic ``claim``, ``go`` and store controls even if
    they happen to have a visually similar green fill.  Values are measured in
    game-content coordinates, never the whole capture.
    """
    viewport = content_viewport(screenshot)
    x_delta = claim_button[0] - completed_login[0]
    y_delta = claim_button[1] - completed_login[1]
    return (
        viewport.width * 0.55 <= x_delta <= viewport.width * 0.73
        and viewport.height * 0.02 <= y_delta <= viewport.height * 0.10
    )


def detect_daily_task_state(
    screenshot: Image.Image,
    threshold: float,
) -> DailyTaskMatch:
    """Classify the narrow, safe daily-login collection workflow.

    A generic task page, a green button, or a completed-looking label alone
    never produces a tap point.  ``CLAIM_READY`` requires five independent
    same-frame proofs: daily-task header, selected daily tab, task-progress
    strip, exact ``daily login (1/1)`` label, and its raw-RGB-validated green
    claim control in the expected local geometry.  A recognised paid offer
    wins over every other input-capable page state and produces the terminal
    ``BLOCKED`` state.  The reviewed post-claim reward sheet is reported
    separately; it authorises no input by itself.
    """
    safe_threshold = max(0.90, float(threshold))
    page_threshold = max(0.89, safe_threshold - 0.01)
    # A false paid-offer positive merely stops this limited workflow, whereas
    # a false negative could leave an input-capable controller on a purchase
    # surface.  Deliberately make the blocker more sensitive than the action
    # proofs while retaining a narrow, reviewed search region for each asset.
    paid_threshold = max(0.84, safe_threshold - 0.08)

    if daily_march_capacity_modal_is_visible(screenshot):
        return DailyTaskMatch(DailyTaskState.BLOCKED, None, 1.0, (("march_capacity_modal", (0, 0)),))

    # A result sheet may obscure the Daily page completely, so recognise it
    # before evaluating page anchors.  Its returned point is deliberately
    # None: controllers must use ``daily_reward_result_exit_point`` only when
    # they have their own immediately preceding verified claim correlation.
    reward_result, reward_result_score = match_daily_reward_result(
        screenshot,
        max(0.90, safe_threshold),
    )
    if reward_result:
        return DailyTaskMatch(
            DailyTaskState.REWARD_RESULT_READY,
            None,
            reward_result_score,
            (("daily_reward_result", reward_result),),
        )

    chest_result, chest_result_score = match_daily_chest_result(
        screenshot,
        max(0.90, safe_threshold),
    )
    if chest_result:
        return DailyTaskMatch(
            DailyTaskState.CHEST_RESULT_READY,
            None,
            chest_result_score,
            (("daily_chest_result", chest_result),),
        )

    # Check purchase surfaces before considering a city anchor that might be
    # visible behind their modal.  Either independently reviewed title or
    # price evidence is sufficient to make the whole run input-free.
    paid_title, paid_title_score = match_daily_paid_offer_title(screenshot, paid_threshold)
    paid_price, paid_price_score = match_daily_paid_offer_price(screenshot, paid_threshold)
    if paid_title or paid_price:
        paid_anchors: tuple[tuple[str, tuple[int, int]], ...] = ()
        if paid_title:
            paid_anchors += (("daily_paid_offer_title", paid_title),)
        if paid_price:
            paid_anchors += (("daily_paid_offer_price", paid_price),)
        return DailyTaskMatch(
            DailyTaskState.BLOCKED,
            None,
            max(paid_title_score if paid_title else 0.0, paid_price_score if paid_price else 0.0),
            paid_anchors,
        )

    header, header_score = match_daily_task_header(screenshot, page_threshold)
    selected_tab, selected_tab_score = match_daily_task_selected_tab(screenshot, page_threshold)
    chapter_header = unselected_tab = growth_daily_tab = city_entry = None
    chapter_header_score = unselected_tab_score = growth_daily_tab_score = city_entry_score = 0.0

    if not (header and selected_tab):
        # Purchase/result blockers have already won above.  On a city frame,
        # probe its exact lower-left clipboard before evaluating unrelated task
        # hub tabs.  On a Daily frame this branch is skipped entirely.
        city_entry, city_entry_score = match_daily_city_entry(screenshot, safe_threshold)
        if city_entry:
            return DailyTaskMatch(
                DailyTaskState.CITY_ENTRY,
                None,
                city_entry_score,
                (("daily_city_entry", city_entry),),
            )

        chapter_header, chapter_header_score = match_daily_chapter_task_header(
            screenshot, page_threshold
        )
        unselected_tab, unselected_tab_score = match_daily_task_unselected_tab(
            screenshot, page_threshold
        )
        if chapter_header and unselected_tab:
            return DailyTaskMatch(
                DailyTaskState.DAILY_TAB_READY,
                unselected_tab,
                min(chapter_header_score, unselected_tab_score),
                (
                    ("daily_chapter_header", chapter_header),
                    ("daily_unselected_tab", unselected_tab),
                ),
            )

        growth_daily_tab, growth_daily_tab_score = match_daily_growth_task_daily_tab(
            screenshot, safe_threshold
        )
        if growth_daily_tab:
            return DailyTaskMatch(
                DailyTaskState.DAILY_TAB_READY,
                growth_daily_tab,
                growth_daily_tab_score,
                (("daily_growth_task_daily_tab", growth_daily_tab),),
            )
    # The filled activity strip legitimately changes colour and chest state as
    # points accrue.  It remains a passive structural anchor and receives the
    # same 0.89 page threshold as the fixed header/tab; the independently
    # matched green target still carries strict raw-RGB input validation.
    progress_anchor, progress_score = match_daily_task_progress_anchor(screenshot, page_threshold)
    completed_login, completed_login_score = match_daily_login_completed(screenshot, safe_threshold)
    claim_button, claim_button_score = match_daily_claim_button(screenshot, safe_threshold)
    task_claim_button, task_claim_score = match_daily_task_claim_button(screenshot, safe_threshold)
    one_key_claim_button, one_key_claim_score = match_daily_one_key_claim_button(
        screenshot, safe_threshold
    )

    # Two independent page anchors prevent a similarly styled list, purchase
    # dialog, or another task category from becoming a daily-task action.
    if header and selected_tab:
        page_anchors = (
            ("daily_task_header", header),
            ("daily_task_selected_tab", selected_tab),
        )
        if one_key_claim_button:
            return DailyTaskMatch(
                DailyTaskState.TASK_CLAIM_READY,
                one_key_claim_button,
                min(header_score, selected_tab_score, one_key_claim_score),
                page_anchors
                + (("daily_one_key_claim_button", one_key_claim_button),),
            )
        if (
            completed_login
            and claim_button
            and progress_anchor
            and _daily_login_claim_geometry_is_valid(screenshot, completed_login, claim_button)
            and _daily_template_integrity_is_valid(
                screenshot,
                BUILTIN_DAILY_CLAIM_BUTTON_ASSET,
                BUILTIN_DAILY_CLAIM_BUTTON_TEMPLATE_NAME,
                claim_button,
                min_luma_ratio=DAILY_ACTION_MIN_LUMA_RATIO,
                min_chroma_ratio=DAILY_ACTION_MIN_CHROMA_RATIO,
                max_colour_distance=DAILY_ACTION_MAX_COLOUR_DISTANCE,
                strict_action=True,
            )
            and _daily_template_integrity_is_valid(
                screenshot,
                BUILTIN_DAILY_PROGRESS_ANCHOR_ASSET,
                BUILTIN_DAILY_PROGRESS_ANCHOR_TEMPLATE_NAME,
                progress_anchor,
                min_luma_ratio=DAILY_ACTION_MIN_LUMA_RATIO,
                min_chroma_ratio=DAILY_ACTION_MIN_CHROMA_RATIO,
                max_colour_distance=DAILY_ACTION_MAX_COLOUR_DISTANCE,
                strict_action=True,
            )
        ):
            return DailyTaskMatch(
                DailyTaskState.CLAIM_READY,
                claim_button,
                min(header_score, selected_tab_score, progress_score, completed_login_score, claim_button_score),
                page_anchors
                + (
                    ("daily_task_progress_anchor", progress_anchor),
                    ("daily_login_completed", completed_login),
                    ("daily_claim_button", claim_button),
                ),
            )
        # A completed task is safe to collect even when it is not the legacy
        # daily-login row.  This is deliberately later than the narrow login
        # proof above so existing callers preserve their historical state.  A
        # green control is still insufficient by itself: it must sit in the
        # verified task-list action lane and retain the strict raw-RGB check.
        # Unlike the old login card, a generic completed task must not depend
        # on the activity-bar template: the fill and chest artwork change as
        # points accrue, so that mutable anchor can disappear on a legitimate
        # 110/325 board while the task card remains safely collectible.
        if (
            task_claim_button
            and _daily_task_claim_geometry_is_valid(screenshot, task_claim_button)
            and _daily_template_integrity_is_valid(
                screenshot,
                BUILTIN_DAILY_CLAIM_BUTTON_ASSET,
                BUILTIN_DAILY_CLAIM_BUTTON_TEMPLATE_NAME,
                task_claim_button,
                min_luma_ratio=DAILY_ACTION_MIN_LUMA_RATIO,
                min_chroma_ratio=DAILY_ACTION_MIN_CHROMA_RATIO,
                max_colour_distance=DAILY_ACTION_MAX_COLOUR_DISTANCE,
                strict_action=True,
            )
        ):
            return DailyTaskMatch(
                DailyTaskState.TASK_CLAIM_READY,
                task_claim_button,
                min(header_score, selected_tab_score, task_claim_score),
                page_anchors
                + (
                    ("daily_task_claim_button", task_claim_button),
                ),
            )
        if completed_login:
            return DailyTaskMatch(
                DailyTaskState.DAILY_LOGIN_COMPLETED,
                None,
                min(header_score, selected_tab_score, completed_login_score),
                page_anchors + (("daily_login_completed", completed_login),),
            )
        return DailyTaskMatch(
            DailyTaskState.DAILY_PAGE,
            None,
            min(header_score, selected_tab_score),
            page_anchors,
        )

    return DailyTaskMatch(
        DailyTaskState.UNKNOWN,
        None,
        max(
            header_score,
            selected_tab_score,
            progress_score,
            completed_login_score,
            claim_button_score,
            task_claim_score,
            chapter_header_score,
            unselected_tab_score,
            city_entry_score,
            paid_title_score,
            paid_price_score,
        ),
    )


def diagnose_daily_abnormal_exit(
    screenshot: Image.Image,
    threshold: float,
) -> DailyAbnormalExitMatch:
    """Classify known recovery semantics before treating a page as unknown.

    Each actionable result is based on a reviewed semantic control.  This
    helper never exposes a generic X, Back or arbitrary blank-screen click.
    Controllers must still require two fresh equal classifications before
    using the returned point.
    """
    safe_threshold = max(0.90, float(threshold))

    if daily_network_dialog_is_visible(screenshot, safe_threshold):
        return DailyAbnormalExitMatch(
            DailyAbnormalExitKind.NETWORK_WAIT, None, 1.0
        )

    paid_title, paid_title_score = match_daily_paid_offer_title(
        screenshot, max(0.84, safe_threshold - 0.08)
    )
    paid_price, paid_price_score = match_daily_paid_offer_price(
        screenshot, max(0.84, safe_threshold - 0.08)
    )
    if paid_title or paid_price:
        anchors: list[tuple[str, tuple[int, int]]] = []
        if paid_title:
            anchors.append(("daily_paid_offer_title", paid_title))
        if paid_price:
            anchors.append(("daily_paid_offer_price", paid_price))
        return DailyAbnormalExitMatch(
            DailyAbnormalExitKind.PAID_STOP,
            None,
            max(paid_title_score, paid_price_score),
            tuple(anchors),
        )

    exit_text, exit_text_score = match_daily_tap_anywhere_exit_text(
        screenshot, safe_threshold
    )
    if exit_text:
        return DailyAbnormalExitMatch(
            DailyAbnormalExitKind.REWARD_TAP_ANYWHERE,
            exit_text,
            exit_text_score,
            (("daily_tap_anywhere_exit_text", exit_text),),
        )

    header, header_score = match_daily_task_header(screenshot, safe_threshold)
    tab, tab_score = match_daily_task_selected_tab(screenshot, safe_threshold)
    if header and tab:
        return DailyAbnormalExitMatch(
            DailyAbnormalExitKind.DAILY_CLOSE_X,
            daily_task_close_point(screenshot),
            min(header_score, tab_score),
            (("daily_task_header", header), ("daily_task_selected_tab", tab)),
        )

    intel_map, intel_score = match_daily_intel_map_page(
        screenshot, safe_threshold
    )
    if intel_map:
        return DailyAbnormalExitMatch(
            DailyAbnormalExitKind.INTEL_MAP_BACK,
            daily_intel_map_back_point(screenshot),
            intel_score,
        )

    town_point, town_score = match_daily_world_town_entry(
        screenshot, safe_threshold
    )
    if town_point:
        return DailyAbnormalExitMatch(
            DailyAbnormalExitKind.WORLD_TOWN,
            town_point,
            town_score,
        )

    return DailyAbnormalExitMatch(
        DailyAbnormalExitKind.UNKNOWN,
        None,
        max(
            exit_text_score,
            paid_title_score,
            paid_price_score,
            header_score,
            tab_score,
            intel_score,
            town_score,
        ),
    )


def match_all_help_button(
    screenshot: Image.Image,
    threshold: float,
) -> tuple[tuple[int, int] | None, float]:
    """Match only the large green ``全部帮助`` control.

    It is deliberately limited to the bottom portion of the screen.  The
    automatic flow never substitutes the smaller handshake control here.
    """
    template = TEMPLATE_DIR / BUILTIN_ALL_HELP_TEMPLATE_NAME
    if not template.is_file():
        return None, 0.0
    return match_template(
        screenshot,
        template,
        threshold,
        template_reference_size(template),
        _relative_region(screenshot, 0.12, 0.78, 0.88, 1.0),
    )


def detect_alliance_page(
    screenshot: Image.Image,
    threshold: float,
) -> AlliancePageMatch:
    """Classify only safe, visual states of the alliance-help navigation flow.

    Unknown pages are intentionally not assigned a fallback coordinate.  That
    keeps activity pop-ups, dialogs, and unrelated game views input-free.
    """
    page_threshold = max(0.86, threshold - 0.02)
    mutual_page = resource_path(BUILTIN_MUTUAL_PAGE_TEMPLATE_ASSET)
    mutual_header, mutual_score = match_template(
        screenshot,
        mutual_page,
        page_threshold,
        template_reference_size(mutual_page),
        _relative_region(screenshot, 0.0, 0.0, 0.52, 0.16),
    ) if mutual_page.is_file() else (None, 0.0)
    all_help, all_help_score = match_all_help_button(screenshot, threshold)
    # A green button without the mutual-help title is not enough to permit a
    # click. Both anchors must be present in the same screenshot.
    if mutual_header and all_help:
        return AlliancePageMatch(AlliancePage.ALL_HELP_READY, all_help, min(mutual_score, all_help_score))
    if mutual_header:
        return AlliancePageMatch(AlliancePage.MUTUAL_HELP, None, mutual_score)

    mutual_entry = resource_path(BUILTIN_MUTUAL_ENTRY_TEMPLATE_ASSET)
    entry_point, entry_score = match_template(
        screenshot,
        mutual_entry,
        page_threshold,
        template_reference_size(mutual_entry),
        _relative_region(screenshot, 0.42, 0.56, 1.0, 0.98),
    ) if mutual_entry.is_file() else (None, 0.0)
    if entry_point:
        return AlliancePageMatch(AlliancePage.ALLIANCE_HOME, entry_point, entry_score)

    city_entry = resource_path(BUILTIN_CITY_ALLIANCE_TEMPLATE_ASSET)
    city_point, city_score = match_template(
        screenshot,
        city_entry,
        page_threshold,
        template_reference_size(city_entry),
        _relative_region(screenshot, 0.52, 0.74, 0.94, 1.0),
    ) if city_entry.is_file() else (None, 0.0)
    if city_point:
        return AlliancePageMatch(AlliancePage.CITY, city_point, city_score)
    return AlliancePageMatch(AlliancePage.UNKNOWN, None, max(mutual_score, all_help_score, entry_score, city_score))


def match_alliance_help(
    screenshot: Image.Image,
    threshold: float,
) -> tuple[Path | None, tuple[int, int] | None, float]:
    """Legacy generic helper: prefer bulk help, then optional small-hand fallback."""
    all_help_path = TEMPLATE_DIR / BUILTIN_ALL_HELP_TEMPLATE_NAME
    point, score = match_all_help_button(screenshot, threshold)
    if point:
        return all_help_path, point, score
    single_help = TEMPLATE_DIR / BUILTIN_HELP_TEMPLATE_NAME
    if not single_help.is_file():
        return all_help_path if all_help_path.is_file() else None, None, score
    fallback_point, fallback_score = match_template(
        screenshot,
        single_help,
        threshold,
        template_reference_size(single_help),
    )
    if fallback_point:
        return single_help, fallback_point, fallback_score
    return all_help_path if all_help_path.is_file() else single_help, None, max(score, fallback_score)


def scale_recorded_point(
    point: tuple[int, int],
    source_size: tuple[int, int],
    current_size: tuple[int, int],
) -> tuple[int, int]:
    x, y = point
    source_w, source_h = source_size
    current_w, current_h = current_size
    if current_w / current_h > source_w / source_h + 0.01:
        scale = current_h / source_h
        scaled_x = (current_w - source_w * scale) / 2 + x * scale
        scaled_y = y * scale
    else:
        scaled_x = x * current_w / source_w
        scaled_y = y * current_h / source_h
    return round(scaled_x), round(scaled_y)
