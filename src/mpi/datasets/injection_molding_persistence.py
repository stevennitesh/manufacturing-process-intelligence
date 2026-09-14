"""Dataset 2 bundle preparation and standalone loading."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import uuid
from dataclasses import asdict, dataclass, replace
from datetime import UTC, datetime
from pathlib import Path
from typing import Final, Literal, NoReturn, cast

import polars as pl
from pydantic import BaseModel, ConfigDict, Field, TypeAdapter, ValidationError

from mpi.core.config import DatasetConfig
from mpi.data.canonical import BundleMetadata, ManufacturingBundle
from mpi.datasets.injection_molding import (
    DEFAULT_CONFIG_PATH,
    DEFAULT_MANIFEST_PATH,
    DEFAULT_RAW_ROOT,
    AcquisitionError,
    resolve_archive_identity,
    resolve_dataset_config,
)
from mpi.datasets.injection_molding_canonicalization import (
    SOURCE_VERSION,
    CanonicalizationError,
    canonicalize_injection_molding,
    validate_injection_molding_bundle,
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
_PAYLOAD_NAMES: Final = (*[f"{name}.parquet" for name in _TABLE_NAMES], "metadata.json")
_SHA256_PATTERN: Final = r"^[0-9a-f]{64}$"


class PersistenceError(RuntimeError):
    """A bundle could not be loaded, published or reused."""

    def __init__(self, check_id: str, path: Path, message: str) -> None:
        super().__init__(f"check={check_id}; path={path}; {message}")
        self.check_id = check_id
        self.path = path


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class _Payload(_StrictModel):
    path: str
    sha256: str = Field(pattern=_SHA256_PATTERN)


class _Manifest(_StrictModel):
    files: tuple[_Payload, ...]


@dataclass(frozen=True)
class PreparationResult:
    """Verified publication or exact table/source reuse of one bundle directory."""

    output_path: Path
    disposition: Literal["published", "reused"]
    manifest_sha256: str
    bundle: ManufacturingBundle
    source_version: str
    source_manifest_sha256: str


def _fail(check_id: str, path: Path, message: str) -> NoReturn:
    raise PersistenceError(check_id, path, message)


def _is_link(path: Path) -> bool:
    try:
        return path.is_symlink() or (hasattr(os.path, "isjunction") and os.path.isjunction(path))
    except OSError:
        return True


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    try:
        with path.open("rb") as stream:
            while chunk := stream.read(1024 * 1024):
                digest.update(chunk)
    except OSError as error:
        _fail("artifact.read", path, str(error))
    return digest.hexdigest()


def _json_bytes(value: object) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode()


def _write_bytes(path: Path, content: bytes) -> None:
    try:
        with path.open("xb") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
    except OSError as error:
        _fail("artifact.write", path, str(error))


def _table(bundle: ManufacturingBundle, name: str) -> pl.DataFrame:
    return cast(pl.DataFrame, getattr(bundle, name))


def _metadata_bytes(metadata: BundleMetadata) -> bytes:
    return _json_bytes(asdict(metadata))


def _metadata_from_bytes(content: bytes, path: Path) -> BundleMetadata:
    try:
        raw: object = json.loads(content)
        metadata = TypeAdapter(BundleMetadata).validate_json(content)
        if raw != json.loads(_metadata_bytes(metadata)):
            _fail("metadata.schema", path, "metadata contains unknown or noncanonical fields")
        return metadata
    except (ValidationError, ValueError) as error:
        _fail("metadata.schema", path, str(error))


def _validate_metadata_identity(metadata: BundleMetadata, path: Path) -> None:
    identity = (metadata.dataset, metadata.candidate, metadata.source_version)
    if identity != ("injection_molding", "dataset2", SOURCE_VERSION):
        _fail("metadata.identity", path, f"unsupported source identity {identity!r}")
    if (
        metadata.archive_size <= 0
        or len(metadata.archive_sha256) != 64
        or len(metadata.manifest_sha256) != 64
    ):
        _fail("metadata.identity", path, "source archive identity is incomplete")


def _git_evidence(package_file: Path | None = None) -> tuple[str | None, bool | None, str | None]:
    executing_file = (package_file or Path(__file__)).resolve()
    repository: Path | None = None
    for candidate in executing_file.parents:
        if (candidate / ".git").exists() and executing_file.is_relative_to(
            candidate / "src" / "mpi"
        ):
            repository = candidate
            break
    if repository is None:
        return None, None, "executing package is not owned by a source checkout"
    try:
        commit = subprocess.run(
            ["git", "-C", str(repository), "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
            timeout=10,
        ).stdout.strip()
        status = subprocess.run(
            ["git", "-C", str(repository), "status", "--porcelain", "--untracked-files=normal"],
            check=True,
            capture_output=True,
            text=True,
            timeout=10,
        ).stdout
        if len(commit) != 40:
            raise ValueError("Git returned a non-commit identity")
        return commit, bool(status), None
    except (OSError, subprocess.SubprocessError, ValueError) as error:
        return None, None, str(error)


def _record_preparation_context(
    bundle: ManufacturingBundle,
    *,
    source_url: str,
    receipt_path: Path | None,
    downloaded_at_utc: str | None,
) -> ManufacturingBundle:
    commit, dirty, git_reason = _git_evidence()
    if receipt_path is None:
        acquisition_time = None
        acquisition_source = None
        acquisition_reason = "identity-validated acquisition receipt unavailable"
    elif downloaded_at_utc is None:
        acquisition_time = None
        acquisition_source = None
        acquisition_reason = "identity-validated receipt contains no download timestamp"
    else:
        acquisition_time = downloaded_at_utc
        acquisition_source = "downloaded_at_utc"
        acquisition_reason = None
    metadata = replace(
        bundle.metadata,
        source_repository_url=source_url.rstrip("/"),
        prepared_at_utc=datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        acquisition_time_utc=acquisition_time,
        acquisition_time_source=acquisition_source,
        acquisition_time_unavailable_reason=acquisition_reason,
        git_commit=commit,
        git_dirty=dirty,
        git_unavailable_reason=git_reason,
    )
    return ManufacturingBundle(
        units=bundle.units,
        operations=bundle.operations,
        process_features=bundle.process_features,
        signals=bundle.signals,
        quality=bundle.quality,
        context=bundle.context,
        metadata=metadata,
    )


def _manifest_for(staging: Path) -> _Manifest:
    return _Manifest(
        files=tuple(_Payload(path=name, sha256=_sha256(staging / name)) for name in _PAYLOAD_NAMES),
    )


def _write_candidate(staging: Path, bundle: ManufacturingBundle) -> str:
    try:
        staging.mkdir()
        for name in _TABLE_NAMES:
            _table(bundle, name).write_parquet(staging / f"{name}.parquet")
    except (OSError, pl.exceptions.PolarsError) as error:
        _fail("artifact.write", staging, str(error))
    _write_bytes(staging / "metadata.json", _metadata_bytes(bundle.metadata))
    manifest_bytes = _json_bytes(_manifest_for(staging).model_dump(mode="json"))
    _write_bytes(staging / "manifest.json", manifest_bytes)
    return hashlib.sha256(manifest_bytes).hexdigest()


def _read_manifest(path: Path) -> tuple[_Manifest, str]:
    manifest_path = path / "manifest.json"
    try:
        content = manifest_path.read_bytes()
        raw: object = json.loads(content)
    except (OSError, ValueError) as error:
        _fail("manifest.schema", manifest_path, str(error))
    if not isinstance(raw, dict):
        _fail("manifest.schema", manifest_path, "manifest must be a JSON object")
    manifest_object = cast(dict[str, object], raw)
    try:
        manifest = _Manifest.model_validate(manifest_object)
    except (ValidationError, ValueError) as error:
        _fail("manifest.schema", manifest_path, str(error))
    names = tuple(item.path for item in manifest.files)
    if names != _PAYLOAD_NAMES or len(set(names)) != len(_PAYLOAD_NAMES):
        _fail("manifest.inventory", manifest_path, "required payload names/order differ")
    return manifest, hashlib.sha256(content).hexdigest()


def _validate_artifact_path(path: Path, *, allow_staging: bool) -> None:
    if not path.is_dir():
        _fail("artifact.path", path, "bundle path must be a directory")
    if allow_staging:
        if not path.name.startswith(".") or ".staging-" not in path.name:
            _fail("artifact.publication", path, "internal candidate has an unexpected name")
    elif ".staging-" in path.name:
        _fail("artifact.publication", path, "staging directories are not public artifacts")


def _load_bundle(path: Path, *, allow_staging: bool) -> tuple[ManufacturingBundle, str]:
    _validate_artifact_path(path, allow_staging=allow_staging)
    manifest, manifest_sha256 = _read_manifest(path)
    for entry in manifest.files:
        payload_path = path / entry.path
        if _is_link(payload_path) or not payload_path.is_file():
            _fail("artifact.path", payload_path, "required payload must be a regular file")
        if _sha256(payload_path) != entry.sha256:
            _fail("artifact.hash", payload_path, "payload SHA-256 differs")
    metadata_path = path / "metadata.json"
    try:
        metadata = _metadata_from_bytes(metadata_path.read_bytes(), metadata_path)
    except OSError as error:
        _fail("artifact.read", metadata_path, str(error))
    _validate_metadata_identity(metadata, metadata_path)
    tables: dict[str, pl.DataFrame] = {}
    for name in _TABLE_NAMES:
        table_path = path / f"{name}.parquet"
        try:
            tables[name] = pl.read_parquet(table_path)
        except (OSError, pl.exceptions.PolarsError) as error:
            _fail("artifact.parquet", table_path, str(error))
    bundle = ManufacturingBundle(metadata=metadata, **tables)
    try:
        validate_injection_molding_bundle(bundle)
    except CanonicalizationError as error:
        _fail(error.check_id, path, str(error))
    return bundle, manifest_sha256


def load_bundle(path: Path) -> ManufacturingBundle:
    """Load a prepared bundle using only the named artifact directory."""
    bundle, _ = _load_bundle(path, allow_staging=False)
    return bundle


def _publish_noreplace(staging: Path, destination: Path) -> None:
    if os.path.lexists(destination):
        raise FileExistsError(destination)
    os.rename(staging, destination)


def _reuse_identity(metadata: BundleMetadata) -> tuple[object, ...]:
    return (
        metadata.dataset,
        metadata.candidate,
        metadata.source_version,
        metadata.archive_size,
        metadata.archive_sha256,
        metadata.manifest_sha256,
        metadata.exclusions,
    )


def _same_candidate(candidate: ManufacturingBundle, existing: ManufacturingBundle) -> bool:
    return _reuse_identity(candidate.metadata) == _reuse_identity(existing.metadata) and all(
        _table(candidate, name).equals(_table(existing, name)) for name in _TABLE_NAMES
    )


def _load_reusable_destination(
    destination: Path, *, bundle: ManufacturingBundle
) -> PreparationResult:
    try:
        existing_bundle, existing_hash = _load_bundle(destination, allow_staging=False)
    except PersistenceError as error:
        _fail(
            "publication.conflict",
            destination,
            f"existing destination is not reusable ({error}); select a new output",
        )
    if not _same_candidate(bundle, existing_bundle):
        _fail(
            "publication.conflict",
            destination,
            "existing artifact has different tables or source identity; select a new output",
        )
    return PreparationResult(
        output_path=destination.resolve(strict=True),
        disposition="reused",
        manifest_sha256=existing_hash,
        bundle=existing_bundle,
        source_version=existing_bundle.metadata.source_version,
        source_manifest_sha256=existing_bundle.metadata.manifest_sha256,
    )


def _persist_candidate(
    bundle: ManufacturingBundle,
    *,
    output: Path,
    source_url: str = "https://github.com/sc4t1m/scatimdata",
    receipt_path: Path | None = None,
    downloaded_at_utc: str | None = None,
) -> PreparationResult:
    destination = output.absolute()
    if ".staging-" in destination.name:
        _fail("publication.path", destination, "output name is reserved for staging state")
    parent = destination.parent
    if _is_link(parent):
        _fail("publication.path", parent, "destination parent must not be a link")
    try:
        parent.mkdir(parents=True, exist_ok=True)
        resolved_parent = parent.resolve(strict=True)
    except OSError as error:
        _fail("publication.path", parent, str(error))
    if destination.name in {"", ".", ".."}:
        _fail("publication.path", destination, "output must name one bundle directory")
    destination = resolved_parent / destination.name
    if os.path.lexists(destination):
        return _load_reusable_destination(destination, bundle=bundle)
    candidate = _record_preparation_context(
        bundle,
        source_url=source_url,
        receipt_path=receipt_path,
        downloaded_at_utc=downloaded_at_utc,
    )
    staging = resolved_parent / f".{destination.name}.staging-{uuid.uuid4().hex}"
    try:
        candidate_hash = _write_candidate(staging, candidate)
        candidate_bundle, verified_hash = _load_bundle(staging, allow_staging=True)
        if verified_hash != candidate_hash:
            _fail("publication.verify", staging, "candidate manifest identity changed")
        try:
            _publish_noreplace(staging, destination)
        except (AttributeError, OSError) as error:
            _fail("publication.publish", destination, str(error))
        return PreparationResult(
            output_path=destination.resolve(strict=True),
            disposition="published",
            manifest_sha256=candidate_hash,
            bundle=candidate_bundle,
            source_version=candidate_bundle.metadata.source_version,
            source_manifest_sha256=candidate_bundle.metadata.manifest_sha256,
        )
    finally:
        if staging.exists() and not _is_link(staging):
            shutil.rmtree(staging, ignore_errors=True)


def _validate_preparation_config(config: DatasetConfig, path: Path) -> None:
    if (
        config.dataset != "injection_molding"
        or config.stage != "mvp"
        or not config.enabled
        or config.source_url is None
        or config.version != SOURCE_VERSION
    ):
        _fail(
            "preparation.config",
            path,
            "configuration must enable the pinned injection_molding MVP source",
        )


def prepare(
    *,
    raw_root: Path = DEFAULT_RAW_ROOT,
    output: Path = DEFAULT_OUTPUT,
    config_path: Path = DEFAULT_CONFIG_PATH,
    manifest_path: Path = DEFAULT_MANIFEST_PATH,
) -> PreparationResult:
    """Validate, canonicalize and publish the pinned Dataset 2 source offline."""
    try:
        config = resolve_dataset_config(config_path)
    except AcquisitionError as error:
        _fail("preparation.config", config_path, str(error))
    _validate_preparation_config(config, config_path)
    resolved = resolve_archive_identity(config, manifest_path)
    source = validate_resolved_injection_molding(raw_root=raw_root, resolved=resolved)
    bundle = canonicalize_injection_molding(source)
    return _persist_candidate(
        bundle,
        output=output,
        source_url=resolved.identity.repository_url,
        receipt_path=source.receipt_path,
        downloaded_at_utc=source.receipt_downloaded_at_utc,
    )


__all__ = [
    "DEFAULT_OUTPUT",
    "PersistenceError",
    "PreparationResult",
    "load_bundle",
    "prepare",
]
