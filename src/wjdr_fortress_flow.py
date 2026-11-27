"""Run the verified fortress checkpoints for one leased account."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from time import monotonic

import wjdr_fortress as fortress
from wjdr_schedule import GRACE_SECONDS


class RecoveryFailed(ValueError):
    """A verified continuation was unavailable after the recovery attempt."""


@dataclass(frozen=True)
class VictoryWatch:
    until: datetime
    arrival_windows: tuple[tuple[datetime, datetime], ...] = ()


def claim_scheduled_start(run: dict, start_at: datetime, save, *, now: datetime | None = None) -> None:
    current = now if now is not None else datetime.now(fortress.SHANGHAI)
    if current < start_at:
        raise ValueError("首站预约还未到点")
    if (current - start_at).total_seconds() > GRACE_SECONDS:
        raise ValueError("到点核验已超过首站预约时间 30 秒")
    if run["index"] != 0 or run.get("scheduled_start"):
        raise ValueError("本轮首站预约已提交，后续请按保存进度手动续跑")
    run["scheduled_start"] = fortress.format_stamp(start_at)
    save()


def _tap(target, stop_event, frame, point):
    if stop_event.is_set() or not target.foreground_is_game():
        raise InterruptedError()
    fortress.tap_game_point(target, frame, point)


def _close_known_overlay(target, ocr, stop_event):
    def page(image, lines):
        if fortress.is_member_announcement_editor(lines):
            return "announcement-editor"
        if fortress.is_member_announcement(lines):
            return "announcement"
        if _war_tab(image, lines):
            return "war"
        if fortress.is_alliance_relocation_prompt(lines):
            return "relocation"
        if fortress.can_confirm_alliance_exit(lines):
            return "exit-confirmation"
        if fortress.is_game_root(lines):
            return "root"
        if fortress.is_regular_activity(lines):
            return "activity"
        if fortress.is_alliance_settings(lines):
            return "alliance"
        if fortress.is_mail_list(lines):
            return "mail"
        if fortress.reward_detail_titles(lines):
            return "mail-detail"
        if (fortress.is_unaffiliated_in_frame(image, lines, ocr) or fortress.read_joined_in_frame(image, lines, ocr)
                or fortress.read_alliance_application(image, lines, ocr)):
            return "alliance"
        controls = set(fortress._text_in(lines, (140, 1138, 544, 1192)))
        if "联盟" in fortress._text_in(lines, (70, 0, 170, 60)) and len(controls & {"成员", "设置", "激励"}) >= 2:
            return "alliance"
        return None

    frame, visible = fortress._wait_alliance_page(target, ocr, stop_event, page, "请打开野外、联盟或本轮已核对邮件")
    if visible in {"announcement", "announcement-editor", "war"}:
        if visible == "announcement-editor":
            fortress.dismiss_member_announcement_editor(target, ocr, stop_event)
        else:
            point = (622, 285) if visible == "announcement" else (37, 36)
            _tap(target, stop_event, frame, point)
        frame, visible = fortress._wait_alliance_page(
            target, ocr, stop_event,
            lambda image, lines: state if (state := page(image, lines)) in {"root", "alliance"} else None,
            "关闭联盟页面后未确认当前位置")
    if visible in {"relocation", "exit-confirmation"}:
        point = (622, 148) if visible == "relocation" else (200, 726)
        fortress.tap_verified_transition(target, stop_event, frame, point)
        fortress._wait_alliance_page(
            target, ocr, stop_event, lambda image, lines: page(image, lines) == "alliance",
            "关闭联盟提示后，联盟页面未确认")
    if visible == "mail-detail":
        def after_detail(image, lines):
            result = page(image, lines)
            return result if result in {"root", "mail", "alliance"} else None

        fortress.tap_verified_transition(target, stop_event, frame, (636, 36))
        frame, visible = fortress._wait_alliance_page(
            target, ocr, stop_event, after_detail,
            "关闭奖励邮件详情后的页面未确认")
    if visible in {"activity", "mail"}:
        fortress.tap_verified_transition(target, stop_event, frame, (37, 36) if visible == "activity" else (636, 36))
        frame, _ = fortress._wait_alliance_page(
            target, ocr, stop_event, lambda _im, lines: fortress.is_game_root(lines), "返回野外的结果未确认")
        visible = "root"
    return frame if visible == "root" else None


def _visit(target, ocr, stop_event, run, tag, save, notify, on_timeout, rate, due=None):
    root = _close_known_overlay(target, ocr, stop_event)
    result = fortress.enter_route_alliance(target, ocr, stop_event, run, tag, save, leave_current=True,
                                         notify=notify, on_timeout=on_timeout, return_by=due, rapid_rate=rate,
                                         verified_root=root)
    if not result.joined:
        raise ValueError(result.message)
    save_needed = run.get("current_alliance") != tag
    if save_needed:
        run["current_alliance"] = tag
        run["current_alliance_entered_at"] = fortress.format_stamp(datetime.now(fortress.SHANGHAI))
    if not run["applications"].get(tag):
        run["applications"][tag] = {
            "state": "joined", "method": "direct", "confirmed": True,
            "started_at": fortress.parse_stamp(run["round_start"]).timestamp(),
        }
        save_needed = True
    if save_needed:
        save()
    notify(result.message)


def _refresh_tab_point(image, lines, ocr):
    def visible_tab(names):
        for line in lines:
            if fortress.compact(line["text"]) not in names or not line.get("words"):
                continue
            first, last = line["words"][0], line["words"][-1]
            center = round((first["x"] + last["x"] + last["width"]) / 2)
            if 138 <= first["y"] <= 170 and 45 <= center <= 627:
                return center, 133
        return None

    result = visible_tab({"联盟争霸赛", "巨熊行动"})
    if result:
        return result
    selected = fortress.fortress_tab_point(image, lines)
    if selected:
        for shift, name in ((190, "巨熊行动"), (-190, "联盟争霸赛")):
            center = selected[0] + shift
            if 75 <= center <= 598:
                label = image.crop((center - 70, 137, center + 71, 173)).resize((282, 72))
                if any(name in fortress.compact(row["text"]) for row in ocr(label)):
                    return center, 133
    return visible_tab({"全军参战", "全军參战", "日历"})


def resolve_targets(target, ocr, stop_event, run, station, save):
    station = fortress.resolved_station(run, station)
    if all(entry["number"] is not None for entry in station["targets"]):
        return station
    fortress.open_fortress_activity(target, ocr, stop_event)
    tag = station["alliance"]
    all_registered = station["targets"][0]["kind"] == fortress.ALL_REGISTERED
    reader = fortress.read_registered_targets if all_registered else fortress.read_unique_fortress
    required = "全部报名目标" if all_registered else "唯一堡垒"
    _, detected = fortress._wait_alliance_page(
        target, ocr, stop_event, lambda image, lines: reader(image, lines, ocr),
        f"[{tag}] 未确认{required}，请核对报名数量和可见卡片")
    registered = run.setdefault("resolved_targets", {})
    previous = registered.get(tag)
    registered[tag] = [list(entry) for entry in detected] if all_registered else detected
    try:
        resolved = fortress.resolved_station(run, station)
    except ValueError:
        if previous is None:
            registered.pop(tag)
        else:
            registered[tag] = previous
        raise
    save()
    return resolved


def _occupation(target, ocr, stop_event, station, *, watch_march=None):
    fortress.open_game_screen(target, ocr, stop_event, "activity")
    next_tap = monotonic()
    failures = 0
    required = {(entry["kind"], entry["number"]) for entry in station["targets"]}

    def state(image, lines):
        occupied = fortress.read_occupation(image, lines, ocr)
        if occupied is not None:
            if watch_march is not None:
                registered = fortress.read_registered_targets(image, lines, ocr)
                if registered is None:
                    return None
                if not required <= set(registered) or (station.get("all_registered") and required != set(registered)):
                    return "registration-mismatch", registered
            if fortress.occupation_complete(occupied, station) and fortress.registration_matches(image, lines, ocr, station):
                return "occupied", None
            if watch_march is not None:
                return "war", tuple(sorted(required & occupied))
            point = _refresh_tab_point(image, lines, ocr)
            return ("navigate", point) if point else ("observe", None)
        if fortress.is_regular_activity(lines):
            point = fortress.fortress_tab_point(image, lines)
            return ("navigate", point) if point else ("find-fortress", None)
        return None

    while not stop_event.is_set():
        if stop_event.wait(max(0, next_tap - monotonic())):
            break
        try:
            frame, (action, point) = fortress._wait_alliance_page(
                target, ocr, stop_event, state, "堡垒争夺或相邻活动页未确认")
            if stop_event.is_set():
                break
            if action == "occupied":
                return True
            if action == "registration-mismatch":
                found = "、".join(f"{kind}{number}" for kind, number in point)
                planned = "、".join(f"{kind}{number}" for kind, number in sorted(required))
                raise RecoveryFailed(f"[{station['alliance']}] 路线目标 {planned} 与本轮报名 {found} 不符")
            if action == "find-fortress":
                fortress.open_fortress_activity(target, ocr, stop_event)
            elif action == "navigate":
                _tap(target, stop_event, frame, point)
            failures = 0
        except fortress.PageNotVerified:
            failures += 1
            if failures >= 2 or not target.foreground_is_game():
                raise
        else:
            if action == "war":
                return watch_march(point)
        next_tap = monotonic() + 1
    return False


def _war_tab(image, lines):
    for tab in ("集结", "单人"):
        if fortress.rally_war_page(image, lines, tab):
            return tab
    return None


def _open_war(target, ocr, stop_event, tag):
    def entry(image, lines):
        if tab := _war_tab(image, lines):
            return "war", tab
        if fortress.joined_tag_matches(image, lines, ocr, tag):
            for box in ((176, 602, 279, 646), (151, 590, 285, 648)):
                strip = image.crop(box)
                local = fortress.embedded_text(ocr, strip)
                if local:
                    if fortress.matches_ui_label(local, "联盟战争"):
                        return "member", (205, 625)
                    continue
                crop = strip.resize((strip.width * 2, strip.height * 2))
                labels = {fortress.compact(item["text"]) for item in ocr(crop)}
                if any(fortress.matches_ui_label(label, "联盟战争") for label in labels):
                    return "member", (205, 625)
        if fortress.is_game_root(lines):
            return "root", (498, 1138)
        if fortress.is_regular_activity(lines):
            return "activity", (37, 36)
        return None

    transitions = {
        "activity": {"root"},
        "root": {"member"},
        "member": {"war"},
    }
    allowed = set(transitions) | {"war"}

    def expected(image, lines):
        match = entry(image, lines)
        return match if match and match[0] in allowed else None

    for _ in range(4):
        frame, (page, item) = fortress._wait_alliance_page(
            target, ocr, stop_event, expected, "未核对联盟战争入口和当前联盟")
        if page == "war":
            return frame, item
        fortress.tap_verified_transition(target, stop_event, frame, item)
        allowed = transitions[page]
    return fortress._wait_alliance_page(target, ocr, stop_event, _war_tab, "未确认联盟战争页")


def _close_war(target, ocr, stop_event, tag):
    frame, _ = fortress._wait_alliance_page(target, ocr, stop_event, _war_tab, "未确认当前联盟战争页")
    fortress.tap_verified_transition(target, stop_event, frame, (37, 36))
    _member_to_root(target, ocr, stop_event, tag)


def march_tabs(station):
    modes = {target["mode"] for target in station["targets"]}
    if fortress.UNSPECIFIED_TACTIC in modes or modes == {"单撞", "集结"}:
        return ("集结", "单人")
    return ("单人",) if modes == {"单撞"} else ("集结",)


def _switch_war_tab(target, ocr, stop_event, frame, next_tab):
    deadline = monotonic() + fortress.RECOVERY_SECONDS
    point = (336 if next_tab == "单人" else 123, 118)
    error = f"未确认联盟战争「{next_tab}」页"

    def requested(image, lines):
        return next_tab if _war_tab(image, lines) == next_tab else None

    fortress.tap_verified_transition(target, stop_event, frame, point)
    try:
        return fortress._wait_alliance_page(target, ocr, stop_event, requested, error, timeout=3.0)
    except fortress.PageNotVerified:
        fresh, visible = fortress._wait_alliance_page(target, ocr, stop_event, _war_tab, error, timeout=0.8)
        if visible == next_tab:
            return fresh, visible
        if monotonic() >= deadline:
            raise fortress.PageNotVerified(error)
        fortress.tap_verified_transition(target, stop_event, fresh, point)
        return fortress._wait_alliance_page(target, ocr, stop_event, requested, error,
                                              timeout=max(0, deadline - monotonic()))


def _clipped_rally(lines):
    at_bottom = fortress._text_in(lines, (410, 835, 646, 1058))
    return any(text.startswith(("行军中", "集结中")) for text in at_bottom)


def _scroll_war_list(target, stop_event, frame):
    if stop_event.is_set() or not target.foreground_is_game():
        raise InterruptedError()
    start = fortress.map_content_point((172, 973), fortress.REFERENCE, frame)
    end = fortress.map_content_point((172, 596), fortress.REFERENCE, frame)
    target.shell(["input", "swipe", *map(str, (*start, *end)), "260"], timeout=2)


def read_march_arrivals(target, ocr, stop_event, station, until, *, decide=None):
    tag = station["alliance"]
    tabs = march_tabs(station)
    names_by_tab = {
        tab: {f"{item['kind']}{item['number']}" for item in station["targets"]
              if item["mode"] in {mode, fortress.UNSPECIFIED_TACTIC}}
        for tab, mode in (("集结", "集结"), ("单人", "单撞"))
    }
    frame, selected = _open_war(target, ocr, stop_event, tag)
    next_switch = monotonic() + (2 if selected in tabs else 0)
    previous = ()
    page_seen = monotonic()
    clipped = False
    scrolled = False
    completed = False
    try:
        while not stop_event.is_set():
            deadline = until() if callable(until) else until
            if deadline is not None and datetime.now(fortress.SHANGHAI) >= deadline:
                break
            frame = target.screenshot(timeout=fortress.RECOVERY_SECONDS)
            observed = datetime.now(fortress.SHANGHAI).replace(microsecond=0)
            image = fortress.normalize_frame(frame)
            lines = ocr(image)
            if _war_tab(image, lines) != selected:
                if monotonic() - page_seen >= fortress.RECOVERY_SECONDS:
                    raise fortress.PageNotVerified("联盟战争行军页未能重新核对")
                stop_event.wait(0.08)
                continue
            page_seen = monotonic()
            confirmed = ()
            current = ()
            if selected in tabs and (marches := fortress.fortress_marches(image, lines, ocr, tab=selected)) is not None:
                current = tuple((name, observed + timedelta(seconds=seconds))
                                for name, seconds in marches if name in names_by_tab[selected])
                if current and len(current) == len(previous) and all(
                    name == prior_name and abs(prior - arrival) <= fortress.MARCH_TIME_TOLERANCE
                    for (name, arrival), (prior_name, prior) in zip(current, previous)
                ):
                    confirmed = tuple((name, min(arrival, prior))
                                      for (name, arrival), (_, prior) in zip(current, previous))
                previous = current
            else:
                previous = ()
            if decide is not None:
                if (decision := decide(confirmed, selected)) is not None:
                    completed = True
                    return decision
            elif confirmed:
                completed = True
                return confirmed
            cut_off = (selected == "集结" and selected in tabs
                       and not names_by_tab[selected] <= {name for name, _ in current} and _clipped_rally(lines))
            if cut_off and clipped and not scrolled:
                _scroll_war_list(target, stop_event, frame)
                scrolled = True
                next_switch = max(next_switch, monotonic() + 0.45)
                stop_event.wait(0.12)
                continue
            clipped = cut_off
            if (selected not in tabs or len(tabs) == 2) and monotonic() >= next_switch:
                next_tab = "单人" if selected == "集结" else "集结"
                started_switch = monotonic()
                _, selected = _switch_war_tab(target, ocr, stop_event, frame, next_tab)
                previous = ()
                clipped = False
                page_seen = monotonic()
                next_switch = started_switch + 2
            else:
                stop_event.wait(0.08)
        completed = True
        return None if decide is not None else ()
    finally:
        if completed and not stop_event.is_set():
            _close_war(target, ocr, stop_event, tag)


def march_key_conflict(arrivals, settlement):
    if not arrivals:
        return None
    target, arrival = min(arrivals, key=lambda item: abs(item[1] - settlement))
    return (target, arrival) if abs(arrival - settlement) < fortress.KEY_MARCH_GAP else None


def _key_during_march(run, station, arrivals, checked, save, notify, *, uncertainty=timedelta()):
    now = datetime.now(fortress.SHANGHAI)
    choices = []
    current = station["alliance"]
    for settlement, tag in fortress.key_windows(run):
        if tag == current or (settlement, tag) in checked:
            continue
        cutoff = fortress.key_return_by(run, tag, settlement)
        if now < cutoff <= now + fortress.KEY_MARCH_GAP:
            choices.append((cutoff, settlement, tag))
    if not choices:
        return None
    next_key = None
    first_arrival = min(arrival for _, arrival in arrivals)
    for cutoff, settlement, tag in sorted(choices):
        if conflict := march_key_conflict(arrivals, settlement):
            name, arrival = conflict
            if abs(arrival - settlement) + uncertainty >= fortress.KEY_MARCH_GAP:
                continue
            checked.add((settlement, tag))
            run.setdefault("key_conflicts", {}).setdefault(tag, {})[fortress.format_stamp(settlement)] = {
                "alliance": current, "target": name, "arrival": fortress.format_stamp(arrival),
            }
            save()
            notify(f"[{tag}] 跳过 {settlement:%H:%M:%S} 的钥匙 · [{current}] {name} 行军到达 {arrival:%H:%M:%S}")
            continue
        if (next_key is None and settlement + fortress.KEY_MARCH_GAP + uncertainty <= first_arrival
                and datetime.now(fortress.SHANGHAI) < cutoff):
            checked.add((settlement, tag))
            next_key = settlement, tag, first_arrival
    return next_key


def victory_watch_for(arrivals, now):
    grace = timedelta(seconds=fortress.RECOVERY_SECONDS) + fortress.MARCH_TIME_TOLERANCE
    end = None
    for arrival in sorted(arrivals):
        starts = arrival - fortress.VICTORY_MAIL_LEAD
        finishes = arrival + grace
        if finishes <= now:
            continue
        if end is None:
            if starts > now:
                return None
        elif starts > end:
            break
        end = finishes
    return VictoryWatch(end) if end is not None else None


def _watch_station_marches(target, ocr, stop_event, run, station, occupied, checked_keys, save, notify):
    tag = station["alliance"]
    now = datetime.now(fortress.SHANGHAI)
    claimed = sum(state == "claimed" for state in run["mail"].get(tag, {}).values())
    grace = timedelta(seconds=fortress.RECOVERY_SECONDS) + fortress.MARCH_TIME_TOLERANCE
    blue = {f"{kind}{number}" for kind, number in occupied}
    saved = run.setdefault("march_forecast", {}).setdefault(tag, [])
    plans = [row for row in saved
             if row["target"] not in blue and fortress.parse_stamp(row["arrival"]) + grace > now]
    if plans != saved:
        saved[:] = plans
        save()
    if len(blue) > claimed:
        return VictoryWatch(now + grace)

    applicable = [row for row in station["targets"] if f"{row['kind']}{row['number']}" not in blue]
    if not applicable:
        return VictoryWatch(now + grace)
    station = dict(station, targets=applicable)
    seen = {}

    def decide(confirmed, tab):
        clock = datetime.now(fortress.SHANGHAI)
        added = []
        for name, arrival in confirmed:
            match = next((row for row in saved if row["target"] == name and row["tab"] == tab
                          and abs(fortress.parse_stamp(row["arrival"]) - arrival) <= fortress.MARCH_TIME_TOLERANCE), None)
            if match is None:
                match = {"target": name, "tab": tab, "arrival": fortress.format_stamp(arrival)}
                saved.append(match)
                added.append((name, arrival))
            seen[(name, tab, match["arrival"])] = clock
        if added:
            save()
            for name, arrival in added:
                estimated = arrival + fortress.KEY_MAIL_DELAY
                key_text = f" · 钥匙预计 {estimated:%H:%M:%S}" if run.get("take_keys", True) else ""
                notify(f"[{tag}] {name} · {tab}预计 {arrival:%H:%M:%S} 到达{key_text}")

        upcoming = [(row["target"], fortress.parse_stamp(row["arrival"])) for row in saved]
        fresh = clock - 2 * fortress.MARCH_TIME_TOLERANCE
        live = [(name, fortress.parse_stamp(arrival)) for (name, _, arrival), seen_at in seen.items()
                if seen_at >= fresh and fortress.parse_stamp(arrival) + fortress.MARCH_TIME_TOLERANCE >= clock]
        if live:
            key = _key_during_march(run, station, live, checked_keys, save, notify,
                                    uncertainty=fortress.MARCH_TIME_TOLERANCE)
            if key:
                return key
        return victory_watch_for((arrival for _, arrival in upcoming), clock)

    return read_march_arrivals(target, ocr, stop_event, station, None, decide=decide)


def claim_victory(target, ocr, stop_event, run, tag, save, *, opened=None, expected_stamp=None, arrival_windows=()):
    member = run["applications"].get(tag)
    if not member or member["state"] != "joined":
        raise ValueError("本站入盟记录未确认")
    mails = run["mail"].get(tag, {})
    original_entry = run.get("deferred_victory", {}).get(
        tag, run.get("victory_since", {}).get(tag, member["started_at"]))
    since = max(fortress.parse_stamp(run["round_start"]),
                datetime.fromtimestamp(original_entry, fortress.SHANGHAI).replace(microsecond=0))
    known = {fortress.victory_stamp(stamp) for records in run["mail"].values() for stamp in records}
    pending_id = next((stamp for stamp, state in mails.items() if state == "pending"), None)
    pending = fortress.victory_stamp(pending_id) if pending_id else None
    if pending is not None and expected_stamp is not None and pending != expected_stamp:
        raise ValueError("配对的胜利邮件时间与待核对记录不一致")
    verified = None
    if opened is None:
        if pending_id and "#" in pending_id:
            raise RecoveryFailed("同秒邮件的领取详情已离开，请人工核对后继续")
        repeatable = {fortress.victory_stamp(stamp) for stamp, state in mails.items() if state == "claimed"}
        verified = fortress.open_recent_victory_mail(
            target, ocr, stop_event, since, known - {pending}, expected=pending or expected_stamp,
            repeatable=repeatable if pending is None and expected_stamp is None else frozenset(),
            arrival_windows=arrival_windows)
        _, opened = verified
    key = fortress.format_stamp(opened.stamp)
    repeat = (verified is not None and opened.title in fortress.FORTRESS_MAIL and not opened.claimed
              and pending_id is None and key in mails)
    if repeat:
        copies = sum(fortress.victory_stamp(entry) == opened.stamp for entry in mails)
        key = f"{key}#{copies + 1}"
    if pending == opened.stamp:
        key = pending_id
    if (not since <= opened.stamp <= datetime.now(fortress.SHANGHAI)
            or (opened.stamp in known and mails.get(key) != "pending" and not repeat)
            or ("pending" in mails.values() and mails.get(key) != "pending")
            or (arrival_windows and not any(start <= opened.stamp <= end for start, end in arrival_windows))
            or (expected_stamp is not None and opened.stamp != expected_stamp)):
        raise ValueError("当前邮件不能与本站待领取记录匹配")
    if pending is not None and not opened.claimed:
        raise fortress.MailClaimUnconfirmed("当前邮件已发出领取操作，等待游戏结果")

    def record(mail, status):
        if (mail.stamp, mail.title) != (opened.stamp, opened.title):
            raise ValueError("当前邮件已变化")
        fortress.record_mail(run, tag, mail.stamp, status, datetime.now(fortress.SHANGHAI), receipt=key)
        save()

    return fortress.collect_reward(target, ocr, stop_event, record, claim=True, verified=verified, on_claimed=None)


def _detail_back(target, ocr, stop_event):
    frame, _ = fortress._wait_alliance_page(
        target, ocr, stop_event,
        lambda _im, ln: fortress.reward_detail_titles(ln),
        "当前奖励邮件详情未确认",
    )
    _tap(target, stop_event, frame, (37, 36))
    fortress._wait_alliance_page(target, ocr, stop_event, lambda _im, ln: fortress.is_mail_list(ln),
                                  "已返回邮件列表的结果未确认")


def _paired_victory_times(target, ocr, stop_event, run, pair, save):
    if "stamps" in pair:
        return tuple(fortress.parse_stamp(stamp) for stamp in pair["stamps"])
    earlier = pair["earlier"]
    confirmed_earlier = pair.get("earlier_stamp")
    if confirmed_earlier:
        start = fortress.parse_stamp(confirmed_earlier)
    else:
        start = datetime.fromtimestamp(run["deferred_victory"][earlier], fortress.SHANGHAI).replace(microsecond=0)
    known = {fortress.victory_stamp(stamp) for records in run["mail"].values() for stamp in records}
    fortress.open_game_screen(target, ocr, stop_event, "mail")

    def read(image, lines):
        if not fortress.alliance_mail_selected(image, lines):
            return None
        now = datetime.now(fortress.SHANGHAI)
        times = [stamp for stamp in fortress.visible_reward_stamps(lines, start, now, image=image, ocr=ocr)
                 if stamp not in known]
        if confirmed_earlier and len(times) == 1:
            return start, times[0]
        return tuple(times) if len(times) == 2 else None

    try:
        _, times = fortress._wait_alliance_page(target, ocr, stop_event, read, "等待两封胜利邮件供按时间配对")
    except fortress.PageNotVerified as exc:
        raise fortress.MailNotYetVisible(str(exc)) from exc
    pair["stamps"] = [fortress.format_stamp(stamp) for stamp in times]
    save()
    return times


def claim_key_mail(target, ocr, stop_event, run, tag, save, *, settlement=None):
    """Read the alliance mailbox directly. Return a verified claim or no new mail."""
    pending = fortress.pending_key_settlements(run, tag)
    if settlement is None:
        settlement = pending[0] if pending else None
    if settlement not in pending:
        raise ValueError(f"[{tag}] 没有待领取的钥匙时点")
    due = fortress.key_return_by(run, tag, settlement)
    settlements = fortress.key_settlements(run, tag)
    arrival = run["returned"].get(tag)
    if not due or not arrival or fortress.parse_stamp(arrival) >= due:
        raise ValueError(f"[{tag}] 没有截止前的入盟记录")
    earliest = max(fortress.parse_stamp(run["round_start"]), fortress.parse_stamp(arrival))
    station = fortress.resolved_station(run, next(stop for stop in run["route"] if stop["alliance"] == tag))
    if any(entry["number"] is None for entry in station["targets"]):
        raise ValueError(f"[{tag}] 钥匙邮件对应的堡垒编号未登记")
    wanted = {f"{entry['kind']}{entry['number']}" for entry in station["targets"]}
    confirmed_targets = run.get("key_targets", {}).get(tag)
    if confirmed_targets is not None:
        if not confirmed_targets or not set(confirmed_targets) <= wanted:
            raise ValueError(f"[{tag}] 已核对的钥匙目标与报名目标不一致")
        wanted = set(confirmed_targets)
    receipts = run.setdefault("key_mail", {}).setdefault(tag, {})

    def eligible_settlement(sent):
        if sent is not None and not earliest <= sent <= datetime.now(fortress.SHANGHAI):
            return None
        if len(settlements) > 1:
            match = fortress.corresponding_settlement(settlements, sent)
            if sent is not None and (match is None or match not in pending):
                nearby = [due for due in settlements if abs(due - sent) <= fortress.MARCH_TIME_TOLERANCE]
                skipped = run.get("key_conflicts", {}).get(tag, {})
                if not any(fortress.format_stamp(due) in skipped for due in nearby):
                    match = next((due for due in nearby if due in pending), match)
            if match not in pending or fortress.parse_stamp(arrival) >= fortress.key_return_by(run, tag, match):
                return None
            return match
        return settlement

    def outstanding(label, sent):
        if label not in wanted or eligible_settlement(sent) is None:
            return False
        prior = receipts.get(label)
        return prior is None or (prior["state"] == "pending"
                                 and (sent is None or fortress.format_stamp(sent) == prior["stamp"]))

    def row(image, lines, *, unclaimed=None):
        if not fortress.alliance_mail_selected(image, lines):
            return None
        for line in lines:
            word = (line.get("words") or [None])[0]
            if not word or fortress.compact(line["text"]) != fortress.CONTROL_MAIL:
                continue
            y = round(word["y"])
            if not (142 < word["x"] < 226 and 155 < y < 1063):
                continue
            body = "".join(fortress._text_in(lines, (142, y + 19, 590, y + 53)))
            label = fortress._control_mail_target(body)
            sent = fortress.mail_row_stamp(image, lines, y, ocr)
            if not outstanding(label, sent):
                continue
            if unclaimed and ((label, sent) != (unclaimed.target, unclaimed.stamp)
                              or not fortress.control_gift_visible(image, y)):
                continue
            return (312, y + 36), label, sent
        return None

    def open_row(identify):
        frame, (point, label, listed_stamp) = fortress._wait_alliance_page(
            target, ocr, stop_event, identify, "成功控制堡垒邮件列表在打开前发生变化")
        _tap(target, stop_event, frame, point)
        frame, opened = fortress._wait_alliance_page(
            target, ocr, stop_event, lambda im, ln: fortress.read_control_reward(im, ln, ocr),
            "钥匙邮件详情和右上角时间未确认")
        if opened.target != label or listed_stamp is not None and opened.stamp != listed_stamp:
            raise ValueError("钥匙邮件详情与列表不一致")
        return frame, opened

    frame, image, lines = fortress._alliance_frame(target, ocr, stop_event)
    current = fortress.read_control_reward(image, lines, ocr)
    if current and not outstanding(current.target, current.stamp):
        _detail_back(target, ocr, stop_event)
        _, image, lines = fortress._alliance_frame(target, ocr, stop_event)
        current = None

    if current is None:
        if not fortress.alliance_mail_selected(image, lines):
            image, lines = fortress.open_game_screen(target, ocr, stop_event, "mail")
        if not row(image, lines):
            return None
        frame, current = open_row(row)

    if not outstanding(current.target, current.stamp):
        raise ValueError("当前邮件不属于本站到期的钥匙奖励")
    key, stamp = current.target, fortress.format_stamp(current.stamp)
    matched_settlement = eligible_settlement(current.stamp)
    def recover(reward, prior):
        elapsed = datetime.now(fortress.SHANGHAI).timestamp() - prior.get("attempt_at", 0)
        if elapsed < fortress.RECOVERY_SECONDS:
            raise fortress.MailClaimUnconfirmed("这封钥匙邮件已有领取操作，等待结果")
        if prior.get("recovery_checked") or prior.get("verified_recovery_sent"):
            raise RecoveryFailed(f"[{tag}] 钥匙领取纠错后仍未确认，流程已停止")
        prior["recovery_checked"] = True
        save()
        try:
            _detail_back(target, ocr, stop_event)
            verified_frame, checked = open_row(lambda im, ln: row(im, ln, unclaimed=reward))
        except fortress.PageNotVerified as error:
            raise RecoveryFailed(f"[{tag}] 无法重新核对钥匙邮件或礼物图标，流程已停止 · {error}") from error
        if not checked.claimed:
            _tap(target, stop_event, verified_frame, checked.point)
        return checked

    def acknowledge(reward):
        fortress._wait_alliance_page(
            target, ocr, stop_event,
            lambda im, ln: ((mail := fortress.read_control_reward(im, ln, ocr)) is not None
                            and (mail.target, mail.stamp) == (reward.target, reward.stamp) and mail.claimed),
            "钥匙领取结果待核对")

    def confirm_recovery(reward):
        if not reward.claimed:
            try:
                acknowledge(reward)
            except fortress.PageNotVerified as error:
                raise RecoveryFailed(f"[{tag}] 钥匙补领仍无回执，流程已停止") from error

    prior = receipts.get(key)
    if not current.claimed and prior is not None:
        current = recover(current, prior)
        confirm_recovery(current)
    elif not current.claimed:
        with target.touch_session() as touch:
            frame, _ = fortress._wait_alliance_page(
                target, ocr, stop_event, lambda im, ln: fortress.read_control_reward(im, ln, ocr) == current,
                "钥匙领取控件已变化")
            if stop_event.is_set() or not target.foreground_is_game():
                raise InterruptedError()
            receipts[key] = {"stamp": stamp, "state": "pending",
                             "attempt_at": datetime.now(fortress.SHANGHAI).timestamp()}
            save()
            if stop_event.is_set():
                raise InterruptedError()
            touch.touch_request(fortress.map_content_point(current.point, fortress.REFERENCE, frame))

        try:
            acknowledge(current)
        except fortress.PageNotVerified:
            reward = current
            try:
                _, latest = fortress._wait_alliance_page(
                    target, ocr, stop_event,
                    lambda im, ln: (mail if (mail := fortress.read_control_reward(im, ln, ocr)) is not None
                                    and (mail.target, mail.stamp) == (reward.target, reward.stamp) else None),
                    "未重新确认同一封钥匙邮件")
            except fortress.PageNotVerified as error:
                raise RecoveryFailed(f"[{tag}] 钥匙纠错时无法确认同一封邮件，流程已停止") from error
            current = latest if latest.claimed else recover(latest, receipts[key])
            confirm_recovery(current)
    if key in receipts and receipts[key]["stamp"] != stamp:
        raise ValueError("当前邮件与本站钥匙发件时间记录不一致")
    receipts[key] = {"stamp": stamp, "state": "claimed"}
    if len(settlements) > 1:
        receipts[key]["settlement"] = fortress.format_stamp(matched_settlement)
    if all(receipts.get(target_key, {}).get("state") == "claimed" for target_key in wanted):
        run["keys"][tag] = fortress.format_stamp(datetime.now(fortress.SHANGHAI))
    save()
    return current


def _member_to_root(target, ocr, stop_event, tag):
    def state(image, lines):
        if fortress.is_game_root(lines):
            return "root"
        if fortress.joined_tag_matches(image, lines, ocr, tag):
            return "member"
        return None

    frame, page = fortress._wait_alliance_page(target, ocr, stop_event, state, f"[{tag}] 的成员页未确认")
    if page == "member":
        _tap(target, stop_event, frame, (37, 36))
        try:
            fortress._wait_alliance_page(target, ocr, stop_event, lambda _im, ln: fortress.is_game_root(ln),
                                          "返回野外未确认")
        except fortress.PageNotVerified:
            frame, page = fortress._wait_alliance_page(target, ocr, stop_event, state,
                                                       f"[{tag}] 纠错时未确认成员页或野外")
            if page == "member":
                fortress.tap_verified_transition(target, stop_event, frame, (37, 36))
                fortress._wait_alliance_page(target, ocr, stop_event, lambda _im, ln: fortress.is_game_root(ln),
                                              "返回野外纠错失败，流程已停止")


def _currently_returned(run, tag):
    current = run.get("current_alliance")
    if current is None:
        current = max(run["returned"], key=run["returned"].get, default=None)
    if current != tag:
        return None
    return max(filter(None, (run["returned"].get(tag), run.get("current_alliance_entered_at"))), default=None)


def _next_key(run, *, start_return):
    now = datetime.now(fortress.SHANGHAI)
    waiting = run.get("key_waiting")
    eligible = []
    for settlement, tag in fortress.key_windows(run):
        checkpoint = [fortress.format_stamp(settlement), tag]
        if waiting == checkpoint:
            return settlement, tag
        if start_return:
            cutoff = fortress.key_return_by(run, tag, settlement)
            arrival = _currently_returned(run, tag)
            if (arrival and fortress.parse_stamp(arrival) < cutoff) or cutoff > now:
                eligible.append((cutoff, settlement, tag))
    if eligible:
        _, settlement, tag = min(eligible)
        return settlement, tag
    return None


def _key_visit(target, ocr, stop_event, run, tag, settlement, save, notify, on_timeout, rate, *, march_at=None):
    cutoff = fortress.key_return_by(run, tag, settlement)
    arrival = _currently_returned(run, tag)
    if not arrival or fortress.parse_stamp(arrival) >= cutoff:
        _visit(target, ocr, stop_event, run, tag, save, notify, on_timeout, rate, cutoff)
        arrived = datetime.now(fortress.SHANGHAI)
        run["returned"][tag] = fortress.format_stamp(arrived)
        save()
        if arrived >= cutoff:
            raise ValueError(f"[{tag}] 入盟时已超过钥匙返回截止")
        notify(f"[{tag}] 已在截止前返回")
        _member_to_root(target, ocr, stop_event, tag)
    else:
        _, image, lines = fortress._alliance_frame(target, ocr, stop_event)
        if fortress.joined_tag_matches(image, lines, ocr, tag):
            _member_to_root(target, ocr, stop_event, tag)
        run["returned"][tag] = arrival
    run["key_waiting"] = [fortress.format_stamp(settlement), tag]
    if march_at is not None:
        run["key_march_at"] = fortress.format_stamp(march_at)
    else:
        run.pop("key_march_at", None)
    save()
    notify(f"[{tag}] 在联盟邮件等待 {fortress.format_stamp(settlement)} 的钥匙")
    read_failed = False
    while not stop_event.is_set() and settlement in fortress.pending_key_settlements(run, tag):
        if march_at is not None and datetime.now(fortress.SHANGHAI) >= march_at - timedelta(seconds=fortress.RECOVERY_SECONDS):
            notify(f"[{tag}] 尚未收到 {settlement:%H:%M:%S} 的钥匙邮件，返回堡垒路线")
            break
        try:
            mail = claim_key_mail(target, ocr, stop_event, run, tag, save, settlement=settlement)
        except fortress.PageNotVerified as error:
            if read_failed:
                raise RecoveryFailed(f"[{tag}] 无法核对联盟邮件，流程已停止 · {error}") from error
            read_failed = True
            continue
        except fortress.MailClaimUnconfirmed:
            stop_event.wait(1)
            continue
        read_failed = False
        if mail is None:
            stop_event.wait(1)
            continue
        notify(f"[{tag}] 已确认领取 {mail.target} 钥匙 · {fortress.format_stamp(mail.stamp)}")
    if not stop_event.is_set():
        run.pop("key_waiting", None)
        run.pop("key_march_at", None)
        save()


def run_route(target, ocr, stop_event, run, save, *, notify, on_timeout, rate=100, initial_watch=None):
    active = run.get("current_alliance") if initial_watch is not None else None
    watch = initial_watch
    victory_read_failed = False
    waiting_notice = False
    waiting_on_list = False
    checked_keys = set()
    while not stop_event.is_set():
        normal_station = run["index"] < len(run["route"])
        deferred = run.get("deferred_victory", {})
        remaining_sites = normal_station or bool(deferred)
        key_visit = _next_key(run, start_return=not remaining_sites)
        if key_visit:
            due, tag = key_visit
            same_wait = run.get("key_waiting") == [fortress.format_stamp(due), tag]
            march = run.get("key_march_at") if same_wait else None
            if march:
                _key_visit(target, ocr, stop_event, run, tag, due, save, notify, on_timeout, rate,
                           march_at=fortress.parse_stamp(march))
            else:
                _key_visit(target, ocr, stop_event, run, tag, due, save, notify, on_timeout, rate)
            active = None
            watch = None
            waiting_on_list = False
            continue
        if not remaining_sites:
            now = datetime.now(fortress.SHANGHAI)
            missed = [f"{tag} {due:%H:%M:%S}" for due, tag in fortress.key_windows(run)
                      if fortress.key_return_by(run, tag, due) <= now]
            return "堡垒路线已完成" + (f" · 超过钥匙截止：{'、'.join(missed)}" if missed else "")

        requested = (run["route"][run["index"]] if normal_station
                     else next(stop for stop in run["route"] if stop["alliance"] in deferred))
        station = fortress.resolved_station(run, requested)
        tag = station["alliance"]
        wanted = len(station["targets"])
        mails = run["mail"].get(tag, {})
        pending_victory = "pending" in mails.values()
        if (all(entry["number"] is not None for entry in station["targets"])
                and sum(state == "claimed" for state in mails.values()) >= wanted):
            if normal_station:
                run["index"] += 1
            else:
                deferred.pop(tag)
            run.get("march_forecast", {}).pop(tag, None)
            watch = None
            waiting_on_list = False
            save()
            continue

        checked_detail = None
        if pending_victory and run.get("current_alliance") not in (None, tag):
            raise RecoveryFailed(f"[{tag}] 胜利邮件领取仍待核对，请确认当前联盟")
        if (run.get("current_alliance") in (None, tag) and (not waiting_on_list or pending_victory)
                and (tag in run["occupied"] or watch is not None or pending_victory)):
            _, checked_detail = fortress.capture_reward(target, ocr)
        if active != tag and checked_detail is None and not pending_victory:
            _visit(target, ocr, stop_event, run, tag, save, notify, on_timeout, rate)
            _member_to_root(target, ocr, stop_event, tag)
            victory_read_failed = False
            waiting_notice = False
        active = tag
        if tag in run["applications"] and tag not in run.setdefault("victory_since", {}):
            run["victory_since"][tag] = run["applications"][tag]["started_at"]
            save()
        if tag not in run["occupied"] and watch is None and not pending_victory:
            if any(entry["number"] is None for entry in station["targets"]):
                station = resolve_targets(target, ocr, stop_event, run, station, save)
                wanted = len(station["targets"])
                names = "、".join(f"{entry['kind']}{entry['number']}" for entry in station["targets"])
                notify(f"[{tag}] 已识别目标 {names}")
            notify(f"[{tag}] 核对堡垒报名，跟踪对应行军和胜利邮件")

            def watch_march(occupied):
                return _watch_station_marches(target, ocr, stop_event, run, station, occupied,
                                                checked_keys, save, notify)

            occupation = _occupation(target, ocr, stop_event, station, watch_march=watch_march)
            if not occupation:
                continue
            if isinstance(occupation, tuple):
                settlement, key_tag, march_at = occupation
                _key_visit(target, ocr, stop_event, run, key_tag, settlement, save, notify, on_timeout, rate,
                           march_at=march_at)
                active = None
                continue
            if isinstance(occupation, VictoryWatch):
                watch = occupation
                notify(f"[{tag}] 进入联盟邮件等待这一波胜利奖励")
            else:
                run["occupied"].append(tag)
                save()
        try:
            expected_stamp = None
            pair = run.get("paired_victory")
            if pair and pair["later"] == tag:
                if checked_detail and "stamps" not in pair:
                    _detail_back(target, ocr, stop_event)
                    checked_detail = None
                earlier_stamp, expected_stamp = _paired_victory_times(target, ocr, stop_event, run, pair, save)
                earlier = pair["earlier"]
                earlier_text = fortress.format_stamp(earlier_stamp)
                if run["mail"].get(earlier, {}).get(earlier_text) != "claimed":
                    prior = checked_detail if checked_detail and checked_detail.stamp == earlier_stamp else None
                    mail = claim_victory(target, ocr, stop_event, run, earlier, save, opened=prior,
                                         expected_stamp=earlier_stamp)
                    notify(f"[{earlier}] 已登记较早的胜利邮件 · {fortress.format_stamp(mail.stamp)}")
                    _detail_back(target, ocr, stop_event)
                    checked_detail = None
                elif checked_detail and checked_detail.stamp == earlier_stamp:
                    _detail_back(target, ocr, stop_event)
                    checked_detail = None
                if earlier in deferred:
                    deferred.pop(earlier)
                    save()
            mail = claim_victory(target, ocr, stop_event, run, tag, save, opened=checked_detail,
                                 expected_stamp=expected_stamp, arrival_windows=watch.arrival_windows if watch else ())
        except fortress.MailNotYetVisible as error:
            if pending_victory:
                raise RecoveryFailed(f"[{tag}] 未找到待核对的胜利邮件，已保留领取记录") from error
            victory_read_failed = False
            waiting_on_list = True
            if watch is not None and datetime.now(fortress.SHANGHAI) >= watch.until:
                if not waiting_notice:
                    notify(f"[{tag}] 还有胜利邮件未到，继续停在联盟邮件页等待")
                    waiting_notice = True
            stop_event.wait(0.1)
            continue
        except fortress.MailClaimUnconfirmed as error:
            pending = {fortress.victory_stamp(stamp) for mails in run["mail"].values()
                       for stamp, state in mails.items() if state == "pending"}
            try:
                fortress._wait_alliance_page(
                    target, ocr, stop_event,
                    lambda im, ln: ((mail := fortress.read_mail(im, ln, ocr)) is not None
                                    and mail.stamp in pending and mail.claimed),
                    "胜利邮件仍未确认已领取")
            except fortress.PageNotVerified:
                raise RecoveryFailed(f"[{tag}] 胜利邮件纠错后仍无领取回执，流程已停止") from error
            continue
        except fortress.PageNotVerified as error:
            if victory_read_failed:
                raise RecoveryFailed(f"[{tag}] 无法核对胜利邮件页面，流程已停止 · {error}") from error
            victory_read_failed = True
            waiting_on_list = False
            _, _, lines = fortress._alliance_frame(target, ocr, stop_event)
            if fortress.reward_detail_titles(lines) - {fortress.CONTROL_MAIL}:
                _detail_back(target, ocr, stop_event)
            continue
        victory_read_failed = False
        notify(f"[{tag}] 已领取胜利邮件 · {fortress.format_stamp(mail.stamp)}")
        if sum(state == "claimed" for state in run["mail"][tag].values()) < wanted:
            _detail_back(target, ocr, stop_event)
            waiting_on_list = True
    raise InterruptedError()
