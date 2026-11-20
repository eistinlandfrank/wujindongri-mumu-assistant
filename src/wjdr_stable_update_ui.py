"""Nonblocking update checks and verified downloads in the About page."""

from pathlib import Path

from PySide6.QtCore import QIODevice, QSaveFile, QStandardPaths, QTimer, QUrl, Signal
from PySide6.QtGui import QDesktopServices
from PySide6.QtNetwork import QNetworkAccessManager, QNetworkReply, QNetworkRequest
from PySide6.QtWidgets import QFileDialog, QHBoxLayout, QLabel, QProgressBar, QPushButton, QVBoxLayout

from wjdr_stable_update import LATEST_RELEASE, PortableVerification, StableRelease, read_stable_release
from wjdr_ui_components import Card


class StableUpdateCard(Card):
    available_changed = Signal(bool)
    _metadata_limit = 1024 * 1024

    def __init__(self, current_version: str) -> None:
        super().__init__()
        self._current_version = current_version
        self._release: StableRelease | None = None
        self._saved_path: Path | None = None
        self._reply: QNetworkReply | None = None
        self._manager = QNetworkAccessManager(self)
        self._manager.setRedirectPolicy(QNetworkRequest.RedirectPolicy.NoLessSafeRedirectPolicy)
        self._deadline = QTimer(self)
        self._deadline.setSingleShot(True)
        self._deadline.timeout.connect(self._stop_reply)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 22, 28, 22)
        title = QLabel("稳定版更新")
        title.setObjectName("sectionTitle")
        layout.addWidget(title)
        self._status = QLabel("正在等待首次检查…")
        self._status.setObjectName("aboutText")
        self._status.setWordWrap(True)
        layout.addWidget(self._status)
        self._progress = QProgressBar()
        self._progress.setRange(0, 100)
        self._progress.hide()
        layout.addWidget(self._progress)

        actions = QHBoxLayout()
        self._check_button = QPushButton("检查更新")
        self._check_button.setObjectName("secondaryButton")
        self._check_button.clicked.connect(lambda: self._check(manual=True))
        actions.addWidget(self._check_button)
        self._download_button = QPushButton("下载更新")
        self._download_button.setObjectName("primaryButton")
        self._download_button.clicked.connect(self._download)
        self._download_button.hide()
        actions.addWidget(self._download_button)
        self._folder_button = QPushButton("打开保存位置")
        self._folder_button.setObjectName("secondaryButton")
        self._folder_button.clicked.connect(self._open_folder)
        self._folder_button.hide()
        actions.addWidget(self._folder_button)
        actions.addStretch()
        layout.addLayout(actions)

        self._poll = QTimer(self)
        self._poll.timeout.connect(self._check)
        self._poll.start(60 * 60 * 1000)
        QTimer.singleShot(4000, self, self._check)

    def _request(self, url: str) -> QNetworkReply:
        request = QNetworkRequest(QUrl(url))
        request.setRawHeader(b"User-Agent", b"WJDRMuMuAssistant-StableUpdate")
        request.setTransferTimeout(15000)
        reply = self._manager.get(request)
        reply.setReadBufferSize(256 * 1024)
        self._reply = reply
        self._check_button.setEnabled(False)
        self._download_button.setEnabled(False)
        return reply

    def _stop_reply(self) -> None:
        if self._reply is not None:
            self._reply.abort()

    def _finish_reply(self, reply: QNetworkReply) -> None:
        self._deadline.stop()
        self._reply = None
        self._check_button.setEnabled(True)
        self._download_button.setEnabled(True)
        reply.deleteLater()

    def _clear_release(self) -> None:
        self._release = None
        self._saved_path = None
        self._download_button.hide()
        self._folder_button.hide()
        self.available_changed.emit(False)

    def _check(self, *, manual: bool = False) -> None:
        if self._reply is not None:
            return
        reply = self._request(LATEST_RELEASE)
        data = bytearray()
        self._deadline.start(25000)
        self._status.setText("正在检查稳定版…")

        def receive() -> None:
            data.extend(bytes(reply.readAll()))
            if len(data) > self._metadata_limit:
                reply.abort()

        def finished() -> None:
            data.extend(bytes(reply.readAll()))
            status = reply.attribute(QNetworkRequest.Attribute.HttpStatusCodeAttribute)
            try:
                if status == 404:
                    release = None
                elif reply.error() != QNetworkReply.NetworkError.NoError or len(data) > self._metadata_limit:
                    raise ValueError("Unavailable release metadata")
                else:
                    release = read_stable_release(data, self._current_version)
            except ValueError:
                self._clear_release()
                self._status.setText("暂时无法检查更新。请稍后重试或检查 GitHub 连接。")
            else:
                if release is None:
                    self._clear_release()
                    self._status.setText("当前没有可用的稳定版更新。")
                elif release == self._release and self._saved_path is not None:
                    self._show_saved()
                else:
                    self._saved_path = None
                    self._release = release
                    self._folder_button.hide()
                    self._download_button.show()
                    self._status.setText(
                        f"稳定版 {release.version} 可下载（{release.size / 1024**2:.1f} MB）。"
                    )
                    self.available_changed.emit(True)
            self._finish_reply(reply)

        reply.readyRead.connect(receive)
        reply.finished.connect(finished)

    def _download(self) -> None:
        release = self._release
        if release is None or self._reply is not None:
            return
        directory = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.DownloadLocation)
        chosen, _ = QFileDialog.getSaveFileName(
            self, "保存新版便携包", str(Path(directory) / release.filename), "便携程序 (*.exe)"
        )
        if not chosen or release != self._release or self._reply is not None:
            return
        path = Path(chosen)
        output = QSaveFile(str(path), self)
        if not output.open(QIODevice.OpenModeFlag.WriteOnly):
            self._status.setText("无法写入所选位置。请重新选择保存位置。")
            output.deleteLater()
            return

        verifier = PortableVerification(release)
        reply = self._request(release.url)
        self._saved_path = None
        self._folder_button.hide()
        self._progress.setValue(0)
        self._progress.show()
        self._status.setText(f"正在下载稳定版 {release.version}…")
        failed = False

        def receive() -> None:
            nonlocal failed
            chunk = bytes(reply.readAll())
            try:
                verifier.add(chunk)
                if output.write(chunk) != len(chunk):
                    raise OSError("Cannot write portable download")
            except (OSError, ValueError):
                failed = True
                reply.abort()
                return
            self._progress.setValue(verifier.size * 100 // release.size)

        def finished() -> None:
            if not failed and reply.error() == QNetworkReply.NetworkError.NoError and reply.bytesAvailable():
                receive()
            if not failed and reply.error() == QNetworkReply.NetworkError.NoError and verifier.complete() and output.commit():
                self._saved_path = path
                self._show_saved()
            else:
                if output.isOpen():
                    output.cancelWriting()
                    output.commit()
                self._status.setText("下载未完成或校验失败。请重试下载。")
            output.deleteLater()
            self._progress.hide()
            self._finish_reply(reply)

        reply.readyRead.connect(receive)
        reply.finished.connect(finished)

    def _show_saved(self) -> None:
        self._status.setText("下载已校验。请在当前任务结束后双击新版便携包。")
        self._folder_button.show()

    def _open_folder(self) -> None:
        if self._saved_path is not None:
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(self._saved_path.parent)))

    def cancel(self) -> None:
        self._poll.stop()
        self._deadline.stop()
        self._stop_reply()
