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
from pdfclean.debug.pdf_debug import PDFDebug

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
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
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

    console.print(f"[green]Input file[/green] : {pdf_file}")
    with PDFDocument(pdf_file) as document:

        validator = PDFValidator()

        headers, footers, page_numbers = validator.validate(document)
        
    console.print()

    console.print(f"Headers      : {len(headers)}")
    console.print(f"Footers      : {len(footers)}")
    console.print(f"Page numbers : {len(page_numbers)}")


@app.command()
@click.argument(
    "pdf_file",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
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