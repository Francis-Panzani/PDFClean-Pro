"""
Tests for FooterDetector.
"""

from pdfclean.detector.fingerprint import Fingerprint
from pdfclean.detector.footer_detector import FooterDetector


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


def test_detect_footer() -> None:
    detector = FooterDetector()

    fp = make_fingerprint(
        text="- 15 -",
        y0=780,
        occurrences=5,
    )

    footers = detector.detect([fp])

    assert len(footers) == 1
    assert footers[0].text == "- 15 -"


def test_ignore_single_occurrence() -> None:
    detector = FooterDetector()

    fp = make_fingerprint(
        text="Unique",
        y0=780,
        occurrences=1,
    )

    footers = detector.detect([fp])

    assert footers == []


def test_ignore_header_position() -> None:
    detector = FooterDetector()

    fp = make_fingerprint(
        text="Header",
        y0=30,
        occurrences=5,
    )

    footers = detector.detect([fp])

    assert footers == []


def test_ignore_empty_text() -> None:
    detector = FooterDetector()

    fp = make_fingerprint(
        text="   ",
        y0=780,
        occurrences=5,
    )

    footers = detector.detect([fp])

    assert footers == []


def test_multiple_footers() -> None:
    detector = FooterDetector()

    fp1 = make_fingerprint(
        text="- 15 -",
        y0=780,
        occurrences=5,
    )

    fp2 = make_fingerprint(
        text="© ENI Editions",
        y0=760,
        occurrences=5,
    )

    footers = detector.detect([fp1, fp2])

    assert len(footers) == 2