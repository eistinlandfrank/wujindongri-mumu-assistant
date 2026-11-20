"""Per-account Polar Terror controls for the existing desktop worker and scheduler."""

from datetime import datetime, time, timedelta
import json
from pathlib import Path
from tempfile import TemporaryDirectory

from PySide6.QtCore import QDate, QSettings
from PySide6.QtWidgets import (
    QDateEdit, QFormLayout, QFrame, QHBoxLayout, QLabel, QLineEdit, QMessageBox,
    QPlainTextEdit, QPushButton, QVBoxLayout, QWidget,
)

import wjdr_schedule as schedules
from wjdr_backend import DeviceLease, _atomic_json_write
from wjdr_bear import ZONE, account_file, reconcile_dispatch, roster_settings
from wjdr_bear_war import WarBearFlow
from wjdr_fortress_ocr import FortressOcr


class BearUI:
    def _build_bear_page(self):
        body = QWidget()
        layout = QVBoxLayout(body)
        layout.setContentsMargins(0, 0, 0, 0)
        card = QFrame()
        card.setObjectName("card")
        form = QVBoxLayout(card)
        form.setContentsMargins(24, 22, 24, 22)
        title = QLabel("联盟战争集结")
        title.setObjectName("sectionTitle")
        form.addWidget(title)
        self.bear_account = QLabel("请先连接目标手机")
        self.bear_account.setObjectName("muted")
        form.addWidget(self.bear_account)
        fields = QFormLayout()
        self.bear_player = QLineEdit()
        self.bear_player.setMaxLength(40)
        self.bear_player.setPlaceholderText("用于确认出征后本人已进入集结名单")
        self.bear_player.setAccessibleName("我的游戏昵称")
        fields.addRow("我的游戏昵称", self.bear_player)
        self.bear_names = QPlainTextEdit()
        self.bear_names.setPlaceholderText("每行一个队长昵称")
        self.bear_names.setAccessibleName("打熊队长名单")
        self.bear_names.setFixedHeight(115)
        fields.addRow("集结队长", self.bear_names)
        now = datetime.now(ZONE)
        day = now.date() + timedelta(days=int(now.time() >= time(20, 30)))
        self.bear_date = QDateEdit(QDate(day.year, day.month, day.day))
        self.bear_date.setDisplayFormat("yyyy/MM/dd")
        self.bear_date.setCalendarPopup(True)
        self.bear_date.setAccessibleName("首场打熊日期")
        fields.addRow("首场日期", self.bear_date)
        form.addLayout(fields)
        notice = QLabel("边翻集结列表边找绿色「+」，只加入名单内队长的变异巨熊集结。\n"
                        "请从野外红旗或联盟战争的集结列表开始。每场 30 分钟，每 5 分钟最多出征 6 次。"
                        "预约按北京时间每两天 20:30 启动。"
                        "预约期间请保持当前账号的助手窗口打开、电脑和 MuMu 在线。")
        notice.setObjectName("noticeText")
        notice.setWordWrap(True)
        form.addWidget(notice)
        actions = QHBoxLayout()
        self.bear_start_button = QPushButton("立即监听")
        self.bear_start_button.setObjectName("primaryButton")
        self.bear_start_button.clicked.connect(self._start_bear_flow)
        actions.addWidget(self.bear_start_button)
        reserve = QPushButton("预约每两天 20:30")
        reserve.setObjectName("softButton")
        reserve.clicked.connect(self._add_bear_schedule)
        actions.addWidget(reserve)
        save_names = QPushButton("保存队长名单")
        save_names.setObjectName("softButton")
        save_names.clicked.connect(self._save_bear_names)
        actions.addWidget(save_names)
        actions.addStretch()
        form.addLayout(actions)
        reconcile = QPushButton("标记待核实出征已核对")
        reconcile.setObjectName("ghostButton")
        reconcile.clicked.connect(self._reconcile_bear_dispatch)
        form.addWidget(reconcile)
        layout.addWidget(card)
        layout.addStretch()
        return body

    def _show_bear_account(self, item):
        identity = str(item.get("identity", "")) if item else ""
        if identity == getattr(self, "_bear_form_identity", None):
            return
        self._bear_form_identity = identity
        self.bear_player.clear()
        self.bear_names.clear()
        if not identity:
            self.bear_account.setText("请先连接目标手机")
            return
        self.bear_account.setText(f"当前手机 #{item['index']} · {self._masked_account_label(identity)}")
        try:
            path = account_file(identity, "profile")
            if path.exists():
                data = json.loads(path.read_text("utf-8"))
                self.bear_player.setText(data["player"])
                self.bear_names.setPlainText("\n".join(data["names"]))
            else:
                self.bear_names.setPlainText(QSettings().value("bear/defaultNames", "", type=str))
        except (OSError, ValueError, KeyError, TypeError) as exc:
            self.log(f"读取打熊设置失败：{exc}")

    def _bear_account_binding(self):
        item = self.device_combo.currentData()
        if not self.adb or not item or item["device"] != self.adb.device:
            raise ValueError("请先选择并连接目标手机")
        identity = str(item.get("identity", ""))
        if identity != self._bear_form_identity:
            raise ValueError("手机正在切换，请等待连接完成")
        return item, identity

    def _save_bear_roster(self, identity):
        config = roster_settings(self.bear_names.toPlainText().splitlines(), self.bear_player.text())
        _atomic_json_write(account_file(identity, "profile"), config)
        return config

    def _save_bear_names(self):
        try:
            _, identity = self._bear_account_binding()
            config = self._save_bear_roster(identity)
            self.log(f"打熊名单已保存，共 {len(config['names'])} 位队长。")
        except (OSError, ValueError, KeyError, TypeError) as exc:
            QMessageBox.warning(self, "打熊名单未保存", str(exc))

    def _add_bear_schedule(self):
        try:
            item, identity = self._bear_account_binding()
            config = self._save_bear_roster(identity)
            day = self.bear_date.date().toPython()
            starts = datetime.combine(day, time(20, 30), tzinfo=ZONE)
            schedules.add_job(identity, item["device"], f"#{item['index']} · {self._masked_account_label(identity)}",
                              starts.timestamp(), task="bear", bear=config, path=self.schedule_path)
            self._refresh_schedule_table()
            self._show_page(5)
            self.log(f"已预约打熊，北京时间 {starts:%Y/%m/%d} 20:30 开始，每两天一次。")
        except (OSError, ValueError, KeyError, TypeError) as exc:
            QMessageBox.warning(self, "打熊预约未保存", str(exc))

    def _start_bear_flow(self, _checked=False, *, scheduled=None):
        try:
            item, identity = self._bear_account_binding()
            if scheduled:
                if scheduled["identity"] != identity:
                    raise ValueError("当前手机与打熊预约不符")
                data = scheduled["bear"]
                config = roster_settings(data["names"], data["player"])
            else:
                config = self._save_bear_roster(identity)
            path = account_file(identity, "ledger")
            target = self.adb.clone_for_device(item["device"])
        except (OSError, ValueError, KeyError, TypeError) as exc:
            if scheduled:
                self.log(f"打熊预约未启动：{exc}")
            else:
                QMessageBox.warning(self, "打熊未启动", str(exc))
            return

        def job():
            with TemporaryDirectory(prefix="wjdr-bear-ocr-") as tmp, FortressOcr(Path(tmp), self.stop_event) as ocr:
                WarBearFlow(target, self.stop_event, ocr, config, path,
                            lambda message: self._log_for_device(target.device, message),
                            profile=account_file(identity, "profile")).run()

        self._start_worker(target.device, job, expected_identity=identity)

    def _reconcile_bear_dispatch(self):
        try:
            _, identity = self._bear_account_binding()
            path = account_file(identity, "ledger")
            answer = QMessageBox.question(self, "核对打熊出征",
                "请先在游戏中核对上一次出征。标记为已核对后，这次提交仍会占用本场的 1 次额度。")
            if answer != QMessageBox.StandardButton.Yes:
                return
            lease = DeviceLease(identity)
            if not lease.acquire():
                raise ValueError("当前手机正在运行任务，请停止后再核对")
            try:
                message = "已标记出征已核对。" if reconcile_dispatch(path=path) else "没有待核实的打熊出征。"
            finally:
                lease.release()
            self.log(message)
        except (OSError, ValueError, KeyError, TypeError) as exc:
            QMessageBox.warning(self, "打熊出征核对", str(exc))
