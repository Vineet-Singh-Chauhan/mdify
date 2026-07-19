"""Integration tests for ClamAV scanning — uses a mock clamd."""
from unittest.mock import MagicMock, patch
from pathlib import Path
import clamd
import pytest
from src.IngestionContext.scanner import scan_file
from src.exceptions import VirusDetectedError, AntivirusUnavailableError


@patch("src.IngestionContext.scanner.clamd")
def test_clean_file_passes(mock_clamd: MagicMock, tmp_path: Path) -> None:
    test_file = tmp_path / "clean.txt"
    test_file.write_text("Hello world")
    mock_clamd.ClamdNetworkSocket.return_value.scan.return_value = {
        str(test_file): ("OK", None)
    }
    scan_file(test_file)  # Should not raise


@patch("src.IngestionContext.scanner.clamd")
def test_infected_file_raises_virus_detected(mock_clamd: MagicMock, tmp_path: Path) -> None:
    test_file = tmp_path / "eicar.com"
    test_file.write_bytes(b"X5O!P%@AP[4\\PZX54(P^)7CC)7}$EICAR-STANDARD-ANTIVIRUS-TEST-FILE!$H+H*")
    mock_clamd.ClamdNetworkSocket.return_value.scan.return_value = {
        str(test_file): ("FOUND", "Win.Test.EICAR_HDB-1")
    }
    with pytest.raises(VirusDetectedError):
        scan_file(test_file)


@patch("src.IngestionContext.scanner.time")
@patch("src.IngestionContext.scanner.clamd")
def test_clamav_unavailable_raises_after_retries(
    mock_clamd: MagicMock, mock_time: MagicMock, tmp_path: Path
) -> None:
    """All 3 attempts fail → raises AntivirusUnavailableError."""
    test_file = tmp_path / "doc.pdf"
    test_file.write_bytes(b"%PDF test")
    mock_clamd.ClamdNetworkSocket.return_value.scan.side_effect = ConnectionRefusedError()
    mock_clamd.ConnectionError = clamd.ConnectionError
    with pytest.raises(AntivirusUnavailableError):
        scan_file(test_file)
    # 1 original + 2 retries = 3 total attempts
    assert mock_clamd.ClamdNetworkSocket.return_value.scan.call_count == 3


@patch("src.IngestionContext.scanner.time")
@patch("src.IngestionContext.scanner.clamd")
def test_transient_error_recovers_on_retry(
    mock_clamd: MagicMock, mock_time: MagicMock, tmp_path: Path
) -> None:
    """First attempt times out, second attempt succeeds."""
    test_file = tmp_path / "report.pdf"
    test_file.write_bytes(b"%PDF test")
    mock_clamd.ConnectionError = clamd.ConnectionError
    mock_clamd.ClamdNetworkSocket.return_value.scan.side_effect = [
        clamd.ConnectionError("Error while reading from socket: ('timed out',)"),
        {str(test_file): ("OK", None)},
    ]
    scan_file(test_file)  # Should not raise — recovered on retry
    assert mock_clamd.ClamdNetworkSocket.return_value.scan.call_count == 2

