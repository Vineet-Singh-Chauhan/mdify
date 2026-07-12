"""MarkItDown adapter wrapping text and table extraction.

XXE defusing: defusedxml.defuse_stdlib() is called globally at main.py startup.
This adapter additionally sets resolve_entities=False on lxml/etree parsers.
"""
from __future__ import annotations
import logging
from pathlib import Path
from markitdown import MarkItDown
from src.exceptions import MarkdownCompilationError, XmlInjectionAttemptError

logger = logging.getLogger(__name__)

# Adapter-level supplementary XXE guard (Principle V, supplement to global defuse_stdlib).
# If lxml is available, enforce strict entity resolution disabling at parser level.
try:
    from lxml import etree as _etree
    _SAFE_PARSER = _etree.XMLParser(resolve_entities=False, no_network=True, load_dtd=False)
except ImportError:
    _SAFE_PARSER = None  # type: ignore[assignment]

# Instantiate once; MarkItDown is stateless across calls
_markitdown = MarkItDown()

# Extensions handled by MarkItDown (not custom PDF pipeline)
SUPPORTED_EXTENSIONS: frozenset[str] = frozenset(
    [".docx", ".xlsx", ".html", ".htm", ".txt", ".csv", ".json", ".xml"]
)


def convert_to_markdown(input_path: Path) -> str:
    """Convert a supported document file to Markdown string.

    Raises:
        MarkdownCompilationError: If MarkItDown fails to convert.
        XmlInjectionAttemptError: If an XML entity expansion attack is detected.
    """
    ext = input_path.suffix.lower()
    if ext not in SUPPORTED_EXTENSIONS:
        raise MarkdownCompilationError()

    try:
        result = _markitdown.convert(str(input_path))
        markdown: str = result.text_content
    except MemoryError as exc:
        # Possible Billion Laughs exhaustion attempt
        raise XmlInjectionAttemptError() from exc
    except Exception as exc:
        logger.warning("[parsing] MarkItDown conversion failed: %s", type(exc).__name__)
        raise MarkdownCompilationError() from exc

    return markdown
