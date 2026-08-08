"""
Tests for Footer.
"""

from pdfclean.detector.fingerprint import Fingerprint
from pdfclean.detector.footer import Footer


def create_fingerprint() -> Fingerprint:
    fp = Fingerprint(
        text="- 15 -",
        x0=500,
        y0=780,
        x1=550,
        y1=800,
    )

    fp.add_page(0)
    fp.add_page(1)
    fp.add_page(2)

    return fp


def test_footer_text() -> None:
    footer = Footer(create_fingerprint())

    assert footer.text == "- 15 -"


def test_footer_occurrences() -> None:
    footer = Footer(create_fingerprint())

    assert footer.occurrences == 3


def test_footer_pages() -> None:
    footer = Footer(create_fingerprint())

    assert footer.pages == [0, 1, 2]


def test_footer_coordinates() -> None:
    footer = Footer(create_fingerprint())

    assert footer.y0 == 780
    assert footer.y1 == 800