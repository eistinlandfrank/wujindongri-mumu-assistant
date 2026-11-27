"""Use local single-line recognition and reuse Windows OCR for page layout."""
from __future__ import annotations

import json
import logging
import subprocess
import time
import unicodedata
from functools import lru_cache
from pathlib import Path
from queue import Empty, Queue
from threading import Thread

import cv2
import numpy as np

from wjdr_backend import CREATE_NO_WINDOW, resource_path
from wjdr_scoreboard import restore_ocr_coordinates


class _LocalChineseLine:
    def __init__(self):
        import onnxruntime

        assets = resource_path("assets/ocr")
        options = onnxruntime.SessionOptions()
        options.intra_op_num_threads = 1
        options.inter_op_num_threads = 1
        self.session = onnxruntime.InferenceSession(
            str(assets / "pp-ocrv6-tiny-rec.onnx"), options, providers=["CPUExecutionProvider"])
        dictionary = json.loads((assets / "pp-ocrv6-tiny-characters.json").read_text(encoding="utf-8"))
        self.characters = ("", *dictionary, " ")
        self.input_name = self.session.get_inputs()[0].name

    def _read(self, pixels, padded_width):
        batch = np.zeros((1, 3, 48, max(padded_width, pixels.shape[-1])), dtype=np.float32)
        batch[0, :, :, :pixels.shape[-1]] = pixels
        scores = self.session.run(None, {self.input_name: batch})[0][0]
        tokens = scores.argmax(axis=-1)
        keep = (tokens != 0) & np.r_[True, tokens[1:] != tokens[:-1]]
        active = tokens[keep]
        if not len(active):
            return "", 0.0
        confidence = float(scores[np.flatnonzero(keep), active].min())
        return "".join(self.characters[index] for index in active), confidence

    def recognize(self, image):
        size = min(768, max(16, round(image.width * 48 / image.height)))
        rgb = cv2.resize(np.asarray(image.convert("RGB")), (size, 48), interpolation=cv2.INTER_LINEAR)
        pixels = rgb[:, :, ::-1].transpose(2, 0, 1).astype(np.float32) / 127.5 - 1.0
        text, confidence = self._read(pixels, 96)
        if confidence < 0.80 and size < 320:
            alternative, score = self._read(pixels, 320)
            if score > confidence:
                return alternative, score
        return text, confidence


@lru_cache(maxsize=1)
def _local_chinese_line():
    try:
        return _LocalChineseLine()
    except Exception as error:
        logging.getLogger(__name__).warning("内嵌中文 OCR 初始化失败，使用 Windows OCR · %s", error)
        return None


def embedded_text(ocr, image):
    reader = getattr(type(ocr), "recognize_line", None)
    return reader(ocr, image) if reader is not None else None


def matches_ui_label(observed, expected):
    actual = "".join(unicodedata.normalize("NFKC", observed).split())
    if actual == expected:
        return True
    if (len(expected) < 4 or abs(len(actual) - len(expected)) > 1
            or not all("\u3400" <= character <= "\u9fff" for character in actual)):
        return False
    if len(actual) == len(expected):
        return sum(a != b for a, b in zip(actual, expected)) == 1
    shorter, longer = sorted((actual, expected), key=len)
    first = next((index for index, (a, b) in enumerate(zip(shorter, longer)) if a != b), len(shorter))
    return shorter[first:] == longer[first + 1:]


class FortressOcr:
    def __init__(self, directory: Path, stop_event) -> None:
        self.directory = directory
        self.stop_event = stop_event
        self.process = None
        self.replies = Queue()
        self.frame_number = 0
        self.local_failed = False

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self._close()

    def recognize_line(self, image):
        if self.stop_event.is_set():
            raise InterruptedError()
        model = None if self.local_failed else _local_chinese_line()
        if model is None:
            return None
        try:
            text, confidence = model.recognize(image)
        except Exception as error:
            self.local_failed = True
            logging.getLogger(__name__).warning("内嵌中文 OCR 识别失败，使用 Windows OCR · %s", error)
            return None
        return text if confidence >= 0.78 else None

    def _close(self) -> None:
        if self.process is None:
            return
        process, reader = self.process, self.reader
        self.process = None
        try:
            process.stdin.close()
            process.wait(timeout=0.7)
        except (OSError, subprocess.TimeoutExpired):
            if process.poll() is None:
                try:
                    subprocess.run(["taskkill", "/PID", str(process.pid), "/T", "/F"],
                                   timeout=4, capture_output=True, creationflags=CREATE_NO_WINDOW)
                finally:
                    if process.poll() is None:
                        process.kill()
                    process.wait(timeout=2)
        finally:
            reader.join(timeout=1)
            process.stdout.close()

    def _start(self) -> None:
        self.process = subprocess.Popen(
            ["powershell.exe", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass",
             "-File", str(resource_path("assets/scoreboard_ocr.ps1")), "-StreamRequests"],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
            text=True, encoding="utf-8", bufsize=1, creationflags=CREATE_NO_WINDOW,
        )

        self.replies = Queue()
        process, replies = self.process, self.replies

        def read():
            try:
                for line in process.stdout:
                    replies.put(line)
            finally:
                replies.put(None)

        self.reader = Thread(target=read, daemon=True)
        self.reader.start()

    def __call__(self, image, language="zh-Hans-CN") -> list[dict]:
        if self.stop_event.is_set():
            raise InterruptedError()
        if self.process is None:
            self._start()
        self.frame_number += 1
        path = self.directory / f"frame-{self.frame_number}.bmp"
        image.save(path)
        request = json.dumps(
            {"id": self.frame_number, "path": str(path), "language": language}, ensure_ascii=False)
        try:
            self.process.stdin.write(request + "\n")
            self.process.stdin.flush()
        except OSError:
            self._close()
            raise
        deadline = time.monotonic() + 8
        while not self.stop_event.is_set():
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                self._close()
                raise ValueError("Windows OCR 识别超时")
            try:
                reply = self.replies.get(timeout=min(0.1, remaining))
            except Empty:
                continue
            if reply is None:
                self._close()
                raise ValueError("Windows OCR 进程已退出")
            try:
                result = json.loads(reply)
                if result.get("id") != self.frame_number:
                    raise ValueError("Windows OCR 返回了另一帧的结果")
            except (AttributeError, ValueError):
                self._close()
                raise
            try:
                path.unlink()
            except OSError:
                # WinRT can keep an input file open briefly. The operation's
                # temporary directory is cleaned after this process exits.
                pass
            if "error" in result:
                raise ValueError(f"Windows OCR 识别失败：{result['error']}")
            return restore_ocr_coordinates(result["lines"], image.width, image.height)
        raise InterruptedError()
