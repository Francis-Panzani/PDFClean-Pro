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
from pdfclean.detector.title import TitleDetector


@dataclass(slots=True)
class SpaceBand:
    """Non-overlapping vertical band extracted from a source page."""

    source_page: int
    y0: float
    y1: float

    @property
    def height(self) -> float:
        return self.y1 - self.y0


@dataclass(slots=True)
class OutputBand:
    """Band placed on an output page."""

    source_page: int
    source_y0: float
    source_y1: float
    target_y0: float
    target_y1: float

    @property
    def height(self) -> float:
        return self.source_y1 - self.source_y0


class SpaceEngine:
    """
    Compact excessive vertical whitespace in a PDF.

    The source PDF is never modified.

    Content is moved using non-overlapping vertical bands.
    """

    TOP_MARGIN = 48.0
    BOTTOM_MARGIN = 48.0

    # ------------------------------------------------------------
    # White-space rules
    # ------------------------------------------------------------

    # Petit espace : on le considère comme faisant partie
    # du même bloc visuel.
    BAND_MERGE_GAP = 12.0

    # Grand espace : peut devenir une vraie coupure.
    MIN_GAP = 25.0

    # Espace entre deux bandes réellement conservées.
    BLOCK_SPACING = 0.0

    # Une petite marge supplémentaire autour du contenu.
    CONTENT_PADDING = 1.0

    def __init__(self) -> None:
        self._pages_created = 0
        self._blocks_moved = 0

    @property
    def pages_created(self) -> int:
        return self._pages_created

    @property
    def blocks_moved(self) -> int:
        return self._blocks_moved

    # ============================================================
    # PUBLIC
    # ============================================================

    def apply(
        self,
        document: PDFDocument,
        output_path: str | Path,
    ) -> None:
        """
        Reflow the PDF and save the result.
        """

        if document.document is None:
            raise RuntimeError("PDF is not open.")

        source = document.document

        blocks = TextExtractor.extract(source)

        # --------------------------------------------------------
        # Detect titles once.
        # --------------------------------------------------------

        title_detector = TitleDetector(blocks)
        titles = title_detector.detect()

        page_bands = self._build_page_bands(
            source,
            blocks,
            titles,
        )

        output_bands = self._build_output_flow(
            source,
            page_bands,
            titles,
        )

        self._write_output(
            source,
            output_bands,
            output_path,
        )

    # ============================================================
    # SOURCE BANDS
    # ============================================================

    def _build_page_bands(
        self,
        document: fitz.Document,
        blocks: list[TextBlock],
        titles,
    ) -> list[list[SpaceBand]]:
        """
        Build compact vertical bands.

        Important:
        A page is never duplicated.
        """

        page_blocks: dict[int, list[TextBlock]] = {}

        for block in blocks:

            if block.is_empty:
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

            page_titles = [
                title
                for title in titles
                if title.page == page_number
            ]

            bands = self._make_bands(
                page_number,
                page.rect.height,
                blocks_on_page,
                page_titles,
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
        titles,
    ) -> list[SpaceBand]:
        """
        Convert blocks into a small number of meaningful
        vertical bands.

        The important difference with the previous version is
        that small gaps between text blocks do NOT generate
        independent PDF objects.
        """

        if not blocks:
            return []

        intervals: list[tuple[float, float]] = []

        for block in blocks:

            y0 = max(
                0.0,
                block.y0 - self.CONTENT_PADDING,
            )

            y1 = min(
                page_height,
                block.y1 + self.CONTENT_PADDING,
            )

            if y1 <= y0:
                continue

            intervals.append(
                (y0, y1)
            )

        if not intervals:
            return []

        intervals.sort()

        merged: list[list[float]] = []

        for y0, y1 in intervals:

            if not merged:
                merged.append(
                    [y0, y1]
                )
                continue

            previous = merged[-1]

            gap = y0 - previous[1]

            # ----------------------------------------------------
            # IMPORTANT
            #
            # Small gaps remain inside ONE band.
            # This avoids creating dozens of show_pdf_page()
            # objects for one paragraph/page.
            # ----------------------------------------------------

            if gap <= self.BAND_MERGE_GAP:

                previous[1] = max(
                    previous[1],
                    y1,
                )

            else:

                merged.append(
                    [y0, y1]
                )

        # --------------------------------------------------------
        # Now remove only genuinely unnecessary large spaces.
        #
        # A large gap is retained as a boundary between bands.
        # --------------------------------------------------------

        bands: list[SpaceBand] = []

        for y0, y1 in merged:

            if y1 <= y0:
                continue

            bands.append(
                SpaceBand(
                    source_page=page_number,
                    y0=y0,
                    y1=y1,
                )
            )

        return bands

    # ============================================================
    # OUTPUT FLOW
    # ============================================================

    def _build_output_flow(
        self,
        document: fitz.Document,
        pages: list[list[SpaceBand]],
        titles,
    ) -> list[list[OutputBand]]:
        """
        Move bands into a compact output flow.

        Titles representing major sections are forced onto a
        new page when required by TitleDetector.
        """

        if document.page_count == 0:
            return []

        page_width = document[0].rect.width
        page_height = document[0].rect.height

        output_pages: list[list[OutputBand]] = []

        current_page: list[OutputBand] = []

        cursor = self.TOP_MARGIN

        for source_page, bands in enumerate(pages):

            if not bands:
                continue

            page_titles = [
                title
                for title in titles
                if title.page == source_page
            ]

            for band_index, band in enumerate(bands):

                band_height = band.height

                if band_height <= 0:
                    continue

                # ------------------------------------------------
                # Determine whether a title occurs in this band.
                # ------------------------------------------------

                band_titles = [
                    title
                    for title in page_titles
                    if self._title_is_in_band(
                        title,
                        band,
                    )
                ]

                force_new_page = any(
                    self._title_requires_new_page(title)
                    for title in band_titles
                )

                # ------------------------------------------------
                # Major title -> new page.
                #
                # We don't do this for every subsection.
                # ------------------------------------------------

                if (
                    force_new_page
                    and current_page
                ):
                    output_pages.append(
                        current_page
                    )

                    current_page = []

                    cursor = self.TOP_MARGIN

                # ------------------------------------------------
                # Normal overflow.
                # ------------------------------------------------

                if (
                    cursor + band_height
                    > page_height - self.BOTTOM_MARGIN
                ):

                    if current_page:
                        output_pages.append(
                            current_page
                        )

                    current_page = []

                    cursor = self.TOP_MARGIN

                target_y0 = cursor

                target_y1 = (
                    cursor
                    + band_height
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

                if (
                    abs(
                        band.y0
                        - target_y0
                    )
                    > 1.0
                ):
                    self._blocks_moved += 1

                cursor = (
                    target_y1
                    + self.BLOCK_SPACING
                )

        if current_page:
            output_pages.append(
                current_page
            )

        return output_pages

    # ============================================================
    # TITLE HELPERS
    # ============================================================

    def _title_is_in_band(
        self,
        title,
        band: SpaceBand,
    ) -> bool:
        """
        Determine whether a title belongs to a source band.
        """

        try:
            title_y0 = title.block.y0
            title_y1 = title.block.y1
        except AttributeError:
            return False

        return (
            title_y1 >= band.y0
            and title_y0 <= band.y1
        )

    def _title_requires_new_page(
        self,
        title,
    ) -> bool:
        """
        Decide whether a detected title starts a new major section.

        Rules used for the current ENI document:

        - level 1 => new page
        - level 2 => normally stays on the current page
        - short subsection headings do not force a new page
        """

        try:
            level = title.level
        except AttributeError:
            return False

        return level == 1

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

        Each source band is rendered independently before being inserted
        into the output document.

        This avoids duplicated hidden PDF objects caused by repeated
        show_pdf_page(..., clip=...).
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

                    band_height = (
                        band.source_y1
                        - band.source_y0
                    )

                    if band_height <= 0:
                        continue

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

                    # ------------------------------------------------
                    # Render only the actual source band.
                    #
                    # A higher resolution is used to preserve the
                    # visual quality of text, images and diagrams.
                    # ------------------------------------------------

                    matrix = fitz.Matrix(
                        2.0,
                        2.0,
                    )

                    pixmap = source_page.get_pixmap(
                        matrix=matrix,
                        clip=source_rect,
                        alpha=False,
                    )

                    image_bytes = pixmap.tobytes(
                        "png"
                    )

                    # ------------------------------------------------
                    # Insert exactly one visible object.
                    # ------------------------------------------------

                    target_page.insert_image(
                        target_rect,
                        stream=image_bytes,
                        keep_proportion=False,
                        overlay=True,
                    )

                    if (
                        abs(
                            band.source_y0
                            - band.target_y0
                        )
                        > 1.0
                    ):
                        self._blocks_moved += 1

            self._pages_created = len(output)

            output.save(
                output_path,
                garbage=4,
                deflate=True,
                clean=True,
            )

        finally:
            output.close()