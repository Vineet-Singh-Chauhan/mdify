"""Integration tests for ClamAV scanning — uses a mock clamd."""
from unittest.mock import MagicMock, patch
from pathlib import Path
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


@patch("src.IngestionContext.scanner.clamd")
def test_clamav_unavailable_raises_service_error(mock_clamd: MagicMock, tmp_path: Path) -> None:
    test_file = tmp_path / "doc.pdf"
    test_file.write_bytes(b"%PDF test")
    mock_clamd.ClamdNetworkSocket.return_value.scan.side_effect = ConnectionRefusedError()
    with pytest.raises(AntivirusUnavailableError):
        scan_file(test_file)
