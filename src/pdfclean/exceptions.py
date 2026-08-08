"""
PDFClean Pro - Custom exceptions.
"""

from __future__ import annotations


class PDFCleanError(Exception):
    """
    Base exception for PDFClean Pro.

    All project-specific exceptions inherit from this class.
    """


class ConfigurationError(PDFCleanError):
    """
    Raised when the application configuration is invalid.
    """


class PDFError(PDFCleanError):
    """
    Base exception for PDF-related errors.
    """


class PDFOpenError(PDFError):
    """
    Raised when a PDF cannot be opened.
    """


class PDFSaveError(PDFError):
    """
    Raised when a PDF cannot be saved.
    """


class InvalidPDFError(PDFError):
    """
    Raised when the file is not a valid PDF.
    """


class DetectorError(PDFCleanError):
    """
    Raised when the detector fails.
    """


class CleanerError(PDFCleanError):
    """
    Raised when the cleaning process fails.
    """


class ValidationError(PDFCleanError):
    """
    Raised when the validation process fails.
    """