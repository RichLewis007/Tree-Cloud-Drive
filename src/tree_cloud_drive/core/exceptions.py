"""Global exception handling and error reporting.

This module installs a custom exception hook that:
- Displays a user-friendly error dialog with detailed stack trace
- Provides copy-to-clipboard functionality for error details

The exception hook is installed early in application startup to catch
all unhandled exceptions throughout the application lifecycle.
"""
# Author: Rich Lewis - GitHub: @RichLewis007

from __future__ import annotations

import contextlib
import sys

from PySide6.QtWidgets import QApplication, QWidget


def install_exception_hook(
    error_dialog_factory=None,
) -> None:
    """Handle uncaught exceptions and present a user-friendly dialog.

    Args:
        error_dialog_factory: Optional callable(exc_type, exc, tb, parent)
            that creates and returns an error dialog. If None, uses default ErrorDialog.
            This allows the application layer to inject the dialog dependency,
            avoiding circular dependencies.
    """

    def excepthook(exc_type, exc, tb):  # type: ignore[no-untyped-def]
        with contextlib.suppress(Exception):
            # Only show dialog if QApplication exists
            app = QApplication.instance()
            if not app:
                return

            # Find the main window if available for parent
            parent: QWidget | None = None
            if isinstance(app, QApplication):
                for widget in app.topLevelWidgets():
                    if widget.isVisible() and hasattr(widget, "windowTitle"):
                        parent = widget
                        break

            # Use factory if provided, otherwise lazy import to avoid circular dependency
            if error_dialog_factory:
                dialog = error_dialog_factory(exc_type, exc, tb, parent)
                dialog.exec()
            else:
                # Lazy import only when needed (after QApplication exists)
                from ..dialogs.error_dialog import ErrorDialog

                dialog = ErrorDialog(exc_type, exc, tb, parent)
                dialog.exec()

    sys.excepthook = excepthook
