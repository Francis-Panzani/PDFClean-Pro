"""
PDFClean Pro - Logging configuration.
"""

from __future__ import annotations

import logging
from typing import Optional

from rich.logging import RichHandler


_LOGGER_NAME = "pdfclean"


def configure_logging(level: str = "INFO") -> logging.Logger:
    """
    Configure the application logger.

    Parameters
    ----------
    level:
        Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)

    Returns
    -------
    logging.Logger
        Configured logger instance.
    """
    
    logger = logging.getLogger(_LOGGER_NAME)
    #
    # Toujours mettre à jour le niveau demandé
    #
    logger.setLevel(level.upper())

    #
    # Les handlers ne sont créés qu'une seule fois
    #
    if logger.handlers:
        return logger

    handler = RichHandler(
        show_path=False,
        rich_tracebacks=True,
        markup=True,
    )

    formatter = logging.Formatter("%(message)s")

    handler.setFormatter(formatter)

    logger.addHandler(handler)

    logger.propagate = False

    return logger


_logger: Optional[logging.Logger] = None


def get_logger() -> logging.Logger:
    """
    Return the singleton logger.
    """

    global _logger

    if _logger is None:
        _logger = configure_logging()

    return _logger