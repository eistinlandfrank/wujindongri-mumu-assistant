"""Qt scheduling page; uses the existing account-bound Beast worker."""
import json
import time
from PySide6.QtCore import QDateTime, QTime, Qt
from PySide6.QtWidgets import (QWidget, QFrame, QScrollArea, QVBoxLayout, QHBoxLayout,
    QLabel, QDateTimeEdit, QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
    QAbstractItemView, QMessageBox)
import wjdr_schedule as schedules


class ScheduleUI:
    def _build_schedule_page(self):
        page = QScrollArea()
        page.setWidgetResizable(True)
        body = QWidget()
        self._set_window_background(page.viewport())
        self._set_window_background(body)
        page.setWidget(body)
        layout = QVBoxLayout(body)
        layout.setContentsMargins(0, 0, 8, 0)
        layout.setSpacing(16)
        card = QFrame()
        card.setObjectName("card")
        form = QVBoxLayout(card)
        form.setContentsMargins(24, 22, 24, 22)
        title = QLabel("预约巨兽集结 · 仅启动一次")
        title.setObjectName("sectionTitle")
        form.addWidget(title)
        self.schedule_account_label = QLabel("先在顶部选择目标手机，再保存预约")
        self.schedule_account_label.setObjectName("muted")
        form.addWidget(self.schedule_account_label)
        row = QHBoxLayout()
        row.addWidget(QLabel("开始时间"))
        tomorrow = QDateTime(QDateTime.currentDateTime().date().addDays(1), QTime(0, 0))
        self.schedule_time = QDateTimeEdit(tomorrow)
        self.schedule_time.setDisplayFormat("yyyy/MM/dd HH:mm:ss")
        self.schedule_time.setCalendarPopup(True)
        self.schedule_time.setAccessibleName("预约开始日期和时间（本机时间）")
        row.addWidget(self.schedule_time, 1)
        save = QPushButton("保存预约")
        save.setObjectName("primaryButton")
        save.clicked.connect(self._add_schedule)
        row.addWidget(save)
        form.addLayout(row)
        self.schedule_clock = QLabel("按本机时间触发")
        self.schedule_clock.setObjectName("muted")
        form.addWidget(self.schedule_clock)
        rules = QLabel("使用该账号巨兽设置：8级 / 3分钟 / 打野编组。\n"
            "请保持电脑不休眠、MuMu在线，并保持绑定该账号的助手窗口打开。关闭窗口或切到其他账号，不会由后台代为启动。\n"
            "到点已有任务运行则跳过；超过30秒未能触发则标记错过，不延迟补跑。保存预约不会立即出征。F8会取消所有尚未启动的预约。")
        rules.setObjectName("noticeText")
        rules.setWordWrap(True)
        form.addWidget(rules)
        layout.addWidget(card)
        history = QFrame()
        history.setObjectName("card")
        table_layout = QVBoxLayout(history)
        table_layout.setContentsMargins(20, 18, 20, 18)
        heading = QLabel("预约记录 · 所有手机")
        heading.setObjectName("sectionTitle")
        table_layout.addWidget(heading)
        self.schedule_table = QTableWidget(0, 5)
        self.schedule_table.setHorizontalHeaderLabels(["手机", "开始时间", "任务", "状态", "说明"])
        self.schedule_table.verticalHeader().hide()
        self.schedule_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.schedule_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.schedule_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.schedule_table.setMinimumHeight(200)
        self.schedule_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        table_layout.addWidget(self.schedule_table)
        actions = QHBoxLayout()
        for text, callback in (("取消选中预约", self._cancel_schedule), ("清除已结束记录", self._clear_schedule_history)):
            button = QPushButton(text)
            button.setObjectName("softButton")
            button.clicked.connect(callback)
            actions.addWidget(button)
        actions.addStretch()
        table_layout.addLayout(actions)
        layout.addWidget(history)
        return page

    def _refresh_schedule_table(self):
        jobs = schedules.read_jobs(self.schedule_path)
        signature = json.dumps(jobs, sort_keys=True)
        if signature == getattr(self, "_schedule_table_signature", None):
            return jobs
        self._schedule_table_signature = signature
        selected = self.schedule_table.currentItem()
        selected_id = selected.data(Qt.ItemDataRole.UserRole) if selected else None
        self.schedule_table.setRowCount(len(jobs))
        for row, job in enumerate(sorted(jobs, key=lambda j: j["run_at"], reverse=True)):
            values = [job["label"], QDateTime.fromSecsSinceEpoch(int(job["run_at"])).toString("MM/dd HH:mm:ss"),
                      "巨兽集结", schedules.STATES.get(job["state"], job["state"]), job["note"]]
            for col, value in enumerate(values):
                cell = QTableWidgetItem(value)
                cell.setData(Qt.ItemDataRole.UserRole, job["id"])
                cell.setToolTip(value)
                self.schedule_table.setItem(row, col, cell)
            if job["id"] == selected_id:
                self.schedule_table.selectRow(row)
        self.schedule_table.resizeRowsToContents()
        return jobs

    def _add_schedule(self):
        item = self.device_combo.currentData()
        if not item or not self.adb:
            QMessageBox.information(self, "定时启动", "请先选择并连接目标手机。")
            return
        try:
            identity = self._mining_identity_for_item(item) or ""
            label = f"#{item['index']} · {self._masked_account_label(identity)}"
            schedules.add_job(identity, item["device"], label,
                              self.schedule_time.dateTime().toSecsSinceEpoch(), path=self.schedule_path)
            self._refresh_schedule_table()
            self.log(f"已保存巨兽定时启动：{self.schedule_time.dateTime().toString('yyyy/MM/dd HH:mm:ss')}（本机时间）。")
        except Exception as exc:
            QMessageBox.warning(self, "预约未保存", str(exc))

    def _cancel_schedule(self):
        cell = self.schedule_table.currentItem()
        if cell:
            try:
                if not schedules.cancel_job(cell.data(Qt.ItemDataRole.UserRole), path=self.schedule_path):
                    QMessageBox.information(self, "定时启动", "只能取消尚未启动的预约。已运行的任务请在对应手机窗口点击停止。")
                self._refresh_schedule_table()
            except Exception as exc:
                QMessageBox.warning(self, "定时启动", str(exc))

    def _clear_schedule_history(self):
        try:
            schedules.clear_history(path=self.schedule_path)
            self._refresh_schedule_table()
        except Exception as exc:
            QMessageBox.warning(self, "定时启动", str(exc))

    def _schedule_tick(self):
        if self.closing.is_set():
            return
        self.schedule_clock.setText("当前本机时间：" + QDateTime.currentDateTime().toString("yyyy/MM/dd HH:mm:ss t"))
        item = self.device_combo.currentData()
        self.schedule_account_label.setText(
            f"目标：#{item['index']} · {item['device']} · {self._masked_account_label(item.get('identity', ''))}"
            if item else "先在顶部选择目标手机，再保存预约")
        try:
            jobs = self._refresh_schedule_table()
            if (self._schedule_checking or not self.adb or getattr(self, "_connecting", False)
                    or not any(j["state"] in {"pending", "claimed"} for j in jobs)):
                return
            identity = str(item.get("identity", "")) if item else ""
            job = schedules.claim_due(identity, busy=bool(self.worker and self.worker.is_alive()), path=self.schedule_path)
            if not job:
                return
            self._schedule_checking = True
            target = self.adb.clone_for_device()
            def verify():
                error = ""
                try:
                    deadline = time.monotonic() + 12
                    original_run = target._run
                    def bounded_read(args, **kwargs):
                        remaining = deadline - time.monotonic()
                        if remaining <= 0:
                            raise TimeoutError("定时启动设备核验超过12秒")
                        kwargs["timeout"] = min(float(kwargs.get("timeout", 3)), 3, remaining)
                        return original_run(args, **kwargs)
                    target._run = bounded_read
                    target.device_identities.clear()
                    if target.device_identity() != job["identity"]:
                        error = "当前手机身份与预约不符，未启动"
                    elif not target.foreground_is_game():
                        error = "游戏不在手机前台，未启动；请打开游戏后重新预约"
                except Exception as exc:
                    error = f"设备不可用，未启动：{exc}"
                self.signals.schedule_verified.emit(job, error)
            self._run_async(verify)
        except Exception as exc:
            self.schedule_clock.setText(f"定时器已暂停：{exc}")
            self.schedule_timer.stop()
            self.log(f"定时器安全暂停：{exc}")

    def _schedule_verified(self, job, error):
        self._schedule_checking = False
        item = self.device_combo.currentData()
        if not error and (self.closing.is_set() or not item or item.get("identity") != job["identity"]):
            error = "核验期间切换或关闭了账号窗口，未启动"
        if not error and time.time() > job["run_at"] + schedules.GRACE_SECONDS:
            error = "超过预约时间30秒，未启动；请重新预约"
        if not error and self.worker and self.worker.is_alive():
            error = "本窗口已有任务运行，未打断当前任务"
        try:
            if error:
                schedules.transition(job["id"], job["token"], "failed", error, path=self.schedule_path)
                self.log("定时启动未执行：" + error)
                return
            current = next((j for j in schedules.read_jobs(self.schedule_path) if j["id"] == job["id"]), {})
            if current.get("state") != "claimed" or current.get("token") != job["token"]:
                return
            self._launching_schedule = job
            self.log("定时已到，账号核验通过，开始巨兽集结流程。")
            self._start_beast_rally_flow()
            if not self.worker or not self.worker.is_alive():
                schedules.transition(job["id"], job["token"], "failed", "启动检查未通过，请查看运行日志", path=self.schedule_path)
        except Exception as exc:
            self.log(f"定时启动失败：{exc}；未重试启动")
        finally:
            self._launching_schedule = None
