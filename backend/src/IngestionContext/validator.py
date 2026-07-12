"""Magic-number (hex signature) file type validator for the IngestionContext.

Security: Extension claims and MIME-type headers are NEVER trusted.
Only the raw byte signature is authoritative (Principle V).
"""
from __future__ import annotations
from dataclasses import dataclass
from enum import StrEnum
from src.exceptions import MagicNumberMismatchError, UnsupportedFileTypeError


class SupportedMimeType(StrEnum):
    PDF = "application/pdf"
    DOCX = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    HTML = "text/html"
    TXT = "text/plain"
    CSV = "text/csv"
    JSON = "application/json"
    XML = "application/xml"


@dataclass(frozen=True)
class _Signature:
    offset: int
    magic: bytes
    mime: SupportedMimeType


_SIGNATURES: list[_Signature] = [
    _Signature(0, b"%PDF", SupportedMimeType.PDF),
    # DOCX/XLSX are ZIP-based; zip magic at offset 0
    _Signature(0, b"PK\x03\x04", SupportedMimeType.DOCX),  # refined by extension
    _Signature(0, b"<?xml", SupportedMimeType.XML),
    _Signature(0, b"<html", SupportedMimeType.HTML),
    _Signature(0, b"<!DOCTYPE", SupportedMimeType.HTML),
    _Signature(0, b"{", SupportedMimeType.JSON),
    _Signature(0, b"[", SupportedMimeType.JSON),
]

_EXTENSION_MAP: dict[str, SupportedMimeType] = {
    ".pdf": SupportedMimeType.PDF,
    ".docx": SupportedMimeType.DOCX,
    ".xlsx": SupportedMimeType.XLSX,
    ".html": SupportedMimeType.HTML,
    ".htm": SupportedMimeType.HTML,
    ".txt": SupportedMimeType.TXT,
    ".csv": SupportedMimeType.CSV,
    ".json": SupportedMimeType.JSON,
    ".xml": SupportedMimeType.XML,
}

_TEXT_EXTENSIONS: frozenset[str] = frozenset([".txt", ".csv", ".json", ".xml", ".html", ".htm"])


def validate_file_signature(filename: str, file_bytes: bytes) -> SupportedMimeType:
    """Validate file by hex signature; return detected MIME type.

    Raises:
        UnsupportedFileTypeError: Extension is not in the allowed list.
        MagicNumberMismatchError: Byte signature does not match the extension claim.
    """
    ext = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""

    if ext not in _EXTENSION_MAP:
        raise UnsupportedFileTypeError()

    expected_mime = _EXTENSION_MAP[ext]

    # Text-based formats: validate they are readable UTF-8/ASCII, no binary header
    if ext in _TEXT_EXTENSIONS:
        try:
            file_bytes[:512].decode("utf-8", errors="strict")
        except UnicodeDecodeError as exc:
            raise MagicNumberMismatchError() from exc
        # Extra guard: if text file starts with binary PK or PDF signature, reject
        if file_bytes[:4] == b"PK\x03\x04" or file_bytes[:4] == b"%PDF":
            raise MagicNumberMismatchError()
        return expected_mime

    # ZIP-based (DOCX, XLSX): check PK header, then trust extension
    if ext in (".docx", ".xlsx"):
        if not file_bytes[:4] == b"PK\x03\x04":
            raise MagicNumberMismatchError()
        return expected_mime

    # Binary formats: match against known signatures
    matched_mime = None
    for sig in _SIGNATURES:
        candidate = file_bytes[sig.offset : sig.offset + len(sig.magic)]
        if candidate.lower() == sig.magic.lower():
            matched_mime = sig.mime
            break

    if matched_mime != expected_mime:
        raise MagicNumberMismatchError()

    return matched_mime
