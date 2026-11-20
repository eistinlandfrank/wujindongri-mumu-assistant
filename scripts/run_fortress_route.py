"""Validate a fortress route or execute one explicitly selected checkpoint."""
from __future__ import annotations

import argparse
from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime
import json
from pathlib import Path
import re
from statistics import median
import sys
from tempfile import TemporaryDirectory
from threading import Event
from time import perf_counter

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from wjdr_backend import MuMuADB
from wjdr_backend import DeviceLease
from wjdr_beast_supervision import verify_bound_identity
import wjdr_fortress as fortress
import wjdr_fortress_flow as flow
from wjdr_fortress_ocr import FortressOcr
from wjdr_mumu_ipc import RouteCapture
from wjdr_schedule import GRACE_SECONDS


STEPS = ("status", "capture-check", "enter", "solo-ready", "solo-record", "occupation", "mail-list",
         "reward", "auto-reward", "advance", "return-keys", "key-record", "key-mail",
         "rapid-enter", "rapid-enter-check", "auto-route")
KEY_STEPS = {"return-keys", "key-record", "key-mail"}


@dataclass(frozen=True)
class Plan:
    device: str
    mumu_index: int
    round_start: datetime
    take_keys: bool
    stops: tuple[fortress.Stop, ...]
    start_at: datetime | None = None


def read_plan(path: Path) -> Plan:
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    fields = {"device", "mumu_index", "round_start", "take_keys", "stops"}
    if not isinstance(data, dict) or not fields <= data.keys() or data.keys() - fields - {"capture", "start_at"}:
        raise ValueError("配置需包含 device、mumu_index、round_start、take_keys 和 stops")
    device = data["device"]
    index = data["mumu_index"]
    if not isinstance(device, str) or not re.fullmatch(r"[A-Za-z0-9.:_-]+", device):
        raise ValueError("device 请填写明确的 ADB 序列号")
    if type(index) is not int or index < 0:
        raise ValueError("mumu_index 必须是 MuMu 实例编号")
    if type(data["take_keys"]) is not bool:
        raise ValueError("take_keys 必须是 true 或 false")
    if data.get("capture", "ipc") != "ipc":
        raise ValueError("capture 只支持 ipc，也可省略")
    start = data["round_start"]
    if not isinstance(start, str):
        raise ValueError("round_start 请按北京时间填写 YYYY-MM-DD HH:MM:SS")
    round_start = fortress.parse_stamp(start)
    scheduled = data.get("start_at")
    if scheduled is not None and not isinstance(scheduled, str):
        raise ValueError("start_at 请按北京时间填写 YYYY-MM-DD HH:MM:SS")
    start_at = fortress.parse_stamp(scheduled) if scheduled else None
    if not isinstance(data["stops"], list) or not data["stops"]:
        raise ValueError("stops 至少填写一个联盟")
    rows = []
    for row in data["stops"]:
        if not isinstance(row, dict) or set(row) != {"alliance", "targets"}:
            raise ValueError("每站填写 alliance 和 targets")
        tag = row["alliance"]
        if not isinstance(tag, str) or not re.fullmatch(r"[A-Za-z0-9-]{1,16}", tag):
            raise ValueError("alliance 填游戏内方括号里的短标签，例如 ZYZ")
        if not isinstance(row["targets"], list) or not row["targets"]:
            raise ValueError(f"[{tag}] 至少填写一个目标")
        targets = []
        for target in row["targets"]:
            if (not isinstance(target, dict) or "kind" not in target
                    or target.keys() - {"kind", "number", "mode"}):
                raise ValueError(f"[{tag}] 请填写目标类型并核对编号和打法")
            kind, number, mode = target["kind"], target.get("number"), target.get("mode")
            if kind == fortress.ALL_REGISTERED:
                mode = target.get("mode", fortress.UNSPECIFIED_TACTIC)
                if number is not None or mode not in ("单撞", "集结", fortress.UNSPECIFIED_TACTIC):
                    raise ValueError(f"[{tag}] 全部报名可填写整站打法")
            elif (not isinstance(kind, str) or kind not in fortress.TARGET_LIMITS
                    or (number is None and kind != "堡垒")
                    or (number is not None and (type(number) is not int or not 1 <= number <= fortress.TARGET_LIMITS[kind]))
                    or mode not in ("单撞", "集结")):
                raise ValueError(f"[{tag}] 堡垒选 1–12，要塞选 1–4，打法为单撞或集结")
            targets.append(fortress.target_text(kind, number, mode))
        rows.append((tag, "，".join(targets)))
    return Plan(device, index, round_start, data["take_keys"], fortress.parse_route(rows), start_at)


def print_plan(plan: Plan) -> None:
    print(f"MuMu {plan.mumu_index} 号 · {plan.device}")
    print(f"本轮开始 {fortress.format_stamp(plan.round_start)}（北京时间）")
    if plan.start_at:
        print(f"首站预约 {fortress.format_stamp(plan.start_at)}（北京时间）")
    print("钥匙返回 " + ("开启" if plan.take_keys else "关闭"))
    print("截图 MuMu IPC")
    for index, stop in enumerate(plan.stops, 1):
        targets = "、".join(fortress.target_text(t.kind, t.number, t.mode) for t in stop.targets)
        print(f"{index}. [{stop.alliance}] {targets}")


def bind(plan: Plan):
    adb = MuMuADB()
    adb.players = adb._manager_players()
    adb.set_device(plan.device)
    identity = adb.device_identity(plan.device)
    if not identity.startswith(f"mumu:{plan.mumu_index}:android:"):
        raise ValueError(f"配置的 ADB 无法确认是 MuMu {plan.mumu_index} 号")
    return adb, identity


def wait_for_start(start_at: datetime, stop_event, *, clock=None) -> None:
    clock = clock or (lambda: datetime.now(fortress.SHANGHAI))
    while not stop_event.is_set():
        remaining = (start_at - clock()).total_seconds()
        if remaining < -GRACE_SECONDS:
            raise ValueError("已超过首站预约时间 30 秒，本次预约已错过")
        if remaining <= 0:
            return
        stop_event.wait(min(remaining, 15))
    raise InterruptedError()


claim_scheduled_start = flow.claim_scheduled_start


def route_state(plan: Plan, previous: dict | None) -> dict:
    run = fortress.new_run(plan.stops, plan.round_start)
    if previous:
        same_round = previous["round_start"] == run["round_start"]
        if same_round and previous["route"] == run["route"]:
            run = deepcopy(previous)
        else:
            prior_actions = previous.get("applications", {})
            if same_round and (previous.get("scheduled_start") or previous["index"] or previous["occupied"] or previous["mail"]
                               or previous["last_solo"] or prior_actions):
                raise ValueError("同一轮已有进度，请保留原路线和目标后继续")
            run["applications"] = deepcopy({
                tag: record for tag, record in prior_actions.items() if record["state"] != "joined"
            })
    run["take_keys"] = plan.take_keys
    return run


def current_stop(run: dict) -> dict:
    if run["index"] >= len(run["route"]):
        raise ValueError("本轮路线已走完")
    return fortress.resolved_station(run, run["route"][run["index"]])


def print_status(run: dict) -> None:
    index = run["index"]
    if index == len(run["route"]):
        deferred = run.get("deferred_victory", {})
        print(f"待补领胜利邮件 {'、'.join(deferred)}" if deferred else "联盟路线已完成")
    else:
        stop = current_stop(run)
        tag = stop["alliance"]
        claimed = sum(status == "claimed" for status in run["mail"].get(tag, {}).values())
        print(f"当前第 {index + 1} 站 [{tag}] · 占领{'已核对' if tag in run['occupied'] else '待核对'}"
              f" · 已登记胜利邮件 {claimed} 封")
    now = datetime.now(fortress.SHANGHAI)
    for due, tag in fortress.return_queue(run):
        state = "已返回，钥匙待登记" if tag in run["returned"] else "待返回"
        if due <= now and tag not in run["returned"]:
            state = "已过返回截止"
        print(f"[{tag}] {fortress.format_stamp(due)} 前返回 · {state}")


def check_capture(target: RouteCapture, ocr) -> None:
    target.screenshot()
    times = []
    known = 0
    for _ in range(4):
        start = perf_counter()
        frame = target.screenshot()
        times.append((perf_counter() - start) * 1000)
        view = fortress.normalize_frame(frame)
        lines = ocr(view)
        if (fortress.is_game_root(lines) or fortress.is_regular_activity(lines)
                or fortress.is_mail_list(lines) or fortress.read_joined_alliance(lines)
                or fortress.is_unaffiliated_alliance_page(lines) or fortress.read_mail(view, lines, ocr)
                or fortress.read_control_reward(view, lines, ocr)):
            known += 1
    print(f"MuMu IPC 热帧中位数 {median(times):.1f} ms · 已识别游戏画面 {known}/4")
    if known != 4:
        raise ValueError("请保持在联盟、活动、邮件或主城页面后重查")


def check_occupation(target, ocr, stop_event, station: dict) -> None:
    frame, lines = fortress.open_fortress_activity(target, ocr, stop_event)
    first = fortress.read_occupation(frame, lines, ocr)
    first_registration = fortress.registration_matches(frame, lines, ocr, station)
    _, frame, lines = fortress._alliance_frame(target, ocr, stop_event)
    second = fortress.read_occupation(frame, lines, ocr)
    if (first is None or first != second or not fortress.occupation_complete(first, station)
            or not first_registration or not fortress.registration_matches(frame, lines, ocr, station)):
        raise ValueError("本站尚未核对到全部目标由指定联盟蓝色占领")


def run_step(args, target, ocr, stop_event, run: dict, save, timeout_messages: list[str]) -> None:
    now = datetime.now(fortress.SHANGHAI)
    if args.step == "status":
        print_status(run)
        return
    if args.step == "auto-route":
        message = flow.run_route(
            target, ocr, stop_event, run, save, rate=getattr(args, "rapid_rate", 10),
            notify=lambda message: print(message, flush=True), on_timeout=timeout_messages.append)
        print(message)
        return
    if args.step == "key-mail":
        returned = [tag for tag in run["returned"] if tag not in run["keys"]]
        if not returned:
            raise ValueError("没有已按时返回且待领取钥匙的联盟")
        tag = max(returned, key=run["returned"].get)
        mail = flow.claim_key_mail(target, ocr, stop_event, run, tag, save)
        if mail is None:
            print(f"[{tag}] 当前联盟邮件尚无对应的钥匙奖励")
        else:
            print(f"[{tag}] 已核对 {mail.target} 钥匙 · {fortress.format_stamp(mail.stamp)}")
        return
    if args.step == "key-record":
        _, tag = fortress._wait_alliance_page(
            target, ocr, stop_event, lambda _image, lines: fortress.read_joined_alliance(lines),
            "请打开已经领取钥匙的联盟主页")
        if fortress.return_deadline(run, tag) is None:
            raise ValueError(f"[{tag}] 没有本轮胜利邮件记录")
        run["keys"][tag] = fortress.format_stamp(datetime.now(fortress.SHANGHAI))
        save()
        print(f"[{tag}] 已登记钥匙领取")
        return
    if args.step == "return-keys":
        pending = [(due, tag) for due, tag in fortress.return_queue(run)
                   if now < due and "claimed" in run["mail"][tag].values()]
        if not pending:
            raise ValueError("没有尚可按时返回的钥匙站点")
        due, tag = pending[0]
        result = fortress.enter_route_alliance(
            target, ocr, stop_event, run, tag, save, leave_current=args.leave_current,
            notify=lambda msg: print(msg, flush=True), on_timeout=timeout_messages.append, return_by=due)
        if not result.joined:
            raise ValueError(result.message)
        arrived = datetime.now(fortress.SHANGHAI)
        run["returned"][tag] = fortress.format_stamp(arrived)
        save()
        print(f"[{tag}] {'已按时返回' if arrived < due else '已返回，超过截止时间'} · 钥匙领取后运行 key-record")
        return

    rapid_tag = getattr(args, "rapid_alliance", None)
    station = {"alliance": rapid_tag} if rapid_tag else current_stop(run)
    tag = station["alliance"]
    if args.step in {"rapid-enter", "rapid-enter-check"}:
        check_only = args.step == "rapid-enter-check"
        duration = (None if getattr(args, "rapid_unlimited", False)
                    else 60.0 * getattr(args, "rapid_minutes", 3))
        result = fortress.run_rapid_join(
            target, ocr, stop_event, run, tag, save, rate=getattr(args, "rapid_rate", 10),
            duration=duration, check_only=check_only,
            notify=lambda message: print(message, flush=True), on_timeout=timeout_messages.append)
        if not result.joined and not check_only:
            raise ValueError(result.message)
        if result.joined:
            due = fortress.return_deadline(run, tag)
            if due and now < due and tag not in run["returned"] and tag not in run["keys"]:
                arrived = datetime.now(fortress.SHANGHAI)
                if arrived < due:
                    run["returned"][tag] = fortress.format_stamp(arrived)
                    save()
        print(result.message)
    elif args.step == "enter":
        result = fortress.enter_route_alliance(
            target, ocr, stop_event, run, tag, save, leave_current=args.leave_current,
            notify=lambda msg: print(msg, flush=True), on_timeout=timeout_messages.append)
        if not result.joined:
            raise ValueError(result.message)
        print(result.message)
    elif args.step in {"solo-ready", "solo-record"}:
        if not any(t["mode"] == "单撞" for t in station["targets"]):
            raise ValueError("本站没有单撞目标")
        last = run["last_solo"]
        if last and now - fortress.parse_stamp(last) < fortress.SOLO_INTERVAL:
            allowed = fortress.parse_stamp(last) + fortress.SOLO_INTERVAL
            raise ValueError(f"下一次单撞时间 {fortress.format_stamp(allowed)}")
        if args.step == "solo-record":
            run["last_solo"] = fortress.format_stamp(now)
            save()
            print(f"已登记单撞，下一次可在 {fortress.format_stamp(now + fortress.SOLO_INTERVAL)} 后进行")
        else:
            print("已达到 3 分钟单撞间隔")
    elif args.step in {"occupation", "auto-reward"}:
        already_verified = tag in run["occupied"]
        if args.step == "occupation" or not already_verified:
            station = flow.resolve_targets(target, ocr, stop_event, run, station, save)
            check_occupation(target, ocr, stop_event, station)
        if not already_verified:
            run["occupied"].append(tag)
            save()
        print(f"[{tag}] 全部目标蓝色占领已核对")
        if args.step == "auto-reward":
            mails = run["mail"].get(tag, {})
            if sum(value == "claimed" for value in mails.values()) >= len(station["targets"]):
                print(f"[{tag}] 本站胜利邮件已登记")
                return
            opened = None
            if already_verified:
                _, opened = fortress.capture_reward(target, ocr)
            mail = flow.claim_victory(target, ocr, stop_event, run, tag, save, opened=opened)
            print(f"[{tag}] 已登记胜利邮件 {fortress.format_stamp(mail.stamp)}")
    elif args.step in {"mail-list", "reward", "advance"}:
        if tag not in run["occupied"]:
            raise ValueError("请先运行 occupation 核对本站全部目标")
        if args.step == "mail-list":
            _, lines = fortress.open_game_screen(target, ocr, stop_event, "mail")
            times = fortress.visible_reward_stamps(
                lines, fortress.parse_stamp(run["round_start"]), datetime.now(fortress.SHANGHAI))
            print("当前画面胜利邮件 " + ("、".join(map(fortress.format_stamp, times)) or "暂无"))
        elif args.step == "reward":
            expected = fortress.parse_stamp(args.sent_at)

            def record(mail, status):
                if mail.stamp != expected:
                    raise ValueError("当前邮件右上角时间与 --sent-at 不一致")
                fortress.record_mail(run, tag, expected, status, datetime.now(fortress.SHANGHAI))
                save()

            mail = fortress.collect_reward(target, ocr, stop_event, record, claim=True)
            print(f"[{tag}] 已登记胜利邮件 {fortress.format_stamp(mail.stamp)}")
        else:
            mails = run["mail"].get(tag, {})
            if "pending" in mails.values() or sum(status == "claimed" for status in mails.values()) < len(station["targets"]):
                raise ValueError("请核对并登记本站本轮的全部胜利邮件")
            run["index"] += 1
            save()
            print_status(run)


def show_timeout(message: str):
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QApplication, QInputDialog, QMessageBox

    app = QApplication.instance() or QApplication([])
    box = QMessageBox(QMessageBox.Icon.Warning, "联盟加入超时", message, QMessageBox.StandardButton.Ok)
    resume = None
    if "连点时间已到" in message:
        resume = box.addButton("继续连点…", QMessageBox.ButtonRole.ActionRole)
    box.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, True)
    box.setTextFormat(Qt.TextFormat.PlainText)
    box.show()
    box.raise_()
    box.activateWindow()
    app.alert(box)
    box.exec()
    if resume is None or box.clickedButton() is not resume:
        return None
    mode, ok = QInputDialog.getItem(None, "继续连点", "停止方式", ["定时停止", "不限时"], 0, False)
    if not ok:
        return None
    duration = ["--rapid-unlimited"]
    if mode == "定时停止":
        minutes, ok = QInputDialog.getInt(None, "连点时长", "分钟", 3, 1, 1440)
        if not ok:
            return None
        duration = ["--rapid-minutes", str(minutes)]
    tag = message.partition("]")[0].lstrip("[")
    return ["--rapid-alliance", tag, "--rapid-rate", "100", *duration]


def _run_main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("plan", type=Path, help="UTF-8 JSON 路线配置")
    parser.add_argument("--step", choices=STEPS, help="单步运行检查点，省略只校验和打印配置")
    parser.add_argument("--execute", action="store_true", help="实际连接配置中的实例并运行该步")
    parser.add_argument("--wait-start", action="store_true", help="等到 start_at，仅启动一次指定流程")
    parser.add_argument("--leave-current", action="store_true", help="允许 enter 或 return-keys 退出当前联盟")
    parser.add_argument("--rapid-rate", choices=(10, 100), type=int, default=10, help="加入连点的目标频率")
    parser.add_argument("--rapid-alliance", help="明确选择本轮路线中的连点目标")
    rapid_limit = parser.add_mutually_exclusive_group()
    rapid_limit.add_argument("--rapid-minutes", type=int, default=3, help="连点时长，默认 3 分钟")
    rapid_limit.add_argument("--rapid-unlimited", action="store_true", help="连点直到入盟、画面变化或手动停止")
    parser.add_argument("--sent-at", help="已核对归属的当前胜利邮件右上角时间，仅用于 reward")
    args = parser.parse_args(argv)
    timeout_messages = []
    stop_event = Event()
    try:
        plan = read_plan(args.plan)
        if args.step in KEY_STEPS and not plan.take_keys:
            raise ValueError("take_keys 为 false，本轮关闭钥匙流程")
        if args.sent_at and args.step != "reward":
            raise ValueError("--sent-at 仅用于 reward")
        if args.leave_current and args.step not in {"enter", "return-keys"}:
            raise ValueError("--leave-current 仅用于 enter 或 return-keys")
        if not 1 <= args.rapid_minutes <= 1440:
            raise ValueError("--rapid-minutes 需为 1 到 1440")
        if (args.rapid_minutes != 3 or args.rapid_unlimited) and args.step not in {
            "rapid-enter", "rapid-enter-check",
        }:
            raise ValueError("自定义时长仅用于加入连点")
        if args.rapid_rate != 10 and args.step not in {"rapid-enter", "rapid-enter-check", "auto-route"}:
            raise ValueError("连点速度仅用于加入连点及自动跑盟")
        if args.rapid_alliance and (args.step not in {"rapid-enter", "rapid-enter-check"}
                                    or args.rapid_alliance not in {stop.alliance for stop in plan.stops}):
            raise ValueError("--rapid-alliance 需为本轮已配置的连点目标")
        if args.wait_start and (args.step not in {"enter", "auto-route"} or plan.start_at is None):
            raise ValueError("--wait-start 需要 start_at 和 enter 或 auto-route 步骤")
        if not args.execute:
            print_plan(plan)
            if args.step:
                print(f"拟运行检查点 {args.step}")
            return 0
        if not args.step:
            raise ValueError("--execute 必须搭配 --step")
        if (args.step == "auto-route" and not args.wait_start
                and plan.round_start > datetime.now(fortress.SHANGHAI)):
            raise ValueError("尚未到本轮时间，可加 --wait-start 预约开跑")
        if args.step == "reward" and not args.sent_at:
            raise ValueError("reward 需用 --sent-at 明确当前邮件的右上角发件时间")
        if args.sent_at:
            fortress.parse_stamp(args.sent_at)
        if args.wait_start:
            print(f"等待首站预约 {fortress.format_stamp(plan.start_at)}（北京时间）", flush=True)
            wait_for_start(plan.start_at, stop_event)
        target, identity = bind(plan)
        lease = DeviceLease(identity)
        if not lease.acquire():
            raise ValueError("当前账号正在执行其他任务")
        try:
            if not verify_bound_identity(target, plan.device, identity):
                raise ValueError("实时账号身份未确认")
            if args.step == "capture-check":
                if not target.foreground_is_game():
                    raise ValueError("请先打开游戏并保持同一页面")
                with (TemporaryDirectory(prefix="wjdr-fortress-route-") as temp,
                      FortressOcr(Path(temp), stop_event) as ocr,
                      RouteCapture(target, plan.mumu_index) as capture):
                    check_capture(capture, ocr)
                return 0
            previous = fortress.load_run(identity)
            run = route_state(plan, previous)

            def save():
                nonlocal previous
                fortress.save_run(identity, previous, run)
                previous = deepcopy(run)

            if args.step not in {"status", "advance", "solo-ready", "solo-record"} and not target.foreground_is_game():
                raise ValueError("请先在配置的 MuMu 实例打开游戏")
            if args.wait_start:
                claim_scheduled_start(run, plan.start_at, save)
            elif args.step not in {"status", "rapid-enter-check"} and run != previous:
                save()
            with (TemporaryDirectory(prefix="wjdr-fortress-route-") as temp,
                  FortressOcr(Path(temp), stop_event) as ocr,
                  RouteCapture(target, plan.mumu_index) as capture):
                run_step(args, capture, ocr, stop_event, run, save, timeout_messages)
        finally:
            lease.release()
        return 0
    except (KeyboardInterrupt, InterruptedError):
        stop_event.set()
        print("已停止", file=sys.stderr)
        return 130
    except (OSError, ValueError, RuntimeError) as exc:
        print(str(exc), file=sys.stderr)
        for message in timeout_messages:
            resume = show_timeout(message)
            if resume:
                next_args = [str(args.plan), "--step", "rapid-enter", "--execute", *resume]
                after = ([str(args.plan), "--step", "auto-route", "--execute", "--rapid-rate", str(args.rapid_rate)]
                         if args.step == "auto-route" else None)
                return next_args, after
        return 1


def main(argv=None) -> int:
    pending_route = None
    while True:
        result = _run_main(argv)
        if isinstance(result, int):
            if result or pending_route is None:
                return result
            argv, pending_route = pending_route, None
        else:
            argv, after = result
            if after is not None:
                pending_route = after


if __name__ == "__main__":
    raise SystemExit(main())
