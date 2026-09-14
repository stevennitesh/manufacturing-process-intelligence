from pathlib import Path
from typing import Literal

import pytest
from typer.testing import CliRunner

from mpi import __version__
from mpi.cli.app import app
from mpi.datasets.injection_molding import (
    AcquisitionResult,
)
from mpi.datasets.injection_molding_persistence import PersistenceError

runner = CliRunner()


def test_version() -> None:
    result = runner.invoke(app, ["--version"])

    assert result.exit_code == 0
    assert result.stdout.strip() == __version__


def test_validate_dataset_config() -> None:
    result = runner.invoke(app, ["config", "validate", "configs/datasets/injection_molding.yaml"])

    assert result.exit_code == 0
    assert "valid dataset config: injection_molding (mvp)" in result.stdout


@pytest.mark.parametrize("disposition", ["downloaded", "reused"])
def test_acquire_injection_molding_cli_handoff(
    monkeypatch: pytest.MonkeyPatch, disposition: Literal["downloaded", "reused"]
) -> None:
    def acquire_stub(*, raw_root: Path) -> AcquisitionResult:
        assert raw_root == Path("isolated-raw")
        return AcquisitionResult(
            dataset="injection_molding",
            candidate="dataset2",
            source_version="abc123",
            archive_path=Path("isolated-raw/version/dataset2.zip"),
            size=12,
            sha256="f" * 64,
            disposition=disposition,
        )

    monkeypatch.setattr("mpi.cli.app.acquire_injection_molding", acquire_stub)

    result = runner.invoke(
        app, ["data", "acquire", "injection_molding", "--raw-root", "isolated-raw"]
    )

    assert result.exit_code == 0
    assert f"disposition: {disposition}" in result.stdout
    assert "byte-verified; schema validation and preparation not performed" in result.stdout


def test_validate_cli_missing_archive_is_local_only(tmp_path: Path) -> None:
    raw_root = tmp_path / "raw"

    result = runner.invoke(
        app, ["data", "validate", "injection_molding", "--raw-root", str(raw_root)]
    )

    assert result.exit_code == 1
    assert "check=archive.present" in result.output
    assert "mpi data acquire injection_molding" in result.output
    assert not raw_root.exists()


def test_prepare_cli_rejects_unsupported_dataset() -> None:
    result = runner.invoke(app, ["data", "prepare", "cip_dmd"])

    assert result.exit_code == 1
    assert "unsupported preparation dataset: cip_dmd" in result.output


def test_prepare_cli_missing_archive_is_local_only(tmp_path: Path) -> None:
    raw_root = tmp_path / "raw"
    output = tmp_path / "processed"

    result = runner.invoke(
        app,
        [
            "data",
            "prepare",
            "injection_molding",
            "--raw-root",
            str(raw_root),
            "--output",
            str(output),
        ],
    )

    assert result.exit_code == 1
    assert "check=archive.present" in result.output
    assert "mpi data acquire injection_molding" in result.output
    assert not raw_root.exists()
    assert not output.exists()


def test_prepare_cli_reports_structured_publication_failure_without_success_summary(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    output = tmp_path / "output"

    def fail_prepare(*, raw_root: Path, output: Path):  # type: ignore[no-untyped-def]
        del raw_root
        raise PersistenceError("publication.publish", output, "permission denied")

    monkeypatch.setattr("mpi.cli.app.prepare_injection_molding", fail_prepare)
    result = runner.invoke(
        app,
        [
            "data",
            "prepare",
            "injection_molding",
            "--raw-root",
            str(tmp_path / "raw"),
            "--output",
            str(output),
        ],
    )

    assert result.exit_code == 1
    assert "check=publication.publish" in result.output
    assert "disposition:" not in result.output
    assert "artifact manifest sha256:" not in result.output
