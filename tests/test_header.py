"""
Tests for Header.
"""

from pdfclean.detector.fingerprint import Fingerprint
from pdfclean.detector.header import Header


def create_fingerprint() -> Fingerprint:
    fp = Fingerprint(
        text="ENI - Windows Server",
        x0=10,
        y0=25,
        x1=200,
        y1=45,
    )

    fp.add_page(0)
    fp.add_page(1)
    fp.add_page(2)

    return fp


def test_header_text() -> None:
    header = Header(create_fingerprint())

    assert header.text == "ENI - Windows Server"


def test_header_occurrences() -> None:
    header = Header(create_fingerprint())

    assert header.occurrences == 3


def test_header_pages() -> None:
    header = Header(create_fingerprint())

    assert header.pages == [0, 1, 2]


def test_header_coordinates() -> None:
    header = Header(create_fingerprint())

    assert header.y0 == 25
    assert header.y1 == 45