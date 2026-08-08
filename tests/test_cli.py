from click.testing import CliRunner

from pdfclean.cli import app


def test_help() -> None:
    runner = CliRunner()

    result = runner.invoke(app, ["--help"])

    assert result.exit_code == 0
    assert "PDFClean Pro" in result.output