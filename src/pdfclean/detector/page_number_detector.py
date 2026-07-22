"""
PDFClean Pro - Page number detector.
"""

from __future__ import annotations

import re

from pdfclean.detector.fingerprint import Fingerprint
from pdfclean.detector.page_number import PageNumber


class PageNumberDetector:
    """
    Detect page numbers from fingerprints.

    The detector supports formats such as:

        12
        - 12 -
        Page 12
        p.12
    """

    #
    # Footer area
    #
    MIN_Y = 700.0

    #
    # At least two occurrences
    #
    MIN_OCCURRENCES = 2

    #
    # Supported page number patterns
    #
    PATTERNS = (
        r"^\d+$",
        r"^-\s*\d+\s*-$",
        r"^Page\s+\d+$",
        r"^page\s+\d+$",
        r"^P\.\s*\d+$",
        r"^p\.\s*\d+$",
    )

    def detect(
        self,
        fingerprints: list[Fingerprint],
    ) -> list[PageNumber]:
        """
        Detect page numbers.
        """

        numbers: list[PageNumber] = []

        for fingerprint in fingerprints:

            if fingerprint.occurrences < self.MIN_OCCURRENCES:
                continue

            if fingerprint.y0 < self.MIN_Y:
                continue

            text = fingerprint.text.strip()

            if not text:
                continue

            if any(
                re.fullmatch(pattern, text)
                for pattern in self.PATTERNS
            ):
                numbers.append(PageNumber(fingerprint))

        return numbers