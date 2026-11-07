"""Preparation leaderboard snapshot editor, import and comparison page."""
from __future__ import annotations

import subprocess
import tempfile
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QAbstractItemView, QComboBox, QFileDialog, QGridLayout, QHBoxLayout,
    QHeaderView, QInputDialog, QLabel, QMessageBox, QPushButton, QTabWidget,
    QTableWidget, QTableWidgetItem, QTextEdit, QVBoxLayout, QWidget)

import wjdr_scoreboard as scores
from wjdr_backend import APP_NAME, CREATE_NO_WINDOW, resource_path


class ScoreboardUI:
    def _build_scoreboard_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        intro = QLabel("选择当前手机；程序会从已识别的页面进入备战总榜。可识别当前画面或连续采集（F8 停止）；核对后保存快照，即可比较任意两版。")
        intro.setWordWrap(True)
        layout.addWidget(intro)
        actions = QGridLayout()
        for index, (label, slot) in enumerate((("新建", self._score_new_editor), ("导入 Excel / CSV", self._score_import), ("识别当前画面", self._score_capture), ("连续采集", self._score_capture_many), ("恢复采集草稿", self._score_recover_draft),
                            ("添加一行", self._score_add_row), ("删除选中行", self._score_delete_rows),
                            ("保存快照", self._score_save))):
            button = QPushButton(label)
            button.setObjectName("secondaryButton")
            button.clicked.connect(slot)
            actions.addWidget(button, index // 4, index % 4)
        layout.addLayout(actions)
        self.score_info = QLabel("快照按账号保存。请逐项核对识别结果；未采集完整的快照会标为不完整。")
        self.score_info.setWordWrap(True)
        layout.addWidget(self.score_info)
        self.score_tabs = QTabWidget()
        self.score_tabs.setStyleSheet("QTabBar::tab { background: #E7EDF7; color: #233857; padding: 8px 14px; border: 0; } QTabBar::tab:selected { background: white; color: #1D58C8; font-weight: 600; } QTabWidget::pane { border: 1px solid #D9E3F0; background: white; }")
        self.score_table = QTableWidget(0, 5)
        self.score_table.setHorizontalHeaderLabels(["排名", "国家", "联盟", "玩家昵称", "积分"])
        self.score_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.score_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.score_tabs.addTab(self.score_table, "快照编辑")
        self.score_ocr = QTextEdit()
        self.score_ocr.setReadOnly(True)
        self.score_tabs.addTab(self.score_ocr, "画面识别结果")
        self.score_diff = QTableWidget(0, 7)
        self.score_diff.setHorizontalHeaderLabels(["国家", "联盟", "玩家昵称", "原积分", "新积分", "异动", "新排名"])
        self.score_diff.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.score_diff.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.score_tabs.addTab(self.score_diff, "积分异动")
        self.score_unmatched = QTableWidget(0, 6)
        self.score_unmatched.setHorizontalHeaderLabels(["所在快照", "排名", "国家", "联盟", "玩家昵称", "积分"])
        self.score_unmatched.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.score_unmatched.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.score_tabs.addTab(self.score_unmatched, "未匹配")
        layout.addWidget(self.score_tabs, 1)
        choices = QHBoxLayout()
        self.score_old = QComboBox()
        self.score_new = QComboBox()
        choices.addWidget(QLabel("基准快照"))
        choices.addWidget(self.score_old, 1)
        choices.addWidget(QLabel("对比快照"))
        choices.addWidget(self.score_new, 1)
        for label, slot in (("刷新快照", self._score_refresh), ("载入基准编辑", self._score_load_old),
                            ("比较异动", self._score_compare)):
            button = QPushButton(label)
            button.setObjectName("secondaryButton")
            button.clicked.connect(slot)
            choices.addWidget(button)
        layout.addLayout(choices)
        self.score_editor_identity = None
        self.score_has_unreviewed_ocr = False
        return page

    def _score_new_editor(self):
        try:
            identity = self._score_identity()
            if self.score_table.rowCount() and QMessageBox.question(self, APP_NAME, "清空当前编辑内容并新建快照？") != QMessageBox.StandardButton.Yes:
                return
            self._score_put_rows([], identity)
        except Exception as exc:
            self._score_error(exc)

    def _score_identity(self):
        if not self.adb or not self.adb.device:
            raise ValueError("请先连接并选择手机账号。")
        identity = self.adb.device_identity(self.adb.device)
        scores.account_dir(identity)
        return identity

    def _score_error(self, exc):
        QMessageBox.warning(self, APP_NAME, str(exc))

    def _score_put_rows(self, rows, identity):
        self.score_editor_identity = identity
        self.score_has_unreviewed_ocr = False
        self.score_table.setRowCount(0)
        for row in rows:
            number = self.score_table.rowCount()
            self.score_table.insertRow(number)
            for column, key in enumerate(("rank", "country", "alliance", "name", "score")):
                self.score_table.setItem(number, column, QTableWidgetItem(str(row.get(key, ""))))
        self.score_tabs.setCurrentWidget(self.score_table)
        self.score_info.setText(f"正在编辑 {len(rows)} 条记录，请核对每一项后保存快照。")

    def _score_import(self):
        try:
            identity = self._score_identity()
            path, _ = QFileDialog.getOpenFileName(self, "导入备战榜首版或其他快照", "", "表格 (*.xlsx *.csv)")
            if not path:
                return
            rows = scores.read_xlsx(path) if path.lower().endswith(".xlsx") else scores.read_csv(path)
            self._score_put_rows(rows, identity)
            self.score_info.setText(f"导入 {len(rows)} 条记录；请确认后保存。支持原始首版 Excel。")
        except Exception as exc:
            self._score_error(exc)

    def _score_recover_draft(self):
        try:
            identity = self._score_identity()
            if self.score_table.rowCount() and QMessageBox.question(self, APP_NAME, "恢复草稿将替换当前编辑内容，是否继续？") != QMessageBox.StandardButton.Yes:
                return
            drafts = scores.list_capture_drafts(identity)
            if not drafts:
                raise ValueError('当前账号没有可恢复的采集草稿。')
            selected = 0
            if len(drafts) > 1:
                labels = [f"{datetime.fromtimestamp(d['modified']).strftime('%Y-%m-%d %H:%M:%S')} · {len(d['rows'])} 条 · {d['id'][:8]}" for d in drafts]
                choice, accepted = QInputDialog.getItem(self, APP_NAME, '选择要恢复的采集草稿：', labels, 0, False)
                if not accepted:
                    return
                selected = labels.index(choice)
            rows = drafts[selected]['rows']
            self._score_put_rows(rows, identity)
            self.score_has_unreviewed_ocr = True
            self.score_info.setText(f"已恢复 {len(rows)} 条未核对的采集草稿；请逐项核对后保存快照。")
        except Exception as exc:
            self._score_error(exc)

    def _score_add_row(self):
        try:
            identity = self._score_identity()
            if self.score_editor_identity not in (None, identity):
                raise ValueError("当前编辑内容属于另一个账号，请先保存或重新导入。")
            self.score_editor_identity = identity
            self.score_table.insertRow(self.score_table.rowCount())
            self.score_tabs.setCurrentWidget(self.score_table)
        except Exception as exc:
            self._score_error(exc)

    def _score_delete_rows(self):
        for row in sorted({item.row() for item in self.score_table.selectedIndexes()}, reverse=True):
            self.score_table.removeRow(row)

    def _score_save(self):
        try:
            identity = self._score_identity()
            if self.score_editor_identity != identity:
                raise ValueError("编辑内容与当前手机账号不一致，请重新导入或载入。")
            if self.score_has_unreviewed_ocr and QMessageBox.question(
                    self, APP_NAME, "识别结果可能有错漏。是否已对照游戏画面逐项核对全部排名、国家、联盟、昵称和积分？") != QMessageBox.StandardButton.Yes:
                return
            rows = []
            for row in range(self.score_table.rowCount()):
                values = [(self.score_table.item(row, col).text() if self.score_table.item(row, col) else "") for col in range(5)]
                try:
                    rows.append(scores.normalize_row(values))
                except Exception as exc:
                    raise ValueError(f"第 {row + 1} 行：{exc}") from exc
            label, ok = QInputDialog.getText(self, "保存快照", "快照名称（例如：首版、11 月 7 日下午）")
            if not ok:
                return
            saved = scores.save_snapshot(identity, rows, label)
            self._score_refresh()
            self.score_info.setText(f"已保存 {len(rows)} 条；" + ("前 200 名完整。" if saved["complete"] else "快照不完整，缺失排名不会被当作零分。"))
        except Exception as exc:
            self._score_error(exc)

    def _score_refresh(self):
        try:
            identity = self._score_identity()
            snapshots = scores.load_snapshots(identity)
            for combo in (self.score_old, self.score_new):
                combo.clear()
                for item in snapshots:
                    incomplete = "（不完整）" if not item.get("complete") else ""
                    combo.addItem(f"{item['label']} · {item['created_at'][:19].replace('T', ' ')}{incomplete}", item)
            if snapshots:
                self.score_new.setCurrentIndex(len(snapshots) - 1)
            self.score_info.setText(f"当前账号共 {len(snapshots)} 个快照。")
        except Exception as exc:
            self._score_error(exc)

    def _score_load_old(self):
        try:
            identity = self._score_identity()
            item = self.score_old.currentData()
            if not item or item["identity"] != identity:
                raise ValueError("请刷新并选择当前账号的基准快照。")
            self._score_put_rows(item["rows"], identity)
        except Exception as exc:
            self._score_error(exc)

    def _score_compare(self):
        try:
            identity = self._score_identity()
            old, new = self.score_old.currentData(), self.score_new.currentData()
            if not old or not new or old["identity"] != identity or new["identity"] != identity:
                raise ValueError("请刷新并选择当前账号的两个快照。")
            result = scores.compare_snapshots(old, new)
            self.score_diff.setRowCount(len(result["changed"]))
            for index, item in enumerate(result["changed"]):
                before, after = item["old"], item["new"]
                values = [after["country"], after["alliance"], after["name"], f"{before['score']:,}",
                          f"{after['score']:,}", f"{item['delta']:+,}", after["rank"]]
                for col, value in enumerate(values):
                    self.score_diff.setItem(index, col, QTableWidgetItem(str(value)))
            unmatched = [("基准", row) for row in result["unmatched_old"]] + [("当前", row) for row in result["unmatched_new"]]
            self.score_unmatched.setRowCount(len(unmatched))
            for index, (side, row) in enumerate(unmatched):
                for col, value in enumerate((side, row["rank"], row["country"], row["alliance"], row["name"], f"{row['score']:,}")):
                    self.score_unmatched.setItem(index, col, QTableWidgetItem(str(value)))
            self.score_info.setText(f"异动 {len(result['changed'])} 人，按积分变化降序；基准未匹配 {len(result['unmatched_old'])} 人，当前未匹配 {len(result['unmatched_new'])} 人。重名、改名或缺国家不会猜测配对。")
            self.score_tabs.setCurrentWidget(self.score_diff)
        except Exception as exc:
            self._score_error(exc)

    def _score_run_ocr(self, path, language='zh-Hans-CN'):
        import json
        process = subprocess.Popen(["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass",
                                    "-File", str(resource_path("assets/scoreboard_ocr.ps1")),
                                    "-ImagePath", str(path), "-Language", language],
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE, creationflags=CREATE_NO_WINDOW)
        try:
            out, err = process.communicate(timeout=20)
        except subprocess.TimeoutExpired:
            subprocess.run(["taskkill", "/PID", str(process.pid), "/T", "/F"],
                           timeout=5, capture_output=True, creationflags=CREATE_NO_WINDOW)
            process.communicate(timeout=2)
            raise ValueError("画面识别超时，已停止。")
        if process.returncode:
            raise ValueError("Windows 文字识别失败：" + err.decode("utf-8", errors="replace")[-600:])
        from PIL import Image
        with Image.open(path) as image:
            width, height = image.size
        return scores.restore_ocr_coordinates(json.loads(out.decode("utf-8-sig")), width, height)

    def _score_navigation(self, target, identity):
        from wjdr_scoreboard_identity import verify_bound_identity
        used = set()
        uncertain = 0
        self.log("正在识别当前页面并进入备战总榜。")
        for _ in range(28):
            if self.stop_event.is_set():
                raise InterruptedError()
            if not verify_bound_identity(target, target.device, identity) or not target.foreground_is_game():
                raise ValueError("账号或游戏状态发生变化，已停止进入榜单。")
            frame = target.screenshot(timeout=15)
            if abs(frame.width / frame.height - 1440 / 2560) > .01:
                raise ValueError("画面比例不是受支持的竖屏榜单比例。")
            with tempfile.TemporaryDirectory(prefix="wjdr-score-nav-") as directory:
                path = Path(directory) / "screen.png"
                frame.resize((1440, 2560)).save(path)
                decision = scores.navigation_decision(frame, self._score_run_ocr(path))
            if decision and decision[0] == 'ready':
                self.log("已确认备战阶段个人总榜。")
                return
            if decision is None or decision[0] in used:
                uncertain += 1
                if uncertain >= 4:
                    raise ValueError("页面加载或识别结果无法确认；请打开备战阶段个人总榜后重试。")
                continue  # observe a fresh frame; never repeat an unacknowledged input
            uncertain = 0
            action, points = decision
            if self.stop_event.is_set() or not verify_bound_identity(target, target.device, identity):
                raise InterruptedError()
            # Reconfirm that the page is still the one just identified; an
            # animated transition may change other pixels, so compare action anchors.
            fresh = target.screenshot(timeout=15)
            with tempfile.TemporaryDirectory(prefix="wjdr-score-nav-") as directory:
                path = Path(directory) / "confirm.png"
                fresh.resize((1440, 2560)).save(path)
                confirmed = scores.navigation_decision(fresh, self._score_run_ocr(path))
            same_action = (confirmed is not None and confirmed[0] == decision[0] and
                           len(confirmed[1]) == len(decision[1]) and
                           all(abs(a - b) <= 8 for a, b in zip(confirmed[1], decision[1])))
            if not same_action:
                self.log("页面变化，重新识别后再决定下一步。")
                continue
            if self.stop_event.is_set() or not target.foreground_is_game() or not verify_bound_identity(target, target.device, identity):
                raise InterruptedError()
            action, points = confirmed
            used.add(action)
            xscale, yscale = fresh.width / 1440, fresh.height / 2560
            mapped = [str(round(v * (xscale if i % 2 == 0 else yscale))) for i, v in enumerate(points)]
            command = ['input', 'swipe', *mapped, '500'] if action == 'find_kingdom_tab' else ['input', 'tap', *mapped]
            names = {'open_activities': '打开常规活动', 'find_kingdom_tab': '查找最强王国标签',
                     'open_kingdom': '打开最强王国', 'open_ranking': '打开排行菜单',
                     'open_personal': '打开个人排行', 'select_preparation': '选择备战阶段',
                     'select_total': '选择总榜'}
            self.log(f"已确认页面，{names.get(action, '进入榜单')}。")
            target.shell(command, timeout=8)
        raise ValueError("进入榜单的观察次数已用完；请检查当前页面。")

    def _score_read_frame(self, frame, identity):
        with tempfile.TemporaryDirectory(prefix="wjdr-score-") as directory:
            image = Path(directory) / "frame.png"
            if abs(frame.width / frame.height - 1440 / 2560) > .01:
                raise ValueError("画面比例不是受支持的竖屏榜单比例。")
            frame = frame.resize((1440, 2560))
            scores.validate_total_selection(frame)
            frame.save(image)
            lines = self._score_run_ocr(image)
            rank_image, rank_positions = scores.prepare_rank_ocr(frame)
            # Retry unreadable score text in its observed row. A binary crop
            # improves comma recognition without synthesizing any digits.
            for index, position in enumerate(rank_positions):
                if self.stop_event.is_set():
                    break
                if position < 1000 or position + 134 > 2100:
                    continue
                has_score = any(position <= min(w['y'] for w in line['words']) <= position + 110
                                and scores.is_score_line(line) for line in lines if line.get('words'))
                if has_score:
                    continue
                left, top = 520, position + 14
                crop = frame.crop((left, top, 1000, position + 134)).convert('L')
                crop = crop.point(lambda value: 0 if value < 150 else 255)
                crop_path = Path(directory) / f'score-{index}.png'
                crop.resize((crop.width * 2, crop.height * 2)).save(crop_path)
                for line in self._score_run_ocr(crop_path):
                    words = [dict(word, x=left + word['x'] / 2, y=top + word['y'] / 2,
                                  width=word.get('width', 0) / 2,
                                  height=word.get('height', 0) / 2)
                             for word in line.get('words', [])]
                    if words:
                        lines.append({'text': line.get('text', ''), 'words': words})
            # Full-frame OCR sometimes misses a name even while it reads the
            # score below it. Retry that precise visible row at higher scale;
            # never invent a name or advance past a missing rank.
            for index, y in enumerate(scores.missing_name_score_positions(lines)):
                if self.stop_event.is_set():
                    break
                left, top = 685, y - 140
                crop = frame.crop((left, top, 1350, y - 25))
                crop_path = Path(directory) / f'name-{index}.png'
                crop.resize((crop.width * 2, crop.height * 2)).save(crop_path)
                for line in self._score_run_ocr(crop_path):
                    words = [dict(word, x=left + word['x'] / 2, y=top + word['y'] / 2,
                                  width=word.get('width', 0) / 2,
                                  height=word.get('height', 0) / 2)
                             for word in line.get('words', [])]
                    if words:
                        lines.append({'text': line.get('text', ''), 'words': words})
            badge = Path(directory) / "badges.png"
            scores.prepare_badge_ocr(frame).save(badge)
            rank_path = Path(directory) / "ranks.png"
            rank_image.save(rank_path)
            glyphs = scores.read_rank_glyphs(frame, rank_positions)
            badges = scores.merge_rank_ocr(self._score_run_ocr(badge, 'en-US'), self._score_run_ocr(rank_path, 'en-US'), rank_positions, glyphs)
            candidates = scores.candidate_rows(lines, badges)
            # The three medals do not reliably OCR as digits. Infer their ranks
            # only when a fully visible fourth row anchors all four in order.
            if len(candidates) == 4 and [str(r['rank']) for r in candidates] == ['', '', '', '4']:
                for i, row in enumerate(candidates[:3], 1):
                    row['rank'] = str(i)
            return {"text": "\n".join(line["text"].replace(" ", "") for line in lines),
                    "rows": candidates, "identity": identity}

    def _score_capture(self):
        try:
            identity = self._score_identity()
            if self.score_editor_identity not in (None, identity):
                raise ValueError("当前编辑内容属于另一个账号，请先保存或重新导入。")
            target = self.adb.clone_for_device(self.adb.device)
            def job():
                self._score_navigation(target, identity)
                result = self._score_read_frame(target.screenshot(timeout=15), identity)
                self.signals.score_ocr.emit(result)
            self._start_worker(target.device, job, expected_identity=identity)
        except Exception as exc:
            self._score_error(exc)

    def _score_capture_many(self):
        try:
            identity = self._score_identity()
            if self.score_editor_identity not in (None, identity):
                raise ValueError("当前编辑内容属于另一个账号，请先保存或重新导入。")
            if self.score_table.rowCount():
                if QMessageBox.question(self, APP_NAME, "连续采集需要新建编辑表，是否清空当前内容？") != QMessageBox.StandardButton.Yes:
                    return
                self._score_put_rows([], identity)
            target = self.adb.clone_for_device(self.adb.device)
            def job():
                import uuid
                from wjdr_scoreboard_identity import verify_bound_identity
                self._score_navigation(target, identity)
                draft_id = uuid.uuid4().hex
                draft_rows = {}
                previous = None
                seeking_last = None
                seeking_rechecks = 0
                captured_pages = 0
                for page in range(240):
                    if self.stop_event.is_set() or not target.foreground_is_game():
                        self.log("连续采集停止；已识别的内容保留在编辑表。")
                        return
                    frame = target.screenshot(timeout=15)
                    screen_width, screen_height = frame.size
                    result = None
                    valid = False
                    for attempt in range(3):
                        try:
                            result = self._score_read_frame(frame, identity)
                        except ValueError as exc:
                            # Transient in-game notices may briefly hide the
                            # selection marker. Reobserve; never tap or swipe.
                            self.log(f"榜单画面暂不可确认：{exc}；重新观察，不重复输入。")
                            if attempt < 2 and not self.stop_event.wait(0.5) and target.foreground_is_game():
                                frame = target.screenshot(timeout=15)
                                continue
                            break
                        ranks = [int(row['rank']) for row in result['rows'] if str(row['rank']).isdigit()]
                        valid = (ranks and len(ranks) == len(result['rows']) and
                                 ranks == list(range(min(ranks), max(ranks) + 1)) and
                                 (previous is None or scores.ranks_advance(previous, ranks)))
                        if valid:
                            break
                        if attempt < 2 and not self.stop_event.is_set() and target.foreground_is_game():
                            self.log("排名尚未确认，读取新的画面再次识别；不会重复滑动。")
                            frame = target.screenshot(timeout=15)
                    if not valid:
                        self.log("多次读取仍无法确认排名衔接，已停止滚动并保留本屏结果供核对。")
                        if result is not None:
                            self.signals.score_ocr.emit(result)
                        return
                    # Starting on an already-scrolled board must not silently
                    # produce a snapshot that begins in the middle. Each
                    # backwards swipe requires observable backwards progress.
                    if previous is None and min(ranks) > 1:
                        if seeking_last is not None and min(ranks) >= seeking_last:
                            seeking_rechecks += 1
                            if seeking_rechecks >= 3:
                                self.log("无法确认榜单回到前面的排名，已停止；请检查页面。")
                                return
                            self.log("等待榜单向前移动，重新观察，不重复滑动。")
                            continue
                        seeking_last = min(ranks)
                        seeking_rechecks = 0
                        if self.stop_event.is_set() or not verify_bound_identity(target, target.device, identity) or not target.foreground_is_game():
                            self.log("已停止寻找榜首。")
                            return
                        if not self._score_confirm_swipe(target, identity, frame):
                            self.log("榜单画面发生变化，已停止寻找榜首。")
                            return
                        if self.stop_event.is_set():
                            return
                        self.log(f"当前从第 {min(ranks)} 名附近开始，正在返回榜首。")
                        target.shell(['input', 'swipe', str(round(screen_width * 1050 / 1440)), str(round(screen_height * 1100 / 2560)), str(round(screen_width * 1050 / 1440)), str(round(screen_height * 1900 / 2560)), '550'], timeout=8)
                        continue
                    for row in result['rows']:
                        rank = int(row['rank'])
                        if rank not in draft_rows:
                            draft_rows[rank] = scores.normalize_row([row[k] for k in ('rank', 'country', 'alliance', 'name', 'score')])
                    scores.save_capture_draft(identity, list(draft_rows.values()), draft_id)
                    self.signals.score_ocr.emit(result)
                    captured_pages += 1
                    self.log(f"备战榜识别第 {captured_pages} 屏，当前可见排名至 {max(ranks)}；结果待人工核对。")
                    if max(ranks) >= 200:
                        self.log("已到第 200 名；请检查缺失行和识别错误后保存。")
                        return
                    previous = ranks
                    if self.stop_event.is_set():
                        self.log("已按停止请求结束采集；已识别的内容保留在编辑表。")
                        return
                    if not verify_bound_identity(target, target.device, identity) or not target.foreground_is_game():
                        self.log("账号或游戏状态变化，已停止采集。")
                        return
                    if not self._score_confirm_swipe(target, identity, frame):
                        self.log("榜单画面发生变化，已停止采集。")
                        return
                    if self.stop_event.is_set():
                        return
                    target.shell(['input', 'swipe', str(round(screen_width * 1050 / 1440)), str(round(screen_height * 1920 / 2560)), str(round(screen_width * 1050 / 1440)), str(round(screen_height * 1420 / 2560)), '550'], timeout=8)
                self.log("达到采集屏数上限；请检查结果，未继续滑动。")
            self._start_worker(target.device, job, expected_identity=identity)
        except Exception as exc:
            self._score_error(exc)

    def _score_confirm_swipe(self, target, identity, frame):
        """Reobserve a briefly obscured board; never send an input here."""
        from PIL import ImageChops, ImageStat
        from wjdr_scoreboard_identity import verify_bound_identity
        title_before = frame.resize((1440, 2560)).crop((480, 175, 950, 310))
        for attempt in range(3):
            if self.stop_event.is_set() or not target.foreground_is_game() or not verify_bound_identity(target, target.device, identity):
                return False
            fresh = target.screenshot(timeout=15).resize((1440, 2560))
            try:
                scores.validate_total_selection(fresh)
                title_after = fresh.crop((480, 175, 950, 310))
                if max(ImageStat.Stat(ImageChops.difference(title_before, title_after)).mean) <= 2:
                    return True
            except ValueError:
                pass
            if attempt < 2 and self.stop_event.wait(0.5):
                return False
        return False

    def _score_show_ocr(self, result):
        self.score_ocr.setPlainText(result["text"])
        if self.score_editor_identity not in (None, result["identity"]):
            self.score_info.setText("识别结果属于其他账号，未加入编辑表。")
            return
        self.score_editor_identity = result["identity"]
        known = {self.score_table.item(row, 0).text().strip() for row in range(self.score_table.rowCount()) if self.score_table.item(row, 0)}
        added = 0
        for entry in result["rows"]:
            rank = str(entry['rank'])
            if rank and rank in known:
                continue
            row = self.score_table.rowCount()
            self.score_table.insertRow(row)
            for col, key in enumerate(("rank", "country", "alliance", "name", "score")):
                self.score_table.setItem(row, col, QTableWidgetItem(str(entry[key])))
            if rank:
                known.add(rank)
            added += 1
        self.score_tabs.setCurrentWidget(self.score_table)
        if added:
            self.score_has_unreviewed_ocr = True
        self.score_info.setText(f"本屏新增 {added} 条待核对记录。姓名、国家、排名和积分可能错误或遗漏，请对照游戏画面核对；手动滚动后可继续识别。")
