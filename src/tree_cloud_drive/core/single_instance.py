"""Single-instance application guard.

This module provides functionality to ensure only one instance of the
application runs at a time. It uses QLocalServer/QLocalSocket for
inter-process communication.

When a second instance is launched:
- The new instance detects the existing instance via socket connection
- Sends an "activate" message to bring the existing window to front
- Exits immediately

The first instance listens for incoming connections and can activate
the window when a new instance attempts to start.
"""
# Author: Rich Lewis - GitHub: @RichLewis007

from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtNetwork import QLocalServer, QLocalSocket

from .paths import APP_NAME


class SingleInstanceGuard:
    """Ensures only one instance of the application is running."""

    def __init__(self, app_id: str | None = None) -> None:
        self.app_id = app_id or APP_NAME.replace(" ", "-").lower()
        self.server: QLocalServer | None = None
        self.socket: QLocalSocket | None = None
        self._is_running = False

    def is_another_instance_running(self) -> bool:
        """
        Check if another instance is already running.

        Returns:
            True if another instance is running, False otherwise.
        """
        self.socket = QLocalSocket()
        socket_name = f"{self.app_id}-single-instance"

        self.socket.connectToServer(socket_name, QLocalSocket.OpenModeFlag.ReadWrite)

        if self.socket.waitForConnected(500):
            # Another instance is running
            self.socket.disconnectFromServer()
            self.socket = None
            return True

        # No other instance, create server
        self._create_server(socket_name)
        return False

    def _create_server(self, socket_name: str) -> None:
        """Create a local server to listen for other instances."""
        self.server = QLocalServer()

        # Remove existing socket file if it exists (Linux/Unix)
        if sys.platform != "win32":
            import contextlib

            socket_path = Path(f"/tmp/{socket_name}")
            if socket_path.exists():
                with contextlib.suppress(OSError):
                    socket_path.unlink()

        if self.server.listen(socket_name):
            self._is_running = True
        else:
            pass

    def send_message_to_existing_instance(self, message: bytes = b"activate") -> bool:
        """
        Send a message to the existing instance.

        Args:
            message: Message to send (default: "activate" to bring window to front)

        Returns:
            True if message was sent successfully, False otherwise.
        """
        if not self.socket:
            return False

        self.socket.write(message)
        return self.socket.waitForBytesWritten(1000)

    def set_new_connection_callback(self, callback) -> None:
        """Set callback to handle messages from new instances."""
        if self.server:
            self.server.newConnection.connect(callback)
