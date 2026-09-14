# pyright: reportMissingTypeStubs=false, reportPrivateUsage=false
"""Local save/load behavior and one raw-to-CLI integration."""

from __future__ import annotations

import json
import shutil
from dataclasses import replace
from pathlib import Path
from typing import NoReturn

import polars as pl
import pytest
from typer.testing import CliRunner

from mpi.cli.app import app
from mpi.core.config import DatasetConfig
from mpi.data.canonical import ManufacturingBundle
from mpi.datasets import injection_molding_canonicalization as canonicalization
from mpi.datasets import injection_molding_persistence as persistence
from mpi.datasets import injection_molding_validation as validation
from mpi.datasets.injection_molding import (
    DEFAULT_CONFIG_PATH,
    DEFAULT_MANIFEST_PATH,
    ResolvedArchiveInputs,
    resolve_archive_inputs,
)
from mpi.datasets.injection_molding_canonicalization import canonicalize_injection_molding
from mpi.datasets.injection_molding_persistence import PersistenceError, load_bundle
from mpi.datasets.injection_molding_validation import RawValidationError, _Expectations
from tests.unit.injection_molding_helpers import canonicalize_fixture, validated_fixture

runner = CliRunner()
TABLES = ("units", "operations", "process_features", "signals", "quality", "context")


@pytest.fixture
def fixture_bundle(tmp_path: Path) -> ManufacturingBundle:
    source, expectations = validated_fixture(tmp_path)
    return canonicalize_fixture(source, expectations)


def test_roundtrip_preserves_tables_and_source_metadata(
    fixture_bundle: ManufacturingBundle,
    tmp_path: Path,
) -> None:
    output = tmp_path / "prepared"
    persistence._write_bundle(fixture_bundle, output)
    assert {item.name for item in output.iterdir()} == {
        *(f"{name}.parquet" for name in TABLES),
        "metadata.json",
    }
    loaded = load_bundle(output)
    for table in TABLES:
        assert getattr(loaded, table).equals(getattr(fixture_bundle, table))
    assert loaded.metadata == fixture_bundle.metadata


def test_writer_does_not_overwrite_existing_output(
    fixture_bundle: ManufacturingBundle,
    tmp_path: Path,
) -> None:
    output = tmp_path / "owned"
    output.mkdir()
    marker = output / "notes.txt"
    marker.write_text("preserve", encoding="utf-8")
    with pytest.raises(PersistenceError, match=r"artifact.write"):
        persistence._write_bundle(fixture_bundle, output)
    assert list(output.iterdir()) == [marker]
    assert marker.read_text(encoding="utf-8") == "preserve"


def test_loader_reports_missing_table_and_wrong_schema(
    fixture_bundle: ManufacturingBundle,
    tmp_path: Path,
) -> None:
    output = tmp_path / "prepared"
    persistence._write_bundle(fixture_bundle, output)
    table = output / "signals.parquet"
    table.unlink()
    with pytest.raises(PersistenceError, match=r"artifact.read"):
        load_bundle(output)
    pl.DataFrame({"wrong_column": [1]}).write_parquet(table)
    with pytest.raises(PersistenceError, match=r"bundle.schema"):
        load_bundle(output)


def test_prepare_missing_raw_stays_offline_and_publishes_nothing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def fail_network(*args: object, **kwargs: object) -> NoReturn:
        del args, kwargs
        pytest.fail("preparation attempted network access")

    monkeypatch.setattr("urllib.request.urlopen", fail_network)
    output = tmp_path / "output"
    with pytest.raises(RawValidationError, match=r"check=archive.present"):
        persistence.prepare(raw_root=tmp_path / "missing-raw", output=output)
    assert not output.exists()


def test_generated_raw_cli_runs_prepare_and_loads_bundle(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fixture_root = tmp_path / "fixture"
    fixture_root.mkdir()
    source, canonical_expectations = validated_fixture(fixture_root)
    raw_expectations = _Expectations(
        scalar_rows=2,
        signal_cycles=3,
        signal_rows=513,
        member_size=(fixture_root / "source.h5").stat().st_size,
        missingness=(("Charge", 1), ("Twkz", 1), ("mittlerer Feuchtegehalt", 1), ("PT-PT002L*", 1)),
        experiment_blocks=((20, 1, 100, 100), (23, 1, 101, 101)),
        matched=2,
        signal_only=1,
    )
    raw_root = tmp_path / "raw"
    version_dir = raw_root / f"scatimdata-{source.source_version}"
    version_dir.mkdir(parents=True)
    shutil.copy2(source.archive_path, version_dir / "dataset2.zip")
    production = resolve_archive_inputs(DEFAULT_CONFIG_PATH, DEFAULT_MANIFEST_PATH)
    config = production.config
    production_identity = production.identity
    fixture_identity = replace(
        production_identity, size=source.archive_size, sha256=source.archive_sha256
    )

    def fixture_config(path: Path) -> DatasetConfig:
        del path
        return config

    def fixture_inputs(
        resolved_config: DatasetConfig, manifest_path: Path
    ) -> ResolvedArchiveInputs:
        del manifest_path
        return ResolvedArchiveInputs(
            config=resolved_config,
            identity=fixture_identity,
            manifest_sha256="d" * 64,
        )

    monkeypatch.setattr(persistence, "resolve_dataset_config", fixture_config)
    monkeypatch.setattr(
        persistence,
        "resolve_archive_identity",
        fixture_inputs,
    )
    monkeypatch.setattr(validation, "_Expectations", lambda: raw_expectations)
    monkeypatch.setattr(canonicalization, "_CanonicalExpectations", lambda: canonical_expectations)

    output = tmp_path / "prepared"
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
    assert result.exit_code == 0, result.output
    assert "disposition: published" in result.output
    assert "- units: 2" in result.output
    loaded = load_bundle(output)
    expected = canonicalize_injection_molding(replace(source, manifest_sha256="d" * 64))
    for table in TABLES:
        assert getattr(loaded, table).equals(getattr(expected, table))
    assert loaded.metadata == expected.metadata

    # Reuse is a local read, not a second raw audit or canonicalization.
    def forbidden_validation(*args: object, **kwargs: object) -> NoReturn:
        pytest.fail("reuse revalidated the raw archive")

    monkeypatch.setattr(persistence, "validate_resolved_injection_molding", forbidden_validation)
    reused = persistence.prepare(raw_root=raw_root, output=output)
    assert reused.disposition == "reused"
    assert reused.bundle.metadata == loaded.metadata

    metadata_path = output / "metadata.json"
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    metadata["archive_sha256"] = "0" * 64
    metadata_path.write_text(json.dumps(metadata), encoding="utf-8")
    with pytest.raises(PersistenceError, match=r"preparation.source"):
        persistence.prepare(raw_root=raw_root, output=output)
