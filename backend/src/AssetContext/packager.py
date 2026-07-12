"""ZIP packaging utilities for single and batch conversion outputs."""
from __future__ import annotations
import io
import logging
import zipfile
from datetime import datetime, timezone
from src.exceptions import ZipPackagingError

logger = logging.getLogger(__name__)


def assemble_zip_package(markdown_content: str, images: dict[str, bytes]) -> bytes:
    """Create a ZIP package containing a Markdown file with relative image links.

    Args:
        markdown_content: Markdown text with relative image references like ![](images/img.png)
        images: Dict mapping relative image path -> raw bytes.

    Returns:
        Raw bytes of the ZIP archive.

    Raises:
        ZipPackagingError: If ZIP assembly fails.
    """
    try:
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("document.md", markdown_content.encode("utf-8"))
            for rel_path, data in images.items():
                zf.writestr(rel_path, data)
        buf.seek(0)
        return buf.getvalue()
    except Exception as exc:
        logger.warning("[asset] ZIP packaging failed: %s", type(exc).__name__)
        raise ZipPackagingError() from exc


def assemble_batch_zip(task_packages: dict[str, bytes | str]) -> bytes:
    """Aggregate multiple task outputs into a single timestamped batch ZIP.

    Args:
        task_packages: Dict mapping filename -> bytes (ZIP) or str (Markdown).

    Returns:
        Raw bytes of the batch ZIP archive.

    Raises:
        ZipPackagingError: If batch ZIP assembly fails.
    """
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    batch_filename = f"Batch_Conversion_{ts}.zip"
    try:
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
            for name, content in task_packages.items():
                if isinstance(content, str):
                    zf.writestr(name, content.encode("utf-8"))
                else:
                    zf.writestr(name, content)
        buf.seek(0)
        logger.info("[asset] Batch ZIP assembled: %s (%d items)", batch_filename, len(task_packages))
        return buf.getvalue()
    except Exception as exc:
        logger.warning("[asset] Batch ZIP packaging failed: %s", type(exc).__name__)
        raise ZipPackagingError() from exc
