"""
Tests for HeaderDetector.
"""

from pdfclean.detector.fingerprint import Fingerprint
from pdfclean.detector.header_detector import HeaderDetector


def make_fingerprint(
    text: str,
    y0: float,
    occurrences: int,
) -> Fingerprint:

    fp = Fingerprint(
        text=text,
        x0=0,
        y0=y0,
        x1=200,
        y1=y0 + 20,
    )

    for page in range(occurrences):
        fp.add_page(page)

    return fp


def test_detect_header() -> None:
    detector = HeaderDetector()

    fp = make_fingerprint(
        text="ENI",
        y0=30,
        occurrences=5,
    )

    headers = detector.detect([fp])

    assert len(headers) == 1
    assert headers[0].text == "ENI"


def test_ignore_single_occurrence() -> None:
    detector = HeaderDetector()

    fp = make_fingerprint(
        text="Unique",
        y0=20,
        occurrences=1,
    )

    headers = detector.detect([fp])

    assert headers == []


def test_ignore_low_page() -> None:
    detector = HeaderDetector()

    fp = make_fingerprint(
        text="Footer",
        y0=750,
        occurrences=5,
    )

    headers = detector.detect([fp])

    assert headers == []


def test_ignore_empty_text() -> None:
    detector = HeaderDetector()

    fp = make_fingerprint(
        text="   ",
        y0=20,
        occurrences=5,
    )

    headers = detector.detect([fp])

    assert headers == []


def test_multiple_headers() -> None:
    detector = HeaderDetector()

    fp1 = make_fingerprint(
        text="ENI",
        y0=20,
        occurrences=5,
    )

    fp2 = make_fingerprint(
        text="Chapitre 4",
        y0=60,
        occurrences=5,
    )

    headers = detector.detect([fp1, fp2])

    assert len(headers) == 2