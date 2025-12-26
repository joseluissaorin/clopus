# =============================================================================
# CLOPUS v3 Interface Layer
# =============================================================================
"""
Interface adapters for CLOPUS interaction.
Supports CLI, file-based, and webhook interfaces.
"""

from .base import InterfaceAdapter
from .cli_adapter import CLIAdapter
from .file_adapter import FileAdapter

__all__ = ["InterfaceAdapter", "CLIAdapter", "FileAdapter"]
