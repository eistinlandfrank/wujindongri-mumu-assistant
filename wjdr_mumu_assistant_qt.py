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
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "正在获取 MuMu 画面…")
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
        brand_icon = QLabel("❄")
        brand_icon.setObjectName("brandIcon")
        brand_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        brand_text = QVBoxLayout()
        brand = QLabel("无尽冬日助手")
        brand.setObjectName("brand")
        brand_sub = QLabel(f"DESKTOP  ·  v{APP_VERSION}")
        brand_sub.setObjectName("brandSub")
        brand_text.addWidget(brand)
        brand_text.addWidget(brand_sub)
        brand_row.addWidget(brand_icon)
        brand_row.addLayout(brand_text, 1)
        side.addLayout(brand_row)
        side.addSpacing(25)
        self.nav_buttons: list[QPushButton] = []
        nav_items = [
            ("⌂", "设备中心"),
            ("◉", "联盟帮助"),
            ("✦", "联盟红包"),
            ("☷", "任务编排"),
            ("≡", "运行日志"),
            ("i", "关于与安全"),
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
        safety_title = QLabel("全局急停")
        safety_title.setObjectName("sideCardTitle")
        safety_text = QLabel("按 F8 停止所有助手窗口\n界面停止仅影响当前窗口")
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
        self.page_title = QLabel("设备中心")
        self.page_title.setObjectName("pageTitle")
        self.page_subtitle = QLabel("选择 MuMu 实例，确认画面后开始运行")
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
        scan = QPushButton("↻  扫描")
        scan.setObjectName("ghostButton")
        scan.clicked.connect(lambda: self._run_async(self._connect_job))
        top.addWidget(scan)
        self.status_pill = QLabel("●  正在连接")
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
        kicker = QLabel("联盟帮助页面流程")
        kicker.setObjectName("heroKicker")
        title = QLabel("自动进入联盟互助，识别后点击“全部帮助”")
        title.setObjectName("heroTitle")
        desc = QLabel("主城 → 联盟 → 联盟互助；仅在标题与绿色按钮同时确认时点击，空页原地等待。")
        desc.setObjectName("heroText")
        hero_text.addWidget(kicker)
        hero_text.addWidget(title)
        hero_text.addWidget(desc)
        hero_layout.addLayout(hero_text, 1)
        self.start_button = QPushButton("▶  自动导航并全部帮助")
        self.start_button.setObjectName("primaryButton")
        self.start_button.clicked.connect(self._start_help_preset)
        stop = QPushButton("■  停止")
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
        preview_title = QLabel("实时画面")
        preview_title.setObjectName("cardTitle")
        self.point_label = QLabel("单击选点 · 拖动框选模板")
        self.point_label.setObjectName("muted")
        preview_header.addWidget(preview_title)
        preview_header.addStretch()
        preview_header.addWidget(self.point_label)
        preview_layout.addLayout(preview_header)
        self.screenshot = ScreenshotView()
        self.screenshot.point_selected.connect(self._point_selected)
        self.screenshot.region_selected.connect(self._region_selected)
        preview_layout.addWidget(self.screenshot, 1)
        preview_footer = QHBoxLayout()
        capture = QPushButton("↻  刷新画面")
        capture.setObjectName("softButton")
        capture.clicked.connect(lambda: self._run_async(self._capture_job))
        save_template = QPushButton("＋  保存框选为模板")
        save_template.setObjectName("softButton")
        save_template.clicked.connect(self._save_template)
        preview_footer.addWidget(capture)
        preview_footer.addStretch()
        preview_footer.addWidget(save_template)
        preview_layout.addLayout(preview_footer)
        content.addWidget(preview_card, 3)

        right = QVBoxLayout()
        right.setSpacing(16)
        device_card = Card()
        device_layout = QVBoxLayout(device_card)
        device_layout.setContentsMargins(20, 18, 20, 18)
        device_title = QLabel("当前实例")
        device_title.setObjectName("cardTitle")
        self.instance_name = QLabel("正在扫描 MuMu…")
        self.instance_name.setObjectName("instanceName")
        self.instance_meta = QLabel("ADB —  ·  分辨率 —")
        self.instance_meta.setObjectName("muted")
        self.instance_state = QLabel("连接中")
        self.instance_state.setObjectName("greenPill")
        device_layout.addWidget(device_title)
        device_layout.addSpacing(5)
        device_layout.addWidget(self.instance_name)
        device_layout.addWidget(self.instance_meta)
        device_layout.addWidget(self.instance_state, 0, Qt.AlignmentFlag.AlignLeft)
        action_grid = QGridLayout()
        launch = QPushButton("切回游戏")
        launch.setObjectName("softButton")
        launch.clicked.connect(lambda: self._run_async(self._launch_game_job))
        separate = QPushButton("独立窗口")
        separate.setObjectName("softButton")
        separate.clicked.connect(self._open_selected_window)
        all_instances = QPushButton("全部实例挂机")
        all_instances.setObjectName("secondaryButton")
        all_instances.clicked.connect(self._start_all_instances)
        action_grid.addWidget(launch, 0, 0)
        action_grid.addWidget(separate, 0, 1)
        action_grid.addWidget(all_instances, 1, 0, 1, 2)
        device_layout.addSpacing(10)
        device_layout.addLayout(action_grid)
        right.addWidget(device_card)

        stats = Card()
        stats_layout = QGridLayout(stats)
        stats_layout.setContentsMargins(20, 18, 20, 18)
        stats_title = QLabel("本次运行")
        stats_title.setObjectName("cardTitle")
        stats_layout.addWidget(stats_title, 0, 0, 1, 2)
        self.click_count = QLabel("0")
        self.click_count.setObjectName("statValue")
        self.runtime_label = QLabel("00:00:00")
        self.runtime_label.setObjectName("statValue")
        stats_layout.addWidget(self.click_count, 1, 0)
        stats_layout.addWidget(self.runtime_label, 1, 1)
        label1, label2 = QLabel("累计点击"), QLabel("运行时间")
        label1.setObjectName("muted")
        label2.setObjectName("muted")
        stats_layout.addWidget(label1, 2, 0)
        stats_layout.addWidget(label2, 2, 1)
        right.addWidget(stats)

        note = Card(name="noticeCard")
        note_layout = QVBoxLayout(note)
        note_layout.setContentsMargins(18, 15, 18, 15)
        note_title = QLabel("安全提示")
        note_title.setObjectName("noticeTitle")
        note_text = QLabel("F8 会停止所有助手窗口。建议保持短时、有人观察，不用于战斗或充值操作。")
        note_text.setObjectName("noticeText")
        note_text.setWordWrap(True)
        note_layout.addWidget(note_title)
        note_layout.addWidget(note_text)
        right.addWidget(note)
        right.addStretch()
        content.addLayout(right, 2)
        layout.addLayout(content, 1)

        self.runtime_timer = QTimer(self)
        self.runtime_timer.timeout.connect(self._update_runtime)
        return page

    def _build_automation(self) -> QWidget:
        page = QScrollArea()
        page.setWidgetResizable(True)
        page.setFrameShape(QFrame.Shape.NoFrame)
        body = QWidget()
        body.setObjectName("scrollBody")
        self._set_window_background(page.viewport())
        self._set_window_background(body)
        page.setWidget(body)
        layout = QHBoxLayout(body)
        layout.setContentsMargins(0, 0, 8, 0)
        layout.setSpacing(18)
        recognition = Card()
        form = QVBoxLayout(recognition)
        form.setContentsMargins(24, 22, 24, 24)
        title = QLabel("识图点击")
        title.setObjectName("sectionTitle")
        desc = QLabel("自动流程会识别主城、联盟主页和联盟互助页；仅点击已确认的绿色“全部帮助”。")
        desc.setObjectName("muted")
        desc.setWordWrap(True)
        form.addWidget(title)
        form.addWidget(desc)
        form.addSpacing(16)
        form.addWidget(self._field_label("运行模式"))
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["识图点击（推荐）", "固定坐标连点"])
        form.addWidget(self.mode_combo)
        form.addSpacing(12)
        form.addWidget(self._field_label("按钮模板"))
        row = QHBoxLayout()
        self.template_combo = QComboBox()
        row.addWidget(self.template_combo, 1)
        refresh = QPushButton("刷新")
        refresh.setObjectName("softButton")
        refresh.clicked.connect(self._refresh_templates)
        row.addWidget(refresh)
        form.addLayout(row)
        form.addSpacing(12)
        form.addWidget(self._field_label("相似度阈值"))
        threshold_row = QHBoxLayout()
        self.threshold_slider = QSlider(Qt.Orientation.Horizontal)
        self.threshold_slider.setRange(70, 99)
        self.threshold_slider.setValue(88)
        self.threshold_value = QLabel("0.88")
        self.threshold_value.setObjectName("valuePill")
        self.threshold_slider.valueChanged.connect(lambda value: self.threshold_value.setText(f"{value / 100:.2f}"))
        threshold_row.addWidget(self.threshold_slider, 1)
        threshold_row.addWidget(self.threshold_value)
        form.addLayout(threshold_row)
        form.addSpacing(12)
        fixed = QLabel("固定坐标（可选）")
        fixed.setObjectName("fieldLabel")
        form.addWidget(fixed)
        self.fixed_label = QLabel("在设备中心的画面上单击一个位置")
        self.fixed_label.setObjectName("inputLike")
        form.addWidget(self.fixed_label)
        form.addStretch()
        layout.addWidget(recognition, 1)

        limits = Card()
        limit_layout = QVBoxLayout(limits)
        limit_layout.setContentsMargins(24, 22, 24, 24)
        limit_title = QLabel("运行设置")
        limit_title.setObjectName("sectionTitle")
        limit_layout.addWidget(limit_title)
        limit_layout.addSpacing(14)
        self.interval_spin = QDoubleSpinBox()
        self.interval_spin.setRange(0.5, 3600)
        self.interval_spin.setValue(3.0)
        self.interval_spin.setSuffix(" 秒")
        self.duration_spin = QSpinBox()
        self.duration_spin.setRange(0, 100000)
        self.duration_spin.setValue(60)
        self.duration_spin.setSuffix(" 分钟")
        self.max_clicks_spin = QSpinBox()
        self.max_clicks_spin.setRange(0, 1000000)
        self.max_clicks_spin.setValue(500)
        self.guard_check = QCheckBox("仅当《无尽冬日》位于模拟器前台时点击")
        self.guard_check.setChecked(True)
        for label, widget in (
            ("循环 / 点击间隔", self.interval_spin),
            ("运行时长（0 = 不限）", self.duration_spin),
            ("最多点击次数（0 = 不限）", self.max_clicks_spin),
        ):
            limit_layout.addWidget(self._field_label(label))
            limit_layout.addWidget(widget)
            limit_layout.addSpacing(10)
        limit_layout.addWidget(self.guard_check)
        limit_layout.addStretch()
        start_custom = QPushButton("开始识图运行")
        start_custom.setObjectName("primaryButton")
        start_custom.clicked.connect(self._start_custom_clicker)
        limit_layout.addWidget(start_custom)
        layout.addWidget(limits, 1)
        return page

    def _build_red_packet_page(self) -> QWidget:
        """Build the independent, guarded furnace-upgrade red-packet workflow."""
        page = QScrollArea()
        page.setWidgetResizable(True)
        page.setFrameShape(QFrame.Shape.NoFrame)
        body = QWidget()
        body.setObjectName("scrollBody")
        self._set_window_background(page.viewport())
        self._set_window_background(body)
        page.setWidget(body)
        layout = QVBoxLayout(body)
        layout.setContentsMargins(0, 0, 8, 0)
        layout.setSpacing(18)

        hero = Card(name="redPacketHero")
        hero_layout = QHBoxLayout(hero)
        hero_layout.setContentsMargins(28, 24, 26, 24)
        hero_text = QVBoxLayout()
        kicker = QLabel("联盟频道 · 熔炉升级红包")
        kicker.setObjectName("redPacketKicker")
        title = QLabel("发现红包浮标后，自动确认并开启目标红包")
        title.setObjectName("redPacketTitle")
        desc = QLabel("浮标仅用于唤醒检查。程序会依次确认聊天、联盟频道、熔炉升级红包和“开启”按钮；任一步不成立都不输入。")
        desc.setObjectName("redPacketText")
        desc.setWordWrap(True)
        hero_text.addWidget(kicker)
        hero_text.addWidget(title)
        hero_text.addWidget(desc)
        hero_layout.addLayout(hero_text, 1)
        actions = QVBoxLayout()
        self.red_packet_start_button = QPushButton("✦  开始自动抢红包")
        self.red_packet_start_button.setObjectName("redPacketPrimaryButton")
        self.red_packet_start_button.clicked.connect(self._start_red_packet_flow)
        stop = QPushButton("■  停止")
        stop.setObjectName("redPacketStopButton")
        stop.clicked.connect(self.stop_all)
        actions.addWidget(self.red_packet_start_button)
        actions.addWidget(stop)
        hero_layout.addLayout(actions)
        layout.addWidget(hero)

        status_card = Card(name="redPacketStatusCard")
        status_layout = QHBoxLayout(status_card)
        status_layout.setContentsMargins(22, 17, 22, 17)
        state_text = QVBoxLayout()
        state_title = QLabel("红包监听状态")
        state_title.setObjectName("cardTitle")
        self.red_packet_state_label = QLabel("待命：等待右下角红包浮标")
        self.red_packet_state_label.setObjectName("redPacketState")
        state_hint = QLabel("领取成功后会先确认结果页，再安全关闭并回到主城继续监听。")
        state_hint.setObjectName("muted")
        state_text.addWidget(state_title)
        state_text.addWidget(self.red_packet_state_label)
        state_text.addWidget(state_hint)
        status_layout.addLayout(state_text, 1)
        all_instances = QPushButton("全部实例抢红包")
        all_instances.setObjectName("redPacketSecondaryButton")
        all_instances.clicked.connect(lambda: self._start_all_instances("red_packet"))
        status_layout.addWidget(all_instances)
        layout.addWidget(status_card)

        content = QHBoxLayout()
        content.setSpacing(18)
        safety = Card()
        safety_layout = QVBoxLayout(safety)
        safety_layout.setContentsMargins(24, 22, 24, 24)
        safety_title = QLabel("确认链路")
        safety_title.setObjectName("sectionTitle")
        safety_desc = QLabel(
            "① 连续两帧检测红包浮标\n"
            "② 确认聊天页，再确认“联盟”已选中\n"
            "③ 识别“熔炉升级红包”卡片\n"
            "④ 标题与“开启”按钮同屏且几何关系正确\n"
            "⑤ 识别奖励结果页后才关闭，随后重新监听"
        )
        safety_desc.setObjectName("redPacketRules")
        safety_desc.setWordWrap(True)
        safety_note = QLabel("不会滚动聊天记录；未看到目标卡、已领完、页面未知或游戏不在前台时，均不点击。")
        safety_note.setObjectName("noticeText")
        safety_note.setWordWrap(True)
        safety_layout.addWidget(safety_title)
        safety_layout.addSpacing(12)
        safety_layout.addWidget(safety_desc)
        safety_layout.addSpacing(14)
        safety_layout.addWidget(safety_note)
        safety_layout.addStretch()
        content.addWidget(safety, 3)

        limits = Card()
        limit_layout = QVBoxLayout(limits)
        limit_layout.setContentsMargins(24, 22, 24, 24)
        limit_title = QLabel("红包运行设置")
        limit_title.setObjectName("sectionTitle")
        limit_layout.addWidget(limit_title)
        limit_layout.addSpacing(14)
        self.red_packet_interval_spin = QDoubleSpinBox()
        self.red_packet_interval_spin.setRange(0.8, 3600)
        self.red_packet_interval_spin.setValue(2.0)
        self.red_packet_interval_spin.setSuffix(" 秒 / 检查")
        self.red_packet_duration_spin = QSpinBox()
        self.red_packet_duration_spin.setRange(0, 100000)
        self.red_packet_duration_spin.setValue(120)
        self.red_packet_duration_spin.setSuffix(" 分钟")
        self.red_packet_max_claims_spin = QSpinBox()
        self.red_packet_max_claims_spin.setRange(0, 1000000)
        self.red_packet_max_claims_spin.setValue(100)
        self.red_packet_guard_check = QCheckBox("仅当《无尽冬日》位于模拟器前台时点击")
        self.red_packet_guard_check.setChecked(True)
        for label, widget in (
            ("截图 / 检查间隔", self.red_packet_interval_spin),
            ("运行时长（0 = 不限）", self.red_packet_duration_spin),
            ("最多领取次数（0 = 不限）", self.red_packet_max_claims_spin),
        ):
            limit_layout.addWidget(self._field_label(label))
            limit_layout.addWidget(widget)
            limit_layout.addSpacing(10)
        limit_layout.addWidget(self.red_packet_guard_check)
        limit_layout.addStretch()
        content.addWidget(limits, 2)
        layout.addLayout(content)
        layout.addStretch()
        return page

    def _build_tasks_page(self) -> QWidget:
        page = QWidget()
        layout = QHBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(18)
        editor = Card()
        edit = QVBoxLayout(editor)
        edit.setContentsMargins(22, 20, 22, 22)
        title = QLabel("任务步骤")
        title.setObjectName("sectionTitle")
        self.task_combo = QComboBox()
        self.task_combo.currentIndexChanged.connect(self._load_selected_task)
        self.step_list = QListWidget()
        row = QHBoxLayout()
        for text, callback in (
            ("＋ 选点", self._task_add_point),
            ("＋ 等待", self._task_add_wait),
            ("＋ 返回", self._task_add_back),
            ("＋ 识图", self._task_add_template),
        ):
            button = QPushButton(text)
            button.setObjectName("softButton")
            button.clicked.connect(callback)
            row.addWidget(button)
        edit.addWidget(title)
        edit.addWidget(self.task_combo)
        edit.addWidget(self.step_list, 1)
        edit.addLayout(row)
        layout.addWidget(editor, 3)
        actions = Card()
        action_layout = QVBoxLayout(actions)
        action_layout.setContentsMargins(22, 20, 22, 22)
        action_title = QLabel("任务操作")
        action_title.setObjectName("sectionTitle")
        action_layout.addWidget(action_title)
        for text, object_name, callback in (
            ("新建任务", "softButton", self._new_task),
            ("删除选中步骤", "softButton", self._delete_task_step),
            ("保存任务", "secondaryButton", self._save_task),
            ("删除任务", "dangerButton", self._delete_task),
        ):
            button = QPushButton(text)
            button.setObjectName(object_name)
            button.clicked.connect(callback)
            action_layout.addWidget(button)
        action_layout.addSpacing(12)
        self.repeat_check = QCheckBox("循环执行")
        self.repeat_wait = QSpinBox()
        self.repeat_wait.setRange(0, 86400)
        self.repeat_wait.setValue(30)
        self.repeat_wait.setSuffix(" 秒 / 轮")
        action_layout.addWidget(self.repeat_check)
        action_layout.addWidget(self.repeat_wait)
        action_layout.addStretch()
        run = QPushButton("▶  运行当前任务")
        run.setObjectName("primaryButton")
        run.clicked.connect(self._run_task)
        action_layout.addWidget(run)
        layout.addWidget(actions, 1)
        return page

    def _build_log_page(self) -> QWidget:
        page = Card()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(22, 20, 22, 22)
        header = QHBoxLayout()
        title = QLabel("运行日志")
        title.setObjectName("sectionTitle")
        open_folder = QPushButton("打开日志目录")
        open_folder.setObjectName("softButton")
        open_folder.clicked.connect(lambda: os.startfile(CONFIG_DIR))
        clear = QPushButton("清空显示")
        clear.setObjectName("softButton")
        clear.clicked.connect(lambda: self.log_edit.clear())
        header.addWidget(title)
        header.addStretch()
        header.addWidget(open_folder)
        header.addWidget(clear)
        layout.addLayout(header)
        self.log_edit = QTextEdit()
        self.log_edit.setObjectName("logEdit")
        self.log_edit.setReadOnly(True)
        layout.addWidget(self.log_edit, 1)
        return page

    def _build_about_page(self) -> QWidget:
        page = QScrollArea()
        page.setWidgetResizable(True)
        page.setFrameShape(QFrame.Shape.NoFrame)
        body = QWidget()
        body.setObjectName("scrollBody")
        self._set_window_background(page.viewport())
        self._set_window_background(body)
        page.setWidget(body)
        layout = QVBoxLayout(body)
        layout.setContentsMargins(0, 0, 8, 0)
        about = Card()
        about_layout = QVBoxLayout(about)
        about_layout.setContentsMargins(28, 26, 28, 28)
        title = QLabel(f"{APP_NAME}  {APP_VERSION}")
        title.setObjectName("heroTitle")
        text = QLabel(
            "这是一个只通过 MuMu 自带 ADB 截图、识图和模拟点击工作的本地工具。\n\n"
            "• 不读取游戏内存，不修改 APK，不读取账号密码。\n"
            "• 每个窗口绑定一个独立 ADB 端口，同一实例带跨进程占用锁。\n"
            "• 内置模板支持 720×1280 至 1600×2560 的已测分辨率范围。\n"
            "• F8 是全局急停；普通停止按钮只停止当前窗口。\n\n"
            "游戏服务条款可能禁止 auto / macro / bot。无人值守自动化可能导致账号处罚，"
            "请保持短时、有人观察，不要用于战斗、抢占、充值或批量账号。"
        )
        text.setObjectName("aboutText")
        text.setWordWrap(True)
        about_layout.addWidget(title)
        about_layout.addSpacing(10)
        about_layout.addWidget(text)
        layout.addWidget(about)
        layout.addStretch()
        return page

    @staticmethod
    def _field_label(text: str) -> QLabel:
        label = QLabel(text)
        label.setObjectName("fieldLabel")
        return label

    @staticmethod
    def _set_window_background(widget: QWidget) -> None:
        palette = widget.palette()
        palette.setColor(QPalette.ColorRole.Window, QColor(COLORS["window"]))
        widget.setPalette(palette)
        widget.setAutoFillBackground(True)

    def _apply_style(self) -> None:
        self.setStyleSheet(
            f"""
            * {{ font-family: 'Microsoft YaHei UI'; font-size: 14px; color: {COLORS['text']}; }}
            QMainWindow, QWidget#root, QWidget#main {{ background: {COLORS['window']}; }}
            QFrame#sidebar {{ background: {COLORS['navy']}; }}
            QLabel#brandIcon {{ background: #2E6FE6; color: white; border-radius: 13px; min-width: 42px; min-height: 42px; font-size: 24px; font-weight: 700; }}
            QLabel#brand {{ color: white; font-size: 17px; font-weight: 700; }}
            QLabel#brandSub {{ color: #8294B3; font-size: 10px; font-weight: 600; letter-spacing: 1px; }}
            QPushButton#navButton {{ text-align: left; color: #93A4C0; background: transparent; border: none; border-radius: 9px; padding: 12px 14px; font-weight: 600; }}
            QPushButton#navButton:hover {{ color: white; background: #172947; }}
            QPushButton#navButton:checked {{ color: white; background: #245FD0; }}
            QFrame#sidebarCard {{ background: #172947; border: 1px solid #233A60; border-radius: 12px; }}
            QLabel#sideCardTitle {{ color: #DCE8FB; font-weight: 700; }}
            QLabel#sideCardText {{ color: #8294B3; font-size: 11px; line-height: 1.4; }}
            QLabel#pageTitle {{ font-size: 26px; font-weight: 750; }}
            QLabel#pageSubtitle, QLabel#muted {{ color: {COLORS['muted']}; font-size: 12px; }}
            QLabel#statusPill {{ background: {COLORS['green_soft']}; color: #11865B; border-radius: 15px; padding: 8px 12px; font-weight: 700; }}
            QFrame#card, QFrame#noticeCard {{ background: white; border: 1px solid {COLORS['border']}; border-radius: 14px; }}
            QFrame#hero {{ background: qlineargradient(x1:0,y1:0,x2:1,y2:1, stop:0 #183A73, stop:1 #2358B3); border-radius: 16px; }}
            QLabel#heroKicker {{ color: #91B6FF; font-size: 12px; font-weight: 700; letter-spacing: 1px; }}
            QLabel#heroTitle {{ color: white; font-size: 23px; font-weight: 750; }}
            QLabel#heroText {{ color: #C2D3EF; font-size: 12px; }}
            QFrame#redPacketHero {{ background: qlineargradient(x1:0,y1:0,x2:1,y2:1, stop:0 #8C2631, stop:.56 #C94734, stop:1 #E88338); border-radius: 16px; }}
            QLabel#redPacketKicker {{ color: #FFE3A4; font-size: 12px; font-weight: 700; letter-spacing: 1px; }}
            QLabel#redPacketTitle {{ color: white; font-size: 23px; font-weight: 750; }}
            QLabel#redPacketText {{ color: #FFF0D3; font-size: 12px; }}
            QFrame#redPacketStatusCard {{ background: #FFF8F0; border: 1px solid #F1D4B1; border-radius: 14px; }}
            QLabel#redPacketState {{ color: #B45624; font-size: 15px; font-weight: 750; }}
            QLabel#redPacketRules {{ color: #52627A; font-size: 14px; line-height: 1.8; }}
            QLabel#cardTitle, QLabel#sectionTitle {{ font-size: 17px; font-weight: 750; }}
            QLabel#instanceName {{ font-size: 19px; font-weight: 750; }}
            QLabel#greenPill {{ background: {COLORS['green_soft']}; color: #11865B; border-radius: 12px; padding: 5px 9px; font-size: 11px; font-weight: 700; }}
            QLabel#statValue {{ color: {COLORS['blue']}; font-size: 25px; font-weight: 800; }}
            QLabel#noticeTitle {{ color: #945A0C; font-weight: 750; }}
            QLabel#noticeText {{ color: #8B6A39; font-size: 11px; }}
            QLabel#fieldLabel {{ font-weight: 700; margin-top: 2px; }}
            QLabel#inputLike {{ background: {COLORS['surface_alt']}; border: 1px solid {COLORS['border']}; border-radius: 8px; padding: 11px; color: {COLORS['muted']}; }}
            QLabel#valuePill {{ background: #EAF1FF; color: #255EC5; border-radius: 10px; padding: 5px 9px; font-weight: 700; }}
            QLabel#aboutText {{ color: #52627A; font-size: 14px; line-height: 1.6; }}
            QPushButton {{ min-height: 38px; border-radius: 9px; padding: 0 16px; font-weight: 650; }}
            QPushButton#primaryButton {{ background: {COLORS['blue']}; color: white; border: none; min-height: 44px; }}
            QPushButton#primaryButton:hover {{ background: {COLORS['blue_dark']}; }}
            QPushButton#redPacketPrimaryButton {{ background: #FFF5DF; color: #A63B20; border: none; min-height: 44px; }}
            QPushButton#redPacketPrimaryButton:hover {{ background: #FFFFFF; color: #8E2D1B; }}
            QPushButton#redPacketSecondaryButton {{ background: #FFF0DE; color: #AF5427; border: 1px solid #F0C594; }}
            QPushButton#redPacketSecondaryButton:hover {{ background: #FFE6C7; }}
            QPushButton#redPacketStopButton {{ background: rgba(77, 17, 21, .32); color: white; border: 1px solid rgba(255,255,255,.34); }}
            QPushButton#redPacketStopButton:hover {{ background: rgba(77, 17, 21, .48); }}
            QPushButton#secondaryButton {{ background: #E9F0FE; color: #275FBF; border: 1px solid #CDDCF8; }}
            QPushButton#softButton, QPushButton#ghostButton {{ background: white; color: #3D4C63; border: 1px solid {COLORS['border']}; }}
            QPushButton#softButton:hover, QPushButton#ghostButton:hover {{ border-color: #AFC3E3; background: #F8FAFE; }}
            QPushButton#dangerButton {{ background: {COLORS['red']}; color: white; border: none; }}
            QComboBox, QSpinBox, QDoubleSpinBox {{ background: white; border: 1px solid {COLORS['border']}; border-radius: 9px; padding: 8px 11px; min-height: 24px; }}
            QComboBox:hover, QSpinBox:hover, QDoubleSpinBox:hover {{ border-color: #AFC3E3; }}
            QComboBox QAbstractItemView {{ background: white; border: 1px solid {COLORS['border']}; selection-background-color: #E9F0FE; selection-color: {COLORS['text']}; padding: 6px; }}
            QCheckBox {{ spacing: 8px; }}
            QListWidget {{ background: {COLORS['surface_alt']}; border: 1px solid {COLORS['border']}; border-radius: 10px; padding: 6px; }}
            QListWidget::item {{ padding: 10px; border-radius: 7px; }}
            QListWidget::item:selected {{ background: #E4EDFE; color: #255EC5; }}
            QTextEdit#logEdit {{ background: #0D1627; color: #D7E3F6; border: none; border-radius: 11px; padding: 12px; font-family: 'Cascadia Mono'; font-size: 12px; }}
            QScrollArea {{ background: transparent; border: none; }}
            QScrollBar:vertical {{ width: 10px; background: transparent; margin: 4px 0; }}
            QScrollBar::handle:vertical {{ background: #CAD4E4; border-radius: 5px; min-height: 30px; }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
            QSlider::groove:horizontal {{ height: 5px; background: #DDE5F2; border-radius: 2px; }}
            QSlider::sub-page:horizontal {{ background: {COLORS['blue']}; border-radius: 2px; }}
            QSlider::handle:horizontal {{ background: white; border: 2px solid {COLORS['blue']}; width: 16px; margin: -6px 0; border-radius: 8px; }}
            """
        )

    def _show_page(self, index: int) -> None:
        titles = [
            ("设备中心", "选择实例、确认画面并快速启动"),
            ("联盟帮助", "识图阈值与运行限制"),
            ("联盟红包", "只开启已确认的熔炉升级红包"),
            ("任务编排", "组合点击、等待、返回和识图步骤"),
            ("运行日志", "每条记录都标注绑定的 ADB 端口"),
            ("关于与安全", "版本、兼容范围与账号风险"),
        ]
        self.stack.setCurrentIndex(index)
        self.page_title.setText(titles[index][0])
        self.page_subtitle.setText(titles[index][1])
        for number, button in enumerate(self.nav_buttons):
            button.setChecked(number == index)

    def _run_async(self, callback: Callable[[], None]) -> None:
        threading.Thread(target=callback, daemon=True).start()

    def log(self, message: str) -> None:
        device = self.adb.device if self.adb and self.adb.device else "未绑定"
        self._log_for_device(device, message)

    def _log_for_device(self, device: str, message: str) -> None:
        stamp = time.strftime("%H:%M:%S")
        self.signals.log.emit(f"[{stamp}] [{device}] {message}")

    @staticmethod
    def _page_label(page: AlliancePage) -> str:
        return {
            AlliancePage.ALL_HELP_READY: "联盟互助 · 可全部帮助",
            AlliancePage.MUTUAL_HELP: "联盟互助 · 空页",
            AlliancePage.ALLIANCE_HOME: "联盟主页",
            AlliancePage.CITY: "主城 / 世界地图",
            AlliancePage.UNKNOWN: "未知页面",
        }[page]

    @staticmethod
    def _red_packet_page_label(state: RedPacketState) -> str:
        return {
            RedPacketState.MARKER: "红包浮标",
            RedPacketState.CHAT_ENTRY: "主城聊天入口",
            RedPacketState.CHAT_PANEL: "聊天面板",
            RedPacketState.ALLIANCE_CHAT: "联盟频道",
            RedPacketState.FURNACE_PACKET: "熔炉升级红包卡",
            RedPacketState.FURNACE_DETAIL: "熔炉红包详情",
            RedPacketState.DETAIL_OPEN_READY: "熔炉红包可开启",
            RedPacketState.CLAIM_RESULT_READY: "红包领取结果",
            RedPacketState.UNKNOWN: "未知页面",
        }[state]

    def _append_log(self, line: str) -> None:
        self.log_edit.append(line)
        try:
            with LOG_FILE.open("a", encoding="utf-8") as handle:
                handle.write(line + "\n")
        except OSError:
            pass

    def _load_log_tail(self) -> None:
        try:
            lines = LOG_FILE.read_text(encoding="utf-8").splitlines()[-100:]
            self.log_edit.setPlainText("\n".join(lines))
        except OSError:
            pass

    def _set_status(self, text: str, kind: str) -> None:
        self.status_pill.setText(text)
        colors = {
            "ready": ("#E7F8F1", "#11865B"),
            "busy": ("#EAF1FF", "#275FBF"),
            "error": ("#FDECEE", "#B63B4A"),
            "idle": ("#F1F4F8", "#65738A"),
        }
        bg, fg = colors.get(kind, colors["idle"])
        self.status_pill.setStyleSheet(f"background:{bg};color:{fg};border-radius:15px;padding:8px 12px;font-weight:700;")

    def _set_running(self, running: bool, text: str) -> None:
        self.start_button.setEnabled(not running)
        self.red_packet_start_button.setEnabled(not running)
        self.signals.status.emit(f"●  {text}", "busy" if running else "ready")
        if running:
            self.started_at = time.monotonic()
            self.runtime_timer.start(1000)
        else:
            self.runtime_timer.stop()

    def _show_alert(self, title: str, message: str) -> None:
        QMessageBox.warning(self, title, message)

    def _connect_job(self) -> None:
        try:
            self.signals.status.emit("●  正在扫描", "busy")
            adb = MuMuADB()
            preferred = self.adb.device if self.adb and self.adb.device else self.preferred_device
            devices = adb.connect(preferred)
            summaries = [adb.device_summary(device) for device in devices]
            self.adb = adb
            self.signals.devices.emit(summaries, adb.device)
            self.log(f"MuMu 连接成功，共发现 {len(devices)} 个运行中实例。")
            self._capture_job()
        except Exception as exc:
            self.signals.status.emit("●  连接失败", "error")
            self.log(str(exc))
            self.signals.alert.emit(APP_NAME, str(exc))

    def _apply_devices(self, summaries: list[dict[str, Any]], selected: str) -> None:
        self.devices = [item["device"] for item in summaries]
        self.device_combo.blockSignals(True)
        self.device_combo.clear()
        selected_index = 0
        for index, item in enumerate(summaries):
            label = f"#{item['index']}  {item['name']}   ·   {item['device']}"
            self.device_combo.addItem(label, item)
            if item["device"] == selected:
                selected_index = index
        self.device_combo.setCurrentIndex(selected_index)
        self.device_combo.blockSignals(False)
        self._show_device_info(self.device_combo.currentData())
        self.signals.status.emit("●  已就绪", "ready")
        if self.all_auto_red_packet_requested:
            self.all_auto_red_packet_requested = False
            QTimer.singleShot(250, lambda: self._start_all_instances("red_packet"))
        elif self.all_auto_help_requested:
            self.all_auto_help_requested = False
            QTimer.singleShot(250, self._start_all_instances)
        elif self.auto_red_packet_requested:
            self.auto_red_packet_requested = False
            QTimer.singleShot(250, self._start_red_packet_flow)
        elif self.auto_help_requested:
            self.auto_help_requested = False
            QTimer.singleShot(250, self._start_help_preset)

    def _show_device_info(self, item: dict[str, Any] | None) -> None:
        if not item:
            return
        self.instance_name.setText(f"#{item['index']}  {item['name']}")
        self.instance_meta.setText(f"ADB {item['device']}   ·   {item['resolution']}")
        self.instance_state.setText(item["state"])

    def _device_changed(self, index: int) -> None:
        if index < 0 or not self.adb:
            return
        if self.worker and self.worker.is_alive():
            current = next((i for i in range(self.device_combo.count()) if self.device_combo.itemData(i)["device"] == self.adb.device), 0)
            self.device_combo.blockSignals(True)
            self.device_combo.setCurrentIndex(current)
            self.device_combo.blockSignals(False)
            QMessageBox.information(self, APP_NAME, "当前任务正在运行。请用“独立窗口”控制另一实例。")
            return
        item = self.device_combo.itemData(index)
        self.adb.set_device(item["device"])
        self.preferred_device = item["device"]
        self._show_device_info(item)
        self.log(f"当前窗口已绑定 {item['device']}。")
        self._run_async(self._capture_job)

    def _capture_job(self) -> None:
        try:
            if not self.adb:
                return
            image = self.adb.screenshot()
            self.current_image = image
            self.signals.image.emit(image)
        except Exception as exc:
            self.log(f"截图失败：{exc}")

    def _apply_image(self, image: Image.Image) -> None:
        self.screenshot.set_pil_image(image)

    def _launch_game_job(self) -> None:
        try:
            if not self.adb:
                raise RuntimeError("尚未连接 MuMu。")
            self.adb.launch_game()
            self.log("已启动或切回《无尽冬日》。")
            time.sleep(1.2)
            self._capture_job()
        except Exception as exc:
            self.log(str(exc))

    def _point_selected(self, x: int, y: int) -> None:
        if not self.current_image:
            return
        self.selected_point = (x, y)
        self.selected_source_size = self.current_image.size
        self.selected_region = None
        self.point_label.setText(f"已选坐标  {x}, {y}")
        self.fixed_label.setText(f"当前坐标：({x}, {y})  ·  {self.current_image.width}×{self.current_image.height}")

    def _region_selected(self, region: tuple[int, int, int, int]) -> None:
        if not self.current_image:
            return
        self.selected_region = region
        self.selected_point = ((region[0] + region[2]) // 2, (region[1] + region[3]) // 2)
        self.selected_source_size = self.current_image.size
        self.point_label.setText(f"已框选  {region[2] - region[0]}×{region[3] - region[1]}")

    def _save_template(self) -> None:
        if not self.current_image or not self.selected_region:
            QMessageBox.information(self, APP_NAME, "请先在实时画面上拖动框选一个按钮。")
            return
        name, ok = QInputDialog.getText(self, APP_NAME, "模板名称：")
        if not ok or not name.strip():
            return
        path = TEMPLATE_DIR / f"{clean_name(name)}.png"
        self.current_image.crop(self.selected_region).save(path, "PNG")
        path.with_suffix(".json").write_text(
            json.dumps({"screen_width": self.current_image.width, "screen_height": self.current_image.height}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        self._refresh_templates()
        self.template_combo.setCurrentText(path.name)
        self.log(f"已保存模板：{path.name}")

    def _refresh_templates(self) -> None:
        names = sorted(path.name for path in TEMPLATE_DIR.glob("*.png"))
        current = self.template_combo.currentText() if hasattr(self, "template_combo") else ""
        if hasattr(self, "template_combo"):
            self.template_combo.clear()
            self.template_combo.addItems(names)
            if current in names:
                self.template_combo.setCurrentText(current)
            elif BUILTIN_ALL_HELP_TEMPLATE_NAME in names:
                self.template_combo.setCurrentText(BUILTIN_ALL_HELP_TEMPLATE_NAME)
            elif BUILTIN_HELP_TEMPLATE_NAME in names:
                self.template_combo.setCurrentText(BUILTIN_HELP_TEMPLATE_NAME)

    def _start_help_preset(self) -> None:
        self.mode_combo.setCurrentIndex(0)
        self.template_combo.setCurrentText(BUILTIN_ALL_HELP_TEMPLATE_NAME)
        self.threshold_slider.setValue(max(88, self.threshold_slider.value()))
        self.guard_check.setChecked(True)
        self._start_alliance_help_flow()

    def _start_alliance_help_flow(self) -> None:
        """Start the guarded page-flow used by the one-click alliance preset."""
        if not self.adb:
            QMessageBox.warning(self, APP_NAME, "尚未连接 MuMu。")
            return
        required = [
            TEMPLATE_DIR / BUILTIN_ALL_HELP_TEMPLATE_NAME,
            resource_path(BUILTIN_MUTUAL_PAGE_TEMPLATE_ASSET),
            resource_path(BUILTIN_MUTUAL_ENTRY_TEMPLATE_ASSET),
            resource_path(BUILTIN_CITY_ALLIANCE_TEMPLATE_ASSET),
        ]
        if any(not path.is_file() for path in required):
            QMessageBox.warning(self, APP_NAME, "自动导航模板缺失，请重新解压或重新下载完整程序包。")
            return
        target = self.adb.clone_for_device()
        interval = self.interval_spin.value()
        duration = self.duration_spin.value()
        max_clicks = self.max_clicks_spin.value()
        threshold = max(0.88, self.threshold_slider.value() / 100)
        guard = self.guard_check.isChecked()

        def job() -> None:
            clicks, failures = 0, 0
            started = time.monotonic()
            last_tap_at = float("-inf")
            cached_point: tuple[int, int] | None = None
            cached_size: tuple[int, int] | None = None
            last_page: AlliancePage | None = None
            last_notice_key = ""
            last_notice_at = -30.0
            navigation_page: AlliancePage | None = None
            navigation_attempts = 0
            next_navigation_at = 0.0

            def notice(key: str, message: str, minimum_gap: float = 30.0) -> None:
                nonlocal last_notice_key, last_notice_at
                now = time.monotonic()
                if key != last_notice_key or now - last_notice_at >= minimum_gap:
                    self._log_for_device(target.device, message)
                    last_notice_key, last_notice_at = key, now

            self._log_for_device(
                target.device,
                f"开始自动导航 + 全部帮助：点击间隔 {interval:.1f} 秒；F8 可全局停止。",
            )
            while not self.stop_event.is_set():
                now = time.monotonic()
                if duration and now - started >= duration * 60:
                    self._log_for_device(target.device, "已达到运行时长。")
                    break
                if max_clicks and clicks >= max_clicks:
                    self._log_for_device(target.device, "已达到最多点击次数。")
                    break
                try:
                    if guard and not target.foreground_is_game():
                        cached_point = cached_size = None
                        notice("not-foreground", "游戏不在前台，本轮暂停。")
                    else:
                        image = target.screenshot()
                        page = detect_alliance_page(image, threshold)
                        if page.page != last_page:
                            self._log_for_device(target.device, f"页面识别：{self._page_label(page.page)}（分数 {page.score:.3f}）。")
                            last_page = page.page
                            navigation_page = None
                            navigation_attempts = 0
                        if page.page is AlliancePage.ALL_HELP_READY:
                            assert page.point is not None
                            if (
                                cached_point is None
                                or cached_size != image.size
                                or abs(cached_point[0] - page.point[0]) > 18
                                or abs(cached_point[1] - page.point[1]) > 18
                            ):
                                cached_point, cached_size = page.point, image.size
                                self._log_for_device(target.device, f"已记录全部帮助坐标 {cached_point}，分数 {page.score:.3f}。")
                            # The current screenshot has re-verified both the page title and
                            # the green button. Never tap a stale cache after either disappears.
                            if now - last_tap_at >= interval:
                                target.tap(*cached_point)
                                last_tap_at = time.monotonic()
                                clicks += 1
                                self.signals.clicks.emit(clicks)
                                if clicks == 1 or clicks % 20 == 0:
                                    self._log_for_device(target.device, f"已点击全部帮助 {cached_point}，累计 {clicks} 次。")
                        elif page.page is AlliancePage.MUTUAL_HELP:
                            cached_point = cached_size = None
                            notice("mutual-empty", "已在联盟互助页；当前没有“全部帮助”，原地等待。")
                        elif page.page in (AlliancePage.ALLIANCE_HOME, AlliancePage.CITY):
                            cached_point = cached_size = None
                            assert page.point is not None
                            if navigation_page is not page.page:
                                navigation_page, navigation_attempts, next_navigation_at = page.page, 0, 0.0
                            if now >= next_navigation_at:
                                if navigation_attempts < 3:
                                    destination = "联盟互助" if page.page is AlliancePage.ALLIANCE_HOME else "联盟"
                                    target.tap(*page.point)
                                    navigation_attempts += 1
                                    next_navigation_at = now + max(2.0, interval)
                                    self._log_for_device(
                                        target.device,
                                        f"导航：点击{destination}入口 {page.point}（第 {navigation_attempts}/3 次）。",
                                    )
                                else:
                                    next_navigation_at = now + 30.0
                                    notice(
                                        f"navigation-stalled-{page.page.value}",
                                        "导航页面没有按预期切换，已暂停输入 30 秒；请检查游戏是否有弹窗或未加入联盟。",
                                        30.0,
                                    )
                        else:
                            cached_point = cached_size = None
                            notice("unknown", f"未识别为主城、联盟或联盟互助页（最高分 {page.score:.3f}），不执行点击。")
                    failures = 0
                except Exception as exc:
                    failures += 1
                    backoff = min(30.0, max(interval, 1.0) * (2 ** min(failures, 4)))
                    self._log_for_device(target.device, f"本轮识别失败（{failures}）：{exc}；{backoff:.1f} 秒后安全重试。")
                    if self.stop_event.wait(backoff):
                        break
                    continue
                if self.stop_event.wait(interval):
                    break
            self._log_for_device(target.device, f"自动导航帮助已停止，共点击 {clicks} 次。")

        self._start_worker(target.device, job)

    def _start_red_packet_flow(self) -> None:
        """Start the visual, one-claim-at-a-time alliance red-packet workflow.

        The small envelope marker never authorizes a claim by itself.  It only
        arms a bounded page-flow; every subsequent tap uses a fresh screenshot
        and a more specific visual state from :func:`detect_red_packet_state`.
        """
        if not self.adb:
            QMessageBox.warning(self, APP_NAME, "尚未连接 MuMu。")
            return
        required = [resource_path(asset) for asset, _name in RED_PACKET_BUILTIN_TEMPLATES]
        missing = [path for path in required if not path.is_file()]
        if missing:
            names = "、".join(path.name for path in missing)
            QMessageBox.warning(self, APP_NAME, f"红包识别素材缺失：{names}\n请重新解压完整程序包。")
            return

        target = self.adb.clone_for_device()
        interval = self.red_packet_interval_spin.value()
        duration = self.red_packet_duration_spin.value()
        max_claims = self.red_packet_max_claims_spin.value()
        guard = self.red_packet_guard_check.isChecked()
        threshold = 0.90

        def job() -> None:
            claims, failures = 0, 0
            started = time.monotonic()
            armed = False
            marker_streak = 0
            marker_clear_streak = 0
            waiting_for_clear = False
            opened_at: float | None = None
            result_closed_at: float | None = None
            back_sent = False
            last_state: RedPacketState | None = None
            state_streak = 0
            action_attempts: dict[str, int] = {}
            next_input_at = 0.0
            hold_until = 0.0
            last_notice_key = ""
            last_notice_at = -30.0
            last_ui_state = ""

            def set_state(text: str) -> None:
                nonlocal last_ui_state
                if text != last_ui_state:
                    last_ui_state = text
                    self.signals.red_packet_state.emit(text)

            def notice(key: str, message: str, minimum_gap: float = 20.0) -> None:
                nonlocal last_notice_key, last_notice_at
                now = time.monotonic()
                if key != last_notice_key or now - last_notice_at >= minimum_gap:
                    self._log_for_device(target.device, message)
                    last_notice_key, last_notice_at = key, now

            def tap_for_state(
                action: str,
                point: tuple[int, int],
                description: str,
                limit: int = 3,
            ) -> bool:
                nonlocal next_input_at, hold_until
                now = time.monotonic()
                if now < next_input_at or now < hold_until:
                    return False
                count = action_attempts.get(action, 0)
                if count >= limit:
                    hold_until = now + 30.0
                    notice(
                        f"stalled-{action}",
                        f"{description}连续 {limit} 次未发生预期页面切换，暂停输入 30 秒。",
                        30.0,
                    )
                    return False
                target.tap(*point)
                action_attempts[action] = count + 1
                next_input_at = now + max(0.8, min(2.5, interval))
                self._log_for_device(target.device, f"{description} {point}（第 {count + 1}/{limit} 次）。")
                return True

            self._log_for_device(
                target.device,
                f"开始自动抢熔炉升级红包：检查间隔 {interval:.1f} 秒；F8 可全局停止。",
            )
            set_state("监听中：等待右下角红包浮标")
            while not self.stop_event.is_set():
                now = time.monotonic()
                if duration and now - started >= duration * 60:
                    self._log_for_device(target.device, "已达到红包运行时长。")
                    break
                if max_claims and claims >= max_claims:
                    self._log_for_device(target.device, "已达到最多领取次数。")
                    break
                try:
                    if guard and not target.foreground_is_game():
                        marker_streak = 0
                        set_state("已暂停：游戏不在模拟器前台")
                        notice("not-foreground", "游戏不在前台，本轮不截图、不点击。")
                    else:
                        image = target.screenshot()

                        # At rest, the notification marker is the only thing
                        # examined.  A city chat launcher by itself can never
                        # cause navigation.
                        if not armed:
                            marker, marker_score = match_red_packet_marker(image, 0.84)
                            if marker:
                                marker_streak += 1
                                set_state(f"发现红包浮标，正在复核（{marker_streak}/2）")
                                if marker_streak >= 2:
                                    armed = True
                                    marker_streak = 0
                                    action_attempts.clear()
                                    last_state = None
                                    self._log_for_device(
                                        target.device,
                                        f"红包浮标已连续确认，分数 {marker_score:.3f}；开始检查联盟频道。",
                                    )
                                    set_state("已确认浮标：正在打开聊天")
                            else:
                                marker_streak = 0
                                set_state("监听中：等待右下角红包浮标")
                        else:
                            page = detect_red_packet_state(image, threshold)
                            if page.state is last_state:
                                state_streak += 1
                            else:
                                last_state = page.state
                                state_streak = 1
                                action_attempts.clear()
                                self._log_for_device(
                                    target.device,
                                    f"红包页面识别：{self._red_packet_page_label(page.state)}（分数 {page.score:.3f}）。",
                                )

                            # After a verified result has been closed, the
                            # only permitted inputs are a guarded back from a
                            # confirmed chat and then passive marker-clear
                            # observation in the city.  This prevents a second
                            # tap on the same card.
                            if waiting_for_clear:
                                if page.state in (RedPacketState.ALLIANCE_CHAT, RedPacketState.FURNACE_PACKET):
                                    set_state("领取已确认：正在返回主城继续监听")
                                    if result_closed_at and not back_sent and now - result_closed_at >= 0.7:
                                        target.back()
                                        back_sent = True
                                        next_input_at = now + max(0.8, min(2.5, interval))
                                        self._log_for_device(target.device, "已确认联盟聊天页，安全返回主城。")
                                elif page.state is RedPacketState.CHAT_ENTRY:
                                    marker, _score = match_red_packet_marker(image, 0.84)
                                    if marker:
                                        marker_clear_streak = 0
                                        set_state("领取已确认：等待红包浮标消失")
                                    else:
                                        marker_clear_streak += 1
                                        set_state(f"领取已确认：复核浮标已消失（{marker_clear_streak}/2）")
                                        if marker_clear_streak >= 2:
                                            armed = False
                                            waiting_for_clear = False
                                            opened_at = result_closed_at = None
                                            back_sent = False
                                            marker_clear_streak = 0
                                            last_state = None
                                            action_attempts.clear()
                                            self._log_for_device(target.device, "红包浮标已消失，恢复监听下一次红包。")
                                            set_state("监听中：等待右下角红包浮标")
                                elif page.state is RedPacketState.CLAIM_RESULT_READY:
                                    set_state("领取已确认：正在关闭结果页")
                                    if result_closed_at and now - result_closed_at >= 12.0:
                                        notice("result-close-stalled", "结果页关闭后仍未切回聊天，已停止后续输入，请手动检查。", 30.0)
                                else:
                                    set_state("领取已确认：等待页面回到主城")
                            elif page.state is RedPacketState.CLAIM_RESULT_READY:
                                # A reward result is counted only when it
                                # immediately follows this worker's own
                                # exactly-once “开启” tap.
                                if opened_at and now - opened_at <= 12.0 and page.point:
                                    claims += 1
                                    self.signals.clicks.emit(claims)
                                    waiting_for_clear = True
                                    result_closed_at = now
                                    set_state("已确认领取结果：正在安全关闭")
                                    target.tap(*page.point)
                                    next_input_at = now + max(0.8, min(2.5, interval))
                                    self._log_for_device(
                                        target.device,
                                        f"已确认红包领取结果，累计领取 {claims} 次；关闭结果页 {page.point}。",
                                    )
                                else:
                                    set_state("发现结果页，但未关联本次开启：不点击")
                                    notice("unlinked-result", "结果页未与本窗口刚刚的开启操作关联，不关闭、不计数。")
                            elif opened_at:
                                # Never press “开启” twice.  If the result is
                                # not positively observed soon afterwards,
                                # leave the page untouched for the user.
                                if now - opened_at >= 12.0:
                                    set_state("开启后未确认结果：已停止输入，请手动检查")
                                    notice("open-result-timeout", "开启后 12 秒未识别到红包结果页，已停止后续输入。", 30.0)
                                    hold_until = max(hold_until, now + 30.0)
                            elif page.state is RedPacketState.CHAT_ENTRY:
                                set_state("已确认浮标：正在打开聊天")
                                if state_streak >= 2 and page.point:
                                    tap_for_state("chat-entry", page.point, "点击主城聊天入口")
                            elif page.state is RedPacketState.CHAT_PANEL:
                                set_state("聊天已打开：正在切换联盟频道")
                                if state_streak >= 2:
                                    alliance_tab = scale_recorded_point((720, 228), (1440, 2560), image.size)
                                    tap_for_state("alliance-tab", alliance_tab, "点击联盟频道", limit=3)
                            elif page.state is RedPacketState.ALLIANCE_CHAT:
                                set_state("已在联盟频道：等待熔炉升级红包")
                                notice("alliance-wait", "已确认联盟频道，当前未见“熔炉升级红包”卡片，原地等待。")
                            elif page.state is RedPacketState.FURNACE_PACKET:
                                set_state("已确认熔炉升级红包：正在打开")
                                if state_streak >= 2 and page.point:
                                    tap_for_state("furnace-card", page.point, "点击熔炉升级红包卡", limit=2)
                            elif page.state is RedPacketState.DETAIL_OPEN_READY:
                                set_state("已确认红包详情与开启按钮：正在开启")
                                if state_streak >= 2 and page.point:
                                    if tap_for_state("open", page.point, "点击红包开启按钮", limit=1):
                                        opened_at = time.monotonic()
                            elif page.state is RedPacketState.FURNACE_DETAIL:
                                set_state("已打开熔炉红包详情：未见可用开启按钮")
                                notice("detail-not-ready", "已打开熔炉升级红包详情，但未同时识别到可用“开启”按钮，不点击。")
                            elif page.state is RedPacketState.MARKER:
                                set_state("已确认浮标：未识别主城聊天入口")
                                notice("no-chat-entry", "已看到红包浮标，但未确认主城聊天入口，不执行坐标点击。")
                            else:
                                set_state("已确认浮标：未知页面，等待安全识别")
                                notice("unknown-page", f"红包流程未识别当前页面（最高分 {page.score:.3f}），不执行点击。")
                    failures = 0
                except Exception as exc:
                    failures += 1
                    backoff = min(30.0, max(interval, 1.0) * (2 ** min(failures, 4)))
                    self._log_for_device(target.device, f"红包识别失败（{failures}）：{exc}；{backoff:.1f} 秒后安全重试。")
                    set_state("识别异常：正在安全重试")
                    if self.stop_event.wait(backoff):
                        break
                    continue
                if self.stop_event.wait(interval):
                    break
            set_state("已停止")
            self._log_for_device(target.device, f"自动抢熔炉升级红包已停止，累计领取 {claims} 次。")

        self._start_worker(target.device, job)

    def _start_custom_clicker(self) -> None:
        self._start_clicker("template" if self.mode_combo.currentIndex() == 0 else "fixed")

    def _start_clicker(self, mode: str) -> None:
        if not self.adb:
            QMessageBox.warning(self, APP_NAME, "尚未连接 MuMu。")
            return
        template = TEMPLATE_DIR / self.template_combo.currentText()
        if mode == "template" and not template.is_file():
            QMessageBox.warning(self, APP_NAME, "请选择有效的按钮模板。")
            return
        if mode == "fixed" and (not self.selected_point or not self.selected_source_size):
            QMessageBox.warning(self, APP_NAME, "请先在设备中心的实时画面上单击要连点的位置。")
            return
        fixed_point = self.selected_point
        fixed_source_size = self.selected_source_size
        target = self.adb.clone_for_device()
        interval = self.interval_spin.value()
        duration = self.duration_spin.value()
        max_clicks = self.max_clicks_spin.value()
        threshold = self.threshold_slider.value() / 100
        guard = self.guard_check.isChecked()

        def job() -> None:
            clicks, failures = 0, 0
            started, last_idle = time.monotonic(), -30.0
            label = "识图运行" if mode == "template" else "固定坐标连点"
            self.log(f"开始{label}，F8 可全局停止。")
            while not self.stop_event.is_set():
                if duration and time.monotonic() - started >= duration * 60:
                    self.log("已达到运行时长。")
                    break
                if max_clicks and clicks >= max_clicks:
                    self.log("已达到最多点击次数。")
                    break
                try:
                    if guard and not target.foreground_is_game():
                        elapsed = time.monotonic() - started
                        if elapsed - last_idle >= 30:
                            self.log("游戏不在前台，本轮暂停。")
                            last_idle = elapsed
                    elif mode == "fixed":
                        assert fixed_point is not None and fixed_source_size is not None
                        point = scale_recorded_point(fixed_point, fixed_source_size, target.screen_size())
                        target.tap(*point)
                        clicks += 1
                        self.signals.clicks.emit(clicks)
                        if clicks == 1 or clicks % 20 == 0:
                            self.log(f"已点击 {clicks} 次，坐标 {point}。")
                    else:
                        image = target.screenshot()
                        point, score = match_template(image, template, threshold, template_reference_size(template))
                        matched_name = template.stem
                        if point:
                            target.tap(*point)
                            clicks += 1
                            self.signals.clicks.emit(clicks)
                            self.log(f"识别成功并点击 {matched_name} {point}，相似度 {score:.3f}，累计 {clicks} 次。")
                        else:
                            elapsed = time.monotonic() - started
                            if elapsed - last_idle >= 30:
                                self.log(f"等待按钮出现，当前最高相似度 {score:.3f}。")
                                last_idle = elapsed
                    failures = 0
                except Exception as exc:
                    failures += 1
                    self.log(f"本轮失败（{failures}/3）：{exc}")
                    if failures >= 3:
                        break
                if self.stop_event.wait(interval):
                    break
            self.log(f"运行结束，共点击 {clicks} 次。")

        self._start_worker(target.device, job)

    def _start_worker(self, device: str, callback: Callable[[], None]) -> None:
        if self.worker and self.worker.is_alive():
            QMessageBox.information(self, APP_NAME, "当前窗口已有任务正在运行。")
            return
        self.stop_event.clear()
        self.signals.clicks.emit(0)

        def protected() -> None:
            lease = DeviceLease(device)
            if not lease.acquire():
                self.log(f"实例 {device} 已被另一个窗口占用，本窗口未启动任务。")
                self.signals.alert.emit(APP_NAME, f"{device} 已在另一个助手窗口运行。\n为防止重复点击，本窗口未启动任务。")
                return
            self.signals.running.emit(True, "运行中")
            try:
                callback()
            finally:
                lease.release()
                self.stop_event.set()
                self.signals.running.emit(False, "已停止")

        self.worker = threading.Thread(target=protected, daemon=True)
        self.worker.start()

    def stop_all(self) -> None:
        self.stop_event.set()
        self.log("已发出停止指令。")

    def _update_runtime(self) -> None:
        seconds = max(0, int(time.monotonic() - self.started_at))
        self.runtime_label.setText(f"{seconds // 3600:02d}:{seconds // 60 % 60:02d}:{seconds % 60:02d}")

    def _assistant_command(self, device: str, startup_mode: str | None = None) -> list[str]:
        if getattr(sys, "frozen", False):
            command = [sys.executable]
        else:
            command = [sys.executable, str(Path(__file__).resolve())]
        command += ["--device", device]
        if startup_mode == "help":
            command += ["--auto-help", "--interval", str(self.interval_spin.value())]
        elif startup_mode == "red_packet":
            command += ["--auto-red-packet", "--interval", str(self.red_packet_interval_spin.value())]
        return command

    def _spawn_instance(self, device: str, startup_mode: str | None = None) -> None:
        try:
            subprocess.Popen(
                self._assistant_command(device, startup_mode),
                cwd=str(Path(sys.executable).resolve().parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parent),
                creationflags=CREATE_NO_WINDOW,
            )
            mode_text = {"help": "并开始联盟帮助", "red_packet": "并开始抢红包"}.get(startup_mode, "")
            self.log(f"已为 {device} 打开独立窗口{mode_text}。")
        except OSError as exc:
            QMessageBox.warning(self, APP_NAME, f"无法打开独立窗口：{exc}")

    def _open_selected_window(self) -> None:
        if self.adb:
            self._spawn_instance(self.adb.device)

    def _start_all_instances(self, startup_mode: str = "help") -> None:
        if not self.devices:
            QMessageBox.warning(self, APP_NAME, "没有发现运行中的 MuMu 实例。")
            return
        for device in self.devices:
            self._spawn_instance(device, startup_mode)
        mode_text = "联盟帮助" if startup_mode == "help" else "联盟红包"
        self.log(f"已为 {len(self.devices)} 个实例分别启动{mode_text}窗口。")

    def _load_tasks(self) -> dict[str, list[dict[str, Any]]]:
        try:
            data = json.loads(TASK_FILE.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                return {str(key): list(value) for key, value in data.items() if isinstance(value, list)}
        except (OSError, json.JSONDecodeError, TypeError):
            pass
        return {name: [dict(step) for step in steps] for name, steps in DEFAULT_TASKS.items()}

    def _refresh_tasks(self) -> None:
        current = self.task_combo.currentText() if hasattr(self, "task_combo") else ""
        self.task_combo.blockSignals(True)
        self.task_combo.clear()
        self.task_combo.addItems(sorted(self.tasks))
        if current in self.tasks:
            self.task_combo.setCurrentText(current)
        self.task_combo.blockSignals(False)
        self._load_selected_task()

    def _load_selected_task(self) -> None:
        self.active_steps = [dict(step) for step in self.tasks.get(self.task_combo.currentText(), [])]
        self._render_steps()

    def _step_text(self, index: int, step: dict[str, Any]) -> str:
        action = step.get("action")
        if action == "tap":
            detail = f"点击 ({step['x']}, {step['y']})"
        elif action == "wait":
            detail = f"等待 {step['seconds']} 秒"
        elif action == "back":
            detail = "Android 返回键"
        else:
            detail = f"识图 {step.get('template')} · 超时 {step.get('timeout', 15)} 秒"
        return f"{index + 1:02d}    {detail}"

    def _render_steps(self) -> None:
        self.step_list.clear()
        self.step_list.addItems([self._step_text(i, step) for i, step in enumerate(self.active_steps)])

    def _new_task(self) -> None:
        name, ok = QInputDialog.getText(self, APP_NAME, "新任务名称：")
        if ok and name.strip():
            self.tasks[name.strip()] = []
            self._refresh_tasks()
            self.task_combo.setCurrentText(name.strip())

    def _task_add_point(self) -> None:
        if not self.selected_point or not self.selected_source_size:
            QMessageBox.information(self, APP_NAME, "请先在设备中心画面上选择一个坐标。")
            return
        self.active_steps.append({"action": "tap", "x": self.selected_point[0], "y": self.selected_point[1], "width": self.selected_source_size[0], "height": self.selected_source_size[1]})
        self._render_steps()

    def _task_add_wait(self) -> None:
        value, ok = QInputDialog.getDouble(self, APP_NAME, "等待秒数：", 2.0, 0, 86400, 1)
        if ok:
            self.active_steps.append({"action": "wait", "seconds": value})
            self._render_steps()

    def _task_add_back(self) -> None:
        self.active_steps.append({"action": "back"})
        self._render_steps()

    def _task_add_template(self) -> None:
        names = [self.template_combo.itemText(i) for i in range(self.template_combo.count())]
        if not names:
            return
        name, ok = QInputDialog.getItem(self, APP_NAME, "选择模板：", names, 0, False)
        if ok:
            timeout, accepted = QInputDialog.getDouble(self, APP_NAME, "等待超时（秒）：", 15, 1, 86400, 1)
            if accepted:
                self.active_steps.append({"action": "template", "template": name, "timeout": timeout, "threshold": self.threshold_slider.value() / 100})
                self._render_steps()

    def _delete_task_step(self) -> None:
        row = self.step_list.currentRow()
        if 0 <= row < len(self.active_steps):
            self.active_steps.pop(row)
            self._render_steps()

    def _save_task(self) -> None:
        name = self.task_combo.currentText().strip()
        if not name:
            return
        self.tasks[name] = [dict(step) for step in self.active_steps]
        TASK_FILE.write_text(json.dumps(self.tasks, ensure_ascii=False, indent=2), encoding="utf-8")
        self.log(f"已保存任务：{name}")

    def _delete_task(self) -> None:
        name = self.task_combo.currentText()
        if name and QMessageBox.question(self, APP_NAME, f"删除任务“{name}”？") == QMessageBox.StandardButton.Yes:
            self.tasks.pop(name, None)
            TASK_FILE.write_text(json.dumps(self.tasks, ensure_ascii=False, indent=2), encoding="utf-8")
            self._refresh_tasks()

    def _run_task(self) -> None:
        if not self.adb or not self.active_steps:
            QMessageBox.information(self, APP_NAME, "请先连接实例并准备任务步骤。")
            return
        target = self.adb.clone_for_device()
        steps = [dict(step) for step in self.active_steps]
        repeat, repeat_wait = self.repeat_check.isChecked(), self.repeat_wait.value()

        def job() -> None:
            round_number = 0
            self.log("开始执行任务序列。")
            while not self.stop_event.is_set():
                round_number += 1
                for index, step in enumerate(steps):
                    if self.stop_event.is_set():
                        break
                    action = step.get("action")
                    try:
                        if action in {"tap", "back", "template"} and not target.foreground_is_game():
                            self.log(f"步骤 {index + 1} 暂停：游戏不在前台。")
                            while not self.stop_event.wait(2):
                                if target.foreground_is_game():
                                    break
                        if action == "tap":
                            point = scale_recorded_point((int(step["x"]), int(step["y"])), (int(step["width"]), int(step["height"])), target.screen_size())
                            target.tap(*point)
                            self.log(f"步骤 {index + 1}：点击 {point}。")
                        elif action == "wait":
                            if self.stop_event.wait(float(step["seconds"])):
                                break
                        elif action == "back":
                            target.back()
                        elif action == "template":
                            deadline = time.monotonic() + float(step.get("timeout", 15))
                            while time.monotonic() < deadline and not self.stop_event.is_set():
                                path = TEMPLATE_DIR / str(step["template"])
                                point, score = match_template(target.screenshot(), path, float(step.get("threshold", 0.88)), template_reference_size(path))
                                if point:
                                    target.tap(*point)
                                    self.log(f"步骤 {index + 1}：识图点击 {point}，相似度 {score:.3f}。")
                                    break
                                self.stop_event.wait(1)
                    except Exception as exc:
                        self.log(f"步骤 {index + 1} 失败：{exc}")
                        self.stop_event.set()
                        break
                if not repeat or self.stop_event.is_set():
                    break
                if self.stop_event.wait(repeat_wait):
                    break
            self.log("任务序列已结束。")

        self._start_worker(target.device, job)

    def _hotkey_loop(self) -> None:
        if os.name != "nt":
            return
        user32 = ctypes.windll.user32
        while not self.closing.is_set():
            if user32.GetAsyncKeyState(0x77) & 1:
                self.stop_event.set()
                self.log("检测到全局 F8，正在停止。")
            time.sleep(0.08)

    def closeEvent(self, event: Any) -> None:
        self.closing.set()
        self.stop_event.set()
        event.accept()


def main() -> None:
    parser = argparse.ArgumentParser(description=APP_NAME)
    parser.add_argument("--device")
    parser.add_argument("--auto-help", action="store_true")
    parser.add_argument("--all-auto-help", action="store_true")
    parser.add_argument("--auto-red-packet", action="store_true")
    parser.add_argument("--all-auto-red-packet", action="store_true")
    parser.add_argument("--interval", type=float, help="自动导航帮助的点击 / 识别间隔（秒）")
    args = parser.parse_args()
    if hasattr(Qt.ApplicationAttribute, "AA_EnableHighDpiScaling"):
        QApplication.setAttribute(Qt.ApplicationAttribute.AA_EnableHighDpiScaling, True)
    app = QApplication(sys.argv[:1])
    app.setApplicationName(APP_NAME)
    app.setApplicationVersion(APP_VERSION)
    app.setOrganizationName("WJDR Tools")
    app.setStyle("Fusion")
    window = MainWindow(
        args.device,
        args.auto_help,
        args.all_auto_help,
        args.auto_red_packet,
        args.all_auto_red_packet,
        args.interval,
    )
    window.show()
    qa_page = os.environ.get("WJDR_QA_PAGE")
    if qa_page and qa_page.isdigit():
        window._show_page(min(int(qa_page), window.stack.count() - 1))
    qa_screenshot = os.environ.get("WJDR_QA_SCREENSHOT")
    if qa_screenshot:
        def save_qa_screenshot() -> None:
            saved = window.grab().save(qa_screenshot, "PNG")
            window.log(f"UI 验收截图{'已保存' if saved else '保存失败'}：{qa_screenshot}")

        QTimer.singleShot(3500, save_qa_screenshot)
    raise SystemExit(app.exec())


if __name__ == "__main__":
    main()
