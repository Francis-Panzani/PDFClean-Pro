from __future__ import annotations

from pathlib import Path

import fitz

from pdfclean.pdf import document
from pdfclean.pdf.document import PDFDocument
from pdfclean.detector.header import Header
from pdfclean.detector.footer import Footer
from pdfclean.detector.page_number import PageNumber

class PDFDebug:

    def draw_regions(
        self,
        document: PDFDocument,
        headers: list[Header],
        footers: list[Footer],
        page_numbers: list[PageNumber],
        output_path: Path,
    ) -> None:
        for header in headers:
            for page in header.pages:
                rect = fitz.Rect(
                    header.x0,
                    header.y0,
                    header.x1,
                    header.y1,
                )
                document.document[page].draw_rect(
                rect,
                color=(1, 0, 0),
                width=0.8,
            )
            for footer in footers:
                            rect = fitz.Rect(
                                footer.x0,
                                footer.y0,
                                footer.x1,
                                footer.y1,
                            )
                            document.document[page].draw_rect(
                            rect,
                            color=(0, 0, 1),
                            width=0.8,
                        )
            for page_number in page_numbers:
                rect = fitz.Rect(
                    page_number.x0,
                    page_number.y0,
                    page_number.x1,
                    page_number.y1,
                )
                document.document[page].draw_rect(
                rect,
                color=(0, 1, 0),
                width=0.8,
            )   
            document.save_copy(output_path)   