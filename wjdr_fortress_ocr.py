"""Reuse one Windows OCR process for a fortress operation."""
from __future__ import annotations

import json
import subprocess
import time
from pathlib import Path
from queue import Empty, Queue
from threading import Thread

from wjdr_backend import CREATE_NO_WINDOW, resource_path
from wjdr_scoreboard import restore_ocr_coordinates


class FortressOcr:
    def __init__(self, directory: Path, stop_event) -> None:
        self.directory = directory
        self.stop_event = stop_event
        self.process = None
        self.replies = Queue()
        self.frame_number = 0

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self._close()

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
