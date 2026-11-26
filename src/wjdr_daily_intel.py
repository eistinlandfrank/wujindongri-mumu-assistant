"""Account-scoped intent for the Intel expert's non-repeatable input."""
from __future__ import annotations

import hashlib
import json
import time
from collections.abc import Callable

import numpy as np
from PIL import Image

import wjdr_backend as backend
from wjdr_backend import PetDispatchLedger
from wjdr_daily_visuals import _find, intel_expert, intel_expert_maybe_visible


def match_intel_wilderness_entry(image, threshold: float):
    """Look for the current Intel shortcut only on an anchored Wilderness map."""
    town, _ = backend.match_daily_world_town_entry(image, threshold)
    if town is None:
        return None, 0.0
    point, score = _find(image, "daily_intel_wilderness_entry.png", (.87, .62, 1., .73), .97, 12.)
    if point is not None:
        return point, score
    return backend.match_daily_intel_map_entry(image, threshold)


def match_intel_execute_all(image, threshold: float):
    """Require the enabled Execute All label and its ordinary stamina icon."""
    if not backend.match_daily_intel_map_page(image, threshold)[0]:
        return None
    label, _ = _find(image, "daily_intel_execute_label.png", (.12, .905, .39, .944), .95, 17.)
    icon, _ = _find(image, "daily_intel_execute_stamina.png", (.17, .933, .31, .979))
    if label is None or icon is None:
        return None
    return label


def match_intel_batch_running(image, threshold: float) -> bool:
    return bool(backend.match_daily_intel_map_page(image, threshold)[0] and
                _find(image, "daily_intel_execute_running.png", (.10, .906, .43, .968), .94, 17.)[0])


def match_intel_claim_all(image, threshold: float):
    """The grey zero-count Claim All control has no action coordinate."""
    if not backend.match_daily_intel_map_page(image, threshold)[0]:
        return None
    return _find(image, "daily_intel_claim_label.png", (.60, .905, .86, .966), .94, 17.)[0]


def match_selected_hero_battle(image, threshold: float):
    """Require the setup page and all five green selected-hero checks."""
    auto, battle, score = backend.match_daily_intel_hero_setup(image, threshold)
    if not auto or not battle:
        return None, score
    pixels = np.asarray(image.convert("RGB"))
    height, width = pixels.shape[:2]
    for x in (.125, .3125, .5, .6875, .875):
        patch = pixels[int(height * .635):int(height * .68),
                       int(width * (x - .035)):int(width * (x + .035))].astype(np.float32)
        green = ((patch[:, :, 1] > 125) & (patch[:, :, 1] > patch[:, :, 0] * 1.3)
                 & (patch[:, :, 1] > patch[:, :, 2] * 1.3))
        if green.mean() < .12:
            return None, score
    return battle, score


def match_hero_victory(image, threshold: float):
    """Require the victory banner and full exit phrase before a safe exit."""
    old = backend.match_daily_intel_hero_victory(image, threshold)
    if old[0]:
        return old
    victory, vscore = backend._match_daily_task_template(
        image, backend.BUILTIN_DAILY_INTEL_HERO_VICTORY_ASSET,
        backend.BUILTIN_DAILY_INTEL_HERO_VICTORY_TEMPLATE_NAME,
        max(.98, float(threshold)), backend._relative_region(image, .20, .20, .80, .60))
    phrase, pscore = _find(image, "daily_intel_hero_exit_generic.png",
                           (.15, .72, .85, .96), .96, 12.0)
    if not victory or not phrase:
        return None, max(vscore, pscore)
    return backend.map_content_point((90, 1200), backend.BUILTIN_DAILY_TASK_REFERENCE_SIZE, image), min(vscore, pscore)


def match_hero_preview_any_level(image, threshold: float):
    """Prove a Hero Journey title and its ordinary blue View button."""
    title, title_score = _find(image, "daily_intel_hero_title_generic.png",
                               (.20, .18, .80, .38), .96, 12.0)
    if not title:
        return None, title_score
    action, action_score = backend._match_daily_task_template(
        image, backend.BUILTIN_DAILY_INTEL_HERO_PREVIEW_GO_ASSET,
        backend.BUILTIN_DAILY_INTEL_HERO_PREVIEW_GO_TEMPLATE_NAME,
        max(.98, float(threshold)), backend._relative_region(image, .20, .58, .80, .78))
    if not action or abs(title[0] - action[0]) > backend.content_viewport(image).width * .18:
        return None, action_score
    if not backend._daily_template_integrity_is_valid(
        image, backend.BUILTIN_DAILY_INTEL_HERO_PREVIEW_GO_ASSET,
        backend.BUILTIN_DAILY_INTEL_HERO_PREVIEW_GO_TEMPLATE_NAME, action,
        min_luma_ratio=backend.DAILY_ACTION_MIN_LUMA_RATIO,
        min_chroma_ratio=backend.DAILY_ACTION_MIN_CHROMA_RATIO,
        max_colour_distance=backend.DAILY_ACTION_MAX_COLOUR_DISTANCE, strict_action=True,
    ):
        return None, action_score
    return action, min(title_score, action_score)


class IntelExpertLedger(PetDispatchLedger):
    """Allow another expert only after the preceding action was confirmed.

    The caller must hold the stable account lease. A pending or damaged record
    blocks across restarts and date changes.
    """

    def __init__(self, identity: str, day: str, directory=None) -> None:
        super().__init__(identity, day, directory)
        digest = hashlib.sha256(identity.encode("utf-8")).hexdigest()[:24]
        self.path = self.path.with_name(f"daily_intel_expert_{digest}.json")

    def available(self) -> bool:
        try:
            data = self._read()
        except (OSError, ValueError, TypeError, json.JSONDecodeError):
            return False
        return data is None or data["status"] == "confirmed"


class IntelBatchLedger(IntelExpertLedger):
    """Keep each non-repeatable batch action separate from the expert input."""

    def __init__(self, identity: str, day: str, action: str, directory=None) -> None:
        super().__init__(identity, day, directory)
        self.path = self.path.with_name(self.path.name.replace("intel_expert_", f"intel_batch_{action}_"))


def run_intel_expert(
    first: Image.Image,
    capture: Callable[[], Image.Image],
    tap: Callable[[int, int], None],
    wait: Callable[[float], bool],
    threshold: float,
    ledger: IntelExpertLedger,
    trace: Callable[[str], None],
) -> tuple[str, Image.Image]:
    """Allow the portrait to settle while preserving two consecutive proofs."""
    if not ledger.available():
        return "pending", first
    start = time.monotonic()
    frame = first
    prior = None
    best = 0.0
    samples = 0
    absent = 0
    seen = False
    while not wait(0) and time.monotonic() - start < 4.0:
        samples += 1
        if backend.match_daily_intel_map_page(frame, threshold)[0]:
            point, score = intel_expert(frame)
            best = max(best, score)
            if point is not None:
                seen = True
                absent = 0
                if prior and max(abs(a - b) for a, b in zip(prior, point)) <= 16:
                    if wait(0) or not ledger.reserve():
                        return "pending", frame
                    trace(f"情报专家双帧确认，采样={samples}，最高分={best:.3f}，坐标={point}。")
                    tap(*point)
                    break
                prior = point
            else:
                prior = None
                seen = seen or intel_expert_maybe_visible(frame)
                absent = 0 if seen else absent + 1
                if absent >= 2 and time.monotonic() - start >= .35:
                    trace(f"情报地图已双帧确认无可用专家，采样={samples}。")
                    return "absent", frame
        else:
            prior = None
            absent = 0
        if not prior and wait(.08):
            return "stopped", frame
        frame = capture()
    else:
        trace(f"情报专家未稳定，采样={samples}，最高分={best:.3f}，未提交点击。")
        return ("stopped" if wait(0) else "unstable"), frame

    cleared = 0
    deadline = time.monotonic() + 8.0
    while not wait(0) and time.monotonic() < deadline:
        frame = capture()
        gone = (backend.match_daily_intel_map_page(frame, threshold)[0]
                and not intel_expert_maybe_visible(frame))
        cleared = cleared + 1 if gone else 0
        if cleared >= 2:
            return ("activated" if ledger.confirm() else "pending"), frame
        if not gone and wait(.08):
            break
    return "pending", frame


def run_intel_bulk_action(
    first: Image.Image,
    capture: Callable[[], Image.Image],
    tap: Callable[[int, int], None],
    wait: Callable[[float], bool],
    threshold: float,
    execute_ledger: IntelBatchLedger,
    claim_ledger: IntelBatchLedger,
    *, settle: bool = False,
) -> str:
    """Handle one exact bulk action and give the Daily scanner back control."""
    def same_action(first_point, second_point) -> bool:
        return bool(first_point and second_point and
                    max(abs(x - y) for x, y in zip(first_point, second_point)) <= 12)

    def observe(matcher, timeout: float):
        deadline = time.monotonic() + timeout
        prior = None
        while time.monotonic() < deadline and not wait(0):
            frame = capture()
            current = matcher(frame)
            if current and current == prior:
                return frame
            prior = current
            if wait(.08):
                break
        return None

    def action(frame):
        claim = match_intel_claim_all(frame, threshold)
        if claim:
            return "claim", claim
        if match_intel_batch_running(frame, threshold):
            return "running", None
        execute = match_intel_execute_all(frame, threshold)
        return ("execute", execute) if execute else None

    prior = action(first)
    if prior is None and not settle:
        return "unsupported"
    ready_by = time.monotonic() + 3.0
    while not wait(0) and time.monotonic() < ready_by:
        current = action(capture())
        if (current and prior and current[0] == prior[0]
                and (current[0] == "running" or same_action(prior[1], current[1]))):
            kind, point = current
            break
        prior = current
        if wait(.08):
            return "unconfirmed"
    else:
        return "unstable"

    if kind == "claim":
        if wait(0) or not claim_ledger.available() or not claim_ledger.reserve():
            return "unconfirmed"
        tap(*point)

        def reward_result(frame):
            result = backend.diagnose_daily_abnormal_exit(frame, threshold)
            return result.point if result.kind is backend.DailyAbnormalExitKind.REWARD_TAP_ANYWHERE else None

        result = observe(reward_result, 10.0)
        if result is None or wait(0):
            return "unconfirmed"
        # The bulk reward grid can swallow a tap beside its items. The exit
        # instruction itself is below that grid and was verified in game.
        tap(*backend.map_content_point((720, 2366), (1440, 2560), result))
        settled = observe(lambda frame: backend.match_daily_intel_map_page(frame, threshold)[0]
                          and match_intel_claim_all(frame, threshold) is None, 8.0)
        return "claimed" if settled is not None and claim_ledger.confirm() else "unconfirmed"

    if kind == "running":
        return "running"
    if wait(0) or not execute_ledger.available() or not execute_ledger.reserve():
        return "unconfirmed"
    tap(*point)
    accepted = observe(lambda frame: match_intel_batch_running(frame, threshold)
                       or match_intel_claim_all(frame, threshold), 8.0)
    return "started" if accepted is not None and execute_ledger.confirm() else "unconfirmed"
