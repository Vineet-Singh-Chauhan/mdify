"""Contract tests for FastAPI endpoints."""
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from src.main import app


client = TestClient(app)

def test_health_check_endpoint() -> None:
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json() == {
        "status": "healthy",
        "services": {
            "api": "online",
        },
    }

def test_get_nonexistent_task_returns_404() -> None:
    response = client.get("/api/v1/tasks/00000000-0000-0000-0000-000000000000/status")
    assert response.status_code == 404
    assert "error" in response.json()


def test_batch_limit_exceeded() -> None:
    files = [("files", ("test.txt", b"content", "text/plain")) for _ in range(11)]
    response = client.post("/api/v1/upload/batch", files=files)
    assert response.status_code == 400
    assert response.json()["error"] == "Batch upload exceeds the maximum allowed count of 10 files."


@patch("src.IngestionContext.routers.run_conversion")
@pytest.mark.parametrize(
    "filename,content,content_type",
    [
        ("report.docx", b"PK\x03\x04filecontent", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"),
        ("report.xlsx", b"PK\x03\x04filecontent", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
        ("notes.txt", b"Hello Text", "text/plain"),
        ("data.csv", b"col1,col2\nval1,val2", "text/csv"),
        ("index.html", b"<html><body>hello</body></html>", "text/html"),
        ("config.json", b'{"key": "value"}', "application/json"),
        ("data.xml", b"<root>test</root>", "application/xml"),
    ],
)
def test_upload_supported_formats_success(mock_run: MagicMock, filename: str, content: bytes, content_type: str) -> None:
    response = client.post(
        "/api/v1/upload",
        files={"file": (filename, content, content_type)},
        data={"output_mode": "standalone"},
    )
    assert response.status_code == 200
    res_json = response.json()
    assert res_json["original_name"] == filename
    assert res_json["status"] == "queued"
    assert "task_id" in res_json
    mock_run.apply_async.assert_called_once()

