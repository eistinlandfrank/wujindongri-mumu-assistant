"""Named hunting formation and one-team Beast lifecycle, separate from Daily."""
from dataclasses import dataclass
from functools import lru_cache
import time

import cv2
import numpy as np
from PIL import Image

from wjdr_backend import (
    BeastRallyMatch, BeastRallyState, BUILTIN_DAILY_TASK_REFERENCE_SIZE,
    content_viewport, map_content_point, match_beast_rally_formation_controls,
    resource_path, AdbError, DailyMarchCapacity,
    read_beast_rally_collapsed_march_capacity,
    read_daily_march_capacity,
    match_beast_rally_world_search,
    match_beast_rally_progress_sidebar_collapsed,
    match_beast_rally_progress_sidebar_expanded,
    _daily_white_numeric_components, _read_daily_numeric_glyph,
)

HUNT_NAME_ASSET = "assets/beast_rally_hunt_name.png"


def consume_beast_test_cycle_limit(environ, automatic_start=False):
    """One-shot launch QA only; never leak a test cap to buttons/child apps."""
    raw = environ.pop('WJDR_BEAST_MAX_CYCLES', '0')
    if not automatic_start:
        return 0
    try:
        return max(0, int(raw))
    except (ValueError, TypeError):
        return 0


def consume_beast_search_race_pause(environ, automatic_start=False):
    """Explicit user-requested 20s race injection; one automatic launch only."""
    raw=environ.pop('WJDR_BEAST_SEARCH_RACE_PAUSE', '')
    return 20.0 if automatic_start and raw=='20' else 0.0


@lru_cache(maxsize=1)
def target_conflict_templates():
    return tuple(np.asarray(Image.open(resource_path('assets/'+name)).convert('RGB'))
                 for name in ('beast_same_target_warning.png','beast_same_target_cancel.png'))


def match_same_target_conflict(image):
    """Exact warning sentence AND orange Cancel; never generic Confirm/X."""
    viewport=content_viewport(image)
    if viewport.width<720 or abs(viewport.width/viewport.height-9/16)>.008:
        return None
    rgb=np.asarray(image.crop((viewport.left,viewport.top,viewport.right,viewport.bottom)).resize((1440,2560)).convert('RGB'))
    body,cancel=target_conflict_templates()
    for region,template in ((rgb[1120:1300,180:1260],body),(rgb[1535:1620,240:580],cancel)):
        score=cv2.matchTemplate(region,template,cv2.TM_CCOEFF_NORMED)[0,0]
        if score<.94 or np.abs(region.astype(float)-template).mean()>16:
            return None
    return map_content_point((420,1580),BUILTIN_DAILY_TASK_REFERENCE_SIZE,image)


@lru_cache(maxsize=1)
def compact_header_masks():
    with Image.open(resource_path('assets/beast_rally_compact_march_title.png')) as image:
        return tuple(white_mask(np.asarray(image.convert('RGB').resize((round(image.width*s), round(image.height*s)))))
                     for s in (1., 1.2, 4/3, 1.5))


@lru_cache(maxsize=1)
def compact_closed_masks():
    with Image.open(resource_path('assets/beast_rally_progress_sidebar_collapsed_live.png')) as image:
        return tuple(white_mask(np.asarray(image.convert('RGB').resize((round(image.width*s),round(image.height*s)))))
                     for s in (1., 4/3, 1.5))


def read_compact_capacity(image, threshold=.90):
    """Numeric header, or user-confirmed hidden-list idle on a proved world.

    total=0 is explicitly unknown capacity, not a fabricated six-slot reading.
    Header/text/bar presence vetoes hidden-idle even if its digits fail OCR.
    """
    viewport = content_viewport(image)
    if viewport.width < 720 or abs(viewport.width / viewport.height - 9/16) > .008:
        return None
    numeric = read_beast_rally_collapsed_march_capacity(image, threshold)
    if numeric:
        return numeric
    if (not match_beast_rally_world_search(image, threshold)[0]
            or match_beast_rally_progress_sidebar_expanded(image, threshold)[0]):
        return None
    frame = image.crop((viewport.left, viewport.top, viewport.right, viewport.bottom)).resize((1440,2560)).convert('RGB')
    rgb = np.asarray(frame)
    roi = rgb[300:1400, 0:590]
    white = white_mask(roi)
    header_score = max(cv2.minMaxLoc(cv2.matchTemplate(white, mask, cv2.TM_CCOEFF_NORMED))[1]
                       for mask in compact_header_masks())
    if header_score >= .70:
        # A strong title + its fixed numeric lane establishes the compact
        # header directly, without a background-sensitive unrelated arrow.
        return read_daily_march_capacity(image) if header_score >= .90 else None
    if not match_beast_rally_progress_sidebar_collapsed(image, threshold)[0]:
        arrow_roi = white_mask(rgb[980:1240, 0:120])
        closed = any(cv2.minMaxLoc(cv2.matchTemplate(arrow_roi, mask, cv2.TM_CCOEFF_NORMED))[1] >= .94
                     for mask in compact_closed_masks())
        if not closed:
            return None
    if read_compact_rally_rows(image):
        return None
    # A visible countdown bar or the opaque wide header must never become
    # idle merely because the text is blurred. These are vetoes, not actions.
    dark = ((roi.max(axis=2) < 90) & (roi.min(axis=2) < 65)).astype(np.uint8)
    n, _, stats, _ = cv2.connectedComponentsWithStats(dark, 8)
    if any(w >= 170 and 12 <= h <= 130 and area > w*h*.60
           for x,y,w,h,area in stats[1:n]):
        return None
    return DailyMarchCapacity(0, 0, .95, 'hidden_idle')


class GuardedBeastADB:
    """Retry fresh reads only. Never replay input or migrate to another device."""

    def __init__(self, adb, stop_event, report, clock=time.monotonic):
        self.adb, self.stop_event, self.report, self.clock = adb, stop_event, report, clock
        self.bound_device = adb.device

    def __getattr__(self, name):
        return getattr(self.adb, name)

    def check_active(self):
        if self.stop_event.is_set():
            raise InterruptedError("用户已停止；取消后续输入")
        if self.adb.device != self.bound_device:
            raise AdbError("ADB目标发生变化；不自动迁移当前队伍")

    def screenshot(self):
        deadline = self.clock() + 8.0
        for attempt in range(3):
            self.check_active()
            remaining = deadline - self.clock()
            if remaining <= 0:
                raise AdbError("新帧恢复超过8秒；保留当前流程记录")
            try:
                image = self.adb.screenshot(timeout=min(2.5, remaining))
                self.check_active()
                if self.clock() > deadline:
                    raise AdbError("截图恢复超时；拒绝过期画面")
                return image
            except AdbError:
                self.check_active()
                if attempt == 2 or self.clock() >= deadline:
                    raise
                self.report(f"截图暂时失败，立即获取新帧（{attempt + 1}/2）；不重放点击、不切换ADB")

    def tap(self, *point):
        self.check_active()
        return self.adb.tap(*point)

    def back(self):
        self.check_active()
        return self.adb.back()

    def shell(self, *args, **kwargs):
        self.check_active()
        return self.adb.shell(*args, **kwargs)


@dataclass(frozen=True)
class CompactRallyRow:
    owner: str  # own / joined / unknown; only while exact 集结中 is present
    point: tuple[int, int]
    seconds: int | None
    phase: str = 'rallying'


@lru_cache(maxsize=1)
def compact_marching_icon():
    with Image.open(resource_path('assets/beast_rally_compact_marching_icon.png')) as image:
        return np.asarray(image.convert('L'))


def read_compact_marching_rows(image):
    """Reviewed green marching glyph + same-row timer, not green bar colour.

    Coordinates replace the rally title during marching. Ownership is only
    usable by a controller with an already correlated self-rally proof.
    """
    viewport = content_viewport(image)
    rgb = np.asarray(image.crop((viewport.left,viewport.top,viewport.right,viewport.bottom)).resize((1440,2560)).convert('RGB'))
    roi=rgb[390:1400,:140]
    scores=cv2.matchTemplate(white_mask(roi),compact_marching_icon(),cv2.TM_CCOEFF_NORMED)
    rows=[]
    for _ in range(8):
        _,score,_,(x,y)=cv2.minMaxLoc(scores)
        if score<.90:
            break
        icon=roi[y:y+75,x:x+77]
        hsv=cv2.cvtColor(icon,cv2.COLOR_RGB2HSV)
        yy,xx=np.ogrid[:75,:77]
        circle=(xx-38)**2+(yy-37)**2<28**2
        colored=circle&(hsv[:,:,1]>110)&(hsv[:,:,2]>100)
        green=((hsv[:,:,0]>=35)&(hsv[:,:,0]<=85))[colored].mean() if colored.any() else 0
        # Large white marching glyph covers most of the circle; classify its
        # remaining saturated fill, requiring substantial coloured coverage.
        if colored.sum()/circle.sum()>.15 and green>.95:
            # Glyph top is reference y503 in the reviewed frame; timer y540.
            timer=Image.fromarray(rgb[390+y+37:390+y+88, x+80:min(x+370,520)])
            comps=_daily_white_numeric_components(timer)
            digits=[_read_daily_numeric_glyph(c[4]) for c in comps] if len(comps)==6 else []
            seconds=None
            if digits and all(d and d[1]>=.80 for d in digits):
                v=[d[0] for d in digits]
                hh,mm,ss=v[0]*10+v[1],v[2]*10+v[3],v[4]*10+v[5]
                if hh<24 and mm<60 and ss<60:
                    seconds=hh*3600+mm*60+ss
            if seconds is not None:
                rows.append(CompactRallyRow('own',map_content_point((x+38,390+y+37),BUILTIN_DAILY_TASK_REFERENCE_SIZE,image),seconds,'marching'))
        scores[max(0,y-50):y+90,:]=-1
    return tuple(rows)


def only_joined_rallies(capacity, rows):
    """A complete visible list of exact BLUE 集结中 rows, never blue returns.

    Missing/hidden/truncated/duplicate rows and full capacity cannot authorize
    a Beast. Numeric count alone is not ownership or completion evidence.
    """
    return bool(capacity and capacity.evidence=='numeric'
                and 0<capacity.used<capacity.total and len(rows)==capacity.used
                and all(r.owner=='joined' and r.phase=='rallying' for r in rows)
                and len({r.point for r in rows})==len(rows))


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
        yy, xx = np.ogrid[:icon.shape[0], :icon.shape[1]]
        circle = (xx-icon.shape[1]/2)**2 + (yy-icon.shape[0]/2)**2 <= (min(icon.shape[:2])*.38)**2
        green = ((hsv[:,:,0]>=35)&(hsv[:,:,0]<=85)&(hsv[:,:,1]>110)&(hsv[:,:,2]>100))[circle].mean()
        blue = ((hsv[:,:,0]>=95)&(hsv[:,:,0]<=125)&(hsv[:,:,1]>100)&(hsv[:,:,2]>100))[circle].mean()
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


@lru_cache(maxsize=1)
def hunt_name_variants():
    with Image.open(resource_path('assets/beast_rally_hunt_name_large.png')) as image:
        return hunt_name_template(), white_mask(np.asarray(image.convert('RGB')))


def match_hunt_formation(image: Image.Image, *, selected: bool = False) -> BeastRallyMatch:
    """Require the Beast formation page and the literal 打野 name anywhere in its tab strip."""
    controls = match_beast_rally_formation_controls(image)
    if controls.state is not BeastRallyState.FORMATION:
        return BeastRallyMatch(BeastRallyState.UNKNOWN, None, 0.0)
    viewport = content_viewport(image)
    rgb = np.asarray(image.crop((viewport.left, viewport.top, viewport.right, viewport.bottom)).resize((1440, 2560)).convert("RGB"))
    left, top, right, bottom = 25, 175, 1210, 315
    mask = white_mask(rgb[top:bottom, left:right])
    best = None
    distinct_names = []
    # Native text sizes differ across emulator density/account UI variants.
    # Normalize the frame, then search a small fixed glyph-scale pyramid.
    for base_template in hunt_name_variants():
        for scale in (.9, 1., 1.1, 1.2):
            template = cv2.resize(base_template, None, fx=scale, fy=scale, interpolation=cv2.INTER_NEAREST)
            scores = cv2.matchTemplate(mask, template, cv2.TM_CCOEFF_NORMED)
            _, candidate_score, _, location = cv2.minMaxLoc(scores)
            if candidate_score >= .90:
                candidate_center = (location[0]+template.shape[1]//2, location[1]+template.shape[0]//2)
                if not any(abs(candidate_center[0]-p[0]) <= 30 and abs(candidate_center[1]-p[1]) <= 20 for p in distinct_names):
                    distinct_names.append(candidate_center)
            if best is None or candidate_score > best[0]:
                best = candidate_score, location, template, scores
    score, (x, y), template, scores = best
    if len(distinct_names) > 1:
        return BeastRallyMatch(BeastRallyState.UNKNOWN, None, score)
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
