"""
PDFClean Pro - Text extraction.
"""

from __future__ import annotations

from typing import List

import fitz

from pdfclean.pdf.text_block import TextBlock


class TextExtractor:
    """
    Extract text blocks from a PDF document.
    """

    @staticmethod
    def extract(
        document: fitz.Document,
    ) -> List[TextBlock]:

        blocks: list[TextBlock] = []

        for page_number, page in enumerate(document):

            # ----------------------------------------------------
            # Get graphical objects from the page.
            # ----------------------------------------------------

            drawings = page.get_drawings()

            page_blocks = page.get_text(
                "dict"
            ).get(
                "blocks",
                [],
            )

            for block_number, block in enumerate(
                page_blocks
            ):

                # ------------------------------------------------
                # Ignore non-text blocks.
                # ------------------------------------------------

                if block.get("type") != 0:
                    continue

                bbox = block.get("bbox")

                if not bbox or len(bbox) < 4:
                    continue

                x0 = float(bbox[0])
                y0 = float(bbox[1])
                x1 = float(bbox[2])
                y1 = float(bbox[3])

                lines = block.get(
                    "lines",
                    [],
                )

                text_parts: list[str] = []

                font_sizes: list[float] = []
                font_names: list[str] = []

                bold_count = 0
                span_count = 0

                for line in lines:

                    for span in line.get(
                        "spans",
                        [],
                    ):

                        span_text = str(
                            span.get(
                                "text",
                                "",
                            )
                        )

                        text_parts.append(
                            span_text
                        )

                        size = span.get(
                            "size"
                        )

                        if size is not None:
                            font_sizes.append(
                                float(size)
                            )

                        font = span.get(
                            "font",
                            "",
                        )

                        if font:
                            font_names.append(
                                str(font)
                            )

                        flags = int(
                            span.get(
                                "flags",
                                0,
                            )
                        )

                        # PyMuPDF bold flag.
                        if flags & 16:
                            bold_count += 1

                        span_count += 1

                text = "".join(
                    text_parts
                ).strip()

                if not text:
                    continue

                # ------------------------------------------------
                # Font information
                # ------------------------------------------------

                font_size = (
                    sum(font_sizes)
                    / len(font_sizes)
                    if font_sizes
                    else 0.0
                )

                font_name = (
                    font_names[0]
                    if font_names
                    else ""
                )

                is_bold = (
                    span_count > 0
                    and bold_count
                    >= span_count / 2
                )

                line_count = len(lines)

                # ------------------------------------------------
                # Background detection
                # ------------------------------------------------

                (
                    has_background,
                    background_color,
                    background_coverage,
                ) = TextExtractor._detect_background(
                    bbox,
                    drawings,
                )

                blocks.append(
                    TextBlock(
                        page=page_number,
                        block_no=block_number,
                        x0=x0,
                        y0=y0,
                        x1=x1,
                        y1=y1,
                        text=text,
                        block_type=0,
                        font_size=font_size,
                        font_name=font_name,
                        is_bold=is_bold,
                        line_count=line_count,
                        has_background=has_background,
                        background_color=background_color,
                        background_coverage=background_coverage,
                    )
                )

        return blocks

    # ============================================================
    # BACKGROUND DETECTION
    # ============================================================

    @staticmethod
    def _detect_background(
        bbox,
        drawings,
    ) -> tuple[
        bool,
        tuple[float, float, float] | None,
        float,
    ]:
        """
        Detect a filled drawing behind a text block.

        Returns:
            has_background
            background_color
            coverage ratio
        """

        block_rect = fitz.Rect(
            bbox
        )

        block_area = block_rect.get_area()

        if block_area <= 0:
            return False, None, 0.0

        best_coverage = 0.0
        best_color = None

        for drawing in drawings:

            fill = drawing.get(
                "fill"
            )

            if fill is None:
                continue

            rect = drawing.get(
                "rect"
            )

            if rect is None:
                continue

            drawing_rect = fitz.Rect(
                rect
            )

            intersection = (
                block_rect
                & drawing_rect
            )

            if intersection.is_empty:
                continue

            intersection_area = (
                intersection.get_area()
            )

            coverage = (
                intersection_area
                / block_area
            )

            if coverage > best_coverage:

                best_coverage = coverage

                best_color = (
                    float(fill[0]),
                    float(fill[1]),
                    float(fill[2]),
                )

        return (
            best_coverage >= 0.50,
            best_color,
            best_coverage,
        )