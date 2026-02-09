"""Update version strings across the project."""
# Author: Rich Lewis - GitHub: @RichLewis007

from __future__ import annotations

import re
import sys
from pathlib import Path


def replace_in_file(path: Path, pattern: str, repl: str) -> None:
    text = path.read_text()
    new_text, count = re.subn(pattern, repl, text, flags=re.MULTILINE)
    if count == 0:
        raise SystemExit(f"No matches for {pattern!r} in {path}")
    path.write_text(new_text)


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("Usage: python scripts/bump-version.py X.Y.Z")
    version = sys.argv[1].strip()
    if not re.match(r"^\\d+\\.\\d+\\.\\d+$", version):
        raise SystemExit("Version must look like X.Y.Z")

    repo_root = Path(__file__).resolve().parents[1]

    replace_in_file(
        repo_root / "pyproject.toml",
        r'^(version\\s*=\\s*")\\d+\\.\\d+\\.\\d+(")$',
        rf'\\1{version}\\2',
    )
    replace_in_file(
        repo_root / "README.md",
        r'^(\\*\\*Version:\\*\\*\\s*)\\d+\\.\\d+\\.\\d+$',
        rf'\\1{version}',
    )
    replace_in_file(
        repo_root / "src/tree_cloud_drive/app.py",
        r'^(#\\s*Version:\\s*)\\d+\\.\\d+\\.\\d+$',
        rf'\\1{version}',
    )
    replace_in_file(
        repo_root / "src/tree_cloud_drive/core/paths.py",
        r'^(_DEFAULT_VERSION\\s*=\\s*")\\d+\\.\\d+\\.\\d+(")',
        rf'\\1{version}\\2',
    )

    print(f"Updated version to {version}")


if __name__ == "__main__":
    main()
