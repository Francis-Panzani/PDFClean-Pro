"""
PDFClean Pro - Command Line Interface.
"""

from __future__ import annotations

from pathlib import Path

import click
from rich.console import Console
from rich.panel import Panel

from pdfclean.version import VERSION
from pdfclean.pdf.document import PDFDocument
from pdfclean.validator.pdf_validator import PDFValidator
from pdfclean.cleaner.pdf_cleaner import PDFCleaner

from pdfclean.space.space_engine import SpaceEngine

from pdfclean.detector.title import TitleDetector

console = Console()

@click.group(context_settings={"help_option_names": ["-h", "--help"]})
@click.version_option(
    VERSION.string,
    "--version",
    "-V",
    prog_name="PDFClean Pro",
)
def app() -> None:
    """
    PDFClean Pro.

    Automatic removal of headers, footers and page numbers
    from ENI PDF books.
    """


@app.command()
@click.argument(
    "pdf_file",
    type=click.Path(
        exists=True,
        dir_okay=False,
        path_type=Path,
    ),
)
def analyse(pdf_file: Path) -> None:
    """
    Analyse a PDF document.
    """

    console.print()

    console.print(
        Panel.fit(
            "[bold cyan]PDFClean Pro[/bold cyan]\n"
            f"Version {VERSION.string}",
            title="Analysis",
        )
    )

    console.print(
        f"[green]Input file[/green] : {pdf_file}"
    )

    # --------------------------------------------------------------
    # Analyse headers / footers / page numbers
    # --------------------------------------------------------------

    with PDFDocument(pdf_file) as document:

        validator = PDFValidator()

        headers, footers, page_numbers = (
            validator.validate(document)
        )

    console.print()

    console.print(
        f"Headers      : {len(headers)}"
    )
    console.print(
        f"Footers      : {len(footers)}"
    )
    console.print(
        f"Page numbers : {len(page_numbers)}"
    )

    # --------------------------------------------------------------
    # V2 - Analyse des blocs et des titres
    # --------------------------------------------------------------

    with PDFDocument(pdf_file) as document:

        blocks = document.extract_text_blocks()

        title_detector = TitleDetector(blocks)

        titles = title_detector.detect()

        for title in titles:

            print(
                f"TITLE "
                f"page={title.page + 1} "
                f"level={title.level} "
                f"size={title.font_size:.1f} "
                f"lines_after={title.lines_after} "
                f"new_page={title.new_page} "
                f"text={title.text!r}"
            )

        # ----------------------------------------------------------
        # Debug des fonds
        # ----------------------------------------------------------

        for block in blocks:

            if block.has_background:

                print(
                    f"BACKGROUND "
                    f"page={block.page + 1} "
                    f"text={block.text!r} "
                    f"color={block.background_color} "
                    f"coverage={block.background_coverage:.2f} "
                    f"grey={block.is_grey_background}"
                )

## supprime les espaces blancs inutiles dans un PDF
@app.command()
@click.argument(
    "pdf_file",
    type=click.Path(
        exists=True,
        dir_okay=False,
        path_type=Path,
    ),
)
@click.option(
    "--output",
    type=click.Path(
        dir_okay=False,
        path_type=Path,
    ),
    default=None,
)
def space(
    pdf_file: Path,
    output: Path | None,
) -> None:
    """
    Reduce unnecessary white space in a PDF.
    """

    console.print()

    console.print(
        Panel.fit(
            "[bold cyan]PDFClean Pro[/bold cyan]\n"
            f"Version {VERSION.string}",
            title="Space",
        )
    )

    console.print(
        f"[green]Input file[/green] : {pdf_file}"
    )

    if output is None:
        output = pdf_file.with_stem(
            f"{pdf_file.stem}_space"
        )

    with PDFDocument(pdf_file) as document:

        engine = SpaceEngine()

        engine.apply(
            document,
            output,
        )

    console.print()

    console.print(
        f"[green]Output file[/green] : {output}"
    )

    console.print(
        f"[green]Pages created[/green] : "
        f"{engine.pages_created}"
    )

    console.print(
        f"[green]Blocks moved[/green] : "
        f"{engine.blocks_moved}"
    )

def clean(pdf_file: Path) -> None:
    """
    Clean a PDF document.
    """
    console.print(
        Panel.fit(
            "[bold cyan]PDFClean Pro[/bold cyan]\n"
            f"Version {VERSION.string}",
            title="Cleaning",
        )
    )

    console.print(f"[green]Input file[/green] : {pdf_file}")
    with PDFDocument(pdf_file) as document:

        validator = PDFValidator()

        headers, footers, page_numbers = validator.validate(document)

        #pour debug
        # debug = PDFDebug()

        # debug.draw_regions(
        #     document,
        #     headers,
        #     footers,
        #     page_numbers,
        #     pdf_file.with_stem(f"{pdf_file.stem}_debug"),
        # )

        # return
        cleaner = PDFCleaner()

        cleaner.build_regions(
            headers,
            footers,
            page_numbers,
        )

        cleaner.apply(document)

        output = pdf_file.with_stem(f"{pdf_file.stem}_clean")

        document.save_copy(output)

    console.print()
    console.print(f"[green]Output file[/green] : {output}")
    console.print(f"[green]Regions removed[/green] : {len(cleaner.regions)}")


@app.command(name="info")
def info_command() -> None:
    """
    Display application information.
    """

    console.print()

    console.print(
        Panel.fit(
            f"[bold]PDFClean Pro[/bold]\n"
            f"Version : {VERSION.string}\n"
            "Target : ENI PDF books",
            title="Information",
        )
    )

