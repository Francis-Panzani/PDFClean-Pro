"""
Tests for Fingerprint.
"""

from pdfclean.detector.fingerprint import Fingerprint


def test_add_page() -> None:
    fp = Fingerprint(
        text="ENI",
        x0=0,
        y0=20,
        x1=100,
        y1=40,
    )

    fp.add_page(0)
    fp.add_page(1)
    fp.add_page(2)

    assert fp.occurrences == 3
    assert fp.pages == [0, 1, 2]


def test_duplicate_page() -> None:
    fp = Fingerprint(
        text="ENI",
        x0=0,
        y0=20,
        x1=100,
        y1=40,
    )

    fp.add_page(1)
    fp.add_page(1)

    assert fp.occurrences == 1
    assert fp.pages == [1]


def test_width_height() -> None:
    fp = Fingerprint(
        text="ENI",
        x0=10,
        y0=20,
        x1=110,
        y1=70,
    )

    assert fp.width == 100
    assert fp.height == 50


def test_first_last_page() -> None:
    fp = Fingerprint(
        text="ENI",
        x0=0,
        y0=0,
        x1=10,
        y1=10,
    )

    fp.add_page(3)
    fp.add_page(1)
    fp.add_page(2)

    assert fp.first_page == 1
    assert fp.last_page == 3