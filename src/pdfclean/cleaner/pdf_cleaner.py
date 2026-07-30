"""
PDFClean Pro - PDF cleaning engine.
"""

from __future__ import annotations

import fitz

from pdfclean.cleaner.clean_region import CleanRegion
from pdfclean.detector.footer import Footer
from pdfclean.detector.header import Header
from pdfclean.detector.page_number import PageNumber
from pdfclean.pdf.document import PDFDocument


class PDFCleaner:
    """
    Build cleaning regions and apply them to a PDF.
    """

    def __init__(self) -> None:
        self._regions: list[CleanRegion] = []

    @property
    def regions(self) -> list[CleanRegion]:
        """
        Return generated cleaning regions.
        """
        return self._regions

    def clear(self) -> None:
        """
        Remove all generated regions.
        """
        self._regions.clear()

    def build_regions(
        self,
        headers: list[Header],
        footers: list[Footer],
        page_numbers: list[PageNumber],
    ) -> list[CleanRegion]:
        """
        Build all cleaning regions.
        """

        self.clear()

        #
        # Headers
        #
        for header in headers:

            for page in header.pages:

                self._regions.append(
                    CleanRegion(
                        page=page,
                        x0=header.fingerprint.x0,
                        y0=header.fingerprint.y0,
                        x1=header.fingerprint.x1,
                        y1=header.fingerprint.y1,
                    )
                )

        #
        # Footers
        #
        for footer in footers:

            for page in footer.pages:

                self._regions.append(
                    CleanRegion(
                        page=page,
                        x0=footer.fingerprint.x0,
                        y0=footer.fingerprint.y0,
                        x1=footer.fingerprint.x1,
                        y1=footer.fingerprint.y1,
                    )
                )

        #
        # Page numbers
        #
        for number in page_numbers:

            for page in number.pages:

                self._regions.append(
                    CleanRegion(
                        page=page,
                        x0=number.fingerprint.x0,
                        y0=number.fingerprint.y0,
                        x1=number.fingerprint.x1,
                        y1=number.fingerprint.y1,
                    )
                )

        return self._regions

    def apply(
        self,
        pdf: PDFDocument,
    ) -> None:
        """
        Apply all cleaning regions using PDF redactions.
        """

        if pdf.document is None:
            raise RuntimeError("PDF is not open.")

        document: fitz.Document = pdf.document

        for region in self._regions:

            page = document[region.page]

            rect = fitz.Rect(
                region.x0,
                region.y0,
                region.x1,
                region.y1,
            )

            page.add_redact_annot(rect)

        #
        # Apply page by page.
        #
        for page in document:
            page.apply_redactions()

