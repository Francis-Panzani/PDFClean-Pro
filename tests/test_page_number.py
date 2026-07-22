"""
Tests for PageNumber.
"""

from pdfclean.detector.fingerprint import Fingerprint
from pdfclean.detector.page_number import PageNumber


def create_fingerprint() -> Fingerprint:
    fp = Fingerprint(
        text="- 12 -",
        x0=500,
        y0=780,
        x1=550,
        y1=795,
    )

    fp.add_page(0)
    fp.add_page(1)
    fp.add_page(2)

    return fp


def test_page_number_text() -> None:
    page = PageNumber(create_fingerprint())

    assert page.text == "- 12 -"


def test_page_number_occurrences() -> None:
    page = PageNumber(create_fingerprint())

    assert page.occurrences == 3


def test_page_number_pages() -> None:
    page = PageNumber(create_fingerprint())

    assert page.pages == [0, 1, 2]


def test_page_number_coordinates() -> None:
    page = PageNumber(create_fingerprint())

    assert page.y0 == 780
    assert page.y1 == 795