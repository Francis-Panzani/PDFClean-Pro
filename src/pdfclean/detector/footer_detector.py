"""
PDFClean Pro - Footer detector.
"""

from __future__ import annotations

from pdfclean.detector.fingerprint import Fingerprint
from pdfclean.detector.footer import Footer


class FooterDetector:
    """
    Detect repeated text blocks located in the lower part of pages.
    """

    #
    # Position minimale (en points PDF) pour considérer
    # qu'un bloc est un pied de page.
    #
    MIN_FOOTER_Y = 700.0

    #
    # Nombre minimum d'occurrences.
    #
    MIN_OCCURRENCES = 2

    def detect(
        self,
        fingerprints: list[Fingerprint],
    ) -> list[Footer]:
        """
        Detect document footers.

        Parameters
        ----------
        fingerprints:
            Fingerprints produced by FingerprintEngine.

        Returns
        -------
        list[Footer]
        """

        footers: list[Footer] = []

        for fingerprint in fingerprints:

            #
            # Doit apparaître plusieurs fois.
            #
            if fingerprint.occurrences < self.MIN_OCCURRENCES:
                continue

            #
            # Doit être situé dans la partie basse.
            #
            if fingerprint.y0 < self.MIN_FOOTER_Y:
                continue

            #
            # Texte vide ignoré.
            #
            if not fingerprint.text.strip():
                continue

            footers.append(Footer(fingerprint))

        return footers