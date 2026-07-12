"""Unit tests for PDF image extraction."""
from pathlib import Path
import pytest
from unittest.mock import patch, MagicMock
from src.ParsingContext.adapters.pdf import extract_images, extract_text, ImageAsset
from src.exceptions import PdfImageExtractionError, MarkdownCompilationError


def test_extract_from_nonexistent_pdf_raises_error() -> None:
    path = Path("/nonexistent/file.pdf")
    with pytest.raises(MarkdownCompilationError):
        extract_text(path)
    with pytest.raises(PdfImageExtractionError):
        extract_images(path)


@patch("src.ParsingContext.adapters.pdf.pdfplumber.open")
def test_extract_text_success(mock_open: MagicMock) -> None:
    mock_pdf = MagicMock()
    mock_page = MagicMock()
    mock_page.width = 100
    mock_page.height = 100
    mock_page.find_tables.return_value = []
    mock_page.extract_text.return_value = "Page 1 text"
    
    mock_pdf.pages = [mock_page]
    mock_open.return_value.__enter__.return_value = mock_pdf

    pdf_path = Path("test.pdf")
    res = extract_text(pdf_path)
    assert res == "Page 1 text"
    mock_open.assert_called_once_with("test.pdf")


@patch("src.ParsingContext.adapters.pdf.pypdf.PdfReader")
def test_extract_images_success(mock_reader_cls: MagicMock) -> None:
    mock_reader = MagicMock()
    mock_page = MagicMock()
    
    mock_image = MagicMock()
    mock_image.name = "logo.png"
    mock_image.data = b"FAKE_PNG_BYTES"
    
    mock_page.images = [mock_image]
    mock_reader.pages = [mock_page]
    mock_reader_cls.return_value = mock_reader

    pdf_path = Path("test.pdf")
    images = extract_images(pdf_path)
    assert len(images) == 1
    assert images[0].name == "logo.png"
    assert images[0].data == b"FAKE_PNG_BYTES"
    assert images[0].extension == "png"
    assert images[0].page_index == 0
    assert images[0].image_index == 0
