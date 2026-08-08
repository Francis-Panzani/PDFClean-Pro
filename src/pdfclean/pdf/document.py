"""
PDF document abstraction.
"""

from __future__ import annotations

from pathlib import Path

import fitz

from pdfclean.exceptions import PDFOpenError
from pdfclean.exceptions import PDFSaveError

from pdfclean.pdf.extractor import TextExtractor
from pdfclean.pdf.text_block import TextBlock

class PDFDocument:
    """
    Wrapper around PyMuPDF.

    Central access point for PDF operations.
    """

    def __init__(self, pdf_path: str | Path) -> None:
        self._path = Path(pdf_path)

        self._document: fitz.Document | None = None

    @property
    def document(self) -> fitz.Document | None:
        """
        Return underlying PyMuPDF document.
        """
        return self._document

    @property
    def path(self) -> Path:
        """
        Return PDF path.
        """
        return self._path

    @property
    def is_open(self) -> bool:
        """
        Return True if document is open.
        """
        return self._document is not None

    @property
    def page_count(self) -> int:
        """
        Return page count.
        """
        if self._document is None:
            return 0

        return self._document.page_count

    @property
    def metadata(self) -> dict:
        """
        Return PDF metadata.
        """
        if self._document is None:
            return {}

        return self._document.metadata

    def open(self) -> None:
        """
        Open PDF document.
        """
        if self.is_open:
            return

        try:
            self._document = fitz.open(self._path)
        except Exception as exc:
            raise PDFOpenError(
                f"Unable to open PDF: {self._path}"
            ) from exc

    def close(self) -> None:
        """
        Close PDF document.
        """
        if self._document is None:
            return

        self._document.close()
        self._document = None
        
    def extract_text_blocks(self) -> list[TextBlock]:
        """
        Extract all text blocks from the document.

        Returns
        -------
        list[TextBlock]
            List of extracted text blocks.

        Raises
        ------
        PDFOpenError
            If the document is not open.
        """
        if self._document is None:
            raise PDFOpenError("Document is not open.")

        return TextExtractor.extract(self._document)
    
    def save_copy(self, output_path: str | Path) -> None:
        """
        Save a copy of the document.
        """
        if self._document is None:
            raise PDFSaveError(
                "Cannot save a closed document."
            )

        try:
            self._document.save(output_path)
        except Exception as exc:
            raise PDFSaveError(
                f"Unable to save PDF: {output_path}"
            ) from exc

    def __enter__(self) -> "PDFDocument":
        self.open()
        return self

    def __exit__(
        self,
        exc_type,
        exc_value,
        traceback,
    ) -> None:
        self.close()
      