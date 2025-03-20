#!/usr/bin/env bash
# Author: Rich Lewis - GitHub: @RichLewis007
set -euo pipefail

# Ensure we run from repo root so tooling config is discovered.
SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
REPO_ROOT=$(cd "${SCRIPT_DIR}/.." && pwd)

cd "${REPO_ROOT}"

uv run pytest
