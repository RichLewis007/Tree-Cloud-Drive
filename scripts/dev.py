#!/usr/bin/env python3
"""Development server with live reload for PySide6 app."""

import os
import signal
import subprocess
import sys
import time
from pathlib import Path

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer


class AppRestartHandler(FileSystemEventHandler):
    """Handles file changes and restarts the app."""
# Author: Rich Lewis - GitHub: @RichLewis007

    def __init__(self, script_path, restart_callback):
        super().__init__()
        self.script_path = script_path
        self.restart_callback = restart_callback
        self.last_restart = 0
        self.debounce_seconds = 0.5  # Wait 0.5s before restarting to avoid rapid restarts

    def should_restart(self, file_path):
        """Check if we should restart based on file extension."""
        path = Path(file_path)
        # Restart on Python or UI file changes
        return path.suffix in {".py", ".ui"}

    def on_modified(self, event):
        if event.is_directory:
            return
        if self.should_restart(event.src_path):
            current_time = time.time()
            # Debounce: don't restart too frequently
            if current_time - self.last_restart > self.debounce_seconds:
                self.last_restart = current_time
                print(f"\n🔄 File changed: {event.src_path}")
                print("   Restarting app...\n")
                self.restart_callback()


class DevServer:
    """Manages the development server with auto-reload."""

    def __init__(self, script_path):
        self.script_path = Path(script_path).resolve()
        self.process = None
        self.observer = None
        self.should_run = True

    def start_app(self):
        """Start the Python application."""
        if self.process:
            self.stop_app()

        env = os.environ.copy()
        # Run the app
        self.process = subprocess.Popen(
            [sys.executable, str(self.script_path)],
            env=env,
            stdout=sys.stdout,
            stderr=sys.stderr,
        )

    def stop_app(self):
        """Stop the running application."""
        if self.process:
            try:
                self.process.terminate()
                self.process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait()
            except ProcessLookupError:
                pass  # Process already dead
            self.process = None

    def restart_app(self):
        """Restart the application."""
        self.stop_app()
        time.sleep(0.2)  # Brief pause before restart
        self.start_app()

    def setup_watcher(self):
        """Set up file watchers for source and UI files."""
        project_root = self.script_path.parent.parent.parent
        src_dir = project_root / "src"
        ui_dir = project_root / "ui"

        event_handler = AppRestartHandler(self.script_path, self.restart_app)
        self.observer = Observer()

        if src_dir.exists():
            self.observer.schedule(event_handler, str(src_dir), recursive=True)
            print(f"📁 Watching: {src_dir}")

        if ui_dir.exists():
            self.observer.schedule(event_handler, str(ui_dir), recursive=True)
            print(f"📁 Watching: {ui_dir}")

        self.observer.start()

    def run(self):
        """Run the development server."""
        print("🚀 Starting development server with live reload...")
        print("   Press Ctrl+C to stop\n")

        # Handle Ctrl+C gracefully
        def signal_handler(sig, frame):
            print("\n\n🛑 Stopping development server...")
            self.should_run = False
            self.stop_app()
            if self.observer:
                self.observer.stop()
            sys.exit(0)

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

        # Start watching files
        self.setup_watcher()

        # Start the app initially
        self.start_app()

        # Keep running until interrupted
        try:
            while self.should_run:
                # Check if process died
                if self.process and self.process.poll() is not None:
                    print("\n⚠️  App exited. Restarting...\n")
                    self.start_app()
                time.sleep(0.5)
        except KeyboardInterrupt:
            signal_handler(None, None)


def main():
    """Main entry point."""
    # Find the main.py script
    script_dir = Path(__file__).parent.parent
    script_path = script_dir / "src" / "app" / "main.py"

    if not script_path.exists():
        print(f"❌ Error: Could not find {script_path}")
        sys.exit(1)

    server = DevServer(script_path)
    server.run()


if __name__ == "__main__":
    main()
