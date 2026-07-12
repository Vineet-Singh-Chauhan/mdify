"""Integration tests for 10-minute sandbox purge lifecycle."""
import time
from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest
from src.IngestionContext.sandbox import SandboxManager
from src.ParsingContext.tasks import purge_workspace_task


def test_workspace_directory_exists_after_creation(tmp_path: Path) -> None:
    mgr = SandboxManager(base_dir=str(tmp_path))
    workspace = mgr.create("test-task-id")
    assert workspace.exists()
    assert (workspace / "input").exists()
    assert (workspace / "output").exists()


def test_purge_task_deletes_workspace(tmp_path: Path) -> None:
    mgr = SandboxManager(base_dir=str(tmp_path))
    workspace = mgr.create("test-purge-task")
    assert workspace.exists()
    # Simulate the purge Celery task
    with patch("src.ParsingContext.tasks.ProgressTracker") as mock_tracker:
        mock_tracker.return_value.mark_purged = MagicMock()
        purge_workspace_task(str(workspace))
    assert not workspace.exists()


def test_sandbox_purge_is_unrecoverable(tmp_path: Path) -> None:
    mgr = SandboxManager(base_dir=str(tmp_path))
    workspace = mgr.create("sensitive-task")
    secret_file = workspace / "input" / "secret.txt"
    secret_file.write_text("TOP SECRET DATA")
    mgr.purge("sensitive-task")
    assert not workspace.exists()
    assert not secret_file.exists()
