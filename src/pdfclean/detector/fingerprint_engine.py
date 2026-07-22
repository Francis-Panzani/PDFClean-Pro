"""
PDFClean Pro - Fingerprint Engine.

Groups identical text blocks appearing on multiple pages.
"""

from __future__ import annotations

from collections import OrderedDict

from pdfclean.detector.fingerprint import Fingerprint
from pdfclean.pdf.text_block import TextBlock

import re

class FingerprintEngine:
    """
    Detect repeated text blocks.

    This class does NOT decide whether a block is a header,
    footer or page number. It only groups repeated blocks.
    """
    @staticmethod
    def _normalize_text(text: str) -> str:
        """
        Normalize text before fingerprinting.

        This allows variable page numbers such as:

            - 1 -
            - 2 -
            Page 12

        to be grouped together.
        """

        text = text.strip()

        #
        # Replace every sequence of digits by '#'
        #
        text = re.sub(r"\d+", "#", text)

        #
        # Collapse multiple spaces
        #
        text = re.sub(r"\s+", " ", text)

        return text
    def __init__(self) -> None:
        self._fingerprints: OrderedDict[
            tuple[str, int, int],
            Fingerprint,
        ] = OrderedDict()

    def _build_key(self, block: TextBlock) -> tuple[str, int, int]:
        """
        Build a grouping key.

        Two blocks are considered identical if they have:

        - the same text
        - approximately the same vertical position
        - approximately the same height

        Horizontal position will be analysed later by the
        detector modules.
        """

        return (
            self._normalize_text(block.text),
            round(block.y0),
            round(block.height),
        )

    def analyse(
        self,
        blocks: list[TextBlock],
    ) -> list[Fingerprint]:
        """
        Analyse all extracted text blocks.

        Parameters
        ----------
        blocks:
            Text blocks extracted from a PDF.

        Returns
        -------
        list[Fingerprint]
        """

        self._fingerprints.clear()

        for block in blocks:

            if block.is_empty:
                continue

            if not block.is_text:
                continue

            key = self._build_key(block)

            if key not in self._fingerprints:

                fingerprint = Fingerprint(
                    text=block.text.strip(),
                    x0=block.x0,
                    y0=block.y0,
                    x1=block.x1,
                    y1=block.y1,
                )

                self._fingerprints[key] = fingerprint

            self._fingerprints[key].add_page(block.page)

        return list(self._fingerprints.values())

    def clear(self) -> None:
        """Reset the engine."""

        self._fingerprints.clear()

    @property
    def fingerprint_count(self) -> int:
        """Return number of fingerprints."""

        return len(self._fingerprints)