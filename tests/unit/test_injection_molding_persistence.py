# pyright: reportMissingTypeStubs=false, reportPrivateUsage=false
"""Format-2 persistence, standalone loading and preparation integration."""

from __future__ import annotations

import hashlib
import json
import shutil
from dataclasses import replace
from importlib.resources import files
from pathlib import Path
from typing import Any, NoReturn, cast

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
from mpi.datasets.injection_molding_persistence import (
    PersistenceError,
    load_bundle,
)
from mpi.datasets.injection_molding_validation import RawValidationError, _Expectations
from tests.unit.injection_molding_helpers import canonicalize_fixture, validated_fixture

runner = CliRunner()
TABLES = ("units", "operations", "process_features", "signals", "quality", "context")


@pytest.fixture
def fixture_bundle(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> ManufacturingBundle:
    source, expectations = validated_fixture(tmp_path)
    monkeypatch.setattr(canonicalization, "_CanonicalExpectations", lambda: expectations)
    return canonicalize_fixture(source, expectations)


def _persist(bundle: ManufacturingBundle, output: Path) -> persistence.PreparationResult:
    return persistence._persist_candidate(bundle, output=output)


def _manifest(output: Path) -> dict[str, Any]:
    return cast(dict[str, Any], json.loads((output / "manifest.json").read_text(encoding="utf-8")))


def _write_manifest(output: Path, manifest: dict[str, Any]) -> None:
    (output / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def _refresh_hash(output: Path, payload_name: str) -> None:
    manifest = _manifest(output)
    payloads = cast(list[dict[str, str]], manifest["files"])
    entry = next(item for item in payloads if item["path"] == payload_name)
    entry["sha256"] = hashlib.sha256((output / payload_name).read_bytes()).hexdigest()
    _write_manifest(output, manifest)


def test_roundtrip_preserves_exact_tables_and_full_research_context(
    fixture_bundle: ManufacturingBundle, tmp_path: Path
) -> None:
    output = tmp_path / "published"
    result = _persist(fixture_bundle, output)

    assert result.disposition == "published"
    manifest = _manifest(output)
    assert manifest == {
        "files": [
            {
                "path": name,
                "sha256": hashlib.sha256((output / name).read_bytes()).hexdigest(),
            }
            for name in (*[f"{table}.parquet" for table in TABLES], "metadata.json")
        ],
    }
    loaded = load_bundle(output)
    for table in TABLES:
        assert getattr(loaded, table).equals(getattr(fixture_bundle, table))
    packaged = json.loads(
        files("mpi.datasets")
        .joinpath("resources/injection_molding_research.json")
        .read_text(encoding="utf-8")
    )
    assert list(loaded.metadata.research_context) == packaged
    assert loaded.metadata.research_context == fixture_bundle.metadata.research_context
    assert loaded.metadata.source_repository_url == "https://github.com/sc4t1m/scatimdata"
    assert loaded.metadata.prepared_at_utc is not None


def test_loader_is_standalone_and_ignores_unrelated_notes(
    fixture_bundle: ManufacturingBundle,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output = tmp_path / "published"
    _persist(fixture_bundle, output)
    (output / "README.local.txt").write_text("analyst note", encoding="utf-8")

    def forbidden(*args: object, **kwargs: object) -> NoReturn:
        del args, kwargs
        pytest.fail("standalone loading consulted an external owner")

    monkeypatch.setattr(canonicalization, "files", forbidden)
    monkeypatch.setattr(persistence, "resolve_dataset_config", forbidden)
    monkeypatch.setattr("urllib.request.urlopen", forbidden)
    loaded = load_bundle(output)
    assert loaded.units.equals(fixture_bundle.units)


def test_compatible_reuse_is_write_free_and_preserves_recorded_context(
    fixture_bundle: ManufacturingBundle,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output = tmp_path / "published"
    first = _persist(fixture_bundle, output)
    before = {item.name: item.read_bytes() for item in output.iterdir() if item.is_file()}

    def forbidden_write(*args: object, **kwargs: object) -> NoReturn:
        del args, kwargs
        pytest.fail("reuse attempted to stage a new candidate")

    monkeypatch.setattr(persistence, "_write_candidate", forbidden_write)
    second = _persist(fixture_bundle, output)
    after = {item.name: item.read_bytes() for item in output.iterdir() if item.is_file()}
    assert second.disposition == "reused"
    assert second.manifest_sha256 == first.manifest_sha256
    assert second.bundle.metadata.prepared_at_utc == first.bundle.metadata.prepared_at_utc
    assert after == before


@pytest.mark.parametrize("payload", ["metadata.json", "signals.parquet"])
def test_loader_rejects_missing_or_corrupt_required_payload(
    fixture_bundle: ManufacturingBundle, tmp_path: Path, payload: str
) -> None:
    missing = tmp_path / "missing"
    _persist(fixture_bundle, missing)
    (missing / payload).unlink()
    with pytest.raises(PersistenceError, match=r"check=artifact.path"):
        load_bundle(missing)

    corrupt = tmp_path / "corrupt"
    _persist(fixture_bundle, corrupt)
    (corrupt / payload).write_bytes(b"changed")
    with pytest.raises(PersistenceError, match=r"check=artifact.hash"):
        load_bundle(corrupt)


def test_loader_rejects_unknown_metadata_and_recomputed_scientific_corruption(
    fixture_bundle: ManufacturingBundle, tmp_path: Path
) -> None:
    metadata_output = tmp_path / "metadata"
    _persist(fixture_bundle, metadata_output)
    metadata_path = metadata_output / "metadata.json"
    metadata = cast(dict[str, Any], json.loads(metadata_path.read_text(encoding="utf-8")))
    metadata["duplicate_contract"] = True
    metadata_path.write_text(json.dumps(metadata), encoding="utf-8")
    _refresh_hash(metadata_output, "metadata.json")
    with pytest.raises(PersistenceError, match=r"check=metadata.schema"):
        load_bundle(metadata_output)

    table_output = tmp_path / "table"
    _persist(fixture_bundle, table_output)
    units_path = table_output / "units.parquet"
    pl.read_parquet(units_path).with_columns(
        pl.when(pl.col("source_row_index") == 1)
        .then(pl.lit("injection_molding/dataset2/100"))
        .otherwise(pl.col("unit_id"))
        .alias("unit_id")
    ).write_parquet(units_path)
    _refresh_hash(table_output, "units.parquet")
    with pytest.raises(PersistenceError, match=r"check=bundle.keys"):
        load_bundle(table_output)


def test_existing_destination_conflicts_are_preserved(
    fixture_bundle: ManufacturingBundle, tmp_path: Path
) -> None:
    output = tmp_path / "owned"
    output.mkdir()
    marker = output / "owner.txt"
    marker.write_text("preserve", encoding="utf-8")
    with pytest.raises(PersistenceError, match=r"check=publication.conflict"):
        _persist(fixture_bundle, output)
    assert marker.read_text(encoding="utf-8") == "preserve"
    assert {item.name for item in output.iterdir()} == {"owner.txt"}


def test_failed_write_cleans_only_owned_staging(
    fixture_bundle: ManufacturingBundle,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output = tmp_path / "failed"
    original = pl.DataFrame.write_parquet
    calls = 0

    def failing_write(self: pl.DataFrame, file: Path, *args: Any, **kwargs: Any) -> None:
        nonlocal calls
        calls += 1
        if calls == 2:
            raise OSError("injected write failure")
        original(self, file, *args, **kwargs)

    monkeypatch.setattr(pl.DataFrame, "write_parquet", failing_write)
    with pytest.raises(PersistenceError, match=r"check=artifact.write"):
        _persist(fixture_bundle, output)
    assert not output.exists()
    assert not list(tmp_path.glob(".failed.staging-*"))


def test_absent_acquisition_time_is_recorded_honestly(
    fixture_bundle: ManufacturingBundle, tmp_path: Path
) -> None:
    result = _persist(fixture_bundle, tmp_path / "published")
    metadata = result.bundle.metadata
    assert metadata.acquisition_time_utc is None
    assert metadata.acquisition_time_source is None
    assert metadata.acquisition_time_unavailable_reason == (
        "identity-validated acquisition receipt unavailable"
    )


@pytest.mark.parametrize(
    ("enabled", "version"), [(False, "7bd35941d75c97a3f276439377dc430ab47402be"), (True, "0" * 40)]
)
def test_prepare_rejects_disabled_or_unpinned_config_before_raw_access(
    tmp_path: Path, enabled: bool, version: str
) -> None:
    config = DatasetConfig(
        dataset="injection_molding",
        stage="mvp",
        enabled=enabled,
        source_url="https://github.com/sc4t1m/scatimdata",
        version=version,
    )
    with pytest.raises(PersistenceError, match=r"check=preparation.config"):
        persistence._validate_preparation_config(config, tmp_path / "config.yaml")


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
    assert loaded.metadata.research_context == expected.metadata.research_context
