"""
PDFClean Pro - Header model.
"""

from __future__ import annotations

from dataclasses import dataclass

from pdfclean.detector.fingerprint import Fingerprint


@dataclass(slots=True, frozen=True)
class Header:
    """
    Represents a detected page header.
    """

    fingerprint: Fingerprint

    @property
    def text(self) -> str:
        """Header text."""
        return self.fingerprint.text

    @property
    def y0(self) -> float:
        """Top coordinate."""
        return self.fingerprint.y0

    @property
    def y1(self) -> float:
        """Bottom coordinate."""
        return self.fingerprint.y1

    @property
    def pages(self) -> list[int]:
        """Pages where the header appears."""
        return self.fingerprint.pages

    @property
    def occurrences(self) -> int:
        """Number of occurrences."""
        return self.fingerprint.occurrences

    def __str__(self) -> str:
        return (
            f"Header("
            f"occurrences={self.occurrences}, "
            f"text='{self.text}')"
        )