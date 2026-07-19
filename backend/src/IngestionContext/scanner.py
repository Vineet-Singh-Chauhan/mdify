"""ClamAV client wrapper for the IngestionContext.

Streams file bytes to the clamd daemon over a network socket.
No shell subprocess is invoked (Zero-Shell principle, Principle V).
"""
from __future__ import annotations
import logging
import time
from pathlib import Path
import clamd
from src.config import settings
from src.exceptions import VirusDetectedError, AntivirusUnavailableError

logger = logging.getLogger(__name__)

# Transient errors that are safe to retry (network hiccups, ClamAV busy
# reloading signatures, slow scan on large files).
_TRANSIENT_ERRORS = (
    ConnectionRefusedError,
    ConnectionResetError,
    TimeoutError,
    OSError,
    clamd.ConnectionError,
)

_MAX_RETRIES = 2
_INITIAL_BACKOFF_SECONDS = 3


def _get_clamav_client() -> clamd.ClamdNetworkSocket:
    """Return a configured ClamAV network socket client."""
    return clamd.ClamdNetworkSocket(
        host=settings.clamav_host,
        port=settings.clamav_port,
        timeout=settings.clamav_scan_timeout,
    )


def scan_file(file_path: Path) -> None:
    """Scan a file for malware using the ClamAV daemon.

    Retries up to ``_MAX_RETRIES`` times with exponential backoff for
    transient network/timeout errors before giving up.

    Raises:
        VirusDetectedError: If the file contains a known malware signature.
        AntivirusUnavailableError: If the ClamAV daemon is unreachable.
    """
    last_exc: Exception | None = None

    for attempt in range(_MAX_RETRIES + 1):
        try:
            client = _get_clamav_client()
            result = client.scan(str(file_path))
            break  # success — exit retry loop
        except _TRANSIENT_ERRORS as exc:
            last_exc = exc
            if attempt < _MAX_RETRIES:
                wait = _INITIAL_BACKOFF_SECONDS * (2 ** attempt)
                logger.warning(
                    "[scanner] Transient ClamAV error (attempt %d/%d): %s — retrying in %ds",
                    attempt + 1, _MAX_RETRIES + 1, type(exc).__name__, wait,
                )
                time.sleep(wait)
            else:
                logger.error(
                    "[scanner] ClamAV unavailable after %d attempts: %s",
                    _MAX_RETRIES + 1, type(exc).__name__,
                )
                raise AntivirusUnavailableError() from exc
        except Exception as exc:
            logger.error("[scanner] Unexpected scan error: %s", type(exc).__name__)
            raise AntivirusUnavailableError() from exc
    else:
        # All retries exhausted (should not reach here, but guard anyway)
        raise AntivirusUnavailableError() from last_exc

    if result is None:
        logger.warning("[scanner] ClamAV returned no result for %s", file_path.name)
        raise AntivirusUnavailableError()

    for path, (status, threat_name) in result.items():
        if status == "FOUND":
            logger.warning("[scanner] Virus detected in %s: %s", file_path.name, "[REDACTED]")
            raise VirusDetectedError()
        elif status != "OK":
            logger.error("[scanner] Unexpected ClamAV status for %s: %s", file_path.name, status)
            raise AntivirusUnavailableError()

    logger.info("[scanner] File %s passed AV scan.", file_path.name)
