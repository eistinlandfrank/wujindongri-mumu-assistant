"""Claimable Alliance Chests and Activity Incentives on a leased device."""

from __future__ import annotations

import time

import numpy as np

from wjdr_backend import AlliancePage, detect_alliance_page, map_content_point
from wjdr_backend import match_daily_hero_recruit_summary_exit
from wjdr_daily_visuals import _find


def _anchor(frame, name, region):
    return _find(frame, f"daily_alliance_{name}.png", region, .93, 22.)[0]


def _red_badge(frame, region):
    width, height = frame.size
    left, top, right, bottom = region
    pixels = np.asarray(frame.crop((round(left * width), round(top * height),
                                    round(right * width), round(bottom * height))).convert("RGB"), dtype=np.int16)
    red, green, blue = pixels.transpose(2, 0, 1)
    return ((red > 140) & (green * 2 < red) & (blue * 2 < red)).mean() > .08


def _chest_header(frame):
    return _anchor(frame, "chest_header", (.10, .006, .36, .056))


def _incentive_header(frame):
    return _anchor(frame, "incentive_header", (.10, .006, .36, .056))


def _same_point(first, second):
    return first is not None and second is not None and max(abs(a - b) for a, b in zip(first, second)) <= 9


def run_alliance_rewards(capture, tap, swipe, wait, log, threshold=.90):
    """Visit marked rewards from Alliance Home and return to the same page."""
    deadline = time.monotonic() + 26.0

    def point(frame, x, y):
        return map_content_point((x, y), (1440, 2560), frame)

    def pair(probe, seconds=1.8):
        end = min(deadline, time.monotonic() + seconds)
        prior = None
        while time.monotonic() < end and not wait(0):
            frame = capture()
            current = probe(frame)
            if _same_point(prior, current):
                return frame, current
            prior = current
            if wait(.10):
                break
        return None

    def home(frame):
        return point(frame, 78, 75) if detect_alliance_page(frame, threshold).page is AlliancePage.ALLIANCE_HOME else None

    def send(stage):
        if stage is None or wait(0):
            return False
        tap(*stage[1])
        return True

    def exit_reward():
        return send(pair(lambda frame: match_daily_hero_recruit_summary_exit(
            frame, threshold, at_phrase=True)[0], 5.0))

    def chest_entry(frame):
        if home(frame) and _red_badge(frame, (.922, .473, .984, .509)):
            return _anchor(frame, "chest_entry", (.70, .485, .94, .55))
        return None

    def top_chest(frame):
        if _chest_header(frame) and _red_badge(frame, (.598, .104, .662, .144)):
            return _anchor(frame, "top_chest", (.35, .13, .66, .235))
        return None

    trophy_badge = (.436, .275, .506, .303)
    gift_badge = (.916, .274, .974, .301)

    def select_tab(frame, badge, x):
        return point(frame, x, 791) if _chest_header(frame) and _red_badge(frame, badge) else None

    def trophy_button(frame):
        if _chest_header(frame) and _anchor(frame, "trophy_selected", (.13, .28, .44, .34)):
            return _anchor(frame, "trophy_bulk", (.31, .916, .69, .978))
        return None

    def gift_tab(frame):
        return _chest_header(frame) and _anchor(frame, "gift_selected", (.59, .28, .92, .34))

    def gift_button(frame):
        return _anchor(frame, "gift_claim", (.75, .44, .97, .84)) if gift_tab(frame) else None

    def incentive_notice(frame):
        if home(frame) and _anchor(frame, "incentive_notice", (.54, .87, .64, .946)):
            return point(frame, 720, 2410)
        return None

    def weekly(frame):
        if _incentive_header(frame) and _anchor(frame, "incentive_weekly", (.25, .56, .55, .62)):
            return point(frame, 720, 930)
        return None

    def weekly_exit(frame):
        if _anchor(frame, "weekly_title", (.30, .22, .71, .33)):
            return _anchor(frame, "weekly_exit", (.29, .899, .72, .963))
        return None

    def personal(frame):
        if (_incentive_header(frame) and _red_badge(frame, (.942, .612, .979, .638))
                and _anchor(frame, "incentive_personal", (.32, .626, .73, .691))):
            return point(frame, 706, 1746)
        return None

    if send(pair(chest_entry)):
        if not pair(_chest_header, 4.0):
            return False
        if send(pair(lambda frame: select_tab(frame, trophy_badge, 382))):
            if send(pair(trophy_button, 3.0)):
                if not exit_reward() or not pair(_chest_header, 3.0):
                    return False
                log("联盟奖励：已一键领取战利品宝箱。")
        if send(pair(top_chest)):
            if not exit_reward() or not pair(_chest_header, 3.0):
                return False
            log("联盟奖励：已领取顶部红标大箱。")
        if send(pair(lambda frame: select_tab(frame, gift_badge, 1059))):
            if not pair(gift_tab, 3.0):
                return False
            scrolls = 0
            while time.monotonic() < deadline and not wait(0):
                # A clear badge ends the list immediately. Scroll only while
                # there is a confirmed remaining count and the visible cards
                # have no claimable button.
                if not pair(lambda frame: select_tab(frame, gift_badge, 1059), .65):
                    break
                claim = pair(gift_button, .70)
                if claim is not None:
                    if not send(claim):
                        return False
                    previous = claim[1]
                    if not pair(lambda frame: gift_tab(frame) and not _same_point(previous, gift_button(frame))
                                and point(frame, 78, 75), 2.0):
                        return False
                    log("联盟奖励：已领取一项盟友赠礼。")
                    continue
                viewport = pair(gift_tab, .65)
                if viewport is None or wait(0):
                    return False
                if scrolls >= 3:
                    log("联盟奖励：盟友赠礼仍有红标，本轮达到列表检查上限。")
                    break
                before = viewport[0]
                swipe(point(before, 840, 2040), point(before, 840, 1250))
                scrolls += 1
                if wait(.35):
                    return False
                after = capture()
                if not gift_tab(after):
                    return False
                x, y = after.size
                box = (round(x * .21), round(y * .47), round(x * .69), round(y * .82))
                delta = np.abs(np.asarray(before.crop(box), dtype=np.int16) - np.asarray(after.crop(box), dtype=np.int16))
                if delta.mean() <= 2.0:
                    break
        if not send(pair(lambda frame: point(frame, 78, 75) if _chest_header(frame) else None)) or not pair(home, 4.0):
            return False

    if send(pair(incentive_notice)):
        if not pair(_incentive_header, 4.0):
            return False
        if send(pair(weekly)):
            if not send(pair(weekly_exit, 5.0)) or not pair(_incentive_header, 3.0):
                return False
            log("联盟奖励：已领取活跃激励每周结算。")
        if send(pair(personal)):
            if not exit_reward() or not pair(_incentive_header, 3.0):
                return False
            log("联盟奖励：已领取个人活跃激励宝箱。")
        if not send(pair(lambda frame: point(frame, 78, 75) if _incentive_header(frame) else None)):
            return False
    return pair(home, 3.0) is not None
