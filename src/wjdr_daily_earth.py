"""Live recognition and free retries for the Labyrinth."""

from __future__ import annotations

import time

from wjdr_daily_visuals import _find
from wjdr_backend import (
    _DAILY_MISSION_GO_SPECS,
    _USER_DOCUMENT_DAILY_MISSION_GO_SPECS,
    map_content_point,
)


def _earth_anchor(frame, name, region):
    return _find(frame, f"daily_earth_{name}.png", region, .92, 21.0)[0]


def earth_defeat(frame, read_number):
    if not _earth_anchor(frame, "defeat", (.408, .235, .599, .316)):
        return None
    if (_earth_anchor(frame, "countdown", (.30, .704, .558, .753))
            and _earth_anchor(frame, "retry_disabled", (.64, .753, .82, .815))):
        return 0, None
    if not _earth_anchor(frame, "remaining", (.31, .70, .636, .751)):
        return None
    reading = read_number(frame, (900, 1827, 965, 1898), "white")
    if reading is None or reading[1] < .86 or not 0 <= reading[0] < 5:
        return None
    retry = _earth_anchor(frame, "retry", (.64, .753, .82, .815))
    return reading[0], retry


def confirm_earth_view(capture, wait, recognize, timeout, *, tolerate_occlusion=False):
    deadline = time.monotonic() + timeout
    previous = None
    observed_at = 0.
    while time.monotonic() < deadline and not wait(0):
        frame = capture()
        value = recognize(frame)
        now = time.monotonic()
        if value is not None:
            if value == previous and (not tolerate_occlusion or now - observed_at < 1.5):
                return frame, value
            previous, observed_at = value, now
        elif not tolerate_occlusion:
            previous = None
        if wait(.14):
            break
    return None


def retry_earth_defeat(capture, tap, wait, read_number, expected_attempts=None):
    """Return the verified count and whether a retry was sent."""
    view = confirm_earth_view(capture, wait, lambda frame: earth_defeat(frame, read_number), 2.5)
    if view is None:
        return None
    _, (attempts, retry) = view
    if (attempts == 0 or retry is None or wait(0)
            or (expected_attempts is not None and attempts != expected_attempts)):
        return attempts, False
    tap(*retry)
    return attempts, True


def earth_battle_skip(frame):
    return _earth_anchor(frame, "skip", (.79, .105, .99, .17))


def earth_victory_action(frame):
    if not _find(frame, "daily_earth_victory.png", (.39, .23, .62, .31), .85, 21.)[0]:
        return None
    point = _earth_anchor(frame, "next_stage", (.63, .659, .83, .72))
    if point:
        return "next", point
    point = _earth_anchor(frame, "next_chapter", (.59, .659, .87, .72))
    return ("chapter", point) if point else None


def earth_victory_next(frame):
    action = earth_victory_action(frame)
    return action[1] if action else None


def earth_map(frame):
    return _earth_anchor(frame, "map_title", (.105, .006, .34, .052))


def earth_daily_go(frame, match_go):
    title = _earth_anchor(frame, "earth_daily_card", (.05, .37, .49, .766))
    if title is None:
        return None
    x, y = title
    width, height = frame.size
    point, _score = match_go(
        frame, .95, (round(width * .70), y, round(width * .975), min(height, y + round(height * .094))),
        (*_DAILY_MISSION_GO_SPECS, *_USER_DOCUMENT_DAILY_MISSION_GO_SPECS),
    )
    return point


def earth_hero_entry(frame):
    if (earth_map(frame)
            and _earth_anchor(frame, "heroes", (.53, .216, .76, .253))
            and _earth_anchor(frame, "heroes_open", (.61, .146, .69, .206))):
        return map_content_point((930, 450), (1440, 2560), frame)
    return None


def earth_hero_stage(frame, read_number, zone="hero"):
    if not _earth_anchor(frame, f"{zone}_title", (.105, .006, .34, .052)):
        return None
    if (_earth_anchor(frame, "stage_countdown", (.31, .880, .55, .921))
            and _earth_anchor(frame, "challenge_disabled", (.425, .924, .581, .985))):
        return "empty", 0
    x, y = map_content_point((480, 2455), (1440, 2560), frame)
    r, g, b = frame.getpixel((x, y))[:3]
    if (g > 130 and g > 1.3 * r and g > 1.3 * b
            and _earth_anchor(frame, "sweep_label", (.30, .744, .49, .789))):
        return "sweep", 0
    if (b > 160 and b > g > r
            and _earth_anchor(frame, "challenge_label", (.30, .744, .49, .789))):
        reading = read_number(frame, (895, 2266, 949, 2344), "white")
        has_counter = _find(frame, "daily_earth_stage_remaining.png", (.32, .88, .629, .92), .87, 21.)[0]
        if reading and 1 <= reading[0] <= 5 and (reading[1] >= .86 or (has_counter and reading[1] >= .83)):
            return "challenge", reading[0]
    return None


def earth_sweep_claim(frame):
    if _earth_anchor(frame, "sweep_reward", (.33, .307, .68, .368)):
        return _earth_anchor(frame, "sweep_claim", (.43, .65, .57, .71))
    return None


def earth_stage_close(frame, zone="hero"):
    if _earth_anchor(frame, f"{zone}_title", (.105, .006, .34, .052)):
        return _earth_anchor(frame, "stage_close", (.90, .006, .99, .063))
    return None


def earth_dispatch(frame, zone="hero"):
    if _earth_anchor(frame, "setup", (.105, .006, .36, .059)) or (
        zone in ("beasts", "gems") and _earth_anchor(frame, f"{zone}_setup_title", (.105, .006, .34, .052))
        and _earth_anchor(frame, f"{zone}_setup", (.10, .16, .90, .22))
    ):
        return _earth_anchor(frame, "dispatch", (.65, .898, .82, .981))
    return None


def drain_earth_defeats(capture, tap, wait, log, read_number, first_attempts):
    """Retry only once per verified decrease; a changed result must be read."""
    for expected in range(first_attempts, -1, -1):
        result = retry_earth_defeat(capture, tap, wait, read_number, expected)
        if result != (expected, expected > 0):
            return False
        if expected == 0:
            log("地心挑战今日剩余失败次数已确认归零。")
            return True
        log(f"地心挑战剩余 {expected} 次，已点击重试。")
        skip = confirm_earth_view(capture, wait, earth_battle_skip, 4.0)
        if skip is not None and not wait(0):
            tap(*skip[1])
        settled = confirm_earth_view(
            capture, wait,
            lambda frame: expected - 1
            if (result := earth_defeat(frame, read_number)) and result[0] == expected - 1
            else None,
            7.0,
        )
        if settled is None:
            log("地心挑战结算尚未确认，保留当前状态。")
            return False
    return False


def run_earth_hero_stage(capture, tap, wait, log, read_number, zone="hero"):
    """Consume the zone's free failure attempts and collect its sweep reward."""
    def pair(probe, timeout=6., *, occlusion=False):
        return confirm_earth_view(capture, wait, probe, timeout, tolerate_occlusion=occlusion)

    def stage(frame):
        return earth_hero_stage(frame, read_number, zone)

    def battle_result(frame):
        defeat = earth_defeat(frame, read_number)
        if defeat is not None:
            return "defeat", defeat
        return earth_victory_action(frame)

    def settle_battle(previous=None):
        departed = previous is None
        skipped = False

        def observe(frame):
            nonlocal departed
            result = battle_result(frame)
            if result != previous:
                departed = True
            if departed:
                if result:
                    return "result", result
                if not skipped and (skip := earth_battle_skip(frame)):
                    return "skip", skip
            return None

        observed = pair(observe, 10.)
        if observed and observed[1][0] == "skip" and not wait(0):
            tap(*observed[1][1])
            skipped = True
            observed = pair(observe, 8.)
        return observed[1][1] if observed and observed[1][0] == "result" else None

    swept = False
    attempts = None
    result = None
    for _ in range(40):
        if wait(0):
            return False
        if result is None:
            current = pair(stage, occlusion=True)
            if not current:
                return False
            status, count = current[1]
            if status == "empty":
                log("地心探险已确认无剩余次数。")
                return True
            if (status == "sweep" and swept) or wait(0):
                return False
            tap(*map_content_point((720, 2430), (1440, 2560), current[0]))
            if status == "sweep":
                swept = True
                reward = pair(earth_sweep_claim)
                if not reward or wait(0):
                    return False
                tap(*reward[1])
                log("已领取地心探险扫荡奖励。")
                continue
            deploy = pair(lambda frame: earth_dispatch(frame, zone))
            if not deploy or wait(0):
                return False
            tap(*deploy[1])
            attempts = count
            result = settle_battle()
            if result is None:
                return False
            continue

        kind, point = result
        if kind == "defeat":
            remaining, retry = point
            if remaining != attempts - 1:
                log(f"地心探险剩余次数未按预期变化，预期 {attempts - 1}，识别 {remaining}。")
                return False
            log(f"地心探险剩余失败次数 {remaining}。")
            if remaining == 0:
                return True
            if not retry or wait(0):
                return False
            tap(*retry)
            attempts = remaining
        else:
            if wait(0):
                return False
            tap(*point)
            log("地心探险已胜利，继续挑战。")
            if kind == "chapter":
                result = None
                continue
        result = settle_battle(result)
        if result is None:
            return False
    log("地心探险本轮已达到过关复核上限。")
    return False


EARTH_ZONE_LABELS = {"hero": "英雄之地", "beasts": "群兽洞窟", "gems": "宝石矿洞"}


def earth_zone_entry(frame, zone):
    if zone == "hero":
        return earth_hero_entry(frame)
    if not earth_map(frame):
        return None
    landmarks = {
        "beasts": ((.20, .356, .38, .393), (411, 753)),
        "gems": ((.60, .467, .80, .511), (1018, 1047)),
    }
    region, point = landmarks[zone]
    if _earth_anchor(frame, f"{zone}_open", region):
        return map_content_point(point, (1440, 2560), frame)
    return None


def earth_stage_back(frame, zone):
    if _earth_anchor(frame, f"{zone}_title", (.105, .006, .34, .052)):
        name = "gems_stage_back" if zone == "gems" else "stage_back"
        return _earth_anchor(frame, name, (.005, .004, .110, .057))
    return None


def run_earth_from_map(capture, tap, back, wait, log, read_number, city_entry, town_entry):
    """Run the recognized open zones and return through verified navigation."""
    def proof(probe, timeout=3.):
        return confirm_earth_view(capture, wait, probe, timeout)

    zones = proof(
        lambda frame: tuple(zone for zone in EARTH_ZONE_LABELS if earth_zone_entry(frame, zone))
        if earth_map(frame) else None, 5.,
    )
    finished = bool(zones and zones[1])
    if zones:
        for zone in zones[1]:
            entry = proof(lambda frame: earth_zone_entry(frame, zone))
            if not entry or wait(0):
                return "unconfirmed", None
            tap(*entry[1])
            log(f"地心探险已进入{EARTH_ZONE_LABELS[zone]}。")
            zone_done = run_earth_hero_stage(capture, tap, wait, log, read_number, zone)
            finished = finished and zone_done
            exhausted = proof(lambda frame: True if earth_defeat(frame, read_number) == (0, None) else None, 1.)
            if exhausted and not wait(0):
                back()
            stage = proof(lambda frame: earth_stage_back(frame, zone), 2.)
            if stage and not wait(0):
                tap(*stage[1])
            elif not proof(earth_map, 1.):
                return "unconfirmed", None

    world_map = proof(earth_map)
    if world_map and not wait(0):
        tap(*map_content_point((82, 75), (1440, 2560), world_map[0]))
    city = proof(city_entry, 2.)
    if city is None:
        town = proof(town_entry, 2.)
        if town and not wait(0):
            tap(*town[1])
            city = proof(city_entry)
    if city is None or wait(0):
        return "unconfirmed", None
    return ("done" if finished else "deferred"), city[1]
