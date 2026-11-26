"""Bounded Expedition idle-reward controller; caller owns the account lease."""
from __future__ import annotations

import time
import hashlib
from collections.abc import Callable
from PIL import Image
from wjdr_backend import PetDispatchLedger
from wjdr_daily_visuals import (
    expedition_back, expedition_city_entry, expedition_claim, expedition_disabled_back, expedition_idle_claim,
)


class ExpeditionClaimLedger(PetDispatchLedger):
    """Independent per-account/day intent with the same durable fail-closed rules."""

    def __init__(self, identity: str, day: str, directory=None) -> None:
        super().__init__(identity, day, directory)
        digest = hashlib.sha256(identity.encode("utf-8")).hexdigest()[:24]
        self.path = self.path.with_name(f"daily_expedition_claim_{digest}.json")


def run_expedition_claim(
    capture: Callable[[], Image.Image], tap: Callable[[int, int], None],
    stopped: Callable[[], bool], wait: Callable[[float], bool],
    city: Callable[[Image.Image], bool], reward_exit: Callable[[Image.Image], tuple[int, int] | None],
    reserve: Callable[[], bool], confirm: Callable[[], bool],
    log: Callable[[str], None], timeout: float = 24.0,
    *, trace: Callable[[str], None] | None = None,
) -> str:
    """One entry, one chest, one idle claim, one exit, one back; never retry input.

    Reserve must durably fail closed across restarts before the actual reward
    claim; confirm is called only after the correlated reward result appears.
    A caller must bind and lease the account throughout this function.
    """
    stage = "city"
    prior = None
    streak = 0
    city_without_entry_streak = 0
    chest_disabled_streak = 0
    background_chest = False
    returned_city_streak = 0
    deadline = time.monotonic() + min(max(timeout, 0.0), 24.0)
    score: float | None = None
    while not stopped() and time.monotonic() < deadline:
        try:
            frame = capture()
            point = None
            score = None
            if stage == "city":
                city_visible = city(frame)
                if city_visible:
                    point, score = expedition_city_entry(frame)
                if city_visible and point is None:
                    city_without_entry_streak += 1
                    if city_without_entry_streak >= 2:
                        if trace:
                            trace(f"探险识别：两帧均为主城，入口未匹配，末帧分数={score:.3f}。")
                        log("主城已双帧确认，探险收益入口当前不可用；继续其他每日任务。")
                        return "unavailable"
                else:
                    city_without_entry_streak = 0
            elif stage == "chest":
                point, score = expedition_claim(frame)
                disabled_back = expedition_disabled_back(frame) if point is None else None
                chest_disabled_streak = chest_disabled_streak + 1 if disabled_back else 0
                if chest_disabled_streak >= 2 and not stopped():
                    if trace:
                        trace(f"探险识别：两帧确认灰色宝箱，返回点={disabled_back}。")
                    tap(*disabled_back)
                    stage = "done"
                    background_chest = True
                    log("探险关卡宝箱当前为灰色；已返回主城。")
                    continue
            elif stage == "idle":
                point, score = expedition_idle_claim(frame)
            elif stage == "result":
                point = reward_exit(frame)
            elif stage == "back":
                point, score = expedition_back(frame)
            elif stage == "done":
                returned_city_streak = returned_city_streak + 1 if city(frame) else 0
                if returned_city_streak >= 2:
                    return "unavailable" if background_chest else "claimed"
            if point is not None and prior is not None and max(abs(a-b) for a,b in zip(point, prior)) <= 4:
                streak += 1
            elif point is not None:
                prior, streak = point, 1
            else:
                prior, streak = None, 0
            if streak >= 2 and point is not None:
                old = stage
                if trace:
                    confidence = f"，末帧分数={score:.3f}" if score is not None else ""
                    trace(f"探险识别：阶段={old}，坐标={point}，连续帧={streak}/2{confidence}。")
                if old == "idle" and not reserve():
                    log("探险领取记录不可用；未点击收益领取。")
                    return "unconfirmed"
                if old == "result" and not confirm():
                    log("探险收益结果已出现，但领取记录无法确认；未继续输入。")
                    return "unconfirmed"
                stage = {"city": "chest", "chest": "idle", "idle": "result",
                         "result": "back", "back": "done"}[old]
                prior, streak = None, 0
                tap(*point)
                log(f"探险收益：已完成 {old} 步骤。")
                continue
            if wait(.1):
                return "stopped"
        except Exception as exc:
            log(f"探险收益状态未确认：阶段={stage}，{type(exc).__name__}: {exc}。")
            return "unconfirmed"
    if stopped():
        return "stopped"
    if trace:
        confidence = f"{score:.3f}" if score is not None else "无"
        trace(f"探险识别：阶段={stage} 超时，末帧分数={confidence}，连续帧={streak}/2。")
    log(f"探险收益未确认 {stage} 步骤，未重复输入。")
    return "unconfirmed"
