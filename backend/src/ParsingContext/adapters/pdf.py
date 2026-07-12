"""pypdf-based image extractor for PDF documents.

Extracts raw binary image data from embedded PDF images without rasterisation.
PDF JavaScript payloads are treated as inert text by pypdf by default.
"""
from __future__ import annotations
import logging
from dataclasses import dataclass
from pathlib import Path
import pypdf
from src.exceptions import PdfImageExtractionError, MarkdownCompilationError

logger = logging.getLogger(__name__)


@dataclass
class ImageAsset:
    """Raw binary image extracted from a PDF page."""
    page_index: int
    image_index: int
    name: str
    data: bytes
    extension: str  # e.g. "png", "jpg"


import pdfplumber

def table_to_markdown(table: list[list[str | None]]) -> str:
    """Format a list-of-lists table into a GFM Markdown table grid."""
    if not table or not table[0]:
        return ""
    
    clean_table = []
    for row in table:
        clean_row = []
        for cell in row:
            val = cell or ""
            # Clean up newlines and pipe characters to preserve markdown table syntax
            val = val.replace("\r", " ").replace("\n", " ").replace("|", "\\|").strip()
            clean_row.append(val)
        clean_table.append(clean_row)
        
    headers = clean_table[0]
    rows = clean_table[1:]
    
    md = "| " + " | ".join(headers) + " |\n"
    md += "| " + " | ".join(["---"] * len(headers)) + " |\n"
    for row in rows:
        if len(row) < len(headers):
            row += [""] * (len(headers) - len(row))
        md += "| " + " | ".join(row[:len(headers)]) + " |\n"
    return md


def extract_text(pdf_path: Path) -> str:
    """Extract structured text and tables from all PDF pages via pdfplumber.

    Table layouts are preserved as GFM Markdown tables.
    Raises:
        MarkdownCompilationError: If extraction fails.
    """
    try:
        parts: list[str] = []
        with pdfplumber.open(str(pdf_path)) as pdf:
            for page in pdf.pages:
                tables = page.find_tables()
                valid_tables = [t for t in tables if t.bbox and len(t.bbox) == 4]
                valid_tables = sorted(valid_tables, key=lambda t: t.bbox[1])
                
                last_bottom = 0
                page_content: list[str] = []
                
                for table in valid_tables:
                    t_top = table.bbox[1]
                    t_bottom = table.bbox[3]
                    
                    # Extract text above this table
                    if t_top > last_bottom:
                        try:
                            above_page = page.crop((0, last_bottom, page.width, t_top), relative=False)
                            text = above_page.extract_text()
                            if text and text.strip():
                                page_content.append(text.strip())
                        except Exception:
                            pass
                    
                    # Format and insert the table
                    try:
                        raw_table = table.extract()
                        if raw_table:
                            md_table = table_to_markdown(raw_table)
                            if md_table:
                                page_content.append(md_table.strip())
                    except Exception:
                        pass
                    
                    last_bottom = t_bottom
                
                # Extract remaining text below the last table
                if valid_tables and last_bottom < page.height:
                    try:
                        below_page = page.crop((0, last_bottom, page.width, page.height), relative=False)
                        text = below_page.extract_text()
                        if text and text.strip():
                            page_content.append(text.strip())
                    except Exception:
                        pass
                
                # If no tables were found, fall back to simple full-page text extraction
                if not valid_tables:
                    text = page.extract_text()
                    if text and text.strip():
                        page_content.append(text.strip())
                
                if page_content:
                    parts.append("\n\n".join(page_content))
                    
        return "\n\n---\n\n".join(parts)
    except Exception as exc:
        logger.warning("[parsing] PDF structured text extraction failed: %s", type(exc).__name__)
        raise MarkdownCompilationError() from exc


def extract_images(pdf_path: Path) -> list[ImageAsset]:
    """Extract embedded binary image assets from a PDF.

    Returns a list of ImageAsset objects. An empty list is valid for text-only PDFs.

    Raises:
        PdfImageExtractionError: If the PDF cannot be opened or an image is corrupt.
    """
    try:
        reader = pypdf.PdfReader(str(pdf_path))
        assets: list[ImageAsset] = []
        for page_idx, page in enumerate(reader.pages):
            for img_idx, image_obj in enumerate(page.images):
                raw_data: bytes = image_obj.data
                name: str = image_obj.name or f"img_{page_idx}_{img_idx}"
                ext = name.rsplit(".", 1)[-1].lower() if "." in name else "png"
                assets.append(
                    ImageAsset(
                        page_index=page_idx,
                        image_index=img_idx,
                        name=name,
                        data=raw_data,
                        extension=ext,
                    )
                )
        return assets
    except PdfImageExtractionError:
        raise
    except Exception as exc:
        logger.warning("[parsing] PDF image extraction failed: %s", type(exc).__name__)
        raise PdfImageExtractionError() from exc
