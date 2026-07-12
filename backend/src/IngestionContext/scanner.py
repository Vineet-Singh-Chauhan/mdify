"""ClamAV client wrapper for the IngestionContext.

Streams file bytes to the clamd daemon over a network socket.
No shell subprocess is invoked (Zero-Shell principle, Principle V).
"""
from __future__ import annotations
import logging
from pathlib import Path
import clamd
from src.config import settings
from src.exceptions import VirusDetectedError, AntivirusUnavailableError

logger = logging.getLogger(__name__)


def _get_clamav_client() -> clamd.ClamdNetworkSocket:
    """Return a configured ClamAV network socket client."""
    return clamd.ClamdNetworkSocket(
        host=settings.clamav_host,
        port=settings.clamav_port,
        timeout=30,
    )


def scan_file(file_path: Path) -> None:
    """Scan a file for malware using the ClamAV daemon.

    Raises:
        VirusDetectedError: If the file contains a known malware signature.
        AntivirusUnavailableError: If the ClamAV daemon is unreachable.
    """
    try:
        client = _get_clamav_client()
        result = client.scan(str(file_path))
    except (ConnectionRefusedError, TimeoutError, OSError) as exc:
        logger.error("[scanner] ClamAV daemon unavailable: %s", type(exc).__name__)
        raise AntivirusUnavailableError() from exc
    except Exception as exc:
        logger.error("[scanner] Unexpected scan error: %s", type(exc).__name__)
        raise AntivirusUnavailableError() from exc

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
