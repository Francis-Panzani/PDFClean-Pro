from typer.testing import CliRunner

from pdfclean.__main__ import app


def test_help_output_includes_clean_command() -> None:
    runner = CliRunner()
    result = runner.invoke(app, ["--help"])

    assert result.exit_code == 0
    assert "clean" in result.stdout.lower()
