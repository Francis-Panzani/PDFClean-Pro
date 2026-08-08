"""
Tests for configuration.
"""

from pathlib import Path

from pdfclean.config import CONFIG


def test_application_name() -> None:
    assert CONFIG.application_name == "PDFClean Pro"


def test_version() -> None:
    assert CONFIG.version == "0.1.0"


def test_output_filename() -> None:
    output = CONFIG.build_output_filename(Path("cours.pdf"))

    assert output.name == "cours_clean.pdf"


def test_output_extension() -> None:
    assert CONFIG.output_extension == ".pdf"