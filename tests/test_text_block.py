"""
Tests for TextBlock.
"""

from pdfclean.pdf.text_block import TextBlock


def test_width() -> None:
    block = TextBlock(
        page=0,
        block_no=0,
        x0=10,
        y0=20,
        x1=110,
        y1=70,
        text="Hello",
        block_type=0,
    )

    assert block.width == 100


def test_height() -> None:
    block = TextBlock(
        page=0,
        block_no=0,
        x0=10,
        y0=20,
        x1=110,
        y1=70,
        text="Hello",
        block_type=0,
    )

    assert block.height == 50


def test_is_text() -> None:
    block = TextBlock(
        page=0,
        block_no=0,
        x0=0,
        y0=0,
        x1=10,
        y1=10,
        text="Hello",
        block_type=0,
    )

    assert block.is_text is True
    assert block.is_image is False


def test_is_image() -> None:
    block = TextBlock(
        page=0,
        block_no=0,
        x0=0,
        y0=0,
        x1=10,
        y1=10,
        text="",
        block_type=1,
    )

    assert block.is_image is True
    assert block.is_text is False


def test_empty_text() -> None:
    block = TextBlock(
        page=0,
        block_no=0,
        x0=0,
        y0=0,
        x1=10,
        y1=10,
        text="   \n",
        block_type=0,
    )

    assert block.is_empty is True