"""Unit tests for the custom exception hierarchy and global handler (Principle VI)."""
import pytest
from fastapi.testclient import TestClient
from fastapi import FastAPI
from src.exceptions import (
    domain_exception_handler,
    IngestionError, ParsingError, AssetError,
    PayloadTooLargeError,
    MagicNumberMismatchError,
    UnsupportedFileTypeError,
    SandboxCreationError,
    VirusDetectedError,
    AntivirusUnavailableError,
    TaskNotFoundError,
    TaskAlreadyPurgedError,
    MarkdownCompilationError,
    PdfImageExtractionError,
    XmlInjectionAttemptError,
    Base64EncodingError,
    ZipPackagingError,
)


def make_app(*exc_types: type[Exception]) -> TestClient:
    app = FastAPI()
    for exc_type in exc_types:
        app.add_exception_handler(exc_type, domain_exception_handler)
    return TestClient(app, raise_server_exceptions=False)


def test_all_exceptions_are_subclasses_of_context_bases() -> None:
    ingestion_excs = [
        PayloadTooLargeError, MagicNumberMismatchError, UnsupportedFileTypeError,
        SandboxCreationError, VirusDetectedError, AntivirusUnavailableError,
        TaskNotFoundError, TaskAlreadyPurgedError,
    ]
    parsing_excs = [MarkdownCompilationError, PdfImageExtractionError, XmlInjectionAttemptError]
    asset_excs = [Base64EncodingError, ZipPackagingError]

    for exc in ingestion_excs:
        assert issubclass(exc, IngestionError), f"{exc.__name__} must inherit IngestionError"
    for exc in parsing_excs:
        assert issubclass(exc, ParsingError), f"{exc.__name__} must inherit ParsingError"
    for exc in asset_excs:
        assert issubclass(exc, AssetError), f"{exc.__name__} must inherit AssetError"


def test_virus_detected_returns_400_with_generic_message() -> None:
    app = FastAPI()
    app.add_exception_handler(IngestionError, domain_exception_handler)

    @app.get("/test")
    async def _route() -> None:
        raise VirusDetectedError()

    client = TestClient(app, raise_server_exceptions=False)
    res = client.get("/test")
    assert res.status_code == 400
    body = res.json()
    assert "error" in body
    assert "virus" in body["error"].lower() or "scanner" in body["error"].lower()
    # Must not contain internal details
    assert "VirusDetectedError" not in body["error"]
    assert "clamd" not in body["error"].lower()


def test_payload_too_large_returns_413() -> None:
    app = FastAPI()
    app.add_exception_handler(IngestionError, domain_exception_handler)

    @app.get("/test")
    async def _route() -> None:
        raise PayloadTooLargeError()

    client = TestClient(app, raise_server_exceptions=False)
    res = client.get("/test")
    assert res.status_code == 413


def test_task_purged_returns_410() -> None:
    app = FastAPI()
    app.add_exception_handler(IngestionError, domain_exception_handler)

    @app.get("/test")
    async def _route() -> None:
        raise TaskAlreadyPurgedError()

    client = TestClient(app, raise_server_exceptions=False)
    res = client.get("/test")
    assert res.status_code == 410
