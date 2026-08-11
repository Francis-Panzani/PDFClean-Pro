"""
PDFClean Pro - Space optimization engine.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import fitz

from pdfclean.pdf.document import PDFDocument
from pdfclean.pdf.extractor import TextExtractor
from pdfclean.pdf.text_block import TextBlock


# ================================================================
# DATA MODELS
# ================================================================


@dataclass(slots=True)
class SpaceBand:
    """
    Vertical content band belonging to one source page.
    """

    source_page: int
    y0: float
    y1: float

    @property
    def height(self) -> float:
        return self.y1 - self.y0


@dataclass(slots=True)
class OutputBand:
    """
    Content band placed on an output page.
    """

    source_page: int

    source_y0: float
    source_y1: float

    target_y0: float
    target_y1: float

    @property
    def height(self) -> float:
        return self.source_y1 - self.source_y0


# ================================================================
# ENGINE
# ================================================================


class SpaceEngine:
    """
    Compact excessive vertical whitespace in a PDF.

    The source PDF is never modified.

    Each source page is processed once.

    Content is moved vertically while preserving the complete
    horizontal page width.
    """

    TOP_MARGIN = 48.0
    BOTTOM_MARGIN = 48.0

    # Minimum empty vertical area considered removable.
    MIN_GAP = 25.0

    # Space inserted between two compacted content areas.
    BLOCK_SPACING = 4.0

    # A title of this size is considered a major section.
    MAJOR_TITLE_SIZE = 20.0

    # A smaller title is considered a subsection.
    SUBTITLE_SIZE = 14.0

    # A subsection can remain at the bottom if at least this many
    # following text lines remain with it.
    MIN_LINES_AFTER_SUBTITLE = 5

    def __init__(self) -> None:
        self._pages_created = 0
        self._blocks_moved = 0

    @property
    def pages_created(self) -> int:
        """Return the number of generated pages."""
        return self._pages_created

    @property
    def blocks_moved(self) -> int:
        """Return the number of moved content bands."""
        return self._blocks_moved

    # ============================================================
    # PUBLIC API
    # ============================================================

    def apply(
        self,
        document: PDFDocument,
        output_path: str | Path,
    ) -> None:
        """
        Compact the PDF and save the result.
        """

        if document.document is None:
            raise RuntimeError("PDF is not open.")

        source = document.document

        blocks = TextExtractor.extract(source)

        page_bands = self._build_page_bands(
            source,
            blocks,
        )

        output_pages = self._build_output_flow(
            source,
            page_bands,
            blocks,
        )

        self._write_output(
            source,
            output_pages,
            output_path,
        )

    # ============================================================
    # SOURCE ANALYSIS
    # ============================================================

    def _build_page_bands(
        self,
        document: fitz.Document,
        blocks: list[TextBlock],
    ) -> list[list[SpaceBand]]:
        """
        Build the occupied vertical bands of every page.

        A page is analysed only once.

        The bands represent the complete vertical extent of the
        page content, not individual text blocks.
        """

        page_blocks: dict[int, list[TextBlock]] = {}

        for block in blocks:

            if block.is_empty:
                continue

            if not block.is_text:
                continue

            if block.width <= 0:
                continue

            if block.height <= 0:
                continue

            page_blocks.setdefault(
                block.page,
                [],
            ).append(block)

        result: list[list[SpaceBand]] = []

        for page_number in range(document.page_count):

            page = document[page_number]

            blocks_on_page = page_blocks.get(
                page_number,
                [],
            )

            blocks_on_page.sort(
                key=lambda block: (
                    block.y0,
                    block.x0,
                )
            )

            bands = self._make_bands(
                page_number,
                page.rect.height,
                blocks_on_page,
            )

            result.append(bands)

        return result

    # ============================================================
    # BAND CREATION
    # ============================================================

    def _make_bands(
        self,
        page_number: int,
        page_height: float,
        blocks: list[TextBlock],
    ) -> list[SpaceBand]:
        """
        Merge overlapping text blocks into vertical bands.

        Only occupied areas are returned.
        """

        if not blocks:
            return []

        intervals: list[tuple[float, float]] = []

        for block in blocks:

            y0 = max(
                0.0,
                block.y0,
            )

            y1 = min(
                page_height,
                block.y1,
            )

            if y1 <= y0:
                continue

            intervals.append(
                (
                    y0,
                    y1,
                )
            )

        if not intervals:
            return []

        intervals.sort()

        merged: list[list[float]] = []

        for y0, y1 in intervals:

            if not merged:
                merged.append(
                    [
                        y0,
                        y1,
                    ]
                )
                continue

            previous = merged[-1]

            # Merge overlapping or touching intervals.
            if y0 <= previous[1] + 2.0:

                previous[1] = max(
                    previous[1],
                    y1,
                )

            else:

                merged.append(
                    [
                        y0,
                        y1,
                    ]
                )

        return [
            SpaceBand(
                source_page=page_number,
                y0=y0,
                y1=y1,
            )
            for y0, y1 in merged
        ]

    # ============================================================
    # TITLE DETECTION
    # ============================================================

    def _titles_on_page(
        self,
        blocks: list[TextBlock],
        page_number: int,
    ) -> list[TextBlock]:
        """
        Return probable title blocks for one page.

        No title names are hard-coded.

        Titles are detected from their typography.
        """

        page_blocks = [
            block
            for block in blocks
            if block.page == page_number
            and block.is_text
            and not block.is_empty
        ]

        if not page_blocks:
            return []

        # We need font information. TextBlock versions without
        # typography information simply cannot participate here.
        result: list[TextBlock] = []

        for block in page_blocks:

            font_size = getattr(
                block,
                "font_size",
                0.0,
            )

            if font_size < self.SUBTITLE_SIZE:
                continue

            text = block.text.strip()

            if not text:
                continue

            result.append(block)

        return result

    def _title_requires_new_page(
        self,
        title: TextBlock,
        blocks: list[TextBlock],
    ) -> bool:
        """
        Decide whether a title must start a new page.

        Major titles:
            always start a new page.

        Smaller section titles:
            start a new page only when fewer than five lines
            of content follow them.
        """

        size = getattr(
            title,
            "font_size",
            0.0,
        )

        # Major chapter / section.
        if size >= self.MAJOR_TITLE_SIZE:
            return True

        # Smaller subsection.
        following = [
            block
            for block in blocks
            if block.page == title.page
            and block.is_text
            and block.y0 > title.y1
            and not block.is_empty
        ]

        lines_after = 0

        for block in following:

            text = block.text.strip()

            if not text:
                continue

            lines_after += max(
                1,
                text.count("\n") + 1,
            )

            if lines_after >= self.MIN_LINES_AFTER_SUBTITLE:
                break

        return lines_after < self.MIN_LINES_AFTER_SUBTITLE

    # ============================================================
    # OUTPUT FLOW
    # ============================================================

    def _build_output_flow(
        self,
        document: fitz.Document,
        pages: list[list[SpaceBand]],
        blocks: list[TextBlock],
    ) -> list[list[OutputBand]]:
        """
        Build the compacted output.

        IMPORTANT:

        A source page is consumed once.

        We never append several independent copies of the same
        source page to the output flow.
        """

        if document.page_count == 0:
            return []

        page_width = document[0].rect.width
        page_height = document[0].rect.height

        usable_bottom = (
            page_height
            - self.BOTTOM_MARGIN
        )

        output_pages: list[list[OutputBand]] = []

        current_page: list[OutputBand] = []

        cursor = self.TOP_MARGIN

        for source_page, source_bands in enumerate(pages):

            if not source_bands:
                continue

            # ----------------------------------------------------
            # Detect major titles on this source page.
            # ----------------------------------------------------

            titles = self._titles_on_page(
                blocks,
                source_page,
            )

            force_page = any(
                self._title_requires_new_page(
                    title,
                    blocks,
                )
                for title in titles
            )

            # A title beginning the page does not need an
            # additional empty page.
            if force_page and current_page:

                self._flush_current_page(
                    current_page,
                    output_pages,
                )

                current_page = []

                cursor = self.TOP_MARGIN

            # ----------------------------------------------------
            # Process the complete source page once.
            # ----------------------------------------------------

            for band in source_bands:

                if band.height <= 0:
                    continue

                # Do not create a second copy of the source page.
                if (
                    cursor + band.height
                    > usable_bottom
                ):

                    if current_page:

                        self._flush_current_page(
                            current_page,
                            output_pages,
                        )

                    current_page = []

                    cursor = self.TOP_MARGIN

                target_y0 = cursor

                target_y1 = (
                    target_y0
                    + band.height
                )

                current_page.append(
                    OutputBand(
                        source_page=band.source_page,
                        source_y0=band.y0,
                        source_y1=band.y1,
                        target_y0=target_y0,
                        target_y1=target_y1,
                    )
                )

                if abs(
                    band.y0
                    - target_y0
                ) > 1.0:

                    self._blocks_moved += 1

                cursor = (
                    target_y1
                    + self.BLOCK_SPACING
                )

        if current_page:

            self._flush_current_page(
                current_page,
                output_pages,
            )

        return output_pages

    def _flush_current_page(
        self,
        current_page: list[OutputBand],
        output_pages: list[list[OutputBand]],
    ) -> None:
        """
        Add one output page to the result.

        A page is added exactly once.
        """

        if not current_page:
            return

        output_pages.append(
            list(current_page)
        )

    # ============================================================
    # OUTPUT
    # ============================================================

    def _write_output(
        self,
        source: fitz.Document,
        pages: list[list[OutputBand]],
        output_path: str | Path,
    ) -> None:
        """
        Write the compacted PDF.

        Each output band is copied exactly once.
        """

        output = fitz.open()

        try:

            for page_bands in pages:

                target_page = output.new_page(
                    width=source[0].rect.width,
                    height=source[0].rect.height,
                )

                for band in page_bands:

                    source_page = source[
                        band.source_page
                    ]

                    source_rect = fitz.Rect(
                        0,
                        band.source_y0,
                        source_page.rect.width,
                        band.source_y1,
                    )

                    target_rect = fitz.Rect(
                        0,
                        band.target_y0,
                        source_page.rect.width,
                        band.target_y1,
                    )

                    target_page.show_pdf_page(
                        target_rect,
                        source,
                        band.source_page,
                        clip=source_rect,
                        keep_proportion=False,
                        overlay=True,
                    )

            self._pages_created = len(output)

            output.save(
                output_path,
                garbage=4,
                deflate=True,
            )

        finally:

            output.close()