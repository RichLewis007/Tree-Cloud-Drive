"""Folder download dialog using rclone."""
# Author: Rich Lewis - GitHub: @RichLewis007

from __future__ import annotations

import subprocess
import time
from pathlib import Path

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QDialog,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QProgressBar,
    QVBoxLayout,
)

from ..core.workers import WorkContext, Worker, WorkerPool, WorkRequest


class DownloadDialog(QDialog):
    """Dialog to download a remote folder to a local destination."""

    def __init__(self, remote_path: str, parent=None) -> None:
        super().__init__(parent)
        self.remote_path = remote_path
        self.pool = WorkerPool()
        self.worker: Worker[str] | None = None
        self._start_time: float | None = None
        self._last_status: str = ""

        self.setWindowTitle("Download Folder")
        self.setModal(True)
        self.setMinimumWidth(520)

        self.source_edit = QLineEdit(self.remote_path)
        self.source_edit.setReadOnly(True)

        default_dest = str(Path.home() / "Downloads")
        self.dest_edit = QLineEdit(default_dest)
        self.browse_btn = QPushButton("Browse...")
        self.browse_btn.clicked.connect(self._browse_dest)

        dest_row = QHBoxLayout()
        dest_row.addWidget(self.dest_edit)
        dest_row.addWidget(self.browse_btn)

        form = QFormLayout()
        form.addRow("Remote path", self.source_edit)
        form.addRow("Local folder", dest_row)

        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.progress.setFormat("Idle")

        self.status_label = QLabel("")
        self.status_label.setWordWrap(True)

        self.download_btn = QPushButton("Download")
        self.download_btn.clicked.connect(self._start_download)

        self.close_btn = QPushButton("Close")
        self.close_btn.clicked.connect(self.close)
        self.close_btn.setEnabled(True)

        self.open_btn = QPushButton("Open in Finder")
        self.open_btn.clicked.connect(self._open_dest)
        self.open_btn.setEnabled(False)

        buttons = QHBoxLayout()
        buttons.addStretch(1)
        buttons.addWidget(self.open_btn)
        buttons.addWidget(self.close_btn)
        buttons.addWidget(self.download_btn)

        layout = QVBoxLayout()
        layout.addLayout(form)
        layout.addWidget(self.progress)
        layout.addWidget(self.status_label)
        layout.addLayout(buttons)

        self.setLayout(layout)

    def _browse_dest(self) -> None:
        dest = QFileDialog.getExistingDirectory(self, "Select download folder", self.dest_edit.text())
        if dest:
            self.dest_edit.setText(dest)

    def _open_dest(self) -> None:
        path = self.dest_edit.text().strip()
        if path:
            QDesktopServices.openUrl(QUrl.fromLocalFile(path))

    def _set_busy(self, busy: bool) -> None:
        if busy:
            self.progress.setRange(0, 0)
            self.progress.setFormat("Downloading...")
        else:
            self.progress.setRange(0, 100)

        self.download_btn.setEnabled(not busy)
        self.browse_btn.setEnabled(not busy)
        self.dest_edit.setEnabled(not busy)

    def _update_status(self, line: str) -> None:
        elapsed = 0.0
        if self._start_time is not None:
            elapsed = time.monotonic() - self._start_time
        self._last_status = line.strip()
        if self._last_status:
            self.status_label.setText(f"{self._last_status}\nElapsed: {elapsed:.1f}s")
        else:
            self.status_label.setText(f"Elapsed: {elapsed:.1f}s")

    def _start_download(self) -> None:
        if self.worker is not None:
            return
        dest = self.dest_edit.text().strip()
        if not dest:
            self.status_label.setText("Please select a local folder.")
            return

        self._set_busy(True)
        self.open_btn.setEnabled(False)
        self._start_time = time.monotonic()
        self.status_label.setText("Starting download...")

        def work(ctx: WorkContext) -> str:
            ctx.check_cancelled()
            cmd = [
                "rclone",
                "copy",
                self.remote_path,
                dest,
                "--progress",
                "--stats=1s",
                "--stats-one-line",
            ]
            with subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
            ) as proc:
                if proc.stdout:
                    for raw in proc.stdout:
                        if not raw:
                            continue
                        line = raw.replace("\r", "").strip()
                        if line:
                            ctx.progress(0, line)
                        ctx.check_cancelled()
                return_code = proc.wait()
            if return_code != 0:
                raise RuntimeError(f"rclone exited with code {return_code}")
            return "Download complete"

        def progress(_percent: int, message: str) -> None:
            self._update_status(message)

        def done(result: str) -> None:
            self._set_busy(False)
            self.progress.setValue(100)
            self.progress.setFormat("Complete")
            if self._last_status:
                self.status_label.setText(f"{self._last_status}\n{result}")
            else:
                self.status_label.setText(result)
            self.open_btn.setEnabled(True)
            self.worker = None

        def error(msg: str) -> None:
            self._set_busy(False)
            self.progress.setValue(0)
            self.progress.setFormat("Error")
            self.status_label.setText(msg)
            self.worker = None

        req = WorkRequest(fn=work, on_done=done, on_error=error, on_progress=progress)
        self.worker = self.pool.submit(req)
