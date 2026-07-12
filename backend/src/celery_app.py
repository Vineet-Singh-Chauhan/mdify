"""Celery application configuration and lifecycle hooks."""
import shutil
import logging
from pathlib import Path
from celery import Celery
from celery.signals import task_postrun
from src.config import settings

logger = logging.getLogger(__name__)

celery_app = Celery(
    "mdify",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=["src.ParsingContext.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    result_expires=settings.purge_interval_seconds,
    timezone="UTC",
    enable_utc=True,
    worker_prefetch_multiplier=1,
    task_acks_late=True,
)


@task_postrun.connect
def schedule_workspace_purge(
    task_id: str,
    task: object,
    retval: object,
    state: str,
    **kwargs: object,
) -> None:
    """Schedule sandbox workspace purge exactly purge_interval_seconds after task completion.

    Logs lifecycle event without logging any file content or extracted text (Principle V).
    """
    # The actual timed purge is applied via apply_async with countdown
    from src.ParsingContext.tasks import purge_workspace_task
    workspace = Path(settings.conversion_base_dir) / task_id
    if workspace.exists():
        purge_workspace_task.apply_async(
            args=[str(workspace)],
            countdown=settings.purge_interval_seconds,
        )
        logger.info("[lifecycle] Task %s completed (state=%s). Purge scheduled in %ds.",
                    task_id, state, settings.purge_interval_seconds)
