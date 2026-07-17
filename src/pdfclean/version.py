"""
PDFClean Pro version information.

This module centralizes the application version.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Version:
    """Application version."""

    major: int
    minor: int
    patch: int

    @property
    def string(self) -> str:
        """Return the semantic version as a string."""
        return f"{self.major}.{self.minor}.{self.patch}"


VERSION = Version(
    major=0,
    minor=1,
    patch=0,
)