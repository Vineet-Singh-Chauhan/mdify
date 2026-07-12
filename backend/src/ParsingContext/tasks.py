"""Celery task definitions for the ParsingContext.

Coordinates ClamAV scanning, document parsing, image extraction,
asset formatting, and output packaging in a single atomic pipeline.
"""
from __future__ import annotations
import logging
import shutil
from pathlib import Path

from celery import Task
from src.celery_app import celery_app
from src.config import settings
from src.exceptions import (
    VirusDetectedError,
    AntivirusUnavailableError,
    MarkdownCompilationError,
)
from src.IngestionContext.sandbox import SandboxManager
from src.IngestionContext.scanner import scan_file
from src.IngestionContext.tracker import ProgressTracker, PipelineStage, TaskStatus
from src.ParsingContext.adapters.markitdown import convert_to_markdown, SUPPORTED_EXTENSIONS
from src.ParsingContext.adapters.pdf import extract_text, extract_images
from src.AssetContext.formatters import encode_image_to_data_uri
from src.AssetContext.packager import assemble_zip_package, assemble_batch_zip

logger = logging.getLogger(__name__)
sandbox = SandboxManager()


@celery_app.task(bind=True, name="src.ParsingContext.tasks.run_conversion")
def run_conversion(self: Task, task_id: str, filename: str, output_mode: str) -> dict[str, object]:
    """Main conversion pipeline: scan → parse → resolve assets → package.

    Raises domain exceptions which Celery captures as task failure state.
    All filesystem access is scoped to the task sandbox.
    """
    tracker = ProgressTracker(task_id)
    input_path = sandbox.get_input_path(task_id, filename)

    try:
        # Stage 1: Malware scan (FR-003, FR-009)
        tracker.advance(PipelineStage.SCANNING)
        scan_file(input_path)

        # Stage 2: Text/table parsing (FR-005)
        tracker.advance(PipelineStage.PARSING)
        ext = Path(filename).suffix.lower()

        if ext == ".pdf":
            text_content = extract_text(input_path)
            # Stage 3: Image asset extraction (FR-006)
            tracker.advance(PipelineStage.RESOLVING_ASSETS)
            image_assets = extract_images(input_path)
        else:
            text_content = convert_to_markdown(input_path)
            tracker.advance(PipelineStage.RESOLVING_ASSETS)
            image_assets = []

        # Stage 4: Output assembly (FR-007)
        tracker.advance(PipelineStage.PACKAGING)
        output_dir = Path(settings.conversion_base_dir) / task_id / "output"
        stem = Path(filename).stem

        if output_mode == "standalone":
            # Inline Base64 images into Markdown
            md_content = text_content
            for asset in image_assets:
                data_uri = encode_image_to_data_uri(asset.data, asset.extension)
                md_content += f"\n\n![{asset.name}]({data_uri})"
            output_path = output_dir / f"{stem}.md"
            output_path.write_text(md_content, encoding="utf-8")
        else:
            # ZIP package with relative image paths
            images: dict[str, bytes] = {}
            md_content = text_content
            for asset in image_assets:
                rel_path = f"images/{asset.name}"
                images[rel_path] = asset.data
                md_content += f"\n\n![{asset.name}]({rel_path})"
            zip_bytes = assemble_zip_package(md_content, images)
            output_path = output_dir / f"{stem}.zip"
            output_path.write_bytes(zip_bytes)

        tracker.advance(PipelineStage.PACKAGING, TaskStatus.SUCCESS)
        if ext == ".pdf":
            try:
                from src.IngestionContext.stats import increment_conversions
                increment_conversions()
            except Exception:
                pass
        logger.info("[pipeline] Task %s completed successfully.", task_id)
        return {"task_id": task_id, "status": "success"}

    except (VirusDetectedError, AntivirusUnavailableError) as exc:
        tracker.fail(PipelineStage.SCANNING, exc.user_message)
        raise
    except MarkdownCompilationError as exc:
        tracker.fail(PipelineStage.PARSING, exc.user_message)
        raise
    except Exception as exc:
        tracker.fail(PipelineStage.PACKAGING, "An unexpected error occurred during processing.")
        raise


@celery_app.task(name="src.ParsingContext.tasks.purge_workspace_task")
def purge_workspace_task(workspace_path: str) -> None:
    """Securely delete a sandbox workspace directory (FR-010)."""
    path = Path(workspace_path)
    if path.exists():
        shutil.rmtree(path, ignore_errors=False)
        task_id = path.name
        ProgressTracker(task_id).mark_purged()
        logger.info("[lifecycle] Purged workspace: %s", workspace_path)


@celery_app.task(name="src.ParsingContext.tasks.aggregate_batch_results")
def aggregate_batch_results(batch_id: str, task_ids: list[str]) -> dict[str, object]:
    """Wait for all sibling tasks to complete, then aggregate into a batch ZIP."""
    from celery.result import AsyncResult
    import time

    packages: dict[str, bytes | str] = {}
    timeout = 300  # 5 minutes
    start = time.time()

    while time.time() - start < timeout:
        all_done = True
        for task_id in task_ids:
            result = AsyncResult(task_id, app=celery_app)
            if not result.ready():
                all_done = False
                break
        if all_done:
            break
        time.sleep(1)

    for task_id in task_ids:
        tracker = ProgressTracker(task_id)
        state = tracker.get()
        if state and state.get("status") == "SUCCESS":
            output_dir = Path(settings.conversion_base_dir) / task_id / "output"
            for f in output_dir.iterdir():
                packages[f"{task_id[:8]}_{f.name}"] = f.read_bytes()

    batch_zip = assemble_batch_zip(packages)
    batch_output = Path(settings.conversion_base_dir) / batch_id
    batch_output.mkdir(parents=True, exist_ok=True)
    zip_path = batch_output / f"Batch_Conversion_{batch_id[:8]}.zip"
    zip_path.write_bytes(batch_zip)

    logger.info("[pipeline] Batch %s aggregated: %d tasks.", batch_id, len(task_ids))
    return {"batch_id": batch_id, "status": "success"}
