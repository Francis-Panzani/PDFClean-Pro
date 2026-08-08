"""
Tests for logging configuration.
"""

import logging

from pdfclean.logging_config import configure_logging
from pdfclean.logging_config import get_logger


def test_logger_creation() -> None:
    logger = configure_logging()

    assert isinstance(logger, logging.Logger)


def test_singleton_logger() -> None:
    logger1 = get_logger()
    logger2 = get_logger()

    assert logger1 is logger2


def test_logger_name() -> None:
    logger = get_logger()

    assert logger.name == "pdfclean"


def test_logger_level() -> None:
    logger = configure_logging("DEBUG")

    assert logger.level == logging.DEBUG