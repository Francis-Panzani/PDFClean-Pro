"""Command Line Interface for PDFClean Pro."""

from __future__ import annotations

import click
from rich.console import Console

console = Console()


@click.group()
@click.version_option(version="0.1.0", prog_name="PDFClean Pro")
def app() -> None:
    """PDFClean Pro - Intelligent PDF Cleaner."""
    pass


@app.command()
@click.argument("pdf", required=False)
def analyse(pdf: str | None) -> None:
    """Analyse un document PDF."""
    if pdf is None:
        console.print("[yellow]Aucun fichier fourni.[/yellow]")
        return

    console.print(f"[green]Analyse du fichier :[/green] {pdf}")


@app.command()
def version() -> None:
    """Affiche la version."""
    console.print("[bold cyan]PDFClean Pro v0.1.0[/bold cyan]")