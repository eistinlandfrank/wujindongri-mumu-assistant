"""Account-scoped preparation leaderboard snapshots and conservative comparison."""
from __future__ import annotations

import csv
import hashlib
import json
import math
import os
import re
import tempfile
import uuid
import zipfile
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from xml.etree import ElementTree as ET

import numpy as np
from PIL import Image

from wjdr_backend import CONFIG_DIR, match_daily_regular_activity_back, match_world_control_interiors, resource_path

SNAPSHOT_ROOT = CONFIG_DIR / "preparation_snapshots"
NS = {"x": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}


def restore_ocr_coordinates(lines: list[dict], width: int, height: int) -> list[dict]:
    """Map WinRT's deskewed word coordinates back to the source image."""
    cx, cy = width / 2, height / 2
    restored = []
    for line in lines:
        angle = float(line.get('angle') or 0)
        cosine, sine = math.cos(math.radians(angle)), math.sin(math.radians(angle))
        words = []
        for word in line.get('words', []):
            dx, dy = word['x'] - cx, word['y'] - cy
            words.append(dict(word, x=cx + dx * cosine - dy * sine,
                              y=cy + dx * sine + dy * cosine))
        restored.append(dict(line, words=words))
    return restored


def account_dir(identity: str, root: Path = SNAPSHOT_ROOT) -> Path:
    if not re.fullmatch(r"mumu:\d+:android:[0-9a-f]+", identity):
        raise ValueError("无法确认模拟器实例和 Android ID，请重新连接该账号。")
    return root / hashlib.sha256(identity.encode("utf-8")).hexdigest()[:24]


def save_capture_draft(identity: str, rows: list[dict], draft_id: str, root: Path = SNAPSHOT_ROOT) -> None:
    """Persist unreviewed OCR separately from snapshots, with account binding."""
    if not re.fullmatch(r'[0-9a-f]{32}', draft_id):
        raise ValueError('采集草稿标识无效。')
    cleaned = validate_rows(rows)
    directory = account_dir(identity, root) / 'drafts'
    directory.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile('w', encoding='utf-8', dir=directory, suffix='.tmp', delete=False) as f:
        temporary = f.name
        try:
            json.dump({'schema': 1, 'identity': identity, 'rows': cleaned}, f, ensure_ascii=False)
            f.flush()
            os.fsync(f.fileno())
        except BaseException:
            os.unlink(temporary)
            raise
    os.replace(temporary, directory / (draft_id + '.json'))


def list_capture_drafts(identity: str, root: Path = SNAPSHOT_ROOT) -> list[dict]:
    directory = account_dir(identity, root) / 'drafts'
    result = []
    for path in directory.glob('*.json'):
        if not re.fullmatch(r'[0-9a-f]{32}', path.stem):
            continue
        try:
            data = json.loads(path.read_text(encoding='utf-8'))
            if data.get('schema') != 1 or data.get('identity') != identity:
                continue
            rows = validate_rows(data['rows'])
            modified = path.stat().st_mtime
        except (OSError, ValueError, KeyError, TypeError):
            continue
        result.append({'id': path.stem, 'rows': rows, 'modified': modified})
    return sorted(result, key=lambda item: item['modified'], reverse=True)


def load_latest_capture_draft(identity: str, root: Path = SNAPSHOT_ROOT) -> list[dict]:
    candidates = list_capture_drafts(identity, root)
    if not candidates:
        raise ValueError('当前账号没有可恢复的采集草稿。')
    return candidates[0]['rows']


def normalize_row(values: list | tuple) -> dict:
    if len(values) < 5:
        raise ValueError("每行需要排名、国家、联盟、玩家昵称和积分。")
    rank = int(str(values[0]).strip())
    country = str(values[1] or "").strip().replace("＃", "#")
    alliance = str(values[2] or "").strip().strip("[]［］")
    name = str(values[3] or "").strip()
    score = int(str(values[4]).replace(",", "").replace("，", "").strip())
    if not 1 <= rank <= 200 or not name or score < 0:
        raise ValueError("排名必须为 1–200，昵称不能为空，积分不能为负数。")
    if country and not re.fullmatch(r"#\d+", country):
        raise ValueError(f"国家格式不正确：{country}")
    return {"rank": rank, "country": country, "alliance": alliance, "name": name, "score": score}


def validate_rows(rows: list[dict]) -> list[dict]:
    cleaned = [normalize_row([r.get(k, "") for k in ("rank", "country", "alliance", "name", "score")]) for r in rows]
    ranks = [r["rank"] for r in cleaned]
    if not ranks or len(set(ranks)) != len(ranks):
        raise ValueError("快照不能为空，排名不能重复。")
    return sorted(cleaned, key=lambda r: r["rank"])


def save_snapshot(identity: str, rows: list[dict], label: str, root: Path = SNAPSHOT_ROOT) -> dict:
    cleaned = validate_rows(rows)
    directory = account_dir(identity, root)
    directory.mkdir(parents=True, exist_ok=True)
    snapshot = {"schema": 1, "identity": identity, "id": uuid.uuid4().hex,
                "created_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="microseconds"),
                "label": label.strip() or "备战榜快照", "complete": [r["rank"] for r in cleaned] == list(range(1, 201)),
                "rows": cleaned}
    target = directory / (snapshot["id"] + ".json")
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=directory, suffix=".tmp", delete=False) as f:
        temporary = f.name
        try:
            json.dump(snapshot, f, ensure_ascii=False, indent=2)
            f.flush()
            os.fsync(f.fileno())
        except BaseException:
            os.unlink(temporary)
            raise
    os.replace(temporary, target)
    return snapshot


def load_snapshots(identity: str, root: Path = SNAPSHOT_ROOT) -> list[dict]:
    directory = account_dir(identity, root)
    result = []
    for path in directory.glob("*.json"):
        data = json.loads(path.read_text(encoding="utf-8"))
        if data.get("identity") != identity or data.get("schema") != 1:
            raise ValueError(f"快照身份不一致或格式不支持：{path.name}")
        data["rows"] = validate_rows(data["rows"])
        result.append(data)
    return sorted(result, key=lambda s: (s["created_at"], s["id"]))


def identity_key(row: dict) -> tuple[str, str] | None:
    country = row["country"]
    name = row["name"].strip()
    # Unknown country or missing name cannot safely establish identity.
    return (country, name) if country and name else None


def compare_snapshots(old: dict, new: dict) -> dict:
    if old["identity"] != new["identity"]:
        raise ValueError("不能比较不同账号的快照。")
    before, after = old["rows"], new["rows"]
    count_old = Counter(identity_key(row) for row in before)
    count_new = Counter(identity_key(row) for row in after)
    eligible_old = {identity_key(r): r for r in before if identity_key(r) and count_old[identity_key(r)] == 1}
    eligible_new = {identity_key(r): r for r in after if identity_key(r) and count_new[identity_key(r)] == 1}
    changed = []
    for key in eligible_old.keys() & eligible_new.keys():
        if count_old[key] != 1 or count_new[key] != 1:
            continue
        a, b = eligible_old[key], eligible_new[key]
        delta = b["score"] - a["score"]
        if delta:
            changed.append({"old": a, "new": b, "delta": delta})
    changed.sort(key=lambda item: (-item["delta"], item["new"]["rank"], item["new"]["name"]))
    matched = eligible_old.keys() & eligible_new.keys()
    return {"changed": changed, "unmatched_old": [r for r in before if identity_key(r) not in matched],
            "unmatched_new": [r for r in after if identity_key(r) not in matched]}


def read_xlsx(path: str | Path) -> list[dict]:
    """Read the first plain worksheet; never execute macros or spreadsheet formulas."""
    with zipfile.ZipFile(path) as archive:
        shared = []
        if "xl/sharedStrings.xml" in archive.namelist():
            tree = ET.fromstring(archive.read("xl/sharedStrings.xml"))
            shared = ["".join(node.itertext()) for node in tree.findall("x:si", NS)]
        names = [n for n in archive.namelist() if re.fullmatch(r"xl/worksheets/sheet\d+\.xml", n)]
        if not names:
            raise ValueError("工作簿没有可读取的工作表。")
        sheet = ET.fromstring(archive.read(sorted(names)[0]))
        rows = []
        for element in sheet.findall(".//x:sheetData/x:row", NS):
            columns = {}
            for cell in element.findall("x:c", NS):
                col = re.match(r"[A-Z]+", cell.get("r", ""))
                if not col or cell.find("x:f", NS) is not None:
                    continue
                value = cell.findtext("x:v", "", NS)
                if cell.get("t") == "s":
                    value = shared[int(value)]
                elif cell.get("t") == "inlineStr":
                    value = "".join(cell.find("x:is", NS).itertext())
                columns[col.group()] = value
            try:
                rows.append(normalize_row([columns.get(c, "") for c in "ABCDE"]))
            except (ValueError, TypeError):
                continue
    return validate_rows(rows)


def read_csv(path: str | Path) -> list[dict]:
    rows = []
    with open(path, encoding="utf-8-sig", newline="") as f:
        for row in csv.reader(f):
            try:
                rows.append(normalize_row(row))
            except (ValueError, TypeError):
                continue
    return validate_rows(rows)


def prepare_badge_ocr(image: Image.Image) -> Image.Image:
    """Isolate white rank/country glyphs; output keeps OCR coordinates aligned."""
    width, height = image.size
    if abs(width / height - 1440 / 2560) > .01:
        raise ValueError("画面比例不是受支持的竖屏榜单比例。")
    normalized = image.convert("RGB").resize((1440, 2560))
    pixels = np.asarray(normalized)
    result = np.full((2560, 1440), 255, dtype=np.uint8)
    for x1, x2 in ((120, 310), (530, 685)):
        area = pixels[945:2105, x1:x2]
        result[945:2105, x1:x2] = np.where(np.min(area, axis=2) > 220, 0, 255)
    return Image.fromarray(result)


def prepare_rank_ocr(image: Image.Image) -> tuple[Image.Image, list[int]]:
    """Enlarge separate rank glyphs, retaining their original vertical positions."""
    pixels = np.asarray(image.convert('RGB').resize((1440, 2560)))
    bright = (np.min(pixels[950:2100, 160:285], axis=2) > 220).sum(axis=1) > 8
    starts = np.flatnonzero(bright & ~np.r_[False, bright[:-1]]) + 950
    ends = np.flatnonzero(bright & ~np.r_[bright[1:], False]) + 950
    spans = [(int(s), int(e)) for s, e in zip(starts, ends) if 35 <= e - s <= 70]
    # Horizontal tiles prevent Windows OCR from silently omitting closely
    # stacked lines; each tile still maps back to one observed rank position.
    tiles = Image.new('L', (max(400, len(spans) * 400), 150), 255)
    for index, (start, end) in enumerate(spans):
        crop = np.where(np.min(pixels[start:end + 1, 145:285], axis=2) > 220, 0, 255).astype(np.uint8)
        tiles.paste(Image.fromarray(crop).resize((280, (end - start + 1) * 2)), (index * 400 + 50, 20))
    return tiles, [s for s, _ in spans]


def read_rank_glyphs(image: Image.Image, positions: list[int]) -> dict[int, str]:
    """Read complete rank glyphs only when a curated mask matches decisively."""
    import cv2
    try:
        atlas = np.asarray(Image.open(resource_path('assets/scoreboard_rank_digits.png')).convert('L')) > 0
        if atlas.shape != (64, 640):
            return {}
        pixels = np.asarray(image.convert('RGB').resize((1440, 2560)))
        templates = [atlas[:, digit * 64:(digit + 1) * 64] for digit in range(10)]
        result = {}
        for index, y in enumerate(positions):
            mask = (np.min(pixels[y:y + 70, 145:285], axis=2) > 220).astype('uint8')
            _, labels, stats, _ = cv2.connectedComponentsWithStats(mask)
            parts = sorted([(x, yy, w, h, i) for i, (x, yy, w, h, area) in enumerate(stats)
                            if i and h > 30 and w > 5], key=lambda part: part[0])
            if not 1 <= len(parts) <= 3:
                continue
            digits = []
            for x, yy, w, h, component in parts:
                if w > 48 or h > 55:
                    break
                glyph = np.zeros((64, 64), dtype=bool)
                glyph[4:4+h, 4:4+w] = labels[yy:yy+h, x:x+w] == component
                # A one-pixel translation accommodates antialiasing and y rounding.
                similarities = []
                for template in templates:
                    best = 0.0
                    for dy in (-1, 0, 1):
                        for dx in (-1, 0, 1):
                            shifted = np.roll(glyph, (dy, dx), axis=(0, 1))
                            union = np.count_nonzero(shifted | template)
                            best = max(best, np.count_nonzero(shifted & template) / union if union else 0.0)
                    similarities.append(best)
                ordered = sorted(range(10), key=lambda digit: similarities[digit], reverse=True)
                if similarities[ordered[0]] < .82 or similarities[ordered[0]] - similarities[ordered[1]] < .08:
                    break
                digits.append(str(ordered[0]))
            value = ''.join(digits)
            if len(digits) == len(parts) and value and 1 <= int(value) <= 200:
                result[index] = value
        return result
    except (OSError, ValueError):
        return {}


def merge_rank_ocr(badges: list[dict], ranks: list[dict], rank_positions: list[int], glyphs: dict[int, str] | None = None) -> list[dict]:
    """Map tile readings back to frame coordinates; conflicting readings are rejected."""
    original = [w for line in badges for w in line.get('words', [])]
    words = [w for w in original if not 150 <= w['x'] < 285]
    by_tile: dict[int, list[str]] = {}
    for line in ranks:
        for word in line.get('words', []):
            index = int(word['x'] // 400)
            if 0 <= index < len(rank_positions):
                by_tile.setdefault(index, []).append(word['text'])
    for index, position in enumerate(rank_positions):
        tile = ''.join(by_tile.get(index, [])).upper().translate(str.maketrans({'O': '0', 'I': '1', 'L': '1'}))
        nearby = [w for w in original if 150 <= w['x'] < 285 and abs(w['y'] - position) < 70]
        raw = ''.join(w['text'] for w in sorted(nearby, key=lambda w: w['x']))
        valid = lambda s: bool(re.fullmatch(r'\d{1,3}', s)) and 1 <= int(s) <= 200
        tile = tile if valid(tile) else ''
        raw = raw if valid(raw) else ''
        visual = (glyphs or {}).get(index, '')
        value = visual or tile or raw
        if value and (visual or not (tile and raw and tile != raw)):
            words.append({'text': value, 'x': 200, 'y': position})
    # The first few medal rows and some single digits have no tile span.
    words.extend(w for w in original if 150 <= w['x'] < 285 and all(abs(w['y'] - p) >= 70 for p in rank_positions))
    return [{'text': '', 'words': words}]


def validate_total_selection(image: Image.Image) -> None:
    """Reject a phase-specific or war-stage view before treating data as total."""
    if abs(image.width / image.height - 1440 / 2560) > .01:
        raise ValueError('画面比例不是受支持的竖屏榜单比例。')
    pixels = np.asarray(image.convert('RGB').resize((1440, 2560))).astype(np.int16)
    overall = pixels[545:650, 1140:1320]
    orange = ((overall[:, :, 0] > 150) & (overall[:, :, 0] > overall[:, :, 1] * 1.3)
              & (overall[:, :, 1] > 45) & (overall[:, :, 1] < 150) & (overall[:, :, 2] < 100))
    tab = pixels[350:460, 150:680]
    pale = (tab[:, :, 0] > 190) & (tab[:, :, 1] > 200) & (tab[:, :, 2] > 205)
    if orange.mean() < .4 or pale.mean() < .5:
        raise ValueError('请在个人积分排名中选中「备战阶段」和最右侧的总榜按钮，再识别。')


def navigation_decision(image: Image.Image, lines: list[dict]) -> tuple[str, tuple[int, ...]] | None:
    """Only expose reviewed navigation actions backed by a fresh visible page."""
    if abs(image.width / image.height - 1440 / 2560) > .01:
        return None
    frame = image.convert('RGB').resize((1440, 2560))
    pixels = np.asarray(frame)
    def locate(needle, x1, y1, x2, y2):
        for line in lines:
            words = line.get('words', [])
            if not words:
                continue
            text = ''.join(w.get('text', '') for w in sorted(words, key=lambda w: w['x'])).replace(' ', '')
            x, y = min(w['x'] for w in words), min(w['y'] for w in words)
            if needle in text and x1 <= x < x2 and y1 <= y < y2:
                return words
        return None
    # A reviewed startup sales sheet may cover all navigation after reconnect.
    # Require both its exact title and the exact close glyph; never use the
    # purchase control or dismiss an unrecognised overlay.
    if locate('铸匠的珍藏', 0, 320, 520, 500):
        close = np.asarray(Image.open(resource_path('assets/scoreboard_shop_close.png')).convert('RGB'))
        area = pixels[395:520, 1275:1390]
        if close.shape == area.shape and np.abs(area.astype(np.int16) - close.astype(np.int16)).mean() < 8:
            return 'close_known_shop', (1332, 457)
        return None
    title = locate('个人积分排名', 400, 150, 1000, 320)
    preparation = (locate('备战阶段', 200, 320, 600, 480) or
                   locate('备找阶段', 200, 320, 600, 480))
    if title and preparation:
        tab = pixels[350:460, 150:680]
        pale = (tab[:, :, 0] > 190) & (tab[:, :, 1] > 200) & (tab[:, :, 2] > 205)
        if pale.mean() < .5:
            war = pixels[350:460, 750:1280]
            war_pale = (war[:, :, 0] > 190) & (war[:, :, 1] > 200) & (war[:, :, 2] > 205)
            if locate('战争阶段', 750, 320, 1250, 480) and war_pale.mean() > .5:
                return 'select_preparation', (400, 420)
            return None
        try:
            validate_total_selection(frame)
            return 'ready', ()
        except ValueError:
            return 'select_total', (1230, 600)
    header = locate('常规活动', 0, 0, 500, 150)
    if header:
        # The reviewed back/title templates also reject dimmed overlays.
        if not match_daily_regular_activity_back(frame, .985)[0]:
            return None
        personal = locate('个人积分排行', 700, 900, 1080, 1200)
        alliance = locate('联盟积分排行', 1080, 900, 1400, 1200)
        popup = pixels[950:1190, 740:1380]
        if personal and alliance and (np.min(popup, axis=2) > 190).mean() > .5:
            return 'open_personal', (890, 1035)
        kingdom = locate('最强王国', 50, 350, 500, 550)
        ranking = locate('排行榜', 800, 750, 1150, 900)
        prep = locate('备战阶段', 200, 1000, 650, 1200)
        prep_area = pixels[1060:1190, 100:650]
        visible_prep = ((prep_area[:, :, 0] > 210) & (prep_area[:, :, 1] > 145)).mean() > .35
        substage = locate('子阶段目标', 700, 1000, 1400, 1200)
        substage_area = pixels[1060:1190, 740:1350]
        visible_substage = ((substage_area[:, :, 0] > 210) & (substage_area[:, :, 1] > 145)).mean() > .35
        if kingdom and ranking and prep and (visible_prep or (substage and visible_substage)):
            return 'open_ranking', (1245, 930)
        known_activity = (locate('联盟争霸赛', 300, 350, 1100, 700) or
                          locate('佣兵荣耀', 100, 370, 1200, 800) or
                          locate('巨熊行动', 100, 370, 1200, 800))
        if not known_activity:
            return None
        tab = locate('最强王国', 100, 160, 1300, 370)
        if tab:
            x = round((min(w['x'] for w in tab) + max(w['x'] + w.get('width', 0) for w in tab)) / 2)
            return 'open_kingdom', (x, 280)
        return 'find_kingdom_tab', (350, 280, 1150, 280)
    town, lens, _ = match_world_control_interiors(frame)
    if town and lens:
        reference = np.asarray(Image.open(resource_path('assets/scoreboard_activity_icon.png')).convert('RGB'))
        patch = pixels[255:335, 1290:1360]
        error = np.abs(patch.astype(np.int16) - reference.astype(np.int16)).mean()
        if error < 8:
            return 'open_activities', (1325, 295)
    return None


def ranks_advance(previous: list[int], current: list[int]) -> bool:
    """The next frame must show forward progress without an unseen rank gap."""
    if not previous or not current or current != list(range(min(current), max(current) + 1)):
        return False
    return max(current) > max(previous) and min(current) <= max(previous) + 1 and max(current) - max(previous) <= 4


def score_line_value(line: dict) -> int | None:
    words = [w['text'].replace(' ', '').replace('，', ',')
             for w in sorted(line.get('words', []), key=lambda w: w['x']) if 520 <= w['x'] < 1000]
    value = ''.join(words)
    if re.fullmatch(r'\d{1,3}(?:,\d{3})+', value):
        return int(value.replace(',', ''))
    # OCR may drop only a comma while still producing separate numeric groups.
    # Require every digit group, in order and at the standard thousands width.
    if any(not re.fullmatch(r'\d+|,', word) for word in words):
        return None
    groups = [word for word in words if word != ',']
    if len(groups) >= 2 and 1 <= len(groups[0]) <= 3 and all(len(group) == 3 for group in groups[1:]):
        return int(''.join(groups))
    return None


def is_score_line(line: dict) -> bool:
    return score_line_value(line) is not None


def missing_name_score_positions(text_lines: list[dict]) -> list[int]:
    """Identify visible score rows for which full-frame OCR missed the name."""
    positions = []
    for line in text_lines:
        words = line.get('words', [])
        if not words:
            continue
        y = min(word['y'] for word in words)
        if not 1100 <= y < 2100 or not is_score_line(line):
            continue
        if not any(685 <= w['x'] < 1350 and y - 125 <= w['y'] <= y - 35
                   for other in text_lines for w in other.get('words', [])):
            positions.append(y)
    return positions[:4]


def split_ocr_alliance(text: str) -> tuple[str, str]:
    """Propose a split for review, including common OCR bracket confusions."""
    match = re.match(r'^\[([^\]]+)\](.+)$', text)
    if not match:
        match = re.match(r'^[\[I]([A-Za-z0-9×]{2,4})[\]lI刂](.+)$', text)
    return match.groups() if match else ('', text)


def candidate_rows(text_lines: list[dict], badge_lines: list[dict]) -> list[dict]:
    """Return unverified OCR suggestions; every field needs human review."""
    def joined(words):
        return ''.join(w['text'] for w in sorted(words, key=lambda w: w['x'])).replace(' ', '')

    header = ''.join(line['text'].replace(' ', '') for line in text_lines if any(w['y'] < 500 for w in line['words']))
    if '个人积分排名' not in header or not ('备战阶段' in header or '备找阶段' in header):
        raise ValueError('未识别到备战阶段的个人积分排名画面。')
    badge_words = [word for line in badge_lines for word in line['words']]
    result = []
    for line in sorted(text_lines, key=lambda item: min((w['y'] for w in item.get('words', [])), default=99999)):
        words = line['words']
        if not words:
            continue
        y = min(word['y'] for word in words)
        value = score_line_value(line)
        if not 1000 <= y < 2100 or value is None:
            continue
        name_words = [w for other in text_lines for w in other['words']
                      if 685 <= w['x'] < 1350 and y - 125 <= w['y'] <= y - 35]
        if not name_words or min(w['y'] for w in name_words) < 960:
            continue  # clipped by the top of the scrollable list
        name_text = joined(name_words)
        alliance, name = split_ocr_alliance(name_text)
        rank_words = [w for w in badge_words if 150 <= w['x'] < 285 and y - 100 <= w['y'] <= y]
        country_words = [w for w in badge_words if 530 <= w['x'] < 685 and y - 145 <= w['y'] <= y]
        rank = joined(rank_words)
        country = joined(country_words)
        if not re.fullmatch(r'\d{1,3}', rank) or not 1 <= int(rank) <= 200:
            rank = ''
        if not re.fullmatch(r'#\d+', country):
            # Some light badges are clearer to the original colour OCR than
            # to the white-glyph pass; accept only the same-row exact form.
            country = joined([w for other in text_lines for w in other['words']
                              if 530 <= w['x'] < 685 and y - 145 <= w['y'] <= y - 35])
            if not re.fullmatch(r'#\d+', country):
                country = ''
        if name:
            result.append({'rank': rank, 'country': country, 'alliance': alliance,
                           'name': name, 'score': value})
    return result
