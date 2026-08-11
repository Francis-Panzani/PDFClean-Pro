"""
PDFClean Pro - Title detector.

Detects structural titles in ENI PDF documents.

The detector distinguishes:
- preliminary ENI author information,
- level 1 section titles,
- level 2 subsection titles.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from pdfclean.pdf.text_block import TextBlock


# ----------------------------------------------------------------------
# ENI reference
# ----------------------------------------------------------------------

ENI_REFERENCE_RE = re.compile(
    r"Réf\.\s*ENI\s*:\s*(?P<reference>[^|]+)"
    r"\s*\|\s*ISBN\s*:\s*(?P<isbn>[\dXx-]+)",
    re.IGNORECASE,
)


# ----------------------------------------------------------------------
# Detected title
# ----------------------------------------------------------------------


@dataclass(slots=True, frozen=True)
class DetectedTitle:
    """
    Represents a detected structural title.
    """

    block: TextBlock

    level: int

    lines_after: int

    new_page: bool

    @property
    def page(self) -> int:
        """Return the page number."""
        return self.block.page

    @property
    def text(self) -> str:
        """Return the title text."""
        return self.block.text.strip()

    @property
    def font_size(self) -> float:
        """Return the title font size."""
        return self.block.font_size


# ----------------------------------------------------------------------
# Detector
# ----------------------------------------------------------------------


class TitleDetector:
    """
    Detect structural titles in a PDF.

    The detector is intentionally adapted to the structure of
    ENI PDF books.
    """

    # --------------------------------------------------------------
    # Configuration
    # --------------------------------------------------------------

    LEVEL_1_MIN_SIZE = 20.0
    LEVEL_2_MIN_SIZE = 13.0

    # Number of lines required after a level 2 title
    # to keep it on the current page.
    LEVEL_2_MIN_LINES_AFTER = 5

    # Only the beginning of the document can contain the
    # ENI author/editorial block.
    ENI_PRELIMINARY_MAX_PAGE = 6

    def __init__(
        self,
        blocks: list[TextBlock],
    ) -> None:

        self.blocks = blocks

        self._preliminary_pages: set[int] = set()

        self._detect_eni_preliminary_pages()

    # ==============================================================
    # PUBLIC API
    # ==============================================================

    def detect(self) -> list[DetectedTitle]:
        """
        Detect structural titles.

        Returns
        -------
        list[DetectedTitle]
            Detected titles ordered by page and vertical position.
        """

        titles: list[DetectedTitle] = []

        ordered_blocks = sorted(
            self.blocks,
            key=lambda block: (
                block.page,
                block.y0,
            ),
        )

        for index, block in enumerate(
            ordered_blocks
        ):

            if not block.is_text:
                continue

            if block.is_empty:
                continue

            # ------------------------------------------------------
            # Ignore ENI preliminary information.
            # ------------------------------------------------------

            if self._is_preliminary_block(block):
                continue

            level = self._detect_level(block)

            if level is None:
                continue

            lines_after = self._count_lines_after(
                ordered_blocks,
                index,
            )

            new_page = self._must_start_new_page(
                level,
                lines_after,
            )

            titles.append(
                DetectedTitle(
                    block=block,
                    level=level,
                    lines_after=lines_after,
                    new_page=new_page,
                )
            )

        return titles

    # ==============================================================
    # ENI PRELIMINARY BLOCK
    # ==============================================================

    def _detect_eni_preliminary_pages(
        self,
    ) -> None:
        """
        Detect pages containing the ENI author/editorial block.

        The block is identified from:
        - "Auteur(s)"
        - followed somewhere by:
          "Réf. ENI : ... | ISBN : ..."

        No assumption is made about the ENI reference format.
        """

        preliminary_blocks = [
            block
            for block in self.blocks
            if block.is_text
            and block.page <= self.ENI_PRELIMINARY_MAX_PAGE
        ]

        preliminary_blocks.sort(
            key=lambda block: (
                block.page,
                block.y0,
            )
        )

        author_pages: set[int] = set()

        for index, block in enumerate(
            preliminary_blocks
        ):

            text = self._normalize(
                block.text
            )

            if text != "auteur(s)":
                continue

            author_page = block.page

            # Search forward for the ENI reference.
            for next_block in preliminary_blocks[
                index + 1 :
            ]:

                # Do not cross too many pages.
                if (
                    next_block.page
                    > author_page + 3
                ):
                    break

                match = ENI_REFERENCE_RE.search(
                    next_block.text
                )

                if match:

                    # The complete editorial block is
                    # considered preliminary.
                    for page in range(
                        author_page,
                        next_block.page + 1,
                    ):
                        author_pages.add(page)

                    break

        self._preliminary_pages = author_pages

    # --------------------------------------------------------------

    def _is_preliminary_block(
        self,
        block: TextBlock,
    ) -> bool:
        """
        Return True when a block belongs to the
        ENI preliminary author/editorial section.
        """

        return block.page in self._preliminary_pages

    # ==============================================================
    # TITLE LEVEL
    # ==============================================================

    def _detect_level(
        self,
        block: TextBlock,
    ) -> int | None:
        """
        Determine title level.

        Level 1:
            large structural title.

        Level 2:
            numbered subsection or medium title.
        """

        text = self._normalize(
            block.text
        )

        if not text:
            return None

        # ----------------------------------------------------------
        # Level 1
        # ----------------------------------------------------------

        if block.font_size >= self.LEVEL_1_MIN_SIZE:

            # A level 1 title should not be excessively long.
            if len(text) > 150:
                return None

            return 1

        # ----------------------------------------------------------
        # Level 2
        # ----------------------------------------------------------

        if block.font_size >= self.LEVEL_2_MIN_SIZE:

            # Numbered subsection:
            #
            # 1. Qu'est-ce qu'un SGBDR ?
            # 2. Mode de fonctionnement...
            #
            if re.match(
                r"^\d+[\.\)]\s+",
                text,
            ):
                return 2

            return 2

        return None

    # ==============================================================
    # LINES AFTER
    # ==============================================================

    def _count_lines_after(
        self,
        blocks: list[TextBlock],
        index: int,
    ) -> int:
        """
        Count text lines following the title on the same page.
        """

        title = blocks[index]

        count = 0

        for block in blocks[index + 1 :]:

            # Only the same page.
            if block.page != title.page:
                break

            # Ignore blocks above or overlapping the title.
            if block.y0 <= title.y1:
                continue

            if not block.is_text:
                continue

            if block.is_empty:
                continue

            # Prefer explicit line count.
            if block.line_count > 0:
                count += block.line_count
            else:
                count += 1

        return count

    # ==============================================================
    # NEW PAGE RULE
    # ==============================================================

    def _must_start_new_page(
        self,
        level: int,
        lines_after: int,
    ) -> bool:
        """
        Determine whether the title must start a new page.
        """

        # ----------------------------------------------------------
        # Level 1
        # ----------------------------------------------------------

        if level == 1:
            return True

        # ----------------------------------------------------------
        # Level 2
        #
        # Less than 5 lines after the title:
        # move to next page.
        #
        # 5 or more:
        # keep on current page.
        # ----------------------------------------------------------

        if level == 2:
            return (
                lines_after
                < self.LEVEL_2_MIN_LINES_AFTER
            )

        return False

    # ==============================================================
    # UTILITIES
    # ==============================================================

    @staticmethod
    def _normalize(
        text: str,
    ) -> str:
        """
        Normalize text for structural comparisons.
        """

        return " ".join(
            text
            .replace("\n", " ")
            .split()
        ).strip().lower()