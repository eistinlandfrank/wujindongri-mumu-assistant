"""Named hunting formation and one-team Beast lifecycle, separate from Daily."""
from dataclasses import dataclass
from functools import lru_cache

import cv2
import numpy as np
from PIL import Image

from wjdr_backend import (
    BeastRallyMatch, BeastRallyState, BUILTIN_DAILY_TASK_REFERENCE_SIZE,
    content_viewport, map_content_point, match_beast_rally_formation_controls,
    resource_path,
    _daily_white_numeric_components, _read_daily_numeric_glyph,
)

HUNT_NAME_ASSET = "assets/beast_rally_hunt_name.png"


@dataclass(frozen=True)
class CompactRallyRow:
    owner: str  # own / joined / unknown; only while exact 集结中 is present
    point: tuple[int, int]
    seconds: int | None


@lru_cache(maxsize=1)
def compact_rally_title() -> np.ndarray:
    with Image.open(resource_path("assets/beast_rally_compact_rallying_title.png")) as im:
        return np.asarray(im.convert('L').resize((143,36)))


def read_compact_rally_rows(image: Image.Image) -> tuple[CompactRallyRow, ...]:
    """Recognise owner by the ICON fill, never the universally green bar.

    Restricted to the compact list in a full-screen frame. A blue 返回中
    icon does not imply joined ownership, since the rally phase has ended.
    Empty results are unknown/absent, never proof that our troops returned.
    """
    viewport = content_viewport(image)
    frame = image.crop((viewport.left, viewport.top, viewport.right, viewport.bottom)).resize((1440,2560)).convert('RGB')
    rgb = np.asarray(frame)
    left, top = 90, 390
    mask = cv2.cvtColor(rgb[top:1400, left:440], cv2.COLOR_RGB2GRAY)
    template = compact_rally_title()
    scores = cv2.matchTemplate(mask, template, cv2.TM_CCOEFF_NORMED)
    rows = []
    for _ in range(8):
        _, score, _, (x,y) = cv2.minMaxLoc(scores)
        if score < .92:
            break
        x, y = x+left, y+top
        # User reviewed geometry: title immediately right of the circular
        # rally icon. Exclude the timer below/right from colour samples.
        icon = rgb[y:y+80, max(0,x-92):max(0,x-12)]
        hsv = cv2.cvtColor(icon, cv2.COLOR_RGB2HSV)
        green = ((hsv[:,:,0]>=35)&(hsv[:,:,0]<=85)&(hsv[:,:,1]>110)&(hsv[:,:,2]>100)).mean()
        blue = ((hsv[:,:,0]>=95)&(hsv[:,:,0]<=125)&(hsv[:,:,1]>100)&(hsv[:,:,2]>100)).mean()
        owner = 'own' if green > .30 and blue < .15 else 'joined' if blue > .30 and green < .15 else 'unknown'
        timer = frame.crop((x-5,y+36,min(x+275,520),y+86))
        comps = _daily_white_numeric_components(timer)
        digits = [_read_daily_numeric_glyph(c[4]) for c in comps] if len(comps)==6 else []
        seconds = None
        if digits and all(d and d[1]>=.80 for d in digits):
            ds = [d[0] for d in digits]
            hh,mm,ss = ds[0]*10+ds[1],ds[2]*10+ds[3],ds[4]*10+ds[5]
            if hh<24 and mm<60 and ss<60:
                seconds=hh*3600+mm*60+ss
        rows.append(CompactRallyRow(owner, map_content_point((x-50,y+35), BUILTIN_DAILY_TASK_REFERENCE_SIZE,image), seconds))
        local_y=y-top
        scores[max(0,local_y-50):local_y+65,:]=-1
    return tuple(sorted(rows,key=lambda row:row.point[1]))


def read_sidebar_countdown(image: Image.Image) -> int | None:
    """Read HH:MM:SS only in the account's expanded queue rows.

    Never read the allied overlay above the rows or the right-side rally
    timer. This is display/scheduling information, never return authority.
    """
    viewport = content_viewport(image)
    frame = image.crop((viewport.left, viewport.top, viewport.right, viewport.bottom)).resize((1440, 2560)).convert("RGB")
    rgb = np.asarray(frame)
    roi = rgb[680:1670, 140:800]
    dark = (((roi[:,:,0] < 35) & (roi[:,:,1] < 35) & (roi[:,:,2] < 55)) |
            ((roi[:,:,0] < 80) & (roi[:,:,1] > 100) & (roi[:,:,2] < 110))).astype(np.uint8)
    count, _, stats, _ = cv2.connectedComponentsWithStats(dark, 8)
    readings = []
    for x, y, w, h, area in stats[1:count]:
        if not (300 <= w <= 660 and 22 <= h <= 65 and area > w*h*.50):
            continue
        crop = frame.crop((140+x, 680+y, 140+x+w, 680+y+h))
        components = _daily_white_numeric_components(crop)
        if len(components) != 6:
            continue
        digits = [_read_daily_numeric_glyph(c[4]) for c in components]
        if any(d is None or d[1] < .80 for d in digits):
            continue
        values = [d[0] for d in digits]
        hh, mm, ss = values[0]*10+values[1], values[2]*10+values[3], values[4]*10+values[5]
        if hh <= 23 and mm < 60 and ss < 60:
            readings.append(hh*3600+mm*60+ss)
    return readings[0] if len(readings) == 1 else None


def white_mask(rgb: np.ndarray) -> np.ndarray:
    return ((rgb.min(axis=2) >= 195) & (rgb.max(axis=2) - rgb.min(axis=2) < 55)).astype(np.uint8) * 255


@lru_cache(maxsize=1)
def hunt_name_template() -> np.ndarray:
    with Image.open(resource_path(HUNT_NAME_ASSET)) as image:
        return white_mask(np.asarray(image.convert("RGB")))


def match_hunt_formation(image: Image.Image, *, selected: bool = False) -> BeastRallyMatch:
    """Require the Beast formation page and the literal 打野 name anywhere in its tab strip."""
    controls = match_beast_rally_formation_controls(image)
    if controls.state is not BeastRallyState.FORMATION:
        return BeastRallyMatch(BeastRallyState.UNKNOWN, None, 0.0)
    viewport = content_viewport(image)
    rgb = np.asarray(image.crop((viewport.left, viewport.top, viewport.right, viewport.bottom)).resize((1440, 2560)).convert("RGB"))
    left, top, right, bottom = 25, 175, 1210, 315
    mask = white_mask(rgb[top:bottom, left:right])
    template = hunt_name_template()
    scores = cv2.matchTemplate(mask, template, cv2.TM_CCOEFF_NORMED)
    _, score, _, (x, y) = cv2.minMaxLoc(scores)
    if score < 0.90:
        return BeastRallyMatch(BeastRallyState.UNKNOWN, None, score)
    h, w = template.shape
    cx, cy = left + x + w // 2, top + y + h // 2
    # Reject duplicate names, rather than silently choosing one saved team.
    suppressed = scores.copy()
    suppressed[max(0, y-h):y+h, max(0, x-w):x+w] = -1
    if float(suppressed.max()) >= 0.90:
        return BeastRallyMatch(BeastRallyState.UNKNOWN, None, score)
    if selected:
        tile = rgb[max(150, cy-95):cy+25, max(0, cx-64):min(1440, cx+64)]
        yellow = (tile[:,:,0] > 190) & (tile[:,:,1] > 150) & (tile[:,:,2] < 135)
        if float(yellow.mean()) < 0.035:
            return BeastRallyMatch(BeastRallyState.UNKNOWN, None, score)
    point = map_content_point((cx, cy-25), BUILTIN_DAILY_TASK_REFERENCE_SIZE, image)
    return BeastRallyMatch(BeastRallyState.FORMATION, controls.point, score,
                          (("hunt", point), ("dispatch", controls.point)))


@dataclass
class SingleBeastCycle:
    """Conservative account capacity gate: never infer return from another row."""
    total: int
    dispatched: bool = False
    seen_busy: bool = False
    returned: bool = False
    require_owner: bool = False

    def confirm_owned_rally(self) -> None:
        if not self.dispatched:
            raise ValueError("no correlated Expedition")
        self.seen_busy = True

    def observe(self, used: int, total: int) -> str:
        if total != self.total or not 0 <= used <= total:
            raise ValueError("single-team capacity is ambiguous")
        if not self.dispatched:
            return "ready" if used == 0 else "occupied"
        if used == 1:
            if not self.require_owner:
                self.seen_busy = True
            return "busy" if self.seen_busy else "awaiting_dispatch_proof"
        if used > 1:
            # A concurrent manual/game queue never authorises a second Beast.
            # Retain our cycle and wait until ALL rows are freshly idle.
            return "occupied_multiple"
        if self.seen_busy:
            self.returned = True
            return "returned"
        return "awaiting_dispatch_proof"

    def dispatch(self) -> None:
        if self.dispatched:
            raise ValueError("one cycle cannot dispatch twice")
        self.dispatched = True
