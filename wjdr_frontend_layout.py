"""Qt page construction and appearance for the desktop window."""

from __future__ import annotations
import os
from PySide6.QtCore import (
    Qt,
    QTimer,
)
from PySide6.QtGui import (
    QColor,
    QPalette,
)
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QPushButton,
    QScrollArea,
    QSlider,
    QSpinBox,
    QStackedWidget,
    QTextEdit,
    QToolButton,
    QVBoxLayout,
    QWidget,
)
from wjdr_backend import (
    APP_NAME,
    APP_VERSION,
    CONFIG_DIR,
    resource_path,
)
from wjdr_ui_components import (
    COLORS,
    Card,
    ScreenshotView,
)
from wjdr_runtime_config import (
    MAX_SINGLE_WAIT_SECONDS,
)


PAGE_HEADERS = (
    ("设备中心", "查看当前实例的画面和运行状态"),
    ("联盟帮助", "自动识别并点击联盟互助页的全部帮助"),
    ("联盟红包", "监听熔炉升级红包"),
    ("每日任务", "领取奖励并执行已验证的每日任务"),
    ("巨兽集结", "冰原巨兽 · 三分钟集结"),
    ("定时启动", "为当前手机预约一次任务启动"),
    ("任务编排", "编辑点击、等待、返回和识图步骤"),
    ("运行日志", "查看当前手机的运行记录"),
    ("关于与安全", ""),
    ("备战积分", "采集榜单、保存快照并对比积分"),
)
NAV_SECTIONS = (
    ("", (0,)),
    ("自动化", (4, 3, 1, 2)),
    ("任务管理", (5, 9, 6)),
    ("排查与帮助", (7, 8)),
)


class FrontendLayout:
    def _build_ui(self) -> None:
        root = QWidget()
        root.setObjectName("root")
        self.setCentralWidget(root)
        shell = QHBoxLayout(root)
        shell.setContentsMargins(0, 0, 0, 0)
        shell.setSpacing(0)

        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(186)
        side = QVBoxLayout(sidebar)
        side.setContentsMargins(12, 18, 12, 14)
        side.setSpacing(12)
        brand_row = QHBoxLayout()
        brand_row.setContentsMargins(5, 0, 2, 0)
        brand_icon = QLabel("❄")
        brand_icon.setObjectName("brandIcon")
        brand_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        brand_text = QVBoxLayout()
        brand = QLabel("无尽冬日助手")
        brand.setObjectName("brand")
        brand_sub = QLabel(f"v{APP_VERSION}")
        brand_sub.setObjectName("brandSub")
        brand_text.addWidget(brand)
        brand_text.addWidget(brand_sub)
        brand_row.addWidget(brand_icon)
        brand_row.addLayout(brand_text, 1)
        side.addLayout(brand_row)
        self.nav_scroll = QScrollArea()
        self.nav_scroll.setObjectName("navigation")
        self.nav_scroll.setWidgetResizable(True)
        self.nav_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        nav_body = QWidget()
        nav_body.setObjectName("navigationBody")
        self.nav_scroll.setWidget(nav_body)
        nav = QVBoxLayout(nav_body)
        nav.setContentsMargins(0, 0, 0, 0)
        nav.setSpacing(3)
        buttons_by_page = {}
        for heading, pages in NAV_SECTIONS:
            if heading:
                section = QLabel(heading)
                section.setObjectName("navSection")
                nav.addWidget(section)
            for index in pages:
                button = QPushButton(PAGE_HEADERS[index][0])
                button.setObjectName("navButton")
                button.setCheckable(True)
                button.setCursor(Qt.CursorShape.PointingHandCursor)
                button.clicked.connect(lambda _checked=False, page=index: self._show_page(page))
                nav.addWidget(button)
                buttons_by_page[index] = button
        nav.addStretch()
        self.nav_buttons = [buttons_by_page[index] for index in range(len(PAGE_HEADERS))]
        self.nav_buttons[0].setChecked(True)
        side.addWidget(self.nav_scroll, 1)
        safety = QLabel("F8  全局急停")
        safety.setObjectName("sidebarFooter")
        safety.setToolTip("F8 停止所有助手窗口。顶部停止按钮只影响当前窗口。")
        side.addWidget(safety)
        shell.addWidget(sidebar)

        main = QWidget()
        main.setObjectName("main")
        main_layout = QVBoxLayout(main)
        main_layout.setContentsMargins(20, 14, 20, 16)
        main_layout.setSpacing(13)
        toolbar = Card(name="deviceToolbar")
        device_bar = QHBoxLayout(toolbar)
        device_bar.setContentsMargins(12, 7, 12, 7)
        device_bar.setSpacing(8)
        device_bar.addWidget(self._field_label("当前手机"))
        self.device_combo = QComboBox()
        self.device_combo.setObjectName("deviceCombo")
        self.device_combo.setMinimumWidth(200)
        self.device_combo.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        self.device_combo.setMinimumContentsLength(16)
        self.device_combo.setAccessibleName("当前绑定手机")
        self.device_combo.currentIndexChanged.connect(self._device_changed)
        device_bar.addWidget(self.device_combo, 1)
        scan = QPushButton("扫描设备")
        scan.setObjectName("ghostButton")
        scan.clicked.connect(lambda: self._run_async(self._connect_job))
        self.scan_button = scan
        device_bar.addWidget(scan)
        self.device_manager_button = QPushButton("多手机窗口")
        self.device_manager_button.setObjectName("secondaryButton")
        self.device_manager_button.clicked.connect(self._open_device_manager)
        device_bar.addWidget(self.device_manager_button)
        self.status_pill = QLabel("●  正在连接")
        self.status_pill.setObjectName("statusPill")
        device_bar.addWidget(self.status_pill)
        self.stop_button = QPushButton("停止当前")
        self.stop_button.setObjectName("stopCurrentButton")
        self.stop_button.setToolTip("停止当前窗口的任务")
        self.stop_button.clicked.connect(self.stop_all)
        device_bar.addWidget(self.stop_button)
        main_layout.addWidget(toolbar)

        titles = QVBoxLayout()
        titles.setSpacing(2)
        self.page_title = QLabel(PAGE_HEADERS[0][0])
        self.page_title.setObjectName("pageTitle")
        self.page_subtitle = QLabel(PAGE_HEADERS[0][1])
        self.page_subtitle.setObjectName("pageSubtitle")
        titles.addWidget(self.page_title)
        titles.addWidget(self.page_subtitle)
        main_layout.addLayout(titles)

        self.stack = QStackedWidget()
        self.stack.addWidget(self._build_dashboard())
        self.stack.addWidget(self._build_automation())
        self.stack.addWidget(self._build_red_packet_page())
        self.stack.addWidget(self._build_daily_task_page())
        self.stack.addWidget(self._build_beast_rally_page())
        self.stack.addWidget(self._build_schedule_page())
        self.stack.addWidget(self._build_tasks_page())
        self.stack.addWidget(self._build_log_page())
        self.stack.addWidget(self._build_about_page())
        self.stack.addWidget(self._build_scoreboard_page())
        # Every page remains accessible on short/high-DPI displays. Never let
        # a long status or title silently enlarge the native window.
        for label in main.findChildren(QLabel) + self.stack.findChildren(QLabel):
            if label.objectName() not in {"statusPill", "statValue", "greenPill"}:
                label.setWordWrap(True)
        for index in (0, 6):
            body = self.stack.widget(index)
            self.stack.removeWidget(body)
            scroll = QScrollArea()
            scroll.setWidgetResizable(True)
            scroll.setFrameShape(QFrame.Shape.NoFrame)
            self._set_window_background(scroll.viewport())
            self._set_window_background(body)
            scroll.setWidget(body)
            self.stack.insertWidget(index, scroll)
        main_layout.addWidget(self.stack, 1)
        shell.addWidget(main, 1)

    def _build_dashboard(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)
        shortcuts = Card()
        shortcuts_layout = QHBoxLayout(shortcuts)
        shortcuts_layout.setContentsMargins(16, 10, 16, 10)
        title = QLabel("常用任务")
        title.setObjectName("cardTitle")
        shortcuts_layout.addWidget(title)
        shortcuts_layout.addSpacing(8)
        for index in (4, 3, 1):
            button = QPushButton(PAGE_HEADERS[index][0])
            button.setObjectName("quickTask")
            button.setToolTip(f"打开{PAGE_HEADERS[index][0]}页面")
            button.clicked.connect(lambda _checked=False, page=index: self._show_page(page))
            shortcuts_layout.addWidget(button, 1)
        layout.addWidget(shortcuts)

        content = QHBoxLayout()
        content.setSpacing(16)
        preview_card = Card()
        preview_layout = QVBoxLayout(preview_card)
        preview_layout.setContentsMargins(18, 16, 18, 16)
        preview_header = QHBoxLayout()
        preview_title = QLabel("实时画面")
        preview_title.setObjectName("cardTitle")
        self.point_label = QLabel("单击选点 · 拖动框选")
        self.point_label.setObjectName("muted")
        preview_header.addWidget(preview_title)
        preview_header.addStretch()
        preview_header.addWidget(self.point_label)
        preview_layout.addLayout(preview_header)
        self.screenshot = ScreenshotView()
        self.screenshot.setMinimumHeight(328)
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
        action_grid.addWidget(launch, 0, 0)
        action_grid.addWidget(separate, 0, 1)
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
        title = QLabel("自定义识图")
        title.setObjectName("sectionTitle")
        desc = QLabel("可使用已保存的模板，或在设备中心选取固定坐标。")
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
        start_custom = QPushButton("开始自定义识图")
        start_custom.setObjectName("softButton")
        start_custom.clicked.connect(self._start_custom_clicker)
        form.addWidget(start_custom)
        layout.addWidget(recognition, 1)

        limits = Card()
        limit_layout = QVBoxLayout(limits)
        limit_layout.setContentsMargins(24, 22, 24, 24)
        limit_title = QLabel("运行设置")
        limit_title.setObjectName("sectionTitle")
        limit_layout.addWidget(limit_title)
        self.start_button = QPushButton("开始联盟帮助")
        self.start_button.setObjectName("primaryButton")
        self.start_button.clicked.connect(self._start_help_preset)
        limit_layout.addWidget(self.start_button)
        help_hint = QLabel("从已识别的主城或联盟页进入互助，仅点击已确认的「全部帮助」。")
        help_hint.setObjectName("muted")
        limit_layout.addWidget(help_hint)
        limit_layout.addSpacing(14)
        self.interval_spin = QDoubleSpinBox()
        self.interval_spin.setRange(0.12, MAX_SINGLE_WAIT_SECONDS)
        self.interval_spin.setValue(1.0)
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
        self.red_packet_start_button = QPushButton("开始红包监听")
        self.red_packet_start_button.setObjectName("primaryButton")
        self.red_packet_start_button.clicked.connect(self._start_red_packet_flow)
        status_layout.addWidget(self.red_packet_start_button)
        layout.addWidget(status_card)

        limits = Card()
        limit_layout = QVBoxLayout(limits)
        limit_layout.setContentsMargins(24, 22, 24, 24)
        limit_title = QLabel("红包运行设置")
        limit_title.setObjectName("sectionTitle")
        limit_layout.addWidget(limit_title)
        limit_layout.addSpacing(14)
        self.red_packet_interval_spin = QDoubleSpinBox()
        self.red_packet_interval_spin.setRange(0.12, MAX_SINGLE_WAIT_SECONDS)
        self.red_packet_interval_spin.setValue(1.0)
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
        layout.addWidget(limits)

        advanced = QWidget()
        advanced_layout = QVBoxLayout(advanced)
        advanced_layout.setContentsMargins(0, 0, 0, 2)
        all_instances = QPushButton("全部实例抢红包")
        all_instances.setObjectName("secondaryButton")
        all_instances.clicked.connect(lambda: self._start_all_instances("red_packet"))
        advanced_layout.addWidget(all_instances, 0, Qt.AlignmentFlag.AlignLeft)
        rules = QLabel(
            "连续确认红包浮标、联盟频道和熔炉升级红包后才开启。"
            "仅检查当前聊天画面。领取后确认结果页，再返回主城继续监听。"
        )
        rules.setObjectName("muted")
        rules.setWordWrap(True)
        advanced_layout.addWidget(rules)
        layout.addWidget(self._build_disclosure("批量运行与规则", advanced))
        layout.addStretch()
        return page

    def _build_daily_task_page(self) -> QWidget:
        """Build the verified daily-reward and ordinary-gathering workflow."""
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

        status_card = Card(name="dailyTaskStatusCard")
        status_layout = QHBoxLayout(status_card)
        status_layout.setContentsMargins(22, 17, 22, 17)
        state_text = QVBoxLayout()
        state_title = QLabel("每日任务状态")
        state_title.setObjectName("cardTitle")
        self.daily_task_state_label = QLabel("待命：等待每日任务页；仅执行已验证的免费任务")
        self.daily_task_state_label.setObjectName("redPacketState")
        state_hint = QLabel("每一步都需连续两帧确认；采集、训练和建筑任务会等待自然完成，随后继续核验。")
        state_hint.setObjectName("muted")
        state_hint.setWordWrap(True)
        state_text.addWidget(state_title)
        state_text.addWidget(self.daily_task_state_label)
        state_text.addWidget(state_hint)
        status_layout.addLayout(state_text, 1)
        self.daily_task_start_button = QPushButton("开始每日任务")
        self.daily_task_start_button.setObjectName("primaryButton")
        self.daily_task_start_button.clicked.connect(self._start_daily_rewards_flow)
        status_layout.addWidget(self.daily_task_start_button)
        layout.addWidget(status_card)

        limits = Card(name="dailyAccountSettingsCard")
        limit_layout = QVBoxLayout(limits)
        limit_layout.setContentsMargins(24, 22, 24, 24)
        settings_header = QHBoxLayout()
        settings_header.setSpacing(14)
        settings_copy = QVBoxLayout()
        settings_copy.setSpacing(4)
        limit_title = QLabel("当前账号设置")
        limit_title.setObjectName("sectionTitle")
        self.mining_profile_context = QLabel("选择在线 MuMu 账号后可配置")
        self.mining_profile_context.setObjectName("muted")
        settings_copy.addWidget(limit_title)
        settings_copy.addWidget(self.mining_profile_context)
        settings_header.addLayout(settings_copy, 1)
        self.mining_level_button = QPushButton("设置采矿策略")
        self.mining_level_button.setObjectName("settingsButton")
        self.mining_level_button.setAccessibleName("当前账号采矿设置")
        self.mining_level_button.setEnabled(False)
        self.mining_level_button.clicked.connect(self._open_mining_level_settings)
        settings_header.addWidget(self.mining_level_button, 0, Qt.AlignmentFlag.AlignVCenter)
        limit_layout.addLayout(settings_header)
        limit_layout.addSpacing(14)
        runtime_title = QLabel("运行参数")
        runtime_title.setObjectName("fieldLabel")
        limit_layout.addWidget(runtime_title)
        self.daily_interval_spin = QDoubleSpinBox()
        self.daily_interval_spin.setRange(0.0, MAX_SINGLE_WAIT_SECONDS)
        self.daily_interval_spin.setValue(0.0)
        self.daily_interval_spin.setSingleStep(0.05)
        self.daily_interval_spin.setSuffix(" 秒 / 动态检查")
        self.daily_duration_spin = QSpinBox()
        self.daily_duration_spin.setRange(0, 100000)
        # The Daily Task request is target-bound: once 325 is independently
        # confirmed, new-progress routes stop but already-completed rewards
        # are drained before the worker ends.  Keep an explicit time cap
        # available as an opt-in.
        self.daily_duration_spin.setValue(0)
        self.daily_duration_spin.setSuffix(" 分钟")
        self.daily_guard_check = QCheckBox("仅当《无尽冬日》位于模拟器前台时点击")
        self.daily_guard_check.setChecked(True)
        runtime_fields = QGridLayout()
        for column, (label, widget) in enumerate((
            ("截图 / 检查间隔", self.daily_interval_spin),
            ("最长等待（0 = 不限）", self.daily_duration_spin),
        )):
            runtime_fields.addWidget(self._field_label(label), 0, column)
            runtime_fields.addWidget(widget, 1, column)
            runtime_fields.setColumnStretch(column, 1)
        limit_layout.addLayout(runtime_fields)
        limit_layout.addWidget(self.daily_guard_check)
        layout.addWidget(limits)

        advanced = QWidget()
        advanced_layout = QVBoxLayout(advanced)
        advanced_layout.setContentsMargins(0, 0, 0, 2)
        all_instances = QPushButton("全部实例执行每日任务")
        all_instances.setObjectName("secondaryButton")
        all_instances.clicked.connect(lambda: self._start_all_instances("daily"))
        advanced_layout.addWidget(all_instances, 0, Qt.AlignmentFlag.AlignLeft)
        rules = QLabel(
            "自动领取已完成的奖励与活跃度宝箱，执行已验证的采集、训练、建筑、联盟捐献、竞技场和宠物寻宝。"
            "执行范围为已验证的免费操作，宠物派遣消耗 10 体力。"
        )
        rules.setObjectName("muted")
        rules.setWordWrap(True)
        advanced_layout.addWidget(rules)
        layout.addWidget(self._build_disclosure("批量运行与规则", advanced))
        layout.addStretch()
        return page

    def _build_beast_rally_page(self) -> QWidget:
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

        status = Card(name="dailyTaskStatusCard")
        status_layout = QHBoxLayout(status)
        status_layout.setContentsMargins(22, 17, 22, 17)
        state_text = QVBoxLayout()
        state_title = QLabel("巨兽集结状态")
        state_title.setObjectName("cardTitle")
        self.beast_rally_state_label = QLabel("待命：等待已验证的野外页面")
        self.beast_rally_state_label.setObjectName("redPacketState")
        state_text.addWidget(state_title)
        state_text.addWidget(self.beast_rally_state_label)
        status_layout.addLayout(state_text, 1)
        self.beast_rally_start_button = QPushButton("开始自动集结")
        self.beast_rally_start_button.setObjectName("primaryButton")
        self.beast_rally_start_button.clicked.connect(self._start_beast_rally_flow)
        status_layout.addWidget(self.beast_rally_start_button)
        layout.addWidget(status)

        account = Card(name="beastAccountSettingsCard")
        account_layout = QHBoxLayout(account)
        account_layout.setContentsMargins(22, 18, 22, 18)
        account_copy = QVBoxLayout()
        account_copy.setSpacing(4)
        account_title = QLabel("当前账号配置")
        account_title.setObjectName("cardTitle")
        self.beast_rally_profile_context = QLabel("选择在线 MuMu 账号后可配置")
        self.beast_rally_profile_context.setObjectName("muted")
        account_copy.addWidget(account_title)
        account_copy.addWidget(self.beast_rally_profile_context)
        account_layout.addLayout(account_copy, 1)
        self.beast_rally_profile_summary = QLabel("等级 8 · 体力不限 · 今日 0")
        self.beast_rally_profile_summary.setObjectName("valuePill")
        account_copy.addWidget(self.beast_rally_profile_summary)
        self.beast_rally_settings_button = QPushButton("设置巨兽参数")
        self.beast_rally_settings_button.setObjectName("settingsButton")
        self.beast_rally_settings_button.setAccessibleName("当前账号巨兽设置")
        self.beast_rally_settings_button.setEnabled(False)
        self.beast_rally_settings_button.clicked.connect(self._open_beast_rally_settings)
        account_layout.addWidget(self.beast_rally_settings_button)
        layout.addWidget(account)

        advanced = QWidget()
        advanced_layout = QVBoxLayout(advanced)
        advanced_layout.setContentsMargins(0, 0, 0, 2)
        buttons = QHBoxLayout()
        separate = QPushButton("打开当前账号独立窗口")
        separate.setObjectName("softButton")
        separate.clicked.connect(self._open_selected_window)
        buttons.addWidget(separate)
        all_instances = QPushButton("全部实例分别启动")
        all_instances.setObjectName("secondaryButton")
        all_instances.clicked.connect(lambda: self._start_all_instances("beast_rally"))
        buttons.addWidget(all_instances)
        buttons.addStretch()
        advanced_layout.addLayout(buttons)
        rules = QLabel(
            "仅运行冰原巨兽。体力上限为 0 时不限。"
            "队列与归属需新帧确认，不执行支付、加速或自动加入。"
        )
        rules.setObjectName("muted")
        rules.setWordWrap(True)
        advanced_layout.addWidget(rules)
        layout.addWidget(self._build_disclosure("批量运行与规则", advanced))
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
        self.log_edit.document().setMaximumBlockCount(2000)
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
        title.setObjectName("sectionTitle")
        text = QLabel(
            "这是一个使用 MuMu IPC 取帧、识图和 ADB 模拟点击的本地工具。\n\n"
            "• 不读取游戏内存，不修改 APK，不读取账号密码。\n"
            "• 每个窗口绑定一个独立 ADB 端口，同一实例带跨进程占用锁。\n"
            "• 游戏画面自动归一化；具体账号与分辨率仍需首次运行核验。\n"
            "• F8 停止所有助手窗口，顶部停止按钮只影响当前窗口。任务运行时请避免手动点击同一手机。\n\n"
            "游戏服务条款可能禁止 auto / macro / bot。无人值守自动化可能导致账号处罚，"
            "请保持有人观察；仅运行已配置的流程，不进行充值或额外购买。"
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
    def _build_disclosure(title: str, content: QWidget) -> QWidget:
        panel = Card()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(16, 5, 16, 7)
        toggle = QToolButton()
        toggle.setObjectName("disclosureButton")
        toggle.setText(title)
        toggle.setCheckable(True)
        toggle.setArrowType(Qt.ArrowType.RightArrow)
        toggle.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        toggle.setCursor(Qt.CursorShape.PointingHandCursor)
        layout.addWidget(toggle, 0, Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(content)
        content.hide()

        def set_expanded(expanded: bool) -> None:
            toggle.setArrowType(Qt.ArrowType.DownArrow if expanded else Qt.ArrowType.RightArrow)
            content.setVisible(expanded)

        toggle.toggled.connect(set_expanded)
        return panel

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
            QFrame#sidebar, QScrollArea#navigation, QWidget#navigationBody {{ background: {COLORS['navy']}; }}
            QLabel#brandIcon {{ background: #2E6FE6; color: white; border-radius: 10px; min-width: 34px; min-height: 34px; font-size: 19px; font-weight: 700; }}
            QLabel#brand {{ color: #F8FAFF; font-size: 15px; font-weight: 700; }}
            QLabel#brandSub {{ color: #9CAEC9; font-size: 11px; }}
            QLabel#navSection {{ color: #A2B3CC; font-size: 11px; font-weight: 600; padding: 10px 10px 1px; }}
            QPushButton#navButton {{ text-align: left; color: #D3DFF1; background: transparent; border: 1px solid transparent; border-left: 3px solid transparent; border-radius: 7px; min-height: 31px; padding: 0 9px; font-size: 13px; font-weight: 600; }}
            QPushButton#navButton:hover {{ color: white; background: #1A2C4A; }}
            QPushButton#navButton:checked {{ color: #FFFFFF; background: #233E68; border-left-color: #72AAFF; }}
            QPushButton#navButton:focus {{ border-color: #72AAFF; }}
            QLabel#sidebarFooter {{ color: #B7C7DD; font-size: 12px; border-top: 1px solid #2C3C55; padding: 10px 7px 0; }}
            QLabel#pageTitle {{ font-size: 23px; font-weight: 750; }}
            QLabel#pageSubtitle, QLabel#muted {{ color: {COLORS['muted']}; font-size: 12px; }}
            QLabel#statusPill {{ background: {COLORS['green_soft']}; color: #11865B; border-radius: 15px; padding: 8px 12px; font-weight: 700; }}
            QFrame#card, QFrame#noticeCard, QFrame#dailyTaskStatusCard {{ background: white; border: 1px solid {COLORS['border']}; border-radius: 14px; }}
            QFrame#deviceToolbar {{ background: white; border: 1px solid {COLORS['border']}; border-radius: 12px; }}
            QFrame#deviceToolbar QPushButton {{ min-height: 32px; padding: 0 11px; }}
            QFrame#deviceToolbar QComboBox {{ padding: 4px 9px; }}
            QPushButton#stopCurrentButton {{ background: #FFF0F1; color: #A63142; border: 1px solid #F2CCD2; }}
            QPushButton#stopCurrentButton:hover {{ background: #FCE1E4; }}
            QPushButton#quickTask {{ text-align: left; color: #234B8F; border: 1px solid #D9E6F8; background: #F4F8FF; }}
            QPushButton#quickTask:hover {{ color: #1747A0; border-color: #98B8EC; background: #EDF4FF; }}
            QToolButton#disclosureButton {{ min-height: 31px; padding: 0 5px; border: 1px solid transparent; border-radius: 6px; font-weight: 650; }}
            QToolButton#disclosureButton:hover {{ background: #F1F5FC; }}
            QToolButton#disclosureButton:focus {{ border-color: #98B8EC; }}
            QFrame#dailyAccountSettingsCard, QFrame#beastAccountSettingsCard {{ background: #F8FAFE; border: 1px solid #D8E3F5; border-radius: 14px; }}
            QFrame#redPacketStatusCard {{ background: #FFF8F0; border: 1px solid #F1D4B1; border-radius: 14px; }}
            QLabel#redPacketState {{ color: #B45624; font-size: 15px; font-weight: 750; }}
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
            QPushButton#secondaryButton {{ background: #E9F0FE; color: #275FBF; border: 1px solid #CDDCF8; }}
            QPushButton#settingsButton {{ background: white; color: #255EC5; border: 1px solid #BFD1EF; min-width: 168px; }}
            QPushButton#settingsButton:hover {{ background: #EDF3FF; border-color: #8FB0E3; }}
            QPushButton#settingsButton:disabled {{ background: #F1F4F8; color: #98A5B8; border-color: #DCE3EC; }}
            QPushButton#softButton, QPushButton#ghostButton {{ background: white; color: #3D4C63; border: 1px solid {COLORS['border']}; }}
            QPushButton#softButton:hover, QPushButton#ghostButton:hover {{ border-color: #AFC3E3; background: #F8FAFE; }}
            QPushButton#dangerButton {{ background: {COLORS['red']}; color: white; border: none; }}
            QComboBox, QSpinBox, QDoubleSpinBox, QDateTimeEdit {{ background: white; border: 1px solid {COLORS['border']}; border-radius: 9px; padding: 8px 11px; min-height: 24px; }}
            QComboBox:hover, QSpinBox:hover, QDoubleSpinBox:hover {{ border-color: #AFC3E3; }}
            QComboBox::drop-down {{ border: none; width: 28px; }}
            QComboBox::down-arrow, QSpinBox::down-arrow, QDoubleSpinBox::down-arrow {{ image: url("{resource_path('assets/ui_chevron_down.svg').as_posix()}"); width: 12px; height: 8px; }}
            QSpinBox::up-arrow, QDoubleSpinBox::up-arrow {{ image: url("{resource_path('assets/ui_chevron_up.svg').as_posix()}"); width: 12px; height: 8px; }}
            QSpinBox::up-button, QDoubleSpinBox::up-button, QSpinBox::down-button, QDoubleSpinBox::down-button {{ border: none; width: 22px; background: #EDF2FA; }}
            QComboBox QAbstractItemView {{ background: white; border: 1px solid {COLORS['border']}; selection-background-color: #E9F0FE; selection-color: {COLORS['text']}; padding: 6px; }}
            QCheckBox {{ spacing: 8px; }}
            QListWidget {{ background: {COLORS['surface_alt']}; border: 1px solid {COLORS['border']}; border-radius: 10px; padding: 6px; }}
            QTableWidget {{ background: white; alternate-background-color: #F5F8FD; color: #233247; gridline-color: #DCE4F0; border: 1px solid #DCE4F0; selection-background-color: #E4EDFE; selection-color: #233247; }}
            QHeaderView::section {{ background: #EDF3FC; color: #344960; padding: 8px; border: none; font-weight: 600; }}
            QCalendarWidget QWidget {{ background: white; color: #233247; }}
            QCalendarWidget QToolButton {{ background: #EDF3FC; color: #233247; }}
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
        self.stack.setCurrentIndex(index)
        title, subtitle = PAGE_HEADERS[index]
        self.page_title.setText(title)
        self.page_subtitle.setText(subtitle)
        self.page_subtitle.setVisible(bool(subtitle))
        for number, button in enumerate(self.nav_buttons):
            button.setChecked(number == index)
        self.nav_scroll.ensureWidgetVisible(self.nav_buttons[index], 0, 12)
