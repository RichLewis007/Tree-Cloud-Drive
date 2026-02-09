"""About dialog with version and release information.

This module provides a simple about dialog that displays:
- Application name and version
- Application icon/image
- Optional release notes link
- Standard close button

The dialog can optionally be used as a splash/loading screen that:
- Shows for a specified number of seconds before auto-closing
- Waits for user to click OK button (if auto-close not enabled)

The version is typically obtained from package metadata using
importlib.metadata.version() or can be passed directly.
"""
# Author: Rich Lewis - GitHub: @RichLewis007

from __future__ import annotations

from PySide6.QtCore import QSize, Qt, QTimer
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtWidgets import QDialog, QLabel, QPushButton, QVBoxLayout

from ..core.paths import APP_NAME, app_icon_bytes
from ..core.ui_loader import load_ui


class AboutDialog(QDialog):
    """About dialog showing version, icon, and release notes link.

    Can be used as a regular about dialog or as a splash/loading screen
    with optional auto-close timer.
    """

    def __init__(
        self,
        version: str,
        release_notes_url: str = "",
        auto_close_seconds: int | None = None,
        parent=None,
    ) -> None:
        """Initialize the About dialog.

        Args:
            version: Application version string
            release_notes_url: Optional URL to release notes
            auto_close_seconds: If set, dialog will auto-close after this many seconds.
                               If None, user must click OK button.
            parent: Parent widget
        """
        super().__init__(parent)
        self.setWindowTitle(f"About {APP_NAME}")
        # Small rectangular window
        self.setMinimumWidth(350)
        self.setMinimumHeight(200)
        self.setMaximumWidth(400)
        self.setMaximumHeight(300)
        # Use standard dialog flags (modal by default when using exec())
        self.setWindowFlags(Qt.WindowType.Dialog)

        # Load UI from .ui file
        self._ui = load_ui("about_dialog.ui", self)
        main_layout = QVBoxLayout(self)
        main_layout.addWidget(self._ui)

        # Find widgets from UI file
        icon_label = self._ui.findChild(QLabel, "iconLabel")
        name_label = self._ui.findChild(QLabel, "nameLabel")
        version_label = self._ui.findChild(QLabel, "versionLabel")
        release_notes_label = self._ui.findChild(QLabel, "releaseNotesLabel")
        ok_button = self._ui.findChild(QPushButton, "okButton")

        if icon_label is None or name_label is None or version_label is None:
            raise RuntimeError("Required widgets not found in about_dialog.ui")
        if ok_button is None:
            raise RuntimeError("okButton not found in about_dialog.ui")

        # App logo - load and set pixmap
        try:
            from importlib.resources import files

            logo_path = files("tree_cloud_drive") / "assets" / "tree-cloud-drive-logo.jpg"
            logo_bytes = logo_path.read_bytes()
            pixmap = QPixmap()
            if pixmap.loadFromData(logo_bytes):
                # Set window icon
                try:
                    icon_bytes = app_icon_bytes()
                    icon_pixmap = QPixmap()
                    if icon_pixmap.loadFromData(icon_bytes):
                        self.setWindowIcon(QIcon(icon_pixmap))
                except Exception:
                    pass
                # Scale icon to reasonable size for display
                scaled_pixmap = pixmap.scaled(
                    QSize(96, 96),
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
                icon_label.setPixmap(scaled_pixmap)
                icon_label.setVisible(True)
                icon_label.setScaledContents(False)
        except Exception:
            # If icon loading fails, hide the icon label
            icon_label.setVisible(False)

        # App name
        name_label.setText(f"<h2>{APP_NAME}</h2>")

        # Version
        version_label.setText(f"Version {version}")

        # Release notes link
        if release_notes_url and release_notes_label:
            release_notes_label.setText(f'<a href="{release_notes_url}">Release Notes</a>')
        elif release_notes_label:
            release_notes_label.setVisible(False)

        # OK button connection
        ok_button.clicked.connect(self.accept)

        # Auto-close timer if specified
        self._auto_close_timer: QTimer | None = None
        if auto_close_seconds is not None and auto_close_seconds > 0:
            self._auto_close_timer = QTimer(self)
            self._auto_close_timer.setSingleShot(True)
            self._auto_close_timer.timeout.connect(self.accept)
            self._auto_close_timer.start(auto_close_seconds * 1000)

    def closeEvent(self, event) -> None:  # type: ignore[override]
        """Stop auto-close timer if dialog is closed manually."""
        if self._auto_close_timer:
            self._auto_close_timer.stop()
        super().closeEvent(event)
