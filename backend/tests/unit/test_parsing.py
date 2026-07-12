"""Unit tests for document parsing using MarkItDown adapter."""
from pathlib import Path
import pytest
from unittest.mock import patch, MagicMock
from src.ParsingContext.adapters.markitdown import convert_to_markdown
from src.exceptions import MarkdownCompilationError, XmlInjectionAttemptError


def test_convert_unsupported_type_raises_compilation_error(tmp_path: Path) -> None:
    unsupported = tmp_path / "test.invalid"
    unsupported.write_text("content")
    with pytest.raises(MarkdownCompilationError):
        convert_to_markdown(unsupported)


@patch("src.ParsingContext.adapters.markitdown._markitdown")
def test_convert_txt_success(mock_mid: MagicMock, tmp_path: Path) -> None:
    txt_file = tmp_path / "test.txt"
    txt_file.write_text("Hello Text")
    mock_result = MagicMock()
    mock_result.text_content = "Hello Text"
    mock_mid.convert.return_value = mock_result

    res = convert_to_markdown(txt_file)
    assert res == "Hello Text"
    mock_mid.convert.assert_called_once_with(str(txt_file))


@patch("src.ParsingContext.adapters.markitdown._markitdown")
def test_convert_compilation_error_raised(mock_mid: MagicMock, tmp_path: Path) -> None:
    txt_file = tmp_path / "test.txt"
    txt_file.write_text("Hello Text")
    mock_mid.convert.side_effect = Exception("failed conversion")

    with pytest.raises(MarkdownCompilationError):
        convert_to_markdown(txt_file)


@patch("src.ParsingContext.adapters.markitdown._markitdown")
def test_billion_laughs_expansion_raises_xml_injection_error(mock_mid: MagicMock, tmp_path: Path) -> None:
    xml_file = tmp_path / "test.xml"
    xml_file.write_text("<xml>test</xml>")
    mock_mid.convert.side_effect = MemoryError()

    with pytest.raises(XmlInjectionAttemptError):
        convert_to_markdown(xml_file)
