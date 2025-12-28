#!/usr/bin/env python3
"""CLOPUS TUI Entry Point"""

import argparse
import sys


def main():
    """Main entry point for CLOPUS TUI"""
    parser = argparse.ArgumentParser(
        description="CLOPUS Terminal User Interface",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  clopus-tui                    Start the TUI (light theme, websocket enabled)
  clopus-tui --dark             Start with dark theme
  clopus-tui --no-websocket     Start without WebSocket (uses mock data)

Keyboard shortcuts (in TUI):
  d     Dashboard
  w     Workers
  p     Projects
  t     Tasks
  l     Logs
  o     Objectives
  ?     Help
  Ctrl+Q  Quit
        """
    )

    parser.add_argument(
        "--no-websocket", "-nw",
        action="store_true",
        help="Disable WebSocket real-time updates (use mock client instead)"
    )

    parser.add_argument(
        "--dark",
        action="store_true",
        help="Start with dark theme (default is light)"
    )

    parser.add_argument(
        "--no-notifications",
        action="store_true",
        help="Disable desktop notifications"
    )

    parser.add_argument(
        "--screen",
        choices=["dashboard", "workers", "projects", "tasks", "logs", "objectives", "memory", "questions", "config", "browser"],
        default="dashboard",
        help="Initial screen to show"
    )

    args = parser.parse_args()

    try:
        from .app import CLOPUSApp
    except ImportError:
        # Handle direct execution
        sys.path.insert(0, str(__file__).rsplit("/", 2)[0])
        from tui.app import CLOPUSApp

    # Default: websocket enabled, light theme
    app = CLOPUSApp(use_websocket=not args.no_websocket)

    # Default is light theme (dark=False), switch to dark if --dark flag
    app.dark = args.dark

    app.run()


if __name__ == "__main__":
    main()
