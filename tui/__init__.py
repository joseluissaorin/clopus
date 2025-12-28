"""
CLOPUS TUI - Terminal User Interface for CLOPUS

A comprehensive terminal interface for monitoring and controlling
the CLOPUS autonomous agent system.
"""

__version__ = "1.0.0"

from .app import CLOPUSApp, run_tui
from .main import main

__all__ = ["CLOPUSApp", "run_tui", "main"]
