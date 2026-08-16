# -*- coding: utf-8 -*-
"""Fast, read-only visual inspection tools for WJDR MuMu evidence.

The production assistant deliberately favours conservative, individually
reviewed recognisers.  Research and debugging have a different bottleneck:
one screen is often compared with dozens of known assets, and the legacy
``match_template`` helper reloads and converts both images for every match.

This module prepares a frame once, preloads templates once, caches resized
templates by viewport size, and runs independent OpenCV matches concurrently.
It never emits ADB input commands.  ADB support is limited to ``screencap``.
"""

from __future__ import annotations

import argparse
import io
import json
import math
import os
import re
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable, Sequence

import cv2
import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageStat

from wjdr_backend import (
    BUILTIN_ALL_HELP_TEMPLATE_ASSET,
    BUILTIN_ALL_HELP_TEMPLATE_NAME,
    BUILTIN_HELP_REFERENCE_SIZE,
    BUILTIN_HELP_TEMPLATE_ASSET,
    BUILTIN_HELP_TEMPLATE_NAME,
    CREATE_NO_WINDOW,
    DAILY_BUILTIN_TEMPLATES,
    BUILTIN_DAILY_TASK_REFERENCE_SIZE,
    RED_PACKET_BUILTIN_TEMPLATES,
    content_viewport,
    resource_path,
    template_reference_size,
)


DEFAULT_ADB = r"C:\Program Files\Netease\MuMuPlayerGlobal-12.0\shell\adb.exe"
DEFAULT_DEVICE = "127.0.0.1:16416"
DEFAULT_SAFE_RELATIVE_BOX = (0.03, 0.25, 0.97, 0.86)


@dataclass(frozen=True)
class TemplateSpec:
    key: str
    asset: str
    display_name: str
    path: Path
    reference_size: tuple[int, int] | None


@dataclass(frozen=True)
class MatchResult:
    key: str
    display_name: str
    asset: str
    score: float
    hit: bool
    center: tuple[int, int] | None
    box: tuple[int, int, int, int] | None
    scale: float
    elapsed_ms: float


@dataclass(frozen=True)
class DiffResult:
    mean_change: float
    changed_pixel_ratio: float
    max_channel_change: int
    box: tuple[int, int, int, int]


@dataclass
class PreparedFrame:
    image: Image.Image
    gray: np.ndarray
    viewport: tuple[int, int, int, int]

    @classmethod
    def from_image(cls, image: Image.Image) -> "PreparedFrame":
        rgb = image.convert("RGB")
        array = np.asarray(rgb)
        gray = cv2.cvtColor(array, cv2.COLOR_RGB2GRAY)
        viewport = content_viewport(rgb)
        return cls(rgb, gray, (viewport.left, viewport.top, viewport.right, viewport.bottom))


def builtin_template_specs(pattern: str | None = None) -> list[TemplateSpec]:
    """Return bundled template metadata without copying assets to AppData."""
    entries: list[tuple[str, str]] = [
        (BUILTIN_ALL_HELP_TEMPLATE_ASSET, BUILTIN_ALL_HELP_TEMPLATE_NAME),
        (BUILTIN_HELP_TEMPLATE_ASSET, BUILTIN_HELP_TEMPLATE_NAME),
        *RED_PACKET_BUILTIN_TEMPLATES,
        *DAILY_BUILTIN_TEMPLATES,
    ]
    matcher = re.compile(pattern, re.IGNORECASE) if pattern else None
    specs: list[TemplateSpec] = []
    seen: set[str] = set()
    for asset, display_name in entries:
        path = resource_path(asset)
        key = Path(asset).stem
        if key in seen or not path.is_file():
            continue
        searchable = f"{key} {asset} {display_name}"
        if matcher and not matcher.search(searchable):
            continue
        reference = template_reference_size(path)
        if reference is None and asset in {
            BUILTIN_ALL_HELP_TEMPLATE_ASSET,
            BUILTIN_HELP_TEMPLATE_ASSET,
        }:
            reference = BUILTIN_HELP_REFERENCE_SIZE
        specs.append(TemplateSpec(key, asset, display_name, path, reference))
        seen.add(key)
    # Research captures are intentionally allowed to exist before they are
    # promoted into the production recogniser registry.  Include unregistered
    # PNG assets as analysis-only templates; Daily-prefixed captures inherit
    # the game's reviewed 1440x2560 reference geometry.
    asset_root = resource_path("assets")
    if asset_root.is_dir():
        for path in sorted(asset_root.glob("*.png")):
            key = path.stem
            if key in seen:
                continue
            searchable = f"{key} {path.name}"
            if matcher and not matcher.search(searchable):
                continue
            reference = (
                BUILTIN_DAILY_TASK_REFERENCE_SIZE
                if key.startswith("daily_")
                else template_reference_size(path)
            )
            specs.append(TemplateSpec(key, f"assets/{path.name}", path.name, path, reference))
            seen.add(key)
    return specs


class FastVisionEngine:
    """Preloaded, cached batch matcher for repeated inspection."""

    def __init__(self, specs: Sequence[TemplateSpec], workers: int | None = None) -> None:
        if not specs:
            raise ValueError("No templates selected")
        started = time.perf_counter()
        self.specs = list(specs)
        self.workers = max(1, int(workers or min(8, os.cpu_count() or 1)))
        self._base_gray: dict[str, np.ndarray] = {}
        self._scaled_gray: dict[tuple[str, int, int], np.ndarray] = {}
        for spec in self.specs:
            with Image.open(spec.path) as image:
                rgb = np.asarray(image.convert("RGB"))
            self._base_gray[spec.key] = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
        self.preload_ms = (time.perf_counter() - started) * 1000.0

    @staticmethod
    def _scale_candidates(
        spec: TemplateSpec,
        viewport: tuple[int, int, int, int],
        mode: str,
    ) -> list[float]:
        if not spec.reference_size:
            return [1.0]
        left, top, right, bottom = viewport
        viewport_width, viewport_height = right - left, bottom - top
        ref_width, ref_height = spec.reference_size
        width_scale = viewport_width / ref_width
        height_scale = viewport_height / ref_height
        geometric = math.sqrt(width_scale * height_scale)
        if mode == "fast":
            return [geometric]
        candidates: list[float] = []
        for base in (width_scale, height_scale, geometric, min(width_scale, height_scale)):
            for adjustment in (0.96, 1.0, 1.04):
                candidate = base * adjustment
                if 0.25 <= candidate <= 2.5 and all(abs(candidate - old) >= 0.015 for old in candidates):
                    candidates.append(candidate)
        return candidates or [1.0]

    def _scaled(self, spec: TemplateSpec, scale: float) -> np.ndarray:
        base = self._base_gray[spec.key]
        base_height, base_width = base.shape[:2]
        width, height = max(8, round(base_width * scale)), max(8, round(base_height * scale))
        cache_key = (spec.key, width, height)
        cached = self._scaled_gray.get(cache_key)
        if cached is not None:
            return cached
        if (width, height) == (base_width, base_height):
            resized = base
        else:
            resized = cv2.resize(
                base,
                (width, height),
                interpolation=cv2.INTER_AREA if scale < 1.0 else cv2.INTER_CUBIC,
            )
        self._scaled_gray[cache_key] = resized
        return resized

    def _match_one(
        self,
        frame: PreparedFrame,
        spec: TemplateSpec,
        threshold: float,
        mode: str,
        region: tuple[int, int, int, int] | None,
    ) -> MatchResult:
        started = time.perf_counter()
        screen = frame.gray
        offset_x = offset_y = 0
        if region:
            x0, y0, x1, y1 = clamp_box(region, frame.image.size)
            if x1 <= x0 or y1 <= y0:
                return MatchResult(spec.key, spec.display_name, spec.asset, 0.0, False, None, None, 1.0, 0.0)
            screen = screen[y0:y1, x0:x1]
            offset_x, offset_y = x0, y0
        screen_height, screen_width = screen.shape[:2]
        best_score = -1.0
        best_location = (0, 0)
        best_shape = (0, 0)
        best_scale = 1.0
        for scale in self._scale_candidates(spec, frame.viewport, mode):
            template = self._scaled(spec, scale)
            height, width = template.shape[:2]
            if width > screen_width or height > screen_height:
                continue
            result = cv2.matchTemplate(screen, template, cv2.TM_CCOEFF_NORMED)
            _minimum, score, _minimum_location, location = cv2.minMaxLoc(result)
            if score > best_score:
                best_score = float(score)
                best_location = location
                best_shape = (width, height)
                best_scale = scale
        elapsed_ms = (time.perf_counter() - started) * 1000.0
        if best_score < 0.0:
            return MatchResult(spec.key, spec.display_name, spec.asset, 0.0, False, None, None, best_scale, elapsed_ms)
        width, height = best_shape
        left, top = offset_x + best_location[0], offset_y + best_location[1]
        box = (left, top, left + width, top + height)
        center = (left + width // 2, top + height // 2)
        return MatchResult(
            spec.key,
            spec.display_name,
            spec.asset,
            best_score,
            best_score >= threshold,
            center,
            box,
            best_scale,
            elapsed_ms,
        )

    def inspect(
        self,
        image: Image.Image,
        *,
        threshold: float = 0.90,
        mode: str = "fast",
        region: tuple[int, int, int, int] | None = None,
    ) -> tuple[PreparedFrame, list[MatchResult], float]:
        if mode not in {"fast", "robust"}:
            raise ValueError("mode must be 'fast' or 'robust'")
        started = time.perf_counter()
        frame = PreparedFrame.from_image(image)
        if self.workers == 1 or len(self.specs) == 1:
            results = [self._match_one(frame, spec, threshold, mode, region) for spec in self.specs]
        else:
            with ThreadPoolExecutor(max_workers=min(self.workers, len(self.specs))) as executor:
                futures = [
                    executor.submit(self._match_one, frame, spec, threshold, mode, region)
                    for spec in self.specs
                ]
                results = [future.result() for future in futures]
        results.sort(key=lambda item: item.score, reverse=True)
        total_ms = (time.perf_counter() - started) * 1000.0
        return frame, results, total_ms


def capture_adb(device: str, adb_path: str = DEFAULT_ADB, timeout: float = 20.0) -> Image.Image:
    """Capture one frame.  This function has no ADB input command path."""
    command = [adb_path, "-s", device, "exec-out", "screencap", "-p"]
    try:
        process = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout,
            creationflags=CREATE_NO_WINDOW,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise RuntimeError(f"ADB screenshot failed: {exc}") from exc
    if process.returncode != 0:
        error = process.stderr.decode("utf-8", "replace").strip()
        raise RuntimeError(error or f"ADB screenshot returned {process.returncode}")
    try:
        image = Image.open(io.BytesIO(process.stdout))
        image.load()
        return image.convert("RGB")
    except Exception as exc:
        raise RuntimeError(f"ADB screenshot parse failed: {exc}") from exc


def load_image(path: Path) -> Image.Image:
    with Image.open(path) as image:
        return image.convert("RGB")


def clamp_box(box: tuple[int, int, int, int], size: tuple[int, int]) -> tuple[int, int, int, int]:
    width, height = size
    left, top, right, bottom = box
    return (
        max(0, min(width, int(left))),
        max(0, min(height, int(top))),
        max(0, min(width, int(right))),
        max(0, min(height, int(bottom))),
    )


def relative_box(image: Image.Image, values: Sequence[float]) -> tuple[int, int, int, int]:
    if len(values) != 4:
        raise ValueError("A relative box needs four values")
    viewport = content_viewport(image)
    left, top, right, bottom = (float(value) for value in values)
    return (
        viewport.left + round(viewport.width * left),
        viewport.top + round(viewport.height * top),
        viewport.left + round(viewport.width * right),
        viewport.top + round(viewport.height * bottom),
    )


def parse_box(value: str) -> tuple[int, int, int, int]:
    parts = [part.strip() for part in value.split(",")]
    if len(parts) != 4:
        raise argparse.ArgumentTypeError("box must be left,top,right,bottom")
    try:
        return tuple(int(part) for part in parts)  # type: ignore[return-value]
    except ValueError as exc:
        raise argparse.ArgumentTypeError("box values must be integers") from exc


def parse_relative_box(value: str) -> tuple[float, float, float, float]:
    parts = [part.strip() for part in value.split(",")]
    if len(parts) != 4:
        raise argparse.ArgumentTypeError("relative box must have four comma-separated values")
    try:
        values = tuple(float(part) for part in parts)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("relative box values must be numbers") from exc
    if any(number < 0.0 or number > 1.0 for number in values):
        raise argparse.ArgumentTypeError("relative box values must be between 0 and 1")
    return values  # type: ignore[return-value]


def region_diff(
    before: Image.Image,
    after: Image.Image,
    box: tuple[int, int, int, int],
    pixel_threshold: int = 12,
) -> DiffResult:
    if before.size != after.size:
        raise ValueError("Images must have the same size")
    box = clamp_box(box, before.size)
    before_crop = before.convert("RGB").crop(box)
    after_crop = after.convert("RGB").crop(box)
    difference = ImageChops.difference(before_crop, after_crop)
    mean_change = sum(ImageStat.Stat(difference).mean) / 3.0
    array = np.asarray(difference)
    changed = np.any(array >= int(pixel_threshold), axis=2)
    return DiffResult(
        mean_change=float(mean_change),
        changed_pixel_ratio=float(changed.mean()) if changed.size else 0.0,
        max_channel_change=int(array.max()) if array.size else 0,
        box=box,
    )


def annotate(image: Image.Image, results: Iterable[MatchResult], limit: int = 20) -> Image.Image:
    output = image.convert("RGB").copy()
    draw = ImageDraw.Draw(output)
    for index, result in enumerate(item for item in results if item.hit):
        if index >= limit or result.box is None:
            break
        colour = (67, 220, 145) if index == 0 else (255, 190, 70)
        draw.rectangle(result.box, outline=colour, width=4)
        left, top, _right, _bottom = result.box
        label = f"{result.key} {result.score:.3f}"
        draw.rectangle((left, max(0, top - 24), left + min(620, 8 * len(label)), top), fill=(10, 20, 36))
        draw.text((left + 3, max(0, top - 21)), label, fill=colour)
    return output


def result_payload(
    source: str,
    image: Image.Image,
    engine: FastVisionEngine,
    results: Sequence[MatchResult],
    total_ms: float,
    mode: str,
    threshold: float,
) -> dict[str, object]:
    return {
        "captured_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "source": source,
        "screen_size": list(image.size),
        "template_count": len(results),
        "threshold": threshold,
        "mode": mode,
        "preload_ms": round(engine.preload_ms, 3),
        "inspect_ms": round(total_ms, 3),
        "hits": [asdict(result) for result in results if result.hit],
        "ranking": [asdict(result) for result in results],
    }


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def print_results(results: Sequence[MatchResult], total_ms: float, top: int) -> None:
    print(f"inspect_ms={total_ms:.2f} templates={len(results)}")
    print("score  hit  center       template")
    for result in results[: max(1, top)]:
        center = "-" if result.center is None else f"{result.center[0]},{result.center[1]}"
        print(f"{result.score:0.4f}  {'yes' if result.hit else ' no'}  {center:<12} {result.key}")


def add_match_arguments(parser: argparse.ArgumentParser) -> None:
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--image", type=Path, help="offline PNG/JPEG screenshot")
    source.add_argument("--device", help=f"read one ADB frame, for example {DEFAULT_DEVICE}")
    parser.add_argument("--adb", default=DEFAULT_ADB, help="ADB executable path")
    parser.add_argument("--pattern", default="daily", help="regex applied to template id/path/name")
    parser.add_argument("--threshold", type=float, default=0.94)
    parser.add_argument("--mode", choices=("fast", "robust"), default="fast")
    parser.add_argument("--workers", type=int, default=0, help="0 selects up to eight workers")
    parser.add_argument("--region", type=parse_box, help="absolute search box: left,top,right,bottom")
    parser.add_argument("--top", type=int, default=20)
    parser.add_argument("--json-out", type=Path)
    parser.add_argument("--annotated-out", type=Path, help="writes a full/private annotated image")
    parser.add_argument("--safe-crop-out", type=Path, help="writes only a central de-identified crop")
    parser.add_argument(
        "--safe-relative-box",
        type=parse_relative_box,
        default=DEFAULT_SAFE_RELATIVE_BOX,
        help="content-relative safe crop, default 0.03,0.25,0.97,0.86",
    )


def command_inspect(args: argparse.Namespace) -> int:
    specs = builtin_template_specs(args.pattern)
    if not specs:
        raise RuntimeError(f"No built-in templates match pattern: {args.pattern}")
    engine = FastVisionEngine(specs, args.workers or None)
    if args.image:
        image = load_image(args.image)
        source = str(args.image.resolve())
    else:
        image = capture_adb(args.device, args.adb)
        source = f"adb:{args.device}"
    _frame, results, total_ms = engine.inspect(
        image,
        threshold=args.threshold,
        mode=args.mode,
        region=args.region,
    )
    print_results(results, total_ms, args.top)
    payload = result_payload(source, image, engine, results, total_ms, args.mode, args.threshold)
    if args.json_out:
        write_json(args.json_out, payload)
    if args.annotated_out:
        args.annotated_out.parent.mkdir(parents=True, exist_ok=True)
        annotate(image, results, args.top).save(args.annotated_out)
    if args.safe_crop_out:
        args.safe_crop_out.parent.mkdir(parents=True, exist_ok=True)
        safe_box = relative_box(image, args.safe_relative_box)
        annotated = annotate(image, results, args.top)
        annotated.crop(safe_box).save(args.safe_crop_out)
    return 0


def command_corpus(args: argparse.Namespace) -> int:
    specs = builtin_template_specs(args.pattern)
    if not specs:
        raise RuntimeError(f"No built-in templates match pattern: {args.pattern}")
    engine = FastVisionEngine(specs, args.workers or None)
    paths = sorted(path for path in args.input_dir.rglob(args.glob) if path.is_file())
    if not paths:
        raise RuntimeError(f"No images matched {args.glob} below {args.input_dir}")
    payload: list[dict[str, object]] = []
    started = time.perf_counter()
    for path in paths:
        image = load_image(path)
        _frame, results, total_ms = engine.inspect(image, threshold=args.threshold, mode=args.mode)
        payload.append(
            {
                "path": str(path.resolve()),
                "inspect_ms": round(total_ms, 3),
                "hits": [asdict(result) for result in results if result.hit],
                "top": [asdict(result) for result in results[: args.top]],
            }
        )
        best = results[0]
        print(f"{path.name}: {best.key} {best.score:.4f} ({total_ms:.1f} ms)")
    elapsed_ms = (time.perf_counter() - started) * 1000.0
    output = {
        "input_dir": str(args.input_dir.resolve()),
        "image_count": len(paths),
        "template_count": len(specs),
        "preload_ms": round(engine.preload_ms, 3),
        "total_ms": round(elapsed_ms, 3),
        "images": payload,
    }
    if args.json_out:
        write_json(args.json_out, output)
    print(f"corpus_ms={elapsed_ms:.2f} images={len(paths)} templates={len(specs)}")
    return 0


def command_diff(args: argparse.Namespace) -> int:
    before = load_image(args.before)
    after = load_image(args.after)
    if args.relative_region:
        box = relative_box(before, args.relative_region)
    elif args.region:
        box = args.region
    else:
        box = (0, 0, before.width, before.height)
    result = region_diff(before, after, box, args.pixel_threshold)
    payload = asdict(result)
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    if args.json_out:
        write_json(args.json_out, payload)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="WJDR fast, read-only visual inspection suite")
    subparsers = parser.add_subparsers(dest="command", required=True)

    inspect_parser = subparsers.add_parser("inspect", help="batch-match one offline or ADB frame")
    add_match_arguments(inspect_parser)
    inspect_parser.set_defaults(handler=command_inspect)

    corpus_parser = subparsers.add_parser("corpus", help="batch-match an offline screenshot directory")
    corpus_parser.add_argument("--input-dir", type=Path, required=True)
    corpus_parser.add_argument("--glob", default="*.png")
    corpus_parser.add_argument("--pattern", default="daily")
    corpus_parser.add_argument("--threshold", type=float, default=0.94)
    corpus_parser.add_argument("--mode", choices=("fast", "robust"), default="fast")
    corpus_parser.add_argument("--workers", type=int, default=0)
    corpus_parser.add_argument("--top", type=int, default=5)
    corpus_parser.add_argument("--json-out", type=Path)
    corpus_parser.set_defaults(handler=command_corpus)

    diff_parser = subparsers.add_parser("diff", help="measure one pixel region between two frames")
    diff_parser.add_argument("before", type=Path)
    diff_parser.add_argument("after", type=Path)
    region_group = diff_parser.add_mutually_exclusive_group()
    region_group.add_argument("--region", type=parse_box)
    region_group.add_argument("--relative-region", type=parse_relative_box)
    diff_parser.add_argument("--pixel-threshold", type=int, default=12)
    diff_parser.add_argument("--json-out", type=Path)
    diff_parser.set_defaults(handler=command_diff)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    # Each match runs in our own worker pool.  Disabling OpenCV's nested pool
    # avoids oversubscribing the CPU when dozens of templates are inspected.
    cv2.setNumThreads(1)
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.handler(args))
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
