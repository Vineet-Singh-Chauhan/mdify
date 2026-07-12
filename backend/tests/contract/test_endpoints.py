"""Contract tests for FastAPI endpoints."""
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
