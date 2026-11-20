"""Follow this alliance's fresh reward-release messages on one bound account."""
from __future__ import annotations

import argparse
from datetime import datetime
from hashlib import sha256
import json
from pathlib import Path
import re
import sys
from tempfile import TemporaryDirectory
from threading import Event
from time import monotonic

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import wjdr_fortress as fortress
import wjdr_fortress_flow as flow
from scripts.run_fortress_route import wait_for_start
from wjdr_backend import (
    CONFIG_DIR, AdbError, DeviceLease, MuMuADB, match_red_packet_chat_entry,
)
from wjdr_beast_supervision import verify_bound_identity
from wjdr_fortress_ocr import FortressOcr
from wjdr_mumu_ipc import RouteCapture


def is_release(text: str) -> bool:
    text = fortress.compact(text)
    if re.search(r"退出了联盟|加入了我们的联盟|先别|不要|别退|别跑|暂缓|暂时|未发完|没发完|"
                 r"还没|还未|等通知|等发完|发完[了啦]?(?:前|后|的话)|才可以|如果|什么时候|多久|几点|怎么|为啥|"
                 r"[?？吗么]|有人说|谁能|能不能|可不可以", text):
        return False
    if re.search(r"(?:可|可以|请|自由|直接)退盟|(?:大家|全体)退盟|"
                 r"(?:可以|请|直接)退出(?:该|本)?联盟", text):
        return True
    finished = r"已发完|发完(?:了|啦|毕)|发放(?:完成|完毕)"
    if re.fullmatch(r"@所有人[，,:：]?(?:发完[了啦]?|可以跑了)[。！!]?$", text):
        return True
    return bool(re.search(r"(?:鸡蛋|堡垒|要塞|奖励).{0,12}(?:" + finished + r"|发完[。！!]?$)", text)
                or re.search(r"(?:" + finished + r").{0,8}(?:可以跑|可跑|跑路|退盟|去下一个)", text))


def chat_panel(lines) -> bool:
    title = any(text.endswith("聊天") for text in fortress._text_in(lines, (0, 0, 180, 66)))
    tabs = set(fortress._text_in(lines, (71, 75, 590, 143)))
    return title and len(tabs & {"世界", "联盟", "个人"}) >= 2


def alliance_chat(image, lines) -> bool:
    if not chat_panel(lines):
        return False
    r, g, b = image.getpixel((270, 121))[:3]
    return 175 < r < b + 15 and g >= r and b >= 178 and b - r < 45


def release_messages(lines, tag: str, next_tag: str | None = None) -> dict[str, str | None]:
    rows = sorted(
        (round(line["words"][0]["y"]), round(line["words"][0]["x"]), fortress.compact(line["text"]))
        for line in lines if line.get("words") and 145 < line["words"][0]["y"] < 1090
    )
    results = {}
    message_start = 0
    channel_time = None
    body = []
    sender_matches = False

    def add(text, stamp=None, trusted_sender=False):
        handoff = next_tag and re.fullmatch(r"@所有人[，,:：]?(?:去|转|下一站)?" + re.escape(next_tag)
                                             + r"[。！!]?$", text, re.IGNORECASE)
        if handoff or (trusted_sender and is_release(text)):
            results[text] = stamp

    pinned = next((y for y, x, text in rows if x < 95 and "联盟公告" in text), None)
    pin_end = next((y for y, x, text in rows if pinned is not None and pinned < y < 390
                    and x < 100 and text.startswith(f"[{tag}]")), None)
    if pin_end:
        add("".join(text for y, x, text in rows if pinned < y < pin_end and x < 120), trusted_sender=True)
    tag_pattern = r"\[(?:" + "|".join(map(re.escape, filter(None, (tag, next_tag)))) + r")\]"
    for y, x, text in rows:
        if pin_end and y <= pin_end:
            continue
        if re.fullmatch(r"(?:[01]?\d|2[0-3]):[0-5]\d", text) and 225 <= x <= 360:
            add("".join(body), channel_time, sender_matches)
            channel_time = text
            message_start, body, sender_matches = 0, [], False
        elif 95 <= x < 215 and (text.startswith("统帅") or re.search(tag_pattern, text)):
            add("".join(body), channel_time, sender_matches)
            message_start, body = y, []
            sender_matches = bool(re.search(tag_pattern, text))
        elif message_start and 31 <= y - message_start <= 146 and 116 <= x < 610:
            if not re.search(r"退出了|加入了|欢迎!", text):
                body.append(text)
    add("".join(body), channel_time, sender_matches)
    return results


def departing_members(image, lines) -> set[str]:
    members = set()
    for row in lines:
        if not row.get("words"):
            continue
        word = row["words"][0]
        x, y = round(word["x"]), round(word["y"])
        if not (127 <= x < 438 and 239 <= y < 1087):
            continue
        match = re.fullmatch(r"(.{1,40}?)退出了联[盟盥孟驴]?[。！!]?$", fortress.compact(row["text"]))
        if not match:
            continue
        # The game colors the departing member's name red in its system message.
        pixels = np.asarray(image.crop((x, y - 2, min(x + 92, 661), y + 21)).convert("RGB"), dtype=np.int16)
        red, green, blue = pixels.transpose(2, 0, 1)
        if np.count_nonzero((red >= 145) & (3 * green < 2 * red) & (4 * blue < 3 * red)) >= 9:
            members.add(sha256(match[1].encode()).hexdigest())
    return members


def close_chat(target, ocr, stop):
    frame, _ = fortress._wait_alliance_page(target, ocr, stop, lambda _im, lines: chat_panel(lines),
                                            "聊天页未确认")
    flow._tap(target, stop, frame, (636, 36))
    fortress._wait_alliance_page(target, ocr, stop, lambda _im, lines: fortress.is_game_root(lines),
                                "退出聊天后的野外页未确认", timeout=5)


def open_chat(target, ocr, stop):
    deadline = monotonic() + 4
    previous_entry = None
    while monotonic() < deadline:
        frame, _, lines = fortress._alliance_frame(target, ocr, stop)
        entry, _ = match_red_packet_chat_entry(frame, .88)
        if entry and entry == previous_entry and fortress.is_game_root(lines):
            break
        previous_entry = entry
    else:
        raise ValueError("野外聊天入口未确认")
    if stop.is_set() or not target.foreground_is_game():
        raise InterruptedError()
    target.tap(*entry)
    frame, selected = fortress._wait_alliance_page(
        target, ocr, stop,
        lambda im, lines: ("alliance" if alliance_chat(im, lines) else "chat") if chat_panel(lines) else None,
        "聊天面板未确认", timeout=6)
    if selected != "alliance":
        flow._tap(target, stop, frame, (336, 106))
        fortress._wait_alliance_page(target, ocr, stop, alliance_chat, "联盟频道未确认", timeout=5)


def await_release(target, ocr, stop, run, tag, save, notify):
    next_index = run["index"] + 1
    next_tag = run["route"][next_index] if next_index < len(run["route"]) else None
    seen = run.get("baseline")
    if seen is None:
        _, first = fortress._wait_alliance_page(
            target, ocr, stop,
            lambda im, lines: (release_messages(lines, tag, next_tag),) if alliance_chat(im, lines) else None,
            "首次联盟频道画面未确认")
        seen = [sha256(message.encode()).hexdigest() for message in first[0]]
        run["baseline"] = seen
        save()
    notify(f"[{tag}] 监听联盟频道，确认通知或至少 6 个不同成员退出后继续")
    prior = set()
    prior_departures = set()
    confirmed_departures = set()
    last_channel_frame = monotonic()
    while not stop.is_set():
        try:
            _, image, lines = fortress._alliance_frame(target, ocr, stop)
            channel_visible = alliance_chat(image, lines)
        except (AdbError, OSError, ValueError):
            channel_visible = False
        current = set()
        departures = set()
        if channel_visible:
            last_channel_frame = monotonic()
            departures = departing_members(image, lines)
            for message in release_messages(lines, tag, next_tag):
                digest = sha256(message.encode()).hexdigest()
                if digest not in seen:
                    current.add(digest)
        elif monotonic() - last_channel_frame >= 20:
            raise ValueError(f"[{tag}] 联盟频道持续无法确认，停在本盟以保留进度")
        confirmed_departures.update(departures & prior_departures)
        confirmed_notice = bool(current & prior)
        if confirmed_notice or len(confirmed_departures) > 5:
            run["release"] = {"tag": tag, "time": fortress.format_stamp(datetime.now(fortress.SHANGHAI)),
                              "source": "channel_notice" if confirmed_notice else "member_departures"}
            if not confirmed_notice:
                run["release"]["count"] = len(confirmed_departures)
            save()
            if confirmed_notice:
                notify(f"[{tag}] 已确认本盟可退盟通知")
            else:
                notify(f"[{tag}] 频道确认 {len(confirmed_departures)} 个不同成员退出")
            return
        prior = current
        prior_departures = departures
        stop.wait(.35)
    raise InterruptedError()


def run_route(target, ocr, stop, run, save, notify):
    while run["index"] < len(run["route"]):
        tag = run["route"][run["index"]]
        _, image, lines = fortress._alliance_frame(target, ocr, stop)
        on_chat = chat_panel(lines)
        if run.get("release"):
            if on_chat:
                close_chat(target, ocr, stop)
        else:
            at_checkpoint = ("baseline" in run and alliance_chat(image, lines)
                             and run["applications"].get(tag, {}).get("state") == "joined")
            if not at_checkpoint:
                if on_chat:
                    close_chat(target, ocr, stop)
                flow._visit(target, ocr, stop, run, tag, save, notify, notify, 100)
                flow._member_to_root(target, ocr, stop, tag)
                open_chat(target, ocr, stop)
            await_release(target, ocr, stop, run, tag, save, notify)
            close_chat(target, ocr, stop)
        if not fortress.prepare_alliance_route(target, ocr, stop, tag, leave_current=False):
            raise ValueError(f"[{tag}] 通知后当前联盟已变化")
        release = run.pop("release")
        run.setdefault("notices", []).append(release)
        run.pop("baseline", None)
        run["index"] += 1
        save()
        if run["index"] < len(run["route"]):
            notify(f"[{tag}] 转站条件已满足，转下一站 [{run['route'][run['index']]}]")
    notify("鸡蛋路线已完成，停在最后一站")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--device", required=True)
    parser.add_argument("--index", type=int, required=True)
    parser.add_argument("--start-at", required=True)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("route", nargs="+")
    args = parser.parse_args()
    if len(set(args.route)) != len(args.route) or not all(re.fullmatch(r"[A-Z0-9-]{1,16}", tag) for tag in args.route):
        parser.error("请逐站填写不重复的联盟短标签")
    start = fortress.parse_stamp(args.start_at)
    stop = Event()
    try:
        target = MuMuADB()
        target.players = target._manager_players()
        target.set_device(args.device)
        identity = target.device_identity()
        if not identity.startswith(f"mumu:{args.index}:android:") or not verify_bound_identity(target, args.device, identity):
            raise ValueError("未确认所选模拟器账号")
        digest = sha256(identity.encode()).hexdigest()[:24]
        path = CONFIG_DIR / "fortress_egg_runs" / f"{start:%Y%m%d-%H%M%S}-{digest}.json"
        if not args.resume:
            print(f"{args.index} 号等待 {fortress.format_stamp(start)}（北京时间），首站 [{args.route[0]}]", flush=True)
            wait_for_start(start, stop)
        lease = DeviceLease(identity)
        if not lease.acquire():
            raise ValueError("该账号已有任务")
        try:
            if not verify_bound_identity(target, args.device, identity) or not target.foreground_is_game():
                raise ValueError("开跑时未确认设备或游戏前台")
            run = (json.loads(path.read_text("utf8")) if path.exists() else
                   {"route": args.route, "index": 0, "round_start": fortress.format_stamp(start), "applications": {}})
            if run["route"] != args.route:
                raise ValueError("本轮的已保存顺序和命令不同")

            def save():
                fortress._atomic_json_write(path, run)

            save()
            with (TemporaryDirectory(prefix="wjdr-egg-route-") as folder, FortressOcr(Path(folder), stop) as ocr,
                  RouteCapture(target, args.index) as capture):
                run_route(capture, ocr, stop, run, save, lambda message: print(message, flush=True))
        finally:
            lease.release()
        return 0
    except (OSError, ValueError, RuntimeError) as exc:
        print(str(exc), file=sys.stderr, flush=True)
        return 1
    except (KeyboardInterrupt, InterruptedError):
        stop.set()
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
