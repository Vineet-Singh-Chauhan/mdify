"""Pytest configuration and global mocks."""
import pytest
from typing import Generator
from unittest.mock import MagicMock, patch

@pytest.fixture(autouse=True)
def mock_redis() -> Generator[MagicMock, None, None]:
    """Mock redis connection globally for all tests."""
    with patch("src.IngestionContext.tracker.redis") as mock_red:
        # Mock client
        mock_client = MagicMock()
        mock_red.from_url.return_value = mock_client
        
        # In memory fake storage
        fake_redis = {}
        
        def fake_setex(key, ttl, value):
            fake_redis[key] = value
            return True
            
        def fake_get(key):
            return fake_redis.get(key)
            
        def fake_delete(key):
            if key in fake_redis:
                del fake_redis[key]
                return 1
            return 0
            
        mock_client.setex.side_effect = fake_setex
        mock_client.get.side_effect = fake_get
        mock_client.delete.side_effect = fake_delete
        
        yield mock_client
