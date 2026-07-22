"""
PDFClean Pro - Fingerprint model.

Represents a repeated text block detected across a PDF document.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class Fingerprint:
    """
    Represents a repeated text block.

    Attributes
    ----------
    text:
        Text contained in the block.

    x0, y0, x1, y1:
        Average coordinates of the block.

    pages:
        Pages where the block appears.

    occurrences:
        Number of occurrences.
    """

    text: str

    x0: float
    y0: float
    x1: float
    y1: float

    pages: list[int] = field(default_factory=list)

    occurrences: int = 0

    @property
    def width(self) -> float:
        """Return block width."""
        return self.x1 - self.x0

    @property
    def height(self) -> float:
        """Return block height."""
        return self.y1 - self.y0

    def add_page(self, page: int) -> None:
        """
        Register an occurrence on a page.

        Duplicate page numbers are ignored.
        """
        if page not in self.pages:
            self.pages.append(page)
            self.pages.sort()

        self.occurrences = len(self.pages)

    @property
    def first_page(self) -> int | None:
        """
        Return the first page where the block appears.
        """
        if not self.pages:
            return None

        return self.pages[0]

    @property
    def last_page(self) -> int | None:
        """
        Return the last page where the block appears.
        """
        if not self.pages:
            return None

        return self.pages[-1]

    @property
    def page_ratio(self) -> float:
        """
        Placeholder.

        The real ratio will be computed by FingerprintEngine
        once the total page count is known.
        """
        return 0.0

    def __str__(self) -> str:
        preview = self.text.replace("\n", " ").strip()

        if len(preview) > 50:
            preview = preview[:47] + "..."

        return (
            f"Fingerprint("
            f"occurrences={self.occurrences}, "
            f"pages={self.pages}, "
            f"text='{preview}')"
        )