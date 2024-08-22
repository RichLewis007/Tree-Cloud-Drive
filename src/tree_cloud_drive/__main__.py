"""Package entry point for command-line execution.

This module provides the console script entry point for the application.
When run as `python -m tree_cloud_drive` or via the console script,
it calls the main run() function from the app module.
"""
# Author: Rich Lewis - GitHub: @RichLewis007

from __future__ import annotations

import argparse

from .app import run


def main() -> int:
    """Entry point for the console script.

    Parses command-line arguments and runs the application.

    Returns:
        Exit code from the application (0 for success).
    """
    parser = argparse.ArgumentParser(description="tree cloud drive Application")
    splash_group = parser.add_mutually_exclusive_group()
    splash_group.add_argument(
        "--splash-seconds",
        type=int,
        metavar="N",
        help="Show splash screen for N seconds (0 = show until user clicks OK)",
    )
    splash_group.add_argument(
        "--no-splash",
        action="store_true",
        help="Don't show splash screen on startup (overrides settings)",
    )

    args = parser.parse_args()

    # Handle splash screen arguments (mutually exclusive, so only one can be set)
    if args.no_splash:
        # Explicitly don't show splash screen (override settings)
        return run(force_no_splash=True)
    elif getattr(args, "splash_seconds", None) is not None:
        # Explicitly set splash screen duration
        return run(splash_screen_seconds=args.splash_seconds)
    else:
        # No argument provided - check settings (pass None to let app.py check settings)
        return run(splash_screen_seconds=None)


if __name__ == "__main__":
    raise SystemExit(main())
