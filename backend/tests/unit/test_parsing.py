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


def test_convert_real_txt_success(tmp_path: Path) -> None:
    txt_file = tmp_path / "test.txt"
    txt_file.write_text("Hello MarkItDown text parsing")
    res = convert_to_markdown(txt_file)
    assert "Hello MarkItDown text parsing" in res


def test_convert_real_html_success(tmp_path: Path) -> None:
    html_file = tmp_path / "test.html"
    html_file.write_text("<html><body><h1>Title</h1><p>Paragraph</p></body></html>")
    res = convert_to_markdown(html_file)
    assert "# Title" in res
    assert "Paragraph" in res


def test_convert_real_csv_success(tmp_path: Path) -> None:
    csv_file = tmp_path / "test.csv"
    csv_file.write_text("Header1,Header2\nValue1,Value2")
    res = convert_to_markdown(csv_file)
    assert "Header1" in res
    assert "Value1" in res


def test_convert_real_json_success(tmp_path: Path) -> None:
    json_file = tmp_path / "test.json"
    json_file.write_text('{"key": "value"}')
    res = convert_to_markdown(json_file)
    assert "key" in res
    assert "value" in res


def test_convert_real_xml_success(tmp_path: Path) -> None:
    xml_file = tmp_path / "test.xml"
    xml_file.write_text("<root><element>content</element></root>")
    res = convert_to_markdown(xml_file)
    assert "element" in res
    assert "content" in res


def test_convert_xml_with_xxe_payload_defused(tmp_path: Path) -> None:
    xml_file = tmp_path / "xxe.xml"
    xml_file.write_text(
        '<?xml version="1.0" encoding="utf-8"?>\n'
        '<!DOCTYPE test [\n'
        '  <!ENTITY xxe SYSTEM "file:///etc/passwd">\n'
        ']>\n'
        '<test>&xxe;</test>'
    )
    res = convert_to_markdown(xml_file)
    assert "root:x:" not in res


