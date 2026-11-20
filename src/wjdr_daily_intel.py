"""Account-scoped intent for the Intel expert's non-repeatable input."""
from __future__ import annotations

import hashlib
import json

import numpy as np

import wjdr_backend as backend
from wjdr_backend import PetDispatchLedger
from wjdr_daily_visuals import _find


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
