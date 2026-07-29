# -*- coding: utf-8 -*-
"""Shared MuMu/recognition backend for the distributable Qt application."""

from __future__ import annotations

import io
import json
import os
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any

if os.name == "nt":
    import msvcrt

import cv2
import numpy as np
from PIL import Image


APP_NAME = "æ— å°½å†¬æ—¥ MuMu åŠ©æ‰‹"
APP_VERSION = "4.1.1"
GAME_PACKAGE = "com.gof.china"
CREATE_NO_WINDOW = 0x08000000 if os.name == "nt" else 0
CONFIG_DIR = Path(os.environ.get("LOCALAPPDATA", Path.home())) / "WJDRMuMuAssistant"
TEMPLATE_DIR = CONFIG_DIR / "templates"
TASK_FILE = CONFIG_DIR / "tasks.json"
LOG_FILE = CONFIG_DIR / "assistant.log"
LOCK_DIR = CONFIG_DIR / "device_locks"
BUILTIN_ALL_HELP_TEMPLATE_ASSET = "alliance_all_help_builtin.png"
BUILTIN_ALL_HELP_TEMPLATE_NAME = "å†…ç½®_å…¨éƒ¨å¸®åŠ©_å®žæµ‹.png"
BUILTIN_HELP_TEMPLATE_ASSET = "alliance_help_builtin.png"
BUILTIN_HELP_TEMPLATE_NAME = "å†…ç½®_è”ç›Ÿå¸®åŠ©_å®žæµ‹.png"
BUILTIN_MUTUAL_PAGE_TEMPLATE_ASSET = "alliance_mutual_page_builtin.png"
BUILTIN_MUTUAL_ENTRY_TEMPLATE_ASSET = "alliance_mutual_entry_builtin.png"
BUILTIN_CITY_ALLIANCE_TEMPLATE_ASSET = "alliance_city_entry_builtin.png"
BUILTIN_HELP_REFERENCE_SIZE = (1440, 2560)

# Red-packet assets intentionally live below ``assets`` instead of the
# application root.  They are visual anchors for the independent red-packet
# workflow; keeping their names here lets the packaged application and a
# source checkout use the exact same lookup rules.
RED_PACKET_ASSET_DIR = "assets"
# The reviewed built-in anchors are packaged with the application.  The
# chat-entry asset is intentionally reserved for a later city-screen capture.
BUILTIN_RED_PACKET_MARKER_ASSET = f"{RED_PACKET_ASSET_DIR}/redpacket_notification.png"
BUILTIN_RED_PACKET_CHAT_ENTRY_ASSET = f"{RED_PACKET_ASSET_DIR}/red_packet_chat_entry_builtin.png"
BUILTIN_RED_PACKET_CHAT_PANEL_ASSET = f"{RED_PACKET_ASSET_DIR}/chat_panel_header.png"
BUILTIN_RED_PACKET_ALLIANCE_PAGE_ASSET = f"{RED_PACKET_ASSET_DIR}/chat_alliance_selected.png"
BUILTIN_FURNACE_UPGRADE_PACKET_ASSET = f"{RED_PACKET_ASSET_DIR}/furnace_redpacket_card_title.png"
BUILTIN_FURNACE_UPGRADE_TITLE_ASSET = f"{RED_PACKET_ASSET_DIR}/furnace_redpacket_popup_title.png"
BUILTIN_RED_PACKET_OPEN_ASSET = f"{RED_PACKET_ASSET_DIR}/furnace_redpacket_open_button.png"
BUILTIN_RED_PACKET_RESULT_ASSET = f"{RED_PACKET_ASSET_DIR}/redpacket_result_diamond_anchor.png"
BUILTIN_RED_PACKET_RESULT_CLOSE_ASSET = f"{RED_PACKET_ASSET_DIR}/redpacket_result_close_button.png"
BUILTIN_RED_PACKET_MARKER_TEMPLATE_NAME = "å†…ç½®_çº¢åŒ…æµ®æ ‡_å®žæµ‹.png"
BUILTIN_RED_PACKET_CHAT_ENTRY_TEMPLATE_NAME = "å†…ç½®_èŠå¤©å…¥å£_å®žæµ‹.png"
BUILTIN_RED_PACKET_CHAT_PANEL_TEMPLATE_NAME = "å†…ç½®_èŠå¤©é¢æ¿æ ‡é¢˜_å®žæµ‹.png"
BUILTIN_RED_PACKET_ALLIANCE_PAGE_TEMPLATE_NAME = "å†…ç½®_è”ç›Ÿé¢‘é“_å®žæµ‹.png"
BUILTIN_FURNACE_UPGRADE_PACKET_TEMPLATE_NAME = "å†…ç½®_ç†”ç‚‰å‡çº§çº¢åŒ…å¡æ ‡é¢˜_å®žæµ‹.png"
BUILTIN_FURNACE_UPGRADE_TITLE_TEMPLATE_NAME = "å†…ç½®_ç†”ç‚‰å‡çº§çº¢åŒ…æ ‡é¢˜_å®žæµ‹.png"
BUILTIN_RED_PACKET_OPEN_TEMPLATE_NAME = "å†…ç½®_çº¢åŒ…å¼€å¯æŒ‰é’®_å®žæµ‹.png"
BUILTIN_RED_PACKET_RESULT_TEMPLATE_NAME = "å†…ç½®_çº¢åŒ…é¢†å–ç»“æžœ_å®žæµ‹.png"
BUILTIN_RED_PACKET_RESULT_CLOSE_TEMPLATE_NAME = "å†…ç½®_çº¢åŒ…é¢†å–ç»“æžœå…³é—­_å®žæµ‹.png"
BUILTIN_RED_PACKET_REFERENCE_SIZE = (1440, 2560)
BUILTIN_RED_PACKET_MARKER_REFERENCE_SIZE = (720, 1280)
# The city-entry anchor deliberately excludes chat text.  Once that anchor is
# present, this is the measured safe tap location inside the same chat strip.
RED_PACKET_CHAT_ENTRY_REFERENCE_POINT = (430, 2260)
RED_PACKET_BUILTIN_TEMPLATES: tuple[tuple[str, str], ...] = (
    (BUILTIN_RED_PACKET_MARKER_ASSET, BUILTIN_RED_PACKET_MARKER_TEMPLATE_NAME),
    (BUILTIN_RED_PACKET_CHAT_ENTRY_ASSET, BUILTIN_RED_PACKET_CHAT_ENTRY_TEMPLATE_NAME),
    (BUILTIN_RED_PACKET_CHAT_PANEL_ASSET, BUILTIN_RED_PACKET_CHAT_PANEL_TEMPLATE_NAME),
    (BUILTIN_RED_PACKET_ALLIANCE_PAGE_ASSET, BUILTIN_RED_PACKET_ALLIANCE_PAGE_TEMPLATE_NAME),
    (BUILTIN_FURNACE_UPGRADE_PACKET_ASSET, BUILTIN_FURNACE_UPGRADE_PACKET_TEMPLATE_NAME),
    (BUILTIN_FURNACE_UPGRADE_TITLE_ASSET, BUILTIN_FURNACE_UPGRADE_TITLE_TEMPLATE_NAME),
    (BUILTIN_RED_PACKET_OPEN_ASSET, BUILTIN_RED_PACKET_OPEN_TEMPLATE_NAME),
    (BUILTIN_RED_PACKET_RESULT_ASSET, BUILTIN_RED_PACKET_RESULT_TEMPLATE_NAME),
    (BUILTIN_RED_PACKET_RESULT_CLOSE_ASSET, BUILTIN_RED_PACKET_RESULT_CLOSE_TEMPLATE_NAME),
)
RED_PACKET_BUILTIN_TEMPLATE_FILENAMES = frozenset(
    [name for _asset, name in RED_PACKET_BUILTIN_TEMPLATES]
    + [Path(asset).name for asset, _name in RED_PACKET_BUILTIN_TEMPLATES]
)
DEFAULT_TASKS: dict[str, list[dict[str, Any]]] = {
    "ä»Žä¸»åŸŽè¿›å…¥è”ç›Ÿäº’åŠ©": [
        {"action": "tap", "x": 1065, "y": 2460, "width": 1440, "height": 2560},
        {"action": "wait", "seconds": 2.0},
        {"action": "tap", "x": 1060, "y": 2140, "width": 1440, "height": 2560},
        {"action": "wait", "seconds": 2.0},
    ]
}


class AdbError(RuntimeError):
    pass


class AlliancePage(str, Enum):
    """The only page states that the automatic alliance-help flow may act on."""

    ALL_HELP_READY = "all_help_ready"
    MUTUAL_HELP = "mutual_help"
    ALLIANCE_HOME = "alliance_home"
    CITY = "city"
    UNKNOWN = "unknown"


class RedPacketState(str, Enum):
    """Visual states for the guarded alliance red-packet workflow.

    These values deliberately describe what is *currently visible* rather
    than an action to take.  The UI/controller owns timing, retries and taps;
    the backend only reports visual evidence.
    """

    MARKER = "marker"
    CHAT_ENTRY = "chat_entry"
    CHAT_PANEL = "chat_panel"
    ALLIANCE_CHAT = "alliance_chat"
    FURNACE_PACKET = "furnace_packet"
    FURNACE_DETAIL = "furnace_detail"
    DETAIL_OPEN_READY = "detail_open_ready"
    CLAIM_RESULT_READY = "claim_result_ready"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class AlliancePageMatch:
    page: AlliancePage
    point: tuple[int, int] | None
    score: float


@dataclass(frozen=True)
class RedPacketMatch:
    """Result of a red-packet visual classification.

    ``point`` is the primary matched anchor.  For
    :attr:`RedPacketState.DETAIL_OPEN_READY`, it is the ``å¼€å¯`` control and
    ``anchors`` also contains the independently matched furnace-title anchor.
    For :attr:`RedPacketState.CLAIM_RESULT_READY`, it is the result-dialog X.
    That latter state is visual evidence only: a controller must correlate it
    with its own immediately preceding ``å¼€å¯`` click before recording success.
    """

    state: RedPacketState
    point: tuple[int, int] | None
    score: float
    anchors: tuple[tuple[str, tuple[int, int]], ...] = ()


def clean_name(name: str) -> str:
    value = re.sub(r"[^\w\-\u4e00-\u9fff]+", "_", name.strip(), flags=re.UNICODE)
    return value[:40] or "template"


def resource_path(name: str) -> Path:
    root = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
    return root / name


def prepare_storage() -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    TEMPLATE_DIR.mkdir(parents=True, exist_ok=True)
    for asset, name in (
        (BUILTIN_ALL_HELP_TEMPLATE_ASSET, BUILTIN_ALL_HELP_TEMPLATE_NAME),
        (BUILTIN_HELP_TEMPLATE_ASSET, BUILTIN_HELP_TEMPLATE_NAME),
        *RED_PACKET_BUILTIN_TEMPLATES,
    ):
        source = resource_path(asset)
        destination = TEMPLATE_DIR / name
        if source.is_file():
            payload = source.read_bytes()
            if not destination.is_file() or destination.read_bytes() != payload:
                destination.write_bytes(payload)


def template_reference_size(template_path: Path) -> tuple[int, int] | None:
    if template_path.name in (
        BUILTIN_ALL_HELP_TEMPLATE_NAME,
        BUILTIN_HELP_TEMPLATE_NAME,
        BUILTIN_MUTUAL_PAGE_TEMPLATE_ASSET,
        BUILTIN_MUTUAL_ENTRY_TEMPLATE_ASSET,
        BUILTIN_CITY_ALLIANCE_TEMPLATE_ASSET,
    ):
        return BUILTIN_HELP_REFERENCE_SIZE
    if template_path.name in {
        BUILTIN_RED_PACKET_MARKER_TEMPLATE_NAME,
        Path(BUILTIN_RED_PACKET_MARKER_ASSET).name,
    }:
        # The supplied floating-envelope crop came from a 720 x 1280 capture.
        # It must scale independently of the 1440 x 2560 chat/popup anchors.
        return BUILTIN_RED_PACKET_MARKER_REFERENCE_SIZE
    if template_path.name in RED_PACKET_BUILTIN_TEMPLATE_FILENAMES:
        return BUILTIN_RED_PACKET_REFERENCE_SIZE
    try:
        data = json.loads(template_path.with_suffix(".json").read_text(encoding="utf-8"))
        width, height = int(data["screen_width"]), int(data["screen_height"])
        return (width, height) if width > 0 and height > 0 else None
    except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError):
        return None


class DeviceLease:
    def __init__(self, device: str) -> None:
        self.path = LOCK_DIR / f"{clean_name(device)}.lock"
        self.handle: Any = None

    def acquire(self) -> bool:
        if os.name != "nt":
            return True
        LOCK_DIR.mkdir(parents=True, exist_ok=True)
        try:
            self.handle = self.path.open("a+b")
            self.handle.seek(0, os.SEEK_END)
            if self.handle.tell() == 0:
                self.handle.write(b"0")
                self.handle.flush()
            self.handle.seek(0)
            msvcrt.locking(self.handle.fileno(), msvcrt.LK_NBLCK, 1)
            return True
        except OSError:
            if self.handle:
                self.handle.close()
                self.handle = None
            return False

    def release(self) -> None:
        if os.name == "nt" and self.handle:
            try:
                self.handle.seek(0)
                msvcrt.locking(self.handle.fileno(), msvcrt.LK_UNLCK, 1)
            except OSError:
                pass
            self.handle.close()
            self.handle = None


class MuMuADB:
    def __init__(self, adb_path: str | None = None) -> None:
        self.adb_path = adb_path or self._find_adb()
        self.manager_path = self._find_manager()
        self.device = ""
        self.players: list[dict[str, Any]] = []

    @staticmethod
    def _find_adb() -> str:
        candidates = [
            r"C:\Program Files\Netease\MuMuPlayerGlobal-12.0\shell\adb.exe",
            r"C:\Program Files\Netease\MuMuPlayerGlobal-12.0\nx_main\adb.exe",
            r"C:\Program Files\Netease\MuMuPlayerGlobal-12.0\nx_device\12.0\shell\adb.exe",
            r"C:\Program Files\Netease\MuMu Player 12\shell\adb.exe",
            r"C:\Program Files (x86)\Nemu\vmonitor\bin\adb_server.exe",
        ]
        found = shutil.which("adb")
        if found:
            candidates.append(found)
        for candidate in candidates:
            if Path(candidate).is_file():
                return candidate
        raise AdbError("æ²¡æœ‰æ‰¾åˆ° MuMu è‡ªå¸¦çš„ ADBã€‚è¯·å…ˆå®‰è£…å¹¶å¯åŠ¨ MuMu Player 12ã€‚")

    @staticmethod
    def _find_manager() -> str | None:
        for candidate in (
            r"C:\Program Files\Netease\MuMuPlayerGlobal-12.0\nx_main\MuMuManager.exe",
            r"C:\Program Files\Netease\MuMu Player 12\nx_main\MuMuManager.exe",
        ):
            if Path(candidate).is_file():
                return candidate
        return None

    def _run(self, args: list[str], timeout: float = 20, binary: bool = False) -> bytes | str:
        try:
            proc = subprocess.run(
                [self.adb_path, *args],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                timeout=timeout,
                creationflags=CREATE_NO_WINDOW,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise AdbError(f"ADB æ‰§è¡Œå¤±è´¥ï¼š{exc}") from exc
        if proc.returncode != 0:
            output = proc.stdout.decode("utf-8", "replace").strip()
            raise AdbError(output or f"ADB è¿”å›žé”™è¯¯ç  {proc.returncode}")
        return proc.stdout if binary else proc.stdout.decode("utf-8", "replace")

    def _manager_players(self) -> list[dict[str, Any]]:
        if not self.manager_path:
            return []
        try:
            proc = subprocess.run(
                [self.manager_path, "info", "-v", "all"],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                timeout=12,
                creationflags=CREATE_NO_WINDOW,
            )
            output = proc.stdout.decode("utf-8", "replace")
        except (OSError, subprocess.TimeoutExpired):
            return []
        players: list[dict[str, Any]] = []

        def collect(value: Any) -> None:
            if isinstance(value, dict):
                if "index" in value and ("adb_port" in value or "is_process_started" in value):
                    players.append(value)
                else:
                    for nested in value.values():
                        collect(nested)
            elif isinstance(value, list):
                for nested in value:
                    collect(nested)

        decoder, position = json.JSONDecoder(), 0
        while position < len(output):
            match = re.search(r"[\[{]", output[position:])
            if not match:
                break
            start = position + match.start()
            try:
                value, end = decoder.raw_decode(output, start)
            except json.JSONDecodeError:
                position = start + 1
                continue
            collect(value)
            position = end
        return players

    def _candidate_ports(self) -> list[int]:
        ports = {7555, 16384}
        self.players = self._manager_players()
        for player in self.players:
            try:
                if player.get("is_process_started") or player.get("is_android_started"):
                    ports.add(int(player["adb_port"]))
            except (ValueError, TypeError, KeyError):
                pass
        for root in (
            Path(r"C:\Program Files\Netease\MuMuPlayerGlobal-12.0\vms"),
            Path(r"C:\Program Files\Netease\MuMu Player 12\vms"),
        ):
            if root.exists():
                for config in root.glob("*/configs/vm_config.json"):
                    try:
                        data = json.loads(config.read_text(encoding="utf-8"))
                        ports.add(int(data["vm"]["nat"]["port_forward"]["adb"]["host_port"]))
                    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError):
                        pass
        return sorted(ports)

    def connect(self, preferred_device: str | None = None) -> list[str]:
        self._run(["start-server"], timeout=10)
        for port in self._candidate_ports():
            try:
                self._run(["connect", f"127.0.0.1:{port}"], timeout=4)
            except AdbError:
                pass
        output = str(sÛÞ9¶‰žËkºwµçtè(€€€€ˆˆ‰¥¹Ñ¡”±½Ý•ÈµÉ¥¡ÐÉ•µ•¹Ù•±½Á”™±½…Ñ¥¹œµ…É­•ÈÑ¡…ÐÑÉ¥•ÉÌ„¡…Ð¡•¬¸((€€€Q¡”µ…É­•È¥ÑÍ•±˜¥Ì½¹±ä„Í¥¹…°¸€…±±•ÉÌµÕÍÐÍÑ¥±°½¹™¥É´Ñ¡”(€€€…±±¥…¹”¡…ÐÁ…”…¹Ñ¡”Ñ…É•Ð™ÕÉ¹…”Á…­•Ð‰•™½É”Á•É™½Éµ¥¹œ¥¹ÁÕÐ¸(€€€€ˆˆˆ(€€€É•ÑÕÉ¸}µ…Ñ¡}É•‘}Á…­•Ñ}Ñ•µÁ±…Ñ” (€€€€€€€ÍÉ••¹Í¡½Ð°(€€€€€€€	U%1Q%9}I}A-Q}5I-I}MMP°(€€€€€€€	U%1Q%9}I}A-Q}5I-I}Q5A1Q}95°(€€€€€€€Ñ¡É•Í¡½±°(€€€€€€€€ŒQ¡”¹½Ñ¥™¥…Ñ¥½¸¥Ì…¹¡½É•…‰½Ù”Ñ¡”¡…Ð±…Õ¹¡•È¥¸Ñ¡”±½Ý•È(€€€€€€€€ŒÉ¥¡Ð¸€-••Á¥¹œÑ¡¥Ì¹…ÉÉ½Ü…Ù½¥‘Ì½¹™ÕÍ¥¹œ½É‘¥¹…Éä•¹Ù•±½Á”…ÉÐ(€€€€€€€€Œ•±Í•Ý¡•É”¥¸Ñ¡”¥ÑäÍ•¹”Ý¥Ñ Ñ¡”ÑÉ¥•Èµ½¹±ä™±½…Ñ¥¹œµ…É­•È¸(€€€€€€€Í•…É¡}É•¥½¸¥˜Í•…É¡}É•¥½¸¥Ì¹½Ð9½¹”•±Í”}É•±…Ñ¥Ù•}É•¥½¸¡ÍÉ••¹Í¡½Ð°€À¸ÜÈ°€À¸ÜÈ°€À¸äÐ°€À¸äÐ¤°(€€€€¤(()‘•˜µ…Ñ¡}É•‘}Á…­•Ñ}¡…Ñ}•¹ÑÉä (€€€ÍÉ••¹Í¡½Ðè%µ…”¹%µ…”°(€€€Ñ¡É•Í¡½±è™±½…Ð°(€€€Í•…É¡}É•¥½¸èÑÕÁ±•m¥¹Ð°¥¹Ð°¥¹Ð°¥¹Ñtð9½¹”€ô9½¹”°(¤€´øÑÕÁ±•mÑÕÁ±•m¥¹Ð°¥¹Ñtð9½¹”°™±½…Ñtè(€€€€ˆˆ‰¥¹Ñ¡”•¹ÑÉäÑ¡…Ð½Á•¹ÌÑ¡”…µ”Ì¡…ÐÁ…¹•°¸((€€€Q¡”Ñ•µÁ±…Ñ”¥Ì„ÍÑ…‰±”Í¡¥•±€¼Á…•È…¹¡½È…ÐÑ¡”±•™ÐÍ¥‘”½˜Ñ¡”(€€€¥Ñä¡…ÐÍÑÉ¥À¸€%ÑÌ½Ý¸•¹ÑÉ”¥Ì¹½ÐÑ¡”‘•Í¥É•Ñ…ÀÑ…É•Ð°Í¼„(€€€½¹™¥Éµ•µ…Ñ É•ÑÕÉ¹ÌÑ¡”¥¹‘•Á•¹‘•¹Ñ±äµ•…ÍÕÉ•Á½¥¹Ð¥¹Í¥‘”Ñ¡”Í…µ”(€€€ÍÑÉ¥À°Í…±•™É½´Ñ¡”€ÄÐÐÀƒ\€ÈÔØÀÉ•™•É•¹”ÍÉ••¸¸(€€€€ˆˆˆ(€€€Á½¥¹Ð°Í½É”€ô}µ…Ñ¡}É•‘}Á…­•Ñ}Ñ•µÁ±…Ñ” (€€€€€€€ÍÉ••¹Í¡½Ð°(€€€€€€€	U%1Q%9}I}A-Q}!Q}9QIe}MMP°(€€€€€€€	U%1Q%9}I}A-Q}!Q}9QIe}Q5A1Q}95°(€€€€€€€Ñ¡É•Í¡½±°(€€€€€€€Í•…É¡}É•¥½¸¥˜Í•…É¡}É•¥½¸¥Ì¹½Ð9½¹”•±Í”}É•±…Ñ¥Ù•}É•¥½¸¡ÍÉ••¹Í¡½Ð°€À¸À°€À¸àÀ°€À¸Äà°€À¸äÔ¤°(€€€€¤(€€€¥˜¹½ÐÁ½¥¹Ðè(€€€€€€€É•ÑÕÉ¸9½¹”°Í½É”(€€€É•™}Ý¥‘Ñ °É•™}¡•¥¡Ð€ô	U%1Q%9}I}A-Q}II9}M%i(€€€É•ÑÕÉ¸€ (€€€€€€€É½Õ¹¡ÍÉ••¹Í¡½Ð¹Ý¥‘Ñ €¨I}A-Q}!Q}9QIe}II9}A=%9QlÁt€¼É•™}Ý¥‘Ñ ¤°(€€€€€€€É½Õ¹¡ÍÉ••¹Í¡½Ð¹¡•¥¡Ð€¨I}A-Q}!Q}9QIe}II9}A=%9QlÅt€¼É•™}¡•¥¡Ð¤°(€€€€¤°Í½É”(()‘•˜µ…Ñ¡}É•‘}Á…­•Ñ}¡…Ñ}Á…¹•° (€€€ÍÉ••¹Í¡½Ðè%µ…”¹%µ…”°(€€€Ñ¡É•Í¡½±è™±½…Ð°(€€€Í•…É¡}É•¥½¸èÑÕÁ±•m¥¹Ð°¥¹Ð°¥¹Ð°¥¹Ñtð9½¹”€ô9½¹”°(¤€´øÑÕÁ±•mÑÕÁ±•m¥¹Ð°¥¹Ñtð9½¹”°™±½…Ñtè(€€€€ˆˆ‰¥¹Ñ¡”¡…ÐµÁ…¹•°¡•…‘•È…™Ñ•ÈÑ¡”¥Ñä¡…Ð•¹ÑÉä¡…Ì‰••¸½Á•¹•¸ˆˆˆ(€€€É•ÑÕÉ¸}µ…Ñ¡}É•‘}Á…­•Ñ}Ñ•µÁ±…Ñ” (€€€€€€€ÍÉ••¹Í¡½Ð°(€€€€€€€	U%1Q%9}I}A-Q}!Q}A91}MMP°(€€€€€€€	U%1Q%9}I}A-Q}!Q}A91}Q5A1Q}95°(€€€€€€€Ñ¡É•Í¡½±°(€€€€€€€Í•…É¡}É•¥½¸¥˜Í•…É¡}É•¥½¸¥Ì¹½Ð9½¹”•±Í”}É•±…Ñ¥Ù•}É•¥½¸¡ÍÉ••¹Í¡½Ð°€À¸À°€À¸À°€À¸ÐÈ°€À¸Äà¤°(€€€€¤(()‘•˜µ…Ñ¡}…±±¥…¹•}¡…Ñ}Á…” (€€€ÍÉ••¹Í¡½Ðè%µ…”¹%µ…”°(€€€Ñ¡É•Í¡½±è™±½…Ð°(€€€Í•…É¡}É•¥½¸èÑÕÁ±•m¥¹Ð°¥¹Ð°¥¹Ð°¥¹Ñtð9½¹”€ô9½¹”°(¤€´øÑÕÁ±•mÑÕÁ±•m¥¹Ð°¥¹Ñtð9½¹”°™±½…Ñtè(€€€€ˆˆ‰¥¹Ñ¡”Í•±•Ñ•±±¥…¹”Ñ…ˆ°ÁÉ½Ù¥¹œÑ¡…ÐÑ¡¥Ì¡…¹¹•°¥Ì…Ñ¥Ù”¸ˆˆˆ(€€€É•ÑÕÉ¸}µ…Ñ¡}É•‘}Á…­•Ñ}Ñ•µÁ±…Ñ” (€€€€€€€ÍÉ••¹Í¡½Ð°(€€€€€€€	U%1Q%9}I}A-Q}11%9}A}MMP°(€€€€€€€	U%1Q%9}I}A-Q}11%9}A}Q5A1Q}95°(€€€€€€€Ñ¡É•Í¡½±°(€€€€€€€Í•…É¡}É•¥½¸¥˜Í•…É¡}É•¥½¸¥Ì¹½Ð9½¹”•±Í”}É•±…Ñ¥Ù•}É•¥½¸¡ÍÉ••¹Í¡½Ð°€À¸À°€À¸À°€Ä¸À°€À¸ÐÔ¤°(€€€€¤(()‘•˜µ…Ñ¡}™ÕÉ¹…•}ÕÁÉ…‘•}Á…­•Ð (€€€ÍÉ••¹Í¡½Ðè%µ…”¹%µ…”°(€€€Ñ¡É•Í¡½±è™±½…Ð°(€€€Í•…É¡}É•¥½¸èÑÕÁ±•m¥¹Ð°¥¹Ð°¥¹Ð°¥¹Ñtð9½¹”€ô9½¹”°(¤€´øÑÕÁ±•mÑÕÁ±•m¥¹Ð°¥¹Ñtð9½¹”°™±½…Ñtè(€€€€ˆˆ‰¥¹Ñ¡”±¥­…‰±”ƒžSž
'–6žêŸžê‹–2€…É¥¸…¸…±±¥…¹”¡…Ð¸ˆˆˆ(€€€É•ÑÕÉ¸}µ…Ñ¡}É•‘}Á…­•Ñ}Ñ•µÁ±…Ñ” (€€€€€€€ÍÉ••¹Í¡½Ð°(€€€€€€€	U%1Q%9}UI9}UAI}A-Q}MMP°(€€€€€€€	U%1Q%9}UI9}UAI}A-Q}Q5A1Q}95°(€€€€€€€Ñ¡É•Í¡½±°(€€€€€€€Í•…É¡}É•¥½¸¥˜Í•…É¡}É•¥½¸¥Ì¹½Ð9½¹”•±Í”}É•±…Ñ¥Ù•}É•¥½¸¡ÍÉ••¹Í¡½Ð°€À¸ÀÈ°€À¸Àà°€À¸äà°€À¸äÔ¤°(€€€€¤(()‘•˜µ…Ñ¡}™ÕÉ¹…•}ÕÁÉ…‘•}‘•Ñ…¥±}Ñ¥Ñ±” (€€€ÍÉ••¹Í¡½Ðè%µ…”¹%µ…”°(€€€Ñ¡É•Í¡½±è™±½…Ð°(€€€Í•…É¡}É•¥½¸èÑÕÁ±•m¥¹Ð°¥¹Ð°¥¹Ð°¥¹Ñtð9½¹”€ô9½¹”°(¤€´øÑÕÁ±•mÑÕÁ±•m¥¹Ð°¥¹Ñtð9½¹”°™±½…Ñtè(€€€€ˆˆ‰¥¹Ñ¡”Ñ¥Ñ±”½˜Ñ¡”½Á•¹•™ÕÉ¹…”µÕÁÉ…‘”É•µÁ…­•Ð‘¥…±½œ¸ˆˆˆ(€€€É•ÑÕÉ¸}µ…Ñ¡}É•‘}Á…­•Ñ}Ñ•µÁ±…Ñ” (€€€€€€€ÍÉ••¹Í¡½Ð°(€€€€€€€	U%1Q%9}UI9}UAI}Q%Q1}MMP°(€€€€€€€	U%1Q%9}UI9}UAI}Q%Q1}Q5A1Q}95°(€€€€€€€Ñ¡É•Í¡½±°(€€€€€€€Í•…É¡}É•¥½¸¥˜Í•…É¡}É•¥½¸¥Ì¹½Ð9½¹”•±Í”}É•±…Ñ¥Ù•}É•¥½¸¡ÍÉ••¹Í¡½Ð°€À¸ÄÈ°€À¸ÄÔ°€À¸àà°€À¸ÐÔ¤°(€€€€¤(()‘•˜µ…Ñ¡}É•‘}Á…­•Ñ}½Á•¹}‰ÕÑÑ½¸ (€€€ÍÉ••¹Í¡½Ðè%µ…”¹%µ…”°(€€€Ñ¡É•Í¡½±è™±½…Ð°(€€€Í•…É¡}É•¥½¸èÑÕÁ±•m¥¹Ð°¥¹Ð°¥¹Ð°¥¹Ñtð9½¹”€ô9½¹”°(¤€´øÑÕÁ±•mÑÕÁ±•m¥¹Ð°¥¹Ñtð9½¹”°™±½…Ñtè(€€€€ˆˆ‰¥¹Ñ¡”½É…¹”ƒ–ò–B½€½¹ÑÉ½°¥¸„É•µÁ…­•Ð‘•Ñ…¥°‘¥…±½œ¸ˆˆˆ(€€€É•ÑÕÉ¸}µ…Ñ¡}É•‘}Á…­•Ñ}Ñ•µÁ±…Ñ” (€€€€€€€ÍÉ••¹Í¡½Ð°(€€€€€€€	U%1Q%9}I}A-Q}=A9}MMP°(€€€€€€€	U%1Q%9}I}A-Q}=A9}Q5A1Q}95°(€€€€€€€Ñ¡É•Í¡½±°(€€€€€€€Í•…É¡}É•¥½¸¥˜Í•…É¡}É•¥½¸¥Ì¹½Ð9½¹”•±Í”}É•±…Ñ¥Ù•}É•¥½¸¡ÍÉ••¹Í¡½Ð°€À¸ÈÈ°€À¸ÔÔ°€À¸Üà°€À¸äÀ¤°(€€€€¤(()‘•˜µ…Ñ¡}É•‘}Á…­•Ñ}É•ÍÕ±Ð (€€€ÍÉ••¹Í¡½Ðè%µ…”¹%µ…”°(€€€Ñ¡É•Í¡½±è™±½…Ð°(€€€Í•…É¡}É•¥½¸èÑÕÁ±•m¥¹Ð°¥¹Ð°¥¹Ð°¥¹Ñtð9½¹”€ô9½¹”°(¤€´øÑÕÁ±•mÑÕÁ±•m¥¹Ð°¥¹Ñtð9½¹”°™±½…Ñtè(€€€€ˆˆ‰¥¹Ñ¡”‘¥…µ½¹½É•Ý…É…¹¡½È¥¸Ñ¡”Á½ÍÐµ½Á•¹¥¹œÉ•ÍÕ±Ð‘¥…±½œ¸ˆˆˆ(€€€É•ÑÕÉ¸}µ…Ñ¡}É•‘}Á…­•Ñ}Ñ•µÁ±…Ñ” (€€€€€€€ÍÉ••¹Í¡½Ð°(€€€€€€€	U%1Q%9}I}A-Q}IMU1Q}MMP°(€€€€€€€	U%1Q%9}I}A-Q}IMU1Q}Q5A1Q}95°(€€€€€€€Ñ¡É•Í¡½±°(€€€€€€€Í•…É¡}É•¥½¸¥˜Í•…É¡}É•¥½¸¥Ì¹½Ð9½¹”•±Í”}É•±…Ñ¥Ù•}É•¥½¸¡ÍÉ••¹Í¡½Ð°€À¸Äà°€À¸ÈÀ°€À¸ÜÀ°€À¸ÔÔ¤°(€€€€¤(()‘•˜µ…Ñ¡}É•‘}Á…­•Ñ}É•ÍÕ±Ñ}±½Í” (€€€ÍÉ••¹Í¡½Ðè%µ…”¹%µ…”°(€€€Ñ¡É•Í¡½±è™±½…Ð°(€€€Í•…É¡}É•¥½¸èÑÕÁ±•m¥¹Ð°¥¹Ð°¥¹Ð°¥¹Ñtð9½¹”€ô9½¹”°(¤€´øÑÕÁ±•mÑÕÁ±•m¥¹Ð°¥¹Ñtð9½¹”°™±½…Ñtè(€€€€ˆˆ‰¥¹Ñ¡”`…ÑÑ…¡•Ñ¼Ñ¡”Á½ÍÐµ½Á•¹¥¹œÉ•ÍÕ±Ð‘¥…±½œ¸ˆˆˆ(€€€É•ÑÕÉ¸}µ…Ñ¡}É•‘}Á…­•Ñ}Ñ•µÁ±…Ñ” (€€€€€€€ÍÉ••¹Í¡½Ð°(€€€€€€€	U%1Q%9}I}A-Q}IMU1Q}1=M}MMP°(€€€€€€€	U%1Q%9}I}A-Q}IMU1Q}1=M}Q5A1Q}95°(€€€€€€€Ñ¡É•Í¡½±°(€€€€€€€Í•…É¡}É•¥½¸¥˜Í•…É¡}É•¥½¸¥Ì¹½Ð9½¹”•±Í”}É•±…Ñ¥Ù•}É•¥½¸¡ÍÉ••¹Í¡½Ð°€À¸ÜÈ°€À¸Àà°€À¸äØ°€À¸ÌÀ¤°(€€€€¤(()‘•˜}‘•Ñ…¥±}½Á•¹}•½µ•ÑÉå}¥Í}Ù…±¥ (€€€ÍÉ••¹Í¡½Ðè%µ…”¹%µ…”°(€€€‘•Ñ…¥±}Ñ¥Ñ±”èÑÕÁ±•m¥¹Ð°¥¹Ñt°(€€€½Á•¹}‰ÕÑÑ½¸èÑÕÁ±•m¥¹Ð°¥¹Ñt°(¤€´ø‰½½°è(€€€€ˆˆ‰¡•¬Ñ¡…ÐÑ¡”Á…¥É•Á½ÁÕÀ…¹¡½ÉÌÕÍ”Ñ¡”µ•…ÍÕÉ•‘¥…±½œ•½µ•ÑÉä¸ˆˆˆ(€€€á}‘•±Ñ„€ô…‰Ì¡½Á•¹}‰ÕÑÑ½¹lÁt€´‘•Ñ…¥±}Ñ¥Ñ±•lÁt¤(€€€å}‘•±Ñ„€ô½Á•¹}‰ÕÑÑ½¹lÅt€´‘•Ñ…¥±}Ñ¥Ñ±•lÅt(€€€É•ÑÕÉ¸€ (€€€€€€€á}‘•±Ñ„€ðôÍÉ••¹Í¡½Ð¹Ý¥‘Ñ €¨€À¸ÄÐ(€€€€€€€…¹ÍÉ••¹Í¡½Ð¹¡•¥¡Ð€¨€À¸ÌÐ€ðôå}‘•±Ñ„€ðôÍÉ••¹Í¡½Ð¹¡•¥¡Ð€¨€À¸ÔÀ(€€€€¤(()‘•˜‘•Ñ•Ñ}É•‘}Á…­•Ñ}ÍÑ…Ñ” (€€€ÍÉ••¹Í¡½Ðè%µ…”¹%µ…”°(€€€Ñ¡É•Í¡½±è™±½…Ð°(¤€´øI•‘A…­•Ñ5…Ñ è(€€€€ˆˆ‰±…ÍÍ¥™äÍ…™”Ù¥ÍÕ…°ÍÑ…Ñ•Ì™½ÈÑ¡”…±±¥…¹”™ÕÉ¹…”É•µÁ…­•Ð™±½Ü¸((€€€9¼½½É‘¥¹…Ñ”¥ÌÉ•ÑÕÉ¹•™½È„•¹•É¥Œƒ–ò–B½€½¹ÑÉ½°¸€Q¡”½¹±ä(€€€½Á•¹¥¹œµÉ•…‘äÍÑ…Ñ”É•ÅÕ¥É•ÌÑ¡”ƒžSž
'–6žêŸžê‹–2€‘•Ñ…¥°Ñ¥Ñ±”…¹¥ÑÌ(€€€‰ÕÑÑ½¸Ñ¼‰”¥¹‘•Á•¹‘•¹Ñ±äÁÉ•Í•¹Ð¥¸Ñ¡”Í…µ”ÍÉ••¹Í¡½Ð¸(€€€€ˆˆˆ(€€€Í…™•}Ñ¡É•Í¡½±€ôµ…à À¸àà°Ñ¡É•Í¡½±¤(€€€Á…•}Ñ¡É•Í¡½±€ôµ…à À¸àØ°Í…™•}Ñ¡É•Í¡½±€´€À¸ÀÈ¤(€€€€ŒQ¡”ÁÉ½Ù¥‘•Íµ…±°ÑÉ¥•ÈÉ½ÀÍ½É•Ì…‰½ÕÐ€À¸àãŠLÀ¸äÀ…É½ÍÌÑ•ÍÑ•(€€€€ŒÉ•Í½±ÕÑ¥½¹Ì¸€%Ð¥Ì½¹±ä…¸ÕÁÍÑÉ•…´Í¥¹…°ì•Ù•Éä‘½Ý¹ÍÑÉ•…´…Ñ¥½¸(€€€€ŒÉ•µ…¥¹Ì…Ñ•‰äÍÑÉ½¹•ÈÁ…”½…É½‘•Ñ…¥°•Ù¥‘•¹”¸(€€€µ…É­•É}Ñ¡É•Í¡½±€ôµ…à À¸àÐ°Í…™•}Ñ¡É•Í¡½±€´€À¸ÀÐ¤((€€€É•ÍÕ±Ñ}…¹¡½È°É•ÍÕ±Ñ}…¹¡½É}Í½É”€ôµ…Ñ¡}É•‘}Á…­•Ñ}É•ÍÕ±Ð¡ÍÉ••¹Í¡½Ð°µ…à À¸àØ°Í…™•}Ñ¡É•Í¡½±€´€À¸ÀÐ¤¤(€€€É•ÍÕ±Ñ}±½Í”°É•ÍÕ±Ñ}±½Í•}Í½É”€ôµ…Ñ¡}É•‘}Á…­•Ñ}É•ÍÕ±Ñ}±½Í”¡ÍÉ••¹Í¡½Ð°µ…à À¸àä°Í…™•}Ñ¡É•Í¡½±€´€À¸ÀÄ¤¤(€€€¥˜É•ÍÕ±Ñ}…¹¡½È…¹É•ÍÕ±Ñ}±½Í”è(€€€€€€€€ŒQ¡¥ÌÍÑ…Ñ”¥¹Ñ•¹Ñ¥½¹…±±ä‘½•Ì¹½Ðµ•…¸…¸…É‰¥ÑÉ…ÉäÉ•ÍÕ±Ð‘¥…±½œ¥Ì(€€€€€€€€Œ„±…¥´ÍÕ•ÍÌ¸€Q¡”½¹ÑÉ½±±•ÈµÕÍÐÑ¥”¥ÐÑ¼¥ÑÌÁÉ••‘¥¹œ½Á•¸(€€€€€€€€Œ…Ñ¥½¸‰•™½É”½Õ¹Ñ¥¹œ¥Ð…ÌÍÕ ¸(€€€€€€€É•ÑÕÉ¸I•‘A…­•Ñ5…Ñ  (€€€€€€€€€€€I•‘A…­•ÑMÑ…Ñ”¹1%5}IMU1Q}Id°(€€€€€€€€€€€É•ÍÕ±Ñ}±½Í”°(€€€€€€€€€€€µ¥¸¡É•ÍÕ±Ñ}…¹¡½É}Í½É”°É•ÍÕ±Ñ}±½Í•}Í½É”¤°(€€€€€€€€€€€€  ‰±…¥µ}É•ÍÕ±Ðˆ°É•ÍÕ±Ñ}…¹¡½È¤°€ ‰±…¥µ}É•ÍÕ±Ñ}±½Í”ˆ°É•ÍÕ±Ñ}±½Í”¤¤°(€€€€€€€€¤((€€€‘•Ñ…¥±}Ñ¥Ñ±”°‘•Ñ…¥±}Ñ¥Ñ±•}Í½É”€ôµ…Ñ¡}™ÕÉ¹…•}ÕÁÉ…‘•}‘•Ñ…¥±}Ñ¥Ñ±”¡ÍÉ••¹Í¡½Ð°Í…™•}Ñ¡É•Í¡½±¤(€€€½Á•¹}‰ÕÑÑ½¸°½Á•¹}‰ÕÑÑ½¹}Í½É”€ôµ…Ñ¡}É•‘}Á…­•Ñ}½Á•¹}‰ÕÑÑ½¸¡ÍÉ••¹Í¡½Ð°Í…™•}Ñ¡É•Í¡½±¤(€€€¥˜‘•Ñ…¥±}Ñ¥Ñ±”…¹½Á•¹}‰ÕÑÑ½¸…¹}‘•Ñ…¥±}½Á•¹}•½µ•ÑÉå}¥Í}Ù…±¥¡ÍÉ••¹Í¡½Ð°‘•Ñ…¥±}Ñ¥Ñ±”°½Á•¹}‰ÕÑÑ½¸¤è(€€€€€€€É•ÑÕÉ¸I•‘A…­•Ñ5…Ñ  (€€€€€€€€€€€I•‘A…­•ÑMÑ…Ñ”¹Q%1}=A9}Id°(€€€€€€€€€€€½Á•¹}‰ÕÑÑ½¸°(€€€€€€€€€€€µ¥¸¡‘•Ñ…¥±}Ñ¥Ñ±•}Í½É”°½Á•¹}‰ÕÑÑ½¹}Í½É”¤°(€€€€€€€€€€€€  ‰™ÕÉ¹…•}‘•Ñ…¥±}Ñ¥Ñ±”ˆ°‘•Ñ…¥±}Ñ¥Ñ±”¤°€ ‰½Á•¹}‰ÕÑÑ½¸ˆ°½Á•¹}‰ÕÑÑ½¸¤¤°(€€€€€€€€¤(€€€¥˜‘•Ñ…¥±}Ñ¥Ñ±”è(€€€€€€€É•ÑÕÉ¸I•‘A…­•Ñ5…Ñ  (€€€€€€€€€€€I•‘A…­•ÑMÑ…Ñ”¹UI9}Q%0°(€€€€€€€€€€€‘•Ñ…¥±}Ñ¥Ñ±”°(€€€€€€€€€€€‘•Ñ…¥±}Ñ¥Ñ±•}Í½É”°(€€€€€€€€€€€€  ‰™ÕÉ¹…•}‘•Ñ…¥±}Ñ¥Ñ±”ˆ°‘•Ñ…¥±}Ñ¥Ñ±”¤°¤°(€€€€€€€€¤((€€€¡…Ñ}Á…¹•°°¡…Ñ}Á…¹•±}Í½É”€ôµ…Ñ¡}É•‘}Á…­•Ñ}¡…Ñ}Á…¹•°¡ÍÉ••¹Í¡½Ð°µ…à À¸äÌ°Á…•}Ñ¡É•Í¡½±¤¤(€€€…±±¥…¹•}Á…”°…±±¥…¹•}Á…•}Í½É”€ôµ…Ñ¡}…±±¥…¹•}¡…Ñ}Á…”¡ÍÉ••¹Í¡½Ð°µ…à À¸äÀ°Á…•}Ñ¡É•Í¡½±¤¤(€€€™ÕÉ¹…•}Á…­•Ð°™ÕÉ¹…•}Á…­•Ñ}Í½É”€ôµ…Ñ¡}™ÕÉ¹…•}ÕÁÉ…‘•}Á…­•Ð¡ÍÉ••¹Í¡½Ð°µ…à À¸äÀ°Í…™•}Ñ¡É•Í¡½±¤¤(€€€€Œ™ÕÉ¹…”…É¥Ì…Ñ¥½¹…‰±”½¹±ä¥¸„Á½Í¥Ñ¥Ù•±ä¥‘•¹Ñ¥™¥•…±±¥…¹”(€€€€Œ¡…¹¹•°¸€Ù¥ÍÕ…±±äÍ¥µ¥±…È…É¥¸…¹ä½Ñ¡•È¡…Ð½Á…”¥Ì¹½Ð•¹½Õ ¸(€€€¥˜™ÕÉ¹…•}Á…­•Ð…¹…±±¥…¹•}Á…”è(€€€€€€€É•ÑÕÉ¸I•‘A…­•Ñ5…Ñ  (€€€€€€€€€€€I•‘A…­•ÑMÑ…Ñ”¹UI9}A-P°(€€€€€€€€€€€™ÕÉ¹…•}Á…­•Ð°(€€€€€€€€€€€µ¥¸¡…±±¥…¹•}Á…•}Í½É”°™ÕÉ¹…•}Á…­•Ñ}Í½É”¤°(€€€€€€€€€€€€  ‰…±±¥…¹•}¡…Ðˆ°…±±¥…¹•}Á…”¤°€ ‰™ÕÉ¹…•}Á…­•Ðˆ°™ÕÉ¹…•}Á…­•Ð¤¤°(€€€€€€€€¤((€€€¥˜…±±¥…¹•}Á…”è(€€€€€€€É•ÑÕÉ¸I•‘A…­•Ñ5…Ñ  (€€€€€€€€€€€I•‘A…­•ÑMÑ…Ñ”¹11%9}!P°(€€€€€€€€€€€…±±¥…¹•}Á…”°(€€€€€€€€€€€…±±¥…¹•}Á…•}Í½É”°(€€€€€€€€€€€€  ‰…±±¥…¹•}¡…Ðˆ°…±±¥…¹•}Á…”¤°¤°(€€€€€€€€¤((€€€¥˜¡…Ñ}Á…¹•°è(€€€€€€€É•ÑÕÉ¸I•‘A…­•Ñ5…Ñ  (€€€€€€€€€€€I•‘A…­•ÑMÑ…Ñ”¹!Q}A90°(€€€€€€€€€€€¡…Ñ}Á…¹•°°(€€€€€€€€€€€¡…Ñ}Á…¹•±}Í½É”°(€€€€€€€€€€€€  ‰¡…Ñ}Á…¹•°ˆ°¡…Ñ}Á…¹•°¤°¤°(€€€€€€€€¤((€€€¡…Ñ}•¹ÑÉä°¡…Ñ}•¹ÑÉå}Í½É”€ôµ…Ñ¡}É•‘}Á…­•Ñ}¡…Ñ}•¹ÑÉä¡ÍÉ••¹Í¡½Ð°µ…à À¸äÀ°Á…•}Ñ¡É•Í¡½±¤¤(€€€¥˜¡…Ñ}•¹ÑÉäè(€€€€€€€É•ÑÕÉ¸I•‘A…­•Ñ5…Ñ  (€€€€€€€€€€€I•‘A…­•ÑMÑ…Ñ”¹!Q}9QId°(€€€€€€€€€€€¡…Ñ}•¹ÑÉä°(€€€€€€€€€€€¡…Ñ}•¹ÑÉå}Í½É”°(€€€€€€€€€€€€  ‰¡…Ñ}•¹ÑÉäˆ°¡…Ñ}•¹ÑÉä¤°¤°(€€€€€€€€¤((€€€µ…É­•È°µ…É­•É}Í½É”€ôµ…Ñ¡}É•‘}Á…­•Ñ}µ…É­•È¡ÍÉ••¹Í¡½Ð°µ…É­•É}Ñ¡É•Í¡½±¤(€€€¥˜µ…É­•Èè(€€€€€€€É•ÑÕÉ¸I•‘A…­•Ñ5…Ñ  (€€€€€€€€€€€I•‘A…­•ÑMÑ…Ñ”¹5I-H°(€€€€€€€€€€€µ…É­•È°(€€€€€€€€€€€µ…É­•É}Í½É”°(€€€€€€€€€€€€  ‰É•‘}Á…­•Ñ}µ…É­•Èˆ°µ…É­•È¤°¤°(€€€€€€€€¤((€€€É•ÑÕÉ¸I•‘A…­•Ñ5…Ñ  (€€€€€€€I•‘A…­•ÑMÑ…Ñ”¹U9-9=]8°(€€€€€€€9½¹”°(€€€€€€€µ…à (€€€€€€€€€€€É•ÍÕ±Ñ}…¹¡½É}Í½É”°(€€€€€€€€€€€É•ÍÕ±Ñ}±½Í•}Í½É”°(€€€€€€€€€€€‘•Ñ…¥±}Ñ¥Ñ±•}Í½É”°(€€€€€€€€€€€½Á•¹}‰ÕÑÑ½¹}Í½É”°(€€€€€€€€€€€™ÕÉ¹…•}Á…­•Ñ}Í½É”°(€€€€€€€€€€€…±±¥…¹•}Á…•}Í½É”°(€€€€€€€€€€€¡…Ñ}Á…¹•±}Í½É”°(€€€€€€€€€€€¡…Ñ}•¹ÑÉå}Í½É”°(€€€€€€€€€€€µ…É­•É}Í½É”°(€€€€€€€€¤°(€€€€¤(()‘•˜µ…Ñ¡}…±±}¡•±Á}‰ÕÑÑ½¸ (€€€ÍÉ••¹Í¡½Ðè%µ…”¹%µ…”°(€€€Ñ¡É•Í¡½±è™±½…Ð°(¤€´øÑÕÁ±•mÑÕÁ±•m¥¹Ð°¥¹Ñtð9½¹”°™±½…Ñtè(€€€€ˆˆ‰5…Ñ ½¹±äÑ¡”±…É”É••¸ƒ–£¦£–â»–*¥€½¹ÑÉ½°¸((€€€%Ð¥Ì‘•±¥‰•É…Ñ•±ä±¥µ¥Ñ•Ñ¼Ñ¡”‰½ÑÑ½´Á½ÉÑ¥½¸½˜Ñ¡”ÍÉ••¸¸€Q¡”(€€€…ÕÑ½µ…Ñ¥Œ™±½Ü¹•Ù•ÈÍÕ‰ÍÑ¥ÑÕÑ•ÌÑ¡”Íµ…±±•È¡…¹‘Í¡…­”½¹ÑÉ½°¡•É”¸(€€€€ˆˆˆ(€€€Ñ•µÁ±…Ñ”€ôQ5A1Q}%H€¼	U%1Q%9}11}!1A}Q5A1Q}95(€€€¥˜¹½ÐÑ•µÁ±…Ñ”¹¥Í}™¥±” ¤è(€€€€€€€É•ÑÕÉ¸9½¹”°€À¸À(€€€É•ÑÕÉ¸µ…Ñ¡}Ñ•µÁ±…Ñ” (€€€€€€€ÍÉ••¹Í¡½Ð°(€€€€€€€Ñ•µÁ±…Ñ”°(€€€€€€€Ñ¡É•Í¡½±°(€€€€€€€Ñ•µÁ±…Ñ•}É•™•É•¹•}Í¥é”¡Ñ•µÁ±…Ñ”¤°(€€€€€€€}É•±…Ñ¥Ù•}É•¥½¸¡ÍÉ••¹Í¡½Ð°€À¸ÄÈ°€À¸Üà°€À¸àà°€Ä¸À¤°(€€€€¤(()‘•˜‘•Ñ•Ñ}…±±¥…¹•}Á…” (€€€ÍÉ••¹Í¡½Ðè%µ…”¹%µ…”°(€€€Ñ¡É•Í¡½±è™±½…Ð°(¤€´ø±±¥…¹•A…•5…Ñ è(€€€€ˆˆ‰±…ÍÍ¥™ä½¹±äÍ…™”°Ù¥ÍÕ…°ÍÑ…Ñ•Ì½˜Ñ¡”…±±¥…¹”µ¡•±À¹…Ù¥…Ñ¥½¸™±½Ü¸((€€€U¹­¹½Ý¸Á…•Ì…É”¥¹Ñ•¹Ñ¥½¹…±±ä¹½Ð…ÍÍ¥¹•„™…±±‰…¬½½É‘¥¹…Ñ”¸€Q¡…Ð(€€€­••ÁÌ…Ñ¥Ù¥ÑäÁ½ÀµÕÁÌ°‘¥…±½Ì°…¹Õ¹É•±…Ñ•…µ”Ù¥•ÝÌ¥¹ÁÕÐµ™É•”¸(€€€€ˆˆˆ(€€€Á…•}Ñ¡É•Í¡½±€ôµ…à À¸àØ°Ñ¡É•Í¡½±€´€À¸ÀÈ¤(€€€µÕÑÕ…±}Á…”€ôÉ•Í½ÕÉ•}Á…Ñ ¡	U%1Q%9}5UQU1}A}Q5A1Q}MMP¤(€€€µÕÑÕ…±}¡•…‘•È°µÕÑÕ…±}Í½É”€ôµ…Ñ¡}Ñ•µÁ±…Ñ” (€€€€€€€ÍÉ••¹Í¡½Ð°(€€€€€€€µÕÑÕ…±}Á…”°(€€€€€€€Á…•}Ñ¡É•Í¡½±°(€€€€€€€Ñ•µÁ±…Ñ•}É•™•É•¹•}Í¥é”¡µÕÑÕ…±}Á…”¤°(€€€€€€€}É•±…Ñ¥Ù•}É•¥½¸¡ÍÉ••¹Í¡½Ð°€À¸À°€À¸À°€À¸ÔÈ°€À¸ÄØ¤°(€€€€¤¥˜µÕÑÕ…±}Á…”¹¥Í}™¥±” ¤•±Í”€¡9½¹”°€À¸À¤(€€€…±±}¡•±À°…±±}¡•±Á}Í½É”€ôµ…Ñ¡}…±±}¡•±Á}‰ÕÑÑ½¸¡ÍÉ••¹Í¡½Ð°Ñ¡É•Í¡½±¤(€€€€ŒÉ••¸‰ÕÑÑ½¸Ý¥Ñ¡½ÕÐÑ¡”µÕÑÕ…°µ¡•±ÀÑ¥Ñ±”¥Ì¹½Ð•¹½Õ Ñ¼Á•Éµ¥Ð„(€€€€Œ±¥¬¸	½Ñ …¹¡½ÉÌµÕÍÐ‰”ÁÉ•Í•¹Ð¥¸Ñ¡”Í…µ”ÍÉ••¹Í¡½Ð¸(€€€¥˜µÕÑÕ…±}¡•…‘•È…¹…±±}¡•±Àè(€€€€€€€É•ÑÕÉ¸±±¥…¹•A…•5…Ñ ¡±±¥…¹•A…”¹11}!1A}Id°…±±}¡•±À°µ¥¸¡µÕÑÕ…±}Í½É”°…±±}¡•±Á}Í½É”¤¤(€€€¥˜µÕÑÕ…±}¡•…‘•Èè(€€€€€€€É•ÑÕÉ¸±±¥…¹•A…•5…Ñ ¡±±¥…¹•A…”¹5UQU1}!1@°9½¹”°µÕÑÕ…±}Í½É”¤((€€€µÕÑÕ…±}•¹ÑÉä€ôÉ•Í½ÕÉ•}Á…Ñ ¡	U%1Q%9}5UQU1}9QIe}Q5A1Q}MMP¤(€€€•¹ÑÉå}Á½¥¹Ð°•¹ÑÉå}Í½É”€ôµ…Ñ¡}Ñ•µÁ±…Ñ” (€€€€€€€ÍÉ••¹Í¡½Ð°(€€€€€€€µÕÑÕ…±}•¹ÑÉä°(€€€€€€€Á…•}Ñ¡É•Í¡½±°(€€€€€€€Ñ•µÁ±…Ñ•}É•™•É•¹•}Í¥é”¡µÕÑÕ…±}•¹ÑÉä¤°(€€€€€€€}É•±…Ñ¥Ù•}É•¥½¸¡ÍÉ••¹Í¡½Ð°€À¸ÐÈ°€À¸ÔØ°€Ä¸À°€À¸äà¤°(€€€€¤¥˜µÕÑÕ…±}•¹ÑÉä¹¥Í}™¥±” ¤•±Í”€¡9½¹”°€À¸À¤(€€€¥˜•¹ÑÉå}Á½¥¹Ðè(€€€€€€€É•ÑÕÉ¸±±¥…¹•A…•5…Ñ ¡±±¥…¹•A…”¹11%9}!=5°•¹ÑÉå}Á½¥¹Ð°•¹ÑÉå}Í½É”¤((€€€¥Ñå}•¹ÑÉä€ôÉ•Í½ÕÉ•}Á…Ñ ¡	U%1Q%9}%Qe}11%9}Q5A1Q}MMP¤(€€€¥Ñå}Á½¥¹Ð°¥Ñå}Í½É”€ôµ…Ñ¡}Ñ•µÁ±…Ñ” (€€€€€€€ÍÉ••¹Í¡½Ð°(€€€€€€€¥Ñå}•¹ÑÉä°(€€€€€€€Á…•}Ñ¡É•Í¡½±°(€€€€€€€Ñ•µÁ±…Ñ•}É•™•É•¹•}Í¥é”¡¥Ñå}•¹ÑÉä¤°(€€€€€€€}É•±…Ñ¥Ù•}É•¥½¸¡ÍÉ••¹Í¡½Ð°€À¸ÔÈ°€À¸ÜÐ°€À¸äÐ°€Ä¸À¤°(€€€€¤¥˜¥Ñå}•¹ÑÉä¹¥Í}™¥±” ¤•±Í”€¡9½¹”°€À¸À¤(€€€¥˜¥Ñå}Á½¥¹Ðè(€€€€€€€É•ÑÕÉ¸±±¥…¹•A…•5…Ñ ¡±±¥…¹•A…”¹%Qd°¥Ñå}Á½¥¹Ð°¥Ñå}Í½É”¤(€€€É•ÑÕÉ¸±±¥…¹•A…•5…Ñ ¡±±¥…¹•A…”¹U9-9=]8°9½¹”°µ…à¡µÕÑÕ…±}Í½É”°…±±}¡•±Á}Í½É”°•¹ÑÉå}Í½É”°¥Ñå}Í½É”¤¤(()‘•˜µ…Ñ¡}…±±¥…¹•}¡•±À (€€€ÍÉ••¹Í¡½Ðè%µ…”¹%µ…”°(€€€Ñ¡É•Í¡½±è™±½…Ð°(¤€´øÑÕÁ±•mA…Ñ ð9½¹”°ÑÕÁ±•m¥¹Ð°¥¹Ñtð9½¹”°™±½…Ñtè(€€€€ˆˆ‰1•…ä•¹•É¥Œ¡•±Á•ÈèÁÉ•™•È‰Õ±¬¡•±À°Ñ¡•¸½ÁÑ¥½¹…°Íµ…±°µ¡…¹™…±±‰…¬¸ˆˆˆ(€€€…±±}¡•±Á}Á…Ñ €ôQ5A1Q}%H€¼	U%1Q%9}11}!1A}Q5A1Q}95(€€€Á½¥¹Ð°Í½É”€ôµ…Ñ¡}…±±}¡•±Á}‰ÕÑÑ½¸¡ÍÉ••¹Í¡½Ð°Ñ¡É•Í¡½±¤(€€€¥˜Á½¥¹Ðè(€€€€€€€É•ÑÕÉ¸…±±}¡•±Á}Á…Ñ °Á½¥¹Ð°Í½É”(€€€Í¥¹±•}¡•±À€ôQ5A1Q}%H€¼	U%1Q%9}!1A}Q5A1Q}95(€€€¥˜¹½ÐÍ¥¹±•}¡•±À¹¥Í}™¥±” ¤è(€€€€€€€É•ÑÕÉ¸…±±}¡•±Á}Á…Ñ ¥˜…±±}¡•±Á}Á…Ñ ¹¥Í}™¥±” ¤•±Í”9½¹”°9½¹”°Í½É”(€€€™…±±‰…­}Á½¥¹Ð°™…±±‰…­}Í½É”€ôµ…Ñ¡}Ñ•µÁ±…Ñ” (€€€€€€€ÍÉ••¹Í¡½Ð°(€€€€€€€Í¥¹±•}¡•±À°(€€€€€€€Ñ¡É•Í¡½±°(€€€€€€€Ñ•µÁ±…Ñ•}É•™•É•¹•}Í¥é”¡Í¥¹±•}¡•±À¤°(€€€€¤(€€€¥˜™…±±‰…­}Á½¥¹Ðè(€€€€€€€É•ÑÕÉ¸Í¥¹±•}¡•±À°™…±±‰…­}Á½¥¹Ð°™…±±‰…­}Í½É”(€€€É•ÑÕÉ¸…±±}¡•±Á}Á…Ñ ¥˜…±±}¡•±Á}Á…Ñ ¹¥Í}™¥±” ¤•±Í”Í¥¹±•}¡•±À°9½¹”°µ…à¡Í½É”°™…±±‰…­}Í½É”¤(()‘•˜Í…±•}É•½É‘•‘}Á½¥¹Ð (€€€Á½¥¹ÐèÑÕÁ±•m¥¹Ð°¥¹Ñt°(€€€Í½ÕÉ•}Í¥é”èÑÕÁ±•m¥¹Ð°¥¹Ñt°(€€€ÕÉÉ•¹Ñ}Í¥é”èÑÕÁ±•m¥¹Ð°¥¹Ñt°(¤€´øÑÕÁ±•m¥¹Ð°¥¹Ñtè(€€€à°ä€ôÁ½¥¹Ð(€€€Í½ÕÉ•}Ü°Í½ÕÉ•} €ôÍ½ÕÉ•}Í¥é”(€€€ÕÉÉ•¹Ñ}Ü°ÕÉÉ•¹Ñ} €ôÕÉÉ•¹Ñ}Í¥é”(€€€¥˜ÕÉÉ•¹Ñ}Ü€¼ÕÉÉ•¹Ñ} €øÍ½ÕÉ•}Ü€¼Í½ÕÉ•} €¬€À¸ÀÄè(€€€€€€€Í…±”€ôÕÉÉ•¹Ñ} €¼Í½ÕÉ•} (€€€€€€€Í…±•‘}à€ô€¡ÕÉÉ•¹Ñ}Ü€´Í½ÕÉ•}Ü€¨Í…±”¤€¼€È€¬à€¨Í…±”(€€€€€€€Í…±•‘}ä€ôä€¨Í…±”(€€€•±Í”è(€€€€€€€Í…±•‘}à€ôà€¨ÕÉÉ•¹Ñ}Ü€¼Í½ÕÉ•}Ü(€€€€€€€Í…±•‘}ä€ôä€¨ÕÉÉ•¹Ñ} €¼Í½ÕÉ•} (€€€É•ÑÕÉ¸É½Õ¹¡Í…±•‘}à¤°É½Õ¹¡Í…±•‘}ä¤(