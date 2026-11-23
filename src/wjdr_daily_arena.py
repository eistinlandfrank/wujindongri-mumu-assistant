"""Reviewed free challenge route for the Expedition Arena."""

from __future__ import annotations

import time

import cv2
import numpy as np

from wjdr_backend import map_content_point, match_arena_setup, match_daily_hero_recruit_summary_exit
from wjdr_daily_visuals import _find
from wjdr_daily_timer import _read_ocr_lines


def _find_arena(frame, name, region):
    return _find(frame, f"daily_arena_expedition_{name}.png", region, .93, 22.)[0]


def _point(frame, x, y):
    return map_content_point((x, y), (1440, 2560), frame)


def _crop(frame, box):
    return frame.crop((*_point(frame, *box[:2]), *_point(frame, *box[2:])))


def expedition_arena_home(frame):
    return _find_arena(frame, "home_title", (.09, .006, .54, .058))


def expedition_arena_list_close(frame):
    if (_find_arena(frame, "list_title", (.36, .118, .64, .180))
            and _find_arena(frame, "free_label", (.27, .730, .60, .779))):
        return _point(frame, 1332, 380)
    return None


def _power_color(frame, y):
    rgb = np.asarray(_crop(frame, (356, y - 32, 570, y + 34)).convert("RGB"))
    h, s, v = cv2.cvtColor(rgb, cv2.COLOR_RGB2HSV).transpose(2, 0, 1)
    bright = (s >= 120) & (v >= 115)
    green = float(np.mean(bright & (h > 33) & (h < 87)))
    red = float(np.mean(bright & ((h < 10) | (h > 170))))
    if green >= .025 and green > red * 4:
        return "green"
    if red >= .025 and red > green * 4:
        return "red"
    return None


def _arena_list(frame, read_number):
    title = _find_arena(frame, "list_title", (.36, .118, .64, .180))
    label = _find_arena(frame, "free_label", (.27, .730, .60, .779))
    if not title or not label:
        return None
    reading = read_number(frame, (848, 1897, 902, 1963), "dark")
    if reading is None or not 0 <= reading[0] <= 5:
        return None
    rows = []
    for fight_y, power_y in zip((720, 976, 1232, 1488, 1744), (779, 1035, 1292, 1548, 1803)):
        fight = _find_arena(frame, "fight", (.80, (fight_y - 77) / 2560, .93, (fight_y + 77) / 2560))
        color = _power_color(frame, fight_y) or _power_color(frame, power_y)
        rows.append((color, fight))
    return reading[0], tuple(rows)


def run_expedition_arena(capture, tap, wait, log, read_number, *, start_at_list=False):
    """Consume the free attempts, without using the attempts-plus or diamonds."""
    def pair(probe, seconds=8.0):
        deadline = time.monotonic() + seconds
        previous = None
        while time.monotonic() < deadline and not wait(0):
            frame = capture()
            value = probe(frame)
            if value is not None and value == previous:
                return frame, value
            previous = value
            if wait(.10):
                break
        return None

    def list_state(frame):
        return _arena_list(frame, read_number)

    def ordinary_refresh(frame):
        return _find_arena(frame, "refresh", (.32, .787, .68, .843))

    def paid_refresh_visible(frame):
        lines = _read_ocr_lines(_crop(frame, (435, 2010, 1014, 2180)), timeout=2.0)
        joined = "".join("".join(lines).split())
        diamond = _find_arena(frame, "diamond", (.30, .783, .71, .852))
        return "刷新" in joined and ("钻石" in joined or diamond is not None)

    def deploy_point(frame):
        title = _find(frame, "daily_arena_setup_title_live.png", (.09, .005, .36, .073), .93, 22.)[0]
        # Older title assets can use a different reference size. The exact
        # deployment label and proven setup-state title provide alternatives.
        deploy = _find_arena(frame, "deploy", (.12, .904, .41, .953))
        if not deploy:
            return None
        if title or match_arena_setup(frame, require_power_advantage=False):
            return deploy
        return None

    if not start_at_list:
        home = pair(lambda frame: _find_arena(frame, "challenge", (.39, .92, .62, .975))
                    if expedition_arena_home(frame) else None)
        if not home or wait(0):
            return False
        tap(*home[1])

    view = pair(list_state)
    for _ in range(5):
        if view is None or wait(0):
            return False
        frame, (remaining, rows) = view
        if remaining == 0:
            break
        opponent = None
        red_fallback = False
        while not wait(0):
            opponent = next((button for color, button in rows if color == "green" and button), None)
            if opponent is not None:
                break
            if not all(color == "red" and button for color, button in rows):
                log("竞技场战力颜色未完整确认，保留当前次数。")
                return False
            refresh_action = pair(ordinary_refresh, 1.2)
            if refresh_action:
                if wait(0):
                    return False
                before = np.asarray(_crop(refresh_action[0], (105, 620, 1020, 1830)).resize((60, 70)), dtype=np.int16)
                tap(*refresh_action[1])

                def refreshed(image):
                    rows_after = list_state(image)
                    if not rows_after or rows_after[0] != remaining:
                        return None
                    after = np.asarray(_crop(image, (105, 620, 1020, 1830)).resize((60, 70)), dtype=np.int16)
                    return rows_after if np.abs(before - after).mean() > 3 else None

                updated = pair(refreshed)
                if not updated:
                    return False
                _, (_, rows) = updated
                continue
            paid = pair(lambda image: True if list_state(image) is not None and paid_refresh_visible(image) else None, 6.0)
            if not paid:
                log("竞技场未确认免费刷新或钻石刷新状态，保留当前次数。")
                return False
            opponent = rows[-1][1]
            red_fallback = True
            break
        if opponent is None or wait(0):
            return False
        tap(*opponent)
        deploy = pair(deploy_point)
        if not deploy or wait(0):
            return False
        tap(*deploy[1])
        setup = pair(lambda image: value.battle_point if (value := match_arena_setup(
            image, require_power_advantage=not red_fallback)) else None)
        if not setup or wait(0):
            return False
        tap(*setup[1])
        result = pair(lambda image: _find_arena(image, "exit", (.30, .931, .70, .977))
                      or match_daily_hero_recruit_summary_exit(image, .90, at_phrase=True)[0], 26.0)
        if not result or wait(0):
            return False
        tap(*result[1])
        view = pair(lambda image: value if (value := list_state(image)) and value[0] == remaining - 1 else None)
        if not view:
            return False
        log(f"竞技场已一键上阵、结算一场，免费次数 {view[1][0]}。")
    if view is None or view[1][0] != 0:
        return False
    chest = pair(lambda image: _find_arena(image, "daily_chest", (.111, .816, .214, .855))
                 if expedition_arena_list_close(image) else None, 1.2)
    if chest and not wait(0):
        tap(*_point(chest[0], 230, 1994))
        result = pair(lambda image: match_daily_hero_recruit_summary_exit(image, .90, at_phrase=True)[0], 6.0)
        if not result or wait(0):
            return False
        tap(*result[1])
        if not pair(expedition_arena_list_close):
            return False
        log("竞技场 5/5 每日挑战宝箱已领取。")
    return True
