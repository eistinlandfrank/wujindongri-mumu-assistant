"""Polar Terror formation recognition and account-bound dispatch accounting."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, time as clock_time, timedelta, timezone
from functools import lru_cache
from pathlib import Path
import hashlib
import json
import re
import time
import unicodedata

import cv2
import numpy as np
from PIL import Image

from wjdr_backend import (
    CONFIG_DIR, BeastRallyState, _atomic_json_write, _serialized_account_write,
    content_viewport, map_content_point, match_beast_rally_formation_controls,
    read_daily_gather_formation_capacity, resource_path,
)

LIMIT = 6
WAVE_SECONDS = 5 * 60
ZONE = timezone(timedelta(hours=8))
TRAP_END = clock_time(21, 0)
POLL_SECONDS = 0.08
WIDTH = 786
JOIN_TEXT = "点击加入集结队伍一起打败敌人"
COORDINATES = re.compile(r"\((\d{1,4}),(\d{1,4})\)")
TAG = re.compile(r"^\[[A-Za-z0-9]{1,8}\]")
BEAR_TARGET = re.compile(r"(?:(?:等级|Lv\.?)\d{1,2})?(?:变异)?巨熊")


def compact(text):
    return "".join(unicodedata.normalize("NFKC", text).split())


def nickname(text):
    return TAG.sub("", compact(text), count=1)


def roster_settings(names, player):
    if not isinstance(names, (list, tuple)) or not all(isinstance(name, str) for name in names):
        raise ValueError("请输入集结队长名单")
    leaders = tuple(dict.fromkeys(nickname(name) for name in names if name.strip()))
    player = nickname(player) if isinstance(player, str) else ""
    if not leaders or len(leaders) > 40 or not player or player in leaders:
        raise ValueError("请输入自己的游戏昵称和 1–40 个不同的盟友昵称")
    if any(len(name) > 32 for name in (*leaders, player)):
        raise ValueError("游戏昵称最多 32 个字符")
    return {"names": leaders, "player": player}


def account_file(identity: str, purpose: str, directory: Path = CONFIG_DIR) -> Path:
    if not re.fullmatch(r"mumu:\d+:android:[^:]+", identity):
        raise ValueError("无法确认当前 MuMu 手机身份")
    digest = hashlib.sha256(identity.encode()).hexdigest()
    return directory / f"bear_{purpose}_{digest}.json"


def wave_at(now=None):
    return int((time.time() if now is None else now) // WAVE_SECONDS)


def join_cutoff_at(now=None):
    current = datetime.fromtimestamp(time.time() if now is None else now, ZONE)
    return datetime.combine(current.date(), TRAP_END, ZONE).timestamp() - WAVE_SECONDS


def wave_count(records, wave):
    return sum(record["wave"] == wave and record.get("counted", True) for record in records)


def _read_ledger(path, day):
    if not path.exists():
        return []
    payload = json.loads(path.read_text("utf-8"))
    records = payload["records"]
    if (not isinstance(records, list) or len(records) > LIMIT * 288
            or any(not isinstance(record, dict) or record.get("state") not in {"sent", "confirmed", "submitted", "checked"}
                   for record in records)):
        raise ValueError("打熊出征记录异常")
    # An unknown submission from a prior day still needs manual reconciliation.
    if payload["day"] != day and all(record["state"] != "sent" for record in records):
        return []
    legacy_wave = wave_at(path.stat().st_mtime)
    for record in records:
        record.setdefault("wave", legacy_wave)
    return records


def ledger(path, day, *, all_waves=False, now=None):
    records = _read_ledger(path, day)
    if any(record["state"] == "sent" for record in records):
        raise ValueError("有一次打熊出征尚未核实，请先在游戏中核对出征结果")
    wave = wave_at(now)
    return records if all_waves else [record for record in records
                                       if record["wave"] == wave and record.get("counted", True)]


@_serialized_account_write
def set_wave_count(day, count, *, path, now=None):
    if type(count) is not int or not 0 <= count <= LIMIT:
        raise ValueError("本轮出征计数须为 0 到 6")
    now = time.time() if now is None else now
    wave = wave_at(now)
    records = ledger(path, day, all_waves=True, now=now)
    existing = [record for record in records if record["wave"] == wave]
    for index, record in enumerate(reversed(existing)):
        record["counted"] = index < count
    for index in range(max(0, count - len(existing))):
        records.append({"key": f"manual:{wave}:{len(existing) + index}", "state": "checked",
                        "expires": now, "wave": wave})
    _atomic_json_write(path, {"day": day, "records": records})
    return wave_count(records, wave)


@_serialized_account_write
def record_dispatch(day, key, *, expires, confirm=False, rejected=False, submitted=False, path, now=None):
    records = _read_ledger(path, day)
    now = time.time() if now is None else now
    current = wave_at(now)
    pending = [record for record in records if record["state"] == "sent"]
    if confirm or rejected or submitted:
        if len(pending) != 1 or pending[0]["key"] != key:
            raise ValueError("打熊出征回执与记录不符")
        if rejected:
            records.remove(pending[0])
        else:
            pending[0]["state"] = "submitted" if submitted else "confirmed"
    else:
        if pending or wave_count(records, current) >= LIMIT or any(
            record["key"] == key and record["expires"] > now for record in records
        ):
            raise ValueError("打熊出征已达上限、已有相同集结或有待核实记录")
        records.append({"key": key, "state": "sent", "expires": expires, "wave": current})
    _atomic_json_write(path, {"day": day, "records": records})
    return wave_count(records, current)


@_serialized_account_write
def reconcile_dispatch(*, path):
    if not path.exists():
        return False
    payload = json.loads(path.read_text("utf-8"))
    records = _read_ledger(path, payload["day"])
    pending = [record for record in records if record["state"] == "sent"]
    if len(pending) != 1:
        return False
    pending[0]["state"] = "checked"
    payload["records"] = records
    _atomic_json_write(path, payload)
    return True


@dataclass(frozen=True)
class Line:
    text: str
    x: int
    y: int
    right: int

    @property
    def point(self):
        return (self.x + self.right) // 2, self.y


def lines(result):
    items = []
    for row in result:
        if words := row.get("words"):
            items.append(Line(compact(row["text"]), round(min(w["x"] for w in words)),
                              round(sum(w["y"] + w["height"] / 2 for w in words) / len(words)),
                              round(max(w["x"] + w["width"] for w in words))))
    return items


def normalized(image):
    view = content_viewport(image)
    if view.width < 720 or abs(view.height / view.width - 16 / 9) > 0.04:
        raise ValueError("打熊需要标准竖屏 9:16 的 MuMu 游戏画面")
    return image.crop(view.box).resize((WIDTH, round(WIDTH * view.height / view.width))), view


def _in(items, text, x1, x2, y1, y2):
    return next((row for row in items if row.text == text and x1 <= row.x < x2 and y1 <= row.y < y2), None)


def _color(image, point):
    x, y = point
    return np.median(np.asarray(image.crop((x - 3, y - 3, x + 4, y + 4))), axis=(0, 1))


@dataclass(frozen=True)
class Card:
    leader: str
    point: tuple[int, int]

    @property
    def key(self):
        return f"{self.leader}|0,0"


@dataclass(frozen=True)
class Detail:
    join: tuple[int, int] | None
    present: bool
    seconds: int
    origin: tuple[int, int]


def rally_detail(image, items, card, player, *, expected_origin=None):
    if not (_in(items, "联盟战争", 70, 270, 10, 90)
            or _detail_title_visible(image)):
        return None
    leader_label = next((row for row in items if row.text.startswith("队长:")
                         and 225 <= row.x <= 360 and 125 <= row.y <= 290), None)
    if leader_label is None:
        return None
    leader_fields = [row.text for row in items if row.x >= max(325, leader_label.right + 8)
                     and abs(row.y - leader_label.y) < 22]
    leader_text = leader_label.text.removeprefix("队长:") + "".join(leader_fields)
    if nickname(leader_text) != card.leader:
        return None
    target_present = any(BEAR_TARGET.fullmatch(row.text) and row.right < 285
                         and 170 < row.y < 530 for row in items)
    coordinate_label = next((row for row in items if row.text.startswith("坐标:")
                             and 225 <= row.x <= 360 and leader_label.y + 35 < row.y < 460), None)
    # The card coordinates identify the trap. Alliance War shows the captain's origin.
    location = next((location for row in items if coordinate_label is not None
                     and abs(row.y - coordinate_label.y) < 19 and row.right > 540
                     and (location := COORDINATES.search(row.text))), None)
    if not target_present or location is None:
        return None
    origin = tuple(map(int, location.groups()))
    if expected_origin is not None and origin != expected_origin:
        return None
    timer = next((row for row in items if row.text.startswith("集结中")
                  and 265 < row.x < 570 and leader_label.y + 75 < row.y < 550), None)
    seconds = 0
    if timer:
        timer_text = "".join(row.text for row in sorted(items, key=lambda row: row.x)
                             if row.x >= timer.x and abs(row.y - timer.y) <= 15)
        match = re.search(r"(\d{1,2}):(\d{2}):(\d{2})", timer_text)
        if match:
            hours, minutes, seconds = map(int, match.groups())
            seconds += 3600 * hours + 60 * minutes
    present = any(nickname(row.text) == player and 160 <= row.x < 640
                  and 480 < row.y < image.height - 48 for row in items)
    for row in sorted(items, key=lambda item: item.y):
        if row.text == JOIN_TEXT and 152 <= row.x <= 290 and 500 < row.y < image.height - 108:
            r, g, b = _color(image, (row.right + 15, row.y))
            if not present and 0 < seconds <= 600 and 75 < r < 180 and g > r + 40 and b > g + 22:
                return Detail(row.point, False, seconds, origin)
    return Detail(None, present, seconds, origin)


@dataclass(frozen=True)
class Preset:
    point: tuple[int, int]
    selected: bool
    warned: bool = False


def _white(rgb):
    return ((rgb.min(axis=2) >= 195) & (np.ptp(rgb, axis=2) < 55)).astype(np.uint8)


@lru_cache(maxsize=1)
def _preset_templates():
    samples = []
    for name in ("bear_preset_label", "bear_preset_car_label", "bear_preset_compact_label",
                 "bear_preset_selected_label"):
        with Image.open(resource_path(f"assets/{name}.png")) as glyph:
            mask = np.asarray(glyph.convert("L"))
        samples.extend(np.split(mask, mask.shape[0] // 29))
    return [cv2.resize(sample, None, fx=scale, fy=scale, interpolation=cv2.INTER_NEAREST)
            for sample in samples for scale in (0.84, 0.92, 1.0, 1.08, 1.12, 1.16)]


def bear_presets(strip, *, top=0, allow_warning=False):
    rgb = np.asarray(strip)
    mask = _white(rgb)
    candidates = []
    for template in _preset_templates():
        height, width = template.shape
        scores = cv2.matchTemplate(mask, template, cv2.TM_CCOEFF_NORMED)
        for y, x in zip(*np.where(scores >= 0.82)):
            candidates.append((float(scores[y, x]), int(x + width * 0.46), int(y + height // 2)))
    found = []
    occupied = []
    for _, cx, cy in sorted(candidates, reverse=True):
        if cx < 32 or cx + 52 >= strip.width or cy < 32:
            continue
        if any(abs(cx - old_x) < 37 for old_x in occupied):
            continue
        occupied.append(cx)
        badge = rgb[cy-54 if cy >= 54 else 0:cy-19, cx+14:cx+48]
        warning = (badge[:, :, 0] > 215) & (badge[:, :, 1] > 90) & (badge[:, :, 1] < 177) & (badge[:, :, 2] < 85)
        warned = int(warning.sum()) > 30
        if warned and not allow_warning:
            continue
        tile = rgb[cy-31:cy-9, cx-23:cx+24]
        gold = (tile[:, :, 0] > 185) & (tile[:, :, 1] > 147) & (tile[:, :, 2] < 135)
        selected = float(gold.mean()) > 0.12
        found.append(Preset((cx, top + cy - 17), selected, warned))
    return sorted(found, key=lambda preset: preset.point)


@lru_cache(maxsize=3)
def _template(name):
    with Image.open(resource_path(f"assets/{name}.png")) as source:
        return np.asarray(source.convert("RGB"))


def _detail_title_visible(image):
    header = np.asarray(image.crop((66, 6, 285, 100)))
    template = _template("bear_rally_title")
    return cv2.matchTemplate(header, template, cv2.TM_CCOEFF_NORMED).max() >= 0.89


class PageTimeout(ValueError):
    pass


class TroopLimit(ValueError):
    def __init__(self, modal=False):
        super().__init__("当前集结容不下已储存的熊编队")
        self.modal = modal


def troop_limit_dialog(image, items):
    if not _in(items, "士兵超过出征上限,请重新编队", 155, 265, 622, 713):
        return None
    button = _in(items, "确定", 326, 435, 815, 907)
    return button.point if button else None


class BearFlow:
    def __init__(self, target, stop, ocr, settings, path, report):
        self.target = target
        self.stop = stop
        self.ocr = ocr
        self.settings = settings
        self.path = path
        self.report = report
        self.day = datetime.now(ZONE).date().isoformat()
        self.stop_at = None
        self.ignored = {}
        self.ocr_key = None
        self.ocr_lines = []

    def input_stopped(self):
        return self.stop.is_set() or (self.stop_at is not None and time.time() >= self.stop_at)

    def tap(self, point, view=None):
        if self.input_stopped():
            raise InterruptedError()
        if view is not None:
            x, y = point
            point = (view.left + round(x * view.width / WIDTH), view.top + round(y * view.width / WIDTH))
        self.target.tap(*point)

    def read(self, image, predicate):
        # On static screens retain only the interpretation of identical pixels.
        # The tap position and account still come from the current IPC frame.
        key = hashlib.blake2s(image.tobytes(), digest_size=12).digest()
        if key != self.ocr_key:
            self.ocr_lines = lines(self.ocr(image))
            self.ocr_key = key
        return predicate(image, self.ocr_lines)

    def await_page(self, match, stage, seconds=7):
        deadline = time.monotonic() + seconds
        while not self.stop.is_set() and time.monotonic() < deadline:
            raw = self.target.screenshot(timeout=3)
            image, view = normalized(raw)
            if value := match(raw, image):
                return value, view
            self.stop.wait(POLL_SECONDS)
        if self.stop.is_set():
            raise InterruptedError()
        raise PageTimeout(f"{stage}未确认，打熊已停止")

    def formation(self, raw, image):
        controls = match_beast_rally_formation_controls(raw)
        if controls.state is BeastRallyState.FORMATION:
            point = controls.point
        else:
            def dispatch_label(current, items):
                if not _in(items, "出征", 65, 250, 8, 78):
                    return None
                button = _in(items, "出征", 510, 750, current.height - 145, current.height - 17)
                if button is None:
                    return None
                r, g, b = _color(current, (button.x - 15, button.y))
                if 25 < r < 145 and g > r + 36 and b > g + 31:
                    return button.point
                return None
            point = self.read(image, dispatch_label)
            if point is None:
                return None
            point = map_content_point(point, image.size, raw)
        presets = bear_presets(image.crop((0, 65, WIDTH, 232)), top=65, allow_warning=True)
        return (point, presets) if presets else None

    def dispatch(self, card, expires, receipt, *, room=None):
        (_, available), view = self.await_page(self.formation, "可用的「熊」编队")
        for index, preset in enumerate(sorted(available, key=lambda item: (item.warned, not item.selected))):
            def same_slot(raw, image):
                result = self.formation(raw, image)
                if result:
                    return next((item for item in result[1]
                                 if abs(item.point[0] - preset.point[0]) <= 6), None)
                return None

            slot = preset
            if index:
                slot, view = self.await_page(same_slot, "当前可用的「熊」编队")
            if not slot.selected:
                self.tap(slot.point, view)

            def selected(raw, image):
                result = self.formation(raw, image)
                if result is None or not any(item.selected and abs(item.point[0] - preset.point[0]) <= 6
                                             for item in result[1]):
                    return None
                capacity = read_daily_gather_formation_capacity(raw)
                if capacity and capacity.selected_troops > 0:
                    return result[0], capacity.selected_troops
                return None

            (dispatch, troops), _ = self.await_page(selected, "「熊」编队已选中且有兵力")
            if room is None or troops <= room:
                break
        else:
            raise TroopLimit()
        if self.input_stopped():
            raise InterruptedError()
        count = record_dispatch(self.day, card.key, expires=expires, path=self.path)
        try:
            self.tap(dispatch)
        except InterruptedError:
            record_dispatch(self.day, card.key, expires=expires, rejected=True, path=self.path)
            raise
        def outcome(raw, image):
            if self.read(image, troop_limit_dialog):
                return "rejected"
            return receipt(raw, image)

        status, _ = self.await_page(outcome, "出征后返回集结列表")
        if status == "rejected":
            record_dispatch(self.day, card.key, expires=expires, rejected=True, path=self.path)
            raise TroopLimit(modal=True)
        record_dispatch(self.day, card.key, expires=expires, confirm=status == "confirmed",
                        submitted=status == "list", path=self.path)
        self.ignored[card.key] = expires
        self.report(f"打熊出征已提交 {count}/{LIMIT}")
        return count, status
