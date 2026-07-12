"""Unit tests for batch ZIP packaging logic."""
from src.AssetContext.packager import assemble_batch_zip, assemble_zip_package
import zipfile
import io


def test_single_item_batch_zip_is_valid_zip() -> None:
    result = assemble_batch_zip({"file1.md": "# Hello"})
    buf = io.BytesIO(result)
    assert zipfile.is_zipfile(buf)


def test_batch_zip_contains_all_items() -> None:
    items = {"a.md": "# A", "b.md": "# B", "c.zip": b"\x50\x4b\x03\x04"}
    result = assemble_batch_zip(items)
    buf = io.BytesIO(result)
    with zipfile.ZipFile(buf) as zf:
        names = zf.namelist()
    assert "a.md" in names
    assert "b.md" in names
    assert "c.zip" in names


def test_zip_package_structure_contains_markdown_file() -> None:
    result = assemble_zip_package("# Test\n\n![img](images/img.png)", {"images/img.png": b"PNG"})
    buf = io.BytesIO(result)
    with zipfile.ZipFile(buf) as zf:
        names = zf.namelist()
    assert "document.md" in names
    assert "images/img.png" in names


def test_zip_package_markdown_has_relative_links() -> None:
    md = "# Test\n![logo](images/logo.png)"
    result = assemble_zip_package(md, {"images/logo.png": b"PNG"})
    buf = io.BytesIO(result)
    with zipfile.ZipFile(buf) as zf:
        content = zf.read("document.md").decode("utf-8")
    assert "images/logo.png" in content
