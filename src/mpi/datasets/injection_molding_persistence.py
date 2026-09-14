"""Local Dataset 2 preparation: six Parquet tables and source metadata."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Final, Literal

import polars as pl
from pydantic import TypeAdapter, ValidationError

from mpi.data.canonical import BundleMetadata, ManufacturingBundle
from mpi.datasets.injection_molding import (
    DEFAULT_CONFIG_PATH,
    DEFAULT_MANIFEST_PATH,
    DEFAULT_RAW_ROOT,
    resolve_archive_identity,
    resolve_dataset_config,
)
from mpi.datasets.injection_molding_canonicalization import (
    SOURCE_VERSION,
    CanonicalizationError,
    canonicalize_injection_molding,
    validate_bundle_schema,
)
from mpi.datasets.injection_molding_validation import validate_resolved_injection_molding

DEFAULT_OUTPUT: Final = Path("data/processed/injection_molding/dataset2")
_TABLE_NAMES: Final = (
    "units",
    "operations",
    "process_features",
    "signals",
    "quality",
    "context",
)


class PersistenceError(RuntimeError):
    """Preparation or loading failed; existing outputs are never overwritten."""

    def __init__(self, check_id: str, path: Path, message: str) -> None:
        super().__init__(f"check={check_id}; path={path}; {message}")
        self.check_id = check_id
        self.path = path


@dataclass(frozen=True)
class PreparationResult:
    output_path: Path
    disposition: Literal["published", "reused"]
    bundle: ManufacturingBundle

    @property
    def source_version(self) -> str:
        return self.bundle.metadata.source_version

    @property
    def source_manifest_sha256(self) -> str:
        return self.bundle.metadata.manifest_sha256


def load_bundle(path: Path) -> ManufacturingBundle:
    """Read local tables and check their schema, not rerun the raw-data audit."""
    try:
        metadata = TypeAdapter(BundleMetadata).validate_json((path / "metadata.json").read_bytes())
        tables = {name: pl.read_parquet(path / f"{name}.parquet") for name in _TABLE_NAMES}
        bundle = ManufacturingBundle(metadata=metadata, **tables)
        validate_bundle_schema(bundle)
    except (OSError, ValidationError, pl.exceptions.PolarsError, CanonicalizationError) as error:
        raise PersistenceError("artifact.read", path, str(error)) from error
    return bundle


def _write_bundle(bundle: ManufacturingBundle, output: Path) -> PreparationResult:
    """Write a new directory, with metadata last to mark a completed write."""
    try:
        output.mkdir(parents=True)
    except OSError as error:
        raise PersistenceError("artifact.write", output, str(error)) from error
    try:
        for name in _TABLE_NAMES:
            table: pl.DataFrame = getattr(bundle, name)
            table.write_parquet(output / f"{name}.parquet")
        (output / "metadata.json").write_text(
            json.dumps(asdict(bundle.metadata), indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
    except (OSError, pl.exceptions.PolarsError) as error:
        raise PersistenceError(
            "artifact.write",
            output,
            f"{error}; incomplete output left for inspection; remove it or choose a new output",
        ) from error
    return PreparationResult(output.resolve(), "published", bundle)


def prepare(
    *,
    raw_root: Path = DEFAULT_RAW_ROOT,
    output: Path = DEFAULT_OUTPUT,
    config_path: Path = DEFAULT_CONFIG_PATH,
    manifest_path: Path = DEFAULT_MANIFEST_PATH,
) -> PreparationResult:
    """Prepare offline, or load an existing output from the configured source.

    Reuse does not promise freshness after code changes. To regenerate, remove the
    generated output explicitly or select a new directory.
    """
    config = resolve_dataset_config(config_path)
    if (
        config.dataset != "injection_molding"
        or config.stage != "mvp"
        or not config.enabled
        or config.version != SOURCE_VERSION
    ):
        raise PersistenceError(
            "preparation.config",
            config_path,
            "enable the pinned injection_molding MVP source",
        )
    resolved = resolve_archive_identity(config, manifest_path)
    if output.exists():
        bundle = load_bundle(output)
        if (
            bundle.metadata.dataset != config.dataset
            or bundle.metadata.candidate != resolved.identity.candidate
            or bundle.metadata.source_version != config.version
            or bundle.metadata.archive_sha256 != resolved.identity.sha256
            or bundle.metadata.manifest_sha256 != resolved.manifest_sha256
        ):
            raise PersistenceError(
                "preparation.source",
                output,
                "different source; select a new output",
            )
        return PreparationResult(output.resolve(), "reused", bundle)
    source = validate_resolved_injection_molding(raw_root=raw_root, resolved=resolved)
    return _write_bundle(canonicalize_injection_molding(source), output)
