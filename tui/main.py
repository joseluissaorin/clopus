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
  python -m tui.main              Start the TUI (light theme by default)
  python -m tui.main --dark       Start with dark theme
  python -m tui.main --websocket  Enable WebSocket real-time updates

Keyboard shortcuts (in TUI):
  d     Dashboard
  w     Workers
  p     Projects
  t     Tasks
  l     Logs
  o     Objectives
  F1    Help
  Ctrl+T  Toggle theme
  Ctrl+Q  Quit
        """
    )

    parser.add_argument(
        "--websocket", "-ws",
        action="store_true",
        help="Enable WebSocket real-time updates"
    )

    parser.add_argument(
        "--dark",
        action="store_true",
        help="Start with dark theme (default is light)"
    )

    parser.add_argument(
        "--light",
        action="store_true",
        help="Start with light theme (this is the default)"
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
        import os
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        from tui.app import CLOPUSApp

    # Determine theme: dark if --dark, light if --light or default
    start_dark = args.dark and not args.light

    app = CLOPUSApp(
        use_websocket=args.websocket,
        start_dark=start_dark
    )
    app.run()


if __name__ == "__main__":
    main()
