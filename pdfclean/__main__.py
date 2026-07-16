import typer

app = typer.Typer(help="Remove unwanted headers and footers from PDFs")


@app.command()
def clean() -> None:
    """Clean headers and footers from a PDF file."""
    typer.echo("Cleaning PDF content")


if __name__ == "__main__":
    main = app
