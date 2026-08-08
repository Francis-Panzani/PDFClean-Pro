"""
PDFClean Pro - Header detector.
"""

from __future__ import annotations
from email import header
from wsgiref import headers

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
    #: Maximum Y coordinate (PDF points) for a header.
    MAX_HEADER_Y = 100.0 # PDF points

    #
    # Nombre minimum d'occurrences.
    #
    #: Minimum number of occurrences to consider a repeated block.
    MIN_OCCURRENCES = 2  # Minimum repeated pages

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
            # Texte vide ignoré.
            #
            if not fingerprint.text.strip():
                continue

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



            header = Header(fingerprint)
            headers.append(header)

        return headers