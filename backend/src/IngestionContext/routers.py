"""FastAPI route handlers for the IngestionContext.

Enforces 50MB hard limit before any stream buffering (FR-001, Principle V).
SSE routes use Server-Sent Events for real-time progress (FR-008).
"""
from __future__ import annotations
import asyncio
import json
import logging
import uuid
from pathlib import Path
from typing import AsyncGenerator

from fastapi import APIRouter, Depends, UploadFile, File, Form, Request
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel

from src.config import settings
from src.exceptions import (
    PayloadTooLargeError,
    BatchSizeLimitExceededError,
    TaskNotFoundError,
    TaskAlreadyPurgedError,
)
from src.IngestionContext.validator import validate_file_signature
from src.IngestionContext.sandbox import SandboxManager
from src.IngestionContext.tracker import ProgressTracker, TaskStatus, PipelineStage, get_redis
from src.ParsingContext.tasks import run_conversion, aggregate_batch_results

logger = logging.getLogger(__name__)
router = APIRouter()


def get_sandbox() -> SandboxManager:
    return SandboxManager()


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class UploadResponse(BaseModel):
    task_id: str
    original_name: str
    output_mode: str
    status: str


class BatchUploadResponse(BaseModel):
    batch_id: str
    task_ids: list[str]
    status: str


# ---------------------------------------------------------------------------
# Single file upload (FR-001: 50MB enforced before buffering)
# ---------------------------------------------------------------------------

@router.post("/upload", response_model=UploadResponse, tags=["conversion"])
async def upload_file(
    file: UploadFile = File(...),
    output_mode: str = Form(default="standalone"),
    sandbox: SandboxManager = Depends(get_sandbox),
) -> UploadResponse:
    """Accept a single file upload, validate, sandbox, and enqueue for conversion."""
    # Enforce size limit before buffering (FR-001)
    content_length = file.size or 0
    if content_length > settings.max_upload_size_bytes:
        raise PayloadTooLargeError()

    raw = await file.read()
    if len(raw) > settings.max_upload_size_bytes:
        raise PayloadTooLargeError()

    # Magic-number validation (FR-002)
    filename = file.filename or "upload.bin"
    validate_file_signature(filename, raw)

    task_id = str(uuid.uuid4())
    workspace = sandbox.create(task_id)
    input_path = workspace / "input" / filename
    input_path.write_bytes(raw)

    # Initialise progress tracker
    tracker = ProgressTracker(task_id)
    tracker.initialise(original_name=filename, output_mode=output_mode)

    # Enqueue Celery task (FR-003: AV scan inside the task)
    run_conversion.apply_async(
        args=[task_id, filename, output_mode],
        task_id=task_id,
    )

    return UploadResponse(
        task_id=task_id,
        original_name=filename,
        output_mode=output_mode,
        status="queued",
    )


# ---------------------------------------------------------------------------
# Batch upload
# ---------------------------------------------------------------------------

@router.post("/upload/batch", response_model=BatchUploadResponse, tags=["conversion"])
async def upload_batch(
    files: list[UploadFile] = File(...),
    output_mode: str = Form(default="standalone"),
    sandbox: SandboxManager = Depends(get_sandbox),
) -> BatchUploadResponse:
    """Accept a batch of files, enqueue all as sibling tasks under a shared batch_id."""
    if len(files) > 10:
        raise BatchSizeLimitExceededError()
        
    batch_id = str(uuid.uuid4())
    task_ids: list[str] = []

    for file in files:
        raw = await file.read()
        if len(raw) > settings.max_upload_size_bytes:
            raise PayloadTooLargeError()
        filename = file.filename or "upload.bin"
        validate_file_signature(filename, raw)

        task_id = str(uuid.uuid4())
        workspace = sandbox.create(task_id)
        input_path = workspace / "input" / filename
        input_path.write_bytes(raw)

        tracker = ProgressTracker(task_id)
        tracker.initialise(original_name=filename, output_mode=output_mode, batch_id=batch_id)

        run_conversion.apply_async(
            args=[task_id, filename, output_mode],
            task_id=task_id,
        )
        task_ids.append(task_id)

    get_redis().setex(
        f"mdify:batch:{batch_id}",
        settings.purge_interval_seconds + 60,
        json.dumps(task_ids)
    )

    aggregate_batch_results.apply_async(
        args=[batch_id, task_ids]
    )

    return BatchUploadResponse(batch_id=batch_id, task_ids=task_ids, status="queued")


# ---------------------------------------------------------------------------
# Status
# ---------------------------------------------------------------------------

@router.get("/tasks/{task_id}/status", tags=["conversion"])
async def get_task_status(task_id: str) -> dict[str, object]:
    """Return current stage and status for a task."""
    tracker = ProgressTracker(task_id)
    state = tracker.get()
    if state is None:
        raise TaskNotFoundError()
    return state


# ---------------------------------------------------------------------------
# Download (FR-010: 410 Gone after purge)
# ---------------------------------------------------------------------------

@router.get("/tasks/{task_id}/download", tags=["conversion"])
async def download_result(
    task_id: str,
    sandbox: SandboxManager = Depends(get_sandbox),
) -> FileResponse:
    """Download the converted output for a completed task."""
    tracker = ProgressTracker(task_id)
    state = tracker.get()

    if state is None:
        raise TaskAlreadyPurgedError()

    if state.get("status") != TaskStatus.SUCCESS:
        raise TaskNotFoundError()

    output_dir = sandbox.get_output_path(task_id, "")
    # Find the output file (either .md or .zip)
    output_files = list(Path(output_dir).parent.glob("output/*"))
    if not output_files:
        raise TaskAlreadyPurgedError()

    output_file = output_files[0]
    media_type = "application/zip" if output_file.suffix == ".zip" else "text/markdown"
    return FileResponse(
        path=str(output_file),
        filename=output_file.name,
        media_type=media_type,
    )


@router.get("/batches/{batch_id}/download", tags=["conversion"])
async def download_batch_result(
    batch_id: str,
    sandbox: SandboxManager = Depends(get_sandbox),
) -> FileResponse:
    """Download the aggregated ZIP package for a completed batch conversion."""
    # Wait up to 15 seconds for the batch aggregation Celery task to finish writing the zip file
    zip_path = Path(settings.conversion_base_dir) / batch_id / f"Batch_Conversion_{batch_id[:8]}.zip"
    
    for _ in range(30):
        if zip_path.exists():
            break
        await asyncio.sleep(0.5)
        
    if not zip_path.exists():
        raise TaskNotFoundError()
        
    return FileResponse(
        path=str(zip_path),
        filename=zip_path.name,
        media_type="application/zip",
    )


# ---------------------------------------------------------------------------
# SSE progress stream (FR-008)
# ---------------------------------------------------------------------------

@router.get("/events/{task_id}", tags=["streaming"])
async def stream_progress(task_id: str, request: Request) -> StreamingResponse:
    """Server-Sent Events stream for real-time task progress."""
    async def event_generator() -> AsyncGenerator[str, None]:
        last_stage: str | None = None
        while True:
            if await request.is_disconnected():
                break
            tracker = ProgressTracker(task_id)
            state = tracker.get()
            if state is None:
                yield f"data: {json.dumps({'error': 'task_not_found'})}\n\n"
                break
            current_stage = state.get("stage")
            if current_stage != last_stage:
                yield f"data: {json.dumps(state)}\n\n"
                last_stage = current_stage
            status = state.get("status")
            if status in (TaskStatus.SUCCESS, TaskStatus.FAILURE):
                yield f"data: {json.dumps(state)}\n\n"
                break
            await asyncio.sleep(0.3)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/events/batch/{batch_id}", tags=["streaming"])
async def stream_batch_progress(batch_id: str, request: Request) -> StreamingResponse:
    """Server-Sent Events stream for real-time batch progress."""
    async def event_generator() -> AsyncGenerator[str, None]:
        raw_tasks = get_redis().get(f"mdify:batch:{batch_id}")
        if not raw_tasks:
            yield f"data: {json.dumps({'error': 'batch_not_found'})}\n\n"
            return
            
        task_ids = json.loads(raw_tasks)
        last_aggregated_state: dict[str, object] | None = None
        
        while True:
            if await request.is_disconnected():
                break
                
            states = []
            for task_id in task_ids:
                tracker = ProgressTracker(task_id)
                state = tracker.get()
                if state:
                    states.append(state)
                    
            if not states:
                yield f"data: {json.dumps({'error': 'no_tasks_found'})}\n\n"
                break
                
            statuses = [s.get("status") for s in states]
            stages = [s.get("stage") for s in states]
            
            if all(st == TaskStatus.SUCCESS for st in statuses):
                overall_status = TaskStatus.SUCCESS
            elif any(st == TaskStatus.FAILURE for st in statuses):
                overall_status = TaskStatus.FAILURE
            else:
                overall_status = TaskStatus.ACTIVE
                
            stage_priority = {
                PipelineStage.UPLOADED: 0,
                PipelineStage.SCANNING: 1,
                PipelineStage.PARSING: 2,
                PipelineStage.RESOLVING_ASSETS: 3,
                PipelineStage.PACKAGING: 4,
            }
            min_stage = min(stages, key=lambda s: stage_priority.get(s, 0))
            
            aggregated_state = {
                "task_id": batch_id,
                "status": overall_status,
                "stage": min_stage,
                "error_reason": next((s.get("error_reason") for s in states if s.get("error_reason")), None),
            }
            
            if aggregated_state != last_aggregated_state:
                yield f"data: {json.dumps(aggregated_state)}\n\n"
                last_aggregated_state = aggregated_state
                
            if overall_status in (TaskStatus.SUCCESS, TaskStatus.FAILURE):
                break
                
            await asyncio.sleep(0.5)
            
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# ---------------------------------------------------------------------------
# Stats (Upstash tracked visitors & conversions)
# ---------------------------------------------------------------------------

class StatsResponse(BaseModel):
    visitors: int
    conversions: int


@router.get("/stats", response_model=StatsResponse, tags=["stats"])
async def get_current_stats() -> StatsResponse:
    """Retrieve current tracking statistics."""
    from src.IngestionContext.stats import get_stats
    data = get_stats()
    return StatsResponse(
        visitors=data.get("visitors", 0),
        conversions=data.get("conversions", 0),
    )


@router.post("/stats/visitor", response_model=StatsResponse, tags=["stats"])
async def increment_visitor_stat() -> StatsResponse:
    """Increment visitor counter and return updated statistics."""
    from src.IngestionContext.stats import increment_visitors, get_stats
    increment_visitors()
    data = get_stats()
    return StatsResponse(
        visitors=data.get("visitors", 0),
        conversions=data.get("conversions", 0),
    )
