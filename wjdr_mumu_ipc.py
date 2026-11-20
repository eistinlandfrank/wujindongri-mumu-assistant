"""Bounded frame capture from the MuMu renderer installed on this machine."""
from __future__ import annotations

import ctypes
import json
import os
import re
import secrets
import socket
import subprocess
import sys
import time
from multiprocessing.shared_memory import SharedMemory
from pathlib import Path
from threading import Lock
from weakref import finalize

from PIL import Image

WORKER_FLAG = "--wjdr-ipc-worker"
MAX_PIXELS = 12_000_000


def _renderer(root, version, index):
    folder = Path(root)
    libraries = [folder / "nx_main/sdk/external_renderer_ipc.dll"]
    if re.fullmatch(r"\d+\.\d+", version):
        libraries.append(folder / "nx_device" / version / "shell/sdk/external_renderer_ipc.dll")
    libraries.append(folder / "shell/sdk/external_renderer_ipc.dll")
    int_ref = ctypes.POINTER(ctypes.c_int)
    error = "找不到已安装的 MuMu 截图 SDK"
    for library in libraries:
        if not library.is_file():
            continue
        try:
            dll = ctypes.CDLL(str(library))
            dll.nemu_connect.argtypes = (ctypes.c_wchar_p, ctypes.c_int)
            dll.nemu_connect.restype = ctypes.c_int
            dll.nemu_disconnect.argtypes = (ctypes.c_int,)
            dll.nemu_disconnect.restype = None
            dll.nemu_capture_display.argtypes = (
                ctypes.c_int, ctypes.c_int, ctypes.c_int, int_ref, int_ref, ctypes.c_void_p,
            )
            dll.nemu_capture_display.restype = ctypes.c_int
            handle = dll.nemu_connect(root, index)
        except (AttributeError, OSError) as exc:
            error = str(exc)
            continue
        if handle > 0:
            return dll, handle
        error = "MuMu IPC 连接失败"
    raise ValueError(error)


def _send(connection, value):
    connection.sendall(json.dumps(value, ensure_ascii=False).encode("utf-8") + b"\n")


def _receive(stream):
    line = stream.readline(4096)
    if not line:
        raise EOFError("MuMu IPC 进程已退出")
    return json.loads(line)


def worker_main(args):
    port, token, name, root, version, index, game_package = args
    with socket.create_connection(("127.0.0.1", int(port)), timeout=3) as connection:
        _send(connection, token)
        connection.settimeout(None)
        try:
            dll, handle = _renderer(root, version, int(index))
            try:
                display = 0
                if game_package:
                    display_for = dll.nemu_get_display_id
                    display_for.argtypes = (ctypes.c_int, ctypes.c_char_p, ctypes.c_int)
                    display_for.restype = ctypes.c_int
                    package = game_package.encode("ascii")
                    display = display_for(handle, package, 0)
                    if display < 0:
                        raise ValueError("MuMu IPC 未确认当前游戏显示")
                shared = SharedMemory(name=name)
                try:
                    buffer = (ctypes.c_ubyte * shared.size).from_buffer(shared.buf)
                    try:
                        _send(connection, None)
                        while connection.recv(1) == b"C":
                            if game_package and display_for(handle, package, 0) != display:
                                raise ValueError("MuMu IPC 的游戏显示已改变")
                            width, height = ctypes.c_int(), ctypes.c_int()
                            cap = dll.nemu_capture_display
                            result = cap(handle, display, 0, ctypes.byref(width), ctypes.byref(height), None)
                            expected = (width.value, height.value)
                            if result or min(expected) <= 0 or 4 * width.value * height.value > shared.size:
                                raise ValueError("MuMu IPC 截图尺寸异常或分辨率已改变")
                            result = cap(handle, display, shared.size, ctypes.byref(width), ctypes.byref(height), buffer)
                            if result or (width.value, height.value) != expected:
                                raise ValueError("MuMu IPC 抓帧未确认")
                            _send(connection, expected)
                    finally:
                        del buffer
                finally:
                    shared.close()
            finally:
                dll.nemu_disconnect(handle)
        except (AttributeError, OSError, ValueError) as exc:
            try:
                _send(connection, str(exc))
            except OSError:
                pass


def _remaining(deadline):
    left = deadline - time.monotonic()
    if left <= 0:
        raise TimeoutError("MuMu IPC 截图超时")
    return left


def _close_worker(process, shared, connection=None, stream=None):
    if connection is not None:
        connection.close()
    if stream is not None:
        stream.close()
    try:
        if process is not None:
            try:
                process.wait(timeout=0.15)
            except subprocess.TimeoutExpired:
                # The renderer worker has no child processes.
                process.kill()
                process.wait(timeout=0.6)
    finally:
        shared.close()
        shared.unlink()


class _IpcCapture:
    def __init__(self, target, index, size, *, game_display=True, timeout=5):
        if not target.manager_path:
            raise ValueError("找不到 MuMu 管理器")
        if min(size) <= 0 or not 0 < size[0] * size[1] <= MAX_PIXELS:
            raise ValueError("截图尺寸超出 IPC 缓冲区范围")
        deadline = time.monotonic() + timeout
        player = next((row for row in target.players if str(row.get("index")) == str(index)), {})
        version = str(player.get("android_version", ""))
        root = str(Path(target.manager_path).resolve().parent.parent)
        game_package = ""
        if game_display:
            from wjdr_constants import GAME_PACKAGE

            game_package = GAME_PACKAGE

        shared = SharedMemory(create=True, size=size[0] * size[1] * 4)
        process = connection = stream = None
        try:
            with socket.socket() as listener:
                listener.bind(("127.0.0.1", 0))
                listener.listen(1)
                port = listener.getsockname()[1]
                token = secrets.token_hex(16)
                if getattr(sys, "frozen", False):
                    command = [sys.executable, WORKER_FLAG]
                else:
                    command = [sys.executable, "-B", str(Path(__file__).resolve()), WORKER_FLAG]
                env = os.environ.copy()
                # The one-file bootloader can reuse its extraction for this worker.
                env.pop("PYINSTALLER_RESET_ENVIRONMENT", None)
                process = subprocess.Popen(
                    [*command, str(port), token, shared.name, root, version, str(index), game_package],
                    stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                    creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0), env=env,
                )
                listener.settimeout(_remaining(deadline))
                connection, _ = listener.accept()
                stream = connection.makefile("rb")
                connection.settimeout(_remaining(deadline))
                if _receive(stream) != token:
                    raise ValueError("MuMu IPC 进程验证失败")
                connection.settimeout(_remaining(deadline))
                ready = _receive(stream)
                if ready is not None:
                    raise ValueError(str(ready))
        except BaseException:
            _close_worker(process, shared, connection, stream)
            raise
        self._shared = shared
        self._connection = connection
        self._stream = stream
        self._cleanup = finalize(self, _close_worker, process, shared, connection, stream)

    def screenshot(self, timeout):
        self._connection.settimeout(timeout)
        self._connection.sendall(b"C")
        size = _receive(self._stream)
        if isinstance(size, str):
            raise ValueError(size)
        if (
            not isinstance(size, list) or len(size) != 2
            or any(type(dimension) is not int or dimension <= 0 for dimension in size)
            or size[0] * size[1] * 4 > self._shared.size
        ):
            raise ValueError("MuMu IPC 截图尺寸无效")
        image = Image.frombuffer("RGBA", tuple(size), self._shared.buf, "raw", "RGBA", 0, -1)
        return image.convert("RGB")

    def close(self):
        self._cleanup()


class IpcScreenshots:
    """Own live renderer sessions for the ADB serials bound to one transport."""

    def __init__(self, error_type):
        self._error_type = error_type
        self._lock = Lock()
        self._sessions = {}
        self._bindings = {}

    def _open(self, target, serial, deadline):
        output = str(target._run(
            ["-s", serial, "shell", "settings get secure android_id; cat /proc/sys/kernel/random/boot_id; wm size"],
            timeout=min(2, _remaining(deadline)),
        ))
        lines = output.splitlines()
        sizes = re.findall(r"(\d+)x(\d+)", output)
        android_id, boot_id = (line.strip().lower() for line in lines[:2]) if len(lines) >= 2 else ("", "")
        if (
            not sizes or not re.fullmatch(r"[0-9a-f]{1,16}", android_id) or int(android_id, 16) == 0
            or not re.fullmatch(r"[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}", boot_id)
        ):
            raise ValueError("此 ADB 的实例身份或分辨率未复核")

        players = {}
        for player in target.players:
            index = str(player.get("index", ""))
            port = str(player.get("adb_port", ""))
            if index.isdecimal() and port.isdecimal():
                host = player.get("adb_host_ip") or "127.0.0.1"
                players[f"{host}:{port}"] = index
        known_identity = target.device_identities.get(serial, "")
        index = players.get(serial)
        if index is None:
            candidates = players.items()
            if known_identity.startswith("mumu:"):
                known_index = known_identity.split(":", 2)[1]
                candidates = [(address, number) for address, number in candidates if number == known_index]
            matches = []
            for address, number in candidates:
                try:
                    other_boot = str(target._run(
                        ["-s", address, "shell", "cat", "/proc/sys/kernel/random/boot_id"],
                        timeout=min(0.5, _remaining(deadline)),
                    )).strip().lower()
                except RuntimeError:
                    continue
                if other_boot == boot_id:
                    matches.append(number)
            if len(matches) != 1:
                raise ValueError("ADB 别名与 MuMu 管理器实例不一致")
            index = matches[0]
        identity = f"mumu:{index}:android:{android_id}"
        if known_identity.startswith("mumu:") and known_identity != identity:
            raise ValueError("当前 ADB 与已绑定的 MuMu 实例身份不一致")
        binding = (identity, boot_id)
        if self._bindings.setdefault(serial, binding) != binding:
            raise ValueError("MuMu 实例已重启或改变，请重新绑定后再开始")
        size = tuple(map(int, sizes[-1]))
        return _IpcCapture(target, int(index), size, game_display=False, timeout=_remaining(deadline))

    def screenshot(self, target, serial, timeout):
        if not serial:
            raise self._error_type("尚未选择模拟器设备。")
        timeout = min(20, max(0.1, timeout))
        deadline = time.monotonic() + timeout
        if not self._lock.acquire(timeout=timeout):
            raise self._error_type("MuMu IPC 截图排队超时")
        try:
            session = self._sessions.get(serial)
            if session is None:
                session = self._open(target, serial, deadline)
                self._sessions[serial] = session
            return session.screenshot(_remaining(deadline))
        except (EOFError, OSError, ValueError, RuntimeError, KeyError) as exc:
            session = self._sessions.pop(serial, None)
            if session is not None:
                session.close()
            raise self._error_type(f"MuMu IPC 抓帧失败 · {exc}") from exc
        finally:
            self._lock.release()


class RouteCapture:
    """Keep the Fortress CLI's game-display proof for its selected MuMu account."""

    def __init__(self, target, index: int) -> None:
        self.target = target
        self.index = index
        self.ipc = None

    def __getattr__(self, name):
        return getattr(self.target, name)

    def __enter__(self):
        return self

    def __exit__(self, *_):
        if self.ipc is not None:
            self.ipc.close()
            self.ipc = None

    def screenshot(self, *, timeout: float = 6) -> Image.Image:
        try:
            if self.ipc is None:
                self.ipc = _IpcCapture(self.target, self.index, self.target.screen_size())
            return self.ipc.screenshot(timeout)
        except (EOFError, OSError, ValueError, RuntimeError) as exc:
            raise RuntimeError(f"MuMu IPC 抓帧失败 · {exc}") from exc


if __name__ == "__main__" and sys.argv[1:2] == [WORKER_FLAG]:
    worker_main(sys.argv[2:])
