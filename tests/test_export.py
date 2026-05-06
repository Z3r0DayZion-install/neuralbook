"""Tests for NeuralBook export (EPUB + HTML)."""

import zipfile

import pytest

from neuralbook.export import export_epub, export_html
from neuralbook.format import NeuralBookDocument


@pytest.fixture
def sample_doc():
    doc = NeuralBookDocument(
        meta={
            "title": "Test Book",
            "author": "Author",
            "slug": "test-book",
            "edition": "1.0.0",
            "language": "en",
            "license": "MIT",
            "tags": [],
            "word_count": 0,
            "section_count": 0,
        }
    )
    doc.add_section(
        "section", "I", "First Section", "This is the first section body.\nWith multiple lines."
    )
    doc.add_section("section", "II", "Second Section", "Another section here.")
    doc.add_section("part", "I", "Part One", "Part body content.")
    return doc


class TestExportEPUB:
    def test_creates_valid_epub(self, sample_doc, tmp_path):
        out = tmp_path / "test.epub"
        result = export_epub(sample_doc, out)
        assert result == out
        assert out.exists()

    def test_epub_is_zip(self, sample_doc, tmp_path):
        out = tmp_path / "test.epub"
        export_epub(sample_doc, out)
        assert zipfile.is_zipfile(out)

    def test_epub_contains_mimetype(self, sample_doc, tmp_path):
        out = tmp_path / "test.epub"
        export_epub(sample_doc, out)
        with zipfile.ZipFile(out) as zf:
            assert "mimetype" in zf.namelist()

    def test_epub_contains_content(self, sample_doc, tmp_path):
        out = tmp_path / "test.epub"
        export_epub(sample_doc, out)
        with zipfile.ZipFile(out) as zf:
            names = zf.namelist()
            assert any("chapter" in n for n in names)
            assert "OEBPS/content.opf" in names
            assert "OEBPS/nav.xhtml" in names


class TestExportHTML:
    def test_creates_html_file(self, sample_doc, tmp_path):
        out = tmp_path / "test.html"
        result = export_html(sample_doc, out)
        assert result == out
        assert out.exists()

    def test_html_contains_title(self, sample_doc, tmp_path):
        out = tmp_path / "test.html"
        export_html(sample_doc, out)
        content = out.read_text(encoding="utf-8")
        assert "Test Book" in content

    def test_html_contains_sections(self, sample_doc, tmp_path):
        out = tmp_path / "test.html"
        export_html(sample_doc, out)
        content = out.read_text(encoding="utf-8")
        assert "First Section" in content
        assert "Second Section" in content
        assert "Part One" in content

    def test_html_is_valid_markup(self, sample_doc, tmp_path):
        out = tmp_path / "test.html"
        export_html(sample_doc, out)
        content = out.read_text(encoding="utf-8")
        assert content.startswith("<!DOCTYPE html>") or content.startswith("<html")
        assert "</html>" in content
