"""Main application window implementation.

This module provides the main window class that implements:
- Background worker execution with progress tracking
- Command palette integration
- Window state persistence (geometry and toolbar positions)
- Theme-aware UI

The UI layout is loaded from a Qt Designer .ui file, and widgets are
accessed programmatically for signal/slot connections.
"""
# Author: Rich Lewis - GitHub: @RichLewis007

from __future__ import annotations

import subprocess
import time

from PySide6.QtCore import QPoint, QSize, Qt, QTimer, Slot
from PySide6.QtGui import (
    QAction,
    QBrush,
    QColor,
    QIcon,
    QKeySequence,
    QPainter,
    QPixmap,
    QPolygon,
    QShortcut,
)
from PySide6.QtWidgets import (
    QDockWidget,
    QLabel,
    QComboBox,
    QMainWindow,
    QMenu,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QTabWidget,
    QTreeWidget,
    QTreeWidgetItem,
    QToolBar,
    QWidget,
)

from .core.paths import APP_NAME
from .core.settings import Settings
from .core.ui_loader import load_ui
from .core.window_state import WindowStateManager
from .core.workers import WorkContext, Worker, WorkerPool, WorkRequest
from .dialogs.command_palette import Command, CommandPalette
from .dialogs.download_dialog import DownloadDialog
from .dialogs.preferences import PreferencesDialog


class MainWindow(QMainWindow):
    """Main application window with comprehensive UI features and functionality."""

    def __init__(self, settings: Settings, instance_guard=None) -> None:
        super().__init__()
        self.settings = settings
        self.pool = WorkerPool()
        self.window_state = WindowStateManager(settings, self)
        self.action_work: QAction
        self.action_prefs: QAction
        self.action_quit: QAction
        self.action_about: QAction
        self.active_worker: Worker[str] | None
        self.label: QLabel
        self.progress_bar: QProgressBar
        self.btn_work: QPushButton
        self.btn_cancel: QPushButton
        self.btn_prefs: QPushButton
        self.remote_combo: QComboBox
        self.folder_combo: QComboBox
        self.folder_tree: QTreeWidget
        self.ui: QWidget
        self.tab_widget: QTabWidget
        self.view_menu: QMenu
        self.remote_worker: Worker[list[str]] | None
        self.folder_worker: Worker[list[str]] | None
        self.tree_worker: Worker[list[str]] | None
        self._tree_remote: str | None

        self.setWindowTitle(APP_NAME)

        self._build_actions()
        self._build_menus()  # Build menus before loading UI so dock widgets can add to View menu
        self._load_ui()
        self.active_worker = None
        self.remote_worker = None
        self.folder_worker = None
        self.tree_worker = None
        self._tree_remote = None

        # Create horizontal toolbar with square icon buttons
        toolbar = self._create_toolbar()
        self.addToolBar(toolbar)

        self.btn_work.clicked.connect(self.on_run_work)
        self.btn_cancel.clicked.connect(self.on_cancel_work)
        self.btn_prefs.clicked.connect(self.on_open_prefs)
        self.remote_combo.currentIndexChanged.connect(self._on_remote_selected)
        self.folder_combo.currentIndexChanged.connect(self._on_folder_selected)
        self.folder_tree.itemExpanded.connect(self._on_tree_item_expanded)
        self.folder_tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.folder_tree.customContextMenuRequested.connect(self._on_tree_context_menu)

        # Restore window geometry and state
        self.window_state.restore_state()

        # Setup command palette
        self._setup_command_palette()

        # Load available remotes on startup
        self._load_remotes()

    def _build_actions(self) -> None:
        self.action_work = QAction("Run background work", self)
        self.action_work.triggered.connect(self.on_run_work)

        self.action_prefs = QAction("Preferences", self)
        self.action_prefs.triggered.connect(self.on_open_prefs)

        self.action_quit = QAction("Quit", self)
        self.action_quit.setShortcut(QKeySequence.StandardKey.Quit)
        self.action_quit.triggered.connect(self.on_quit)

        self.action_about = QAction("About", self)
        # Set role for macOS native menu integration
        # On macOS, this makes the action appear in the app menu
        # (e.g., "About tree-cloud-drive")
        self.action_about.setMenuRole(QAction.MenuRole.AboutRole)
        self.action_about.triggered.connect(self.on_about)

    def _create_toolbar(self) -> QToolBar:
        """Create a horizontal toolbar with square icon buttons."""
        toolbar = QToolBar("Main", self)
        toolbar.setObjectName("mainToolBar")  # Required for window state persistence

        # Set toolbar to use icon-only mode with square buttons
        toolbar.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)

        # Set icon size for square buttons (e.g., 32x32)
        icon_size = QSize(32, 32)
        toolbar.setIconSize(icon_size)

        # Create icons for actions
        self.action_work.setIcon(self._create_icon_for_action("work"))
        self.action_prefs.setIcon(self._create_icon_for_action("preferences"))
        self.action_quit.setIcon(self._create_icon_for_action("quit"))

        # Add actions to toolbar
        toolbar.addAction(self.action_work)
        toolbar.addAction(self.action_prefs)
        toolbar.addSeparator()  # Visual separator before quit button
        toolbar.addAction(self.action_quit)

        return toolbar

    def _create_icon_for_action(self, action_name: str) -> QIcon:
        """Create an icon for a toolbar action.

        Creates simple colored square icons with symbols.
        Can be extended to load from image files.
        """
        # Create a colored square pixmap for the icon
        size = 32
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.GlobalColor.transparent)

        # Create painter to draw the icon
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Different colors for different actions
        colors = {
            "work": QColor(46, 204, 113),  # Green
            "preferences": QColor(155, 89, 182),  # Purple
            "quit": QColor(231, 76, 60),  # Red
        }
        color = colors.get(action_name, QColor(149, 165, 166))  # Gray default

        # Draw filled rounded rectangle
        margin = 2
        painter.fillRect(margin, margin, size - 2 * margin, size - 2 * margin, color)

        # Add a simple symbol based on action
        painter.setPen(QColor(255, 255, 255))  # White pen
        painter.setFont(painter.font())

        if action_name == "work":
            # Draw play icon (triangle)
            center = pixmap.rect().center()
            triangle = QPolygon(
                [
                    QPoint(center.x() - 6, center.y()),
                    QPoint(center.x() + 6, center.y() - 6),
                    QPoint(center.x() + 6, center.y() + 6),
                ]
            )
            painter.setBrush(QBrush(QColor(255, 255, 255)))
            painter.drawPolygon(triangle)
        elif action_name == "preferences":
            # Draw gear icon (simplified - circles)
            center = pixmap.rect().center()
            painter.drawEllipse(center, 6, 6)
            painter.drawEllipse(center, 10, 10)
        elif action_name == "quit":
            # Draw X icon (exit/close symbol)
            center = pixmap.rect().center()
            # Draw two diagonal lines forming an X
            margin = 8
            painter.drawLine(
                center.x() - margin, center.y() - margin, center.x() + margin, center.y() + margin
            )
            painter.drawLine(
                center.x() + margin, center.y() - margin, center.x() - margin, center.y() + margin
            )

        painter.end()

        return QIcon(pixmap)

    def _build_menus(self) -> None:
        file_menu = self.menuBar().addMenu("&File")
        file_menu.addAction(self.action_prefs)
        file_menu.addSeparator()
        file_menu.addAction(self.action_quit)

        view_menu = self.menuBar().addMenu("&View")
        # Add toggle actions for dock widgets (will be populated after docks are created)
        self.view_menu = view_menu

        help_menu = self.menuBar().addMenu("&Help")
        help_menu.addAction(self.action_about)

    def _load_ui(self) -> None:
        # Create tab widget to organize different content areas
        self.tab_widget = QTabWidget(self)

        # Tab 1: Main UI
        self.ui = load_ui("main_window.ui", self)
        self.tab_widget.addTab(self.ui, "Main")

        # Set tab widget as central widget
        self.setCentralWidget(self.tab_widget)

        # Create dock widgets for additional content
        self._create_dock_widgets()

        label = self.ui.findChild(QLabel, "statusLabel")
        if label is None:
            raise RuntimeError("statusLabel not found in main_window.ui")
        self.label = label

        progress_bar = self.ui.findChild(QProgressBar, "progressBar")
        if progress_bar is None:
            raise RuntimeError("progressBar not found in main_window.ui")
        self.progress_bar = progress_bar
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setFormat("Idle")

        btn_work = self.ui.findChild(QPushButton, "workButton")
        if btn_work is None:
            raise RuntimeError("workButton not found in main_window.ui")
        self.btn_work = btn_work

        btn_cancel = self.ui.findChild(QPushButton, "cancelButton")
        if btn_cancel is None:
            raise RuntimeError("cancelButton not found in main_window.ui")
        self.btn_cancel = btn_cancel
        self.btn_cancel.setEnabled(False)

        btn_prefs = self.ui.findChild(QPushButton, "prefsButton")
        if btn_prefs is None:
            raise RuntimeError("prefsButton not found in main_window.ui")
        self.btn_prefs = btn_prefs

        remote_combo = self.ui.findChild(QComboBox, "remoteCombo")
        if remote_combo is None:
            raise RuntimeError("remoteCombo not found in main_window.ui")
        self.remote_combo = remote_combo
        self.remote_combo.clear()
        self.remote_combo.addItem("Select a remote...")

        folder_combo = self.ui.findChild(QComboBox, "folderCombo")
        if folder_combo is None:
            raise RuntimeError("folderCombo not found in main_window.ui")
        self.folder_combo = folder_combo
        self.folder_combo.clear()
        self.folder_combo.addItem("Select a folder...")
        self.folder_combo.setEnabled(False)

        folder_tree = self.ui.findChild(QTreeWidget, "folderTree")
        if folder_tree is None:
            raise RuntimeError("folderTree not found in main_window.ui")
        self.folder_tree = folder_tree
        self.folder_tree.clear()
        self.folder_tree.setHeaderHidden(True)

    def _set_tree_placeholder(self, item: QTreeWidgetItem) -> None:
        placeholder = QTreeWidgetItem(["Loading..."])
        item.addChild(placeholder)

    def _clear_tree_placeholder(self, item: QTreeWidgetItem) -> None:
        for idx in range(item.childCount()):
            child = item.child(idx)
            if child and child.text(0) == "Loading...":
                item.removeChild(child)
                break

    def _set_item_loaded(self, item: QTreeWidgetItem, loaded: bool) -> None:
        item.setData(0, Qt.ItemDataRole.UserRole + 1, loaded)

    def _is_item_loaded(self, item: QTreeWidgetItem) -> bool:
        return bool(item.data(0, Qt.ItemDataRole.UserRole + 1))

    def _set_item_path(self, item: QTreeWidgetItem, path: str) -> None:
        item.setData(0, Qt.ItemDataRole.UserRole, path)

    def _get_item_path(self, item: QTreeWidgetItem) -> str:
        value = item.data(0, Qt.ItemDataRole.UserRole)
        return str(value) if value is not None else ""

    def _set_status(self, message: str, timeout_ms: int = 2000) -> None:
        self.label.setText(message)
        self.statusBar().showMessage(message, timeout_ms)

    def _run_rclone(self, args: list[str]) -> list[str]:
        result = subprocess.run(
            ["rclone", *args],
            check=False,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            msg = result.stderr.strip() or result.stdout.strip() or "Unknown rclone error"
            raise RuntimeError(msg)
        return [line.strip() for line in result.stdout.splitlines() if line.strip()]

    def _load_remotes(self) -> None:
        if self.remote_worker is not None:
            self.remote_worker.cancel()
            self.remote_worker = None

        self.remote_combo.setEnabled(False)
        self.remote_combo.clear()
        self.remote_combo.addItem("Loading remotes...")
        self.folder_combo.setEnabled(False)
        self.folder_combo.clear()
        self.folder_combo.addItem("Select a folder...")
        self.folder_tree.clear()
        self._set_status("Loading cloud remotes...")

        def work(ctx: WorkContext) -> list[str]:
            ctx.check_cancelled()
            remotes = self._run_rclone(["listremotes"])
            return [remote.rstrip(":") for remote in remotes]

        def done(remotes: list[str]) -> None:
            self.remote_combo.clear()
            self.remote_combo.addItem("Select a remote...")
            if remotes:
                self.remote_combo.addItems(sorted(remotes))
            self.remote_combo.setEnabled(True)
            self._set_status("Select a cloud remote.")
            self.remote_worker = None

        def error(msg: str) -> None:
            self.remote_combo.clear()
            self.remote_combo.addItem("Select a remote...")
            self.remote_combo.setEnabled(True)
            self.remote_worker = None
            QMessageBox.critical(self, "Rclone error", msg)
            self._set_status("Failed to load remotes.")

        req = WorkRequest(fn=work, on_done=done, on_error=error)
        self.remote_worker = self.pool.submit(req)

    def _on_remote_selected(self) -> None:
        idx = self.remote_combo.currentIndex()
        if idx <= 0:
            self.folder_combo.setEnabled(False)
            self.folder_combo.clear()
            self.folder_combo.addItem("Select a folder...")
            self.folder_tree.clear()
            return
        remote = self.remote_combo.currentText()
        self._load_top_level_dirs(remote)

    def _load_top_level_dirs(self, remote: str) -> None:
        if self.folder_worker is not None:
            self.folder_worker.cancel()
            self.folder_worker = None

        self.folder_combo.setEnabled(False)
        self.folder_combo.clear()
        self.folder_combo.addItem("Loading folders...")
        self.folder_tree.clear()
        self._set_status(f"Loading folders from {remote}...")

        def work(ctx: WorkContext) -> list[str]:
            ctx.check_cancelled()
            dirs = self._run_rclone(["lsf", "--dirs-only", "--max-depth", "1", f"{remote}:"])
            return [d.rstrip("/") for d in dirs]

        def done(dirs: list[str]) -> None:
            self.folder_combo.clear()
            self.folder_combo.addItem("Select a folder...")
            if dirs:
                self.folder_combo.addItems(sorted(dirs))
                self.folder_combo.setEnabled(True)
                self._set_status("Select a top-level folder.")
            else:
                self.folder_combo.setEnabled(False)
                self._set_status("No folders found in remote.")
            self.folder_worker = None

        def error(msg: str) -> None:
            self.folder_combo.clear()
            self.folder_combo.addItem("Select a folder...")
            self.folder_combo.setEnabled(False)
            self.folder_worker = None
            QMessageBox.critical(self, "Rclone error", msg)
            self._set_status("Failed to load folders.")

        req = WorkRequest(fn=work, on_done=done, on_error=error)
        self.folder_worker = self.pool.submit(req)

    def _on_folder_selected(self) -> None:
        if self.remote_combo.currentIndex() <= 0:
            return
        idx = self.folder_combo.currentIndex()
        if idx <= 0:
            self.folder_tree.clear()
            return
        remote = self.remote_combo.currentText()
        folder = self.folder_combo.currentText()
        self._load_folder_tree(remote, folder)

    def _load_folder_tree(self, remote: str, folder: str) -> None:
        if self.tree_worker is not None:
            self.tree_worker.cancel()
            self.tree_worker = None

        self.folder_tree.clear()
        self._tree_remote = remote
        self._set_status(f"Loading {remote}:{folder}...")

        root_item = QTreeWidgetItem([folder])
        self._set_item_path(root_item, folder)
        self._set_item_loaded(root_item, False)
        self._set_tree_placeholder(root_item)
        self.folder_tree.addTopLevelItem(root_item)
        root_item.setExpanded(True)

        def work(ctx: WorkContext) -> list[str]:
            ctx.check_cancelled()
            dirs = self._run_rclone(["lsf", "--dirs-only", "--max-depth", "1", f"{remote}:{folder}"])
            return [d.rstrip("/") for d in dirs]

        def done(dirs: list[str]) -> None:
            self._clear_tree_placeholder(root_item)
            self._populate_children(root_item, dirs)
            self._set_item_loaded(root_item, True)
            self._set_status(f"Loaded {remote}:{folder}")
            self.tree_worker = None

        def error(msg: str) -> None:
            self.folder_tree.clear()
            self.tree_worker = None
            QMessageBox.critical(self, "Rclone error", msg)
            self._set_status("Failed to load folder tree.")

        req = WorkRequest(fn=work, on_done=done, on_error=error)
        self.tree_worker = self.pool.submit(req)

    def _populate_children(self, parent: QTreeWidgetItem, paths: list[str]) -> None:
        base_path = self._get_item_path(parent)
        for path in sorted(paths):
            name = path.split("/")[-1] if path else path
            item = QTreeWidgetItem([name])
            full_path = f"{base_path}/{path}" if base_path else path
            self._set_item_path(item, full_path)
            self._set_item_loaded(item, False)
            self._set_tree_placeholder(item)
            parent.addChild(item)

    def _on_tree_item_expanded(self, item: QTreeWidgetItem) -> None:
        if self._tree_remote is None:
            return
        if self._is_item_loaded(item):
            return
        path = self._get_item_path(item)
        if not path:
            return
        self._load_children_for_item(item, self._tree_remote, path)

    def _load_children_for_item(
        self, item: QTreeWidgetItem, remote: str, path: str
    ) -> None:
        if self.tree_worker is not None:
            self.tree_worker.cancel()
            self.tree_worker = None

        self._set_status(f"Loading {remote}:{path}...")

        def work(ctx: WorkContext) -> list[str]:
            ctx.check_cancelled()
            dirs = self._run_rclone(["lsf", "--dirs-only", "--max-depth", "1", f"{remote}:{path}"])
            return [d.rstrip("/") for d in dirs]

        def done(dirs: list[str]) -> None:
            self._clear_tree_placeholder(item)
            self._populate_children(item, dirs)
            self._set_item_loaded(item, True)
            self._set_status(f"Loaded {remote}:{path}")
            self.tree_worker = None

        def error(msg: str) -> None:
            self._clear_tree_placeholder(item)
            self.tree_worker = None
            QMessageBox.critical(self, "Rclone error", msg)
            self._set_status("Failed to load folder.")

        req = WorkRequest(fn=work, on_done=done, on_error=error)
        self.tree_worker = self.pool.submit(req)

    def _on_tree_context_menu(self, pos) -> None:  # type: ignore[override]
        item = self.folder_tree.itemAt(pos)
        if item is None or self._tree_remote is None:
            return
        path = self._get_item_path(item)
        if not path:
            return
        menu = QMenu(self)
        download_action = menu.addAction("Download folder")
        selected = menu.exec(self.folder_tree.mapToGlobal(pos))
        if selected == download_action:
            remote_path = f"{self._tree_remote}:{path}"
            dlg = DownloadDialog(remote_path=remote_path, parent=self)
            dlg.exec()

    def _create_dock_widgets(self) -> None:
        """Create dock widgets for additional content areas."""
        # Info dock widget
        info_dock = QDockWidget("Information", self)
        info_dock.setObjectName("informationDock")  # Required for window state persistence

        # Load UI from .ui file
        info_widget = load_ui("information_dock.ui", self)
        info_dock.setWidget(info_widget)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, info_dock)
        # Add toggle action to View menu
        self.view_menu.addAction(info_dock.toggleViewAction())

        # Splitter demo dock (optional - can be shown via View menu)
        splitter_dock = QDockWidget("Splitter Demo", self)
        splitter_dock.setObjectName("splitterDemoDock")  # Required for window state persistence

        # Load UI from .ui file
        splitter_widget = load_ui("splitter_dock.ui", self)
        splitter_dock.setWidget(splitter_widget)
        # Start with info dock visible, splitter hidden
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, splitter_dock)
        splitter_dock.setVisible(False)
        # Add toggle action to View menu
        self.view_menu.addAction(splitter_dock.toggleViewAction())

    @Slot()
    def on_open_prefs(self) -> None:
        """Open the preferences dialog and handle theme changes."""
        dlg = PreferencesDialog(settings=self.settings, parent=self)
        dlg.theme_changed.connect(self._on_theme_changed)
        dlg.exec()

    def _on_theme_changed(self, theme: str) -> None:
        """Handle theme change from preferences dialog.

        Applies the new theme to both this window and the QApplication
        so dialogs inherit the theme.

        Args:
            theme: Theme name (e.g., "light" or "dark")
        """
        from .core.paths import qss_text

        try:
            qss = qss_text(theme)
            # Apply to this window
            self.setStyleSheet(qss)
            # Also update the QApplication so dialogs inherit the theme
            from PySide6.QtWidgets import QApplication

            app = QApplication.instance()
            if app and isinstance(app, QApplication):
                app.setStyleSheet(qss)
            self.statusBar().showMessage(f"Theme changed to {theme}", 2000)
        except FileNotFoundError:
            QMessageBox.warning(self, "Theme", f"Stylesheet not found for theme: {theme}")

    @Slot()
    def on_about(self) -> None:
        from .core.paths import app_version
        from .dialogs.about import AboutDialog

        dlg = AboutDialog(version=app_version(), release_notes_url="", parent=self)
        dlg.exec()

    def _set_working_state(self, working: bool) -> None:
        """Update UI state to reflect whether background work is running.

        Args:
            working: True if work is in progress, False otherwise
        """
        self.btn_work.setEnabled(not working)
        self.action_work.setEnabled(not working)
        self.btn_cancel.setEnabled(working)

    @Slot()
    def on_run_work(self) -> None:
        """Start a background work task with progress tracking.

        Demonstrates the worker system with a simple task that:
        - Runs in a background thread
        - Reports progress updates
        - Supports cancellation
        - Updates UI safely via signals/callbacks
        """
        if self.active_worker is not None:
            QMessageBox.information(self, "Background work", "Work is already running.")
            return

        # Initialize UI for work
        self.label.setText("Working in background...")
        self.statusBar().showMessage("Working in background...")
        self.progress_bar.setValue(0)
        self.progress_bar.setFormat("Working... %p%")
        self._set_working_state(True)

        def work(ctx: WorkContext) -> str:
            """Background work function - runs in worker thread.

            This function demonstrates:
            - Checking for cancellation
            - Reporting progress
            - Returning a result
            """
            steps = 10
            for step in range(steps):
                ctx.check_cancelled()  # Cooperative cancellation check
                time.sleep(0.25)  # Simulate work
                percent = int(((step + 1) / steps) * 100)
                ctx.progress(percent, f"Step {step + 1} of {steps}")
            return "Done."

        def progress(percent: int, message: str) -> None:
            """Progress callback - runs on main thread via signal."""
            self.progress_bar.setValue(percent)
            if message:
                self.label.setText(message)
                self.statusBar().showMessage(message, 2000)

        def done(result: str) -> None:
            """Completion callback - runs on main thread when worker finishes."""
            self.progress_bar.setValue(100)
            self.progress_bar.setFormat("Done")
            self.label.setText(result)
            self.statusBar().showMessage("Background work finished", 3000)
            self._set_working_state(False)
            self.active_worker = None

        def cancelled() -> None:
            """Cancellation callback - runs on main thread when work is cancelled."""
            self.progress_bar.setValue(0)
            self.progress_bar.setFormat("Cancelled")
            self.label.setText("Cancelled")
            self.statusBar().showMessage("Background work cancelled", 3000)
            self._set_working_state(False)
            self.active_worker = None

        def error(msg: str) -> None:
            """Error callback - runs on main thread when work fails."""
            self.progress_bar.setValue(0)
            self.progress_bar.setFormat("Error")
            self.label.setText("Error")
            self.statusBar().showMessage("Background work failed", 3000)
            self._set_working_state(False)
            self.active_worker = None
            QMessageBox.critical(self, "Worker error", msg)

        req = WorkRequest(
            fn=work,
            on_done=done,
            on_error=error,
            on_progress=progress,
            on_cancel=cancelled,
        )
        self.active_worker = self.pool.submit(req)

    @Slot()
    def on_cancel_work(self) -> None:
        """Cancel the currently running background work task.

        Sends a cancellation request to the worker and updates the UI.
        The worker will check for cancellation at the next check_cancelled()
        call and exit cooperatively.
        """
        if self.active_worker is None:
            return
        self.active_worker.cancel()
        self.label.setText("Cancel requested...")
        self.statusBar().showMessage("Cancel requested...", 3000)
        self.btn_cancel.setEnabled(False)

    @Slot()
    def on_quit(self) -> None:
        """Handle quit action with proper cleanup.

        Checks for running background workers and handles them appropriately.
        If a worker is running, asks the user if they want to cancel it and exit.
        """
        # Check if there's an active worker
        if self.active_worker is not None:
            reply = QMessageBox.question(
                self,
                "Exit Application",
                "A background task is currently running.\n\n"
                "Do you want to cancel the task and exit?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )

            if reply == QMessageBox.StandardButton.No:
                # User cancelled the quit dialog
                return
            # User chose Yes - cancel the worker and exit
            self.active_worker.cancel()
            self.label.setText("Cancelling task before exit...")
            self.statusBar().showMessage("Cancelling task before exit...", 2000)

            # Give the worker a brief moment to cancel cooperatively
            # The closeEvent will also handle cleanup if the worker is still running
            def delayed_close() -> None:
                """Close after a brief delay to allow cancellation."""
                self.close()

            QTimer.singleShot(500, delayed_close)  # Wait 500ms
            return

        # No active worker - exit immediately
        self.close()

    def _setup_command_palette(self) -> None:
        """Initialize command palette with commands and keyboard shortcut."""
        commands = [
            Command(
                name="Run Background Work",
                description="Execute background task",
                shortcut="",
                action=self.on_run_work,
            ),
            Command(
                name="Preferences",
                description="Open preferences dialog",
                shortcut="Ctrl+,",
                action=self.on_open_prefs,
            ),
            Command(
                name="About",
                description="Show about dialog",
                shortcut="",
                action=self.on_about,
            ),
            Command(
                name="Quit",
                description="Exit the application",
                shortcut="Ctrl+Q",
                action=lambda: [self.close(), None][1],  # type: ignore[return-value]
            ),
        ]

        # Create command palette shortcut (Ctrl+K or Ctrl+P)
        cmd_palette_shortcut = QShortcut(QKeySequence("Ctrl+K"), self)
        cmd_palette_shortcut.activated.connect(lambda: self._show_command_palette(commands))

        # Alternative shortcut (Ctrl+Shift+P like VS Code)
        cmd_palette_shortcut2 = QShortcut(QKeySequence("Ctrl+Shift+P"), self)
        cmd_palette_shortcut2.activated.connect(lambda: self._show_command_palette(commands))

    def _show_command_palette(self, commands: list[Command]) -> None:
        """Show the command palette dialog and execute selected command.

        Args:
            commands: List of Command objects to display in the palette
        """
        palette = CommandPalette(commands, self)
        # Position dialog centered horizontally near top of window
        palette.move(
            self.geometry().center().x() - palette.width() // 2,
            self.geometry().top() + 50,
        )
        # Execute command if one was selected
        if (
            palette.exec() == palette.DialogCode.Accepted
            and palette.selected_command
            and palette.selected_command.action
        ):
            palette.selected_command.action()

    def closeEvent(self, event) -> None:  # type: ignore[override]
        """Save window state before closing and cleanup resources."""
        # Cancel any active worker if still running
        if self.active_worker is not None:
            self.active_worker.cancel()
            self.active_worker = None

        # Save window state
        self.window_state.save_state()

        super().closeEvent(event)
