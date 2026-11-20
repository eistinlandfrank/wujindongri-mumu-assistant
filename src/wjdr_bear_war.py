"""Scan the Alliance War rally list while advancing toward its newest end."""

from dataclasses import dataclass
import json
import re
import time

import cv2
import numpy as np

from wjdr_bear import (
    BEAR_TARGET, EVENT_SECONDS, LIMIT, POLL_SECONDS, WAVE_SECONDS, WIDTH, BearFlow, Card,
    PageTimeout, TroopLimit, _color, _detail_title_visible, _in, _template, ledger, nickname, normalized,
    rally_detail, roster_settings, troop_limit_dialog, wave_at, wave_count,
)


def war_page(image, items):
    if not _detail_title_visible(image):
        return False
    if not (_in(items, "集结", 95, 218, 105, 161)
            and _in(items, "单人", 340, 465, 108, 170)
            and _in(items, "活动", 595, 726, 108, 170)):
        return False
    r, g, b = _color(image, (56, 134))
    return r > 185 and g > 205 and b > 215


def world_entry(image):
    box = (int(WIDTH * 0.85), 305, WIDTH, 765)
    area = np.asarray(image.crop(box))
    source = _template("bear_world_rally")
    scores = cv2.matchTemplate(area, source, cv2.TM_CCOEFF_NORMED)
    _, score, _, (x, y) = cv2.minMaxLoc(scores)
    if score < 0.86:
        return None
    return box[0] + x + source.shape[1] // 2, box[1] + y + source.shape[0] // 2


def green_plus(image, name_y):
    left = 658
    top = name_y + 76
    rgb = np.asarray(image.crop((left, top, 753, name_y + 174)))
    tile = _template("bear_war_join_green")
    scores = cv2.matchTemplate(rgb, tile, cv2.TM_CCOEFF_NORMED)
    _, score, _, (x, y) = cv2.minMaxLoc(scores)
    if score < 0.86:
        return None
    h, w = tile.shape[:2]
    r, g, b = rgb[y:y+h, x:x+w].astype(np.int16).transpose(2, 0, 1)
    green = (g > 145) & (g - r > 42) & (g - b > 36)
    return (left + x + w // 2, top + y + h // 2) if green.mean() >= 0.35 else None


@dataclass(frozen=True)
class WarRally:
    card: Card
    seconds: int
    room: int | None = None


def war_rallies(image, items, leaders):
    timers = [row for row in items if row.text.startswith("集结中:")
              and 480 <= row.x <= 580 and 195 < row.y < 1120]
    for timer in sorted(timers, key=lambda item: item.y):
        clock = re.search(r"(\d{1,2}):(\d{2}):(\d{2})", timer.text)
        remaining = 300
        if clock:
            hours, minutes, seconds = map(int, clock.groups())
            remaining = hours * 3600 + minutes * 60 + seconds
        if not 0 < remaining <= 600:
            continue
        for item in items:
            if not (264 <= item.x <= 382 and 40 <= item.y - timer.y <= 94 and item.y < 1054):
                continue
            leader = nickname(item.text.lstrip(".,·、~`'@"))
            if leader not in leaders:
                continue
            if not any(
                BEAR_TARGET.fullmatch(row.text.strip("@《》、`'"))
                and 145 <= row.y - item.y <= 269 and (45 <= row.x < 100 or 255 <= row.x < 370)
                for row in items
            ):
                continue
            point = green_plus(image, item.y)
            if point:
                troop_totals = next((match for row in items if 255 <= row.x <= 410
                                     and 26 <= row.y - item.y <= 72
                                     and (match := re.search(r"(\d{1,3}(?:,\d{3})+)/(\d{1,3}(?:,\d{3})+)", row.text))), None)
                room = None
                if troop_totals:
                    used, total = (int(value.replace(",", "")) for value in troop_totals.groups())
                    room = max(0, total - used)
                if room != 0:
                    yield WarRally(Card(leader, point), remaining, room)


def list_position(image):
    # The static target art moves with the scrolled rows while timers and
    # avatar animations can update in place elsewhere.
    area = image.crop((34, 195, 239, 1200)).resize((21, 101))
    return np.asarray(area, dtype=np.int16)


class WarBearFlow(BearFlow):
    def __init__(self, target, stop, ocr, settings, path, report, *, profile=None):
        super().__init__(target, stop, ocr, settings, path, report)
        self.profile = profile
        self.profile_stamp = None

    def roster(self):
        if self.profile and self.profile.is_file():
            stamp = self.profile.stat().st_mtime_ns
            if stamp != self.profile_stamp:
                data = json.loads(self.profile.read_text("utf-8"))
                updated = roster_settings(data["names"], data["player"])
                if updated["player"] != self.settings["player"]:
                    raise ValueError("本号昵称已更改，请重新启动打熊")
                self.settings = updated
                self.profile_stamp = stamp
        return self.settings["names"]

    def open_war(self):
        def inspect(raw, image):
            if self.read(image, war_page):
                return "list", None
            point = world_entry(image)
            return ("world", point) if point else None

        (page, point), view = self.await_page(inspect, "野外红旗入口或联盟战争列表")
        if page == "world":
            self.tap(point, view)
            self.await_page(lambda raw, image: self.read(image, war_page), "联盟战争集结列表")

    def scroll(self, view, *, toward_bottom=True):
        if self.stop.is_set():
            raise InterruptedError()
        x = view.left + round(578 * view.width / WIDTH)
        start = view.top + round(1137 * view.width / WIDTH)
        end = view.top + round(674 * view.width / WIDTH)
        if not toward_bottom:
            start, end = end, start
        self.target.shell(["input", "swipe", str(x), str(start), str(x), str(end), "150"], timeout=4)

    def board(self, rally, view):
        card = rally.card
        self.tap(card.point, view)

        def transition(raw, image):
            if self.formation(raw, image):
                return "formation", None
            detail = self.read(image, lambda im, items: rally_detail(im, items, card, self.settings["player"]))
            return ("detail", detail) if detail is not None else None

        try:
            (state, detail), view = self.await_page(transition, "绿色加号的编队或巨熊详情", seconds=5)
        except PageTimeout:
            for _ in range(2):
                raw = self.target.screenshot(timeout=3)
                image, _ = normalized(raw)
                if not self.read(image, war_page):
                    raise
            self.ignored[card.key] = time.time() + rally.seconds
            self.report("这次未进入编队，已跳过该集结并继续扫描")
            return
        if state == "detail":
            if not detail.join:
                self.ignored[card.key] = time.time() + rally.seconds
                self.return_to_list()
                return
            self.tap(detail.join, view)
        origin = detail.origin if detail is not None else None

        def receipt(raw, image):
            if self.read(image, war_page):
                return "list"
            page = self.read(image, lambda im, items:
                             rally_detail(im, items, card, self.settings["player"], expected_origin=origin))
            return "confirmed" if page and page.present else None

        try:
            count, status = self.dispatch(card, time.time() + rally.seconds + 5, receipt, room=rally.room)
        except TroopLimit as exc:
            self.ignored[card.key] = time.time() + rally.seconds
            self.report("集结剩余兵力额度不足，已跳过；未改动熊编队")
            if exc.modal:
                point, view = self.await_page(lambda raw, im: self.read(im, troop_limit_dialog), "兵力上限回执")
                self.tap(point, view)
                self.await_page(self.formation, "兵力提示关闭后的出征页")
            self.return_to_list()
            return
        if status != "list":
            self.return_to_list()

    def return_to_list(self):
        if self.stop.is_set():
            raise InterruptedError()
        self.target.back()
        self.open_war()

    def run(self, seconds=EVENT_SECONDS):
        prior = ledger(self.path, self.day, all_waves=True)
        self.ignored.update((record["key"], record["expires"]) for record in prior)
        if not self.target.foreground_is_game():
            raise ValueError("请将无尽冬日留在 MuMu 前台")
        self.open_war()
        wave = wave_at()
        count = wave_count(prior, wave)
        self.report(f"正在逐屏扫描联盟战争集结 · 本轮已出征 {count}/{LIMIT}")
        deadline = time.monotonic() + seconds
        last_scroll = None
        next_scroll = 0.0
        toward_bottom = True
        stationary_since = 0.0
        full_wave = None
        while not self.stop.is_set() and time.monotonic() < deadline:
            now = time.time()
            current = wave_at(now)
            if current != wave:
                wave = current
                count = len(ledger(self.path, self.day, now=now))
                last_scroll = None
                toward_bottom = True
                self.report(f"新一轮打熊 · 本轮已出征 {count}/{LIMIT}")
            if count >= LIMIT:
                latest = len(ledger(self.path, self.day, now=now))
                if latest < LIMIT:
                    count = latest
                    last_scroll = None
                    self.report(f"已更新本轮出征计数 {count}/{LIMIT}")
                    continue
                if full_wave != wave:
                    full_wave = wave
                    self.report("本轮已达 6 次，等下一轮自动续扫")
                self.stop.wait(min(0.25, max(0.02, (wave + 1) * WAVE_SECONDS - now)))
                continue
            raw = self.target.screenshot(timeout=3)
            image, view = normalized(raw)
            if not self.read(image, war_page):
                self.stop.wait(POLL_SECONDS)
                continue
            rally = next((row for row in war_rallies(image, self.ocr_lines, self.roster())
                          if self.ignored.get(row.card.key, 0) <= time.time()), None)
            if rally:
                def confirm(raw, image):
                    if not self.read(image, war_page):
                        return None
                    return next((row for row in war_rallies(image, self.ocr_lines, self.roster())
                                 if row.card.key == rally.card.key
                                 and abs(row.card.point[1] - rally.card.point[1]) <= 5), None)

                fresh = self.target.screenshot(timeout=3)
                current, current_view = normalized(fresh)
                if ready := confirm(fresh, current):
                    self.board(ready, current_view)
                    last_scroll = None
                    toward_bottom = True
                    count = len(ledger(self.path, self.day))
                continue
            position = list_position(image)
            now = time.monotonic()
            changed = last_scroll is None or np.abs(last_scroll-position).mean() > 5
            if changed:
                stationary_since = now
            at_end = not changed and now - stationary_since >= 0.8
            if now >= next_scroll and (changed or at_end):
                if at_end:
                    toward_bottom = not toward_bottom
                self.scroll(view, toward_bottom=toward_bottom)
                last_scroll = position
                next_scroll = time.monotonic() + 0.15
                stationary_since = time.monotonic()
            self.stop.wait(POLL_SECONDS)
