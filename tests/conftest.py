"""Shared pytest fixtures for GUI tests."""

from __future__ import annotations

import pytest

from tree_cloud_drive.core.settings import Settings
from tree_cloud_drive.main_window import MainWindow


@pytest.fixture
def settings() -> Settings:
    """Provide a fresh Settings instance for tests."""

# Author: Rich Lewis - GitHub: @RichLewis007

    return Settings()


@pytest.fixture
def main_window(qtbot, settings) -> MainWindow:
    """Provide a constructed MainWindow attached to qtbot."""
    window = MainWindow(settings=settings)
    qtbot.addWidget(window)
    return window
