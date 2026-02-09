"""Single-instance guard behavior tests."""
# Author: Rich Lewis - GitHub: @RichLewis007

from __future__ import annotations

from tree_cloud_drive.core import single_instance
from tree_cloud_drive.core.single_instance import SingleInstanceGuard


def test_single_instance_message_path(monkeypatch) -> None:
    """Secondary instance keeps socket so it can send activation message."""

    class FakeQLocalSocket:
        connect_calls = 0

        class OpenModeFlag:
            ReadWrite = 0

        def __init__(self) -> None:
            self._last_write: bytes | None = None

        def connectToServer(self, _name, _mode) -> None:  # noqa: D401
            return None

        def waitForConnected(self, _ms: int) -> bool:
            FakeQLocalSocket.connect_calls += 1
            return FakeQLocalSocket.connect_calls > 1

        def write(self, data: bytes) -> None:
            self._last_write = data

        def waitForBytesWritten(self, _ms: int) -> bool:
            return self._last_write is not None

    class FakeQLocalServer:
        def __init__(self) -> None:
            self.listening = False

        @staticmethod
        def removeServer(_name: str) -> bool:
            return True

        def listen(self, _name: str) -> bool:
            self.listening = True
            return True

    monkeypatch.setattr(single_instance, "QLocalSocket", FakeQLocalSocket)
    monkeypatch.setattr(single_instance, "QLocalServer", FakeQLocalServer)

    primary = SingleInstanceGuard(app_id="test-app")
    assert primary.is_another_instance_running() is False
    assert primary.server is not None
    assert primary.server.listening is True

    secondary = SingleInstanceGuard(app_id="test-app")
    assert secondary.is_another_instance_running() is True
    assert secondary.send_message_to_existing_instance(b"ping") is True
