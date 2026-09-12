from typer.testing import CliRunner

from mqi import __version__
from mqi.cli.app import app

runner = CliRunner()


def test_version() -> None:
    result = runner.invoke(app, ["--version"])

    assert result.exit_code == 0
    assert result.stdout.strip() == __version__


def test_validate_dataset_config() -> None:
    result = runner.invoke(app, ["config", "validate", "configs/datasets/solidair.yaml"])

    assert result.exit_code == 0
    assert "valid dataset config: solidair (mvp)" in result.stdout
