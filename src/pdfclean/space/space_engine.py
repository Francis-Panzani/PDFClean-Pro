"""
PDFClean Pro - Space optimization engine.

Compact excessive vertical whitespace while preserving text
as native PDF text.
"""

from __future__ import annotations
import re
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
    Native PDF text item extracted from a PDF.
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

    bold: bool = False
    italic: bool = False

    has_space_before: bool = False


@dataclass(slots=True)
class TextLine:
    """
    Native PDF text line.

    The line keeps the geometry of its original
    PDF text block.
    """

    source_page: int

    block_x0: float
    block_y0: float
    block_x1: float
    block_y1: float

    x0: float
    y0: float
    x1: float
    y1: float

    spans: list[TextItem]

    gaps: list[float]

@dataclass(slots=True)
class SpaceBand:
    """
    Non-overlapping vertical band extracted from a source page.
    """

    source_page: int

    # Identifiant du TextBlock source.
    # Utilisé principalement pour la page 1.
    block_rect: tuple[
    float,
    float,
    float,
    float,
] | None

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

    # Identifiant du TextBlock source.
    block_rect: tuple[
    float,
    float,
    float,
    float,
] | None

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

        self._font_cache: dict[
            str,
            tuple[str, bytes],
        ] = {}

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

        text_lines = self._extract_text_lines(
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
            text_lines,
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

        Page 1 is handled separately because the ENI introduction
        contains positioned text blocks that must keep their original
        reading order.

        Other pages keep the existing behaviour.
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

        for page_number in range(
            document.page_count
        ):

            page = document[page_number]

            blocks_on_page = page_blocks.get(
                page_number,
                [],
            )

            # ========================================================
            # PAGE 1
            #
            # Keep the original extraction order.
            # Do NOT sort by Y/X here.
            #
            # This is important for the ENI introduction page where
            # several text blocks are positioned independently.
            # ========================================================

            if page_number == 0:

                bands = self._make_page1_bands(
                    page_number,
                    page.rect.height,
                    blocks_on_page,
                )

                result.append(bands)
                continue

            # ========================================================
            # OTHER PAGES
            #
            # Existing behaviour remains unchanged.
            # ========================================================

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

    def _make_page1_bands(
        self,
        page_number: int,
        page_height: float,
        blocks: list[TextBlock],
    ) -> list[SpaceBand]:
        """
        Build bands for the ENI introduction page.

        The block extraction order is deliberately preserved.

        The page contains positioned presentation elements that should
        not be reordered globally by Y/X.
        """

        if not blocks:
            return []

        bands: list[SpaceBand] = []

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

           
            bands.append(
                SpaceBand(
                    source_page=page_number,
                    block_rect=(
                        block.x0,
                        block.y0,
                        block.x1,
                        block.y1,
                    ),
                    y0=y0,
                    y1=y1,
                )
            )

        return bands

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
                block_rect=None,
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

                # ----------------------------------------------------
                # Force a new page for a major title.
                # ----------------------------------------------------

                if (
                    force_new_page
                    and current_page
                ):
                    output_pages.append(
                        current_page
                    )

                    current_page = []
                    cursor = self.TOP_MARGIN

                # ----------------------------------------------------
                # Normal page overflow.
                # ----------------------------------------------------

                if (
                    cursor + band.height
                    > page_height - self.BOTTOM_MARGIN
                ):

                    if current_page:
                        output_pages.append(
                            current_page
                        )

                    current_page = []
                    cursor = self.TOP_MARGIN

                # ----------------------------------------------------
                # Create the output band AFTER all page-breaking
                # decisions have been made.
                # ----------------------------------------------------

                output_band = OutputBand(
                    source_page=band.source_page,
                    block_rect=band.block_rect,
                    source_y0=band.y0,
                    source_y1=band.y1,
                    target_y0=cursor,
                    target_y1=cursor + band.height,
                )

                current_page.append(
                    output_band
                )

                if abs(
                    band.y0 - cursor
                ) > 1.0:
                    self._blocks_moved += 1

                cursor = (
                    output_band.target_y1
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
    def _extract_text_lines(
        self,
        document: fitz.Document,
        headers,
        footers,
        page_numbers,
    ) -> list[TextLine]:
        """
        Extract native PDF text lines.

        Each TextLine keeps the geometry of its original
        PDF text block.

        IMPORTANT:
            We do not manufacture a block number.
            The source block rectangle is kept instead.
        """

        lines: list[TextLine] = []

        for page_number, page in enumerate(document):

            data = page.get_text("dict")

            for block in data.get(
                "blocks",
                [],
            ):

                if block.get("type") != 0:
                    continue

                block_bbox = block.get(
                    "bbox"
                )

                if not block_bbox:
                    continue

                (
                    block_x0,
                    block_y0,
                    block_x1,
                    block_y1,
                ) = map(
                    float,
                    block_bbox,
                )

                for line in block.get(
                    "lines",
                    [],
                ):

                    line_spans: list[TextItem] = []

                    for span in line.get(
                        "spans",
                        [],
                    ):

                        text = str(
                            span.get(
                                "text",
                                "",
                            )
                        )

                        if not text:
                            continue

                        bbox = span.get(
                            "bbox"
                        )

                        if not bbox:
                            continue

                        x0, y0, x1, y1 = map(
                            float,
                            bbox,
                        )

                        if (
                            x1 <= x0
                            or y1 <= y0
                        ):
                            continue

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

                        if size <= 0:
                            size = 10.0

                        font = str(
                            span.get(
                                "font",
                                "helv",
                            )
                        )

                        flags = int(
                            span.get(
                                "flags",
                                0,
                            )
                        )

                        bold = bool(
                            flags & 16
                        )

                        italic = bool(
                            flags & 2
                        )

                        color = (
                            self._pdf_color_to_rgb(
                                span.get(
                                    "color",
                                    0,
                                )
                            )
                        )

                        line_spans.append(
                            TextItem(
                                source_page=page_number,
                                x0=x0,
                                y0=y0,
                                x1=x1,
                                y1=y1,
                                text=text,
                                font=font,
                                size=size,
                                color=color,
                                bold=bold,
                                italic=italic,
                            )
                        )

                    if not line_spans:
                        continue

                    # ------------------------------------------------
                    # Keep spans in their original left-to-right order.
                    # ------------------------------------------------

                    line_spans.sort(
                        key=lambda span: (
                            span.x0,
                            span.y0,
                        )
                    )

                    # ------------------------------------------------
                    # Detect logical spaces.
                    #
                    # IMPORTANT:
                    # Never modify span.text here.
                    # ------------------------------------------------

                    for index in range(
                        1,
                        len(line_spans),
                    ):

                        previous = line_spans[
                            index - 1
                        ]

                        current = line_spans[
                            index
                        ]

                        previous_text = (
                            previous.text.rstrip()
                        )

                        current_text = (
                            current.text.lstrip()
                        )

                        if (
                            not previous_text
                            or not current_text
                        ):
                            continue

                        previous_last = (
                            previous_text[-1]
                        )

                        current_first = (
                            current_text[0]
                        )

                        geometric_gap = (
                            current.x0
                            - previous.x1
                        )

                        no_space_before = {
                            ".",
                            ",",
                            ";",
                            "%",
                            ")",
                            "]",
                            "}",
                            "»",
                        }

                        no_space_after = {
                            "(",
                            "[",
                            "{",
                            "«",
                        }

                        apostrophes = {
                            "'",
                            "’",
                            "ʼ",
                            "′",
                        }

                        french_space_before = {
                            ":",
                            "?",
                            "!",
                        }

                        explicit_space = (
                            previous.text.endswith(
                                " "
                            )
                            or current.text.startswith(
                                " "
                            )
                        )

                        # ------------------------------------------------
                        # Apostrophe.
                        # ------------------------------------------------

                        if (
                            previous_last
                            in apostrophes
                            or current_first
                            in apostrophes
                        ):
                            current.has_space_before = (
                                explicit_space
                            )
                            continue

                        # ------------------------------------------------
                        # Punctuation without preceding space.
                        # ------------------------------------------------

                        if (
                            current_first
                            in no_space_before
                        ):
                            current.has_space_before = (
                                explicit_space
                            )
                            continue

                        # ------------------------------------------------
                        # Opening punctuation.
                        # ------------------------------------------------

                        if (
                            previous_last
                            in no_space_after
                        ):
                            current.has_space_before = (
                                explicit_space
                            )
                            continue

                        # ------------------------------------------------
                        # French punctuation.
                        # ------------------------------------------------

                        if (
                            current_first
                            in french_space_before
                        ):
                            current.has_space_before = True
                            continue

                        # ------------------------------------------------
                        # Normal word separation.
                        # ------------------------------------------------

                        previous_is_word = (
                            previous_last.isalnum()
                        )

                        current_is_word = (
                            current_first.isalnum()
                        )

                        if geometric_gap < 0:
                            current.has_space_before = False
                            continue

                        geometric_space = (
                            previous_is_word
                            and current_is_word
                            and geometric_gap >= 0.5
                        )

                        current.has_space_before = (
                            explicit_space
                            or geometric_space
                        )

                    # ------------------------------------------------
                    # Preserve geometric gaps.
                    # ------------------------------------------------

                    gaps = [
                        max(
                            0.0,
                            line_spans[i + 1].x0
                            - line_spans[i].x1,
                        )
                        for i in range(
                            len(line_spans) - 1
                        )
                    ]

                    lines.append(
                        TextLine(
                            source_page=page_number,

                            block_x0=block_x0,
                            block_y0=block_y0,
                            block_x1=block_x1,
                            block_y1=block_y1,

                            x0=min(
                                span.x0
                                for span in line_spans
                            ),
                            y0=min(
                                span.y0
                                for span in line_spans
                            ),
                            x1=max(
                                span.x1
                                for span in line_spans
                            ),
                            y1=max(
                                span.y1
                                for span in line_spans
                            ),

                            spans=line_spans,
                            gaps=gaps,
                        )
                    )

        return lines


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

    def _get_output_font(
        self,
        source: fitz.Document,
        source_page_number: int,
        source_font_name: str,
        target_page: fitz.Page,
    ) -> str:
        """
        Extract the real embedded font from the source PDF and install
        it once on the target page.

        Returns the font name to use with insert_text().
        """

        cache_key = (
            source_font_name,
        )

        # --------------------------------------------------------
        # Already installed for this source font.
        # --------------------------------------------------------

        cached = self._font_cache.get(
            cache_key
        )

        if cached is not None:

            output_font_name, _ = cached

            return output_font_name

        source_page = source[
            source_page_number
        ]

        # --------------------------------------------------------
        # Find the PDF font resource corresponding to the span.
        # --------------------------------------------------------

        source_fonts = source_page.get_fonts(
            full=True
        )

        matched_xref: int | None = None

        for font_info in source_fonts:

            if len(font_info) < 4:
                continue

            xref = int(
                font_info[0]
            )

            basefont = str(
                font_info[3]
            )

            # PyMuPDF may expose prefixes such as:
            # ABCDEF+Roboto-Regular
            #
            # Compare both the complete name and the suffix.
            if (
                basefont == source_font_name
                or basefont.endswith(
                    "+" + source_font_name
                )
            ):
                matched_xref = xref
                break

        if matched_xref is None:
            # Some PDFs use a slightly different name in the font
            # resource than in the text span. Try a normalized match.
            wanted = (
                source_font_name
                .replace(
                    "-Identity-H",
                    "",
                )
                .lower()
            )

            for font_info in source_fonts:

                if len(font_info) < 4:
                    continue

                xref = int(
                    font_info[0]
                )

                basefont = str(
                    font_info[3]
                )

                normalized = (
                    basefont
                    .replace(
                        "-Identity-H",
                        "",
                    )
                    .lower()
                )

                if (
                    wanted in normalized
                    or normalized in wanted
                ):
                    matched_xref = xref
                    break

        # --------------------------------------------------------
        # No matching embedded font.
        # --------------------------------------------------------

        if matched_xref is None:
            return self._safe_font(
                source_font_name,
                False,
                False,
            )

        # --------------------------------------------------------
        # Extract the actual font bytes.
        # --------------------------------------------------------

        try:

            font_info = source.extract_font(
                matched_xref
            )

            if not font_info:
                raise ValueError(
                    "Empty extracted font."
                )

            # PyMuPDF returns:
            #
            # (xref, ext, type, name, content)
            #
            # The fifth element is the actual font data.
            font_buffer = font_info[4]

            if not font_buffer:
                raise ValueError(
                    "Font has no embedded data."
                )

        except Exception:
            return self._safe_font(
                source_font_name,
                False,
                False,
            )

        # --------------------------------------------------------
        # Create a unique output font name.
        # --------------------------------------------------------

        safe_name = (
            source_font_name
            .replace(
                "-",
                "_",
            )
            .replace(
                "+",
                "_",
            )
            .replace(
                " ",
                "_",
            )
            .replace(
                "/",
                "_",
            )
            .replace(
                "\\",
                "_",
            )
        )

        output_font_name = (
            f"PDFC_{source_page_number}_"
            f"{safe_name}"
        )

        # Avoid names that are too long or contain problematic chars.
        output_font_name = (
            output_font_name[:60]
        )

        # --------------------------------------------------------
        # Install the real font in the output page.
        # --------------------------------------------------------

        try:

            target_page.insert_font(
                fontname=output_font_name,
                fontbuffer=font_buffer,
                set_simple=False,
            )

        except Exception:

            return self._safe_font(
                source_font_name,
                False,
                False,
            )

        self._font_cache[
            cache_key
        ] = (
            output_font_name,
            font_buffer,
        )

        return output_font_name

    def _normalize_pdf_text(
        self,
        text: str,
    ) -> str:
        """
        Normalize PDF text while preserving French punctuation.
        """

        replacements = {
            "\u2018": "'",
            "\u2019": "'",
            "\u201B": "'",
            "\u2032": "'",
            "\u00B4": "'",
            "\u0060": "'",
        }

        for source, target in replacements.items():
            text = text.replace(
                source,
                target,
            )

        # No space after apostrophe.
        text = re.sub(
            r"'\s+",
            "'",
            text,
        )

        # No space before comma, period, semicolon or percent.
        text = re.sub(
            r"\s+([,.;%])",
            r"\1",
            text,
        )

        # No space before closing punctuation.
        text = re.sub(
            r"\s+([\)\]\}»])",
            r"\1",
            text,
        )

        # No space after opening punctuation.
        text = re.sub(
            r"([\(\[\{«])\s+",
            r"\1",
            text,
        )

        return text
    
    def _write_output(
        self,
        source: fitz.Document,
        pages: list[list[OutputBand]],
        text_lines: list[TextLine],
        output_path: str | Path,
    ) -> None:
        """
        Create the output PDF.

        Text remains native PDF text.

        Each source line is written once for its matching
        source-page band.

        Page 1 uses the original source block rectangle
        to associate a line with its source block.
        """

        output = fitz.open()

        try:

            for page_bands in pages:

                target_page = output.new_page(
                    width=source[0].rect.width,
                    height=source[0].rect.height,
                )

                for band in page_bands:

                    if band.source_page == 0:

                        if band.block_rect is None:
                            continue

                        bx0, by0, bx1, by1 = (
                            band.block_rect
                        )

                    else:

                        bx0 = by0 = bx1 = by1 = 0.0

                    y_offset = (
                        band.target_y0
                        - band.source_y0
                    )

                    for line in text_lines:

                        # ------------------------------------------------
                        # Source page must match.
                        # ------------------------------------------------

                        if (
                            line.source_page
                            != band.source_page
                        ):
                            continue

                        # =================================================
                        # PAGE 1
                        #
                        # Associate the line with its original block
                        # using the stored block rectangle.
                        # =================================================

                        if band.source_page == 0:

                            if not (
                                abs(line.block_x0 - bx0) <= 0.5
                                and
                                abs(line.block_y0 - by0) <= 0.5
                                and
                                abs(line.block_x1 - bx1) <= 0.5
                                and
                                abs(line.block_y1 - by1) <= 0.5
                            ):
                                continue

                        # =================================================
                        # OTHER PAGES
                        # =================================================

                        else:

                            line_center_y = (
                                line.y0
                                + line.y1
                            ) / 2.0

                            if not (
                                band.source_y0
                                <= line_center_y
                                < band.source_y1
                            ):
                                continue

                        # ------------------------------------------------
                        # Vertical translation.
                        # ------------------------------------------------

                        target_baseline = (
                            line.y1
                            + y_offset
                        )

                        # =================================================
                        # INSERT SPANS
                        # =================================================

                        for span in line.spans:

                            text = (
                                self._normalize_pdf_text(
                                    span.text
                                )
                            )

                            fontname = (
                                self._get_output_font(
                                    source,
                                    line.source_page,
                                    span.font,
                                    target_page,
                                )
                            )

                            try:

                                target_page.insert_text(
                                    (
                                        span.x0,
                                        target_baseline,
                                    ),
                                    text,
                                    fontsize=span.size,
                                    fontname=fontname,
                                    color=span.color,
                                    overlay=True,
                                )

                            except Exception:

                                fallback_font = (
                                    self._safe_font(
                                        span.font,
                                        span.bold,
                                        span.italic,
                                    )
                                )

                                target_page.insert_text(
                                    (
                                        span.x0,
                                        target_baseline,
                                    ),
                                    text,
                                    fontsize=span.size,
                                    fontname=fallback_font,
                                    color=span.color,
                                    overlay=True,
                                )

            self._pages_created = len(
                output
            )

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
        bold: bool = False,
        italic: bool = False,
    ) -> str:
        """
        Select a built-in PDF font matching the detected style.

        The original PDF may use embedded fonts such as Roboto.
        In that case we use the closest built-in PDF font while
        preserving bold and italic when possible.
        """

        name = font.lower()

        # ------------------------------------------------------------
        # Courier / monospace
        # ------------------------------------------------------------

        if (
            "courier" in name
            or "mono" in name
            or "consolas" in name
        ):
            if bold and italic:
                return "cobo"

            if bold:
                return "cobo"

            if italic:
                return "coit"

            return "cour"

        # ------------------------------------------------------------
        # Times / serif
        # ------------------------------------------------------------

        if (
            "times" in name
            or "serif" in name
            or "georgia" in name
        ):
            if bold and italic:
                return "tibi"

            if bold:
                return "tibo"

            if italic:
                return "tiit"

            return "tiro"

        # ------------------------------------------------------------
        # Symbol
        # ------------------------------------------------------------

        if "symbol" in name:
            return "symb"

        # ------------------------------------------------------------
        # Sans serif
        #
        # Roboto, Arial, Calibri, Helvetica, etc.
        # ------------------------------------------------------------

        if bold and italic:
            return "hebi"

        if bold:
            return "hebo"

        if italic:
            return "heit"

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
