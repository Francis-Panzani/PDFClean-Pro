"""
Tests for PageNumberDetector.
"""

from pdfclean.detector.fingerprint import Fingerprint
from pdfclean.detector.page_number_detector import PageNumberDetector


def make_fingerprint(
    text: str,
    y0: float,
    occurrences: int,
) -> Fingerprint:

    fp = Fingerprint(
        text=text,
        x0=500,
        y0=y0,
        x1=550,
        y1=y0 + 15,
    )

    for page in range(occurrences):
        fp.add_page(page)

    return fp


def test_detect_dash_number() -> None:
    detector = PageNumberDetector()

    fp = make_fingerprint("- 12 -", 780, 5)

    numbers = detector.detect([fp])

    assert len(numbers) == 1


def test_detect_plain_number() -> None:
    detector = PageNumberDetector()

    fp = make_fingerprint("12", 780, 5)

    numbers = detector.detect([fp])

    assert len(numbers) == 1


def test_detect_page_keyword() -> None:
    detector = PageNumberDetector()

    fp = make_fingerprint("Page 12", 780, 5)

    numbers = detector.detect([fp])

    assert len(numbers) == 1


def test_ignore_normal_footer() -> None:
    detector = PageNumberDetector()

    fp = make_fingerprint(
        "© ENI Editions",
        780,
        5,
    )

    numbers = detector.detect([fp])

    assert numbers == []


def test_ignore_header() -> None:
    detector = PageNumberDetector()

    fp = make_fingerprint(
        "- 12 -",
        40,
        5,
    )

    numbers = detector.detect([fp])

    assert numbers == []


def test_ignore_single_occurrence() -> None:
    detector = PageNumberDetector()

    fp = make_fingerprint(
        "- 12 -",
        780,
        1,
    )

    numbers = detector.detect([fp])

    assert numbers == []