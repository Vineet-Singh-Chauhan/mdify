"""Unit tests for magic-number validation — TDD gate for Phase 4."""
import pytest
from src.IngestionContext.validator import validate_file_signature
from src.exceptions import MagicNumberMismatchError, UnsupportedFileTypeError


def test_valid_pdf_accepted() -> None:
    raw = b"%PDF-1.4 fake pdf content"
    result = validate_file_signature("document.pdf", raw)
    assert result is not None


def test_exe_renamed_as_pdf_rejected() -> None:
    exe_magic = b"MZ" + b"\x00" * 50  # EXE magic
    with pytest.raises(MagicNumberMismatchError):
        validate_file_signature("report.pdf", exe_magic)


def test_zip_renamed_as_exe_rejected() -> None:
    with pytest.raises(UnsupportedFileTypeError):
        validate_file_signature("malware.exe", b"PK\x03\x04")


def test_valid_docx_accepted() -> None:
    docx_magic = b"PK\x03\x04" + b"\x00" * 20
    result = validate_file_signature("report.docx", docx_magic)
    assert result is not None


def test_valid_txt_accepted() -> None:
    result = validate_file_signature("notes.txt", b"Hello world")
    assert result is not None


def test_binary_renamed_as_txt_rejected() -> None:
    binary = bytes(range(256))
    with pytest.raises(MagicNumberMismatchError):
        validate_file_signature("notes.txt", binary)


def test_unsupported_extension_rejected() -> None:
    with pytest.raises(UnsupportedFileTypeError):
        validate_file_signature("script.sh", b"#!/bin/bash")


def test_spoofed_pdf_with_html_content() -> None:
    with pytest.raises(MagicNumberMismatchError):
        validate_file_signature("document.pdf", b"<html><body>Not a PDF</body></html>")


def test_valid_xlsx_accepted() -> None:
    xlsx_magic = b"PK\x03\x04" + b"\x00" * 20
    result = validate_file_signature("report.xlsx", xlsx_magic)
    assert result is not None


def test_valid_csv_accepted() -> None:
    result = validate_file_signature("data.csv", b"col1,col2\nval1,val2")
    assert result is not None


def test_valid_json_accepted() -> None:
    result = validate_file_signature("config.json", b'{"key": "value"}')
    assert result is not None


def test_valid_xml_accepted() -> None:
    result = validate_file_signature("data.xml", b"<root><item>test</item></root>")
    assert result is not None


def test_valid_html_accepted() -> None:
    result = validate_file_signature("index.html", b"<html><body>hello</body></html>")
    assert result is not None


def test_non_zip_as_docx_rejected() -> None:
    with pytest.raises(MagicNumberMismatchError):
        validate_file_signature("report.docx", b"Not a zip file")


def test_non_zip_as_xlsx_rejected() -> None:
    with pytest.raises(MagicNumberMismatchError):
        validate_file_signature("report.xlsx", b"Not a zip file")


def test_zip_spoofed_as_json_rejected() -> None:
    with pytest.raises(MagicNumberMismatchError):
        validate_file_signature("exploit.json", b"PK\x03\x04filecontent")


def test_pdf_spoofed_as_xml_rejected() -> None:
    with pytest.raises(MagicNumberMismatchError):
        validate_file_signature("exploit.xml", b"%PDF-1.4filecontent")

