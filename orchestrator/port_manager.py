# =============================================================================
# CLOPUS v3 Port Manager
# =============================================================================
"""
Dynamic port allocation with availability checking.
"""

import socket
import json
from pathlib import Path
from typing import Optional
import logging

logger = logging.getLogger("clopus.port_manager")


class PortManager:
    """Manages dynamic port allocation for project dev servers."""

    # Common ports to avoid (often already in use)
    RESERVED_PORTS = {
        80, 443,          # HTTP/HTTPS
        22,               # SSH
        3000, 3001,       # Common dev ports
        5432,             # PostgreSQL
        6379,             # Redis
        5173, 5174,       # Vite defaults
        8080, 8000, 8888, # Common web servers
        5000,             # Flask
        4000,             # Phoenix
        9000,             # PHP-FPM
    }

    # Port range for CLOPUS projects
    PORT_RANGE_START = 3100
    PORT_RANGE_END = 3199

    def __init__(self, registry_path: str = "/workspace/.clopus-ports.json"):
        self.registry_path = Path(registry_path)
        self._load_registry()

    def _load_registry(self) -> None:
        """Load port registry from file."""
        if self.registry_path.exists():
            try:
                self.registry = json.loads(self.registry_path.read_text())
            except Exception:
                self.registry = {}
        else:
            self.registry = {}

    def _save_registry(self) -> None:
        """Save port registry to file."""
        try:
            self.registry_path.parent.mkdir(parents=True, exist_ok=True)
            self.registry_path.write_text(json.dumps(self.registry, indent=2))
        except Exception as e:
            logger.error(f"Error saving port registry: {e}")

    def is_port_available(self, port: int) -> bool:
        """Check if a port is available for use."""
        if port in self.RESERVED_PORTS:
            return False

        # Try to bind to the port
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            result = sock.connect_ex(('127.0.0.1', port))
            sock.close()
            # If connect_ex returns 0, port is in use
            return result != 0
        except Exception:
            return False

    def get_project_port(self, project_name: str) -> int:
        """
        Get or allocate a port for a project.

        If the project already has an assigned port that's available, use it.
        Otherwise, find a new available port.
        """
        # Check if project already has a port
        if project_name in self.registry:
            assigned_port = self.registry[project_name]
            if self.is_port_available(assigned_port):
                logger.info(f"Reusing port {assigned_port} for {project_name}")
                return assigned_port

        # Find a new available port
        port = self._find_available_port(project_name)

        # Register the port
        self.registry[project_name] = port
        self._save_registry()

        return port

    def _find_available_port(self, project_name: str) -> int:
        """Find an available port for a project."""
        # Start with a hash-based port for consistency
        base_port = self.PORT_RANGE_START + (hash(project_name) % 100)

        # Try the hash-based port first
        if self.is_port_available(base_port):
            logger.info(f"Allocated port {base_port} for {project_name}")
            return base_port

        # Scan the range for an available port
        for port in range(self.PORT_RANGE_START, self.PORT_RANGE_END):
            if port not in self.registry.values() and self.is_port_available(port):
                logger.info(f"Allocated port {port} for {project_name} (fallback)")
                return port

        # Last resort: scan outside our range
        for port in range(3200, 4000):
            if self.is_port_available(port):
                logger.warning(f"Allocated out-of-range port {port} for {project_name}")
                return port

        raise RuntimeError(f"No available ports found for {project_name}")

    def release_port(self, project_name: str) -> None:
        """Release a port allocation for a project."""
        if project_name in self.registry:
            del self.registry[project_name]
            self._save_registry()
            logger.info(f"Released port for {project_name}")

    def get_all_allocations(self) -> dict:
        """Get all current port allocations."""
        return self.registry.copy()


# Global instance
_port_manager: Optional[PortManager] = None


def get_port_manager() -> PortManager:
    """Get the global port manager instance."""
    global _port_manager
    if _port_manager is None:
        _port_manager = PortManager()
    return _port_manager
