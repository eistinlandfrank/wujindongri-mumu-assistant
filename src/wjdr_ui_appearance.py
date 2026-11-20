"""Application-wide appearance, shared by all assistant instances."""

from __future__ import annotations

import ctypes
from ctypes import wintypes

from PySide6.QtCore import QEvent, QObject, QSettings, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QApplication, QWidget


THEME_KEY = "appearance/theme"
APPEARANCE_MODES = {"system": "跟随系统", "light": "浅色", "dark": "深色"}

DWMWA_USE_IMMERSIVE_DARK_MODE = 20
DWMWA_CAPTION_COLOR = 35
DWMWA_TEXT_COLOR = 36


COLORS = {
    "window": "#F4F7FC",
    "surface": "#FFFFFF",
    "surface_alt": "#F7F9FD",
    "navy": "#101C33",
    "navy_2": "#162744",
    "text": "#17243B",
    "muted": "#6C7A91",
    "border": "#DFE6F1",
    "blue": "#3478F6",
    "blue_dark": "#245EC8",
    "green": "#16A36D",
    "green_soft": "#E7F8F1",
    "red": "#DE5262",
    "amber": "#F2A33A",
    "input": "#FFFFFF",
    "header": "#EDF3FC",
    "hover": "#F0F5FC",
    "focus": "#8EAEDE",
    "accent": "#255EC5",
    "accent_bg": "#E9F0FE",
    "accent_border": "#CDDCF8",
    "primary": "#2B64CF",
    "primary_hover": "#2457B8",
    "selection": "#DBE8FF",
    "disabled": "#647388",
    "disabled_bg": "#EEF2F8",
    "success": "#0E7150",
    "warning": "#874525",
    "warning_bg": "#FFF8F0",
    "warning_border": "#F1D4B1",
    "danger": "#A63142",
    "danger_bg": "#FFF0F1",
    "danger_border": "#F2CCD2",
    "danger_hover": "#FCE1E4",
    "danger_button": "#BB3D50",
    "scrollbar": "#BAC8DF",
}

THEMES = {
    "light": COLORS,
    "dark": {
        **COLORS,
        "window": "#101827",
        "surface": "#192538",
        "surface_alt": "#1E2C41",
        "navy": "#0B1322",
        "text": "#E8EFFB",
        "muted": "#A9B8CE",
        "border": "#33445E",
        "input": "#142033",
        "header": "#26364E",
        "hover": "#253650",
        "focus": "#7EA8EF",
        "accent": "#A3C4FF",
        "accent_bg": "#243960",
        "accent_border": "#3A5684",
        "primary": "#3266C9",
        "primary_hover": "#3A71DA",
        "selection": "#314F7D",
        "disabled": "#8799B2",
        "disabled_bg": "#1C283B",
        "success": "#8BE1BF",
        "green_soft": "#163A36",
        "warning": "#F0BF92",
        "warning_bg": "#352921",
        "warning_border": "#614631",
        "danger": "#FFAFB8",
        "danger_bg": "#39232E",
        "danger_border": "#653946",
        "danger_hover": "#50303D",
        "danger_button": "#B04056",
        "scrollbar": "#586D8A",
    },
}


def theme_palette(colors: dict[str, str]) -> QPalette:
    palette = QPalette()
    role = QPalette.ColorRole
    for name, key in {
        role.Window: "window", role.WindowText: "text", role.Base: "input",
        role.AlternateBase: "surface_alt", role.Text: "text", role.Button: "surface",
        role.ButtonText: "text", role.Highlight: "selection", role.HighlightedText: "text",
        role.ToolTipBase: "surface", role.ToolTipText: "text", role.PlaceholderText: "muted",
        role.Link: "accent", role.Mid: "border", role.Light: "focus", role.Dark: "window",
    }.items():
        palette.setColor(name, QColor(colors[key]))
    for name in (role.Text, role.ButtonText, role.WindowText):
        palette.setColor(QPalette.ColorGroup.Disabled, name, QColor(colors["disabled"]))
    return palette


def _dwm_set_window_attribute():
    try:
        setter = ctypes.WinDLL("dwmapi").DwmSetWindowAttribute
    except (AttributeError, OSError):
        return None
    setter.argtypes = (wintypes.HWND, wintypes.DWORD, ctypes.c_void_p, wintypes.DWORD)
    setter.restype = ctypes.c_long
    return setter


class ApplicationAppearance(QObject):
    changed = Signal()

    def __init__(self, app: QApplication, settings: QSettings) -> None:
        super().__init__(app)
        self.app = app
        self.settings = settings
        self.mode = self._stored_mode = self._read_mode()
        self.theme = ""
        self.style_hints = app.styleHints()
        self.style_hints.colorSchemeChanged.connect(self._system_scheme_changed)
        self._set_window_attribute = _dwm_set_window_attribute() if app.platformName() == "windows" else None
        if self._set_window_attribute is not None:
            app.installEventFilter(self)
        self.sync_timer = QTimer(self)
        self.sync_timer.setInterval(1000)
        self.sync_timer.timeout.connect(self.sync_preferences)
        self.sync_timer.start()
        self._apply()

    @classmethod
    def current(cls) -> ApplicationAppearance:
        app = QApplication.instance()
        appearance = getattr(app, "appearance", None)
        if appearance is None:
            appearance = app.appearance = cls(app, QSettings("WJDR Tools", "WJDRMuMuAssistant"))
        return appearance

    def _read_mode(self) -> str:
        mode = self.settings.value(THEME_KEY, "system", type=str)
        return mode if mode in APPEARANCE_MODES else "system"

    def set_mode(self, mode: str, *, persist: bool = True) -> None:
        if mode not in APPEARANCE_MODES:
            raise ValueError(f"Unknown appearance mode: {mode}")
        if persist:
            self.settings.setValue(THEME_KEY, mode)
            self.settings.sync()
            self._stored_mode = mode
        if self.mode != mode:
            self.mode = mode
            self._apply()

    def sync_preferences(self) -> None:
        self.settings.sync()
        mode = self._read_mode()
        if mode != self._stored_mode:
            self._stored_mode = mode
            self.set_mode(mode, persist=False)

    def _system_scheme_changed(self) -> None:
        if self.mode == "system":
            QTimer.singleShot(0, self, self._apply_system_scheme)

    def _apply_system_scheme(self) -> None:
        if self.mode == "system" and self.theme != self._effective_theme():
            self._apply()

    def _effective_theme(self) -> str:
        if self.mode != "system":
            return self.mode
        return "dark" if self.style_hints.colorScheme() == Qt.ColorScheme.Dark else "light"

    def _apply(self) -> None:
        self.theme = self._effective_theme()
        self.app.setPalette(theme_palette(THEMES[self.theme]))
        self.changed.emit()
        if self._set_window_attribute is not None:
            for widget in self.app.topLevelWidgets():
                self._apply_caption(widget)

    def eventFilter(self, target: QObject, event: QEvent) -> bool:
        if event.type() == QEvent.Type.Show and isinstance(target, QWidget):
            self._apply_caption(target)
        return False

    def _apply_caption(self, widget: QWidget) -> None:
        if widget.windowType() not in (Qt.WindowType.Window, Qt.WindowType.Dialog, Qt.WindowType.Tool):
            return
        if widget.windowFlags() & Qt.WindowType.FramelessWindowHint:
            return
        hwnd = widget.effectiveWinId()
        if not hwnd:
            return
        colors = THEMES[self.theme]
        caption, text = (QColor(colors[key]) for key in ("surface", "text"))
        for attribute, value in (
            (DWMWA_USE_IMMERSIVE_DARK_MODE, int(self.theme == "dark")),
            (DWMWA_CAPTION_COLOR, caption.red() | (caption.green() << 8) | (caption.blue() << 16)),
            (DWMWA_TEXT_COLOR, text.red() | (text.green() << 8) | (text.blue() << 16)),
        ):
            data = wintypes.DWORD(value)
            self._set_window_attribute(hwnd, attribute, ctypes.byref(data), ctypes.sizeof(data))
