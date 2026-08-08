"""
PDFClean Pro - Configuration.

Centralised application configuration.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class AppConfig:
    """
    Global application configuration.
    """

    application_name: str = "PDFClean Pro"
    version: str = "0.1.0"

    log_level: str = "INFO"

    output_suffix: str = "_clean"

    keep_backup: bool = False

    overwrite_output: bool = False

    debug: bool = False

    @property
    def output_extension(self) -> str:
        """
        Output PDF extension.
        """
        return ".pdf"

    def build_output_filename(self, input_file: Path) -> Path:
        """
        Build the output filename from an input PDF.

        Example
        -------
        cours.pdf
            ->
        cours_clean.pdf
        """

        return input_file.with_name(
            f"{input_file.stem}{self.output_suffix}{self.output_extension}"
        )


CONFIG = AppConfig()