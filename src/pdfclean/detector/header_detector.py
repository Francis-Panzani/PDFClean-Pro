"""
PDFClean Pro - Header detector.
"""

from __future__ import annotations

from pdfclean.detector.fingerprint import Fingerprint
from pdfclean.detector.header import Header


class HeaderDetector:
    """
    Detect repeated text blocks located in the upper part of pages.
    """

    #
    # Position maximale (en points PDF) pour considérer
    # qu'un bloc est un en-tête.
    #
    MAX_HEADER_Y = 100.0

    #
    # Nombre minimum d'occurrences.
    #
    MIN_OCCURRENCES = 2

    def detect(
        self,
        fingerprints: list[Fingerprint],
    ) -> list[Header]:
        """
        Detect document headers.

        Parameters
        ----------
        fingerprints:
            Fingerprints produced by FingerprintEngine.

        Returns
        -------
        list[Header]
        """

        headers: list[Header] = []

        for fingerprint in fingerprints:

            #
            # Doit apparaître plusieurs fois.
            #
            if fingerprint.occurrences < self.MIN_OCCURRENCES:
                continue

            #
            # Doit être situé dans la partie haute.
            #
            if fingerprint.y0 > self.MAX_HEADER_Y:
                continue

            #
            # Texte vide ignoré.
            #
            if not fingerprint.text.strip():
                continue

            headers.append(Header(fingerprint))

        return headers