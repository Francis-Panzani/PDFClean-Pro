"""
PDF validation orchestration.
"""

from __future__ import annotations
from email.header import Header

from pdfclean.detector.fingerprint_engine import FingerprintEngine
from pdfclean.detector.footer import Footer
from pdfclean.detector.footer_detector import FooterDetector
from pdfclean.detector.header_detector import HeaderDetector
from pdfclean.detector.page_number import PageNumber
from pdfclean.detector.page_number_detector import PageNumberDetector
from pdfclean.pdf.document import PDFDocument


class PDFValidator:
    """
    Validate a PDF document.
    """

    def validate(
        self,
        document: PDFDocument,
    ) -> tuple[list[Header], list[Footer], list[PageNumber]]:
        """
        Detect headers, footers and page numbers.
        """

        blocks = document.extract_text_blocks()

        engine = FingerprintEngine()
        fingerprints = engine.analyse(blocks)

        header_detector = HeaderDetector()
        headers = header_detector.detect(fingerprints)

        footer_detector = FooterDetector()
        footers = footer_detector.detect(fingerprints)

        page_number_detector = PageNumberDetector()
        
        page_numbers = page_number_detector.detect(fingerprints)
        ## temporary debug print
        # for fingerprint in fingerprints:
        #     print(
        #         f"text={fingerprint.text!r} "
        #         f"occurrences={fingerprint.occurrences} "
        #         f"y0={fingerprint.y0}"
        #     )

        return (
            headers,
            footers,
            page_numbers,
        )
