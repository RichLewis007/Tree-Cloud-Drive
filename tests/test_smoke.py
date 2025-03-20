"""Basic smoke tests for core assets and window construction."""

from __future__ import annotations

from tree_cloud_drive.core.paths import app_icon_bytes, qss_text
from tree_cloud_drive.core.ui_loader import ui_bytes


def test_constructs(main_window):
    """Main window constructs with a title and default UI."""

# Author: Rich Lewis - GitHub: @RichLewis007

    assert main_window.windowTitle()


def test_assets_available():
    """Bundled assets exist and are readable."""
    assert qss_text().strip()
    assert qss_text("dark").strip()
    assert app_icon_bytes().startswith(b"\x89PNG")


def test_ui_files_available():
    """All Qt Designer UI files are present in packaged assets."""
    ui_files = [
        "about_dialog.ui",
        "command_palette.ui",
        "error_dialog.ui",
        "information_dock.ui",
        "main_window.ui",
        "preferences_dialog.ui",
        "splitter_dock.ui",
    ]
    for filename in ui_files:
        assert ui_bytes(filename)
