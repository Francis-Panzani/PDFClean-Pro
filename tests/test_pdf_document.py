"""
Tests for PDFDocument.
"""

from pathlib import Path

import fitz

from pdfclean.pdf.document import PDFDocument


def test_open_pdf(tmp_path: Path) -> None:
    pdf_file = tmp_path / "test.pdf"

    doc = fitz.open()
    doc.new_page()
    doc.save(pdf_file)
    doc.close()

    pdf = PDFDocument(pdf_file)

    pdf.open()

    assert pdf.is_open is True
    assert pdf.page_count == 1

    pdf.close()


def test_metadata_property(tmp_path: Path) -> None:
    pdf_file = tmp_path / "test.pdf"

    doc = fitz.open()
    doc.new_page()
    doc.save(pdf_file)
    doc.close()

    pdf = PDFDocument(pdf_file)

    pdf.open()

    assert isinstance(pdf.metadata, dict)

    pdf.close()


def test_context_manager(tmp_path: Path) -> None:
    pdf_file = tmp_path / "test.pdf"

    doc = fitz.open()
    doc.new_page()
    doc.save(pdf_file)
    doc.close()

    with PDFDocument(pdf_file) as pdf:
        assert pdf.page_count == 1

    assert pdf.is_open is False