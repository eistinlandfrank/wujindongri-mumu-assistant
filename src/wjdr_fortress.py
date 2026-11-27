"""Account-scoped fortress routes and conservative game-screen recognition."""
from __future__ import annotations

import json
import re
import time
import unicodedata
from contextlib import nullcontext
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from functools import lru_cache
from pathlib import Path
from statistics import median
from threading import Event, Lock, Thread

import cv2
import numpy as np
from PIL import Image, ImageOps

from wjdr_backend import (
    AdbError, CONFIG_DIR, _atomic_json_write, _serialized_account_write,
    content_viewport, map_content_point, resource_path,
)
from wjdr_mumu_ipc import RouteCapture

SHANGHAI = timezone(timedelta(hours=8))
PROFILE_PATH = CONFIG_DIR / "fortress_routes.json"
HISTORY_KEY = "history"
REFERENCE = (673, 1196)
CLAIM_POINT = (336, 762)
SOLO_INTERVAL = timedelta(minutes=3)
APPLICATION_TIMEOUT = 180
APPLICATION_POLL = 10
RAPID_JOIN_INTERVAL = 0.1
RAPID_JOIN_DURATION = 180.0
RAPID_JOIN_FRAME_TTL = 0.28
FORTRESS_MAIL = {"堡垒争夺胜利", "要塞争夺胜利"}
CONTROL_MAIL = "成功控制堡垒"
STAMP_FORMAT = "%Y-%m-%d %H:%M:%S"
TARGET_LIMITS = {"堡垒": 12, "要塞": 4}
ALL_REGISTERED = "全部报名"
UNSPECIFIED_TACTIC = "按安排"
TARGET_CARD_LEFTS = (36, 226, 416)


def compact(text: str) -> str:
    return "".join(unicodedata.normalize("NFKC", text).split())


@dataclass(frozen=True)
class Target:
    kind: str
    number: int | None
    mode: str


@dataclass(frozen=True)
class Stop:
    alliance: str
    targets: tuple[Target, ...]


def parse_targets(text: str) -> tuple[Target, ...]:
    targets = []
    for piece in re.split(r"[,，、；;\n]+", text):
        value = compact(piece)
        automatic = re.fullmatch(r"(?:默认|全部报名)(单撞|撞|集结|按安排)?", value)
        if automatic:
            mode = automatic[1] or UNSPECIFIED_TACTIC
            targets.append(Target(ALL_REGISTERED, None, "单撞" if mode == "撞" else mode))
            continue
        sole = re.fullmatch(r"(?:唯一)?堡垒(单撞|撞|集结)", value)
        if sole:
            targets.append(Target("堡垒", None, "单撞" if sole[1] == "撞" else sole[1]))
            continue
        match = re.fullmatch(r"(堡垒|要塞)([1-9][0-9]?)号?(单撞|撞|集结)", value)
        if not match:
            raise ValueError("请选择全部报名，或填写目标和打法，例如堡垒8 单撞、要塞4 集结")
        kind, number, mode = match.groups()
        if int(number) > TARGET_LIMITS[kind]:
            raise ValueError(f"{kind}编号范围为 1–{TARGET_LIMITS[kind]}")
        targets.append(Target(kind, int(number), "单撞" if mode == "撞" else mode))
    if len(targets) > 1 and any(target.kind == ALL_REGISTERED for target in targets):
        raise ValueError("全部报名适用于整站，请选择一种目标模式")
    if len({(target.kind, target.number) for target in targets}) != len(targets):
        raise ValueError("同一联盟的目标重复")
    return tuple(targets)


def target_text(kind: str, number: int | None, mode: str) -> str:
    if kind == ALL_REGISTERED:
        return kind if mode == UNSPECIFIED_TACTIC else f"{kind} {mode}"
    label = f"{kind}{number}" if number is not None else "唯一堡垒"
    if mode == UNSPECIFIED_TACTIC:
        return label
    return f"{label} {mode}"


def parse_route(rows: list[tuple[str, str]]) -> tuple[Stop, ...]:
    stops = []
    for name, targets in rows:
        tag = compact(name)
        if not re.fullmatch(r"[\w-]{1,16}", tag):
            raise ValueError("请为每站填写游戏卡片方括号里的联盟短标签")
        stops.append(Stop(tag, parse_targets(targets)))
    if not stops or len({stop.alliance for stop in stops}) != len(stops):
        raise ValueError("请填写路线，同一联盟的多个目标写在同一行")
    return tuple(stops)


def parse_stamp(text: str) -> datetime:
    text = unicodedata.normalize("NFKC", text).strip().lstrip("'’")
    text = re.sub(r"\s", "", text)
    match = re.fullmatch(r"([0-9]{4})[-–—一.·]([0-9]{2})[-–—一.·]([0-9]{2})([0-9]{2}):([0-9]{2}):([0-9]{2})", text)
    if not match:
        raise ValueError("发件时间无法完整读出")
    return datetime(*map(int, match.groups()), tzinfo=SHANGHAI)


def parse_cropped_mail_stamp(text: str) -> datetime:
    text = unicodedata.normalize("NFKC", text).strip()
    # The header OCR can separate clock fields with spaces when it misses both colons.
    match = re.fullmatch(
        r"([0-9]{4}\s*[-–—一.·]\s*[0-9]{2}\s*[-–—一.·]\s*[0-9]{2})\s+"
        r"([0-9]{2})\s+([0-9]{2})\s+([0-9]{2})", text)
    if match:
        date, hour, minute, second = match.groups()
        text = f"{date} {hour}:{minute}:{second}"
    return parse_stamp(text)


def format_stamp(value: datetime) -> str:
    return value.astimezone(SHANGHAI).strftime(STAMP_FORMAT)


def new_run(stops: tuple[Stop, ...], round_start: datetime) -> dict:
    return {
        "route": [{"alliance": stop.alliance, "targets": [asdict(target) for target in stop.targets]} for stop in stops],
        "round_start": format_stamp(round_start), "index": 0,
        "occupied": [], "mail": {}, "last_solo": None, "returned": {}, "keys": {}, "applications": {},
    }


def run_from_schedule(previous: dict, job: dict) -> dict:
    stamp = datetime.fromtimestamp(job["run_at"], SHANGHAI)
    take_keys = job["fortress_take_keys"]
    if type(take_keys) is not bool:
        raise ValueError("预约的拿钥匙选项无效")
    try:
        route = parse_route([(station["alliance"], "，".join(target_text(**target) for target in station["targets"]))
                             for station in job["route"]])
    except (KeyError, TypeError) as exc:
        raise ValueError("预约的堡垒路线格式异常") from exc
    run = new_run(route, stamp)
    if run["route"] != job["route"] or previous["round_start"] > run["round_start"]:
        raise ValueError("预约路线无效或当前已保存更晚的路线")
    if previous["round_start"] == run["round_start"]:
        if run["route"] != previous["route"] or take_keys != previous.get("take_keys", True):
            raise ValueError("本轮已保存的路线或拿钥匙选项与预约不同")
        return previous
    run["applications"] = {tag: record for tag, record in previous.get("applications", {}).items()
                           if record["state"] != "joined"}
    run["take_keys"] = take_keys
    if previous.get("key_time_accounts"):
        run["key_time_accounts"] = list(previous["key_time_accounts"])
    return run


def resolved_station(run: dict, station: dict) -> dict:
    detected = run.get("resolved_targets", {}).get(station["alliance"])
    requested = station["targets"]
    if requested[0]["kind"] == ALL_REGISTERED:
        if not isinstance(detected, list) or not detected:
            return station
        targets = [dict(kind=kind, number=number, mode=requested[0]["mode"]) for kind, number in detected]
        return dict(station, targets=targets, all_registered=True)
    if type(detected) is not int or all(target["number"] is not None for target in requested):
        return station
    targets = [dict(target, number=detected) if target["number"] is None else target for target in requested]
    if len({(target["kind"], target["number"]) for target in targets}) != len(targets):
        raise ValueError("自动识别的堡垒与本站指定目标重复")
    return dict(station, targets=targets)


def reference_key_times(run: dict) -> dict[str, str]:
    accounts = run.get("key_time_accounts", [])
    if not accounts:
        return {}
    profiles = _profiles(PROFILE_PATH)
    candidates = []
    for account in accounts:
        history = profiles.get(HISTORY_KEY, {}).get(account, [])
        same_round = next((record for record in (profiles.get(account), *reversed(history))
                           if record and record["round_start"] == run["round_start"] and record["route"] == run["route"]), None)
        if same_round is None:
            return {}
        candidates.append({tag: min(stamp for stamp, status in mails.items() if status == "claimed")
                           for tag, mails in same_round["mail"].items() if "claimed" in mails.values()})
    return {tag: min(record[tag] for record in candidates)
            for tag in candidates[0] if all(tag in record for record in candidates)}


def return_deadline(run: dict, alliance: str, reference: dict[str, str] | None = None) -> datetime | None:
    reference = reference_key_times(run) if reference is None else reference
    if alliance in reference:
        return parse_stamp(reference[alliance]) + timedelta(minutes=30)
    stamps = run["mail"].get(alliance, {})
    return parse_stamp(min(stamps)) + timedelta(minutes=30) if stamps else None


def key_collection_status(run: dict, alliance: str, now: datetime) -> str:
    if alliance in run["keys"]:
        return "已领取"
    receipts = run.get("key_mail", {}).get(alliance, {})
    claimed = sum(receipt["state"] == "claimed" for receipt in receipts.values())
    if claimed:
        return f"部分领取（{claimed} 封）"
    if receipts:
        return "领取待核对"
    if alliance in run.get("key_unavailable", {}):
        return "未检测到钥匙邮件 · 已转下站"
    if not run.get("take_keys", True):
        return "本轮关闭"
    due = return_deadline(run, alliance)
    if due is None:
        return "待登记胜利邮件"
    arrival = run["returned"].get(alliance)
    if arrival:
        if parse_stamp(arrival) >= due:
            return "超时返回 · 无领取记录"
        return "已返回 · 等待结算" if now < due else "已返回 · 领取待核对"
    return "待返回" if now < due else "已过返回截止 · 无领取记录"


def return_queue(run: dict) -> list[tuple[datetime, str]]:
    if not run.get("take_keys", True):
        return []
    reference = reference_key_times(run)
    tags = {tag for tag, mails in run["mail"].items() if mails} | reference.keys()
    tags.difference_update(run["keys"], run.get("key_unavailable", {}))
    return sorted((return_deadline(run, tag, reference), tag) for tag in tags)


def record_mail(run: dict, alliance: str, stamp: datetime, status: str, now: datetime) -> None:
    if not parse_stamp(run["round_start"]) <= stamp <= now:
        raise ValueError("邮件发件时间超出本轮核对范围")
    if status not in {"pending", "claimed"}:
        raise ValueError("未知的领取状态")
    key = format_stamp(stamp)
    for tag, mails in run["mail"].items():
        if tag != alliance and key in mails:
            raise ValueError("同一发件时间已归入另一站，请人工核对")
    mails = run["mail"].setdefault(alliance, {})
    if status == "pending" and key in mails:
        raise ValueError("这封邮件已有领取记录，请检查游戏结果")
    mails[key] = status


def _profiles(path: Path) -> dict:
    if not path.exists():
        return {}
    profiles = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(profiles, dict):
        raise ValueError("堡垒路线存档格式异常")
    return profiles


def load_run(identity: str, path: Path = PROFILE_PATH) -> dict | None:
    return _profiles(path).get(identity)


def has_run_progress(run: dict) -> bool:
    if any(run.get(key) for key in ("scheduled_start", "index", "occupied", "mail", "last_solo",
                                    "returned", "keys", "resolved_targets")):
        return True
    round_start = parse_stamp(run["round_start"]).timestamp()
    return any(entry.get("started_at", 0) >= round_start
               for entry in run.get("applications", {}).values())


def load_history(identity: str, path: Path = PROFILE_PATH) -> list[dict]:
    profiles = _profiles(path)
    entries = list(profiles.get(HISTORY_KEY, {}).get(identity, []))
    active = profiles.get(identity)
    if (active and active["index"] >= len(active["route"]) and not active.get("deferred_victory")
            and active not in entries):
        entries.append(active)
    return sorted(reversed(entries), key=lambda run: run["round_start"], reverse=True)


def _append_history(profiles: dict, identity: str, run: dict) -> bool:
    entries = profiles.setdefault(HISTORY_KEY, {}).setdefault(identity, [])
    if run in entries:
        return False
    entries.append(run)
    return True


@_serialized_account_write
def archive_run(identity: str, run: dict, path: Path = PROFILE_PATH) -> None:
    if not identity.startswith("mumu:") or ":android:" not in identity:
        raise ValueError("请先绑定已核验的 MuMu 账号")
    profiles = _profiles(path)
    if _append_history(profiles, identity, run):
        _atomic_json_write(path, profiles)


@_serialized_account_write
def save_run(identity: str, expected: dict | None, run: dict, path: Path = PROFILE_PATH) -> None:
    if not identity.startswith("mumu:") or ":android:" not in identity:
        raise ValueError("请先绑定已核验的 MuMu 账号")
    profiles = _profiles(path)
    if profiles.get(identity) != expected:
        raise ValueError("另一窗口已更新此账号的路线，请重新加载")
    if expected and expected["round_start"] != run["round_start"] and has_run_progress(expected):
        _append_history(profiles, identity, expected)
    profiles[identity] = run
    _atomic_json_write(path, profiles)


def normalize_frame(frame: Image.Image) -> Image.Image:
    viewport = content_viewport(frame).box
    if viewport != (0, 0, *frame.size):
        frame = frame.crop(viewport)
    if frame.mode != "RGB":
        frame = frame.convert("RGB")
    return frame.resize(REFERENCE, Image.Resampling.LANCZOS)


def _text_in(lines: list[dict], box: tuple[int, int, int, int]) -> list[str]:
    x1, y1, x2, y2 = box
    return [
        compact(line["text"]) for line in lines if line.get("words")
        and x1 <= line["words"][0]["x"] < x2 and y1 <= line["words"][0]["y"] < y2
    ]


def is_game_root(lines: list[dict]) -> bool:
    return sum(text in _text_in(lines, (x1, 1148, x2, 1190)) for text, x1, x2 in (
        ("探险", 25, 90), ("背包", 245, 320), ("商店", 354, 425), ("联盟", 457, 530),
    )) >= 3


def root_entry(image: Image.Image, lines: list[dict], entry: str) -> tuple[int, int] | None:
    if not is_game_root(lines):
        return None
    if entry == "activity":
        pixels = np.asarray(image.crop((608, 135, 637, 156)), dtype=np.int16)
        red, green, blue = pixels.transpose(2, 0, 1)
        green_check = ((green > 105) & (green - red > 37) & (green - blue > 29)).mean()
        white = ((pixels.min(axis=2) > 165) & (np.ptp(pixels, axis=2) < 50)).mean()
        return (621, 144) if 0.20 < green_check < 0.40 and white > 0.55 else None
    if entry == "mail":
        pixels = np.asarray(image.crop((595, 957, 645, 1005)), dtype=np.int16)
        red, green, blue = pixels.transpose(2, 0, 1)
        white = ((pixels.min(axis=2) > 165) & (np.ptp(pixels, axis=2) < 50)).mean()
        blue_frame = ((blue - red > 45) & (green - red > 22)).mean()
        return (620, 981) if 0.37 < white < 0.60 and 0.36 < blue_frame < 0.63 else None
    return None


def is_regular_activity(lines: list[dict]) -> bool:
    return any(text.endswith("常规活动") for text in _text_in(lines, (0, 0, 210, 65)))


def is_alliance_relocation_prompt(lines: list[dict]) -> bool:
    details = "".join(_text_in(lines, (60, 838, 610, 946)))
    return (
        "迁城" in _text_in(lines, (280, 100, 419, 194))
        and "联盟总部" in details
        and ("距离过" in details or "请迁城至联盟总部" in details)
        and "迁城" in _text_in(lines, (265, 986, 410, 1051))
    )


def is_fortress_activity(lines: list[dict]) -> bool:
    return is_regular_activity(lines) and "堡垒争夺" in _text_in(lines, (470, 1120, 645, 1175))


@lru_cache(maxsize=1)
def _fortress_tab_image() -> np.ndarray:
    with Image.open(resource_path("assets/fortress_activity_tab.png")) as tile:
        return np.asarray(tile.convert("RGBA"))


def fortress_tab_point(image: Image.Image, lines: list[dict]) -> tuple[int, int] | None:
    if not is_regular_activity(lines):
        return None
    for line in lines:
        if not line.get("words") or compact(line["text"]) != "堡垒争夺":
            continue
        first, last = line["words"][0], line["words"][-1]
        if 138 <= first["y"] <= 165 and 25 < first["x"] < 565:
            return round((first["x"] + last["x"] + last["width"]) / 2), 133
    left, top = 8, 93
    strip = np.asarray(image.crop((left, top, 657, 174)))
    # Unselected tabs put their name over the lower part of the icon.
    template = _fortress_tab_image()[:45]
    scores = cv2.matchTemplate(
        strip, np.ascontiguousarray(template[:, :, :3]), cv2.TM_SQDIFF_NORMED,
        mask=np.ascontiguousarray(template[:, :, 3]),
    )
    scores[~np.isfinite(scores)] = 1
    score, _, (x, y), _ = cv2.minMaxLoc(scores)
    if score > 0.115:
        return None
    scores[:, max(0, x - template.shape[1] // 2):x + template.shape[1] // 2] = 1
    if float(scores.min()) - score < 0.06:
        return None
    return left + x + template.shape[1] // 2, top + y + 33


def is_mail_list(lines: list[dict]) -> bool:
    title = any(text.endswith("邮件") for text in _text_in(lines, (0, 0, 120, 66)))
    tabs = set(_text_in(lines, (38, 75, 620, 140)))
    return title and len(tabs & {"战争", "联盟", "系统", "报告", "收藏"}) >= 3


def alliance_mail_selected(image: Image.Image, lines: list[dict]) -> bool:
    if not is_mail_list(lines):
        return False
    tab = np.asarray(image.crop((154, 115, 177, 137)), dtype=np.int16)
    return bool((tab.min(axis=2) >= 183).mean() > 0.70)


def mail_row_stamp(image, lines, y: int, ocr=None) -> datetime | None:
    fields = _text_in(lines, (142, y + 48, 281, y + 81))
    if len(fields) == 1:
        try:
            return parse_stamp(fields[0])
        except ValueError:
            pass
    if image is not None and ocr is not None:
        crop = image.crop((151, y + 59, 414, y + 87)).resize((789, 84), Image.Resampling.LANCZOS)
        fields = ocr(crop)
        if len(fields) == 1:
            try:
                return parse_cropped_mail_stamp(fields[0]["text"])
            except ValueError:
                pass
    return None


def visible_reward_stamps(lines: list[dict], since: datetime, now: datetime, *, image=None, ocr=None) -> list[datetime]:
    dates = set()
    for line in lines:
        if not line.get("words") or compact(line["text"]) not in FORTRESS_MAIL:
            continue
        word = line["words"][0]
        y = word["y"]
        if not 140 < word["x"] < 215 or not 156 < y < 1070:
            continue
        stamp = mail_row_stamp(image, lines, round(y), ocr)
        if stamp is not None and since <= stamp <= now:
            dates.add(stamp)
    return sorted(dates)


@dataclass(frozen=True)
class RewardMail:
    stamp: datetime
    title: str
    claimed: bool


def _mail_detail_stamp(image, lines, ocr):
    header = _text_in(lines, (360, 105, 640, 157))
    sent = None
    if len(header) == 1:
        try:
            sent = parse_stamp(header[0])
        except ValueError:
            pass
    if ocr is not None:
        stamp_crop = image.crop((386, 113, 639, 151)).resize((759, 114), Image.Resampling.LANCZOS)
        cropped_lines = ocr(stamp_crop)
        if len(cropped_lines) == 1:
            try:
                cropped = parse_cropped_mail_stamp(cropped_lines[0]["text"])
            except ValueError:
                pass
            else:
                if sent is not None and sent != cropped:
                    return None
                sent = cropped
    return sent


def read_mail(image: Image.Image, lines: list[dict], ocr=None) -> RewardMail | None:
    if not any(text.endswith("邮件") for text in _text_in(lines, (0, 0, 120, 66))):
        return None
    titles = set(_text_in(lines, (200, 248, 454, 301))) & FORTRESS_MAIL
    buttons = _text_in(lines, (260, 730, 430, 792))
    if len(titles) != 1:
        return None
    sent = _mail_detail_stamp(image, lines, ocr)
    if sent is None:
        return None
    pixels = np.asarray(image.crop((232, 739, 438, 783)).convert("RGB"), dtype=np.int16)
    red, green, blue = pixels.transpose(2, 0, 1)
    claim_green = ((green > 130) & (green - red > 55) & (green - blue > 48)).mean()
    disabled_gray = ((abs(red - green) < 32) & (abs(blue - green) < 32) & (green < 155)).mean()
    if buttons == ["领取"] and claim_green > 0.62:
        return RewardMail(sent, titles.pop(), False)
    if buttons == ["已领取"] and disabled_gray > 0.62:
        return RewardMail(sent, titles.pop(), True)
    return None


@dataclass(frozen=True)
class ControlReward:
    target: str
    stamp: datetime
    claimed: bool
    point: tuple[int, int]


def _control_mail_target(text: str) -> str | None:
    matches = re.findall(r"(?<![0-9])([1-9][0-9]?)号(堡垒|要塞)", text)
    return f"{matches[0][1]}{matches[0][0]}" if len(matches) == 1 else None


def read_control_reward(image, lines, ocr=None) -> ControlReward | None:
    if not any(text.endswith("邮件") for text in _text_in(lines, (0, 0, 120, 66))):
        return None
    if _text_in(lines, (200, 248, 454, 301)) != [CONTROL_MAIL]:
        return None
    target = _control_mail_target("".join(_text_in(lines, (32, 310, 641, 389))))
    if target is None:
        return None
    stamp = _mail_detail_stamp(image, lines, ocr)
    if stamp is None:
        return None
    actions = []
    for line in lines:
        word = (line.get("words") or [None])[0]
        text = compact(line["text"])
        if word and 258 <= word["x"] <= 410 and 520 <= word["y"] <= 785 and text in {"领取", "已领取"}:
            actions.append((text, round(word["y"])))
    if len(actions) != 1:
        return None
    button, y = actions[0]
    r, g, b = np.asarray(image.crop((223, y - 9, 439, y + 34)), dtype=np.int16).transpose(2, 0, 1)
    if button == "领取" and ((g > 130) & (g - r > 55) & (g - b > 48)).mean() > .62:
        return ControlReward(target, stamp, False, (336, y + 14))
    if button == "已领取" and ((abs(r - g) < 32) & (abs(b - g) < 32) & (g < 155)).mean() > .62:
        return ControlReward(target, stamp, True, (336, y + 14))
    return None


@lru_cache(maxsize=1)
def _target_art() -> dict[str, np.ndarray]:
    with Image.open(resource_path("assets/fortress_target_art.png")) as image:
        return {
            "堡垒": np.asarray(image.crop((0, 0, 112, 97)).convert("RGB")),
            "要塞": np.asarray(image.crop((0, 97, 112, 194)).convert("RGB")),
        }


def _target_kind(image: Image.Image, left: int) -> str | None:
    card = np.asarray(image.crop((left + 34, 868, left + 146, 965)))
    scores = sorted((
        (float(cv2.matchTemplate(card, artwork, cv2.TM_CCOEFF_NORMED)[0, 0]), kind)
        for kind, artwork in _target_art().items()
    ), reverse=True)
    score, kind = scores[0]
    return kind if score > 0.90 and score - scores[1][0] > 0.13 else None


def _target_number(white, ocr) -> int | None:
    digit = Image.fromarray(np.where(white, 0, 255).astype(np.uint8))
    zoom = digit.resize((digit.width * 5, digit.height * 5))
    read = compact("".join(line["text"] for line in ocr(ImageOps.expand(zoom, border=20, fill=255), "en-US")))
    if re.fullmatch(r"[1-9][0-9]?", read):
        return int(read)
    # WinRT skips isolated digits on several live cards. Three identical tiles
    # allow a number only when all three readings agree.
    zoom = digit.resize((digit.width * 3, digit.height * 3), Image.Resampling.LANCZOS)
    repeated = Image.new("L", (zoom.width * 3 + 20, zoom.height + 20), 255)
    for index in range(3):
        repeated.paste(zoom, (10 + index * zoom.width, 10))
    read = compact("".join(line["text"] for line in ocr(repeated, "en-US")))
    matched = re.fullmatch(r"([1-9][0-9]?)\1\1", read)
    if matched:
        return int(matched[1])
    ys, xs = np.where(white)
    if not ys.size:
        return None
    glyph = white[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
    height, width = glyph.shape
    # The outlined in-game 1 has a short cap and a straight, right-aligned stem.
    if (13 <= height <= 16 and 5 <= width <= 7
            and glyph[:3, :width - 3].any()
            and not glyph[3:, :width - 4].any()
            and glyph[3:, -3:].all()):
        return 1
    read = _read_repeated_glyphs(glyph, ocr)
    matched = re.fullmatch(r"([1-9][0-9]?)\1\1", read)
    return int(matched[1]) if matched else None


def _read_repeated_glyphs(glyph, ocr) -> str:
    ys, xs = np.where(glyph)
    if not ys.size:
        return ""
    tight = glyph[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
    cropped = Image.fromarray(np.where(tight, 0, 255).astype(np.uint8))
    zoom = cropped.resize((cropped.width * 3, cropped.height * 3), Image.Resampling.LANCZOS)
    repeated = Image.new("L", (zoom.width * 3 + 50, zoom.height + 40), 255)
    for index in range(3):
        repeated.paste(zoom, (20 + index * (zoom.width + 5), 20))
    return compact("".join(line["text"] for line in ocr(repeated, "en-US")))


def _card_number_mask(image, left):
    number = np.asarray(image.crop((left + 8, 839, left + 34, 863)), dtype=np.int16)
    return (number.min(axis=2) > 170) & (np.ptp(number, axis=2) < 39)


def read_unique_fortress(image, lines, ocr) -> int | None:
    """Resolve a number only when the visible cards establish a single fortress."""
    if not is_fortress_activity(lines):
        return None
    forts = []
    for left in TARGET_CARD_LEFTS:
        white = _card_number_mask(image, left)
        kind = _target_kind(image, left)
        if kind is None:
            if white.sum() >= 10:
                return None
            continue
        if kind == "堡垒":
            forts.append(white)
    return _target_number(forts[0], ocr) if len(forts) == 1 and forts[0].sum() >= 10 else None


def read_registered_targets(image, lines, ocr) -> tuple[tuple[str, int], ...] | None:
    if not is_fortress_activity(lines):
        return None
    box = (277, 782, 397, 814)
    labels = _text_in(lines, box)
    count = _registered_count(labels)
    if count is None:
        crop = np.asarray(image.crop(box), dtype=np.int16)
        for threshold in (130, 125, 120):
            mask = (crop.min(axis=2) > threshold) & (np.ptp(crop, axis=2) < 44)
            glyphs = Image.fromarray(np.where(mask, 0, 255).astype(np.uint8))
            enlarged = glyphs.resize((glyphs.width * 4, glyphs.height * 4))
            labels = [line["text"] for line in ocr(ImageOps.expand(enlarged, border=20, fill=255))]
            count = _registered_count(labels)
            if count is not None:
                break
    if count is None or not 1 <= count <= len(TARGET_CARD_LEFTS):
        return None
    targets = []
    for index, left in enumerate(TARGET_CARD_LEFTS):
        kind = _target_kind(image, left)
        white = _card_number_mask(image, left)
        if index >= count:
            if kind is not None or white.sum() >= 10:
                return None
            continue
        if kind is None or white.sum() < 10:
            return None
        number = _target_number(white, ocr)
        if number is None or not 1 <= number <= TARGET_LIMITS[kind] or (kind, number) in targets:
            return None
        targets.append((kind, number))
    return tuple(targets)


def _registered_count(labels: list[str]) -> int | None:
    for text in labels:
        match = re.fullmatch(r"已[报報]名([0-9]+)[/／]([0-9]+)", compact(text))
        if match:
            count, capacity = map(int, match.groups())
            if count <= capacity:
                return count
    return None


def read_occupation(image: Image.Image, lines: list[dict], ocr) -> set[tuple[str, int]] | None:
    """Identify target cards that show the current alliance's blue occupation color."""
    if not is_fortress_activity(lines):
        return None
    occupied = set()
    for left in TARGET_CARD_LEFTS:
        white = _card_number_mask(image, left)
        if white.sum() < 10:
            continue
        label = image.crop((left + 16, 979, left + 168, 1037))
        red, green, blue = np.asarray(label, dtype=np.int16).transpose(2, 0, 1)
        blue_text = (blue > 145) & (green - red > 46) & (blue - green > 34)
        if (blue_text.sum() < 45 or np.count_nonzero(blue_text.sum(axis=0) >= 2) < 6
                or np.count_nonzero(blue_text.sum(axis=1) >= 3) < 4):
            continue
        kind = _target_kind(image, left)
        if not kind:
            continue
        number_value = _target_number(white, ocr)
        if number_value is not None:
            key = (kind, number_value)
            if key in occupied:
                return None
            occupied.add(key)
    return occupied


def read_alliance(lines: list[dict]) -> str | None:
    if "联盟" not in _text_in(lines, (70, 0, 170, 60)):
        return None
    tags = _text_in(lines, (230, 84, 420, 139))
    labels = _text_in(lines, (245, 145, 378, 280))
    if len(tags) != 1 or sum(any(label.endswith(field) for label in labels)
                             for field in ("盟主:", "实力:", "排名:", "成员:")) < 3:
        return None
    match = re.match(r"\[([\w-]{1,16})\]", tags[0])
    return match.group(1) if match else None


def alliance_exit_point(lines: list[dict]) -> tuple[int, int] | None:
    if "管理" not in _text_in(lines, (70, 0, 170, 60)):
        return None
    original_list = "联盟列表" in _text_in(lines, (435, 130, 590, 187))
    relocated_list = any(text.endswith("盟列表") for text in _text_in(lines, (130, 252, 285, 550)))
    if not (original_list or relocated_list):
        return None
    locations = (
        ((435, 370, 590, 430), (510, 402)),
        ((130, 488, 290, 545), (179, 520)),
        ((130, 725, 290, 781), (179, 757)),
    )
    visible = [point for box, point in locations if "退出联盟" in _text_in(lines, box)]
    return visible[0] if len(visible) == 1 else None


def is_alliance_settings(lines: list[dict]) -> bool:
    return alliance_exit_point(lines) is not None


def can_confirm_alliance_exit(lines: list[dict]) -> bool:
    return (
        "退出联盟" in _text_in(lines, (250, 386, 450, 471))
        and any("失去联盟所有科技加成" in text for text in _text_in(lines, (137, 483, 595, 563)))
        and "取消" in _text_in(lines, (145, 688, 275, 756))
        and "确定" in _text_in(lines, (410, 688, 565, 756))
    )


def can_confirm_inactive_alliance_join(lines: list[dict]) -> bool:
    body = _text_in(lines, (138, 500, 599, 631))
    return (
        "温馨提示" in _text_in(lines, (250, 386, 450, 471))
        and any("该联盟盟主处于非活跃状态" in line for line in body)
        and any(line.startswith("是否继续加入该联盟") for line in body)
        and "取消" in _text_in(lines, (145, 688, 275, 756))
        and "确定" in _text_in(lines, (410, 688, 565, 756))
    )


def is_inactive_alliance_leave_warning(lines: list[dict]) -> bool:
    return (
        "温馨提示" in _text_in(lines, (250, 380, 450, 451))
        and any(line.startswith("当前联盟的盟主暂时处于非活跃") for line in _text_in(lines, (138, 493, 599, 555)))
        and "该联盟不再提示" in _text_in(lines, (255, 646, 488, 698))
        and "取消" in _text_in(lines, (145, 709, 275, 769))
        and "退出联盟" in _text_in(lines, (395, 709, 565, 769))
    )


def is_join_recommendation(lines: list[dict]) -> bool:
    return (
        "温馨提示" in _text_in(lines, (253, 167, 421, 218))
        and any("盟主最近不太活跃" in text for text in _text_in(lines, (45, 249, 628, 326)))
        and any("将加入以上推荐联盟" in text for text in _text_in(lines, (130, 854, 565, 924)))
        and "加入" in _text_in(lines, (280, 934, 400, 985))
    )


def is_unaffiliated_alliance_page(lines: list[dict]) -> bool:
    return (
        "联盟" in _text_in(lines, (65, 2, 187, 65))
        and "建立联盟" in _text_in(lines, (51, 85, 211, 150))
        and "邀请/申请" in _text_in(lines, (471, 85, 648, 150))
    )


def is_unaffiliated_in_frame(image, lines, ocr) -> bool:
    if is_unaffiliated_alliance_page(lines):
        return True
    if ("联盟" not in _text_in(lines, (65, 2, 187, 65))
            or "建立联盟" not in _text_in(lines, (51, 85, 211, 150))
            or "加入联盟" not in _text_in(lines, (260, 85, 411, 150))):
        return False
    entry = image.crop((465, 88, 653, 150)).resize((376, 124), Image.Resampling.LANCZOS)
    return [compact(item["text"]) for item in ocr(entry)] == ["邀请/申请"]


def search_tag_in_frame(image, lines, ocr) -> str | None:
    query = alliance_search_field(lines)
    if query is not None:
        return query
    if not is_unaffiliated_in_frame(image, lines, ocr):
        return None
    field = image.crop((36, 171, 300, 232)).resize((1056, 244), Image.Resampling.LANCZOS)
    values = [compact(item["text"]).upper() for item in ocr(field, "en-US")]
    return values[0] if len(values) == 1 else None


def alliance_search_field(lines: list[dict]) -> str | None:
    if is_unaffiliated_alliance_page(lines):
        field = _text_in(lines, (40, 178, 475, 235))
    elif any(text.endswith("联盟列表") for text in _text_in(lines, (0, 0, 245, 65))):
        field = _text_in(lines, (40, 108, 475, 155))
    else:
        return None
    return field[0].upper() if len(field) == 1 else None


@dataclass(frozen=True)
class AllianceListing:
    members: int
    capacity: int
    access: str


def read_alliance_listing(lines: list[dict], tag: str) -> AllianceListing | None:
    row = _alliance_listing_row(lines, tag)
    return row[1] if row else None


def _alliance_listing_row(lines: list[dict], tag: str, *, verified_field=None,
                          unaffiliated=None) -> tuple[int, AllianceListing] | None:
    if (verified_field or alliance_search_field(lines)) != tag.upper():
        return None
    for line in lines:
        if not line.get("words"):
            continue
        # The closing bracket sometimes blends into the first Chinese glyph.
        label = re.match(r"^\[([A-Za-z0-9-]{1,16})(?:\]|(?=[\u3400-\u9fff]))", compact(line["text"]))
        if not label or label.group(1) != tag:
            continue
        word = line["words"][0]
        y = word["y"]
        if not 175 <= word["x"] <= 310 or not 185 <= y <= 1000:
            continue
        capacity = _text_in(lines, (179, y + 47, 369, y + 92))
        no_alliance = is_unaffiliated_alliance_page(lines) if unaffiliated is None else unaffiliated
        access = set(_text_in(lines, (455, y + 49, 660, y + 101))) & {
            "需要申请", "可直接加入", "白名单联盟",
        }
        if no_alliance:
            labels = _text_in(lines, (492, y + 45, 626, y + 101))
            controls = {mode for button, mode in (("加入", "可直接加入"), ("申请", "需要申请"))
                        if button in labels}
            if controls:
                access = controls
        if len(capacity) != 1 or len(access) != 1:
            return None
        match = re.search(r"([0-9]{1,3})/([0-9]{1,3})$", capacity[0])
        if match:
            current, limit = map(int, match.groups())
            if 0 <= current <= limit and limit > 0:
                return round(y), AllianceListing(current, limit, access.pop())
    return None


def _listing_in_frame(image, lines, ocr, tag):
    query = search_tag_in_frame(image, lines, ocr)
    if query != tag.upper():
        return None
    detached = is_unaffiliated_in_frame(image, lines, ocr)
    row = _alliance_listing_row(lines, tag, verified_field=query, unaffiliated=detached)
    if row or not detached or len(tag) != 3:
        return row
    matches = []
    for line in lines:
        if not line.get("words"):
            continue
        x, y = (round(line["words"][0][key]) for key in ("x", "y"))
        label = compact(line["text"])
        if not label.startswith("["):
            tail = re.match(r"^([A-Za-z0-9-]{1,2})\]", label)
            if not tail or not tag.endswith(tail[1]) or not 195 <= x < 230:
                continue
            x = 190  # OCR dropped the opening bracket and the first glyph of the row label.
        if not (175 <= x <= 310 and 255 <= y <= 1000):
            continue
        if _cropped_listing_tag(image, x, y, ocr) != tag:
            continue
        count = image.crop((209, y + 59, 343, y + 93)).resize((402, 102), Image.Resampling.LANCZOS)
        counts = [compact(item["text"]) for item in ocr(count, "en-US")]
        listing = _reviewed_listing_row(lines, y, counts)
        if listing:
            matches.append(listing)
    if matches:
        return matches[0] if len(matches) == 1 else None
    label = image.crop((191, 285, 244, 308)).resize((159, 69), Image.Resampling.LANCZOS)
    if [compact(item["text"]) for item in ocr(label, "en-US")] != [f"[{tag}]"]:
        return None
    return _reviewed_listing_row(lines, 284, _text_in(lines, (179, 345, 369, 376)))


def _reviewed_listing_row(lines, y, counts):
    actions = set(_text_in(lines, (505, y + 42, 601, y + 85))) & {"加入", "申请"}
    if len(counts) != 1 or len(actions) != 1:
        return None
    match = re.fullmatch(r"([0-9]{1,3})/([0-9]{1,3})", counts[0])
    if not match:
        return None
    current, limit = map(int, match.groups())
    if not 0 <= current <= limit or not limit:
        return None
    return y, AllianceListing(current, limit, "可直接加入" if "加入" in actions else "需要申请")


def _cropped_listing_tag(image, x, y, ocr) -> str | None:
    """Separate the three-letter tag from its name by its two visible brackets."""
    pixels = np.asarray(image.crop((x - 6, y - 4, x + 83, y + 26)), dtype=np.int16)
    dark = (pixels.min(axis=2) < 85) & (pixels.max(axis=2) < 148)
    _, _, components, _ = cv2.connectedComponentsWithStats(dark.astype(np.uint8))
    opening = [(left, top, width, height) for left, top, width, height, _ in components[1:]
               if 2 <= left <= 9 and 2 <= width <= 8 and 15 <= height <= 26]
    if len(opening) != 1:
        return None
    left, top, width, height = opening[0]
    bottom = top + height
    closing = [
        col for col in range(left + width + 24, min(left + width + 62, dark.shape[1]))
        if dark[top + 2:bottom - 2, col].mean() > .68
        and dark[top:top + 3, col - 3:col].mean() > .37
        and dark[bottom - 3:bottom, col - 3:col].mean() > .37
        and dark[top + 4:bottom - 4, col - 3].mean() < .25
    ]
    if not closing or closing[-1] - closing[0] > 3:
        return None
    # First keep descenders, then try a tighter crop if a bracket cap leaked in.
    for last_row, last_column in ((bottom + 2, closing[-1] - 2), (bottom - 2, closing[-1] - 3)):
        glyph = dark[top + 2:last_row, left + width:last_column]
        read = _read_repeated_glyphs(glyph, ocr)
        match = re.fullmatch(r"([A-Za-z0-9-]{3})\1\1", read)
        if match:
            return match[1]
    return None


def _paste_alliance_tag(target, tag, stop_event, *, replace=False):
    if target.shell(["getprop", "ro.build.version.sdk"], timeout=3).strip() != "35":
        raise ValueError("请在当前模拟器中粘贴目标联盟短标签")
    focus_until = time.monotonic() + 2
    while time.monotonic() < focus_until:
        if stop_event.is_set() or not target.foreground_is_game():
            raise InterruptedError()
        ime = target.shell(["dumpsys", "input_method"], timeout=2)
        if "mInputShown=true" in ime and "mServedView=com.unity3d.player." in ime:
            break
        stop_event.wait(.08)
    else:
        raise ValueError("搜索框输入状态未确认")

    def integers(*values):
        return [str(item) for value in values for item in ("i32", value)]

    text = tag.encode("utf-8")
    padded = text + b"\x00" * (4 - len(text) % 4)
    parcel = integers(len(text), *(int.from_bytes(padded[i:i + 4], "little", signed=True)
                                  for i in range(0, len(padded), 4)))
    response = target.shell(
        ["service", "call", "clipboard", "1", *integers(1, 1, -1, 1), "s16", "text/plain",
         *integers(-1, 0, 0, 0, 0, 0, 0, 1, 1), *parcel, *integers(-1, 0, 0, 0, 0, 0),
         "s16", "com.android.shell", *integers(-1, 0, 0)], timeout=4)
    if not re.search(r"Parcel\(\s*00000000\b", response) or "Exception" in response:
        raise ValueError("安卓剪贴板写入未确认")
    if stop_event.is_set() or not target.foreground_is_game():
        raise InterruptedError()
    if replace:
        target.shell(["input", "keycombination", "113", "29"], timeout=3)
    target.shell(["input", "keyevent", "279"], timeout=3)
    target.shell(["input", "keyevent", "66"], timeout=3)


def precheck_alliance(target, ocr, stop_event, tag: str) -> AllianceListing:
    _, first_image, first = _alliance_frame(target, ocr, stop_event)
    frame, second_image, second = _alliance_frame(target, ocr, stop_event)
    field = search_tag_in_frame(first_image, first, ocr)
    if field is None or search_tag_in_frame(second_image, second, ocr) != field:
        raise ValueError("请打开联盟 → 设置 → 联盟列表")
    field_y = 204 if is_unaffiliated_in_frame(second_image, second, ocr) else 133
    previous = _listing_in_frame(first_image, first, ocr, tag)
    observed = _listing_in_frame(second_image, second, ocr, tag)
    if observed is not None and observed == previous:
        return observed[1]
    if field != tag.upper():
        if not re.fullmatch(r"[A-Za-z0-9-]{1,16}", tag):
            raise ValueError("请在游戏搜索框手动输入该联盟的短标签")
        if field != "点击输入" and not re.fullmatch(r"[A-Z0-9-]{1,16}", field):
            raise ValueError("当前搜索框内容未确认")
        if stop_event.is_set() or not target.foreground_is_game():
            raise InterruptedError()
        tap_game_point(target, frame, (225, field_y))
        _paste_alliance_tag(target, tag, stop_event, replace=field != "点击输入")
        frame, _ = _wait_alliance_page(
            target, ocr, stop_event, lambda im, ln: search_tag_in_frame(im, ln, ocr) == tag.upper(),
            "搜索框中的联盟标签未确认")
    if stop_event.is_set() or not target.foreground_is_game():
        raise InterruptedError()
    tap_game_point(target, frame, (598, field_y))
    _, (_, listing) = _wait_alliance_page(
        target, ocr, stop_event, lambda im, ln: _listing_in_frame(im, ln, ocr, tag),
        f"未确认 [{tag}] 的搜索结果，请在游戏中核对短标签和人数")
    return listing


@dataclass(frozen=True)
class AllianceApplication:
    tag: str
    status: str


def read_alliance_application(image: Image.Image, lines: list[dict], ocr) -> AllianceApplication | None:
    if "联盟资讯" not in _text_in(lines, (240, 146, 433, 209)):
        return None
    headers = _text_in(lines, (211, 220, 460, 272))
    match = next((re.match(r"^\[([\w-]{1,16})\]", text) for text in headers if text.startswith("[")), None)
    if not match:
        header = image.crop((211, 219, 384, 269)).resize((519, 150))
        for line in ocr(header):
            match = re.match(r"^\[([\w-]{1,16})\]", compact(line["text"]))
            if match:
                break
    tag = match[1] if match else None
    if not tag:
        red, green, blue = np.asarray(image.crop((225, 231, 296, 270)), dtype=np.int16).transpose(2, 0, 1)
        ink = (red < 132) & (green < 158) & (blue < 180)
        if (ink[13:30, 7:9].mean() > .85 and ink[10:13, 9:11].mean() > .55
                and ink[13:30, 65:68].mean() > .85 and ink[10:13, 63:65].mean() > .50):
            tag = _read_repeated_glyphs(ink[:, 11:63], ocr)
            repeated = re.fullmatch(r"([A-Za-z0-9-]{3})\1\1", tag)
            tag = repeated[1] if repeated else None
    if not tag:
        return None
    actions = set(_text_in(lines, (235, 903, 455, 967)))
    pending = {"已申请", "申请中", "审核中", "等待审核", "已提交申请"}
    apply = {"申请", "申请加入", "申请入盟"}
    if not actions & (pending | apply):
        pixels = np.asarray(image.crop((265, 913, 409, 969)), dtype=np.int16)
        white = (pixels.min(axis=2) > 177) & (np.ptp(pixels, axis=2) < 54)
        label = Image.fromarray(np.where(white, 0, 255).astype(np.uint8)).resize((576, 224), Image.Resampling.LANCZOS)
        actions = {compact(line["text"]) for line in ocr(ImageOps.expand(label, border=18, fill=255))}
    if actions & pending:
        return AllianceApplication(tag, "pending")
    if not actions & apply:
        return None
    pixels = np.asarray(image.crop((222, 912, 450, 958)), dtype=np.int16)
    red, green, blue = pixels.transpose(2, 0, 1)
    enabled = ((green > 105) & (green - red > 52) & ((green - blue > 28) | (blue - red > 48))).mean()
    return AllianceApplication(tag, "ready" if enabled > 0.60 else "gray")


def _alliance_frame(target, ocr, stop_event):
    if stop_event.is_set():
        raise InterruptedError()
    frame = target.screenshot(timeout=6)
    image = normalize_frame(frame)
    return frame, image, ocr(image)


class PageNotVerified(ValueError):
    pass


def _wait_alliance_page(target, ocr, stop_event, identify, error, *, timeout=3.0):
    previous = None
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        frame, image, lines = _alliance_frame(target, ocr, stop_event)
        match = identify(image, lines)
        if match and match == previous:
            return frame, match
        previous = match
        stop_event.wait(min(0.08, max(0, deadline - time.monotonic())))
        if stop_event.is_set():
            raise InterruptedError()
    raise PageNotVerified(error)


def dismiss_inactive_alliance_warning(target, ocr, stop_event) -> None:
    box = (230, 660, 263, 691)

    def checkbox(image):
        return np.asarray(image.crop(box), dtype=np.int16)

    def state(image, lines):
        if not is_inactive_alliance_leave_warning(lines):
            return None
        pixels = checkbox(image)
        red, green, blue = pixels.transpose(2, 0, 1)
        tick = (pixels.min(axis=2) >= 217) | ((green > 130) & (green - red > 45) & (green - blue > 30))
        if tick.mean() >= 0.075:
            return "checked"
        empty = (np.abs(pixels - (148, 178, 196)).max(axis=2) <= 16).mean()
        return "empty" if empty >= 0.85 else None

    def tap(frame, point):
        if stop_event.is_set() or not target.foreground_is_game():
            raise InterruptedError()
        tap_game_point(target, frame, point)

    frame, selected = _wait_alliance_page(
        target, ocr, stop_event, state, "该联盟不再提示的复选框状态未确认")
    if selected == "empty":
        before = checkbox(normalize_frame(frame))
        tap(frame, (246, 676))

        def changed(image, lines):
            if not is_inactive_alliance_leave_warning(lines):
                return None
            pixels = checkbox(image)
            return "checked" if (np.abs(pixels - before).max(axis=2) > 26).mean() >= 0.075 else None

        frame, _ = _wait_alliance_page(
            target, ocr, stop_event, changed, "未确认「该联盟不再提示」已勾选")
    tap(frame, (204, 745))


def prepare_alliance_route(target, ocr, stop_event, tag: str, *, leave_current: bool) -> bool:
    """Open the verified unaffiliated page, or confirm the account is already in this station."""
    def state(image, lines):
        if is_unaffiliated_in_frame(image, lines, ocr):
            return ("available", None)
        application = read_alliance_application(image, lines, ocr)
        if application and application.tag == tag:
            return ("available", None)
        current = read_joined_in_frame(image, lines, ocr)
        if current:
            return ("member", current)
        if is_alliance_settings(lines):
            return ("management", None)
        if is_game_root(lines):
            return ("root", None)
        return None

    def wait_for(predicate, error):
        return _wait_alliance_page(target, ocr, stop_event, lambda _i, lines: predicate(lines), error)[0]

    def tap(frame, point):
        if stop_event.is_set() or not target.foreground_is_game():
            raise InterruptedError()
        tap_game_point(target, frame, point)

    frame, (mode, current) = _wait_alliance_page(
        target, ocr, stop_event, state, "请从野外、主城、联盟主页或管理页开始本站流程")
    if mode == "root":
        tap(frame, (498, 1138))
        frame, (mode, current) = _wait_alliance_page(
            target, ocr, stop_event, lambda image, lines: state(image, lines) if not is_game_root(lines) else None,
            "联盟入口未确认")
    def read_member_from_management(frame):
        tap(frame, (37, 36))
        return _wait_alliance_page(
            target, ocr, stop_event, lambda image, lines: read_joined_in_frame(image, lines, ocr),
            "从联盟管理返回后，未确认当前联盟")

    if mode == "management":
        frame, current = read_member_from_management(frame)
        mode = "member"
    if mode == "available":
        return False
    if current == tag:
        return True
    if not leave_current:
        raise ValueError(f"当前仍在 [{current}]。请退出当前联盟，或使用「退盟并去本站」")

    def management_exit(_image, lines):
        return alliance_exit_point(lines)

    def after_exit(image, lines):
        visible = state(image, lines)
        return visible if visible and visible[0] in {"available", "root"} else None

    def locate_management(image, lines):
        point = alliance_exit_point(lines)
        if point:
            return "management", point
        if (read_joined_in_frame(image, lines, ocr) == current
                and "设置" in _text_in(lines, (430, 1138, 544, 1192))):
            return "overview", None
        return None

    def exit_outcome(image, lines):
        return after_exit(image, lines) or (("confirmation", None) if can_confirm_alliance_exit(lines) else None)

    for attempt in range(2):
        tap(frame, (488, 1126))
        try:
            frame, exit_point = _wait_alliance_page(
                target, ocr, stop_event, management_exit, "联盟管理页面的退出按钮未确认", timeout=2.5)
        except PageNotVerified:
            frame, (page, exit_point) = _wait_alliance_page(
                target, ocr, stop_event, locate_management, "退盟入口无法确认，保持当前联盟")
            if page == "overview":
                tap(frame, (488, 1126))
                frame, exit_point = _wait_alliance_page(
                    target, ocr, stop_event, management_exit, "联盟管理页面的退出按钮未确认")
        tap(frame, exit_point)
        frame = wait_for(can_confirm_alliance_exit, "退盟确认页或确认按钮未就绪")
        tap_verified_transition(target, stop_event, frame, (473, 727))
        try:
            frame, (mode, _) = _wait_alliance_page(target, ocr, stop_event, after_exit, "退盟结果未确认", timeout=5)
            break
        except PageNotVerified:
            if attempt:
                raise
            frame, (mode, _) = _wait_alliance_page(target, ocr, stop_event, exit_outcome, "退盟结果未确认")
            if mode != "confirmation":
                break
            tap(frame, (200, 726))
            frame, _ = _wait_alliance_page(
                target, ocr, stop_event, management_exit, "取消退盟后未确认管理页面")
            frame, still_member = read_member_from_management(frame)
            if still_member != current:
                raise PageNotVerified("取消退盟后，当前联盟与退盟前不一致")
    if mode == "available":
        return False
    tap(frame, (498, 1138))
    _wait_alliance_page(target, ocr, stop_event, lambda im, ln: is_unaffiliated_in_frame(im, ln, ocr),
                        "未确认退出原联盟，请核对游戏")
    return False


def join_available_alliance(target, ocr, stop_event, tag: str, remember) -> None:
    def available(image, lines):
        if not is_unaffiliated_in_frame(image, lines, ocr):
            return None
        row = _listing_in_frame(image, lines, ocr, tag)
        if not row:
            return None
        top, listing = row
        if listing.access != "可直接加入" or listing.members >= listing.capacity:
            return None
        pixels = np.asarray(image.crop((480, top + 53, 615, top + 87)), dtype=np.int16)
        red, green, blue = pixels.transpose(2, 0, 1)
        if ((green > 105) & (green - red > 50) & (green - blue > 35)).mean() > 0.55:
            return top
        return None

    frame, top = _wait_alliance_page(target, ocr, stop_event, available, "本站绿色加入按钮未确认")
    if stop_event.is_set() or not target.foreground_is_game():
        raise InterruptedError()
    remember()
    if stop_event.is_set() or not target.foreground_is_game():
        raise InterruptedError()
    tap_game_point(target, frame, (549, top + 69))
    confirm_direct_join(target, ocr, stop_event, tag)


def rapid_join_anchor(target, ocr, stop_event, tag: str):
    """Confirm the exact search result and green button before arming the clicker."""
    def identify(image, lines):
        if not is_unaffiliated_in_frame(image, lines, ocr) or search_tag_in_frame(image, lines, ocr) != tag.upper():
            return None
        row = _listing_in_frame(image, lines, ocr, tag)
        if row:
            top, entry = row
            if entry.access != "可直接加入":
                return None
        elif len(tag) == 3 and "加入" in _text_in(lines, (505, 326, 601, 369)):
            # A compact first row can lose letters in the whole-page OCR.
            prefix = f"[{tag}]"
            row_labels = _text_in(lines, (175, 271, 310, 310))
            if not any(label.startswith(prefix) for label in row_labels):
                label = image.crop((191, 285, 244, 308)).resize((159, 69), Image.Resampling.LANCZOS)
                if [compact(item["text"]) for item in ocr(label, "en-US")] != [prefix]:
                    return None
            top = 284
        else:
            return None
        red, green, blue = np.asarray(image.crop((480, top + 53, 615, top + 87)), dtype=np.int16).transpose(2, 0, 1)
        ready = ((green > 105) & (green - red > 50) & (green - blue > 35)).mean() > .55
        labels = [round(line["words"][0]["y"]) for line in lines if line.get("words")
                  and compact(line["text"]) == "加入" and 505 <= line["words"][0]["x"] < 601
                  and top + 40 <= line["words"][0]["y"] <= top + 85]
        return (top, labels[0] + 13 if len(labels) == 1 else top + 69) if ready else None

    frame, (top, button_y) = _wait_alliance_page(target, ocr, stop_event, identify, f"[{tag}] 的绿色加入按钮未确认")
    tag_right = 190 + 12 + 14 * len(tag)
    boxes = ((42, 184, 180, 225), (186, top - 5, tag_right, top + 28), (481, top + 53, 610, top + 85))
    physical_boxes = [
        (*map_content_point((left, y), REFERENCE, frame), *map_content_point((right, bottom), REFERENCE, frame))
        for left, y, right, bottom in boxes
    ]
    signatures = [np.asarray(frame.crop(box).convert("RGB"), dtype=np.int16) for box in physical_boxes[:2]]

    def same_page(current):
        if current.size != frame.size or not all(
            np.abs(np.asarray(current.crop(box).convert("RGB"), dtype=np.int16) - signature).mean() < 3.0
            for box, signature in zip(physical_boxes[:2], signatures)
        ):
            return False
        red, green, blue = np.asarray(current.crop(physical_boxes[2]).convert("RGB"), dtype=np.int16).transpose(2, 0, 1)
        return ((green > 90) & (green - red > 36) & (green - blue > 26)).mean() > .45

    return map_content_point((549, button_y), REFERENCE, frame), same_page


def rapid_join_taps(tap, inspect, stop_event, *, duration=RAPID_JOIN_DURATION, interval=RAPID_JOIN_INTERVAL,
                    missing_timeout=0.5):
    """Run a fixed cadence while an independent reader confirms the same live page."""
    done = Event()
    guard = Lock()
    started = time.monotonic()
    deadline = float("inf") if duration is None else started + duration
    valid_until = started
    failures = []
    count = 0

    def click_loop():
        nonlocal count
        try:
            tick = started
            while not stop_event.is_set() and time.monotonic() < deadline:
                if done.wait(max(0.0, tick - time.monotonic())):
                    break
                now = time.monotonic()
                if now >= deadline or stop_event.is_set():
                    break
                with guard:
                    allowed = now < valid_until
                if allowed and not done.is_set():
                    tap()
                    count += 1
                # A stalled transport drops ticks instead of sending a catch-up burst.
                tick += interval
                after = time.monotonic()
                if tick <= after:
                    tick += (int((after - tick) / interval) + 1) * interval
        except (OSError, RuntimeError, ValueError) as exc:
            failures.append(exc)
            done.set()

    worker = Thread(target=click_loop, name="fortress-rapid-join")
    worker.start()
    try:
        missing_since = None
        while not done.is_set() and not stop_event.is_set() and time.monotonic() < deadline:
            sampled = time.monotonic()
            visible = inspect()
            with guard:
                valid_until = sampled + RAPID_JOIN_FRAME_TTL if visible else 0
            if visible:
                missing_since = None
            elif missing_since is None:
                missing_since = sampled
            elif sampled - missing_since >= missing_timeout:
                break
            done.wait(0.025)
    finally:
        done.set()
        worker.join()
    if failures:
        raise failures[0]
    return count


def confirm_direct_join(target, ocr, stop_event, tag: str, *, timeout=6.0) -> None:
    handled = set()

    def identify(image, lines):
        if joined_tag_matches(image, lines, ocr, tag):
            return "joined"
        if "inactive_join" not in handled and can_confirm_inactive_alliance_join(lines):
            return "inactive_join"
        if "inactive_leave" not in handled and is_inactive_alliance_leave_warning(lines):
            return "inactive_leave"
        if "recommendation" not in handled and is_join_recommendation(lines):
            return "recommendation"
        if "relocation" not in handled and is_alliance_relocation_prompt(lines):
            return "relocation"
        if ("recommendation" in handled and "exact_result" not in handled
                and is_unaffiliated_in_frame(image, lines, ocr)):
            row = _listing_in_frame(image, lines, ocr, tag)
            if row and row[1].access == "可直接加入" and row[1].members < row[1].capacity:
                return "exact_result", row[0]
        return None

    def exact_info(_image, lines):
        return (
            "联盟资讯" in _text_in(lines, (240, 146, 433, 209))
            and any(text.startswith(f"[{tag}]") for text in _text_in(lines, (208, 217, 460, 272)))
            and any("任何人均可加入" in text for text in _text_in(lines, (211, 810, 490, 885)))
            and "加入" in _text_in(lines, (273, 903, 420, 968))
        )

    for _ in range(6):
        frame, outcome = _wait_alliance_page(
            target, ocr, stop_event, identify, f"[{tag}] 的入盟结果未确认", timeout=timeout)
        if outcome == "joined":
            return
        if isinstance(outcome, tuple):
            handled.add("exact_result")
            tap_verified_transition(target, stop_event, frame, (125, outcome[1] + 58))
            frame, _ = _wait_alliance_page(
                target, ocr, stop_event, exact_info, f"[{tag}] 的联盟资讯加入按钮未确认")
            tap_verified_transition(target, stop_event, frame, (336, 938))
            continue
        handled.add(outcome)
        if outcome == "inactive_join":
            if stop_event.is_set() or not target.foreground_is_game():
                raise InterruptedError()
            tap_game_point(target, frame, (451, 725))
        elif outcome in {"relocation", "recommendation"}:
            tap_verified_transition(target, stop_event, frame, (622, 195 if outcome == "recommendation" else 148))
        else:
            dismiss_inactive_alliance_warning(target, ocr, stop_event)
    raise ValueError(f"[{tag}] 的入盟结果未确认")


def _join_page_still_ready(inspect, stop_event) -> bool:
    deadline = time.monotonic() + 0.60
    stable_since = None
    while not stop_event.is_set() and time.monotonic() < deadline:
        if inspect():
            now = time.monotonic()
            if stable_since is not None and now - stable_since >= 0.22:
                return True
            if stable_since is None:
                stable_since = now
        else:
            stable_since = None
        stop_event.wait(0.06)
    return False


def run_rapid_join(target, ocr, stop_event, run, tag, save, *, rate=10, duration=RAPID_JOIN_DURATION,
                   check_only=False, notify=None, on_timeout=None, single_first=True):
    records = run["applications"]
    prior = records.get(tag)
    if not check_only and prior and prior.get("method", "application") == "application" and prior["state"] != "joined":
        raise ValueError(f"[{tag}] 正在审核，请继续查看审核结果")
    point, same_page = rapid_join_anchor(target, ocr, stop_event, tag)
    checked_focus = time.monotonic()
    ticks = []

    def inspect():
        nonlocal checked_focus
        if time.monotonic() - checked_focus >= 0.5:
            if not target.foreground_is_game():
                return False
            checked_focus = time.monotonic()
        return same_page(target.screenshot(timeout=1.5))

    with (target.touch_session() if rate == 100 else nullcontext()) as touch:
        def send_touch():
            if touch is not None:
                touch.touch_request(None if check_only else point)
            elif not check_only:
                target.shell(["cmd", "input", "tap", str(point[0]), str(point[1])], timeout=0.8)

        def tap():
            ticks.append(time.monotonic())
            send_touch()

        started = time.monotonic()
        count = 0
        run_clicker = check_only or not single_first
        if not check_only:
            started_at = (prior["started_at"] if prior and prior.get("method") == "direct"
                          and prior["state"] == "waiting" else time.time())
            records[tag] = {"started_at": started_at, "state": "waiting", "confirmed": False, "method": "direct"}
            save()
            if single_first and not stop_event.is_set() and target.foreground_is_game() and inspect():
                send_touch()
                count = 1
                if notify:
                    notify(f"[{tag}] 已单点加入，正在核对入盟或提示框")
                run_clicker = _join_page_still_ready(inspect, stop_event)
        if run_clicker:
            remaining = (None if duration is None else max(0, duration - (time.monotonic() - started)))
            if notify:
                limit = "不限时" if remaining is None else f"剩余 {remaining:.1f} 秒"
                notify(f"[{tag}] 开始连点 · 目标每秒 {rate} 次 · {limit}")
            count += rapid_join_taps(tap, inspect, stop_event, duration=2.1 if check_only else remaining,
                                     interval=1 / rate, missing_timeout=3.5 if duration is None and not check_only else 0.5)
        reached_limit = duration is not None and time.monotonic() - started >= duration

    rhythm = ""
    if len(ticks) >= 2:
        spacing = median(right - left for left, right in zip(ticks, ticks[1:]))
        rhythm = f" · 中位发送间隔 {spacing * 1000:.2f} ms"
    if check_only:
        if count < 2:
            raise ValueError("加入按钮画面在只读检测期间变化")
        return AllianceVisit(False, f"[{tag}] 只读连点检查 {count} 个节拍{rhythm}")
    if notify and run_clicker:
        notify(f"[{tag}] 连点已停止 · 连点发送 {len(ticks)} 次{rhythm}")
    if count == 0:
        if prior is None:
            records.pop(tag)
        else:
            records[tag] = prior
        save()
    if stop_event.is_set() or not target.foreground_is_game():
        return AllianceVisit(False, f"[{tag}] 连点已停止")
    try:
        confirm_direct_join(target, ocr, stop_event, tag, timeout=2.5 if duration is None else 6.0)
    except ValueError:
        if reached_limit:
            if count:
                records[tag]["state"] = "timed_out"
                save()
            message = f"[{tag}] 连点时间已到，仍未确认入盟。可选择继续连点。"
            if on_timeout:
                on_timeout(message)
            return AllianceVisit(False, message)
        return AllianceVisit(False, f"[{tag}] 连点已停止，入盟结果待核对")
    records[tag] = (records.get(tag) or
                    {"started_at": time.time(), "confirmed": False, "method": "direct"})
    records[tag]["state"] = "joined"
    save()
    return AllianceVisit(True, f"已进入 [{tag}]")


def open_alliance_application(
    target, ocr, stop_event, tag: str,
) -> tuple[Image.Image, AllianceApplication] | AllianceListing:
    _, image, lines = _alliance_frame(target, ocr, stop_event)
    dialog_header = "联盟资讯" in _text_in(lines, (240, 146, 433, 209))
    if not dialog_header:
        listing = precheck_alliance(target, ocr, stop_event, tag)
        if listing.access != "需要申请" or listing.members >= listing.capacity:
            return listing
        _, first_image, first = _alliance_frame(target, ocr, stop_event)
        frame, second_image, second = _alliance_frame(target, ocr, stop_event)
        row = _listing_in_frame(second_image, second, ocr, tag)
        if row is None or row != _listing_in_frame(first_image, first, ocr, tag) or row[1] != listing:
            raise ValueError("联盟搜索结果发生变化，请重新核对本站")
        if stop_event.is_set() or not target.foreground_is_game():
            raise InterruptedError()
        tap_game_point(target, frame, (125, row[0] + 58))
    previous = None
    for _ in range(4):
        frame, image, lines = _alliance_frame(target, ocr, stop_event)
        observed = read_alliance_application(image, lines, ocr)
        if observed and observed.tag != tag:
            raise ValueError(f"当前联盟资讯为 [{observed.tag}]，本站为 [{tag}]")
        if observed and observed == previous:
            return frame, observed
        previous = observed
    raise ValueError(f"未确认 [{tag}] 的申请控件")


def start_alliance_application(target, ocr, stop_event, tag, remember) -> AllianceListing | None:
    result = open_alliance_application(target, ocr, stop_event, tag)
    if isinstance(result, AllianceListing):
        return result
    frame, application = result
    if stop_event.is_set() or not target.foreground_is_game():
        raise InterruptedError()
    remember(application.status in {"pending", "gray"})
    if application.status == "ready":
        if stop_event.is_set():
            raise InterruptedError()
        tap_game_point(target, frame, (336, 943))
        def result(image, lines):
            if can_confirm_inactive_alliance_join(lines):
                return "confirm"
            if is_unaffiliated_in_frame(image, lines, ocr) or joined_tag_matches(image, lines, ocr, tag):
                return "changed"
            observed = read_alliance_application(image, lines, ocr)
            return "pending" if observed and observed.tag == tag and observed.status in {"pending", "gray"} else None

        try:
            frame, outcome = _wait_alliance_page(target, ocr, stop_event, result, "申请结果待核对")
        except PageNotVerified:
            return None
        if outcome == "confirm":
            if stop_event.is_set() or not target.foreground_is_game():
                raise InterruptedError()
            tap_game_point(target, frame, (451, 725))
    return None


def read_joined_alliance(lines: list[dict]) -> str | None:
    tag = read_alliance(lines)
    controls = set(_text_in(lines, (140, 1138, 544, 1192)))
    return tag if len(controls & {"成员", "激励", "设置"}) >= 2 else None


def joined_tag_matches(image, lines, ocr, tag: str) -> bool:
    return read_joined_in_frame(image, lines, ocr) == tag


def read_joined_in_frame(image, lines, ocr) -> str | None:
    exact = read_joined_alliance(lines)
    if exact:
        return exact
    controls = set(_text_in(lines, (140, 1138, 544, 1192)))
    if len(controls & {"成员", "激励", "设置"}) < 2:
        return None
    if "联盟" not in _text_in(lines, (70, 0, 170, 60)):
        return None
    titles = _text_in(lines, (230, 84, 490, 139))
    if len(titles) != 1:
        return None
    if titles[0].startswith("["):
        pixels = np.asarray(image.crop((257, 93, 338, 133)), dtype=np.int16)
        text = (pixels.min(axis=2) > 143) & (np.ptp(pixels, axis=2) < 48)
        isolated = Image.fromarray(np.where(text, 0, 255).astype(np.uint8))
        zoom = isolated.resize((243, 120), Image.Resampling.LANCZOS)
        values = ocr(ImageOps.expand(zoom, border=16, fill=255), "en-US")
        tag = re.match(r"^\[([A-Za-z0-9-]{1,16})\]", "".join(compact(row["text"]) for row in values))
        if tag and titles[0].startswith(f"[{tag[1]}"):
            return tag[1]
    tail = re.match(r"^([A-Za-z0-9-]{2})\]", titles[0])
    head = re.match(r"^\[([A-Za-z0-9-]{2})(?:[A-Za-z0-9-][Il|])?(?=[\u3400-\u9fff])", titles[0])
    if not tail and not head:
        return None
    for box, size, pattern in (
        ((261, 99, 321, 130), (180, 93), r"\[([A-Za-z0-9-]{3})\]?"),
        ((252, 93, 320, 134), (272, 164), r"\[([A-Za-z0-9-]{3})\]"),
    ):
        crop = image.crop(box).resize(size, Image.Resampling.LANCZOS)
        values = [compact(line["text"]) for line in ocr(crop, "en-US")]
        local = re.fullmatch(pattern, values[0]) if len(values) == 1 else None
        if local and ((tail is not None and local[1][1:] == tail[1])
                      or (head is not None and local[1][:2] == head[1])):
            return local[1]
    return None


def wait_for_alliance(deadline, stop_event, probe, *, clock=time.monotonic) -> bool:
    while not stop_event.is_set():
        if probe():
            return True
        remaining = deadline - clock()
        if remaining <= 0:
            return False
        stop_event.wait(min(remaining, APPLICATION_POLL))
    raise InterruptedError()


def observe_alliance_application(
    target, ocr, stop_event, tag: str, navigation: set[str], *, confirmed: bool,
) -> str | None:
    if not target.foreground_is_game():
        return None
    _, image, lines = _alliance_frame(target, ocr, stop_event)
    if joined_tag_matches(image, lines, ocr, tag):
        _, fresh_image, fresh = _alliance_frame(target, ocr, stop_event)
        return "joined" if joined_tag_matches(fresh_image, fresh, ocr, tag) else None
    if confirmed and is_alliance_relocation_prompt(lines) and "relocation" not in navigation:
        frame, _ = _wait_alliance_page(
            target, ocr, stop_event, lambda _im, current: is_alliance_relocation_prompt(current),
            "迁城提示未稳定")
        navigation.add("relocation")
        tap_verified_transition(target, stop_event, frame, (622, 148))
        return None
    if confirmed and is_inactive_alliance_leave_warning(lines) and "post_join_warning" not in navigation:
        navigation.add("post_join_warning")
        dismiss_inactive_alliance_warning(target, ocr, stop_event)
        _, first_image, first = _alliance_frame(target, ocr, stop_event)
        _, second_image, second = _alliance_frame(target, ocr, stop_event)
        return "joined" if (joined_tag_matches(first_image, first, ocr, tag)
                            and joined_tag_matches(second_image, second, ocr, tag)) else None
    if is_game_root(lines) and "alliance_home" not in navigation:
        frame, _, fresh = _alliance_frame(target, ocr, stop_event)
        if not is_game_root(fresh) or stop_event.is_set():
            return None
        if not target.foreground_is_game():
            return None
        navigation.discard("back_no_alliance")
        navigation.add("alliance_home")
        tap_game_point(target, frame, (498, 1138))
        _, first_image, first = _alliance_frame(target, ocr, stop_event)
        _, second_image, second = _alliance_frame(target, ocr, stop_event)
        return "joined" if (joined_tag_matches(first_image, first, ocr, tag)
                            and joined_tag_matches(second_image, second, ocr, tag)) else None
    if confirmed and is_unaffiliated_alliance_page(lines) and "back_no_alliance" not in navigation:
        frame, _, fresh = _alliance_frame(target, ocr, stop_event)
        if is_unaffiliated_alliance_page(fresh) and not stop_event.is_set() and target.foreground_is_game():
            navigation.discard("alliance_home")
            navigation.add("back_no_alliance")
            tap_game_point(target, frame, (37, 36))
            return None
    dialog = read_alliance_application(image, lines, ocr)
    if dialog and dialog.tag == tag and dialog.status in {"pending", "gray"}:
        frame, fresh_image, fresh_lines = _alliance_frame(target, ocr, stop_event)
        if read_alliance_application(fresh_image, fresh_lines, ocr) == dialog:
            if stop_event.is_set():
                raise InterruptedError()
            if confirmed and "close_info" not in navigation and target.foreground_is_game():
                navigation.add("close_info")
                tap_game_point(target, frame, (620, 183))
            return "pending"
    if confirmed and alliance_search_field(lines) == tag.upper() and "back_search" not in navigation:
        frame, _, fresh = _alliance_frame(target, ocr, stop_event)
        if (alliance_search_field(fresh) == tag.upper() and not stop_event.is_set()
                and target.foreground_is_game()):
            navigation.add("back_search")
            tap_game_point(target, frame, (37, 36))
    if confirmed and is_alliance_settings(lines) and "back_management" not in navigation:
        frame, _, fresh = _alliance_frame(target, ocr, stop_event)
        if is_alliance_settings(fresh) and not stop_event.is_set() and target.foreground_is_game():
            navigation.add("back_management")
            tap_game_point(target, frame, (37, 36))
    return None


@dataclass(frozen=True)
class AllianceVisit:
    joined: bool
    message: str


def enter_route_alliance(
    target, ocr, stop_event, run: dict, tag: str, save, *, leave_current: bool,
    notify=None, on_timeout=None, return_by: datetime | None = None, rapid_rate: int | None = None,
) -> AllianceVisit:
    applications = run.setdefault("applications", {})
    navigation = set()

    def remember(confirmed, *, method="application"):
        applications[tag] = {
            "started_at": time.time(), "state": "waiting", "confirmed": confirmed, "method": method,
        }
        try:
            save()
        except (OSError, ValueError, RuntimeError):
            applications.pop(tag)
            raise

    def deadline_passed() -> bool:
        return return_by is not None and datetime.now(SHANGHAI) >= return_by

    if deadline_passed():
        return AllianceVisit(False, f"[{tag}] 已到钥匙返回截止时间")
    record = applications.get(tag)
    if record is None or record["state"] == "joined" or leave_current:
        if leave_current and not re.fullmatch(r"[A-Za-z0-9-]{1,16}", tag):
            raise ValueError("请先填写游戏方括号里的联盟短标签")
        if prepare_alliance_route(target, ocr, stop_event, tag, leave_current=leave_current):
            if record and record["state"] != "joined":
                record["state"] = "joined"
                save()
            return AllianceVisit(True, f"当前已在 [{tag}]")
        if record and record["state"] == "joined":
            applications.pop(tag)
            record = None
    if record is None:
        if deadline_passed():
            return AllianceVisit(False, f"[{tag}] 已到钥匙返回截止时间")
        try:
            listing = start_alliance_application(target, ocr, stop_event, tag, remember)
        except (OSError, AdbError):
            if tag not in applications:
                raise
            listing = None
        if listing:
            if rapid_rate is not None and listing.access == "可直接加入":
                seconds = RAPID_JOIN_DURATION
                if return_by is not None:
                    seconds = min(seconds, (return_by - datetime.now(SHANGHAI)).total_seconds())
                if seconds <= 0:
                    return AllianceVisit(False, f"[{tag}] 已到钥匙返回截止时间")
                return run_rapid_join(target, ocr, stop_event, run, tag, save, rate=rapid_rate,
                                      duration=seconds, notify=notify, on_timeout=on_timeout)
            if listing.access == "可直接加入" and listing.members < listing.capacity:
                join_available_alliance(target, ocr, stop_event, tag, lambda: remember(False, method="direct"))
                applications[tag]["state"] = "joined"
                save()
                return AllianceVisit(True, f"已进入 [{tag}]")
            full = " · 已满员" if listing.members >= listing.capacity else ""
            return AllianceVisit(False, f"[{tag}] {listing.members}/{listing.capacity} · {listing.access}{full}")
        record = applications[tag]

    def probe():
        try:
            observed = observe_alliance_application(
                target, ocr, stop_event, tag, navigation, confirmed=record["confirmed"])
        except (OSError, AdbError, ValueError):
            return False
        if stop_event.is_set():
            raise InterruptedError()
        if observed == "pending" and not record["confirmed"]:
            record["confirmed"] = True
            save()
            if notify:
                notify(f"[{tag}] 已确认申请送出，正在核对入盟。")
        return observed == "joined"

    if record.get("method") == "direct" or record["state"] == "timed_out":
        if not probe():
            if record.get("method") == "direct" and record["state"] == "waiting" and rapid_rate is not None:
                remaining = RAPID_JOIN_DURATION - max(0, time.time() - record["started_at"])
                if return_by is not None:
                    remaining = min(remaining, (return_by - datetime.now(SHANGHAI)).total_seconds())
                if remaining > 0:
                    # Rearm only if the exact unaffiliated search and its green Join button are verified again.
                    return run_rapid_join(target, ocr, stop_event, run, tag, save, rate=rapid_rate,
                                          duration=remaining, notify=notify, on_timeout=on_timeout)
            return AllianceVisit(False, f"[{tag}] 仍未确认入盟，请查看游戏中的结果。")
    else:
        elapsed = max(0, time.time() - record["started_at"])
        remaining = max(0, APPLICATION_TIMEOUT - elapsed)
        if return_by is not None:
            remaining = min(remaining, max(0, (return_by - datetime.now(SHANGHAI)).total_seconds()))
        if notify:
            notify(f"[{tag}] 正在核对申请和入盟。")
        if not wait_for_alliance(time.monotonic() + remaining, stop_event, probe):
            if stop_event.is_set():
                raise InterruptedError()
            if deadline_passed() and time.time() - record["started_at"] < APPLICATION_TIMEOUT:
                return AllianceVisit(False, f"[{tag}] 到返回截止仍未确认入盟")
            record["state"] = "timed_out"
            save()
            message = (f"[{tag}] 的申请已提交，3 分钟内未确认进入联盟。请查看游戏中的审核结果。"
                       if record["confirmed"] else
                       f"[{tag}] 在 3 分钟内未确认申请结果或入盟，请打开游戏核对。")
            if on_timeout:
                on_timeout(message)
            return AllianceVisit(False, message)
    record["state"] = "joined"
    save()
    return AllianceVisit(True, f"已进入 [{tag}]")


def occupation_complete(occupied: set[tuple[str, int]], stop: dict) -> bool:
    return bool(stop["targets"]) and all(
        (target["kind"], target["number"]) in occupied for target in stop["targets"]
    )


def registration_matches(image, lines, ocr, stop: dict) -> bool:
    if not stop.get("all_registered"):
        return True
    registered = read_registered_targets(image, lines, ocr)
    return registered is not None and set(registered) == {
        (target["kind"], target["number"]) for target in stop["targets"]
    }


def capture_reward(target, ocr) -> tuple[Image.Image, RewardMail | None]:
    frame = target.screenshot(timeout=6)
    image = normalize_frame(frame)
    return frame, read_mail(image, ocr(image), ocr)


def claim_reward(target, frame: Image.Image) -> None:
    tap_game_point(target, frame, CLAIM_POINT)


def tap_game_point(target, frame: Image.Image, normalized_point: tuple[int, int]) -> None:
    point = map_content_point(normalized_point, REFERENCE, frame)
    target.shell(["input", "tap", str(point[0]), str(point[1])], timeout=5)


def tap_verified_transition(target, stop_event, frame, point) -> None:
    if not isinstance(target, RouteCapture):
        if stop_event.is_set() or not target.foreground_is_game():
            raise InterruptedError()
        tap_game_point(target, frame, point)
        return
    with target.touch_session() as touch:
        if stop_event.is_set() or not target.foreground_is_game():
            raise InterruptedError()
        touch.touch_request(map_content_point(point, REFERENCE, frame))


def open_game_screen(target, ocr, stop_event, entry: str) -> tuple[Image.Image, list[dict]]:
    def read():
        if stop_event.is_set():
            raise InterruptedError()
        frame = target.screenshot(timeout=6)
        image = normalize_frame(frame)
        return frame, image, ocr(image)

    def tap(frame, point):
        if stop_event.is_set() or not target.foreground_is_game():
            raise InterruptedError()
        tap_game_point(target, frame, point)

    def await_page(predicate):
        deadline = time.monotonic() + 5.0
        previous = False
        while time.monotonic() < deadline:
            frame, image, lines = read()
            visible = predicate(lines)
            if visible and previous:
                return frame, image, lines
            previous = visible
            stop_event.wait(0.08)
        raise PageNotVerified("页面未按预期切换")

    frame, image, lines = read()
    if entry == "mail" and is_regular_activity(lines):
        frame, image, lines = read()
        if not is_regular_activity(lines):
            raise ValueError("常规活动画面发生变化")
        tap(frame, (37, 36))
        frame, image, lines = await_page(is_game_root)
    on_target = is_regular_activity(lines) if entry == "activity" else is_mail_list(lines)
    if not on_target:
        point = root_entry(image, lines, entry)
        for _ in range(5):
            frame, image, lines = read()
            fresh = root_entry(image, lines, entry)
            if fresh is not None and fresh == point:
                break
            point = fresh
            stop_event.wait(.08)
        else:
            raise PageNotVerified("主城或野外的目标入口未确认")
        tap(frame, point)
        frame, image, lines = await_page(is_regular_activity if entry == "activity" else is_mail_list)
    if entry == "mail" and not alliance_mail_selected(image, lines):
        frame, image, lines = read()
        if "联盟" not in _text_in(lines, (165, 78, 268, 138)) or not is_mail_list(lines):
            raise ValueError("请打开邮件的联盟标签")
        if not alliance_mail_selected(image, lines):
            tap(frame, (212, 107))
            for _ in range(3):
                _, image, lines = read()
                if alliance_mail_selected(image, lines):
                    break
            else:
                raise ValueError("联盟邮件标签未确认")
    return image, lines


class MailNotYetVisible(ValueError):
    pass


class MailClaimUnconfirmed(ValueError):
    pass


def open_recent_victory_mail(target, ocr, stop_event, since: datetime, known: set[datetime], *, expected=None):
    """Open one visible candidate; the detail header remains the claim gate."""
    open_game_screen(target, ocr, stop_event, "mail")

    def row(image, lines):
        if not alliance_mail_selected(image, lines):
            return None
        candidates = []
        for line in lines:
            title = compact(line["text"])
            if title not in FORTRESS_MAIL or not line.get("words"):
                continue
            position = line["words"][0]
            x, y = position["x"], round(position["y"])
            if 140 < x < 215 and 156 < y < 1070:
                candidates.append((y, title))
        for y, title in sorted(candidates):
            stamp = mail_row_stamp(image, lines, y, ocr)
            if stamp is not None and (stamp < since or stamp in known):
                continue
            if expected is not None and stamp != expected:
                continue
            return y, title, stamp
        return None

    try:
        frame, (y, title, stamp) = _wait_alliance_page(
            target, ocr, stop_event, row, "未看到本次入盟后的胜利邮件")
    except ValueError as exc:
        if str(exc) != "未看到本次入盟后的胜利邮件":
            raise
        raise MailNotYetVisible(str(exc)) from exc
    if stop_event.is_set() or not target.foreground_is_game():
        raise InterruptedError()
    tap_game_point(target, frame, (312, y + 36))
    frame, mail = _wait_alliance_page(
        target, ocr, stop_event, lambda image, lines: read_mail(image, lines, ocr),
        "胜利邮件详情或右上角发件时间未确认")
    if (mail.title != title or (stamp is not None and mail.stamp != stamp)
            or not since <= mail.stamp <= datetime.now(SHANGHAI) or mail.stamp in known
            or (expected is not None and mail.stamp != expected)):
        raise ValueError("已打开邮件，但详情时间未能归入当前站")
    return frame, mail


def open_fortress_activity(target, ocr, stop_event) -> tuple[Image.Image, list[dict]]:
    image, lines = open_game_screen(target, ocr, stop_event, "activity")
    strip_box = (20, 95, 650, 167)
    toward_earlier = None
    before_swipe = None
    blocked = set()
    selection_retried = False

    def activity_location(image, lines):
        if is_fortress_activity(lines):
            return "open", None
        point = fortress_tab_point(image, lines)
        return ("tab", point) if point is not None else None

    for _ in range(12):
        if is_fortress_activity(lines):
            return image, lines
        strip = np.asarray(image.crop(strip_box), dtype=np.int16)
        settle_by = time.monotonic() + 2.0
        while time.monotonic() < settle_by:
            if stop_event.is_set():
                raise InterruptedError()
            frame = target.screenshot(timeout=6)
            fresh = normalize_frame(frame)
            fresh_strip = np.asarray(fresh.crop(strip_box), dtype=np.int16)
            still = np.abs(strip - fresh_strip).mean() < 3
            moved = before_swipe is None or np.abs(fresh_strip - before_swipe).mean() >= 3
            if still and moved:
                break
            strip = fresh_strip
            stop_event.wait(min(0.08, max(0, settle_by - time.monotonic())))
        else:
            if before_swipe is not None and np.abs(strip - before_swipe).mean() < 3:
                blocked.add(toward_earlier)
                if len(blocked) == 2:
                    raise PageNotVerified("活动标签双向滑动未确认")
            else:
                raise PageNotVerified("活动栏持续移动，标签未确认")
        if stop_event.is_set() or not target.foreground_is_game():
            raise InterruptedError()
        lines = ocr(fresh)
        if stop_event.is_set():
            raise InterruptedError()
        if is_fortress_activity(lines):
            return fresh, lines
        point = fortress_tab_point(fresh, lines)
        if point is not None:
            frame, (location, point) = _wait_alliance_page(
                target, ocr, stop_event, activity_location, "堡垒争夺标签位置未稳定")
            if location == "open":
                image = normalize_frame(frame)
                return image, ocr(image)
            tap_verified_transition(target, stop_event, frame, point)
            try:
                frame, _ = _wait_alliance_page(
                    target, ocr, stop_event, lambda _im, current: is_fortress_activity(current),
                    "堡垒争夺页面未确认", timeout=3.0)
            except PageNotVerified:
                if selection_retried:
                    raise
                selection_retried = True
                image = normalize_frame(target.screenshot(timeout=6))
                lines = ocr(image)
                before_swipe = None
                continue
            image = normalize_frame(frame)
            return image, ocr(image)
        if not is_regular_activity(lines):
            break
        tabs = _text_in(lines, (35, 131, 655, 170))
        before_target = any(label in {"日历", "全军参战", "全军參战", "联盟争霸赛"} for label in tabs)
        after_target = any(any(key in label for key in ("巨熊", "霜龙", "乔伊", "王城", "社区")) for label in tabs)
        if before_target != after_target:
            toward_earlier = after_target
        if toward_earlier is None:
            toward_earlier = False
        if toward_earlier in blocked:
            toward_earlier = not toward_earlier
        left, right = (113, 287) if toward_earlier else (560, 386)
        start = map_content_point((left, 125), REFERENCE, frame)
        end = map_content_point((right, 125), REFERENCE, frame)
        target.shell(["input", "swipe", *map(str, (*start, *end, 460))], timeout=5)
        before_swipe = fresh_strip
        stop_event.wait(0.32)
        image = normalize_frame(target.screenshot(timeout=6))
        lines = ocr(image)
    raise PageNotVerified("尚未找到堡垒争夺标签，请在常规活动中核对")


def collect_reward(target, ocr, stop_event, record, *, claim: bool,
                   verified: tuple[Image.Image, RewardMail] | None = None, on_claimed=None) -> RewardMail:
    """Require two agreeing reads and persist intent before a single input."""
    if stop_event.is_set():
        raise InterruptedError()
    if verified is None:
        _, first = capture_reward(target, ocr)
        frame, second = capture_reward(target, ocr)
        if first is None or first != second:
            raise ValueError("请打开本联盟的胜利邮件详情，等待标题、右上角发件时间和领取状态清晰")
    else:
        frame, first = verified
    if stop_event.is_set():
        raise InterruptedError()

    def complete(confirmed_frame, mail):
        record(mail, "claimed")
        if on_claimed is not None:
            on_claimed(confirmed_frame)
        return mail

    if first.claimed:
        return complete(frame, first)
    if not claim:
        raise ValueError("这封邮件尚未领取，请核对后使用「领取当前邮件」")
    if not target.foreground_is_game():
        raise ValueError("游戏不在 Android 前台")
    record(first, "pending")
    if stop_event.is_set():
        raise InterruptedError()
    claim_reward(target, frame)
    for _ in range(3):
        if stop_event.is_set():
            raise InterruptedError()
        confirmed_frame, observed = capture_reward(target, ocr)
        if observed == RewardMail(first.stamp, first.title, True):
            return complete(confirmed_frame, observed)
    raise MailClaimUnconfirmed("领取结果未确认，等待游戏显示「已领取」")
