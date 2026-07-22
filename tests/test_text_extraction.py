"""
Tests for text extraction.
"""

from pathlib import Path

import fitz

from pdfclean.pdf.document import PDFDocument
from pdfclean.pdf.text_block import TextBlock


def test_extract_text_blocks(tmp_path: Path) -> None:
    pdf_file = tmp_path / "sample.pdf"

    doc = fitz.open()

    page = doc.new_page()

    page.insert_text(
        (72, 72),
        "PDFClean Pro Test",
    )

    doc.save(pdf_file)
    doc.close()

    pdf = PDFDocument(pdf_file)

    pdf.open()

    blocks = pdf.extract_text_blocks()

    pdf.close()

    assert len(blocks) > 0

    assert isinstance(blocks[0], TextBlock)

    assert any(
        "PDFClean Pro Test" in block.text
        for block in blocks
    )


def test_extract_closed_document(tmp_path: Path) -> None:
    pdf_file = tmp_path / "sample.pdf"

    doc = fitz.open()

    doc.new_page()

    doc.save(pdf_file)

    doc.close()

    pdf = PDFDocument(pdf_file)

    try:
        pdf.extract_text_blocks()
        assert False
    except Exception:
        assert True