"""Single-shield and one-team Beast lifecycle, separate from Daily."""
from dataclasses import dataclass
from functools import lru_cache
import hashlib
import json
import os
from pathlib import Path
import re
import time

import cv2
import numpy as np
from PIL import Image

from wjdr_backend import (
    BeastRallyMatch, BeastRallyState, BUILTIN_DAILY_TASK_REFERENCE_SIZE,
    content_viewport, map_content_point, match_beast_rally_formation_controls,
    CONFIG_DIR, APP_VERSION,
    resource_path, AdbError, DailyMarchCapacity,
    read_beast_rally_collapsed_march_capacity,
    read_daily_march_capacity,
    match_beast_rally_world_search,
    match_beast_rally_progress_sidebar_collapsed,
    match_beast_rally_progress_sidebar_expanded,
    _daily_white_numeric_components, _read_daily_numeric_glyph,
    _daily_numeric_component_is_slash,
)

HUNT_NAME_ASSET = "assets/beast_rally_hunt_name.png"


class CycleActionPositions:
    """First-cycle positions guarded by identical viewport geometry."""
    def __init__(self):
        self.positions = {}

    def remember(self, name, image, point):
        viewport = content_viewport(image)
        if not point or not (viewport.left <= point[0] < viewport.right and viewport.top <= point[1] < viewport.bottom):
            return None
        x, y = point
        rx = max(3, round(viewport.width * 24 / 1440))
        ry = max(3, round(viewport.height * 12 / 2560))
        box = (x-rx, y-ry, x+rx, y+ry)
        if box[0] < viewport.left or box[1] < viewport.top or box[2] > viewport.right or box[3] > viewport.bottom:
            return None
        crop = np.asarray(image.crop(box).convert('L'), dtype=np.int16).copy()
        self.positions[name] = (image.size, viewport.box, point, box, crop)
        return point

    def reuse(self, name, image, recognized_point=None):
        cached = self.positions.get(name)
        if not cached:
            return None
        size, viewport, point, box, crop = cached
        if image.size != size or content_viewport(image).box != viewport:
            return None
        if recognized_point is not None:
            return point if max(abs(a-b) for a,b in zip(point, recognized_point)) <= 4 else None
        if crop is None:
            return None  # Persisted coordinates carry no screenshot/pixel proof.
        current = np.asarray(image.crop(box).convert('L'), dtype=np.int16)
        return point if current.shape == crop.shape and np.mean(np.abs(current-crop)) <= 12 else None

    def cached_point(self, name, image):
        """Reuse a first-cycle position on the identical game viewport."""
        cached = self.positions.get(name)
        if not cached or image.size != cached[0] or content_viewport(image).box != cached[1]:
            return None
        return cached[2]

    def refresh_recognized(self, name, image, point):
        """Replace a cached point only after fresh recognition on the same viewport."""
        cached = self.positions.get(name)
        if not cached or not point:
            return None
        if image.size != cached[0] or content_viewport(image).box != cached[1]:
            return None
        return self.remember(name, image, point)


_ROUTE_COORDINATE_NAMES = ('world_search', 'beast_card', 'selector_search', 'rally_button',
                           'launch', 'withdraw_all', 'shield_plus', 'dispatch')


def _beast_route_path(identity, directory=None):
    if not isinstance(identity, str) or not re.fullmatch(r'mumu:\d+:android:[a-zA-Z0-9_-]+', identity):
        return None
    root = Path(directory) if directory is not None else CONFIG_DIR / 'beast_route_coordinates'
    return root / (hashlib.sha256(identity.encode('utf-8')).hexdigest() + '.json')


def save_beast_route_coordinates(identity, level, positions, select_three, *, directory=None):
    """Persist only established points, never screenshots, for one stable identity."""
    path = _beast_route_path(identity, directory)
    names = _ROUTE_COORDINATE_NAMES + (('three_minutes',) if select_three else ())
    if path is None or type(level) is not int or level < 1 or type(select_three) is not bool:
        return False
    entries = [positions.positions.get(name) for name in names]
    if any(not entry for entry in entries):
        return False
    size, viewport = entries[0][0], entries[0][1]
    if any(entry[0] != size or entry[1] != viewport for entry in entries):
        return False
    left, top, right, bottom = viewport
    if any(not (left <= entry[2][0] < right and top <= entry[2][1] < bottom) for entry in entries):
        return False
    payload = {'version': 1, 'app_version': APP_VERSION,
               'identity_hash': hashlib.sha256(identity.encode('utf-8')).hexdigest(),
               'level': level, 'troops': [1, 0, 0], 'mode': 'manual',
               'select_three': select_three, 'size': list(size), 'viewport': list(viewport),
               'points': {name: list(entry[2]) for name, entry in zip(names, entries)}}
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f'.{path.name}.{os.getpid()}.{time.time_ns()}.tmp')
    try:
        with temporary.open('w', encoding='utf-8') as stream:
            json.dump(payload, stream, ensure_ascii=False)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass
    return True


def load_beast_route_coordinates(identity, level, image, positions, *, directory=None):
    """Return 3-minute selection flag, or None if identity/config/geometry differs."""
    path = _beast_route_path(identity, directory)
    if path is None or type(level) is not int:
        return None
    try:
        payload = json.loads(path.read_text(encoding='utf-8'))
        if (not isinstance(payload, dict) or payload.get('version') != 1
                or payload.get('app_version') != APP_VERSION
                or payload.get('identity_hash') != hashlib.sha256(identity.encode('utf-8')).hexdigest()
                or payload.get('level') != level or payload.get('mode') != 'manual'
                or payload.get('troops') != [1, 0, 0]
                or type(payload.get('select_three')) is not bool):
            return None
        viewport = content_viewport(image).box
        if payload.get('size') != list(image.size) or payload.get('viewport') != list(viewport):
            return None
        names = _ROUTE_COORDINATE_NAMES + (('three_minutes',) if payload['select_three'] else ())
        points = payload.get('points')
        if not isinstance(points, dict):
            return None
        left, top, right, bottom = viewport
        prepared = {}
        for name in names:
            point = points.get(name)
            if (not isinstance(point, list) or len(point) != 2
                    or any(type(value) is not int for value in point)
                    or not (left <= point[0] < right and top <= point[1] < bottom)):
                return None
            prepared[name] = (image.size, viewport, tuple(point), None, None)
        positions.positions.update(prepared)
        return payload['select_three']
    except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError):
        return None


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


def read_compact_capacity(image, threshold=.90, *, world_proven=False):
    """Numeric header, or user-confirmed hidden-list idle on a proved world.

    total=0 is explicitly unknown capacity, not a fabricated six-slot reading.
    Header/text/bar presence vetoes hidden-idle even if its digits fail OCR.
    ``world_proven`` is only for the same fresh frame after the caller has
    verified world search and confirmed the panel is not expanded. It reuses
    those results and tries the title-anchored numeric header first.
    """
    viewport = content_viewport(image)
    if viewport.width < 720 or abs(viewport.width / viewport.height - 9/16) > .008:
        return None
    if world_proven:
        numeric = read_compact_numeric_capacity(image, threshold, world_proven=True)
        if numeric:
            return numeric
    numeric = read_beast_rally_collapsed_march_capacity(image, threshold)
    if numeric:
        return numeric
    if not world_proven and (not match_beast_rally_world_search(image, threshold)[0]
            or match_beast_rally_progress_sidebar_expanded(image, threshold)[0]):
        return None
    # Live0号: clear5/6 and all five opaque circular icons, but translucent
    # title/background template failed. Cross-check numeric + every icon,
    # never substitute a guessed zero or a fabricated slot count.
    direct = read_compact_header_digits(image)
    if direct and direct.used > 0 and len(read_compact_queue_icons(image,direct)) == direct.used:
        return direct
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
    if read_compact_rally_rows(image, read_timer=False):
        return None
    # A visible countdown bar or the opaque wide header must never become
    # idle merely because the text is blurred. These are vetoes, not actions.
    dark = ((roi.max(axis=2) < 90) & (roi.min(axis=2) < 65)).astype(np.uint8)
    n, _, stats, _ = cv2.connectedComponentsWithStats(dark, 8)
    if any(w >= 170 and 12 <= h <= 130 and area > w*h*.60
           for x,y,w,h,area in stats[1:n]):
        return None
    return DailyMarchCapacity(0, 0, .95, 'hidden_idle')


def _compact_shifted_header(frame):
    """Locate the compact title in normalized content, not desktop pixels.

    Only the calibrated title scale and constrained left-hand lane qualify.
    An unproved title must not authorize a shifted-list interpretation.
    """
    rgb = np.asarray(frame.convert('RGB'))
    lane = white_mask(rgb[300:700, 60:200])
    mask = compact_header_masks()[2]
    score, point = cv2.minMaxLoc(cv2.matchTemplate(lane, mask, cv2.TM_CCOEFF_NORMED))[1::2]
    return (point[0] + 60, point[1] + 300) if score >= .84 else None


def read_compact_header_digits(image):
    """Keep bright map outside the opaque numeric header out of glyph filtering."""
    viewport=content_viewport(image)
    frame=image.crop((viewport.left,viewport.top,viewport.right,viewport.bottom)).resize((1440,2560))
    anchor = _compact_shifted_header(frame)
    top = anchor[1] - 9 if anchor else 400
    components=_daily_white_numeric_components(frame.crop((395,top,485,top+60)))
    if len(components)!=3 or not _daily_numeric_component_is_slash(components[1][4]):
        return None
    left,right=(_read_daily_numeric_glyph(components[i][4]) for i in (0,2))
    if not left or not right or min(left[1],right[1])<.85 or not 0<=left[0]<=right[0]<=9 or right[0]==0:
        return None
    return DailyMarchCapacity(left[0],right[0],min(left[1],right[1]))


def read_compact_numeric_capacity(image, threshold=.90, *, world_proven=False):
    """Read a title-anchored compact capacity without assuming row identity."""
    viewport = content_viewport(image)
    if viewport.width < 720 or abs(viewport.width / viewport.height - 9/16) > .008:
        return None
    if not world_proven and (not match_beast_rally_world_search(image, threshold)[0]
            or match_beast_rally_progress_sidebar_expanded(image, threshold)[0]):
        return None
    frame = image.crop((viewport.left, viewport.top, viewport.right, viewport.bottom)).resize((1440, 2560))
    if _compact_shifted_header(frame) is None:
        return None
    return read_compact_header_digits(image)


class GuardedBeastADB:
    """Retry fresh reads only. Never replay input or migrate to another device."""

    def __init__(self, adb, stop_event, report, clock=time.monotonic):
        self.adb, self.stop_event, self.report, self.clock = adb, stop_event, report, clock
        self.bound_device = adb.device
        self.input_gate = None
        self.input_attempted = False

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
        return self._input(lambda: self.adb.tap(*point))

    def back(self):
        return self._input(self.adb.back)

    def shell(self, *args, **kwargs):
        return self._input(lambda: self.adb.shell(*args, **kwargs))

    def _input(self, operation):
        self.check_active()
        # Mark before transport: an exception does not prove it was ignored.
        self.input_attempted = True
        def guarded():
            self.check_active()
            return operation()
        return self.input_gate(guarded) if self.input_gate else guarded()


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
def compact_gathering_title():
    with Image.open(resource_path('assets/beast_gathering_title.png')) as image:
        return np.asarray(image.convert('L'))


def _compact_gathering_row(rgb, cx, cy):
    """Exact same-row gathering text plus a green icon rim, never a green bar."""
    icon = rgb[cy-38:cy+38,cx-38:cx+38]
    if icon.shape != (76,76,3):
        return False
    hsv = cv2.cvtColor(icon, cv2.COLOR_RGB2HSV)
    yy, xx = np.ogrid[:76,:76]
    radius = (xx-38)**2 + (yy-38)**2
    rim = (radius >= 25**2) & (radius <= 35**2)
    green = rim & (hsv[:,:,0]>=35) & (hsv[:,:,0]<=85) & (hsv[:,:,1]>100) & (hsv[:,:,2]>100)
    if green.sum() < rim.sum()*.30:
        return False
    region = cv2.cvtColor(rgb[cy-52:cy+4,115:255], cv2.COLOR_RGB2GRAY)
    template = compact_gathering_title()
    if region.shape[0] < template.shape[0] or region.shape[1] < template.shape[1]:
        return False
    _, raw_score, _, (raw_x, raw_y) = cv2.minMaxLoc(cv2.matchTemplate(region, template, cv2.TM_CCOEFF_NORMED))
    if raw_score >= .94:
        return True
    # Detailed terrain can obscure one character without changing the green
    # queue rim. Require the whole title, each character and a strong rim.
    if raw_score >= .92 and green.sum() >= rim.sum() * .70:
        matched = region[raw_y:raw_y + template.shape[0], raw_x:raw_x + template.shape[1]]
        if all(cv2.matchTemplate(matched[:, a:b], template[:, a:b], cv2.TM_CCOEFF_NORMED)[0, 0] >= threshold
               for a, b, threshold in ((0, 38, .86), (38, 77, .90), (77, 115, .90))):
            return True
    # A translucent queue can overlay a detailed map object. Remove slowly
    # varying background, then demand a strong match of the whole title and
    # of each character. This fallback does not relax the existing raw score.
    kernel = np.ones((9, 9), np.uint8)
    clean_region = cv2.morphologyEx(region, cv2.MORPH_TOPHAT, kernel)
    clean_template = cv2.morphologyEx(template, cv2.MORPH_TOPHAT, kernel)
    _, score, _, (x, y) = cv2.minMaxLoc(cv2.matchTemplate(clean_region, clean_template, cv2.TM_CCOEFF_NORMED))
    if score < .94:
        return False
    matched = clean_region[y:y + template.shape[0], x:x + template.shape[1]]
    return all(
        cv2.matchTemplate(matched[:, a:b], clean_template[:, a:b], cv2.TM_CCOEFF_NORMED)[0, 0] >= .90
        for a, b in ((0, 38), (38, 77), (77, 115))
    )


def read_compact_queue_icons(image, capacity):
    """Read every circular left icon, independent of rally/coordinate text.

    Blue means no green self-created phase, not proof that troops are home.
    Caller must confirm the world, numeric capacity and both fresh frames.
    """
    if not capacity or capacity.evidence != 'numeric' or not 0 < capacity.used <= capacity.total:
        return ()
    viewport = content_viewport(image)
    if viewport.width < 720 or abs(viewport.width / viewport.height - 9/16) > .008:
        return ()
    frame = image.crop((viewport.left, viewport.top, viewport.right, viewport.bottom)).resize((1440,2560)).convert('RGB')
    anchor = _compact_shifted_header(frame)
    if anchor:
        observed = read_compact_header_digits(image)
        if not observed or (observed.used, observed.total) != (capacity.used, capacity.total):
            return ()
    rgb = np.asarray(frame)
    rows = []
    # Fixed normalized compact layout. Do not segment the whole blue blob:
    # moving allied arrows behind this translucent panel touch its circle.
    for index in range(capacity.used):
        cx,cy = 70,(anchor[1]+141 if anchor else 545)+122*index
        if _compact_gathering_row(rgb, cx, cy):
            rows.append(CompactRallyRow('gathering', (cx,cy), None, 'gathering'))
            continue
        icon = rgb[cy-38:cy+38,cx-38:cx+38]
        patch = cv2.cvtColor(icon,cv2.COLOR_RGB2HSV)
        yy,xx = np.ogrid[:76,:76]
        circle = (xx-38)**2 + (yy-38)**2 < 27**2
        saturated = circle & (patch[:,:,1]>100) & (patch[:,:,2]>100)
        if saturated.sum() < circle.sum()*.20:
            continue
        green = ((patch[:,:,0]>=35)&(patch[:,:,0]<=85))[saturated].mean()
        blue = ((patch[:,:,0]>=95)&(patch[:,:,0]<=125))[saturated].mean()
        glyph = white_mask(icon)[circle] > 0
        if not .08 < glyph.mean() < .72:
            continue
        owner = 'own' if green>.95 else 'blue' if blue>.95 else 'unknown'
        rows.append(CompactRallyRow(owner, (cx,cy), None, 'icon'))
    rows.sort(key=lambda r:r.point[1])
    if (len(rows) != capacity.used or any(not 100 <= b.point[1]-a.point[1] <= 145
                                         for a,b in zip(rows,rows[1:]))):
        return ()
    return tuple(rows)


def blue_only_free_slot(capacity, rows):
    return bool(capacity and capacity.evidence=='numeric' and 0<capacity.used<capacity.total
                and len(rows)==capacity.used and all(r.owner=='blue' for r in rows)
                and len({r.point for r in rows})==len(rows))


def blue_pair_free(first, second, cap1, cap2):
    """User-authorized next search when only blue phases remain, not a return claim."""
    return bool(cap1 and cap2 and (cap1.used,cap1.total)==(cap2.used,cap2.total)
                and match_beast_rally_world_search(first)[0] and match_beast_rally_world_search(second)[0]
                and blue_only_free_slot(cap1,read_compact_queue_icons(first,cap1))
                and blue_only_free_slot(cap2,read_compact_queue_icons(second,cap2)))


def gathering_pair_free(first, second, cap1, cap2):
    """Complete, stable rows of blue icons or explicitly identified gatherers."""
    if not (cap1 and cap2 and cap1.evidence == cap2.evidence == 'numeric'
            and (cap1.used,cap1.total) == (cap2.used,cap2.total)
            and 0 < cap1.used < cap1.total
            and match_beast_rally_world_search(first)[0]
            and match_beast_rally_world_search(second)[0]):
        return False
    first_rows = read_compact_queue_icons(first,cap1)
    second_rows = read_compact_queue_icons(second,cap2)
    return bool(len(first_rows) == len(second_rows) == cap1.used
                and all(a.owner in ('blue','gathering') and a.owner == b.owner
                        and a.point == b.point for a,b in zip(first_rows,second_rows))
                and any(a.owner == 'gathering' for a in first_rows))


@dataclass(frozen=True)
class ConcurrentRallySnapshot:
    used: int
    total: int
    evidence: str
    phases: tuple[str, ...]

    @property
    def rallies(self):
        return self.phases.count('rallying')

    @property
    def green(self):
        return self.rallies + self.phases.count('marching')

    @property
    def free(self):
        return self.evidence == 'hidden_idle' or self.used < self.total


class ConcurrentLineTracker:
    """Conservatively follow owned rows; ambiguous disappearances retain a slot.

    Rows preserve their displayed order. All compatible matchings are kept, so
    an unrelated blue row disappearing cannot release an ambiguously matched
    owned row. An unseen rally-to-march transition remains occupied until the
    entire compact list is proven idle.
    """
    def __init__(self):
        self.states = None
        self.last_snapshot = None

    def observe(self, snapshot, new_rally=False):
        if snapshot is None:
            return False
        if not new_rally and snapshot == self.last_snapshot:
            return True
        if snapshot.evidence == 'hidden_idle':
            if new_rally:
                return False
            self.states = {((), 0)}
            self.last_snapshot = snapshot
            return True
        if (snapshot.evidence != 'numeric' or len(snapshot.phases) != snapshot.used
                or any(p not in ('gathering', 'blue', 'rallying', 'marching') for p in snapshot.phases)):
            return False
        if self.states is None:
            if new_rally:
                return False
            self.states = {(tuple((p, False) for p in snapshot.phases), 0)}
            self.last_snapshot = snapshot
            return True
        results = set()
        allowed = {'gathering': ('gathering',), 'rallying': ('rallying', 'marching'),
                   'marching': ('marching', 'blue'), 'blue': ('blue',)}
        phases = snapshot.phases
        for old, phantom in self.states:
            def visit(i, j, rows, missing, added):
                if len(results) > 512:
                    return
                if i == len(old) and j == len(phases):
                    if added == int(new_rally):
                        results.add((tuple(rows), missing))
                    return
                if i < len(old):
                    phase, owned = old[i]
                    # A vanished rally has no proven march completion.
                    visit(i + 1, j, rows, missing + int(owned and phase == 'rallying'), added)
                    if j < len(phases) and phases[j] in allowed[phase]:
                        visit(i + 1, j + 1, rows + [(phases[j], owned)], missing, added)
                if j < len(phases):
                    phase = phases[j]
                    if phase in ('blue', 'gathering'):
                        visit(i, j + 1, rows + [(phase, False)], missing, added)
                    elif new_rally and phase == 'rallying' and not added:
                        visit(i, j + 1, rows + [(phase, True)], missing, 1)
            visit(0, 0, [], phantom, 0)
            if len(results) > 512:
                break
        if not results or len(results) > 512:
            return False
        self.states = results
        self.last_snapshot = snapshot
        return True

    def has_room(self, limit):
        return bool(self.states is not None and all(
            phantom + sum(owned for _, owned in rows) < limit
            for rows, phantom in self.states))


def concurrent_dispatch_allowed(snapshot, limit):
    """Keep every non-gathering row in the limit until it leaves the list.

    Blue icons can be returning troops or unrelated queues; their ownership is
    not established here, so count them conservatively instead of releasing a
    slot just because a green rally changed colour.
    """
    if snapshot is None or limit < 1 or not snapshot.free:
        return False
    if snapshot.evidence == 'hidden_idle':
        return snapshot.used == 0 and not snapshot.phases
    if (snapshot.evidence != 'numeric' or len(snapshot.phases) != snapshot.used
            or any(p not in ('gathering', 'blue', 'rallying', 'marching') for p in snapshot.phases)):
        return False
    return sum(p != 'gathering' for p in snapshot.phases) < limit


def confirms_new_concurrent_rally(before, after):
    """Prove a new rally under every compatible ordered row matching.

    This gate follows an already issued rally dispatch under the account's
    exclusive worker. Existing rallies may become marches, rows may disappear,
    and independent gathering/blue rows may change. An unexplained new green
    marching row is not treated as a new rally.
    """
    if before is None or after is None:
        return False
    if before.total and after.total != before.total:
        return False
    if after.evidence != 'numeric' or not 0 <= after.used <= after.total:
        return False
    if before.evidence == 'hidden_idle':
        if before.used or before.phases:
            return False
    elif before.evidence != 'numeric' or not 0 <= before.used <= before.total:
        return False
    allowed = {'gathering': ('gathering',), 'blue': ('blue',),
               'rallying': ('rallying', 'marching'), 'marching': ('marching', 'blue'),
               # A partially unreadable baseline can represent any existing
               # row. It cannot itself prove that a later row is new.
               'unknown': ('gathering', 'blue', 'rallying', 'marching')}
    if (len(before.phases) != before.used or len(after.phases) != after.used
            or any(p not in allowed for p in before.phases)
            or any(p not in ('gathering', 'blue', 'rallying', 'marching') for p in after.phases)):
        return False

    @lru_cache(maxsize=None)
    def matches(i, j, added):
        if i == len(before.phases) and j == len(after.phases):
            return frozenset((added,))
        outcomes = set()
        if i < len(before.phases):
            # A previously visible row can leave the compact list.
            outcomes.update(matches(i + 1, j, added))
            if j < len(after.phases) and after.phases[j] in allowed[before.phases[i]]:
                outcomes.update(matches(i + 1, j + 1, added))
        if j < len(after.phases):
            phase = after.phases[j]
            if phase in ('gathering', 'blue'):
                outcomes.update(matches(i, j + 1, added))
            elif phase == 'rallying' and not added:
                outcomes.update(matches(i, j + 1, True))
        return frozenset(outcomes)

    # If a matching without the dispatch exists, the new row is ambiguous.
    return matches(0, 0, False) == frozenset((True,))


def classify_concurrent_rows(capacity, icons, rallies, marches):
    """Classify a complete compact list; all coordinates are normalized."""
    if not capacity:
        return None
    if capacity.evidence == 'hidden_idle':
        return ConcurrentRallySnapshot(0, 0, 'hidden_idle', ()) if capacity.used == 0 and not icons and not rallies and not marches else None
    if capacity.evidence != 'numeric' or not 0 <= capacity.used <= capacity.total or capacity.total <= 0:
        return None
    if len(icons) != capacity.used or len({r.point for r in icons}) != len(icons):
        return None
    phases = []
    used_matches = set()
    for icon in icons:
        if icon.owner in ('blue', 'gathering'):
            phases.append(icon.owner)
            continue
        if icon.owner != 'own':
            return None
        matches = [(kind, i) for kind, rows in (('rallying', rallies), ('marching', marches))
                   for i, row in enumerate(rows)
                   if row.owner == 'own' and abs(row.point[0] - icon.point[0]) <= 60
                   and abs(row.point[1] - icon.point[1]) <= 55]
        if len(matches) != 1 or matches[0] in used_matches:
            return None
        used_matches.add(matches[0])
        phases.append(matches[0][0])
    if any(row.owner == 'unknown' for row in rallies):
        return None
    if sum(r.owner == 'own' for r in rallies) + len(marches) != len(used_matches):
        return None
    return ConcurrentRallySnapshot(capacity.used, capacity.total, capacity.evidence, tuple(phases))


def read_concurrent_snapshot(image):
    if not match_beast_rally_world_search(image)[0]:
        return None
    capacity = read_compact_capacity(image)
    if not capacity:
        return None
    viewport = content_viewport(image)
    def normalized(row):
        x, y = row.point
        return CompactRallyRow(row.owner, (round((x-viewport.left)*1440/viewport.width),
                                            round((y-viewport.top)*2560/viewport.height)), row.seconds, row.phase)
    return classify_concurrent_rows(capacity, read_compact_queue_icons(image, capacity),
                                    tuple(map(normalized, read_compact_rally_rows(image, read_timer=False))),
                                    tuple(map(normalized, read_compact_marching_rows(image))))


@lru_cache(maxsize=1)
def compact_rally_title() -> np.ndarray:
    with Image.open(resource_path("assets/beast_rally_compact_rallying_title.png")) as im:
        return np.asarray(im.convert('L').resize((143,36)))


def read_compact_rally_rows(image: Image.Image, *, read_timer: bool = True) -> tuple[CompactRallyRow, ...]:
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
        seconds = None
        if read_timer:
            timer = frame.crop((x-5,y+36,min(x+275,520),y+86))
            comps = _daily_white_numeric_components(timer)
            digits = [_read_daily_numeric_glyph(c[4]) for c in comps] if len(comps)==6 else []
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


@lru_cache(maxsize=1)
def soldier_type_templates():
    with Image.open(resource_path('assets/beast_soldier_types.png')) as source:
        image = source.convert('RGB')
        return tuple(np.asarray(image.crop((0, i * 50, 56, (i + 1) * 50))) for i in range(3))


def beast_soldier_rows(image: Image.Image):
    """Prove row types and read centered counts; unknown is never zero."""
    if match_beast_rally_formation_controls(image).state is not BeastRallyState.FORMATION:
        return None
    viewport = content_viewport(image)
    if viewport.width < 720 or abs(viewport.width / viewport.height - 9 / 16) > .008:
        return None
    frame = image.crop((viewport.left, viewport.top, viewport.right, viewport.bottom)).resize((1440, 2560)).convert('RGB')
    templates = soldier_type_templates()
    values = []
    for index, y in enumerate((1298, 1578, 1858)):
        icon = np.asarray(frame.crop((52, y, 108, y + 50)))
        scores = [float(cv2.matchTemplate(icon, t, cv2.TM_CCOEFF_NORMED)[0, 0]) for t in templates]
        if scores[index] < .94 or scores[index] < max(s for i, s in enumerate(scores) if i != index) + .08:
            return None
        glyphs = _daily_white_numeric_components(frame.crop((840, y - 3, 1065, y + 38)))
        if not 1 <= len(glyphs) <= 6:
            values.append(None)
            continue
        digits = [_read_daily_numeric_glyph(g[4]) for g in glyphs]
        start, end = glyphs[0][0], glyphs[-1][0] + glyphs[-1][2]
        if (not 94 <= (start + end) / 2 <= 131
                or any(not (8 <= g[2] <= 40 and 27 <= g[3] <= 40) for g in glyphs)
                or any(d is None or d[1] < .82 for d in digits)
                or any(glyphs[i+1][0] - (glyphs[i][0]+glyphs[i][2]) > 18 for i in range(len(glyphs)-1))):
            values.append(None)
        else:
            values.append(int(''.join(str(d[0]) for d in digits)))
    return tuple(values)


def _beast_total_digits(components):
    """Read total digits, including a tightly touching pair when unambiguous."""
    digits = []
    for _x, _y, width, height, glyph in components:
        if width < 45:
            reading = _read_daily_numeric_glyph(glyph)
            if reading is None or reading[1] < .82:
                return None
            digits.append(reading[0])
            continue
        if not (width <= 80 and 27 <= height <= 40):
            return None
        candidates = set()
        for split in range(12, width - 11):
            left = _read_daily_numeric_glyph(glyph[:, :split])
            right = _read_daily_numeric_glyph(glyph[:, split:])
            if left is not None and right is not None and min(left[1], right[1]) >= .92:
                candidates.add((left[0], right[0]))
        if len(candidates) != 1:
            return None
        digits.extend(next(iter(candidates)))
    return digits if 1 <= len(digits) <= 6 else None


def beast_first_visible_shield_row(image: Image.Image):
    """Locate the uppermost visible shield, proving earlier rows are other types."""
    viewport = content_viewport(image)
    if viewport.width < 720 or abs(viewport.width / viewport.height - 9 / 16) > .008:
        return None
    frame = image.crop((viewport.left, viewport.top, viewport.right, viewport.bottom)).resize((1440, 2560)).convert('RGB')
    for index, y in enumerate((1298, 1578, 1858)):
        area = np.asarray(frame.crop((44, y - 8, 116, y + 58)))
        scores = [float(cv2.minMaxLoc(cv2.matchTemplate(area, t, cv2.TM_CCOEFF_NORMED))[1])
                  for t in soldier_type_templates()]
        best = int(np.argmax(scores))
        if best == 0 and scores[0] >= .94 and scores[0] >= max(scores[1:]) + .08:
            return index
        if best == 0 or scores[best] < .84 or scores[best] < max(scores[i] for i in range(3) if i != best) + .08:
            return None
    return None


def beast_mixed_single_shield(image: Image.Image):
    """Read the total and first shield row without assuming one row per type.

    Clear-all is required when enabled; a disabled dispatch and exact zeroes
    prove the cleared state. An unreadable total or row remains unknown.
    """
    viewport = content_viewport(image)
    if viewport.width < 720 or abs(viewport.width / viewport.height - 9 / 16) > .008:
        return None
    frame = image.crop((viewport.left, viewport.top, viewport.right, viewport.bottom)).resize((1440, 2560)).convert('RGB')
    normal = match_beast_rally_formation_controls(image).state is BeastRallyState.FORMATION
    # Clearing troops disables dispatch and replaces "withdraw all" with
    # "quick select".  Prove this distinct state with both the page anchor
    # and its disabled dispatch label, then require exact zero counts below.
    if not normal:
        with Image.open(resource_path('assets/beast_rally_formation_anchor.png')) as source:
            anchor = np.asarray(source.convert('RGB'))
        with Image.open(resource_path('assets/beast_rally_dispatch_disabled.png')) as source:
            disabled = np.asarray(source.convert('RGB'))
        rgb = np.asarray(frame)
        region = rgb[:307, :662]
        if (cv2.minMaxLoc(cv2.matchTemplate(region, anchor, cv2.TM_CCOEFF_NORMED))[1] < .94
                or disabled.shape != rgb[2353:2429, 927:1247].shape
                or cv2.matchTemplate(rgb[2353:2429, 927:1247], disabled, cv2.TM_CCOEFF_NORMED)[0, 0] < .94
                or np.abs(rgb[2353:2429, 927:1247].astype(float) - disabled).mean() > 16):
            return None
    row_index = beast_first_visible_shield_row(image)
    if row_index is None:
        return None
    with Image.open(resource_path('assets/beast_withdraw_all.png')) as source:
        template = np.asarray(source.convert('RGB'))
    area = np.asarray(frame.crop((50, 2290, 220, 2530)))
    if normal and (area.shape != template.shape or float(cv2.matchTemplate(area, template, cv2.TM_CCOEFF_NORMED)[0, 0]) < .94):
        return None
    components = _daily_white_numeric_components(frame.crop((165, 355, 530, 420)))
    slashes = [i for i, item in enumerate(components) if _daily_numeric_component_is_slash(item[4])]
    if len(slashes) != 1:
        return None
    digits = components[:slashes[0]]
    if not 1 <= len(digits) <= 6:
        return None
    readings = _beast_total_digits(digits)
    if readings is None:
        return None
    total = int(''.join(str(d) for d in readings))
    row_y = 1295 + 280 * row_index
    glyphs = _daily_white_numeric_components(frame.crop((840, row_y, 1065, row_y + 41)))
    if not 1 <= len(glyphs) <= 6:
        return None
    row_digits = [_read_daily_numeric_glyph(g[4]) for g in glyphs]
    start, end = glyphs[0][0], glyphs[-1][0] + glyphs[-1][2]
    if (not 94 <= (start + end) / 2 <= 131
            or any(not (8 <= g[2] <= 40 and 27 <= g[3] <= 40) for g in glyphs)
            or any(d is None or d[1] < .82 for d in row_digits)
            or any(glyphs[i+1][0] - (glyphs[i][0]+glyphs[i][2]) > 20 for i in range(len(glyphs)-1))):
        return None
    row = int(''.join(str(d[0]) for d in row_digits))
    if row > total or (not normal and (total, row) != (0, 0)):
        return None
    return total, row, map_content_point((135, 2365), (1440, 2560), image)


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
