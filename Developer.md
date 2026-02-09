# Developer Guide

**Setup**
Prerequisites:
- Install and configure `rclone` for your cloud provider.
- Python 3.13+

```bash
./scripts/setup-initial-dev-environment.sh
```

Or manually:
```bash
uv sync --dev
uv pip install -e .
```

**Run**
```bash
uv run tree-cloud-drive
```

**Dev checks**
```bash
uv run pytest
uv run ruff check .
uv run ruff format .
uv run pyright
```

**Versioning**
```bash
python scripts/bump-version.py X.Y.Z
```

**Project layout**
```
src/tree_cloud_drive/
  app.py              # App startup, exception hook, theme, icon
  main_window.py      # Main window UI + interactions
  core/
    exceptions.py     # Global exception hook
    paths.py          # Version + packaged asset helpers
    settings.py       # QSettings wrapper
    ui_loader.py      # Qt Designer .ui loader
    window_state.py   # Save/restore window state
    workers.py        # Background worker framework
  dialogs/
    about.py
    command_palette.py
    download_dialog.py
    error_dialog.py
    preferences.py
  assets/
    ui/               # Qt Designer .ui files
    styles.qss
    styles_dark.qss
    app_icon.png
```

**Where to start**
- `src/tree_cloud_drive/app.py` – startup + theme/icon wiring
- `src/tree_cloud_drive/main_window.py` – UI wiring + cloud browser
- `src/tree_cloud_drive/dialogs/download_dialog.py` – rclone download dialog
- `src/tree_cloud_drive/core/ui_loader.py` – .ui loader
- `src/tree_cloud_drive/core/workers.py` – worker framework
- `local/step-1-DO-THIS-FIRST.md` – quickstart checklist
