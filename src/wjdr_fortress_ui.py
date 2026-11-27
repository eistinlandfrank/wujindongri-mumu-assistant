"""Fortress route controls for the currently bound account."""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime
from pathlib import Path
from tempfile import TemporaryDirectory
import time

from PySide6.QtCore import QDate, Qt, QTimer
from PySide6.QtWidgets import (
    QApplication, QAbstractItemView, QDateEdit, QDialog, QGridLayout, QHBoxLayout, QHeaderView,
    QCheckBox, QComboBox, QDialogButtonBox, QGroupBox, QInputDialog, QLabel, QMessageBox, QPushButton,
    QRadioButton, QScrollArea, QTableWidget, QTableWidgetItem, QPlainTextEdit, QSpinBox, QVBoxLayout, QWidget,
)

import wjdr_fortress as fortress
import wjdr_fortress_flow as flow
import wjdr_schedule as schedules
from wjdr_fortress_ocr import FortressOcr
from wjdr_backend import APP_NAME
from wjdr_mumu_ipc import RouteCapture
from wjdr_ui_components import set_style_property


HISTORY_PAGE_SIZE = 100


class FortressUI:
    def _build_fortress_page(self) -> QWidget:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        page = QWidget()
        self._set_window_background(scroll.viewport())
        self._set_window_background(page)
        scroll.setWidget(page)
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 6, 0)
        layout.setSpacing(12)
        heading = QHBoxLayout()
        self.fortress_context = QLabel("选择在线 MuMu 账号后可配置")
        self.fortress_context.setObjectName("muted")
        heading.addWidget(self.fortress_context, 1)
        self.fortress_history_button = QPushButton("历史记录")
        self.fortress_history_button.setObjectName("secondaryButton")
        self.fortress_history_button.clicked.connect(self._fortress_history)
        heading.addWidget(self.fortress_history_button)
        start = QPushButton("开始跑盟")
        start.setObjectName("primaryButton")
        start.clicked.connect(self._fortress_start_flow)
        self.fortress_start_button = start
        heading.addWidget(start)
        layout.addLayout(heading)
        self.fortress_progress = QLabel()
        self.fortress_progress.setObjectName("fortressProgress")
        self.fortress_progress.setWordWrap(True)
        self.fortress_notice = QLabel()
        self.fortress_notice.setWordWrap(True)
        self.fortress_notice.setTextFormat(Qt.TextFormat.PlainText)
        layout.addWidget(self.fortress_progress)
        layout.addWidget(self.fortress_notice)

        self.fortress_table = QTableWidget(0, 3)
        self.fortress_table.setMinimumHeight(190)
        self.fortress_table.setHorizontalHeaderLabels(["联盟短标签", "目标和打法", "钥匙返回状态"])
        header = self.fortress_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.fortress_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.fortress_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.fortress_table.cellDoubleClicked.connect(
            lambda row, column: self._fortress_edit_targets(row) if column == 1 else None)
        layout.addWidget(self.fortress_table, 1)

        edit = QHBoxLayout()
        self.fortress_editor_buttons = []
        for label, action in (("添加", lambda: self._fortress_add_row()), ("删除", self._fortress_remove),
                              ("选择目标", lambda: self._fortress_edit_targets(self.fortress_table.currentRow())),
                              ("上移", lambda: self._fortress_move(-1)), ("下移", lambda: self._fortress_move(1)),
                              ("填入示例", self._fortress_example), ("保存路线", self._fortress_save)):
            button = QPushButton(label)
            button.setObjectName("secondaryButton" if label == "保存路线" else "softButton")
            button.clicked.connect(action)
            if label == "保存路线":
                edit.addStretch()
            edit.addWidget(button)
            self.fortress_editor_buttons.append(button)
        layout.addLayout(edit)

        fields = QHBoxLayout()
        self.fortress_round_date = QDateEdit()
        self.fortress_round_date.setDisplayFormat("yyyy-MM-dd")
        self.fortress_round_date.setCalendarPopup(True)
        self.fortress_round_date.setAccessibleName("本轮开始日期")
        fields.addWidget(QLabel("本轮开始（北京时间）"))
        fields.addWidget(self.fortress_round_date)
        self.fortress_take_keys = QCheckBox("拿钥匙")
        self.fortress_take_keys.setChecked(True)
        fields.addWidget(self.fortress_take_keys)
        fields.addStretch()
        layout.addLayout(fields)

        time_fields = QHBoxLayout()
        time_fields.addWidget(QLabel("开始时刻"))
        self.fortress_round_time = []
        for unit, maximum in (("时", 23), ("分", 59), ("秒", 59)):
            spin = QSpinBox()
            spin.setRange(0, maximum)
            spin.setSuffix(f" {unit}")
            spin.setAccessibleName(f"开始时刻（{unit}）")
            spin.setMinimumWidth(68)
            self.fortress_round_time.append(spin)
            time_fields.addWidget(spin)
        time_fields.addStretch()
        layout.addLayout(time_fields)
        self._fortress_set_round_time(datetime.now(fortress.SHANGHAI))

        manual = QWidget()
        actions = QGridLayout(manual)
        actions.setContentsMargins(0, 0, 0, 2)
        self.fortress_action_buttons = [start]
        for index, (label, action) in enumerate((
            ("识别目标占领", lambda: self._fortress_occupation(False)),
            ("人工核对目标", lambda: self._fortress_occupation(True)),
            ("领取当前邮件", lambda: self._fortress_mail(True)),
            ("登记已领取邮件", lambda: self._fortress_mail(False)),
            ("登记单撞", self._fortress_solo),
            ("本站完成／下一站", self._fortress_advance),
            ("登记已返回", lambda: self._fortress_returned(False)),
            ("登记已领取钥匙", lambda: self._fortress_returned(True)),
            ("打开联盟管理", self._fortress_management),
            ("打开堡垒活动", lambda: self._fortress_open("activity")),
            ("打开联盟邮件", lambda: self._fortress_open("mail")),
            ("查本站／自动申请", lambda: self._fortress_apply()),
            ("退盟并去本站", lambda: self._fortress_apply(leave_current=True)),
            ("继续连点", self._fortress_continue_clicking),
        )):
            button = QPushButton(label)
            button.setObjectName("secondaryButton")
            button.clicked.connect(action)
            actions.addWidget(button, index // 4, index % 4)
            self.fortress_action_buttons.append(button)
        layout.addWidget(self._build_disclosure("人工核对与补录", manual))
        self.fortress_identity = None
        self.fortress_run = None
        self.fortress_take_keys.setChecked(True)
        self.fortress_timer = QTimer(self)
        self.fortress_timer.timeout.connect(self._fortress_refresh)
        self.fortress_timer.start(1000)
        self._fortress_refresh()
        return scroll

    def _fortress_add_row(self, alliance: str = "", targets: str = fortress.ALL_REGISTERED) -> None:
        index = self.fortress_table.rowCount()
        self.fortress_table.insertRow(index)
        self.fortress_table.setItem(index, 0, QTableWidgetItem(alliance))
        target_item = QTableWidgetItem(targets)
        target_item.setFlags(target_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        target_item.setToolTip(f"{targets}\n双击选择目标和打法")
        self.fortress_table.setItem(index, 1, target_item)
        status = QTableWidgetItem("待登记邮件")
        status.setFlags(status.flags() & ~Qt.ItemFlag.ItemIsEditable)
        self.fortress_table.setItem(index, 2, status)
        self.fortress_table.selectRow(index)

    def _fortress_edit_targets(self, row: int) -> None:
        if row < 0:
            self.fortress_notice.setText("请先添加或选择一个联盟站点。")
            return
        item = self.fortress_table.item(row, 1)
        invalid = ""
        try:
            saved = fortress.parse_targets(item.text())
        except ValueError as exc:
            saved = ()
            invalid = str(exc)
        current = {(target.kind, target.number): target.mode for target in saved}
        automatic_mode = current.get((fortress.ALL_REGISTERED, None))
        dialog = QDialog(self)
        dialog.setWindowTitle("选择目标和打法")
        dialog.resize(670, 365)
        self._set_window_background(dialog)
        layout = QVBoxLayout(dialog)

        automatic = QRadioButton("全部报名（默认）")
        specified = QRadioButton("指定编号")
        modes = QHBoxLayout()
        modes.addWidget(automatic)
        automatic_tactic = QComboBox()
        automatic_tactic.setAccessibleName("全部报名的打法")
        automatic_tactic.addItems([fortress.UNSPECIFIED_TACTIC, "单撞", "集结"])
        automatic_tactic.setCurrentText(automatic_mode or fortress.UNSPECIFIED_TACTIC)
        modes.addWidget(automatic_tactic)
        modes.addWidget(specified)
        modes.addStretch()
        layout.addLayout(modes)
        hint = QLabel("全部报名会等待该盟每个报名目标都显示蓝色占领。选指定编号时，可同时勾选堡垒和要塞。")
        hint.setWordWrap(True)
        layout.addWidget(hint)

        selectors = QWidget()
        selector_layout = QVBoxLayout(selectors)
        selector_layout.setContentsMargins(0, 0, 0, 0)
        choices = []
        for kind, limit in fortress.TARGET_LIMITS.items():
            group = QGroupBox(kind)
            grid = QGridLayout(group)
            numbers = list(range(1, limit + 1))
            if (kind, None) in current:
                numbers.append(None)
            for index, number in enumerate(numbers):
                line = QHBoxLayout()
                check = QCheckBox(f"{number}号" if number is not None else "唯一堡垒")
                check.setAccessibleName(f"{kind}{number}" if number is not None else "唯一堡垒")
                tactic = QComboBox()
                tactic.setAccessibleName(f"{check.accessibleName()}的打法")
                tactic.addItems(["单撞", "集结"])
                existing = current.get((kind, number))
                if existing:
                    check.setChecked(True)
                    tactic.setCurrentText(existing)
                tactic.setEnabled(check.isChecked())
                check.toggled.connect(tactic.setEnabled)
                line.addWidget(check)
                line.addWidget(tactic)
                grid.addLayout(line, index // 4, index % 4)
                choices.append((kind, number, check, tactic))
            selector_layout.addWidget(group)
        layout.addWidget(selectors)
        automatic.toggled.connect(automatic_tactic.setEnabled)
        specified.toggled.connect(selectors.setEnabled)
        automatic.setChecked(automatic_mode is not None)
        specified.setChecked(automatic_mode is None)
        automatic_tactic.setEnabled(automatic.isChecked())
        selectors.setEnabled(specified.isChecked())

        error = QLabel(invalid)
        error.setWordWrap(True)
        layout.addWidget(error)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText("确定")
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("取消")
        layout.addWidget(buttons)

        def accept() -> None:
            if automatic.isChecked():
                targets = fortress.target_text(fortress.ALL_REGISTERED, None, automatic_tactic.currentText())
            else:
                picked = {(kind, number): tactic.currentText()
                          for kind, number, check, tactic in choices if check.isChecked()}
                ordered = dict.fromkeys((*current, *picked))
                targets = "，".join(fortress.target_text(*key, picked[key])
                                    for key in ordered if key in picked)
                if not targets:
                    error.setText("请勾选至少一个堡垒或要塞。")
                    return
            item.setText(targets)
            item.setToolTip(f"{targets}\n双击选择目标和打法")
            dialog.accept()

        buttons.accepted.connect(accept)
        buttons.rejected.connect(dialog.reject)
        dialog.exec()

    def _fortress_remove(self) -> None:
        row = self.fortress_table.currentRow()
        if row >= 0:
            self.fortress_table.removeRow(row)

    def _fortress_history(self) -> None:
        identity = self.fortress_identity
        if not identity:
            return
        try:
            entries = fortress.load_history(identity)
        except (OSError, ValueError) as exc:
            self.fortress_notice.setText(str(exc))
            return

        dialog = QDialog(self)
        dialog.setWindowTitle(f"跑盟历史 · {self._masked_account_label(identity)}")
        dialog.resize(960, 690)
        self._set_window_background(dialog)
        layout = QVBoxLayout(dialog)
        summary = QLabel()
        layout.addWidget(summary)

        table = QTableWidget(0, 4)
        table.setHorizontalHeaderLabels(["本轮开始（北京时间）", "联盟路线", "已完成站点", "钥匙领取"])
        table.verticalHeader().hide()
        table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        header = table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        layout.addWidget(table, 2)

        layout.addWidget(QLabel("各站钥匙领取情况（北京时间）"))
        key_table = QTableWidget(0, 5)
        key_table.setAccessibleName("各站钥匙领取情况")
        key_table.setHorizontalHeaderLabels(["联盟", "领取状态", "领取确认时间", "返回时间", "返回截止"])
        key_table.verticalHeader().hide()
        key_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        key_table.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        key_header = key_table.horizontalHeader()
        key_header.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        key_header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        key_table.setMinimumHeight(208)
        layout.addWidget(key_table, 3)

        details = QPlainTextEdit()
        details.setAccessibleName("本轮站点和奖励邮件")
        details.setReadOnly(True)
        layout.addWidget(details, 2)
        controls = QHBoxLayout()
        newer = QPushButton("上一页")
        older = QPushButton("下一页")
        close = QPushButton("关闭")
        controls.addWidget(newer)
        controls.addWidget(older)
        controls.addStretch()
        controls.addWidget(close)
        layout.addLayout(controls)

        offset = 0

        def selected() -> None:
            row = table.currentRow()
            if row < 0:
                key_table.setRowCount(0)
                details.clear()
                return
            run = entries[offset + row]
            now = datetime.now(fortress.SHANGHAI)
            key_table.setRowCount(len(run["route"]))
            lines = []
            for station_row, stop in enumerate(run["route"]):
                tag = stop["alliance"]
                due = fortress.return_deadline(run, tag) if run.get("take_keys", True) else None
                values = (tag, fortress.key_collection_status(run, tag, now), run["keys"].get(tag, "—"),
                          run["returned"].get(tag, "—"), fortress.format_stamp(due) if due else "—")
                for column, value in enumerate(values):
                    cell = QTableWidgetItem(value)
                    cell.setToolTip(value)
                    key_table.setItem(station_row, column, cell)
                targets = "、".join(fortress.target_text(**target)
                                   for target in fortress.resolved_station(run, stop)["targets"])
                status = "已核对占领" if tag in run["occupied"] else "未登记占领"
                lines.append(f"[{tag}]  {targets}  ·  {status}")
                for stamp, state in sorted(run["mail"].get(tag, {}).items()):
                    status = "已领取" if state == "claimed" else "待核对"
                    lines.append(f"  胜利邮件  {stamp}  {status}")
                for target, receipt in sorted(run.get("key_mail", {}).get(tag, {}).items()):
                    status = "已领取" if receipt["state"] == "claimed" else "待核对"
                    lines.append(f"  钥匙邮件  {target}  {receipt['stamp']}  {status}")
            details.setPlainText("\n".join(lines))

        def show_page(start: int) -> None:
            nonlocal offset
            offset = start
            page = entries[offset:offset + HISTORY_PAGE_SIZE]
            table.blockSignals(True)
            table.setRowCount(len(page))
            for row, run in enumerate(page):
                keys = (f"已领取 {len(run['keys'])} / {len(run['route'])} 站"
                        if run["keys"] or run.get("take_keys", True) else "关闭")
                deferred = run.get("deferred_victory", {})
                values = (run["round_start"], " → ".join(stop["alliance"] for stop in run["route"]),
                          f"{run['index'] - len(deferred)} / {len(run['route'])}", keys)
                for column, value in enumerate(values):
                    cell = QTableWidgetItem(value)
                    cell.setToolTip(value)
                    table.setItem(row, column, cell)
            table.selectRow(0)
            table.blockSignals(False)
            selected()
            summary.setText(f"第 {offset + 1}–{offset + len(page)} 条，共 {len(entries)} 条"
                            if page else "当前账号暂无跑盟历史")
            newer.setEnabled(offset > 0)
            older.setEnabled(offset + len(page) < len(entries))

        table.itemSelectionChanged.connect(selected)
        newer.clicked.connect(lambda: show_page(offset - HISTORY_PAGE_SIZE))
        older.clicked.connect(lambda: show_page(offset + HISTORY_PAGE_SIZE))
        close.clicked.connect(dialog.accept)
        show_page(0)
        dialog.exec()

    def _fortress_move(self, offset: int) -> None:
        row = self.fortress_table.currentRow()
        dest = row + offset
        if row < 0 or not 0 <= dest < self.fortress_table.rowCount():
            return
        for column in range(3):
            previous = self.fortress_table.takeItem(dest, column)
            self.fortress_table.setItem(dest, column, self.fortress_table.takeItem(row, column))
            self.fortress_table.setItem(row, column, previous)
        self.fortress_table.selectRow(dest)

    def _fortress_example(self) -> None:
        if self.fortress_table.rowCount():
            answer = QMessageBox.question(self, APP_NAME, "用示例替换表格里正在编辑的路线？")
            if answer != QMessageBox.StandardButton.Yes:
                return
        self.fortress_table.setRowCount(0)
        for alliance, targets in (
            ("ZYZ", "堡垒3 单撞"), ("自助餐", "堡垒4 单撞"),
            ("BBK", "堡垒11 集结"), ("520", "要塞4 集结，堡垒8 集结"),
        ):
            self._fortress_add_row(alliance, targets)
        self.fortress_notice.setText("请核对示例联盟的短标签，再填写本轮开始时间。每站各有一个钥匙返回截止。")

    def _fortress_set_account(self, item: dict | None) -> None:
        identity = str((item or {}).get("identity") or "")
        if not identity.startswith("mumu:") or ":android:" not in identity:
            identity = None
        if identity == self.fortress_identity:
            return
        self.fortress_identity = identity
        self.fortress_table.setRowCount(0)
        self._fortress_set_round_time(datetime.now(fortress.SHANGHAI))
        self.fortress_notice.clear()
        self.fortress_run = None
        self.fortress_take_keys.setChecked(True)
        try:
            self.fortress_run = fortress.load_run(identity) if identity else None
        except (OSError, ValueError) as exc:
            self.fortress_notice.setText(str(exc))
        if self.fortress_run:
            self._fortress_show_route(self.fortress_run)
        self.fortress_context.setText(
            f"{self._masked_account_label(identity)} · 按已保存的表格顺序执行"
            if identity else "选择在线 MuMu 账号后可配置"
        )
        self._fortress_refresh()

    def _fortress_show_route(self, run: dict) -> None:
        self.fortress_table.setRowCount(0)
        self.fortress_take_keys.setChecked(run.get("take_keys", True))
        for stop in run["route"]:
            targets = "，".join(fortress.target_text(**target) for target in stop["targets"])
            self._fortress_add_row(stop["alliance"], targets)
        self._fortress_set_round_time(fortress.parse_stamp(run["round_start"]))

    def _fortress_set_round_time(self, stamp: datetime) -> None:
        self.fortress_round_date.setDate(QDate(stamp.year, stamp.month, stamp.day))
        for spin, value in zip(self.fortress_round_time, (stamp.hour, stamp.minute, stamp.second)):
            spin.setValue(value)

    def _fortress_round_stamp(self) -> datetime:
        date = self.fortress_round_date.date().toString("yyyy-MM-dd")
        hour, minute, second = (spin.value() for spin in self.fortress_round_time)
        return fortress.parse_stamp(f"{date} {hour:02d}:{minute:02d}:{second:02d}")

    def _fortress_store(self, run: dict) -> None:
        if not self.fortress_identity:
            raise ValueError("请先绑定已核验的 MuMu 账号")
        fortress.save_run(self.fortress_identity, self.fortress_run, run)
        self.fortress_run = run
        self._fortress_refresh()

    def _fortress_edited_route(self) -> tuple[fortress.Stop, ...]:
        rows = [(self.fortress_table.item(row, 0).text(), self.fortress_table.item(row, 1).text())
                for row in range(self.fortress_table.rowCount())]
        return fortress.parse_route(rows)

    def _fortress_save(self) -> None:
        try:
            route = self._fortress_edited_route()
            since = self._fortress_round_stamp()
            run = fortress.new_run(route, since)
            run["take_keys"] = self.fortress_take_keys.isChecked()
            previous = self.fortress_run
            if previous:
                run["applications"] = {
                    tag: deepcopy(record) for tag, record in previous.get("applications", {}).items()
                    if record["state"] != "joined" or previous["round_start"] == run["round_start"]
                }
            if previous and previous["round_start"] == run["round_start"]:
                if fortress.has_run_progress(previous):
                    locked = previous["index"]
                    if locked < len(previous["route"]):
                        tag = previous["route"][locked]["alliance"]
                        if tag in previous["occupied"] or tag in previous.get("resolved_targets", {}):
                            locked += 1
                    if previous["route"][:locked] != run["route"][:locked]:
                        raise ValueError("本轮已核对的站点需保留原位置和目标。可调整其余站点的顺序")
                    existing = deepcopy(previous)
                    existing["route"] = run["route"]
                    existing["take_keys"] = run["take_keys"]
                    self._fortress_store(existing)
                    self.fortress_notice.setText("路线已保存，本轮进度和截止时间已保留。")
                    return
            if previous and fortress.has_run_progress(previous):
                answer = QMessageBox.question(self, APP_NAME, "保存新一轮路线，并将本轮记录移入历史？")
                if answer != QMessageBox.StandardButton.Yes:
                    return
            self._fortress_store(run)
            self.fortress_notice.setText(f"路线已保存，本轮开始 {fortress.format_stamp(since)}（北京时间）。")
        except (OSError, ValueError, RuntimeError) as exc:
            self.fortress_notice.setText(str(exc))

    def _fortress_current_stop(self, run: dict) -> dict:
        if run["index"] >= len(run["route"]):
            raise ValueError("路线已走完，请查看返回联盟和截止时间")
        return fortress.resolved_station(run, run["route"][run["index"]])

    def _fortress_refresh(self) -> None:
        worker = getattr(self, "worker", None)
        busy = bool(worker and worker.is_alive())
        ready = bool(self.fortress_identity and not busy)
        run = self.fortress_run
        self.fortress_history_button.setEnabled(bool(self.fortress_identity))
        for widget in (self.fortress_table, self.fortress_round_date, *self.fortress_round_time,
                       self.fortress_take_keys, *self.fortress_editor_buttons):
            widget.setEnabled(ready)
        for button in self.fortress_action_buttons:
            button.setEnabled(ready and run is not None)
        now = datetime.now(fortress.SHANGHAI)
        upcoming = run and fortress.parse_stamp(run["round_start"]) > now
        self.fortress_start_button.setText("预约开跑" if upcoming else "开始跑盟")
        if not run:
            set_style_property(self.fortress_progress, "urgent", "false")
            self.fortress_progress.setText("按表格顺序跑联盟。胜利邮件请在邮件 → 联盟中逐封打开。")
            return
        queue = fortress.return_queue(run)
        timing = ("每站按最早胜利邮件的右上角发件时间计时。"
                  if run.get("take_keys", True) else "本轮关闭钥匙返回。")
        urgent = False
        if queue:
            deadline, tag = next(((due, alliance) for due, alliance in queue if due > now), queue[0])
            seconds = (deadline - now).total_seconds()
            remaining = "已到截止时间" if seconds <= 0 else f"剩余 {int(seconds) // 60:02d}:{int(seconds) % 60:02d}"
            timing = f"钥匙待登记 {len(queue)} 站 · {tag} 须在 {fortress.format_stamp(deadline)} 前返回 · {remaining}"
            urgent = seconds <= 300
        set_style_property(self.fortress_progress, "urgent", "true" if urgent else "false")
        for row in range(self.fortress_table.rowCount()):
            tag = fortress.compact(self.fortress_table.item(row, 0).text())
            status = self.fortress_table.item(row, 2)
            due = fortress.return_deadline(run, tag) if run.get("take_keys", True) else None
            if not run.get("take_keys", True):
                display = "关闭"
            elif tag in run["keys"]:
                display = "钥匙已领取"
            elif due is None:
                display = "待登记邮件"
            elif tag in run["returned"]:
                arrived = fortress.parse_stamp(run["returned"][tag])
                display = f"已返回 · {due:%H:%M:%S} 钥匙" if arrived < due else f"{arrived:%H:%M:%S} 返回（超时）"
            else:
                display = f"{due:%m-%d %H:%M:%S} 前返回" if due > now else f"{due:%m-%d %H:%M:%S} 已到时"
            if status.text() != display:
                status.setText(display)
        index = run["index"]
        if index >= len(run["route"]):
            deferred = run.get("deferred_victory", {})
            stage = f"待补领胜利邮件 {'、'.join(deferred)}" if deferred else "路线完成。"
            self.fortress_progress.setText(f"{stage}\n{timing}")
            return
        stop = self._fortress_current_stop(run)
        tag = stop["alliance"]
        targets = "、".join(fortress.target_text(**entry) for entry in stop["targets"])
        mails = run["mail"].get(tag, {})
        count = sum(state == "claimed" for state in mails.values())
        occupy = "占领已核对" if tag in run["occupied"] else "等待核对占领"
        site_due = fortress.return_deadline(run, tag) if run.get("take_keys", True) else None
        site_time = ""
        if site_due:
            label = f"本站最早发件 {min(mails)}" if mails else "参照其他账号的发件时间"
            site_time = f" · {label} · {fortress.format_stamp(site_due)} 前返回"
        solo = ""
        if run["last_solo"]:
            gap = fortress.parse_stamp(run["last_solo"]) + fortress.SOLO_INTERVAL - now
            if gap.total_seconds() > 0:
                seconds = int(gap.total_seconds()) + 1
                solo = f" · 单撞还需等 {seconds // 60:02d}:{seconds % 60:02d}"
        application = run.get("applications", {}).get(tag)
        approval = ""
        if application:
            if application["state"] == "waiting":
                seconds = max(0, int(application["started_at"] + fortress.APPLICATION_TIMEOUT - time.time() + 0.999))
                approval = f" · 核对入盟 {seconds // 60:02d}:{seconds % 60:02d}"
            elif application["state"] == "timed_out":
                approval = " · 连点超时" if application.get("method") == "direct" else " · 申请等待超时"
        self.fortress_progress.setText(
            f"第 {index + 1}/{len(run['route'])} 站  {tag} · {targets}\n"
            f"{occupy} · 已登记领取 {count} 封{solo}{approval}{site_time}\n{timing}"
        )

    def _fortress_worker(self, operation, *, scheduled=None) -> None:
        try:
            identity = self.fortress_identity
            if not identity or not self.adb or not self.adb.device or self.fortress_run is None:
                raise ValueError("请先为当前 MuMu 账号保存路线")
            target = self.adb.clone_for_device()
            run = deepcopy(self.fortress_run)
            self.fortress_notice.setText("正在读取当前账号的游戏画面…")

            def job():
                message = ""
                try:
                    if not target.foreground_is_game():
                        raise ValueError("请将游戏打开到所需页面")
                    with (TemporaryDirectory(prefix="wjdr-fortress-") as directory,
                          RouteCapture(target, int(identity.split(":")[1])) as capture):
                        def save():
                            fortress.save_run(identity, save.previous, run)
                            save.previous = deepcopy(run)
                        save.previous = deepcopy(run)
                        with FortressOcr(Path(directory), self.stop_event) as ocr:
                            message = operation(capture, run, ocr, save)
                except (OSError, ValueError, RuntimeError) as exc:
                    message = str(exc)
                    if scheduled:
                        schedules.transition(scheduled["id"], scheduled["token"], "failed",
                                             message, path=self.schedule_path)
                finally:
                    self.signals.fortress_result.emit(identity, target.device, message)

            self._start_worker(target.device, job, expected_identity=identity)
        except (OSError, ValueError, RuntimeError) as exc:
            self.fortress_notice.setText(str(exc))

    def _fortress_result(self, identity: str, serial: str, message: str) -> None:
        if self.fortress_identity != identity or not self.adb or self.adb.device != serial:
            return
        try:
            updated = fortress.load_run(identity)
        except (OSError, ValueError) as exc:
            self.fortress_notice.setText(str(exc))
            return
        if updated and (not self.fortress_run or updated["round_start"] != self.fortress_run["round_start"]):
            self._fortress_show_route(updated)
        self.fortress_run = updated
        self.fortress_notice.setText(message or "已停止，请核对当前游戏状态。")
        self._fortress_refresh()
        if message:
            self.log(f"堡垒跑联盟 · {message}")

    def _fortress_occupation(self, manual: bool) -> None:
        if manual and QMessageBox.question(
            self, APP_NAME, "当前画面里，本站每个编号及类型都已核对为本联盟的蓝色占领？"
        ) != QMessageBox.StandardButton.Yes:
            return

        def check(target, run, ocr, save):
            stop = self._fortress_current_stop(run)
            stop = flow.resolve_targets(target, ocr, self.stop_event, run, stop, save)
            observations = []
            registrations = []
            for _ in range(2):
                image = fortress.normalize_frame(target.screenshot(timeout=6))
                lines = ocr(image)
                observations.append(fortress.read_occupation(image, lines, ocr))
                registrations.append(fortress.registration_matches(image, lines, ocr, stop))
            if any(observed is None for observed in observations):
                raise ValueError("请打开常规活动 → 堡垒争夺，确保底部目标卡片完整可见")
            if observations[0] != observations[1]:
                raise ValueError("两次画面的占领状态不同，请等页面稳定后再检查")
            observed = observations[0]
            if not all(registrations):
                raise ValueError("请核对报名数量和全部目标卡片")
            if (not manual or stop.get("all_registered")) and not fortress.occupation_complete(observed, stop):
                readable = "、".join(f"{kind}{number}" for kind, number in sorted(observed)) or "暂无"
                raise ValueError(f"已读到蓝色占领：{readable}。请核对其余目标状态")
            if stop["alliance"] not in run["occupied"]:
                run["occupied"].append(stop["alliance"])
                save()
            return f"{stop['alliance']} 目标已核对。打开邮件 → 联盟，逐封核对本轮胜利邮件。"

        self._fortress_worker(check)

    def _fortress_mail(self, claim: bool) -> None:
        try:
            tag = self._fortress_current_stop(self.fortress_run)["alliance"]
            if tag not in self.fortress_run["occupied"]:
                raise ValueError("先核对本站全部目标的蓝色占领")
        except (TypeError, ValueError) as exc:
            self.fortress_notice.setText(str(exc))
            return
        verb = "领取并登记" if claim else "登记"
        if QMessageBox.question(
            self, APP_NAME, f"确认当前打开的胜利邮件属于 {tag} 本轮活动，并{verb}这封邮件？"
        ) != QMessageBox.StandardButton.Yes:
            return

        def collect(target, run, ocr, save):
            def record(mail, status):
                fortress.record_mail(run, tag, mail.stamp, status, datetime.now(fortress.SHANGHAI))
                save()
            result = fortress.collect_reward(target, ocr, self.stop_event, record, claim=claim)
            return f"{tag} 已登记领取 · 发件 {fortress.format_stamp(result.stamp)}"

        self._fortress_worker(collect)

    def _fortress_solo(self) -> None:
        try:
            run = deepcopy(self.fortress_run)
            stop = self._fortress_current_stop(run)
            if not any(entry["mode"] == "单撞" for entry in stop["targets"]):
                raise ValueError("本站配置为集结")
            now = datetime.now(fortress.SHANGHAI)
            if run["last_solo"] and now - fortress.parse_stamp(run["last_solo"]) < fortress.SOLO_INTERVAL:
                raise ValueError("距上次登记单撞不足 3 分钟")
            run["last_solo"] = fortress.format_stamp(now)
            self._fortress_store(run)
            self.fortress_notice.setText("已登记刚完成的单撞，3 分钟倒计时已开始。")
        except (OSError, ValueError, RuntimeError) as exc:
            self.fortress_notice.setText(str(exc))

    def _fortress_advance(self) -> None:
        try:
            run = deepcopy(self.fortress_run)
            stop = self._fortress_current_stop(run)
            tag = stop["alliance"]
            mails = run["mail"].get(tag, {})
            if tag not in run["occupied"] or "pending" in mails.values() or len(mails) < len(stop["targets"]):
                raise ValueError("请核对全部目标，并逐封登记对应胜利邮件的已领取状态")
            if QMessageBox.question(
                self, APP_NAME, f"已查完 {tag} 本轮胜利邮件，且最早的一封也已登记？"
            ) != QMessageBox.StandardButton.Yes:
                return
            run["index"] += 1
            self._fortress_store(run)
            now = datetime.now(fortress.SHANGHAI)
            urgent = [(due, alliance) for due, alliance in fortress.return_queue(run)
                      if 0 < (due - now).total_seconds() <= 300]
            if urgent:
                self.fortress_notice.setText(f"请优先返回 {urgent[0][1]}，并在游戏中核对钥匙奖励。")
            elif run["index"] < len(run["route"]):
                next_tag = self._fortress_current_stop(run)["alliance"]
                self.fortress_notice.setText(f"下一站 {next_tag}。请在游戏里切换联盟后核对占领。")
            elif run.get("take_keys", True):
                self.fortress_notice.setText("路线完成。请按各联盟的截止时间返回，逐站登记钥匙奖励。")
            else:
                self.fortress_notice.setText("路线完成。")
        except (OSError, ValueError, RuntimeError) as exc:
            self.fortress_notice.setText(str(exc))

    def _fortress_alliance_page(self, target, ocr):
        observations = []
        for _ in range(2):
            frame = target.screenshot(timeout=6)
            observations.append(fortress.read_alliance(ocr(fortress.normalize_frame(frame))))
        if not observations[0] or observations[0] != observations[1]:
            raise ValueError("请打开游戏的联盟主页，确保顶部联盟短标签清晰")
        return frame, observations[0]

    def _fortress_returned(self, keys: bool) -> None:
        if self.fortress_run and not self.fortress_run.get("take_keys", True):
            self.fortress_notice.setText("本轮关闭钥匙返回。")
            return
        if keys and QMessageBox.question(
            self, APP_NAME, "已在游戏中领取当前联盟本轮的钥匙奖励？请打开联盟主页核对标签。"
        ) != QMessageBox.StandardButton.Yes:
            return

        def verify(target, run, ocr, save):
            _, tag = self._fortress_alliance_page(target, ocr)
            due = fortress.return_deadline(run, tag)
            if due is None:
                raise ValueError(f"当前联盟 {tag} 暂无本轮胜利邮件记录")
            now = datetime.now(fortress.SHANGHAI)
            if keys:
                run["keys"][tag] = fortress.format_stamp(now)
                save()
                return f"{tag} 钥匙奖励已登记。"
            run["returned"][tag] = fortress.format_stamp(now)
            save()
            result = "已在截止前返回" if now < due else "已返回，超过 30 分钟截止"
            return f"{tag} {result}。"

        self._fortress_worker(verify)

    def _fortress_management(self) -> None:
        def open_settings(target, run, ocr, save):
            frame, tag = self._fortress_alliance_page(target, ocr)
            if not target.foreground_is_game() or self.stop_event.is_set():
                raise InterruptedError()
            fortress.tap_game_point(target, frame, (488, 1126))
            for _ in range(2):
                frame = target.screenshot(timeout=6)
                if fortress.is_alliance_settings(ocr(fortress.normalize_frame(frame))):
                    return f"已打开 {tag} 的联盟管理。"
            raise ValueError("联盟管理页面未确认，请核对游戏画面")

        self._fortress_worker(open_settings)

    def _fortress_open(self, entry: str) -> None:
        def open_page(target, run, ocr, save):
            if entry == "activity":
                fortress.open_fortress_activity(target, ocr, self.stop_event)
                return "已打开堡垒争夺，可识别蓝色占领。"
            _, lines = fortress.open_game_screen(target, ocr, self.stop_event, entry)
            stamps = fortress.visible_reward_stamps(
                lines, fortress.parse_stamp(run["round_start"]), datetime.now(fortress.SHANGHAI))
            if not stamps:
                return "已打开联盟邮件。请检查本轮的胜利邮件。"
            return (
                f"当前画面有 {len(stamps)} 封本轮时间范围内的胜利邮件，"
                f"最早可见 {fortress.format_stamp(stamps[0])}。逐封打开详情，核对联盟和发件时间。"
            )

        self._fortress_worker(open_page)

    def _fortress_apply(self, *, leave_current: bool = False) -> None:
        def apply_and_watch(target, run, ocr, save):
            tag = self._fortress_current_stop(run)["alliance"]
            identity = target.device_identity()
            result = fortress.enter_route_alliance(
                target, ocr, self.stop_event, run, tag, save, leave_current=leave_current,
                notify=lambda message: self.signals.fortress_result.emit(identity, target.device, message),
                on_timeout=lambda message: self.signals.fortress_application_timeout.emit(identity, target.device, message),
            )
            return f"{result.message}，可以核对本站占领。" if result.joined else result.message

        self._fortress_worker(apply_and_watch)

    def _fortress_application_timeout(self, identity: str, serial: str, message: str) -> None:
        if self.fortress_identity != identity or not self.adb or self.adb.device != serial:
            return
        clicking = "连点时间已到" in message
        title = "连点超时" if clicking else "联盟申请等待超时"
        dialog = QMessageBox(QMessageBox.Icon.Warning, title, message,
                             QMessageBox.StandardButton.Ok, self)
        if clicking:
            resume = dialog.addButton("继续连点…", QMessageBox.ButtonRole.ActionRole)
            tag = message.partition("]")[0].lstrip("[")
            dialog.buttonClicked.connect(
                lambda button: QTimer.singleShot(
                    0, lambda: self._fortress_continue_clicking(
                        tag=tag, continue_flow="入盟后续跑本轮" in message)) if button is resume else None)
        dialog.setTextFormat(Qt.TextFormat.PlainText)
        dialog.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, True)
        dialog.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        dialog.open()
        dialog.raise_()
        dialog.activateWindow()
        QApplication.alert(dialog)

    def _fortress_start_flow(self, *, scheduled=None) -> None:
        try:
            run = self.fortress_run
            identity = self.fortress_identity
            if not run or not identity or not self.adb or not self.adb.device:
                raise ValueError("请先为当前 MuMu 账号保存路线")
            stamp = fortress.parse_stamp(run["round_start"])
            if scheduled:
                if fortress.load_run(identity) != run:
                    raise ValueError("预约后路线或时间已改动，请重新预约")
                if "fortress_take_keys" in scheduled:
                    stamp = datetime.fromtimestamp(scheduled["run_at"], fortress.SHANGHAI)
                    fortress.run_from_schedule(run, scheduled)
                elif stamp.timestamp() != scheduled["run_at"] or run["route"] != scheduled["route"]:
                    raise ValueError("预约后路线或时间已改动，请重新预约")
            else:
                edited = fortress.new_run(self._fortress_edited_route(), self._fortress_round_stamp())
                if (edited["round_start"] != run["round_start"] or edited["route"] != run["route"]
                        or self.fortress_take_keys.isChecked() != run.get("take_keys", True)):
                    raise ValueError("路线、开始时间或拿钥匙设置有改动，请先保存路线")
                if stamp > datetime.now(fortress.SHANGHAI):
                    label = f"#{identity.split(':')[1]} · {self._masked_account_label(identity)}"
                    schedules.add_job(identity, self.adb.device, label, stamp.timestamp(),
                                      task="fortress_route", route=run["route"], path=self.schedule_path)
                    self._refresh_schedule_table()
                    self.fortress_notice.setText(
                        f"已预约 {fortress.format_stamp(stamp)}（北京时间），请保持此账号窗口打开。")
                    return
                if any(job["identity"] == identity and job["task"] == "fortress_route"
                       and job["run_at"] == stamp.timestamp() and job["state"] in {"pending", "claimed"}
                       for job in schedules.read_jobs(self.schedule_path)):
                    raise ValueError("本轮预约正在启动，请查看定时启动记录")
        except (OSError, ValueError, RuntimeError) as exc:
            self.fortress_notice.setText(str(exc))
            self.log(f"堡垒跑联盟 · {exc}")
            return

        def auto(target, run, ocr, save):
            if scheduled:
                if "fortress_take_keys" in scheduled:
                    planned = fortress.run_from_schedule(run, scheduled)
                    if planned is not run:
                        run.clear()
                        run.update(planned)
                flow.claim_scheduled_start(run, stamp, save)
                self.signals.fortress_result.emit(identity, target.device,
                                                  f"{fortress.format_stamp(stamp)} 预约已启动，正在核对首站")
            return flow.run_route(
                target, ocr, self.stop_event, run, save, rate=100,
                notify=lambda message: self.signals.fortress_result.emit(identity, target.device, message),
                on_timeout=lambda message: self.signals.fortress_application_timeout.emit(
                    identity, target.device, message + " 入盟后续跑本轮。"),
            )

        self._fortress_worker(auto, scheduled=scheduled)

    def _fortress_continue_clicking(self, *, tag=None, continue_flow=False) -> None:
        try:
            if not self.fortress_run:
                raise ValueError("请先保存路线")
            run = self.fortress_run
            if tag is not None:
                if tag not in {stop["alliance"] for stop in run["route"]}:
                    raise ValueError("超时提示对应的联盟已不在本轮路线")
            elif run["index"] < len(run["route"]):
                tag = self._fortress_current_stop(run)["alliance"]
            else:
                row = self.fortress_table.currentRow()
                if not 0 <= row < len(run["route"]):
                    raise ValueError("请先选择要继续连点的联盟")
                tag = run["route"][row]["alliance"]
            kind, ok = QInputDialog.getItem(
                self, "继续连点", f"[{tag}] 加入连点停止方式", ["定时停止", "不限时"], 0, False)
            if not ok:
                return
            duration = None
            if kind == "定时停止":
                minutes, ok = QInputDialog.getInt(self, "连点时长", "分钟", 3, 1, 1440)
                if not ok:
                    return
                duration = minutes * 60
            rate, ok = QInputDialog.getItem(
                self, "连点速度", f"[{tag}] 每秒点击次数", ["100", "10"], 0, False)
            if not ok:
                return
            identity = self.fortress_identity

            def click_and_watch(target, active_run, ocr, save):
                result = fortress.run_rapid_join(
                    target, ocr, self.stop_event, active_run, tag, save, rate=int(rate), duration=duration,
                    notify=lambda message: self.signals.fortress_result.emit(identity, target.device, message),
                    on_timeout=lambda message: self.signals.fortress_application_timeout.emit(
                        identity, target.device, message + (" 入盟后续跑本轮。" if continue_flow else "")),
                )
                due = fortress.return_deadline(active_run, tag)
                if result.joined and due and tag not in active_run["keys"] and tag not in active_run["returned"]:
                    now = datetime.now(fortress.SHANGHAI)
                    if now < due:
                        active_run["returned"][tag] = fortress.format_stamp(now)
                        save()
                if result.joined and continue_flow:
                    return flow.run_route(
                        target, ocr, self.stop_event, active_run, save, rate=int(rate),
                        notify=lambda message: self.signals.fortress_result.emit(identity, target.device, message),
                        on_timeout=lambda message: self.signals.fortress_application_timeout.emit(
                            identity, target.device, message + " 入盟后续跑本轮。"),
                    )
                return result.message

            self._fortress_worker(click_and_watch)
        except (OSError, ValueError, RuntimeError) as exc:
            self.fortress_notice.setText(str(exc))
