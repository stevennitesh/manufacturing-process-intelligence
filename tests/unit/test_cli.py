import hashlib
import json
from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path
from typing import BinaryIO, Literal

import pytest
from typer.testing import CliRunner

from mpi import __version__
from mpi.cli.app import app
from mpi.datasets.injection_molding import (
    AcquisitionResult,
    acquire_injection_molding,
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
            receipt_path=Path("isolated-raw/version/receipts/result.json"),
            disposition=disposition,
        )

    monkeypatch.setattr("mpi.cli.app.acquire_injection_molding", acquire_stub)

    result = runner.invoke(
        app, ["data", "acquire", "injection_molding", "--raw-root", "isolated-raw"]
    )

    assert result.exit_code == 0
    assert f"disposition: {disposition}" in result.stdout
    assert "byte-verified; schema validation and preparation not performed" in result.stdout


def test_cli_normalizes_real_receipt_obstruction_and_recovers_offline(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    content = b"verified archive"
    version = "7bd35941d75c97a3f276439377dc430ab47402be"
    repository = "https://github.com/sc4t1m/scatimdata"
    config_path = tmp_path / "config.yaml"
    manifest_path = tmp_path / "manifest.json"
    config_path.write_text(
        "\n".join(
            [
                "dataset: injection_molding",
                "stage: mvp",
                "enabled: false",
                f"source_url: {repository}",
                f"version: {version}",
                "",
            ]
        ),
        encoding="utf-8",
    )
    manifest_path.write_text(
        json.dumps(
            {
                "dataset": "injection_molding",
                "source": {"repository_url": repository, "source_version": version},
                "files": [
                    {
                        "candidate": "dataset2",
                        "source_path": "dataset2.zip",
                        "immutable_download_url": (
                            "https://raw.githubusercontent.com/sc4t1m/scatimdata/"
                            f"{version}/dataset2.zip"
                        ),
                        "bytes": len(content),
                        "sha256": hashlib.sha256(content).hexdigest(),
                        "admitted": True,
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    raw_root = tmp_path / "raw"
    version_dir = raw_root / f"scatimdata-{version}"
    version_dir.mkdir(parents=True)
    archive = version_dir / "dataset2.zip"
    archive.write_bytes(content)
    receipts_obstruction = version_dir / "receipts"
    receipts_obstruction.write_text("not a directory", encoding="utf-8")

    @contextmanager
    def offline_transport(url: str, timeout: float) -> Generator[BinaryIO, None, None]:
        del url, timeout
        raise AssertionError("offline reuse attempted network transport")
        yield  # pragma: no cover

    def acquire_real(*, raw_root: Path) -> AcquisitionResult:
        return acquire_injection_molding(
            raw_root=raw_root,
            config_path=config_path,
            manifest_path=manifest_path,
            transport=offline_transport,
        )

    monkeypatch.setattr("mpi.cli.app.acquire_injection_molding", acquire_real)

    failed = runner.invoke(
        app, ["data", "acquire", "injection_molding", "--raw-root", str(raw_root)]
    )

    assert failed.exit_code == 1
    assert str(archive) in failed.output
    assert "archive was left untouched" in failed.output
    assert archive.read_bytes() == content
    assert not (version_dir / ".acquisition.lock").exists()

    receipts_obstruction.unlink()
    recovered = runner.invoke(
        app, ["data", "acquire", "injection_molding", "--raw-root", str(raw_root)]
    )

    assert recovered.exit_code == 0
    assert "disposition: reused" in recovered.output
    receipts = list((version_dir / "receipts").glob("*.json"))
    assert len(receipts) == 1
    receipt = json.loads(receipts[0].read_text(encoding="utf-8"))
    assert "downloaded_at_utc" not in receipt
    assert archive.read_bytes() == content
    assert not (version_dir / ".acquisition.lock").exists()


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
