"""
PDFClean Pro - Space optimization engine.

Compact excessive vertical whitespace while preserving text
as native PDF text.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import fitz
from pdfclean.validator.pdf_validator import PDFValidator

from pdfclean.pdf.document import PDFDocument
from pdfclean.pdf.extractor import TextExtractor
from pdfclean.pdf.text_block import TextBlock
from pdfclean.detector.title import TitleDetector


@dataclass(slots=True)
class TextItem:
    """
    Native text item extracted from a PDF.

    Text is stored with its visual information so it can be
    reinserted as real PDF text.
    """

    source_page: int

    x0: float
    y0: float
    x1: float
    y1: float

    text: str

    font: str
    size: float
    color: tuple[float, float, float]


@dataclass(slots=True)
class SpaceBand:
    """
    Non-overlapping vertical band extracted from a source page.
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
    Band placed on an output page.
    """

    source_page: int

    source_y0: float
    source_y1: float

    target_y0: float
    target_y1: float

    @property
    def height(self) -> float:
        return self.source_y1 - self.source_y0


@dataclass(slots=True)
class GraphicItem:
    """
    Native graphical object extracted from a source page.
    """

    source_page: int

    x0: float
    y0: float
    x1: float
    y1: float

    kind: str

    image_bytes: bytes | None = None
    image_ext: str | None = None

    drawing: dict | None = None

    @property
    def center_y(self) -> float:
        return (self.y0 + self.y1) / 2.0



class SpaceEngine:
    """
    Compact excessive vertical whitespace in a PDF.

    The source document is never modified.

    Unlike the previous implementation, text is not converted
    into images. Text is extracted and reinserted as native
    PDF text.
    """

    TOP_MARGIN = 48.0
    BOTTOM_MARGIN = 48.0

    BAND_MERGE_GAP = 12.0
    CONTENT_PADDING = 1.0
    BLOCK_SPACING = 0.0

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
        Compact the PDF and save the result.
        """

        if document.document is None:
            raise RuntimeError("PDF is not open.")

        source = document.document

        blocks = TextExtractor.extract(source)

        validator = PDFValidator()

        headers, footers, page_numbers = validator.validate(
            document
        )

       

        usable_blocks = [
            block
            for block in blocks
            if not self._is_in_excluded_region(
                block,
                headers,
                footers,
                page_numbers,
            )
        ]

        title_detector = TitleDetector(
            usable_blocks
        )

        titles = title_detector.detect()

        page_bands = self._build_page_bands(
            source,
            usable_blocks,
        )

        text_items = self._extract_text_items(
            source,
            headers,
            footers,
            page_numbers,
        )

        output_bands = self._build_output_flow(
            source,
            page_bands,
            titles,
        )

        self._write_output(
            source,
            output_bands,
            text_items,
            output_path,
        )

    # ============================================================
    # SOURCE BANDS
    # ============================================================

    def _build_page_bands(
        self,
        document: fitz.Document,
        blocks: list[TextBlock],
    ) -> list[list[SpaceBand]]:
        """
        Build meaningful content bands.
        """

        page_blocks: dict[int, list[TextBlock]] = {}

        for block in blocks:

            if not block.is_text:
                continue

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

            result.append(
                self._make_bands(
                    page_number,
                    page.rect.height,
                    blocks_on_page,
                )
            )

        return result

    def _make_bands(
        self,
        page_number: int,
        page_height: float,
        blocks: list[TextBlock],
    ) -> list[SpaceBand]:
        """
        Merge vertically close text blocks into content bands.
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

            if y1 > y0:
                intervals.append(
                    (y0, y1)
                )

        if not intervals:
            return []

        intervals.sort()

        merged: list[list[float]] = []

        for y0, y1 in intervals:

            if not merged:
                merged.append([y0, y1])
                continue

            previous = merged[-1]

            gap = y0 - previous[1]

            if gap <= self.BAND_MERGE_GAP:

                previous[1] = max(
                    previous[1],
                    y1,
                )

            else:

                merged.append(
                    [y0, y1]
                )

        return [
            SpaceBand(
                source_page=page_number,
                y0=y0,
                y1=y1,
            )
            for y0, y1 in merged
            if y1 > y0
        ]

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
        Calculate the new position of every content band.
        """

        if document.page_count == 0:
            return []

        page_height = document[0].rect.height

        output_pages: list[list[OutputBand]] = []
        current_page: list[OutputBand] = []

        cursor = self.TOP_MARGIN

        for source_page, bands in enumerate(pages):

            page_titles = [
                title
                for title in titles
                if title.page == source_page
            ]

            for band in bands:

                if band.height <= 0:
                    continue

                band_titles = [
                    title
                    for title in page_titles
                    if self._title_is_in_band(
                        title,
                        band,
                    )
                ]

                force_new_page = any(
                    self._title_requires_new_page(
                        title,
                        source_page,
                    )
                    for title in band_titles
                )

                if (
                    force_new_page
                    and current_page
                ):
                    output_pages.append(current_page)
                    current_page = []
                    cursor = self.TOP_MARGIN

                if (
                    cursor + band.height
                    > page_height - self.BOTTOM_MARGIN
                ):

                    if current_page:
                        output_pages.append(current_page)

                    current_page = []
                    cursor = self.TOP_MARGIN

                output_band = OutputBand(
                    source_page=band.source_page,
                    source_y0=band.y0,
                    source_y1=band.y1,
                    target_y0=cursor,
                    target_y1=cursor + band.height,
                )

                current_page.append(output_band)

                if abs(
                    band.y0 - cursor
                ) > 1.0:
                    self._blocks_moved += 1

                cursor = (
                    output_band.target_y1
                    + self.BLOCK_SPACING
                )

        if current_page:
            output_pages.append(current_page)

        return output_pages

    # ============================================================
    # TITLE HELPERS
    # ============================================================

    def _title_is_in_band(
        self,
        title,
        band: SpaceBand,
    ) -> bool:

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
        source_page: int,
    ) -> bool:
        """
        Decide whether a title starts a new page.

        The first major title of the document stays on page 1.

        Later level-1 titles start a new page.
        """

        level = getattr(
            title,
            "level",
            0,
        )

        if level != 1:
            return False

        # --------------------------------------------------------
        # SQL Server 2022 is the opening title of the document.
        # It must not create an empty first page.
        # --------------------------------------------------------

        if source_page == 0:
            return False

        return True

    # ============================================================
    # TEXT EXTRACTION
    # ============================================================

    def _extract_text_items(
        self,
        document: fitz.Document,
        headers,
        footers,
        page_numbers,
    ) -> list[TextItem]:
        """
        Extract native text spans while excluding headers,
        footers and page numbers.
        """

        items: list[TextItem] = []

        for page_number, page in enumerate(document):

            data = page.get_text("dict")

            for block in data.get("blocks", []):

                if block.get("type") != 0:
                    continue

                for line in block.get("lines", []):

                    for span in line.get("spans", []):

                        text = span.get(
                            "text",
                            "",
                        )

                        if not text:
                            continue

                        bbox = span.get("bbox")

                        if not bbox:
                            continue

                        x0, y0, x1, y1 = bbox

                        # ------------------------------------------------
                        # Ignore headers / footers / page numbers.
                        # ------------------------------------------------

                        span_rect = fitz.Rect(
                            x0,
                            y0,
                            x1,
                            y1,
                        )

                        if self._rect_in_excluded_region(
                            page_number,
                            span_rect,
                            headers,
                            footers,
                            page_numbers,
                        ):
                            continue

                        size = float(
                            span.get(
                                "size",
                                10.0,
                            )
                        )

                        font = str(
                            span.get(
                                "font",
                                "helv",
                            )
                        )

                        color = self._pdf_color_to_rgb(
                            span.get(
                                "color",
                                0,
                            )
                        )

                        items.append(
                            TextItem(
                                source_page=page_number,
                                x0=float(x0),
                                y0=float(y0),
                                x1=float(x1),
                                y1=float(y1),
                                text=text,
                                font=font,
                                size=size,
                                color=color,
                            )
                        )

        return items

    def _rect_in_excluded_region(
        self,
        page_number: int,
        rect: fitz.Rect,
        headers,
        footers,
        page_numbers,
    ) -> bool:
        """
        Return True when a rectangle belongs to a header,
        footer or page-number region.
        """

        for item in (
            *headers,
            *footers,
            *page_numbers,
        ):

            if page_number not in item.pages:
                continue

            fingerprint = getattr(
                item,
                "fingerprint",
                None,
            )

            if fingerprint is None:
                continue

            excluded_rect = fitz.Rect(
                fingerprint.x0,
                fingerprint.y0,
                fingerprint.x1,
                fingerprint.y1,
            )

            if rect.intersects(
                excluded_rect
            ):
                return True

        return False



    def _pdf_color_to_rgb(
        self,
        value,
    ) -> tuple[float, float, float]:
        """
        Convert PyMuPDF integer colour to RGB floats.
        """

        if isinstance(value, int):

            r = (
                (value >> 16) & 255
            ) / 255.0

            g = (
                (value >> 8) & 255
            ) / 255.0

            b = (
                value & 255
            ) / 255.0

            return (
                r,
                g,
                b,
            )

        return (
            0.0,
            0.0,
            0.0,
        )

    # ============================================================
    # OUTPUT
    # ============================================================

    def _write_output(
        self,
        source: fitz.Document,
        pages: list[list[OutputBand]],
        text_items: list[TextItem],
        output_path: str | Path,
    ) -> None:
        """
        Create the output PDF.

        Text is inserted as actual PDF text.
        No PNG conversion is performed.
        """

        output = fitz.open()

        try:

            items_by_page: dict[
                int,
                list[TextItem],
            ] = {}

            for item in text_items:

                items_by_page.setdefault(
                    item.source_page,
                    [],
                ).append(item)

            for page_bands in pages:

                target_page = output.new_page(
                    width=source[0].rect.width,
                    height=source[0].rect.height,
                )

                for band in page_bands:

                    items = items_by_page.get(
                        band.source_page,
                        [],
                    )

                    for item in items:

                        # Item must belong to the current band.
                        if (
                            item.y1 < band.source_y0
                            or item.y0 > band.source_y1
                        ):
                            continue

                        # ------------------------------------------------
                        # Calculate vertical translation.
                        # ------------------------------------------------

                        y_offset = (
                            band.target_y0
                            - band.source_y0
                        )

                        target_x = item.x0

                        target_y = (
                            item.y0
                            + y_offset
                        )

                        # ------------------------------------------------
                        # Try to reuse the original font.
                        #
                        # Standard fonts work directly. Embedded fonts may
                        # not always be reusable under their PDF name.
                        # ------------------------------------------------

                        fontname = self._safe_font(
                            item.font
                        )

                        try:

                            target_page.insert_text(
                                (
                                    target_x,
                                    target_y + item.size,
                                ),
                                item.text,
                                fontsize=item.size,
                                fontname=fontname,
                                color=item.color,
                                overlay=True,
                            )

                        except Exception:

                            # Safe fallback keeps the text editable.
                            target_page.insert_text(
                                (
                                    target_x,
                                    target_y + item.size,
                                ),
                                item.text,
                                fontsize=item.size,
                                fontname="helv",
                                color=item.color,
                                overlay=True,
                            )

            self._pages_created = len(output)

            output.save(
                output_path,
                garbage=4,
                deflate=True,
                clean=True,
            )

        finally:
            output.close()

    def _safe_font(
        self,
        font: str,
    ) -> str:
        """
        Map common PDF font names to built-in PyMuPDF fonts.

        Unknown embedded fonts fall back to Helvetica.
        """

        name = font.lower()

        if "times" in name:
            return "tiro"

        if (
            "courier" in name
            or "mono" in name
        ):
            return "cour"

        if (
            "helvetica" in name
            or "arial" in name
        ):
            return "helv"

        if "symbol" in name:
            return "symb"

        # Roboto and other embedded PDF fonts cannot reliably
        # be referenced only by their PDF font name.
        return "helv"

    def _is_in_excluded_region(
        self,
        block: TextBlock,
        headers,
        footers,
        page_numbers,
    ) -> bool:
        """
        Return True when a TextBlock belongs to a header,
        footer or page-number region.
        """

        block_rect = fitz.Rect(
            block.x0,
            block.y0,
            block.x1,
            block.y1,
        )

        return self._rect_in_excluded_region(
            block.page,
            block_rect,
            headers,
            footers,
            page_numbers,
        )