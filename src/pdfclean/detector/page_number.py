"""
PDFClean Pro - Page number model.
"""

from __future__ import annotations

from dataclasses import dataclass

from pdfclean.detector.fingerprint import Fingerprint


@dataclass(slots=True, frozen=True)
class PageNumber:
    """
    Represents a detected page number.
    """

    fingerprint: Fingerprint

    @property
    def text(self) -> str:
        return self.fingerprint.text

    @property
    def y0(self) -> float:
        return self.fingerprint.y0

    @property
    def y1(self) -> float:
        return self.fingerprint.y1

    @property
    def pages(self) -> list[int]:
        return self.fingerprint.pages

    @property
    def occurrences(self) -> int:
        return self.fingerprint.occurrences

    def __str__(self) -> str:
        return (
            f"PageNumber("
            f"occurrences={self.occurrences}, "
            f"text='{self.text}')"
        )