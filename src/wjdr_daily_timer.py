"""Read and persist account-scoped Daily countdowns without guessing a phase.

The OCR helper is read-only. Callers own page/identity proof and input leases.
In particular, a march duration is not a gathering duration.
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
import json
import math
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile

from PIL import Image, ImageOps

_TIME = re.compile(r'(?<![0-9A-Za-z])(\d{1,3}):(\d{2}):(\d{2})(?![0-9A-Za-z])')


@dataclass(frozen=True)
class Countdown:
    seconds: int
    observed_at: float
    due_at: float


def parse_countdown_text(text: str) -> int | None:
    """Accept one unambiguous HH:MM:SS reading; never repair OCR digits."""
    normalized = re.sub(r'\s+', '', str(text)).replace('：', ':')
    found = _TIME.findall(normalized)
    if len(found) != 1:
        return None
    hours, minutes, seconds = map(int, found[0])
    if hours > 168 or minutes >= 60 or seconds >= 60:
        return None
    return hours * 3600 + minutes * 60 + seconds


def consistent_countdown(first: int | None, second: int | None,
                         first_at: float, second_at: float) -> Countdown | None:
    """Require two fresh, plausible non-increasing timer observations."""
    if first is None or second is None or not all(math.isfinite(x) for x in (first_at, second_at)):
        return None
    elapsed = second_at - first_at
    if elapsed < 0 or elapsed > 15 or second > first or first - second > math.ceil(elapsed) + 2:
        return None
    return Countdown(second, second_at, second_at + second)


def _read_ocr_lines(image: Image.Image, *, timeout: float = 5.0) -> list[str]:
    """Read a tightly cropped value; failures are never interpreted as zero."""
    if sys.platform != 'win32':
        return []
    from wjdr_backend import resource_path

    script = resource_path('assets/scoreboard_ocr.ps1')
    if not script.is_file() or image.width < 20 or image.height < 10:
        return []
    try:
        with tempfile.TemporaryDirectory(prefix='wjdr_timer_') as directory:
            path = Path(directory) / 'timer.png'
            prepared = image.convert('RGB')
            if prepared.width < 200:
                factor = 640 / prepared.width
                prepared = prepared.resize((640, max(1, round(prepared.height * factor))), Image.Resampling.LANCZOS)
                prepared = ImageOps.expand(prepared, border=20, fill='white')
            prepared.save(path)
            output = subprocess.run(
                ['powershell', '-NoProfile', '-NonInteractive', '-ExecutionPolicy', 'Bypass',
                 '-File', str(script), '-ImagePath', str(path)],
                capture_output=True, timeout=min(8.0, max(0.1, float(timeout))),
                creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0), check=False,
            )
            if output.returncode:
                return []
            lines = json.loads(output.stdout.decode('utf-8-sig'))
            if isinstance(lines, dict):
                lines = [lines]
            return [str(row.get('text', '')) for row in lines if isinstance(row, dict)]
    except (OSError, ValueError, TypeError, subprocess.TimeoutExpired, json.JSONDecodeError):
        return []


def read_countdown(image: Image.Image, *, timeout: float = 5.0) -> int | None:
    """Use packaged Windows OCR on a tight image; reject ambiguous readings."""
    readings = [value for text in _read_ocr_lines(image, timeout=timeout)
                if (value := parse_countdown_text(text)) is not None]
    return readings[0] if len(readings) == 1 else None


def read_countdown_pair(first: Image.Image, second: Image.Image,
                        first_at: float, second_at: float) -> Countdown | None:
    with ThreadPoolExecutor(max_workers=2) as executor:
        first_seconds, second_seconds = executor.map(read_countdown, (first, second))
    return consistent_countdown(first_seconds, second_seconds, first_at, second_at)


def donation_recovery_crop(image: Image.Image, viewport: tuple[int, int, int, int]) -> Image.Image:
    """Crop the cooldown digits directly below the disabled donation button row."""
    left, top, right, bottom = viewport
    width, height = right - left, bottom - top
    return image.crop((left + round(width * .25), top + round(height * .858),
                       left + round(width * .75), top + round(height * .900)))
