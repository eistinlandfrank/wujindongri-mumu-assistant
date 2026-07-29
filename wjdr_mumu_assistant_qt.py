# -*- coding: utf-8 -*-
"""Release-grade PySide6 desktop UI for the MuMu alliance-help assistant."""

from __future__ import annotations

import argparse
import ctypes
import json
import os
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Any, Callable

from PIL import Image
from PySide6.QtCore import QObject, QPoint, QRect, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QFont, QIcon, QImage, QPainter, QPainterPath, QPalette, QPen, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSlider,
    QSpinBox,
    QStackedWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
    QInputDialog,
)

from wjdr_backend import (
    APP_NAME,
    APP_VERSION,
    AlliancePage,
    BUILTIN_ALL_HELP_TEMPLATE_NAME,
    BUILTIN_CITY_ALLIANCE_TEMPLATE_ASSET,
    BUILTIN_HELP_TEMPLATE_NAME,
    BUILTIN_MUTUAL_ENTRY_TEMPLATE_ASSET,
    BUILTIN_MUTUAL_PAGE_TEMPLATE_ASSET,
    CONFIG_DIR,
    CREATE_NO_WINDOW,
    DEFAULT_TASKS,
    DeviceLease,
    LOG_FILE,
    MuMuADB,
    RED_PACKET_BUILTIN_TEMPLATES,
    RedPacketState,
    TASK_FILE,
    TEMPLATE_DIR,
    clean_name,
    detect_alliance_page,
    detect_red_packet_state,
    match_red_packet_marker,
    match_template,
    prepare_storage,
    resource_path,
    scale_recorded_point,
    template_reference_size,
)


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
}


class UiSignals(QObject):
    log = Signal(str)
    status = Signal(str, str)
    devices = Signal(object, str)
    image = Signal(object)
    running = Signal(bool, str)
    clicks = Signal(int)
    red_packet_state = Signal(str)
    alert = Signal(str, str)


class Card(QFrame):
    def __init__(self, parent: QWidget | None = None, name: str = "card") -> None:
        super().__init__(parent)
        self.setObjectName(name)
        self.setFrameShape(QFrame.Shape.NoFrame)


class ScreenshotView(QWidget):
    point_selected = Signal(int, int)
    region_selected = Signal(object)

    def __init__(self) -> None:
        super().__init__()
        self.setMinimumSize(360, 430)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setCursor(Qt.CursorShape.CrossCursor)
        self.image: QImage | None = None
        self.image_size = (1, 1)
        self.drag_start: QPoint | None = None
        self.drag_end: QPoint | None = None

    def set_pil_image(self, image: Image.Image) -> None:
        rgb = image.convert("RGB")
        raw = rgb.tobytes("raw", "RGB")
        self.image = QImage(raw, rgb.width, rgb.height, rgb.width * 3, QImage.Format.Format_RGB888).copy()
        self.image_size = rgb.size
        self.drag_start = self.drag_end = None
        self.update()

    def _target_rect(self) -> QRect:
        margin = 18
        bounds = self.rect().adjusted(margin, margin, -margin, -margin)
        if not self.image:
            return bounds
        scale = min(bounds.width() / self.image.width(), bounds.height() / self.image.height())
        width, height = int(self.image.width() * scale), int(self.image.height() * scale)
        return QRect(bounds.center().x() - width // 2, bounds.center().y() - height // 2, width, height)

    def _to_image(self, point: QPoint) -> tuple[int, int] | None:
        if not self.image:
            return None
        target = self._target_rect()
        if not target.contains(point):
            return None
        x = int((point.x() - target.x()) * self.image.width() / max(1, target.width()))
        y = int((point.y() - target.y()) * self.image.height() / max(1, target.height()))
        return min(x, self.image.width() - 1), min(y, self.image.height() - 1)

    def paintEvent(self, _event: Any) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.fillRect(self.rect(), QColor("#0C1424"))
        if self.image:
            target = self._target_rect()
            path = QPainterPath()
            path.addRoundedRect(target, 12, 12)
            painter.setClipPath(path)
            painter.drawImage(target, self.image)
            painter.setClipping(False)
            painter.setPen(QPen(QColor("#263754"), 1))
            painter.drawRoundedRect(target, 12, 12)
        else:
            painter.setPen(QColor("#8EA1BF"))
            painter.setFont(QFont("Microsoft YaHei UI", 11))
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "æ­£åœ¨èŽ·å– MuMu ç”»é¢â€¦")
        if self.drag_start and self.drag_end:
            rect = QRect(self.drag_start, self.drag_end).normalized()
            painter.fillRect(rect, QColor(52, 120, 246, 45))
            painter.setPen(QPen(QColor(COLORS["blue"]), 2))
            painter.drawRoundedRect(rect, 5, 5)

    def mousePressEvent(self, event: Any) -> None:
        if event.button() == Qt.MouseButton.LeftButton and self._to_image(event.position().toPoint()):
            self.drag_start = self.drag_end = event.position().toPoint()
            self.update()

    def mouseMoveEvent(self, event: Any) -> None:
        if self.drag_start:
            self.drag_end = event.position().toPoint()
            self.update()

    def mouseReleaseEvent(self, event: Any) -> None:
        if not self.drag_start or not self.drag_end:
            return
        start, end = self.drag_start, event.position().toPoint()
        self.drag_end = end
        p0, p1 = self._to_image(start), self._to_image(end)
        if p0 and p1:
            if (start - end).manhattanLength() < 10:
                self.point_selected.emit(*p1)
                self.drag_start = self.drag_end = None
            else:
                x0, x1 = sorted((p0[0], p1[0]))
                y0, y1 = sorted((p0[1], p1[1]))
                if x1 - x0 >= 8 and y1 - y0 >= 8:
                    self.region_selected.emit((x0, y0, x1, y1))
        self.update()


class MainWindow(QMainWindow):
    def __init__(
        self,
        preferred_device: str | None,
        auto_help: bool,
        all_auto_help: bool,
        auto_red_packet: bool,
        all_auto_red_packet: bool,
        interval_override: float | None = None,
    ) -> None:
        super().__init__()
        prepare_storage()
        self.preferred_device = preferred_device
        self.auto_help_requested = auto_help
        self.all_auto_help_requested = all_auto_help
        self.auto_red_packet_requested = auto_red_packet
        self.all_auto_red_packet_requested = all_auto_red_packet
        self.adb: MuMuADB | None = None
        self.devices: list[str] = []
        self.current_image: Image.Image | None = None
        self.selected_point: tuple[int, int] | None = None
        self.selected_source_size: tuple[int, int] | None = None
        self.selected_region: tuple[int, int, int, int] | None = None
        self.stop_event = threading.Event()
        self.closing = threading.Event()
        self.worker: threading.Thread | None = None
        self.started_at = 0.0
        self.tasks = self._load_tasks()
        self.active_steps: list[dict[str, Any]] = []
        self.signals = UiSignals()
        self._connect_signals()
        self.setWindowTitle(f"{APP_NAME} {APP_VERSION}")
        icon = resource_path("app_icon.svg")
        if icon.is_file():
            self.setWindowIcon(QIcon(str(icon)))
        self.resize(1280, 840)
        self.setMinimumSize(1080, 720)
        self._build_ui()
        if interval_override is not None:
            self.interval_spin.setValue(max(self.interval_spin.minimum(), min(interval_override, self.interval_spin.maximum())))
            self.red_packet_interval_spin.setValue(
                max(self.red_packet_interval_spin.minimum(), min(interval_override, self.red_packet_interval_spin.maximum()))
            )
        self._apply_style()
        self._refresh_templates()
        self._refresh_tasks()
        self._load_log_tail()
        threading.Thread(target=self._hotkey_loop, daemon=True).start()
        self._run_async(self._connect_job)

    def _connect_signals(self) -> None:
        self.signals.log.connect(self._append_log)
        self.signals.status.connect(self._set_status)
        self.signals.devices.connect(self._apply_devices)
        self.signals.image.connect(self._apply_image)
        self.signals.running.connect(self._set_running)
        self.signals.clicks.connect(lambda count: self.click_count.setText(str(count)))
        self.signals.red_packet_state.connect(lambda text: self.red_packet_state_label.setText(text))
        self.signals.alert.connect(self._show_alert)

    def _build_ui(self) -> None:
        root = QWidget()
        root.setObjectName("root")
        self.setCentralWidget(root)
        shell = QHBoxLayout(root)
        shell.setContentsMargins(0, 0, 0, 0)
        shell.setSpacing(0)

        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(224)
        side = QVBoxLayout(sidebar)
        side.setContentsMargins(18, 24, 18, 20)
        side.setSpacing(8)
        brand_row = QHBoxLayout()
        brand_icon = QLabel("â„")
        brand_icon.setObjectName("brandIcon")
        brand_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        brand_text = QVBoxLayout()
        brand = QLabel("æ— å°½å†¬æ—¥åŠ©æ‰‹")
        brand.setObjectName("brand")
        brand_sub = QLabel(f"DESKTOP  Â·  v{APP_VERSION}")
        brand_sub.setObjectName("brandSub")
        brand_text.addWidget(brand)
        brand_text.addWidget(brand_sub)
        brand_row.addWidget(brand_icon)
        brand_row.addLayout(brand_text, 1)
        side.addLayout(brand_row)
        side.addSpacing(25)
        self.nav_buttons: list[QPushButton] = []
        nav_items = [
            ("âŒ‚", "è®¾å¤‡ä¸­å¿ƒ"),
            ("â—‰", "è”ç›Ÿå¸®åŠ©"),
            ("âœ¦", "è”ç›Ÿçº¢åŒ…"),
            ("â˜·", "ä»»åŠ¡ç¼–æŽ’"),
            ("â‰¡", "è¿è¡Œæ—¥å¿—"),
            ("i", "å…³äºŽä¸Žå®‰å…¨"),
        ]
        for index, (glyph, text) in enumerate(nav_items):
            button = QPushButton(f"{glyph}    {text}")
            button.setObjectName("navButton")
            button.setCheckable(True)
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.clicked.connect(lambda _checked=False, page=index: self._show_page(page))
            side.addWidget(button)
            self.nav_buttons.append(button)
        self.nav_buttons[0].setChecked(True)
        side.addStretch()
        safety = Card(name="sidebarCard")
        safety_layout = QVBoxLayout(safety)
        safety_layout.setContentsMargins(14, 13, 14, 13)
        safety_title = QLabel("å…¨å±€æ€¥åœ")
        safety_title.setObjectName("sideCardTitle")
        safety_text = QLabel("æŒ‰ F8 åœæ­¢æ‰€æœ‰åŠ©æ‰‹çª—å£\nç•Œé¢åœæ­¢ä»…å½±å“å½“å‰çª—å£")
        safety_text.setObjectName("sideCardText")
        safety_layout.addWidget(safety_title)
        safety_layout.addWidget(safety_text)
        side.addWidget(safety)
        shell.addWidget(sidebar)

        main = QWidget()
        main.setObjectName("main")
        main_layout = QVBoxLayout(main)
        main_layout.setContentsMargins(30, 22, 30, 26)
        main_layout.setSpacing(18)
        top = QHBoxLayout()
        titles = QVBoxLayout()
        self.page_title = QLabel("è®¾å¤‡ä¸­å¿ƒ")
        self.page_title.setObjectName("pageTitle")
        self.page_subtitle = QLabel("é€‰æ‹© MuMu å®žä¾‹ï¼Œç¡®è®¤ç”»é¢åŽå¼€å§‹è¿è¡Œ")
        self.page_subtitle.setObjectName("pageSubtitle")
        titles.addWidget(self.page_title)
        titles.addWidget(self.page_subtitle)
        top.addLayout(titles)
        top.addStretch()
        self.device_combo = QComboBox()
        self.device_combo.setObjectName("deviceCombo")
        self.device_combo.setMinimumWidth(360)
        self.device_combo.currentIndexChanged.connect(self._device_changed)
        top.addWidget(self.device_combo)
        scan = QPushButton("â†»  æ‰«æ")
        scan.setObjectName("ghostButton")
        scan.clicked.connect(lambda: self._run_async(self._connect_job))
        top.addWidget(scan)
        self.status_pill = QLabel("â—  æ­£åœ¨è¿žæŽ¥")
        self.status_pill.setObjectName("statusPill")
        top.addWidget(self.status_pill)
        main_layout.addLayout(top)

        self.stack = QStackedWidget()
        self.stack.addWidget(self._build_dashboard())
        self.stack.addWidget(self._build_automation())
        self.stack.addWidget(self._build_red_packet_page())
        self.stack.addWidget(self._build_tasks_page())
        self.stack.addWidget(self._build_log_page())
        self.stack.addWidget(self._build_about_page())
        main_layout.addWidget(self.stack, 1)
        shell.addWidget(main, 1)

    def _build_dashboard(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)
        hero = Card(name="hero")
        hero_layout = QHBoxLayout(hero)
        hero_layout.setContentsMargins(26, 22, 24, 22)
        hero_text = QVBoxLayout()
        kicker = QLabel("è”ç›Ÿå¸®åŠ©é¡µé¢æµç¨‹")
        kicker.setObjectName("heroKicker")
        title = QLabel("è‡ªåŠ¨è¿›å…¥è”ç›Ÿäº’åŠ©ï¼Œè¯†åˆ«åŽç‚¹å‡»â€œå…¨éƒ¨å¸®åŠ©â€")
        title.setObjectName("heroTitle")
        desc = QLabel("ä¸»åŸŽ â†’ è”ç›Ÿ â†’ è”ç›Ÿäº’åŠ©ï¼›ä»…åœ¨æ ‡é¢˜ä¸Žç»¿è‰²æŒ‰é’®åŒæ—¶ç¡®è®¤æ—¶ç‚¹å‡»ï¼Œç©ºé¡µåŽŸåœ°ç­‰å¾…ã€‚")
        desc.setObjectName("heroText")
        hero_text.addWidget(kicker)
        hero_text.addWidget(title)
        hero_text.addWidget(desc)
        hero_layout.addLayout(hero_text, 1)
        self.start_button = QPushButton("â–¶  è‡ªåŠ¨å¯¼èˆªå¹¶å…¨éƒ¨å¸®åŠ©")
        self.start_button.setObjectName("primaryButton")
        self.start_button.clicked.connect(self._start_help_preset)
        stop = QPushButton("â–   åœæ­¢")
        stop.setObjectName("dangerButton")
        stop.clicked.connect(self.stop_all)
        hero_layout.addWidget(self.start_button)
        hero_layout.addWidget(stop)
        layout.addWidget(hero)

        content = QHBoxLayout()
        content.setSpacing(16)
        preview_card = Card()
        preview_layout = QVBoxLayout(preview_card)
        preview_layout.setContentsMargins(18, 16, 18, 16)
        preview_header = QHBoxLayout()
        preview_title = QLabel("å®žæ—¶ç”»é¢")
        preview_title.setObjectName("cardTitle")
        self.point_label = QLabel("å•å‡»é€‰ç‚¹ Â· æ‹–åŠ¨æ¡†é€‰æ¨¡æ¿")
       ÛNôæÚ$z{-®éÜj×–bÖ…ö6Æ–6·2æB6Æ–6·2ãÒÖ…ö6Æ–6·3 ¢6VÆbæÆör‚.[{.‹ëîX‹iÈZI®x+žX{¾jÊi[8""¢'&V°¢G'“ ¢–bwV&BæBæ÷BF&vWBæf÷&Vw&÷VæEö—5övÖR‚“ ¢VÆ6VBÒF–ÖRæÖöæ÷Föæ–2‚’Ò7F'FV@¢–bVÆ6VBÒÆ7Eö–FÆRãÒ3 ¢6VÆbæÆör‚.k‹ŽhˆþKˆÞYÊŽX˜ÞXûûÈÎiÊÎ‹Úîi¨.XÎ8""¢Æ7Eö–FÆRÒVÆ6V@¢VÆ–bÖöFRÓÒ&f—†VB# ¢76W'Bf—†VE÷ö–çB—2æ÷BæöæRæBf—†VE÷6÷W&6U÷6—¦R—2æ÷BæöæP¢ö–çBÒ66ÆU÷&V6÷&FVE÷ö–çB†f—†VE÷ö–çBÂf—†VE÷6÷W&6U÷6—¦RÂF&vWBç67&VVå÷6—¦R‚’¢F&vWBçF‚§ö–çB¢6Æ–6·2³Ò¢6VÆbç6–væÇ2æ6Æ–6·2æVÖ—B†6Æ–6·2¢–b6Æ–6·2ÓÒ÷"6Æ–6·2R#ÓÒ ¢6VÆbæÆör†b.[{.x+žX{²¶6Æ–6·7ÒjÊûÈÎYÙjr·ö–çGÞ8""¢VÇ6S ¢–ÖvRÒF&vWBç67&VVç6†÷B‚¢ö–çBÂ66÷&RÒÖF6…÷FV×ÆFR†–ÖvRÂFV×ÆFRÂF‡&W6†öÆBÂFV×ÆFU÷&VfW&Væ6U÷6—¦R‡FV×ÆFR’¢ÖF6†VEöæÖRÒFV×ÆFRç7FVÐ¢–bö–çC ¢F&vWBçF‚§ö–çB¢6Æ–6·2³Ò¢6VÆbç6–væÇ2æ6Æ–6·2æVÖ—B†6Æ–6·2¢6VÆbæÆör†b.ŠønXŠ¾h‰X©þ[›nx+žX{²¶ÖF6†VEöæÖWÒ·ö–çGÞûÈÎy»ŽKËÎ[ªb·66÷&S¢ã6gÞûÈÎ{JþŠê¶6Æ–6·7ÒjÊ8""¢VÇ6S ¢VÆ6VBÒF–ÖRæÖöæ÷Föæ–2‚’Ò7F'FV@¢–bVÆ6VBÒÆ7Eö–FÆRãÒ3 ¢6VÆbæÆör†b.zØž[è^hÈž™*îX{®xëûÈÎ[Ù>X˜ÞiÈš¹Žy»ŽKËÎ[ªb·66÷&S¢ã6gÞ8""¢Æ7Eö–FÆRÒVÆ6V@¢f–ÇW&W2Ò ¢W†6WBW†6WF–öâ2W†3 ¢f–ÇW&W2³Ò¢6VÆbæÆör†b.iÊÎ‹ÚîZK‹J^ûÈ‡¶f–ÇW&W7Òó>ûÈžûÉ§¶W†7Ò"¢–bf–ÇW&W2ãÒ3 ¢'&V°¢–b6VÆbç7F÷öWfVçBçv—B†–çFW'fÂ“ ¢'&V°¢6VÆbæÆör†b.‹ùŠÎ{¹>iÙþûÈÎX[x+žX{²¶6Æ–6·7ÒjÊ8"" ¢6VÆbå÷7F'E÷v÷&¶W"‡F&vWBæFWf–6RÂ¦ö" ¢FVb÷7F'E÷v÷&¶W"‡6VÆbÂFWf–6S¢7G"Â6ÆÆ&6³¢6ÆÆ&ÆUµµÒÂæöæUÒ’ÓâæöæS ¢–b6VÆbçv÷&¶W"æB6VÆbçv÷&¶W"æ—5öÆ—fR‚“ ¢ÖW76vT&÷‚æ–æf÷&ÖF–öâ‡6VÆbÂôäÔRÂ.[Ù>X˜Þz©~Xú>[{.iÈžK»¾XªjÚ>YÊŽ‹ùŠÎ8""¢&WGW&à¢6VÆbç7F÷öWfVçBæ6ÆV"‚¢6VÆbç6–væÇ2æ6Æ–6·2æVÖ—Bƒ ¢FVb&÷FV7FVB‚’ÓâæöæS ¢ÆV6RÒFWf–6TÆV6R†FWf–6R¢–bæ÷BÆV6Ræ7V—&R‚“ ¢6VÆbæÆör†b.ZéîKè²¶FWf–6WÒ[{.Š*¾XúnKˆKŠ®z©~Xú>XÚyJŽûÈÎiÊÎz©~Xú>iÊ®Y
þXªŽK»¾Xª8""¢6VÆbç6–væÇ2æÆW'BæVÖ—B„ôäÔRÂb'¶FWf–6WÒ[{.YÊŽXúnKˆKŠ®Xªžh˜¾z©~Xú>‹ùŠÎ8%ÆîK‹®™‹.jÚ.˜xÞZHÞx+žX{¾ûÈÎiÊÎz©~Xú>iÊ®Y
þXªŽK»¾Xª8""¢&WGW&à¢6VÆbç6–væÇ2ç'Vææ–æræVÖ—B…G'VRÂ.‹ùŠÎKŠÒ"¢G'“ ¢6ÆÆ&6²‚¢f–æÆÇ“ ¢ÆV6Rç&VÆV6R‚¢6VÆbç7F÷öWfVçBç6WB‚¢6VÆbç6–væÇ2ç'Vææ–æræVÖ—B„fÇ6RÂ.[{.XÎjÚ"" ¢6VÆbçv÷&¶W"ÒF‡&VF–æråF‡&VB‡F&vWC×&÷FV7FVBÂFVÖöãÕG'VR¢6VÆbçv÷&¶W"ç7F'B‚ ¢FVb7F÷öÆÂ‡6VÆb’ÓâæöæS ¢6VÆbç7F÷öWfVçBç6WB‚¢6VÆbæÆör‚.[{.XùX{®XÎjÚ.hÈ~KºN8"" ¢FVb÷WFFU÷'VçF–ÖR‡6VÆb’ÓâæöæS ¢6V6öæG2ÒÖ‚ƒÂ–çB‡F–ÖRæÖöæ÷Föæ–2‚’Ò6VÆbç7F'FVEöB’¢6VÆbç'VçF–ÖUöÆ&VÂç6WEFW‡B†b'·6V6öæG2òò3c£&GÓ§·6V6öæG2òòcRc£&GÓ§·6V6öæG2Rc£&GÒ" ¢FVbö76—7FçEö6öÖÖæB‡6VÆbÂFWf–6S¢7G"Â7F'GWöÖöFS¢7G"ÂæöæRÒæöæR’ÓâÆ—7E·7G%Ó ¢–bvWFGG"‡7—2Â&g&÷¦Vâ"ÂfÇ6R“ ¢6öÖÖæBÒ·7—2æW†V7WF&ÆUÐ¢VÇ6S ¢6öÖÖæBÒ·7—2æW†V7WF&ÆRÂ7G"…F‚…õöf–ÆUõò’ç&W6öÇfR‚’•Ð¢6öÖÖæB³Ò²"ÒÖFWf–6R"ÂFWf–6UÐ¢–b7F'GWöÖöFRÓÒ&†VÇ# ¢6öÖÖæB³Ò²"ÒÖWFòÖ†VÇ"Â"ÒÖ–çFW'fÂ"Â7G"‡6VÆbæ–çFW'fÅ÷7–âçfÇVR‚’•Ð¢VÆ–b7F'GWöÖöFRÓÒ'&VE÷6¶WB# ¢6öÖÖæB³Ò²"ÒÖWFò×&VB×6¶WB"Â"ÒÖ–çFW'fÂ"Â7G"‡6VÆbç&VE÷6¶WEö–çFW'fÅ÷7–âçfÇVR‚’•Ð¢&WGW&â6öÖÖæ@ ¢FVb÷7våö–ç7Fæ6R‡6VÆbÂFWf–6S¢7G"Â7F'GWöÖöFS¢7G"ÂæöæRÒæöæR’ÓâæöæS ¢G'“ ¢7V'&ö6W72å÷Vâ€¢6VÆbåö76—7FçEö6öÖÖæB†FWf–6RÂ7F'GWöÖöFR’À¢7vC×7G"…F‚‡7—2æW†V7WF&ÆR’ç&W6öÇfR‚’ç&VçB–bvWFGG"‡7—2Â&g&÷¦Vâ"ÂfÇ6R’VÇ6RF‚…õöf–ÆUõò’ç&W6öÇfR‚’ç&VçB’À¢7&VF–öæfÆw3Ô5$TDUôäõõt”äDõrÀ¢¢ÖöFU÷FW‡BÒ²&†VÇ#¢.[›n[ÈZx¾ˆNy¹þ[ŠîXª’"Â'&VE÷6¶WB#¢.[›n[ÈZx¾hª.{ª.XÈR'ÒævWB‡7F'GWöÖöFRÂ""¢6VÆbæÆör†b.[{.K‹¢¶FWf–6WÒh™>[ÈxºÎz¸¾z©~Xú7¶ÖöFU÷FW‡GÞ8""¢W†6WBõ4W'&÷"2W†3 ¢ÖW76vT&÷‚çv&æ–ær‡6VÆbÂôäÔRÂb.izk9^h™>[ÈxºÎz¸¾z©~Xú>ûÉ§¶W†7Ò" ¢FVbö÷Vå÷6VÆV7FVE÷v–æF÷r‡6VÆb’ÓâæöæS ¢–b6VÆbæF# ¢6VÆbå÷7våö–ç7Fæ6R‡6VÆbæF"æFWf–6R ¢FVb÷7F'EöÆÅö–ç7Fæ6W2‡6VÆbÂ7F'GWöÖöFS¢7G"Ò&†VÇ"’ÓâæöæS ¢–bæ÷B6VÆbæFWf–6W3 ¢ÖW76vT&÷‚çv&æ–ær‡6VÆbÂôäÔRÂ.k*iÈžXùxë‹ùŠÎKŠÞy¨B×T×RZéîKè¾8""¢&WGW&à¢f÷"FWf–6R–â6VÆbæFWf–6W3 ¢6VÆbå÷7våö–ç7Fæ6R†FWf–6RÂ7F'GWöÖöFR¢ÖöFU÷FW‡BÒ.ˆNy¹þ[ŠîXª’"–b7F'GWöÖöFRÓÒ&†VÇ"VÇ6R.ˆNy¹þ{ª.XÈR ¢6VÆbæÆör†b.[{.K‹¢¶ÆVâ‡6VÆbæFWf–6W2—ÒKŠ®ZéîKè¾XˆnXŠ¾Y
þXª‡¶ÖöFU÷FW‡GÞz©~Xú>8"" ¢FVböÆöE÷F6·2‡6VÆb’ÓâF–7E·7G"ÂÆ—7E¶F–7E·7G"Âç•ÕÕÓ ¢G'“ ¢FFÒ§6öâæÆöG2…D4µôd”ÄRç&VE÷FW‡B†Væ6öF–æsÒ'WFbÓ‚"’¢–b—6–ç7Fæ6R†FFÂF–7B“ ¢&WGW&â·7G"†¶W’“¢Æ—7B‡fÇVR’f÷"¶W’ÂfÇVR–âFFæ—FV×2‚’–b—6–ç7Fæ6R‡fÇVRÂÆ—7B—Ð¢W†6WB„õ4W'&÷"Â§6öâä¥4ôäFV6öFTW'&÷"ÂG—TW'&÷"“ ¢70¢&WGW&â¶æÖS¢¶F–7B‡7FW’f÷"7FW–â7FW5Òf÷"æÖRÂ7FW2–âDTdTÅEõD4µ2æ—FV×2‚—Ð ¢FVb÷&Vg&W6…÷F6·2‡6VÆb’ÓâæöæS ¢7W'&VçBÒ6VÆbçF6µö6öÖ&òæ7W'&VçEFW‡B‚’–b†6GG"‡6VÆbÂ'F6µö6öÖ&ò"’VÇ6R" ¢6VÆbçF6µö6öÖ&òæ&Æö6µ6–væÇ2…G'VR¢6VÆbçF6µö6öÖ&òæ6ÆV"‚¢6VÆbçF6µö6öÖ&òæFD—FV×2‡6÷'FVB‡6VÆbçF6·2’¢–b7W'&VçB–â6VÆbçF6·3 ¢6VÆbçF6µö6öÖ&òç6WD7W'&VçEFW‡B†7W'&VçB¢6VÆbçF6µö6öÖ&òæ&Æö6µ6–væÇ2„fÇ6R¢6VÆbåöÆöE÷6VÆV7FVE÷F6²‚ ¢FVböÆöE÷6VÆV7FVE÷F6²‡6VÆb’ÓâæöæS ¢6VÆbæ7F—fU÷7FW2Ò¶F–7B‡7FW’f÷"7FW–â6VÆbçF6·2ævWB‡6VÆbçF6µö6öÖ&òæ7W'&VçEFW‡B‚’ÂµÒ•Ð¢6VÆbå÷&VæFW%÷7FW2‚ ¢FVb÷7FW÷FW‡B‡6VÆbÂ–æFWƒ¢–çBÂ7FW¢F–7E·7G"Âç•Ò’Óâ7G# ¢7F–öâÒ7FWævWB‚&7F–öâ"¢–b7F–öâÓÒ'F# ¢FWF–ÂÒb.x+žX{²‡·7FW²w‚u×ÒÂ·7FW²w’u×Ò’ ¢VÆ–b7F–öâÓÒ'v—B# ¢FWF–ÂÒb.zØž[èR·7FW²w6V6öæG2u×Òzy" ¢VÆ–b7F–öâÓÒ&&6²# ¢FWF–ÂÒ$æG&ö–B‹ùNY¹î™Jâ ¢VÇ6S ¢FWF–ÂÒb.ŠønY»â·7FWævWB‚wFV×ÆFRr—Ò+r‹h^i{b·7FWævWB‚wF–ÖV÷WBrÂR—Òzy" ¢&WGW&âb'¶–æFW‚²£&GÒ¶FWF–ÇÒ  ¢FVb÷&VæFW%÷7FW2‡6VÆb’ÓâæöæS ¢6VÆbç7FWöÆ—7Bæ6ÆV"‚¢6VÆbç7FWöÆ—7BæFD—FV×2…·6VÆbå÷7FW÷FW‡B†’Â7FW’f÷"’Â7FW–âVçVÖW&FR‡6VÆbæ7F—fU÷7FW2•Ò ¢FVböæWu÷F6²‡6VÆb’ÓâæöæS ¢æÖRÂö²Ò–çWDF–ÆörævWEFW‡B‡6VÆbÂôäÔRÂ.ikK»¾XªYÞz{ûÉ¢"¢–bö²æBæÖRç7G&—‚“ ¢6VÆbçF6·5¶æÖRç7G&—‚•ÒÒµÐ¢6VÆbå÷&Vg&W6…÷F6·2‚¢6VÆbçF6µö6öÖ&òç6WD7W'&VçEFW‡B†æÖRç7G&—‚’ ¢FVb÷F6µöFE÷ö–çB‡6VÆb’ÓâæöæS ¢–bæ÷B6VÆbç6VÆV7FVE÷ö–çB÷"æ÷B6VÆbç6VÆV7FVE÷6÷W&6U÷6—¦S ¢ÖW76vT&÷‚æ–æf÷&ÖF–öâ‡6VÆbÂôäÔRÂ.Šû~XXŽYÊŽŠëîZH~KŠÞ[ø>yK¾™Ú.Kˆ®˜žhºžKˆKŠ®YÙj~8""¢&WGW&à¢6VÆbæ7F—fU÷7FW2æVæB‡²&7F–öâ#¢'F"Â'‚#¢6VÆbç6VÆV7FVE÷ö–çE³ÒÂ'’#¢6VÆbç6VÆV7FVE÷ö–çE³ÒÂ'v–GF‚#¢6VÆbç6VÆV7FVE÷6÷W&6U÷6—¦U³ÒÂ&†V–v‡B#¢6VÆbç6VÆV7FVE÷6÷W&6U÷6—¦U³×Ò¢6VÆbå÷&VæFW%÷7FW2‚ ¢FVb÷F6µöFE÷v—B‡6VÆb’ÓâæöæS ¢fÇVRÂö²Ò–çWDF–ÆörævWDF÷V&ÆR‡6VÆbÂôäÔRÂ.zØž[è^zy.i[ûÉ¢"Â"ãÂÂƒcCÂ¢–bö³ ¢6VÆbæ7F—fU÷7FW2æVæB‡²&7F–öâ#¢'v—B"Â'6V6öæG2#¢fÇVWÒ¢6VÆbå÷&VæFW%÷7FW2‚ ¢FVb÷F6µöFEö&6²‡6VÆb’ÓâæöæS ¢6VÆbæ7F—fU÷7FW2æVæB‡²&7F–öâ#¢&&6²'Ò¢6VÆbå÷&VæFW%÷7FW2‚ ¢FVb÷F6µöFE÷FV×ÆFR‡6VÆb’ÓâæöæS ¢æÖW2Ò·6VÆbçFV×ÆFUö6öÖ&òæ—FVÕFW‡B†’’f÷"’–â&ævR‡6VÆbçFV×ÆFUö6öÖ&òæ6÷VçB‚’•Ð¢–bæ÷BæÖW3 ¢&WGW&à¢æÖRÂö²Ò–çWDF–ÆörævWD—FVÒ‡6VÆbÂôäÔRÂ.˜žhºžjŠiÛþûÉ¢"ÂæÖW2ÂÂfÇ6R¢–bö³ ¢F–ÖV÷WBÂ66WFVBÒ–çWDF–ÆörævWDF÷V&ÆR‡6VÆbÂôäÔRÂ.zØž[è^‹h^i{nûÈŽzy.ûÈžûÉ¢"ÂRÂÂƒcCÂ¢–b66WFVC ¢6VÆbæ7F—fU÷7FW2æVæB‡²&7F–öâ#¢'FV×ÆFR"Â'FV×ÆFR#¢æÖRÂ'F–ÖV÷WB#¢F–ÖV÷WBÂ'F‡&W6†öÆB#¢6VÆbçF‡&W6†öÆE÷6Æ–FW"çfÇVR‚’òÒ¢6VÆbå÷&VæFW%÷7FW2‚ ¢FVböFVÆWFU÷F6µ÷7FW‡6VÆb’ÓâæöæS ¢&÷rÒ6VÆbç7FWöÆ—7Bæ7W'&VçE&÷r‚¢–bÃÒ&÷rÂÆVâ‡6VÆbæ7F—fU÷7FW2“ ¢6VÆbæ7F—fU÷7FW2ç÷‡&÷r¢6VÆbå÷&VæFW%÷7FW2‚ ¢FVb÷6fU÷F6²‡6VÆb’ÓâæöæS ¢æÖRÒ6VÆbçF6µö6öÖ&òæ7W'&VçEFW‡B‚’ç7G&—‚¢–bæ÷BæÖS ¢&WGW&à¢6VÆbçF6·5¶æÖUÒÒ¶F–7B‡7FW’f÷"7FW–â6VÆbæ7F—fU÷7FW5Ð¢D4µôd”ÄRçw&—FU÷FW‡B†§6öâæGV×2‡6VÆbçF6·2ÂVç7W&Uö66–“ÔfÇ6RÂ–æFVçCÓ"’ÂVæ6öF–æsÒ'WFbÓ‚"¢6VÆbæÆör†b.[{.KùÞZÙŽK»¾XªûÉ§¶æÖWÒ" ¢FVböFVÆWFU÷F6²‡6VÆb’ÓâæöæS ¢æÖRÒ6VÆbçF6µö6öÖ&òæ7W'&VçEFW‡B‚¢–bæÖRæBÖW76vT&÷‚çVW7F–öâ‡6VÆbÂôäÔRÂb.XŠ™šNK»¾Xª(	Ç¶æÖWÞ(	ÞûÉò"’ÓÒÖW76vT&÷‚å7FæF&D'WGFöâå–W3 ¢6VÆbçF6·2ç÷†æÖRÂæöæR¢D4µôd”ÄRçw&—FU÷FW‡B†§6öâæGV×2‡6VÆbçF6·2ÂVç7W&Uö66–“ÔfÇ6RÂ–æFVçCÓ"’ÂVæ6öF–æsÒ'WFbÓ‚"¢6VÆbå÷&Vg&W6…÷F6·2‚ ¢FVb÷'Vå÷F6²‡6VÆb’ÓâæöæS ¢–bæ÷B6VÆbæF"÷"æ÷B6VÆbæ7F—fU÷7FW3 ¢ÖW76vT&÷‚æ–æf÷&ÖF–öâ‡6VÆbÂôäÔRÂ.Šû~XXŽ‹ùîhê^ZéîKè¾[›nXxnZH~K»¾XªjÚ^šªN8""¢&WGW&à¢F&vWBÒ6VÆbæF"æ6ÆöæUöf÷%öFWf–6R‚¢7FW2Ò¶F–7B‡7FW’f÷"7FW–â6VÆbæ7F—fU÷7FW5Ð¢&WVBÂ&WVE÷v—BÒ6VÆbç&WVEö6†V6²æ—46†V6¶VB‚’Â6VÆbç&WVE÷v—BçfÇVR‚ ¢FVb¦ö"‚’ÓâæöæS ¢&÷VæEöçVÖ&W"Ò ¢6VÆbæÆör‚.[ÈZx¾hš~ŠÎK»¾Xª[¨þX‰~8""¢v†–ÆRæ÷B6VÆbç7F÷öWfVçBæ—5÷6WB‚“ ¢&÷VæEöçVÖ&W"³Ò¢f÷"–æFW‚Â7FW–âVçVÖW&FR‡7FW2“ ¢–b6VÆbç7F÷öWfVçBæ—5÷6WB‚“ ¢'&V°¢7F–öâÒ7FWævWB‚&7F–öâ"¢G'“ ¢–b7F–öâ–â²'F"Â&&6²"Â'FV×ÆFR'ÒæBæ÷BF&vWBæf÷&Vw&÷VæEö—5övÖR‚“ ¢6VÆbæÆör†b.jÚ^šªB¶–æFW‚²Òi¨.XÎûÉ®k‹ŽhˆþKˆÞYÊŽX˜ÞXû8""¢v†–ÆRæ÷B6VÆbç7F÷öWfVçBçv—Bƒ"“ ¢–bF&vWBæf÷&Vw&÷VæEö—5övÖR‚“ ¢'&V°¢–b7F–öâÓÒ'F# ¢ö–çBÒ66ÆU÷&V6÷&FVE÷ö–çB‚†–çB‡7FW²'‚%Ò’Â–çB‡7FW²'’%Ò’’Â†–çB‡7FW²'v–GF‚%Ò’Â–çB‡7FW²&†V–v‡B%Ò’’ÂF&vWBç67&VVå÷6—¦R‚’¢F&vWBçF‚§ö–çB¢6VÆbæÆör†b.jÚ^šªB¶–æFW‚²ÞûÉ®x+žX{²·ö–çGÞ8""¢VÆ–b7F–öâÓÒ'v—B# ¢–b6VÆbç7F÷öWfVçBçv—B†fÆöB‡7FW²'6V6öæG2%Ò’“ ¢'&V°¢VÆ–b7F–öâÓÒ&&6²# ¢F&vWBæ&6²‚¢VÆ–b7F–öâÓÒ'FV×ÆFR# ¢FVFÆ–æRÒF–ÖRæÖöæ÷Föæ–2‚’²fÆöB‡7FWævWB‚'F–ÖV÷WB"ÂR’¢v†–ÆRF–ÖRæÖöæ÷Föæ–2‚’ÂFVFÆ–æRæBæ÷B6VÆbç7F÷öWfVçBæ—5÷6WB‚“ ¢F‚ÒDTÕÄDUôD•"ò7G"‡7FW²'FV×ÆFR%Ò¢ö–çBÂ66÷&RÒÖF6…÷FV×ÆFR‡F&vWBç67&VVç6†÷B‚’ÂF‚ÂfÆöB‡7FWævWB‚'F‡&W6†öÆB"Âãƒ‚’’ÂFV×ÆFU÷&VfW&Væ6U÷6—¦R‡F‚’¢–bö–çC ¢F&vWBçF‚§ö–çB¢6VÆbæÆör†b.jÚ^šªB¶–æFW‚²ÞûÉ®ŠønY»îx+žX{²·ö–çGÞûÈÎy»ŽKËÎ[ªb·66÷&S¢ã6gÞ8""¢'&V°¢6VÆbç7F÷öWfVçBçv—Bƒ¢W†6WBW†6WF–öâ2W†3 ¢6VÆbæÆör†b.jÚ^šªB¶–æFW‚²ÒZK‹J^ûÉ§¶W†7Ò"¢6VÆbç7F÷öWfVçBç6WB‚¢'&V°¢–bæ÷B&WVB÷"6VÆbç7F÷öWfVçBæ—5÷6WB‚“ ¢'&V°¢–b6VÆbç7F÷öWfVçBçv—B‡&WVE÷v—B“ ¢'&V°¢6VÆbæÆör‚.K»¾Xª[¨þX‰~[{.{¹>iÙþ8"" ¢6VÆbå÷7F'E÷v÷&¶W"‡F&vWBæFWf–6RÂ¦ö" ¢FVbö†÷F¶W•öÆö÷‡6VÆb’ÓâæöæS ¢–b÷2ææÖRÒ&çB# ¢&WGW&à¢W6W#3"Ò7G—W2çv–æFÆÂçW6W#3 ¢v†–ÆRæ÷B6VÆbæ6Æ÷6–æræ—5÷6WB‚“ ¢–bW6W#3"ävWD7–æ4¶W•7FFRƒƒsr’b ¢6VÆbç7F÷öWfVçBç6WB‚¢6VÆbæÆör‚.j8kX¾X‹XZŽ[cŽûÈÎjÚ>YÊŽXÎjÚ.8""¢F–ÖRç6ÆVWƒã‚ ¢FVb6Æ÷6TWfVçB‡6VÆbÂWfVçC¢ç’’ÓâæöæS ¢6VÆbæ6Æ÷6–ærç6WB‚¢6VÆbç7F÷öWfVçBç6WB‚¢WfVçBæ66WB‚  ¦FVbÖ–â‚’ÓâæöæS ¢'6W"Ò&w'6Rä&wVÖVçE'6W"†FW67&—F–öãÔôäÔR¢'6W"æFEö&wVÖVçB‚"ÒÖFWf–6R"¢'6W"æFEö&wVÖVçB‚"ÒÖWFòÖ†VÇ"Â7F–öãÒ'7F÷&U÷G'VR"¢'6W"æFEö&wVÖVçB‚"ÒÖÆÂÖWFòÖ†VÇ"Â7F–öãÒ'7F÷&U÷G'VR"¢'6W"æFEö&wVÖVçB‚"ÒÖWFò×&VB×6¶WB"Â7F–öãÒ'7F÷&U÷G'VR"¢'6W"æFEö&wVÖVçB‚"ÒÖÆÂÖWFò×&VB×6¶WB"Â7F–öãÒ'7F÷&U÷G'VR"¢'6W"æFEö&wVÖVçB‚"ÒÖ–çFW'fÂ"ÂG—SÖfÆöBÂ†VÇÒ.ˆz®XªŽZûÎˆŠ®[ŠîXªžy¨Nx+žX{²òŠønXŠ¾™{N™©NûÈŽzy.ûÈ’"¢&w2Ò'6W"ç'6Uö&w2‚¢–b†6GG"…BäÆ–6F–öäGG&–'WFRÂ$ôVæ&ÆT†–v„G•66Æ–ær"“ ¢Æ–6F–öâç6WDGG&–'WFR…BäÆ–6F–öäGG&–'WFRäôVæ&ÆT†–v„G•66Æ–ærÂG'VR¢ÒÆ–6F–öâ‡7—2æ&we³£Ò¢ç6WDÆ–6F–öäæÖR„ôäÔR¢ç6WDÆ–6F–öåfW'6–öâ„õdU%4”ôâ¢ç6WD÷&væ—¦F–öäæÖR‚%t¤E"FööÇ2"¢ç6WE7G–ÆR‚$gW6–öâ"¢v–æF÷rÒÖ–åv–æF÷r€¢&w2æFWf–6RÀ¢&w2æWFõö†VÇÀ¢&w2æÆÅöWFõö†VÇÀ¢&w2æWFõ÷&VE÷6¶WBÀ¢&w2æÆÅöWFõ÷&VE÷6¶WBÀ¢&w2æ–çFW'fÂÀ¢¢v–æF÷rç6†÷r‚¢÷vRÒ÷2æVçf—&öâævWB‚%t¤E%õõtR"¢–b÷vRæB÷vRæ—6F–v—B‚“ ¢v–æF÷rå÷6†÷u÷vR†Ö–â†–çB‡÷vR’Âv–æF÷rç7F6²æ6÷VçB‚’Ò’¢÷67&VVç6†÷BÒ÷2æVçf—&öâævWB‚%t¤E%õõ45$TTå4„õB"¢–b÷67&VVç6†÷C ¢FVb6fU÷÷67&VVç6†÷B‚’ÓâæöæS ¢6fVBÒv–æF÷ræw&"‚’ç6fR‡÷67&VVç6†÷BÂ%är"¢v–æF÷ræÆör†b%T’š¨ÎiKnhŠ®Y»ç²~[{.KùÞZÙ‚r–b6fVBVÇ6R~KùÞZÙŽZK‹JRwÞûÉ§·÷67&VVç6†÷GÒ" ¢F–ÖW"ç6–ævÆU6†÷Bƒ3SÂ6fU÷÷67&VVç6†÷B¢&—6R7—7FVÔW†—B†æW†V2‚’  ¦–bõöæÖUõòÓÒ%õöÖ–åõò# ¢Ö–â‚