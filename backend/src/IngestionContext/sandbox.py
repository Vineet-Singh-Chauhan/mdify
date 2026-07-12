"""UUID-partitioned ephemeral workspace manager for the IngestionContext."""
from __future__ import annotations
import logging
import shutil
from pathlib import Path
from src.config import settings
from src.exceptions import SandboxCreationError

logger = logging.getLogger(__name__)


class SandboxManager:
    """Creates and manages isolated per-task filesystem workspaces."""

    def __init__(self, base_dir: str | None = None) -> None:
        self._base = Path(base_dir or settings.conversion_base_dir)

    def create(self, task_id: str) -> Path:
        """Create isolated workspace at <base>/<task_id>/. Returns workspace Path.

        Raises:
            SandboxCreationError: If directory creation fails.
        """
        workspace = self._base / task_id
        try:
            workspace.mkdir(parents=True, exist_ok=False)
            (workspace / "input").mkdir()
            (workspace / "output").mkdir()
            (workspace / "images").mkdir()
        except OSError as exc:
            raise SandboxCreationError() from exc
        logger.info("[sandbox] Workspace created: %s", task_id)
        return workspace

    def purge(self, task_id: str) -> None:
        """Securely and unrecoverably delete workspace and all contents."""
        workspace = self._base / task_id
        if workspace.exists():
            shutil.rmtree(workspace, ignore_errors=False)
            logger.info("[sandbox] Workspace purged: %s", task_id)
        else:
            logger.info("[sandbox] Workspace not found (already purged?): %s", task_id)

    def get_input_path(self, task_id: str, filename: str) -> Path:
        return self._base / task_id / "input" / filename

    def get_output_path(self, task_id: str, filename: str) -> Path:
        return self._base / task_id / "output" / filename

    def get_images_path(self, task_id: str) -> Path:
        return self._base / task_id / "images"
