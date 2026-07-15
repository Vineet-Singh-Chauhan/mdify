"""Integration tests for concurrent batch Celery task processing."""
from unittest.mock import patch, MagicMock
from pathlib import Path
import pytest


def test_batch_endpoint_enqueues_multiple_tasks() -> None:
    """Verify the batch upload route creates one task per file."""
    from fastapi.testclient import TestClient
    from src.main import app
    import io

    client = TestClient(app)

    with patch("src.IngestionContext.routers.run_conversion") as mock_task, \
         patch("src.IngestionContext.routers.aggregate_batch_results") as mock_agg, \
         patch("src.IngestionContext.routers.ProgressTracker") as mock_tracker:
        mock_task.apply_async = MagicMock()
        mock_agg.apply_async = MagicMock()
        mock_tracker.return_value.initialise = MagicMock()
        mock_tracker.return_value.get = MagicMock(return_value=None)

        files = [
            ("files", ("file1.txt", io.BytesIO(b"Hello world"), "text/plain")),
            ("files", ("file2.txt", io.BytesIO(b"Another file"), "text/plain")),
        ]
        res = client.post("/api/v1/upload/batch", files=files, data={"output_mode": "standalone"})

    # Batch endpoint should return 200 with batch_id and task_ids
    assert res.status_code == 200
    body = res.json()
    assert "batch_id" in body
    assert "task_ids" in body
    assert len(body["task_ids"]) == 2


def test_batch_endpoint_mixed_formats() -> None:
    """Verify mixed formats are validated and enqueued in a single batch upload."""
    from fastapi.testclient import TestClient
    from src.main import app
    import io

    client = TestClient(app)

    with patch("src.IngestionContext.routers.run_conversion") as mock_task, \
         patch("src.IngestionContext.routers.aggregate_batch_results") as mock_agg, \
         patch("src.IngestionContext.routers.ProgressTracker") as mock_tracker:
        mock_task.apply_async = MagicMock()
        mock_agg.apply_async = MagicMock()
        mock_tracker.return_value.initialise = MagicMock()
        mock_tracker.return_value.get = MagicMock(return_value=None)

        files = [
            ("files", ("document.pdf", io.BytesIO(b"%PDF-1.4 content"), "application/pdf")),
            ("files", ("report.docx", io.BytesIO(b"PK\x03\x04zipcontent"), "application/vnd.openxmlformats-officedocument.wordprocessingml.document")),
            ("files", ("data.csv", io.BytesIO(b"col1,col2\nval1,val2"), "text/csv")),
        ]
        res = client.post("/api/v1/upload/batch", files=files, data={"output_mode": "standalone"})

    assert res.status_code == 200
    body = res.json()
    assert "batch_id" in body
    assert "task_ids" in body
    assert len(body["task_ids"]) == 3

