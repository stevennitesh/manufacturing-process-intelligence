from typer.testing import CliRunner

from mpi import __version__
from mpi.cli.app import app

runner = CliRunner()


def test_version() -> None:
    result = runner.invoke(app, ["--version"])

    assert result.exit_code == 0
    assert result.stdout.strip() == __version__


def test_validate_dataset_config() -> None:
    result = runner.invoke(app, ["config", "validate", "configs/datasets/injection_molding.yaml"])

    assert result.exit_code == 0
    assert "valid dataset config: injection_molding (mvp)" in result.stdout
