"""
PDFClean Pro - Text block model.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class TextBlock:
    """
    Represents a text block extracted from a PDF page.
    """

    page: int
    block_no: int

    x0: float
    y0: float
    x1: float
    y1: float

    text: str

    block_type: int

    font_size: float = 0.0
    font_name: str = ""
    is_bold: bool = False

    line_count: int = 0

    # ------------------------------------------------------------
    # Graphic information
    # ------------------------------------------------------------

    has_background: bool = False

    background_color: tuple[
        float,
        float,
        float,
    ] | None = None

    background_coverage: float = 0.0

    @property
    def width(self) -> float:
        """Return block width."""
        return self.x1 - self.x0

    @property
    def height(self) -> float:
        """Return block height."""
        return self.y1 - self.y0

    @property
    def area(self) -> float:
        """Return block area."""
        return self.width * self.height

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
        """Return True if the text is empty."""
        return self.text.strip() == ""


    @property
    def is_grey_background(self) -> bool:
        """
        Return True when the block is covered by a genuine
        grey background.

        White is explicitly excluded.
        """

        if not self.has_background:
            return False

        if self.background_color is None:
            return False

        r, g, b = self.background_color

        # --------------------------------------------------------
        # Ignore white backgrounds.
        # --------------------------------------------------------

        if (
            r >= 0.95
            and g >= 0.95
            and b >= 0.95
        ):
            return False

        # --------------------------------------------------------
        # Grey means RGB components are close together.
        # --------------------------------------------------------

        grey_distance = (
            max(r, g, b)
            - min(r, g, b)
        )

        return (
            grey_distance <= 0.08
            and self.background_coverage >= 0.50
        )

    def as_tuple(self) -> tuple:
        """Return tuple representation."""

        return (
            self.page,
            self.block_no,
            self.x0,
            self.y0,
            self.x1,
            self.y1,
            self.text,
            self.block_type,
            self.font_size,
            self.font_name,
            self.is_bold,
            self.line_count,
            self.has_background,
            self.background_color,
            self.background_coverage,
        )

    def __str__(self) -> str:
        preview = self.text.replace(
            "\n",
            " ",
        )

        if len(preview) > 60:
            preview = preview[:57] + "..."

        return (
            f"TextBlock("
            f"page={self.page}, "
            f"block={self.block_no}, "
            f"size={self.font_size:.1f}, "
            f"background={self.has_background}, "
            f"text='{preview}')"
        )