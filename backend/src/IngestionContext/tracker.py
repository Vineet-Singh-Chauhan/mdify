"""Redis-backed task progress state tracker for the IngestionContext."""
from __future__ import annotations
import json
import logging
from enum import StrEnum
from typing import Any
import redis
from src.config import settings

logger = logging.getLogger(__name__)

_redis_client: redis.Redis | None = None


def get_redis() -> redis.Redis:
    global _redis_client
    if _redis_client is None:
        _redis_client = redis.from_url(settings.redis_url, decode_responses=True)
    return _redis_client


class PipelineStage(StrEnum):
    UPLOADED = "UPLOADED"
    SCANNING = "SCANNING"
    PARSING = "PARSING"
    RESOLVING_ASSETS = "RESOLVING_ASSETS"
    PACKAGING = "PACKAGING"


class TaskStatus(StrEnum):
    PENDING = "PENDING"
    ACTIVE = "ACTIVE"
    SUCCESS = "SUCCESS"
    FAILURE = "FAILURE"


class ProgressTracker:
    """Manages task progress state in Redis with TTL matching the purge window."""

    TTL_SECONDS = settings.purge_interval_seconds + 60  # buffer over purge window

    def __init__(self, task_id: str) -> None:
        self.task_id = task_id
        self._key = f"mdify:task:{task_id}"
        self._redis = get_redis()

    def initialise(self, original_name: str, output_mode: str, batch_id: str | None = None) -> None:
        state: dict[str, Any] = {
            "task_id": self.task_id,
            "batch_id": batch_id,
            "original_name": original_name,
            "output_mode": output_mode,
            "stage": PipelineStage.UPLOADED,
            "status": TaskStatus.PENDING,
            "error_reason": None,
        }
        self._redis.setex(self._key, self.TTL_SECONDS, json.dumps(state))
        logger.info("[lifecycle] Task %s created.", self.task_id)

    def advance(self, stage: PipelineStage, status: TaskStatus = TaskStatus.ACTIVE) -> None:
        raw = self._redis.get(self._key)
        if raw is None:
            return
        state: dict[str, Any] = json.loads(raw)
        state["stage"] = stage
        state["status"] = status
        self._redis.setex(self._key, self.TTL_SECONDS, json.dumps(state))
        logger.info("[lifecycle] Task %s → stage=%s status=%s.", self.task_id, stage, status)

    def fail(self, stage: PipelineStage, user_message: str) -> None:
        raw = self._redis.get(self._key)
        if raw is None:
            return
        state: dict[str, Any] = json.loads(raw)
        state["stage"] = stage
        state["status"] = TaskStatus.FAILURE
        state["error_reason"] = user_message
        self._redis.setex(self._key, self.TTL_SECONDS, json.dumps(state))
        logger.info("[lifecycle] Task %s FAILED at stage=%s.", self.task_id, stage)

    def get(self) -> dict[str, Any] | None:
        raw = self._redis.get(self._key)
        if raw is None:
            return None
        return json.loads(raw)  # type: ignore[return-value]

    def mark_purged(self) -> None:
        self._redis.delete(self._key)
        logger.info("[lifecycle] Task %s purged from tracker.", self.task_id)
