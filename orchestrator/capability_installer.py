# =============================================================================
# CLOPUS v3 Capability Installer
# =============================================================================
"""
Installs tools and capabilities on-demand in worker containers.
"""

import asyncio
import logging
import subprocess
from typing import Dict, List, Optional

logger = logging.getLogger("clopus.capability_installer")


# Tool installation commands by category
TOOL_INSTALLERS = {
    # Languages
    "python": "apt-get update && apt-get install -y python3 python3-pip",
    "node": "curl -fsSL https://deb.nodesource.com/setup_20.x | bash - && apt-get install -y nodejs",
    "go": "apt-get update && apt-get install -y golang-go",
    "rust": "curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y",
    "ruby": "apt-get update && apt-get install -y ruby-full",
    "php": "apt-get update && apt-get install -y php php-cli php-mbstring",
    "java": "apt-get update && apt-get install -y openjdk-17-jdk",

    # Media
    "ffmpeg": "apt-get update && apt-get install -y ffmpeg",
    "imagemagick": "apt-get update && apt-get install -y imagemagick",
    "whisper": "pip install openai-whisper",
    "yt-dlp": "pip install yt-dlp",

    # DevOps
    "docker": "curl -fsSL https://get.docker.com | sh",
    "kubectl": "curl -LO https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl && chmod +x kubectl && mv kubectl /usr/local/bin/",
    "terraform": "apt-get update && apt-get install -y gnupg software-properties-common && wget -O- https://apt.releases.hashicorp.com/gpg | gpg --dearmor -o /usr/share/keyrings/hashicorp-archive-keyring.gpg && echo 'deb [signed-by=/usr/share/keyrings/hashicorp-archive-keyring.gpg] https://apt.releases.hashicorp.com $(lsb_release -cs) main' > /etc/apt/sources.list.d/hashicorp.list && apt-get update && apt-get install -y terraform",
    "ansible": "pip install ansible",

    # Mobile
    "expo": "npm install -g expo-cli",
    "react-native": "npm install -g react-native-cli",
    "flutter": "git clone https://github.com/flutter/flutter.git -b stable /opt/flutter && export PATH=$PATH:/opt/flutter/bin",

    # Cloud CLIs
    "aws": "pip install awscli",
    "gcloud": "curl https://sdk.cloud.google.com | bash",
    "azure": "pip install azure-cli",
    "vercel": "npm install -g vercel",
    "railway": "npm install -g @railway/cli",
    "flyctl": "curl -L https://fly.io/install.sh | sh",

    # Databases
    "postgresql-client": "apt-get update && apt-get install -y postgresql-client",
    "mongodb-client": "apt-get update && apt-get install -y mongodb-clients",
    "redis-tools": "apt-get update && apt-get install -y redis-tools",

    # Testing
    "playwright": "npm install -g playwright && npx playwright install --with-deps",
    "cypress": "npm install -g cypress",

    # Utilities
    "jq": "apt-get update && apt-get install -y jq",
    "yq": "pip install yq",
    "httpie": "pip install httpie",
    "pandoc": "apt-get update && apt-get install -y pandoc",
}

# Tool detection commands
TOOL_DETECTORS = {
    "python": "python3 --version",
    "node": "node --version",
    "go": "go version",
    "rust": "rustc --version",
    "ffmpeg": "ffmpeg -version",
    "docker": "docker --version",
    "kubectl": "kubectl version --client",
    "terraform": "terraform version",
    "aws": "aws --version",
    "playwright": "npx playwright --version",
}


class CapabilityInstaller:
    """Installs tools and capabilities on-demand."""

    def __init__(self, worker_pool=None):
        self.worker_pool = worker_pool
        self.installed_tools: Dict[int, set] = {}  # worker_id -> installed tools

    async def check_tool_available(
        self,
        tool: str,
        worker_id: Optional[int] = None
    ) -> bool:
        """Check if a tool is available."""
        detector = TOOL_DETECTORS.get(tool, f"which {tool}")

        try:
            result = await asyncio.to_thread(
                subprocess.run,
                ["bash", "-c", detector],
                capture_output=True,
                text=True,
                timeout=10
            )
            return result.returncode == 0

        except Exception:
            return False

    async def install_tool(
        self,
        tool: str,
        worker_id: Optional[int] = None
    ) -> bool:
        """Install a tool."""
        if tool not in TOOL_INSTALLERS:
            logger.error(f"Unknown tool: {tool}")
            return False

        # Check if already installed
        if await self.check_tool_available(tool, worker_id):
            logger.info(f"Tool {tool} already available")
            return True

        install_cmd = TOOL_INSTALLERS[tool]
        logger.info(f"Installing {tool}...")

        try:
            result = await asyncio.to_thread(
                subprocess.run,
                ["bash", "-c", install_cmd],
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout for installations
            )

            if result.returncode == 0:
                logger.info(f"Successfully installed {tool}")

                # Track installation
                if worker_id:
                    if worker_id not in self.installed_tools:
                        self.installed_tools[worker_id] = set()
                    self.installed_tools[worker_id].add(tool)

                return True
            else:
                logger.error(f"Failed to install {tool}: {result.stderr}")
                return False

        except asyncio.TimeoutError:
            logger.error(f"Timeout installing {tool}")
            return False
        except Exception as e:
            logger.error(f"Error installing {tool}: {e}")
            return False

    async def ensure_tools(
        self,
        tools: List[str],
        worker_id: Optional[int] = None
    ) -> Dict[str, bool]:
        """Ensure multiple tools are available, installing if needed."""
        results = {}

        for tool in tools:
            if await self.check_tool_available(tool, worker_id):
                results[tool] = True
            else:
                results[tool] = await self.install_tool(tool, worker_id)

        return results

    async def detect_required_tools(self, project_path: str) -> List[str]:
        """Detect tools required by a project."""
        from pathlib import Path

        path = Path(project_path)
        required = []

        # Node.js project
        if (path / "package.json").exists():
            required.append("node")

        # Python project
        if (path / "requirements.txt").exists() or (path / "pyproject.toml").exists():
            required.append("python")

        # Go project
        if (path / "go.mod").exists():
            required.append("go")

        # Rust project
        if (path / "Cargo.toml").exists():
            required.append("rust")

        # Docker
        if (path / "Dockerfile").exists() or (path / "docker-compose.yml").exists():
            required.append("docker")

        # Playwright tests
        if (path / "playwright.config.ts").exists() or (path / "playwright.config.js").exists():
            required.append("playwright")

        # Terraform
        if any(path.glob("*.tf")):
            required.append("terraform")

        return required

    def get_available_tools(self) -> List[str]:
        """Get list of all tools that can be installed."""
        return list(TOOL_INSTALLERS.keys())
