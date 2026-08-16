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

    Spans keep their original horizontal positions.
    """

    source_page: int

    x0: float
    y0: float
    x1: float
    y1: float

    spans: list[TextItem]

    # Espaces horizontaux entre les spans successifs.
    gaps: list[float]



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

    def _extract_text_lines(
        self,
        document: fitz.Document,
        headers,
        footers,
        page_numbers,
    ) -> list[TextLine]:
        """
        Extract native PDF lines while preserving the original
        horizontal geometry.

        We explicitly detect spaces between spans so that the
        reconstructed text does not merge words such as:

            optimisationdu

        or:

            Profileret
        """

        lines: list[TextLine] = []

        for page_number, page in enumerate(document):

            data = page.get_text("dict")

            for block in data.get("blocks", []):

                if block.get("type") != 0:
                    continue

                for line in block.get("lines", []):

                    line_spans: list[TextItem] = []

                    for span in line.get("spans", []):

                        text = str(
                            span.get(
                                "text",
                                "",
                            )
                        )

                        if not text:
                            continue

                        bbox = span.get("bbox")

                        if not bbox:
                            continue

                        x0, y0, x1, y1 = map(
                            float,
                            bbox,
                        )

                        if x1 <= x0 or y1 <= y0:
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

                        color = self._pdf_color_to_rgb(
                            span.get(
                                "color",
                                0,
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
                    # Always process spans from left to right.
                    # ------------------------------------------------

                    line_spans.sort(
                        key=lambda span: (
                            span.x0,
                            span.y0,
                        )
                    )

                    # ------------------------------------------------
                    # Determine whether a span needs an explicit
                    # space before it.
                    #
                    # We use both:
                    #   1. the original text
                    #   2. the geometric gap between spans
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

                        # ------------------------------------------------
                        # Determine whether a real word space exists.
                        #
                        # We only infer a missing space when the characters
                        # around the gap are compatible with a word boundary.
                        # ------------------------------------------------

                        previous_text = previous.text.rstrip()
                        current_text = current.text.lstrip()

                        if not previous_text or not current_text:
                            continue

                        previous_last = previous_text[-1]
                        current_first = current_text[0]

                        # ------------------------------------------------
                        # Characters that cannot have a preceding space.
                        # ------------------------------------------------

                        NO_SPACE_BEFORE = {
                            ".",
                            ",",
                            ";",
                            ":",
                            "!",
                            "?",
                            "%",
                            ")",
                            "]",
                            "}",
                            "»",
                        }

                        # ------------------------------------------------
                        # Characters that cannot have a following space.
                        # ------------------------------------------------

                        NO_SPACE_AFTER = {
                            "(",
                            "[",
                            "{",
                            "«",
                        }

                        # ------------------------------------------------
                        # Apostrophe:
                        #
                        # "l'analyseur"
                        # "d'administration"
                        #
                        # must NEVER become:
                        #
                        # "l' analyseur"
                        # ------------------------------------------------

                        APOSTROPHES = {
                            "'",
                            "’",
                            "ʼ",
                            "′",
                        }

                        # ------------------------------------------------
                        # First respect explicit spaces present in the
                        # original extracted text.
                        # ------------------------------------------------

                        explicit_space = (
                            previous.text.endswith(" ")
                            or current.text.startswith(" ")
                        )

                        # ------------------------------------------------
                        # Never insert spaces around punctuation or
                        # apostrophes.
                        # ------------------------------------------------

                        punctuation_case = (
                            current_first in NO_SPACE_BEFORE
                            or previous_last in NO_SPACE_AFTER
                            or previous_last in APOSTROPHES
                            or current_first in APOSTROPHES
                        )

                        if punctuation_case:
                            current.has_space_before = explicit_space
                            continue

                        # ------------------------------------------------
                        # Infer a missing word space geometrically.
                        #
                        # Only do this when both sides look like normal
                        # word characters.
                        # ------------------------------------------------

                        previous_is_word = (
                            previous_last.isalnum()
                            or previous_last in {
                                "à",
                                "â",
                                "ä",
                                "ç",
                                "é",
                                "è",
                                "ê",
                                "ë",
                                "î",
                                "ï",
                                "ô",
                                "ö",
                                "ù",
                                "û",
                                "ü",
                                "ÿ",
                            }
                        )

                        current_is_word = (
                            current_first.isalnum()
                            or current_first in {
                                "à",
                                "â",
                                "ä",
                                "ç",
                                "é",
                                "è",
                                "ê",
                                "ë",
                                "î",
                                "ï",
                                "ô",
                                "ö",
                                "ù",
                                "û",
                                "ü",
                                "ÿ",
                            }
                        )

                        geometric_gap = (
                            current.x0
                            - previous.x1
                        )

                        geometric_space = (
                            previous_is_word
                            and current_is_word
                            and geometric_gap
                            >= max(
                                1.0,
                                current.size * 0.30,
                            )
                        )

                        if (
                            explicit_space
                            or geometric_space
                        ):
                            current.has_space_before = True


                    lines.append(
                        TextLine(
                            source_page=page_number,
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
                            gaps=[
                                max(
                                    0.0,
                                    line_spans[i + 1].x0
                                    - line_spans[i].x1,
                                )
                                for i in range(
                                    len(line_spans) - 1
                                )
                            ],
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
        Normalize PDF text characters and remove
        incorrect spaces around punctuation.
        """

        # --------------------------------------------------------
        # Normalize apostrophe-like characters.
        # --------------------------------------------------------

        replacements = {
            "\u2018": "'",   # ‘
            "\u2019": "'",   # ’
            "\u201B": "'",   # ‛
            "\u2032": "'",   # ′
            "\u00B4": "'",   # ´
            "\u0060": "'",   # `
        }

        for source, target in replacements.items():
            text = text.replace(
                source,
                target,
            )

        # --------------------------------------------------------
        # Remove spaces after apostrophes.
        #
        # l' analyseur -> l'analyseur
        # d' administration -> d'administration
        # --------------------------------------------------------

        text = re.sub(
            r"'\s+",
            "'",
            text,
        )

        # --------------------------------------------------------
        # Remove spaces before punctuation.
        #
        # performances , -> performances,
        # données .      -> données.
        # --------------------------------------------------------

        text = re.sub(
            r"\s+([,.;:!?%\)\]\}])",
            r"\1",
            text,
        )

        # --------------------------------------------------------
        # Remove spaces after opening punctuation.
        #
        # ( texte -> (texte
        # [ texte -> [texte
        # --------------------------------------------------------

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

        Text is inserted as native PDF text.

        Each source line is inserted once while keeping the
        original horizontal span positions.
        """

        output = fitz.open()

        try:

            for page_bands in pages:

                target_page = output.new_page(
                    width=source[0].rect.width,
                    height=source[0].rect.height,
                )

                for band in page_bands:

                    # ------------------------------------------------
                    # Vertical translation applied to this band.
                    # ------------------------------------------------

                    y_offset = (
                        band.target_y0
                        - band.source_y0
                    )

                    # ------------------------------------------------
                    # Process only lines belonging to this source page.
                    # ------------------------------------------------

                    for line in text_lines:

                        if line.source_page != band.source_page:
                            continue

                        if (
                            line.y1 < band.source_y0
                            or line.y0 > band.source_y1
                        ):
                            continue

                        y_offset = (
                            band.target_y0
                            - band.source_y0
                        )

                        target_baseline = (
                            line.y1
                            + y_offset
                        )

                        for index, span in enumerate(
                            line.spans
                        ):

                            text = span.text

                            # --------------------------------------------------------
                            # Preserve an explicit word separator.
                            # --------------------------------------------------------

                            if (
                                index > 0
                                and span.has_space_before
                                and not text.startswith(" ")
                            ):
                                text = " " + text

                            fontname = self._get_output_font(
                                source,
                                band.source_page,
                                span.font,
                                target_page,
                            )

                            text = self._normalize_pdf_text(
                                text
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

                                target_page.insert_text(
                                    (
                                        span.x0,
                                        target_baseline,
                                    ),
                                    text,
                                    fontsize=span.size,
                                    fontname=self._safe_font(
                                        span.font,
                                        span.bold,
                                        span.italic,
                                    ),
                                    color=span.color,
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

def _normalize_pdf_text(
    self,
    text: str,
) -> str:
    """
    Normalize PDF text characters and remove
    incorrect spaces around punctuation.
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

    # ------------------------------------------------
    # Never leave a space after an apostrophe.
    # ------------------------------------------------

    text = re.sub(
        r"(['’])\s+",
        r"\1",
        text,
    )

    # ------------------------------------------------
    # Never leave a space before punctuation.
    # ------------------------------------------------

    text = re.sub(
        r"\s+([,.;:!?%\)\]\}])",
        r"\1",
        text,
    )

    # ------------------------------------------------
    # No space immediately after opening punctuation.
    # ------------------------------------------------

    text = re.sub(
        r"([\(\[\{«])\s+",
        r"\1",
        text,
    )

    return text