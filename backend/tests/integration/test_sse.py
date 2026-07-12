"""Integration tests for SSE progress event stream."""
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from src.main import app


def test_sse_stream_returns_event_stream_content_type() -> None:
    """SSE endpoint must return text/event-stream."""
    client = TestClient(app)
    mock_state = {
        "task_id": "test-id",
        "stage": "UPLOADED",
        "status": "SUCCESS",
        "original_name": "test.pdf",
        "output_mode": "standalone",
        "batch_id": None,
        "error_reason": None,
    }
    with patch("src.IngestionContext.routers.ProgressTracker") as mock_tracker:
        mock_tracker.return_value.get = MagicMock(return_value=mock_state)
        with client.stream("GET", "/api/v1/events/test-id") as response:
            assert response.headers["content-type"] == "text/event-stream; charset=utf-8"
            for chunk in response.iter_text():
                assert "data:" in chunk
                break  # just verify the first chunk


def test_sse_stream_emits_json_stage_events() -> None:
    """SSE events must contain valid JSON with stage/status fields."""
    import json
    client = TestClient(app)
    mock_state = {
        "task_id": "test-id",
        "stage": "PARSING",
        "status": "SUCCESS",
        "original_name": "doc.pdf",
        "output_mode": "standalone",
        "batch_id": None,
        "error_reason": None,
    }
    with patch("src.IngestionContext.routers.ProgressTracker") as mock_tracker:
        mock_tracker.return_value.get = MagicMock(return_value=mock_state)
        with client.stream("GET", "/api/v1/events/test-id") as response:
            for text in response.iter_text():
                # Split by SSE line separator
                lines = text.split("\n")
                for line in lines:
                    if line.startswith("data:"):
                        data = json.loads(line.replace("data: ", "").strip())
                        assert "stage" in data
                        assert "status" in data
                        assert "task_id" in data
                        return
