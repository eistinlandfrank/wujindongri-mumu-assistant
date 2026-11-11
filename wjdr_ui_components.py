"""Reusable Qt widgets and settings dialogs for the desktop frontend."""

from __future__ import annotations
from PySide6.QtCore import (
    QObject,
    QPoint,
    QRect,
    Qt,
    Signal,
)
from PIL import Image
from PySide6.QtGui import (
    QColor,
    QFont,
    QImage,
    QPainter,
    QPainterPath,
    QPalette,
    QPen,
)
from PySide6.QtWidgets import (
    QButtonGroup,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QRadioButton,
    QSizePolicy,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)
from wjdr_backend import (
    APP_NAME,
    BeastRallyProfile,
    MiningLevelProfile,
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
    schedule_verified = Signal(object, str)
    log = Signal(str)
    status = Signal(str, str)
    devices = Signal(object, str)
    image = Signal(object)
    running = Signal(bool, str)
    clicks = Signal(int)
    red_packet_state = Signal(str)
    daily_task_state = Signal(str)
    beast_rally_state = Signal(str)
    score_ocr = Signal(object)
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


class LightSettingsDialog(QDialog):
    """Readable account settings even when Windows supplies a dark palette."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        palette = QPalette()
        for role, color in {
            QPalette.ColorRole.Window: "#F5F8FD",
            QPalette.ColorRole.WindowText: "#233247",
            QPalette.ColorRole.Base: "#FFFFFF",
            QPalette.ColorRole.AlternateBase: "#EDF2FA",
            QPalette.ColorRole.Text: "#233247",
            QPalette.ColorRole.Button: "#FFFFFF",
            QPalette.ColorRole.ButtonText: "#233247",
            QPalette.ColorRole.Highlight: "#245FD0",
            QPalette.ColorRole.HighlightedText: "#FFFFFF",
            QPalette.ColorRole.ToolTipBase: "#FFFFFF",
            QPalette.ColorRole.ToolTipText: "#233247",
        }.items():
            palette.setColor(role, QColor(color))
        for role in (QPalette.ColorRole.Text, QPalette.ColorRole.WindowText,
                     QPalette.ColorRole.ButtonText):
            palette.setColor(QPalette.ColorGroup.Disabled, role, QColor("#65748A"))
        self.setPalette(palette)
        self.setAutoFillBackground(True)
        self.setStyleSheet("""
            QDialog { background: #F5F8FD; color: #233247; }
            QLabel, QRadioButton { color: #233247; background: transparent; }
            QLabel#muted, QLabel#mutedLabel { color: #52627A; }
            QLabel#noticeText { color: #705022; }
            QSpinBox { background: #FFFFFF; color: #233247;
                       border: 1px solid #B8C7DC; border-radius: 6px; padding: 8px; }
            QSpinBox:disabled { background: #EDF2FA; color: #65748A; }
            QPushButton { background: #FFFFFF; color: #233247;
                          border: 1px solid #B8C7DC; border-radius: 6px;
                          min-height: 34px; padding: 0 18px; }
            QPushButton:hover { background: #E6EEFC; border-color: #245FD0; }
            QPushButton:default { background: #245FD0; color: #FFFFFF; }
        """)


class MiningLevelSettingsDialog(LightSettingsDialog):
    """Edit exactly one stable Android account's mining level mode."""

    def __init__(
        self,
        account_label: str,
        device_label: str,
        profile: MiningLevelProfile,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(f"采矿等级设置 — {account_label}")
        self.setModal(True)
        self.setMinimumWidth(520)

        layout = QVBoxLayout(self)
        title = QLabel(f"当前账号：{account_label}")
        title.setObjectName("dialogTitle")
        device = QLabel(f"ADB：{device_label}")
        device.setObjectName("mutedLabel")
        explanation = QLabel("手动与自动只能选择一个；切换账号后读取该账号自己的设置。")
        explanation.setWordWrap(True)
        layout.addWidget(title)
        layout.addWidget(device)
        layout.addWidget(explanation)

        self.mode_group = QButtonGroup(self)
        self.mode_group.setExclusive(True)
        self.auto_radio = QRadioButton("自动识别（地球 → 小房子 → 绿色城堡）")
        self.manual_radio = QRadioButton("手动指定（直接采矿，不点地球）")
        self.mode_group.addButton(self.auto_radio)
        self.mode_group.addButton(self.manual_radio)
        layout.addWidget(self.auto_radio)
        layout.addWidget(self.manual_radio)

        level_row = QHBoxLayout()
        level_row.addSpacing(28)
        level_row.addWidget(QLabel("手动等级"))
        self.manual_level_spin = QSpinBox()
        self.manual_level_spin.setRange(1, 9)
        self.manual_level_spin.setValue(profile.manual_level)
        self.manual_level_spin.setSuffix(" 级")
        level_row.addWidget(self.manual_level_spin)
        level_row.addStretch()
        layout.addLayout(level_row)

        if profile.mode == "manual":
            self.manual_radio.setChecked(True)
        else:
            self.auto_radio.setChecked(True)
        self.manual_level_spin.setEnabled(self.manual_radio.isChecked())
        self.manual_radio.toggled.connect(self.manual_level_spin.setEnabled)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save
            | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def profile(self) -> MiningLevelProfile:
        mode = "manual" if self.manual_radio.isChecked() else "auto"
        return MiningLevelProfile(mode, self.manual_level_spin.value())


class BeastRallySettingsDialog(LightSettingsDialog):
    """Edit one account's Icefield Beast level and daily stamina cap."""

    def __init__(
        self,
        account_label: str,
        device: str,
        profile: BeastRallyProfile,
        spent_today: int,
        parent: QWidget | None = None,
        *, uncertain_today: int = 0,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("自动集结巨兽设置")
        self.setModal(True)
        self.setMinimumWidth(500)
        layout = QVBoxLayout(self)
        title = QLabel("冰原巨兽自动集结")
        title.setObjectName("sectionTitle")
        account = QLabel(f"{account_label}  ·  ADB {device}")
        account.setObjectName("muted")
        layout.addWidget(title)
        layout.addWidget(account)
        layout.addSpacing(12)

        self.level_spin = QSpinBox()
        self.level_spin.setRange(1, 30)
        self.level_spin.setValue(int(profile.beast_level))
        self.level_spin.setSuffix(" 级")
        self.stamina_limit_spin = QSpinBox()
        self.stamina_limit_spin.setRange(0, 1_000_000)
        self.stamina_limit_spin.setValue(int(profile.stamina_limit))
        self.stamina_limit_spin.setSuffix(" 体力（0 = 不限）")
        form = QGridLayout()
        form.addWidget(QLabel("巨兽等级"), 0, 0)
        form.addWidget(self.level_spin, 0, 1)
        form.addWidget(QLabel("每日消耗上限（普通模式）"), 1, 0)
        form.addWidget(self.stamina_limit_spin, 1, 1)
        form.addWidget(QLabel("今日已确认消耗"), 2, 0)
        form.addWidget(QLabel(str(max(0, int(spent_today)))), 2, 1)
        form.addWidget(QLabel("待核实消耗（计入上限）"), 3, 0)
        form.addWidget(QLabel(str(max(0, int(uncertain_today)))), 3, 1)
        self.troop_mode_combo = QComboBox()
        self.troop_mode_combo.addItem("手动设置兵力", "manual")
        self.troop_mode_combo.addItem("已保存编组", "formation")
        self.troop_mode_combo.setCurrentIndex(0 if profile.troop_mode == "manual" else 1)
        form.addWidget(QLabel("出征方式"), 4, 0)
        form.addWidget(self.troop_mode_combo, 4, 1)
        self.troop_spins = []
        for row, (label, value) in enumerate((("盾兵", profile.shield_count), ("矛兵", profile.spear_count), ("射手", profile.bow_count)), 5):
            spin = QSpinBox()
            spin.setRange(0, 999999)
            spin.setValue(value)
            form.addWidget(QLabel(label), row, 0)
            form.addWidget(spin, row, 1)
            self.troop_spins.append(spin)
        self.formation_combo = QComboBox()
        self.formation_combo.addItem("打野（游戏内已保存）", "打野")
        form.addWidget(QLabel("已保存编组"), 8, 0)
        form.addWidget(self.formation_combo, 8, 1)
        self.concurrent_spin = QSpinBox()
        self.concurrent_spin.setRange(1, 10)
        self.concurrent_spin.setValue(profile.max_concurrent_rallies)
        self.concurrent_spin.setSuffix(" 支")
        form.addWidget(QLabel("同时集结上限"), 9, 0)
        form.addWidget(self.concurrent_spin, 9, 1)
        self.run_mode_combo = QComboBox()
        self.run_mode_combo.addItem("普通模式", "normal")
        self.run_mode_combo.addItem("极速模式（单盾坐标复用）", "fast")
        self.run_mode_combo.setCurrentIndex(1 if profile.run_mode == "fast" else 0)
        form.addWidget(QLabel("运行模式"), 10, 0)
        form.addWidget(self.run_mode_combo, 10, 1)
        def update_mode() -> None:
            manual = self.troop_mode_combo.currentData() == "manual"
            for spin in self.troop_spins:
                spin.setEnabled(manual)
            self.formation_combo.setEnabled(not manual)
        self.troop_mode_combo.currentIndexChanged.connect(update_mode)
        update_mode()
        layout.addLayout(form)
        warning = QLabel(
            "默认8级、3分钟。集结结束后有空闲队伍时自动补开；实际出征不超过游戏可用队伍。手动兵力与保存编组二选一；编组识别支持游戏内名为“打野”的编组。"
        )
        warning.setObjectName("noticeText")
        warning.setWordWrap(True)
        layout.addWidget(warning)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save
            | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._accept_valid)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _accept_valid(self) -> None:
        if self.troop_mode_combo.currentData() == "manual" and not sum(s.value() for s in self.troop_spins):
            QMessageBox.warning(self, APP_NAME, "手动出征至少需要一个兵。")
            return
        if (self.run_mode_combo.currentData() == "fast"
                and (self.troop_mode_combo.currentData() != "manual"
                     or tuple(s.value() for s in self.troop_spins) != (1, 0, 0))):
            QMessageBox.warning(self, APP_NAME, "极速模式使用手动 1 盾兵、0 矛兵、0 射手；其他配置可选普通模式。")
            return
        self.accept()

    def profile(self) -> BeastRallyProfile:
        return BeastRallyProfile(
            beast_level=self.level_spin.value(),
            stamina_limit=self.stamina_limit_spin.value(),
            troop_mode=self.troop_mode_combo.currentData(),
            shield_count=self.troop_spins[0].value(), spear_count=self.troop_spins[1].value(),
            bow_count=self.troop_spins[2].value(), formation_name=self.formation_combo.currentData(),
            max_concurrent_rallies=self.concurrent_spin.value(),
            run_mode=self.run_mode_combo.currentData(),
        )
