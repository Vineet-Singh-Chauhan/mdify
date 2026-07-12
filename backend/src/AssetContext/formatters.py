"""Base64 inline image encoder for the AssetContext."""
from __future__ import annotations
import base64
import logging
from src.exceptions import Base64EncodingError

logger = logging.getLogger(__name__)

_MIME_MAP: dict[str, str] = {
    "png": "image/png",
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
    "gif": "image/gif",
    "webp": "image/webp",
    "bmp": "image/bmp",
    "tiff": "image/tiff",
}


def encode_image_to_data_uri(image_bytes: bytes, extension: str) -> str:
    """Encode raw image bytes into a Base64 data URI for inline Markdown embedding.

    Args:
        image_bytes: Raw binary image data.
        extension: File extension (e.g. "png", "jpg").

    Returns:
        Data URI string: `data:image/png;base64,...`

    Raises:
        Base64EncodingError: If encoding fails.
    """
    mime_type = _MIME_MAP.get(extension.lower(), "application/octet-stream")
    try:
        encoded = base64.b64encode(image_bytes).decode("ascii")
        return f"data:{mime_type};base64,{encoded}"
    except Exception as exc:
        logger.warning("[asset] Base64 encoding failed: %s", type(exc).__name__)
        raise Base64EncodingError() from exc
