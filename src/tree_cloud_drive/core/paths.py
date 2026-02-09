"""Application paths and resource management.

This module provides functions for accessing:
- Bundled assets (QSS themes, icons) via importlib.resources
- Works both from source and when installed from wheels

The module uses importlib.resources for accessing packaged assets.

Author: Rich Lewis - GitHub: @RichLewis007
"""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version
from importlib.resources import files
from pathlib import Path

# Application metadata constants
APP_NAME = "tree-cloud-drive"
APP_ORG = "RichLewis.com"
_ASSETS_DIR = "assets"  # Directory name within package for assets
_DEFAULT_VERSION = "0.1.0"  # Fallback version if unable to determine


def app_version() -> str:
    """Get the application version.

    Tries multiple approaches:
    1. importlib.metadata.version() (works when installed)
    2. Reading pyproject.toml from source tree (development mode)
    3. Returns default version as fallback

    Returns:
        Version string (e.g., "0.1.0")
    """
    # Try package metadata first (works when installed)
    try:
        return version(APP_NAME)
    except PackageNotFoundError:
        pass

    # Try reading pyproject.toml from source tree (development mode)
    try:
        # Look for pyproject.toml in the project root
        # This assumes we're in a source checkout
        current_file = Path(__file__)
        # Navigate from src/tree_cloud_drive/core/paths.py to project root
        project_root = current_file.parent.parent.parent.parent
        pyproject_path = project_root / "pyproject.toml"
        if pyproject_path.exists():
            import tomllib  # Python 3.11+

            with pyproject_path.open("rb") as f:
                data = tomllib.load(f)
                if "project" in data and "version" in data["project"]:
                    return data["project"]["version"]
    except Exception:
        pass

    return _DEFAULT_VERSION


def qss_text(theme: str = "light") -> str:
    """Return the bundled QSS stylesheet as text for the given theme."""
    filename = "styles_dark.qss" if theme == "dark" else "styles.qss"
    return (files("tree_cloud_drive") / _ASSETS_DIR / filename).read_text(encoding="utf-8")


def app_icon_bytes() -> bytes:
    """Return the bundled app icon as PNG bytes."""
    return (files("tree_cloud_drive") / _ASSETS_DIR / "app_icon.png").read_bytes()
