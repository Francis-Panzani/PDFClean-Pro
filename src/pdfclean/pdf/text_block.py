"""
PDFClean Pro - Text block model.

Represents a text block extracted from a PDF page.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class TextBlock:
    """
    Represents a text block extracted from a PDF.

    Attributes
    ----------
    page:
        Page number (0-based).
    block_no:
        Block index within the page.
    x0:
        Left coordinate.
    y0:
        Top coordinate.
    x1:
        Right coordinate.
    y1:
        Bottom coordinate.
    text:
        Extracted text.
    block_type:
        PyMuPDF block type.
        0 = text
        1 = image
    """

    page: int
    block_no: int

    x0: float
    y0: float
    x1: float
    y1: float

    text: str

    block_type: int

    @property
    def width(self) -> float:
        """Return block width."""
        return self.x1 - self.x0

    @property
    def height(self) -> float:
        """Return block height."""
        return self.y1 - self.y0

    @property
    def is_text(self) -> bool:
        """Return True if the block contains text."""
        return self.block_type == 0

    @property
    def is_image(self) -> bool:
        """Return True if the block represents an image."""
        return self.block_type == 1

    @property
    def is_empty(self) -> bool:
        """Return True if the text is empty or whitespace."""
        return self.text.strip() == ""

    def as_tuple(self) -> tuple:
        """
        Return a tuple representation.

        Useful for debugging and future comparisons.
        """
        return (
            self.page,
            self.block_no,
            self.x0,
            self.y0,
            self.x1,
            self.y1,
            self.text,
            self.block_type,
        )

    def __str__(self) -> str:
        preview = self.text.replace("\n", " ")

        if len(preview) > 60:
            preview = preview[:57] + "..."

        return (
            f"TextBlock(page={self.page}, "
            f"block={self.block_no}, "
            f"text='{preview}')"
        )