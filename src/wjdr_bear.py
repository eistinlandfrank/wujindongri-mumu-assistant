"""Alliance-chat Polar Terror recognition and a bounded join flow."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
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
    content_viewport, match_beast_rally_formation_controls, match_red_packet_chat_entry,
    read_daily_gather_formation_capacity, resource_path,
)

LIMIT = 6
ZONE = timezone(timedelta(hours=8))
EVENT_SECONDS = 30 * 60
POLL_SECONDS = 0.08
WIDTH = 786
CHAT_TEXT = "快来集结一起击败变异巨熊"
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


def _read_ledger(path, day):
    if not path.exists():
        return []
    payload = json.loads(path.read_text("utf-8"))
    records = payload["records"]
    if (not isinstance(records, list) or len(records) > LIMIT
            or any(not isinstance(record, dict) or record.get("state") not in {"sent", "confirmed", "checked"}
                   for record in records)):
        raise ValueError("打熊出征记录异常")
    # An unknown submission from a prior day still needs manual reconciliation.
    if payload["day"] != day and all(record["state"] != "sent" for record in records):
        return []
    return records


def ledger(path, day):
    records = _read_ledger(path, day)
    if any(record["state"] == "sent" for record in records):
        raise ValueError("有一次打熊出征尚未核实，请先在游戏中核对出征结果")
    return records


@_serialized_account_write
def record_dispatch(day, key, *, expires, confirm=False, path):
    records = _read_ledger(path, day)
    pending = [record for record in records if record["state"] == "sent"]
    if confirm:
        if len(pending) != 1 or pending[0]["key"] != key:
            raise ValueError("打熊出征回执与记录不符")
        pending[0]["state"] = "confirmed"
    else:
        if pending or len(records) >= LIMIT or any(
            record["key"] == key and record["expires"] > time.time() for record in records
        ):
            raise ValueError("打熊出征已达上限、已有相同集结或有待核实记录")
        records.append({"key": key, "state": "sent", "expires": expires})
    _atomic_json_write(path, {"day": day, "records": records})
    return len(records)


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
    raw: str = ""

    @property
    def point(self):
        return (self.x + self.right) // 2, self.y


def lines(result):
    items = []
    for row in result:
        if words := row.get("words"):
            items.append(Line(compact(row["text"]), round(min(w["x"] for w in words)),
                              round(sum(w["y"] + w["height"] / 2 for w in words) / len(words)),
                              round(max(w["x"] + w["width"] for w in words)), row["text"]))
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


def chat_page(image, items):
    """The title alone also appears in world/personal chat and announcements."""
    if not _in(items, "聊天", 50, 220, 10, 75):
        return None
    alliance = _in(items, "联盟", 285, 475, 74, 155)
    if alliance is None:
        return None
    r, g, b = _color(image, (alliance.x - 24, alliance.y))
    if not (r > 190 and g > 210 and b > 217):
        return "alliance_tab", alliance.point
    if _in(items, "联盟公告:", 15, 210, 170, 255):
        box = (670, 175, WIDTH, 270)
        scores = cv2.matchTemplate(np.asarray(image.crop(box)), _template("bear_chat_notice_close"),
                                   cv2.TM_CCOEFF_NORMED)
        _, score, _, (x, y) = cv2.minMaxLoc(scores)
        if score >= 0.91:
            return "notice", (box[0] + x + 18, box[1] + y + 18)
    messages = _in(items, "聊天", 95, 295, 165, 250)
    if messages is None:
        return None
    r, g, b = _color(image, (40, messages.y))
    if not (r > 100 and g > 155 and b > 205):
        return "messages_tab", messages.point
    return "messages", None


def _chat_nickname(row):
    # The rank label is gold and precedes the player name. OCR can read 10 as ℃.
    raw = unicodedata.normalize("NFKC", row.raw or row.text)
    match = re.match(r"^.{0,9}?统\s*帅\s*(?:10|[1-9]|°C)(?=\s|[^\d])\s*", raw)
    return nickname(raw[match.end():] if match else raw)


@dataclass(frozen=True)
class Card:
    leader: str
    coords: tuple[int, int]
    point: tuple[int, int]

    @property
    def key(self):
        return f"{self.leader}|{self.coords[0]},{self.coords[1]}"


def chat_cards(image, items, leaders):
    cards = []
    for title in reversed(sorted(items, key=lambda row: row.y)):
        if title.text != "发起集结" or not (125 <= title.x <= 215 and 260 < title.y < image.height - 90):
            continue
        senders = [row for row in items if 125 <= row.x < 380 and 32 <= title.y - row.y <= 72]
        if len(senders) != 1:
            continue
        leader = _chat_nickname(senders[0])
        if leader not in leaders:
            continue
        if not _in(items, CHAT_TEXT, 125, 225, title.y + 42, title.y + 86):
            continue
        location = next((COORDINATES.search(row.text) for row in items
                         if 125 <= row.x <= 270 and 80 <= row.y - title.y <= 120
                         and COORDINATES.search(row.text)), None)
        if location is None:
            continue
        r, g, b = _color(image, (504, title.y + 104))
        white = _color(image, (153, title.y)).min() > 214
        if white and 20 <= r <= 120 and g > r + 34 and b > g + 27:
            cards.append(Card(leader, tuple(map(int, location.groups())), (490, title.y + 88)))
    return cards


@dataclass(frozen=True)
class Detail:
    join: tuple[int, int] | None
    present: bool
    seconds: int


def rally_detail(image, items, card, player):
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
    coordinate_present = any(
        (location := COORDINATES.search(row.text)) and tuple(map(int, location.groups())) == card.coords
        and row.right > 540 and leader_label.y + 35 < row.y < 460 for row in items
    )
    if not (target_present and coordinate_present):
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
                return Detail(row.point, False, seconds)
    return Detail(None, present, seconds)


@dataclass(frozen=True)
class Preset:
    point: tuple[int, int]
    selected: bool


def _white(rgb):
    return ((rgb.min(axis=2) >= 195) & (np.ptp(rgb, axis=2) < 55)).astype(np.uint8)


@lru_cache(maxsize=1)
def _preset_templates():
    with Image.open(resource_path("assets/bear_preset_label.png")) as glyph:
        mask = np.asarray(glyph.convert("L"))
    samples = np.split(mask, mask.shape[0] // 29)
    return [cv2.resize(sample, None, fx=scale, fy=scale, interpolation=cv2.INTER_NEAREST)
            for sample in samples for scale in (0.84, 0.92, 1.0, 1.08, 1.12, 1.16)]


def bear_presets(strip, *, top=0):
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
        if int(warning.sum()) > 30:
            continue
        tile = rgb[cy-31:cy-9, cx-23:cx+24]
        gold = (tile[:, :, 0] > 185) & (tile[:, :, 1] > 147) & (tile[:, :, 2] < 135)
        selected = float(gold.mean()) > 0.12
        found.append(Preset((cx, top + cy - 17), selected))
    return sorted(found, key=lambda preset: preset.point)


@lru_cache(maxsize=3)
def _template(name):
    with Image.open(resource_path(f"assets/{name}.png")) as source:
        return np.asarray(source.convert("RGB"))


def latest_button(image):
    width, height = image.size
    region = np.asarray(image.crop((width - 90, height - 185, width, height)))
    template = _template("bear_chat_latest")
    scores = cv2.matchTemplate(region, template, cv2.TM_CCOEFF_NORMED)
    _, score, _, (x, y) = cv2.minMaxLoc(scores)
    if score >= 0.91:
        template_height, template_width = template.shape[:2]
        return width - 90 + x + template_width // 2, height - 185 + y + template_height // 2
    return None


def _detail_title_visible(image):
    header = np.asarray(image.crop((66, 6, 285, 100)))
    template = _template("bear_rally_title")
    return cv2.matchTemplate(header, template, cv2.TM_CCOEFF_NORMED).max() >= 0.89


class PageTimeout(ValueError):
    pass


class BearFlow:
    def __init__(self, target, stop, ocr, settings, path, report):
        self.target = target
        self.stop = stop
        self.ocr = ocr
        self.settings = settings
        self.path = path
        self.report = report
        self.day = datetime.now(ZONE).date().isoformat()
        self.ignored = {}
        self.ocr_key = None
        self.ocr_lines = []

    def tap(self, point, view=None):
        if self.stop.is_set():
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

    def chat(self, raw, image):
        state = self.read(image, chat_page)
        if state:
            kind, point = state
            if kind == "messages":
                return kind, latest_button(image)
            return kind, point
        point, _ = match_red_packet_chat_entry(raw, 0.93)
        return ("entry", point) if point else None

    def open_chat(self):
        sent = set()
        while True:
            (kind, point), view = self.await_page(
                lambda raw, image: (result if (result := self.chat(raw, image))
                                    and result[0] not in sent else None), "联盟聊天页")
            if kind == "messages":
                if point:
                    self.tap(point, view)
                    self.await_page(lambda raw, image: self.read(image, chat_page)
                                    == ("messages", None) and not latest_button(image), "聊天底部")
                return
            sent.add(kind)
            self.tap(point, None if kind == "entry" else view)

    def card(self, image):
        def match(current, items):
            if chat_page(current, items) != ("messages", None) or latest_button(current):
                return None
            return next((item for item in chat_cards(current, items, self.settings["names"])
                         if self.ignored.get(item.key, 0) <= time.time()), None)
        return self.read(image, match)

    def formation(self, raw, image):
        controls = match_beast_rally_formation_controls(raw)
        if controls.state is not BeastRallyState.FORMATION:
            return None
        presets = bear_presets(image.crop((0, 65, WIDTH, 193)), top=65)
        return (controls.point, presets) if presets else None

    def join(self, card, view):
        self.tap(card.point, view)
        def detail(raw, image):
            return self.read(image, lambda current, items:
                             rally_detail(current, items, card, self.settings["player"]))

        try:
            page, view = self.await_page(detail, "同一队长、坐标和巨熊目标", seconds=3)
        except PageTimeout:
            # An expired chat card may leave the page unchanged. Observe
            # two still-safe chat frames and never tap this unknown card again.
            for _ in range(2):
                raw = self.target.screenshot(timeout=3)
                image, _ = normalized(raw)
                if self.read(image, chat_page) != ("messages", None):
                    raise
            self.ignored[card.key] = float("inf")
            self.report("集结卡未打开，已跳过这张卡并继续监听")
            return
        if page.join is None:
            self.ignored[card.key] = time.time() + max(12, page.seconds + 5)
            self.back()
            return
        expires = time.time() + page.seconds + 5
        self.tap(page.join, view)
        (_, presets), view = self.await_page(self.formation, "可用的「熊」编队")
        preset = next((item for item in presets if item.selected), None)
        if preset is None:
            preset = presets[0]
            self.tap(preset.point, view)
        def selected(raw, image):
            result = self.formation(raw, image)
            if result is None or not any(item.selected and abs(item.point[0] - preset.point[0]) <= 5
                                         for item in result[1]):
                return None
            capacity = read_daily_gather_formation_capacity(raw)
            return result[0] if capacity and capacity.selected_troops > 0 else None

        dispatch, _ = self.await_page(selected, "「熊」编队已选中且有兵力")
        if self.stop.is_set():
            raise InterruptedError()
        count = record_dispatch(self.day, card.key, expires=expires, path=self.path)
        self.tap(dispatch)
        self.await_page(lambda raw, image: (result if (result := detail(raw, image))
                                            and result.present else None), "出征回执（本人进入同一集结名单）")
        record_dispatch(self.day, card.key, expires=expires, confirm=True, path=self.path)
        self.ignored[card.key] = expires
        self.report(f"打熊出征已确认 {count}/{LIMIT}")
        if count < LIMIT:
            self.back()

    def back(self):
        if self.stop.is_set():
            raise InterruptedError()
        self.target.back()
        self.await_page(lambda raw, image: (page if (page := self.read(image, chat_page))
                                            and page[0] in {"messages", "notice"} else None),
                        "返回联盟聊天页")
        self.open_chat()

    def run(self, seconds=EVENT_SECONDS):
        prior = ledger(self.path, self.day)
        self.ignored.update((record["key"], record["expires"]) for record in prior)
        if len(prior) >= LIMIT:
            self.report("本场已达到 6 次出征上限")
            return
        if not self.target.foreground_is_game():
            raise ValueError("请将无尽冬日留在 MuMu 前台")
        self.open_chat()
        self.report(f"监听联盟聊天 · 已出征 {len(prior)}/{LIMIT}")
        deadline = time.monotonic() + seconds
        while not self.stop.is_set() and time.monotonic() < deadline:
            raw = self.target.screenshot(timeout=3)
            image, view = normalized(raw)
            if card := self.card(image):
                self.join(card, view)
                if len(ledger(self.path, self.day)) >= LIMIT:
                    return
            else:
                self.stop.wait(POLL_SECONDS)
