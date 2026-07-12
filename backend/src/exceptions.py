"""Typed domain exception hierarchy for mdify.

Principle VI (Constitution v2.2.0): Every error condition MUST be represented
by a purpose-built, domain-specific exception class. Generic exceptions are
PROHIBITED. All exceptions are translated to opaque HTTP responses by the
global handler — no internal details are ever exposed to API clients.
"""
from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.status import (
    HTTP_400_BAD_REQUEST,
    HTTP_404_NOT_FOUND,
    HTTP_410_GONE,
    HTTP_413_REQUEST_ENTITY_TOO_LARGE,
    HTTP_422_UNPROCESSABLE_ENTITY,
    HTTP_500_INTERNAL_SERVER_ERROR,
    HTTP_503_SERVICE_UNAVAILABLE,
)


# ---------------------------------------------------------------------------
# Base context exceptions
# ---------------------------------------------------------------------------

class IngestionError(Exception):
    """Base for all IngestionContext errors."""
    http_status: int = HTTP_400_BAD_REQUEST
    user_message: str = "The file could not be accepted for processing."


class ParsingError(Exception):
    """Base for all ParsingContext errors."""
    http_status: int = HTTP_422_UNPROCESSABLE_ENTITY
    user_message: str = "The document could not be converted."


class AssetError(Exception):
    """Base for all AssetContext errors."""
    http_status: int = HTTP_500_INTERNAL_SERVER_ERROR
    user_message: str = "The output package could not be assembled."


# ---------------------------------------------------------------------------
# IngestionContext — specific exceptions
# ---------------------------------------------------------------------------

class PayloadTooLargeError(IngestionError):
    """File exceeds the maximum allowed upload size."""
    http_status = HTTP_413_REQUEST_ENTITY_TOO_LARGE
    user_message = "File exceeds the maximum allowed size of 50 MB."


class BatchSizeLimitExceededError(IngestionError):
    """Batch upload exceeds the maximum allowed file count."""
    http_status = HTTP_400_BAD_REQUEST
    user_message = "Batch upload exceeds the maximum allowed count of 10 files."


class MagicNumberMismatchError(IngestionError):
    """File signature does not match its claimed type."""
    http_status = HTTP_400_BAD_REQUEST
    user_message = "The uploaded file could not be validated. Please check the file and try again."


class UnsupportedFileTypeError(IngestionError):
    """File type is not supported by the converter."""
    http_status = HTTP_400_BAD_REQUEST
    user_message = "This file type is not supported. Accepted types: PDF, DOCX, XLSX, HTML, TXT, CSV, JSON, XML."


class SandboxCreationError(IngestionError):
    """Isolated workspace directory could not be created."""
    http_status = HTTP_500_INTERNAL_SERVER_ERROR
    user_message = "An unexpected error occurred while preparing the conversion environment."


class VirusDetectedError(IngestionError):
    """Antivirus scan flagged the file as malicious."""
    http_status = HTTP_400_BAD_REQUEST
    user_message = "The file was rejected by the security scanner. Please ensure it is free of malware."


class AntivirusUnavailableError(IngestionError):
    """ClamAV daemon is unreachable or returned an error."""
    http_status = HTTP_503_SERVICE_UNAVAILABLE
    user_message = "The security scanning service is temporarily unavailable. Please try again shortly."


class TaskNotFoundError(IngestionError):
    """Conversion task does not exist or has already been purged."""
    http_status = HTTP_404_NOT_FOUND
    user_message = "The requested conversion task was not found."


class TaskAlreadyPurgedError(IngestionError):
    """Conversion task artifacts have been securely purged."""
    http_status = HTTP_410_GONE
    user_message = "The conversion result has expired and is no longer available for download."


# ---------------------------------------------------------------------------
# ParsingContext — specific exceptions
# ---------------------------------------------------------------------------

class MarkdownCompilationError(ParsingError):
    """MarkItDown failed to convert the document structure."""
    http_status = HTTP_422_UNPROCESSABLE_ENTITY
    user_message = "The document could not be converted to Markdown. The file may be corrupted or unsupported."


class PdfImageExtractionError(ParsingError):
    """PDF image extraction via pypdf failed."""
    http_status = HTTP_422_UNPROCESSABLE_ENTITY
    user_message = "Image assets could not be extracted from the PDF."


class XmlInjectionAttemptError(ParsingError):
    """Document contains suspicious XML/entity patterns (XXE, Billion Laughs)."""
    http_status = HTTP_400_BAD_REQUEST
    user_message = "The file was rejected due to a security policy violation."


# ---------------------------------------------------------------------------
# AssetContext — specific exceptions
# ---------------------------------------------------------------------------

class Base64EncodingError(AssetError):
    """Binary image could not be Base64-encoded for inline embedding."""
    http_status = HTTP_500_INTERNAL_SERVER_ERROR
    user_message = "An error occurred while embedding image assets into the Markdown output."


class ZipPackagingError(AssetError):
    """ZIP archive assembly failed."""
    http_status = HTTP_500_INTERNAL_SERVER_ERROR
    user_message = "The output package could not be created. Please try again."


# ---------------------------------------------------------------------------
# Global exception handler (registered in main.py)
# ---------------------------------------------------------------------------

async def domain_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Translate all domain exceptions into opaque, user-safe HTTP responses.

    IMPORTANT: This handler MUST NOT expose stack traces, internal class names,
    file paths, or any implementation detail to the client. Principle VI.
    """
    if isinstance(exc, (IngestionError, ParsingError, AssetError)):
        return JSONResponse(
            status_code=exc.http_status,  # type: ignore[union-attr]
            content={"error": exc.user_message},  # type: ignore[union-attr]
        )
    # Fallback for any unhandled exception — still opaque
    return JSONResponse(
        status_code=HTTP_500_INTERNAL_SERVER_ERROR,
        content={"error": "An unexpected error occurred. Please try again."},
    )
