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
        sidebar.setFixedWidth(204)
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
            ("☀", "每日任务"),
            ("R", "巨兽集结"),
            ("◷", "定时启动"),
            ("☷", "任务编排"),
            ("≡", "运行日志"),
            ("i", "关于与安全"),
            ("榜", "备战积分"),
        ]
        for index, (glyph, text) in enumerate(nav_items):
            button = QPushButton(f"{glyph}    {text}")
            button.setObjectName("navButton")
            button.setFixedHeight(44)
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
        main_layout.setContentsMargins(22, 18, 22, 18)
        main_layout.setSpacing(12)
        top = QHBoxLayout()
        titles = QVBoxLayout()
        self.page_title = QLabel("设备中心")
        self.page_title.setObjectName("pageTitle")
        self.page_subtitle = QLabel("选择 MuMu 实例，确认画面后开始运行")
        self.page_subtitle.setObjectName("pageSubtitle")
        titles.addWidget(self.page_title)
        titles.addWidget(self.page_subtitle)
        top.addLayout(titles, 1)
        self.status_pill = QLabel("●  正在连接")
        self.status_pill.setObjectName("statusPill")
        top.addWidget(self.status_pill, 0, Qt.AlignmentFlag.AlignVCenter)
        main_layout.addLayout(top)
        device_bar = QHBoxLayout()
        device_bar.addWidget(self._field_label("当前手机"))
        self.device_combo = QComboBox()
        self.device_combo.setObjectName("deviceCombo")
        self.device_combo.setMinimumWidth(200)
        self.device_combo.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        self.device_combo.setMinimumContentsLength(16)
        self.device_combo.setAccessibleName("当前绑定手机")
        self.device_combo.currentIndexChanged.connect(self._device_changed)
        device_bar.addWidget(self.device_combo, 1)
        scan = QPushButton("↻  扫描")
        scan.setObjectName("ghostButton")
        scan.clicked.connect(lambda: self._run_async(self._connect_job))
        self.scan_button = scan
        device_bar.addWidget(scan)
        self.device_manager_button = QPushButton("多手机窗口")
        self.device_manager_button.setObjectName("secondaryButton")
        self.device_manager_button.clicked.connect(self._open_device_manager)
        device_bar.addWidget(self.device_manager_button)
        main_layout.addLayout(device_bar)

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
        hero = Card(name="hero")
        hero_layout = QHBoxLayout(hero)
        hero_layout.setContentsMargins(26, 22, 24, 22)
        hero_text = QVBoxLayout()
        kicker = QLabel("设备工作台 · 独立账号 · 并行运行")
        kicker.setObjectName("heroKicker")
        title = QLabel("每台手机，一个独立工作窗口")
        title.setObjectName("heroTitle")
        desc = QLabel("在“多手机窗口”中打开其他设备；设置与任务独立，切换页面不影响正在运行的流程。")
        desc.setObjectName("heroText")
        hero_text.addWidget(kicker)
        hero_text.addWidget(title)
        hero_text.addWidget(desc)
        hero_layout.addLayout(hero_text, 1)
        self.start_button = QPushButton("▶  联盟帮助")
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
        all_instances = QPushButton("管理多手机窗口")
        all_instances.setObjectName("secondaryButton")
        all_instances.clicked.connect(self._open_device_manager)
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
        note_text = QLabel("打开窗口不会启动任务。每台手机单独开始 / 停止；F8 停止所有窗口。请勿同时手动操作正在自动运行的手机。")
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
        content.addWidget(limits, 2)
        layout.addLayout(content)
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

        hero = Card(name="dailyTaskHero")
        hero_layout = QHBoxLayout(hero)
        hero_layout.setContentsMargins(28, 24, 26, 24)
        hero_text = QVBoxLayout()
        kicker = QLabel("每日任务 · 活跃度自动化")
        kicker.setObjectName("heroKicker")
        title = QLabel("自动领取奖励，并执行已验证的每日任务")
        title.setObjectName("heroTitle")
        desc = QLabel(
            "自动收取已完成奖励与活跃度宝箱；可执行已验证的采集、训练、建筑、联盟捐献、"
            "竞技场和宠物寻宝。宠物派遣消耗 10 体力；耗时操作自然完成，不使用钻石、钥匙、加速或购买。"
        )
        desc.setObjectName("heroText")
        desc.setWordWrap(True)
        hero_text.addWidget(kicker)
        hero_text.addWidget(title)
        hero_text.addWidget(desc)
        hero_layout.addLayout(hero_text, 1)
        actions = QVBoxLayout()
        self.daily_task_start_button = QPushButton("☀  开始每日任务自动化")
        self.daily_task_start_button.setObjectName("primaryButton")
        self.daily_task_start_button.clicked.connect(self._start_daily_rewards_flow)
        stop = QPushButton("■  停止")
        stop.setObjectName("dangerButton")
        stop.clicked.connect(self.stop_all)
        actions.addWidget(self.daily_task_start_button)
        actions.addWidget(stop)
        hero_layout.addLayout(actions)
        layout.addWidget(hero)

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
        all_instances = QPushButton("全部实例执行每日任务")
        all_instances.setObjectName("secondaryButton")
        all_instances.clicked.connect(lambda: self._start_all_instances("daily"))
        status_layout.addWidget(all_instances)
        layout.addWidget(status_card)

        content = QHBoxLayout()
        content.setSpacing(18)
        rules = Card()
        rules_layout = QVBoxLayout(rules)
        rules_layout.setContentsMargins(24, 22, 24, 24)
        rules_title = QLabel("固定安全边界")
        rules_title.setObjectName("sectionTitle")
        rules_text = QLabel(
            "① 仅确认主城“任务”入口后，最多点击一次进入每日任务。\n"
            "② 仅在每日任务页、活跃度条与绿色“领取”按钮同屏时收取奖励或宝箱。\n"
            "③ 仅执行已验证的日常路线；宠物派遣前记录账号状态，每个关键按钮需连续两帧确认。\n"
            "④ 不会点击商店、购买、钻石完成、钥匙招募、加速、无关战斗、非任务升级或未知弹窗。"
        )
        rules_text.setObjectName("noticeText")
        rules_text.setWordWrap(True)
        rules_layout.addWidget(rules_title)
        rules_layout.addSpacing(12)
        rules_layout.addWidget(rules_text)
        rules_layout.addStretch()
        content.addWidget(rules, 3)

        limits = Card(name="dailyAccountSettingsCard")
        limit_layout = QVBoxLayout(limits)
        limit_layout.setContentsMargins(24, 22, 24, 24)
        settings_header = QVBoxLayout()
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
        settings_header.addWidget(self.mining_level_button)
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
        for label, widget in (
            ("截图 / 检查间隔", self.daily_interval_spin),
            ("最长等待（0 = 不限）", self.daily_duration_spin),
        ):
            limit_layout.addWidget(self._field_label(label))
            limit_layout.addWidget(widget)
            limit_layout.addSpacing(10)
        limit_layout.addWidget(self.daily_guard_check)
        limit_layout.addStretch()
        content.addWidget(limits, 2)
        layout.addLayout(content)
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

        hero = Card(name="dailyTaskHero")
        hero_layout = QHBoxLayout(hero)
        hero_layout.setContentsMargins(28, 24, 26, 24)
        text = QVBoxLayout()
        kicker = QLabel("冰原巨兽 · 独立自动化")
        kicker.setObjectName("heroKicker")
        title = QLabel("自动发起 3 分钟集结并监控出征状态")
        title.setObjectName("heroTitle")
        desc = QLabel(
            "冰原巨兽 · 账号等级 · 3分钟 · 自选兵力或编组 · 同时集结数量可设。"
            "体力按最终出征页实际数值记账；0 上限表示不限制。"
        )
        desc.setObjectName("heroText")
        desc.setWordWrap(True)
        text.addWidget(kicker)
        text.addWidget(title)
        text.addWidget(desc)
        hero_layout.addLayout(text, 1)
        actions = QVBoxLayout()
        self.beast_rally_start_button = QPushButton("开始自动集结巨兽")
        self.beast_rally_start_button.setObjectName("primaryButton")
        self.beast_rally_start_button.clicked.connect(self._start_beast_rally_flow)
        stop = QPushButton("停止")
        stop.setObjectName("dangerButton")
        stop.clicked.connect(self.stop_all)
        actions.addWidget(self.beast_rally_start_button)
        separate = QPushButton("为当前账号打开独立窗口")
        separate.setObjectName("secondaryButton")
        separate.clicked.connect(self._open_selected_window)
        actions.addWidget(separate)
        all_instances = QPushButton("全部实例分别启动")
        all_instances.setObjectName("secondaryButton")
        all_instances.clicked.connect(lambda: self._start_all_instances("beast_rally"))
        actions.addWidget(all_instances)
        actions.addWidget(stop)
        hero_layout.addLayout(actions)
        layout.addWidget(hero)

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

        bounds = Card()
        bounds_layout = QVBoxLayout(bounds)
        bounds_layout.setContentsMargins(24, 22, 24, 24)
        heading = QLabel("严格操作边界")
        heading.setObjectName("sectionTitle")
        explanation = QLabel(
            "只识别并点击冰原巨兽链路中的唯一控件；不会点击自动加入、其他集结时长、"
            "体力购买、钻石、加速、其他战斗或未知弹窗。队列和归属需连续两张新截图确认。"
        )
        explanation.setObjectName("noticeText")
        explanation.setWordWrap(True)
        bounds_layout.addWidget(heading)
        bounds_layout.addWidget(explanation)
        layout.addWidget(bounds)
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
            "这是一个只通过 MuMu 自带 ADB 截图、识图和模拟点击工作的本地工具。\n\n"
            "• 不读取游戏内存，不修改 APK，不读取账号密码。\n"
            "• 每个窗口绑定一个独立 ADB 端口，同一实例带跨进程占用锁。\n"
            "• 游戏画面自动归一化；具体账号与分辨率仍需首次运行核验。\n"
            "• F8 是全局急停；普通停止按钮只停止当前窗口。\n\n"
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
            QPushButton#navButton {{ text-align: left; color: #93A4C0; background: transparent; border: none; border-radius: 9px; min-height: 0; padding: 8px 14px; font-weight: 600; }}
            QPushButton#navButton:hover {{ color: white; background: #172947; }}
            QPushButton#navButton:checked {{ color: white; background: #245FD0; }}
            QFrame#sidebarCard {{ background: #172947; border: 1px solid #233A60; border-radius: 12px; }}
            QLabel#sideCardTitle {{ color: #DCE8FB; font-weight: 700; }}
            QLabel#sideCardText {{ color: #8294B3; font-size: 11px; line-height: 1.4; }}
            QLabel#pageTitle {{ font-size: 26px; font-weight: 750; }}
            QLabel#pageSubtitle, QLabel#muted {{ color: {COLORS['muted']}; font-size: 12px; }}
            QLabel#statusPill {{ background: {COLORS['green_soft']}; color: #11865B; border-radius: 15px; padding: 8px 12px; font-weight: 700; }}
            QFrame#card, QFrame#noticeCard, QFrame#dailyTaskStatusCard {{ background: white; border: 1px solid {COLORS['border']}; border-radius: 14px; }}
            QFrame#hero, QFrame#dailyTaskHero {{ background: qlineargradient(x1:0,y1:0,x2:1,y2:1, stop:0 #183A73, stop:1 #2358B3); border-radius: 16px; }}
            QFrame#dailyAccountSettingsCard, QFrame#beastAccountSettingsCard {{ background: #F8FAFE; border: 1px solid #D8E3F5; border-radius: 14px; }}
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
        titles = [
            ("设备中心", "选择实例、确认画面并快速启动"),
            ("联盟帮助", "识图阈值与运行限制"),
            ("联盟红包", "只开启已确认的熔炉升级红包"),
            ("每日任务", "优先领取奖励，再执行当前账号已支持的日常流程"),
            ("巨兽集结", "冰原巨兽 · 账号等级 · 3分钟 · 自选兵力或编组 · 体力上限"),
            ("定时启动", "按手机预约开始时间 · 保存后仅触发一次"),
            ("任务编排", "组合点击、等待、返回和识图步骤"),
            ("运行日志", "每条记录都标注绑定的 ADB 端口"),
            ("关于与安全", "版本、兼容范围与账号风险"),
            ("备战积分", "录入榜单 · 账号快照 · 积分异动对比"),
        ]
        self.stack.setCurrentIndex(index)
        self.page_title.setText(titles[index][0])
        self.page_subtitle.setText(titles[index][1])
        for number, button in enumerate(self.nav_buttons):
            button.setChecked(number == index)
