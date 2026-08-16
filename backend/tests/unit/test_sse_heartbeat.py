"""Unit tests for SSE heartbeat generation."""
import json
import time
from unittest.mock import patch, MagicMock

import pytest
from pydantic import ValidationError
from fastapi.testclient import TestClient

from src.main import app
from src.config import Settings, settings

def test_heartbeat_emitted_when_idle():
    """T006: Heartbeat emitted when no data events are sent within the interval."""
    client = TestClient(app)
    state_active = {"task_id": "test", "stage": "PARSING", "status": "ACTIVE"}
    state_success = {"task_id": "test", "stage": "PACKAGING", "status": "SUCCESS"}
    
    with patch("src.IngestionContext.routers.ProgressTracker") as mock_tracker:
        # 10 loops of 0.02s = 0.2s total time. Interval is 0.05s. Heartbeats will trigger.
        mock_tracker.return_value.get = MagicMock(side_effect=[state_active] * 10 + [state_success])
        
        original_interval = settings.sse_heartbeat_interval_seconds
        settings.sse_heartbeat_interval_seconds = 0.05
        
        try:
            with patch("src.IngestionContext.routers.asyncio.sleep") as mock_sleep:
                # Instead of AsyncMock which might break TestClient, just use an async def
                async def fake_sleep(t):
                    time.sleep(0.02)
                mock_sleep.side_effect = fake_sleep
                
                with client.stream("GET", "/api/v1/events/test-id") as response:
                    chunks = list(response.iter_text())
                    assert any(": heartbeat" in chunk for chunk in chunks)
        finally:
            settings.sse_heartbeat_interval_seconds = original_interval

def test_heartbeat_not_emitted_when_data_events_frequent():
    """T007: Heartbeat is skipped if data events are frequent enough."""
    client = TestClient(app)
    state1 = {"task_id": "test", "stage": "PARSING", "status": "ACTIVE"}
    state2 = {"task_id": "test", "stage": "RESOLVING_ASSETS", "status": "ACTIVE"}
    state_success = {"task_id": "test", "stage": "PACKAGING", "status": "SUCCESS"}
    
    with patch("src.IngestionContext.routers.ProgressTracker") as mock_tracker:
        # Every step changes stage, so data events are emitted constantly.
        mock_tracker.return_value.get = MagicMock(side_effect=[state1, state2, state1, state2, state_success])
        
        original_interval = settings.sse_heartbeat_interval_seconds
        settings.sse_heartbeat_interval_seconds = 0.1
        
        try:
            with patch("src.IngestionContext.routers.asyncio.sleep") as mock_sleep:
                async def fake_sleep(t):
                    time.sleep(0.02) # Faster than 0.1s interval
                mock_sleep.side_effect = fake_sleep
                
                with client.stream("GET", "/api/v1/events/test-id") as response:
                    chunks = list(response.iter_text())
                    assert not any(": heartbeat" in chunk for chunk in chunks)
        finally:
            settings.sse_heartbeat_interval_seconds = original_interval

def test_heartbeat_uses_sse_comment_format():
    """T008: Heartbeat must use standard SSE comment format."""
    client = TestClient(app)
    state_active = {"task_id": "test", "stage": "PARSING", "status": "ACTIVE"}
    state_success = {"task_id": "test", "stage": "PACKAGING", "status": "SUCCESS"}
    
    with patch("src.IngestionContext.routers.ProgressTracker") as mock_tracker:
        mock_tracker.return_value.get = MagicMock(side_effect=[state_active] * 5 + [state_success])
        
        original_interval = settings.sse_heartbeat_interval_seconds
        settings.sse_heartbeat_interval_seconds = 0.05
        
        try:
            with patch("src.IngestionContext.routers.asyncio.sleep") as mock_sleep:
                async def fake_sleep(t):
                    time.sleep(0.06) # Guarantee heartbeat
                mock_sleep.side_effect = fake_sleep
                
                with client.stream("GET", "/api/v1/events/test-id") as response:
                    text = "".join(response.iter_text())
                    events = text.split("\n\n")
                    
                    heartbeat_events = [e for e in events if e == ": heartbeat"]
                    assert len(heartbeat_events) > 0
                    assert heartbeat_events[0].startswith(": ")
                    assert not heartbeat_events[0].startswith("data:")
        finally:
            settings.sse_heartbeat_interval_seconds = original_interval

def test_heartbeat_interval_configurable():
    """T018: Heartbeat interval is configurable."""
    # We will test configuring it to 0.2s vs 0.05s
    client = TestClient(app)
    state_active = {"task_id": "test", "stage": "PARSING", "status": "ACTIVE"}
    state_success = {"task_id": "test", "stage": "PACKAGING", "status": "SUCCESS"}
    
    with patch("src.IngestionContext.routers.ProgressTracker") as mock_tracker:
        # Loop 3 times with 0.02s sleep = 0.06s total
        mock_tracker.return_value.get = MagicMock(side_effect=[state_active] * 3 + [state_success])
        
        original_interval = settings.sse_heartbeat_interval_seconds
        settings.sse_heartbeat_interval_seconds = 0.2
        
        try:
            with patch("src.IngestionContext.routers.asyncio.sleep") as mock_sleep:
                async def fake_sleep(t):
                    time.sleep(0.02)
                mock_sleep.side_effect = fake_sleep
                
                with client.stream("GET", "/api/v1/events/test-id") as response:
                    chunks = list(response.iter_text())
                    # At 0.2 interval, no heartbeat should be emitted in 0.06s
                    assert not any(": heartbeat" in chunk for chunk in chunks)
        finally:
            settings.sse_heartbeat_interval_seconds = original_interval

def test_heartbeat_interval_validation():
    """T019: Heartbeat interval must be between 5 and 60."""
    with pytest.raises(ValidationError):
        Settings(SSE_HEARTBEAT_INTERVAL_SECONDS=3)
        
    with pytest.raises(ValidationError):
        Settings(SSE_HEARTBEAT_INTERVAL_SECONDS=61)
        
    s = Settings(SSE_HEARTBEAT_INTERVAL_SECONDS=30)
    assert s.sse_heartbeat_interval_seconds == 30
