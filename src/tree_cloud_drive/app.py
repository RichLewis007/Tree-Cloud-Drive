"""Application entry point and initialization.

This module provides the main application startup logic, including:
- QApplication creation and configuration
- Single-instance guard to prevent multiple instances
- Exception handling setup
- Theme and icon loading
- Main window creation and event loop execution
"""
# Author: Rich Lewis - GitHub: @RichLewis007

from __future__ import annotations

import sys
from contextlib import suppress

from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtWidgets import QApplication

from .core.exceptions import install_exception_hook
from .core.paths import APP_NAME, APP_ORG, app_icon_bytes, app_version, qss_text
from .core.settings import Settings
from .core.single_instance import SingleInstanceGuard
from .main_window import MainWindow


def run(splash_screen_seconds: int | None = None, force_no_splash: bool = False) -> int:
    """Create the QApplication, wire services, and start the event loop.

    This function handles all application initialization:
    - Sets up exception handling
    - Enforces single-instance guard
    - Loads themes and icons from packaged assets
    - Creates and shows the main window
    - Starts the Qt event loop

    Returns:
        Exit code from the application event loop (typically 0 for normal exit).
    """
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setOrganizationName(APP_ORG)
    app.setAttribute(Qt.ApplicationAttribute.AA_UseHighDpiPixmaps, True)

    # Install exception hook with explicit dialog factory to avoid circular dependency
    # This allows core/exceptions to not import dialogs at module level
    from .dialogs.error_dialog import ErrorDialog

    def create_error_dialog(exc_type, exc, tb, parent):
        return ErrorDialog(exc_type, exc, tb, parent)

    install_exception_hook(error_dialog_factory=create_error_dialog)
    # Single instance guard
    guard = SingleInstanceGuard()
    if guard.is_another_instance_running():
        # Try to send activate message to existing instance
        guard.send_message_to_existing_instance()
        return 0

    settings = Settings()

    # Load packaged assets via importlib.resources so this works from wheels.
    # Apply theme from settings
    theme = settings.get_theme()
    with suppress(FileNotFoundError):
        app.setStyleSheet(qss_text(theme))

    try:
        icon_bytes = app_icon_bytes()
    except FileNotFoundError:
        icon_bytes = None
    if icon_bytes:
        pixmap = QPixmap()
        if pixmap.loadFromData(icon_bytes):
            app.setWindowIcon(QIcon(pixmap))

    win = MainWindow(settings=settings, instance_guard=guard)

    # Handle messages from new instances
    def handle_new_instance() -> None:
        if guard.server:
            socket = guard.server.nextPendingConnection()
            if socket:
                socket.readyRead.connect(lambda: _activate_window(win))
                socket.waitForReadyRead(100)

    def _activate_window(window: MainWindow) -> None:
        window.show()
        window.raise_()
        window.activateWindow()

    guard.set_new_connection_callback(handle_new_instance)

    # Determine splash screen duration:
    # - If force_no_splash is True, explicitly don't show (override settings)
    # - If splash_screen_seconds is explicitly provided, use that (command-line override)
    # - Otherwise, check settings
    if force_no_splash:
        splash_screen_seconds = None
    elif splash_screen_seconds is None:
        splash_screen_seconds = settings.get_splash_screen_seconds()

    # Show splash screen if requested
    # If splash_screen_seconds is 0, show but wait for user to click OK (no auto-close)
    # If splash_screen_seconds > 0, show and auto-close after that many seconds
    if splash_screen_seconds is not None:
        from .dialogs.about import AboutDialog

        auto_close = splash_screen_seconds if splash_screen_seconds > 0 else None
        splash = AboutDialog(
            version=app_version(),
            release_notes_url="",
            auto_close_seconds=auto_close,
            parent=None,
        )
        splash.show()
        app.processEvents()  # Process events to show splash immediately
        # Use exec() which blocks until dialog closes (either by timer or user clicking OK)
        splash.exec()

    win.show()
    return app.exec()
