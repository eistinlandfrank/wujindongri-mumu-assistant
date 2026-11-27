"""Run the verified fortress checkpoints for one leased account."""
from __future__ import annotations

from datetime import datetime, timedelta
from time import monotonic

import wjdr_fortress as fortress
from wjdr_schedule import GRACE_SECONDS

KEY_RETURN_LEAD = timedelta(minutes=5)

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
        if fortress.is_game_root(lines):
            return "root"
        if fortress.is_regular_activity(lines):
            return "activity"
        if fortress.is_alliance_settings(lines):
            return "alliance"
        if (fortress.is_mail_list(lines) or
                set(fortress._text_in(lines, (200, 248, 454, 301)))
                & (fortress.FORTRESS_MAIL | {fortress.CONTROL_MAIL})):
            return "mail"
        if (fortress.is_unaffiliated_in_frame(image, lines, ocr) or fortress.read_joined_in_frame(image, lines, ocr)
                or fortress.read_alliance_application(image, lines, ocr)):
            return "alliance"
        controls = set(fortress._text_in(lines, (140, 1138, 544, 1192)))
        if "联盟" in fortress._text_in(lines, (70, 0, 170, 60)) and len(controls & {"成员", "设置", "激励"}) >= 2:
            return "alliance"
        return None

    frame, visible = fortress._wait_alliance_page(target, ocr, stop_event, page, "请打开野外、联盟或本轮已核对邮件")
    if visible in {"activity", "mail"}:
        _tap(target, stop_event, frame, (37, 36) if visible == "activity" else (636, 36))
        fortress._wait_alliance_page(target, ocr, stop_event, lambda _im, lines: fortress.is_game_root(lines),
                                      "返回野外的结果未确认")


def _visit(target, ocr, stop_event, run, tag, save, notify, on_timeout, rate, due=None):
    _close_known_overlay(target, ocr, stop_event)
    result = fortress.enter_route_alliance(target, ocr, stop_event, run, tag, save, leave_current=True,
                                         notify=notify, on_timeout=on_timeout, return_by=due, rapid_rate=rate)
    if not result.joined:
        raise ValueError(result.message)
    if not run["applications"].get(tag):
        run["applications"][tag] = {
            "state": "joined", "method": "direct", "confirmed": True,
            "started_at": fortress.parse_stamp(run["round_start"]).timestamp(),
        }
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


def _occupation(target, ocr, stop_event, station, yield_for_key):
    fortress.open_game_screen(target, ocr, stop_event, "activity")
    next_tap = monotonic()
    failures = 0

    def state(image, lines):
        occupied = fortress.read_occupation(image, lines, ocr)
        if occupied is not None:
            if fortress.occupation_complete(occupied, station) and fortress.registration_matches(image, lines, ocr, station):
                return "occupied", None
            point = _refresh_tab_point(image, lines, ocr)
            return ("navigate", point) if point else ("observe", None)
        if fortress.is_regular_activity(lines):
            point = fortress.fortress_tab_point(image, lines)
            return ("navigate", point) if point else ("find-fortress", None)
        return None

    while not stop_event.is_set() and not yield_for_key():
        if stop_event.wait(max(0, next_tap - monotonic())) or yield_for_key():
            break
        try:
            frame, (action, point) = fortress._wait_alliance_page(
                target, ocr, stop_event, state, "堡垒争夺或相邻活动页未确认")
            if stop_event.is_set() or yield_for_key():
                break
            if action == "occupied":
                return True
            if action == "find-fortress":
                fortress.open_fortress_activity(target, ocr, stop_event)
            elif action == "navigate":
                _tap(target, stop_event, frame, point)
            failures = 0
        except fortress.PageNotVerified:
            failures += 1
            if failures >= 3 or not target.foreground_is_game():
                raise
        next_tap = monotonic() + 1
    return False


def claim_victory(target, ocr, stop_event, run, tag, save, *, opened=None, close_after=False, expected_stamp=None):
    member = run["applications"].get(tag)
    if not member or member["state"] != "joined":
        raise ValueError("本站入盟记录未确认")
    mails = run["mail"].get(tag, {})
    original_entry = run.get("deferred_victory", {}).get(tag, member["started_at"])
    since = max(fortress.parse_stamp(run["round_start"]),
                datetime.fromtimestamp(original_entry, fortress.SHANGHAI).replace(microsecond=0))
    known = {fortress.parse_stamp(stamp) for records in run["mail"].values() for stamp in records}
    pending = next((fortress.parse_stamp(stamp) for stamp, state in mails.items() if state == "pending"), None)
    if pending is not None and expected_stamp is not None and pending != expected_stamp:
        raise ValueError("配对的胜利邮件时间与待核对记录不一致")
    verified = None
    if opened is None:
        verified = fortress.open_recent_victory_mail(target, ocr, stop_event, since, known - {pending},
                                                     expected=pending or expected_stamp)
        _, opened = verified
    key = fortress.format_stamp(opened.stamp)
    if (not since <= opened.stamp <= datetime.now(fortress.SHANGHAI)
            or (opened.stamp in known and mails.get(key) != "pending")
            or ("pending" in mails.values() and mails.get(key) != "pending")
            or (expected_stamp is not None and opened.stamp != expected_stamp)):
        raise ValueError("当前邮件不能与本站待领取记录匹配")
    if pending is not None and not opened.claimed:
        raise fortress.MailClaimUnconfirmed("当前邮件已发出领取操作，等待游戏结果")

    def record(mail, status):
        if (mail.stamp, mail.title) != (opened.stamp, opened.title):
            raise ValueError("当前邮件已变化")
        fortress.record_mail(run, tag, mail.stamp, status, datetime.now(fortress.SHANGHAI))
        save()

    def leave_mail(frame):
        _tap(target, stop_event, frame, (636, 36))
        fortress._wait_alliance_page(
            target, ocr, stop_event, lambda _im, lines: fortress.is_game_root(lines),
            "邮件关闭后的野外页面未确认")

    return fortress.collect_reward(target, ocr, stop_event, record, claim=True, verified=verified,
                                   on_claimed=leave_mail if close_after else None)


def _detail_back(target, ocr, stop_event):
    frame, _ = fortress._wait_alliance_page(
        target, ocr, stop_event,
        lambda _im, ln: bool(set(fortress._text_in(ln, (200, 248, 454, 301)))
                             & (fortress.FORTRESS_MAIL | {fortress.CONTROL_MAIL})),
        "当前奖励邮件详情未确认",
    )
    _tap(target, stop_event, frame, (37, 36))
    fortress._wait_alliance_page(target, ocr, stop_event, lambda _im, ln: fortress.is_mail_list(ln),
                                  "已返回邮件列表的结果未确认")


def _refresh_alliance_mail(target, ocr, stop_event):
    frame, _ = fortress._wait_alliance_page(
        target, ocr, stop_event, fortress.alliance_mail_selected, "待刷新联盟邮件列表未确认")
    _tap(target, stop_event, frame, (636, 36))
    fortress._wait_alliance_page(target, ocr, stop_event, lambda _im, lines: fortress.is_game_root(lines),
                                "邮件刷新前返回野外未确认")


def _paired_victory_times(target, ocr, stop_event, run, pair, save):
    if "stamps" in pair:
        return tuple(fortress.parse_stamp(stamp) for stamp in pair["stamps"])
    earlier = pair["earlier"]
    confirmed_earlier = pair.get("earlier_stamp")
    if confirmed_earlier:
        start = fortress.parse_stamp(confirmed_earlier)
    else:
        start = datetime.fromtimestamp(run["deferred_victory"][earlier], fortress.SHANGHAI).replace(microsecond=0)
    known = {fortress.parse_stamp(stamp) for records in run["mail"].values() for stamp in records}
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


def claim_key_mail(target, ocr, stop_event, run, tag, save):
    """Read the alliance mailbox directly. Return a verified claim or no new mail."""
    due = fortress.return_deadline(run, tag)
    arrival = run["returned"].get(tag)
    if not due or not arrival or fortress.parse_stamp(arrival) >= due:
        raise ValueError(f"[{tag}] 没有截止前的入盟记录")
    if datetime.now(fortress.SHANGHAI) < due:
        return None
    station = fortress.resolved_station(run, next(stop for stop in run["route"] if stop["alliance"] == tag))
    if any(entry["number"] is None for entry in station["targets"]):
        raise ValueError(f"[{tag}] 钥匙邮件对应的堡垒编号未登记")
    wanted = {f"{entry['kind']}{entry['number']}" for entry in station["targets"]}
    receipts = run.setdefault("key_mail", {}).setdefault(tag, {})
    frame, image, lines = fortress._alliance_frame(target, ocr, stop_event)
    current = fortress.read_control_reward(image, lines, ocr)
    if current and current.target in receipts and receipts[current.target]["state"] == "claimed":
        _detail_back(target, ocr, stop_event)
        current = None

    if current is None:
        image, lines = fortress.open_game_screen(target, ocr, stop_event, "mail")

        def row(im, ln):
            if not fortress.alliance_mail_selected(im, ln):
                return None
            for line in ln:
                word = (line.get("words") or [None])[0]
                if not word or fortress.compact(line["text"]) != fortress.CONTROL_MAIL:
                    continue
                y = round(word["y"])
                if not (142 < word["x"] < 226 and 155 < y < 1063):
                    continue
                body = "".join(fortress._text_in(ln, (142, y + 19, 590, y + 53)))
                label = fortress._control_mail_target(body)
                sent = fortress.mail_row_stamp(im, ln, y, ocr)
                if label in wanted - receipts.keys() and (sent is None or sent >= due):
                    return (312, y + 36), label, sent
            return None

        if not row(image, lines):
            return None
        frame, (point, label, listed_stamp) = fortress._wait_alliance_page(
            target, ocr, stop_event, row, "成功控制堡垒邮件列表在打开前发生变化")
        _tap(target, stop_event, frame, point)
        _, current = fortress._wait_alliance_page(
            target, ocr, stop_event, lambda im, ln: fortress.read_control_reward(im, ln, ocr),
            "钥匙邮件详情和右上角时间未确认")
        if current.target != label or listed_stamp is not None and current.stamp != listed_stamp:
            raise ValueError("钥匙邮件详情与列表不一致")

    if current.target not in wanted or not due <= current.stamp <= datetime.now(fortress.SHANGHAI):
        raise ValueError("当前邮件不属于本站到期的钥匙奖励")
    key, stamp = current.target, fortress.format_stamp(current.stamp)
    if not current.claimed:
        prior = receipts.get(key)
        if prior is not None:
            raise fortress.MailClaimUnconfirmed("这封钥匙邮件已有领取操作，等待结果")
        with target.touch_session() as touch:
            frame, _ = fortress._wait_alliance_page(
                target, ocr, stop_event, lambda im, ln: fortress.read_control_reward(im, ln, ocr) == current,
                "钥匙领取控件已变化")
            if stop_event.is_set() or not target.foreground_is_game():
                raise InterruptedError()
            receipts[key] = {"stamp": stamp, "state": "pending"}
            save()
            if stop_event.is_set():
                raise InterruptedError()
            touch.touch_request(fortress.map_content_point(current.point, fortress.REFERENCE, frame))
        fortress._wait_alliance_page(
            target, ocr, stop_event,
            lambda im, ln: ((mail := fortress.read_control_reward(im, ln, ocr)) is not None
                            and (mail.target, mail.stamp) == (current.target, current.stamp) and mail.claimed),
            "钥匙领取结果待核对", timeout=6.0)
    if key in receipts and receipts[key]["stamp"] != stamp:
        raise ValueError("当前邮件与本站钥匙发件时间记录不一致")
    receipts[key] = {"stamp": stamp, "state": "claimed"}
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
        fortress._wait_alliance_page(target, ocr, stop_event, lambda _im, ln: fortress.is_game_root(ln),
                                      "返回野外未确认")


def _next_key(run, *, within=None):
    now = datetime.now(fortress.SHANGHAI)
    for due, tag in fortress.return_queue(run):
        arrival = run["returned"].get(tag)
        if arrival and fortress.parse_stamp(arrival) < due:
            return due, tag
        if due > now and (within is None or due - now <= within):
            return due, tag
    return None


def _key_visit(target, ocr, stop_event, run, tag, due, save, notify, on_timeout, rate):
    arrival = run["returned"].get(tag)
    if not arrival:
        _visit(target, ocr, stop_event, run, tag, save, notify, on_timeout, rate, due)
        arrived = datetime.now(fortress.SHANGHAI)
        run["returned"][tag] = fortress.format_stamp(arrived)
        save()
        if arrived >= due:
            raise ValueError(f"[{tag}] 入盟时已超过钥匙返回截止")
        notify(f"[{tag}] 已在截止前返回")
        _member_to_root(target, ocr, stop_event, tag)
        fortress.open_game_screen(target, ocr, stop_event, "mail")
    else:
        _, image, lines = fortress._alliance_frame(target, ocr, stop_event)
        if fortress.joined_tag_matches(image, lines, ocr, tag):
            _member_to_root(target, ocr, stop_event, tag)
            fortress.open_game_screen(target, ocr, stop_event, "mail")
        elif fortress.is_game_root(lines) or fortress.is_regular_activity(lines) or fortress.is_mail_list(lines):
            fortress.open_game_screen(target, ocr, stop_event, "mail")
    notify(f"[{tag}] 在联盟邮件等待 {fortress.format_stamp(due)} 的钥匙")
    while not stop_event.is_set() and tag not in run["keys"]:
        remaining = (due - datetime.now(fortress.SHANGHAI)).total_seconds()
        if remaining > 0:
            stop_event.wait(min(15, remaining))
            continue
        try:
            mail = claim_key_mail(target, ocr, stop_event, run, tag, save)
        except (fortress.PageNotVerified, fortress.MailClaimUnconfirmed):
            stop_event.wait(1)
            continue
        if mail is None:
            if not run["mail"].get(tag):
                now = datetime.now(fortress.SHANGHAI)
                following = any(other != tag and now < deadline <= now + KEY_RETURN_LEAD
                                for deadline, other in fortress.return_queue(run))
                if following:
                    run.setdefault("key_unavailable", {})[tag] = fortress.format_stamp(now)
                    save()
                    notify(f"[{tag}] 尚未检测到本人钥匙邮件，按已确认的下一站时间继续")
                    return
            try:
                _refresh_alliance_mail(target, ocr, stop_event)
            except fortress.PageNotVerified:
                stop_event.wait(1)
            continue
        notify(f"[{tag}] 已确认领取 {mail.target} 钥匙 · {fortress.format_stamp(mail.stamp)}")


def run_route(target, ocr, stop_event, run, save, *, notify, on_timeout, rate=100):
    active = None
    while not stop_event.is_set():
        normal_station = run["index"] < len(run["route"])
        deferred = run.get("deferred_victory", {})
        remaining_sites = normal_station or bool(deferred)
        key_visit = _next_key(run, within=KEY_RETURN_LEAD if remaining_sites else None)
        if key_visit:
            due, tag = key_visit
            _key_visit(target, ocr, stop_event, run, tag, due, save, notify, on_timeout, rate)
            active = None
            continue
        if not remaining_sites:
            missed = [tag for due, tag in fortress.return_queue(run)
                      if due <= datetime.now(fortress.SHANGHAI) and tag not in run["keys"]]
            return "堡垒路线已完成" + (f" · 超过钥匙截止：{'、'.join(missed)}" if missed else "")

        requested = (run["route"][run["index"]] if normal_station
                     else next(stop for stop in run["route"] if stop["alliance"] in deferred))
        station = fortress.resolved_station(run, requested)
        tag = station["alliance"]
        wanted = len(station["targets"])
        mails = run["mail"].get(tag, {})
        if (all(entry["number"] is not None for entry in station["targets"])
                and sum(state == "claimed" for state in mails.values()) >= wanted):
            if normal_station:
                run["index"] += 1
            else:
                deferred.pop(tag)
            save()
            continue

        checked_detail = None
        if tag in run["occupied"]:
            _, checked_detail = fortress.capture_reward(target, ocr)
        if active != tag and checked_detail is None:
            _visit(target, ocr, stop_event, run, tag, save, notify, on_timeout, rate)
            _member_to_root(target, ocr, stop_event, tag)
        active = tag
        if tag not in run["occupied"]:
            if any(entry["number"] is None for entry in station["targets"]):
                station = resolve_targets(target, ocr, stop_event, run, station, save)
                wanted = len(station["targets"])
                names = "、".join(f"{entry['kind']}{entry['number']}" for entry in station["targets"])
                notify(f"[{tag}] 已识别目标 {names}")
            notify(f"[{tag}] 等待指定目标蓝色占领")
            if not _occupation(target, ocr, stop_event, station, lambda: bool(_next_key(run, within=KEY_RETURN_LEAD))):
                continue
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
            final_mail = sum(state == "claimed" for state in mails.values()) + 1 >= wanted
            mail = claim_victory(target, ocr, stop_event, run, tag, save, opened=checked_detail,
                                 close_after=final_mail, expected_stamp=expected_stamp)
        except fortress.MailNotYetVisible:
            try:
                _refresh_alliance_mail(target, ocr, stop_event)
            except fortress.PageNotVerified:
                stop_event.wait(.7)
            continue
        except (fortress.MailClaimUnconfirmed, fortress.PageNotVerified):
            stop_event.wait(1)
            continue
        notify(f"[{tag}] 已领取胜利邮件 · {fortress.format_stamp(mail.stamp)}")
        if sum(state == "claimed" for state in run["mail"][tag].values()) < wanted:
            _detail_back(target, ocr, stop_event)
    raise InterruptedError()
