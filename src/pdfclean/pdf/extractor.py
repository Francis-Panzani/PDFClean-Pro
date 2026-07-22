"""
PDFClean Pro - Text extraction.

Convert PyMuPDF blocks into TextBlock objects.
"""

from __future__ import annotations

from typing import List

import fitz

from pdfclean.pdf.text_block import TextBlock


class TextExtractor:
    """
    Extract text blocks from a PDF document.
    """

    @staticmethod
    def extract(document: fitz.Document) -> List[TextBlock]:
        """
        Extract all text blocks from every page of a PDF.

        Parameters
        ----------
        document:
            Open PyMuPDF document.

        Returns
        -------
        list[TextBlock]
            List of extracted text blocks.
        """

        blocks: list[TextBlock] = []

        for page_number, page in enumerate(document):

            page_blocks = page.get_text("blocks")

            for block_number, block in enumerate(page_blocks):

                # PyMuPDF returns at least:
                #
                # (x0, y0, x1, y1, text, block_no, block_type)
                #
                if len(block) < 7:
                    continue

                x0 = float(block[0])
                y0 = float(block[1])
                x1 = float(block[2])
                y1 = float(block[3])

                text = str(block[4])

                block_type = int(block[6])

                blocks.append(
                    TextBlock(
                        page=page_number,
                        block_no=block_number,
                        x0=x0,
                        y0=y0,
                        x1=x1,
                        y1=y1,
                        text=text,
                        block_type=block_type,
                    )
                )

        return blocks