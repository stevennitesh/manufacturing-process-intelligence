"""Reproducible byte acquisition for the pinned injection-molding source."""

from __future__ import annotations

import hashlib
import json
import re
import urllib.error
import urllib.request
from collections.abc import Callable, Generator
from contextlib import AbstractContextManager, contextmanager
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import BinaryIO, Literal, cast
from urllib.parse import quote, urlparse

from mpi.core.config import DatasetConfig, parse_dataset_config

DEFAULT_CONFIG_PATH = Path("configs/datasets/injection_molding.yaml")
DEFAULT_MANIFEST_PATH = Path("data/manifests/injection-molding-source.json")
DEFAULT_RAW_ROOT = Path("data/raw/injection_molding")
_SHA256_PATTERN = re.compile(r"[0-9a-f]{64}")
_COMMIT_PATTERN = re.compile(r"[0-9a-f]{40}")
_CHUNK_SIZE = 1024 * 1024


class AcquisitionError(RuntimeError):
    """Raised when raw source bytes cannot be acquired safely."""


@dataclass(frozen=True)
class ArchiveIdentity:
    """Expected identity of the single admitted source archive."""

    dataset: str
    candidate: str
    repository_url: str
    source_version: str
    source_path: str
    download_url: str
    size: int
    sha256: str


@dataclass(frozen=True)
class AcquisitionResult:
    """Byte-verified archive handoff for downstream raw validation."""

    dataset: str
    candidate: str
    source_version: str
    archive_path: Path
    size: int
    sha256: str
    disposition: Literal["downloaded", "reused"]


@dataclass(frozen=True)
class ResolvedArchiveInputs:
    """Configuration and pinned source identity resolved for one invocation."""

    config: DatasetConfig
    identity: ArchiveIdentity
    manifest_sha256: str


Transport = Callable[[str, float], AbstractContextManager[BinaryIO]]


def _require_mapping(value: object, field: str) -> dict[str, object]:
    if not isinstance(value, dict):
        raise AcquisitionError(f"manifest field {field!r} must be an object")
    untyped_mapping = cast(dict[object, object], value)
    if not all(isinstance(key, str) for key in untyped_mapping):
        raise AcquisitionError(f"manifest field {field!r} must use string keys")
    return cast(dict[str, object], value)


def _require_string(mapping: dict[str, object], field: str) -> str:
    value = mapping.get(field)
    if not isinstance(value, str) or not value:
        raise AcquisitionError(f"manifest field {field!r} must be a non-empty string")
    return value


def resolve_dataset_config(config_path: Path) -> DatasetConfig:
    """Load one dataset configuration."""
    try:
        config_bytes = config_path.read_bytes()
        return parse_dataset_config(config_bytes)
    except (OSError, ValueError) as error:
        raise AcquisitionError(f"could not read acquisition configuration: {error}") from error


def resolve_archive_identity(
    config: DatasetConfig,
    manifest_path: Path,
) -> ResolvedArchiveInputs:
    try:
        manifest_bytes = manifest_path.read_bytes()
        raw: object = json.loads(manifest_bytes)
    except (OSError, ValueError) as error:
        raise AcquisitionError(f"could not read acquisition inputs: {error}") from error

    manifest = _require_mapping(raw, "root")
    source = _require_mapping(manifest.get("source"), "source")
    dataset = _require_string(manifest, "dataset")
    repository_url = _require_string(source, "repository_url").rstrip("/")
    version = _require_string(source, "source_version")
    if not _COMMIT_PATTERN.fullmatch(version):
        raise AcquisitionError("manifest source_version must be a lowercase 40-character commit")
    if dataset != config.dataset:
        raise AcquisitionError(
            f"manifest dataset {dataset!r} does not match configuration {config.dataset!r}"
        )
    if config.source_url is None or repository_url != config.source_url.rstrip("/"):
        raise AcquisitionError("manifest repository does not match dataset configuration")
    if version != config.version:
        raise AcquisitionError("manifest source version does not match dataset configuration")

    files_value = manifest.get("files")
    if not isinstance(files_value, list):
        raise AcquisitionError("manifest field 'files' must be a list")
    files = cast(list[object], files_value)
    admitted: list[dict[str, object]] = []
    for index, item in enumerate(files):
        manifest_file = _require_mapping(item, f"files[{index}]")
        if manifest_file.get("admitted") is True:
            admitted.append(manifest_file)
    if len(admitted) != 1:
        raise AcquisitionError("manifest must contain exactly one admitted archive")
    selected = admitted[0]
    candidate = _require_string(selected, "candidate")
    source_path = _require_string(selected, "source_path")
    download_url = _require_string(selected, "immutable_download_url")
    sha256 = _require_string(selected, "sha256")
    size = selected.get("bytes")
    if candidate != "dataset2" or source_path != "dataset2.zip":
        raise AcquisitionError("the single admitted archive must be Dataset 2 at dataset2.zip")
    if not isinstance(size, int) or isinstance(size, bool) or size <= 0:
        raise AcquisitionError("manifest archive size must be a positive integer")
    if not _SHA256_PATTERN.fullmatch(sha256):
        raise AcquisitionError(
            "manifest archive sha256 must be 64 lowercase hexadecimal characters"
        )

    parsed_repository = urlparse(repository_url)
    repository_parts = PurePosixPath(parsed_repository.path).parts
    if parsed_repository.scheme != "https" or parsed_repository.netloc != "github.com":
        raise AcquisitionError("configured source repository must use HTTPS on github.com")
    if len(repository_parts) != 3:
        raise AcquisitionError(
            "configured source repository must identify one owner and repository"
        )
    owner, repository = repository_parts[1:]
    expected_url = (
        f"https://raw.githubusercontent.com/{quote(owner, safe='')}/"
        f"{quote(repository, safe='')}/{version}/{quote(source_path, safe='/')}"
    )
    if download_url != expected_url:
        raise AcquisitionError("manifest download URL does not match the pinned source identity")

    identity = ArchiveIdentity(
        dataset=dataset,
        candidate=candidate,
        repository_url=repository_url,
        source_version=version,
        source_path=source_path,
        download_url=download_url,
        size=size,
        sha256=sha256,
    )
    return ResolvedArchiveInputs(
        config=config,
        identity=identity,
        manifest_sha256=hashlib.sha256(manifest_bytes).hexdigest(),
    )


def resolve_archive_inputs(config_path: Path, manifest_path: Path) -> ResolvedArchiveInputs:
    """Resolve configured source inputs once for an owned pipeline invocation."""
    config = resolve_dataset_config(config_path)
    return resolve_archive_identity(config, manifest_path)


def _destination(raw_root: Path, identity: ArchiveIdentity) -> tuple[Path, Path, Path]:
    try:
        root = raw_root.absolute().resolve(strict=False)
        version_dir = root / f"scatimdata-{identity.source_version}"
        archive_path = version_dir / identity.source_path
        resolved_archive = archive_path.resolve(strict=False)
        resolved_archive.relative_to(root)
    except (OSError, ValueError) as error:
        raise AcquisitionError(f"archive destination escapes raw root: {raw_root}") from error
    if archive_path.is_symlink():
        raise AcquisitionError(f"archive destination must not be a symbolic link: {archive_path}")
    return root, version_dir, archive_path


def resolve_archive_destination(
    raw_root: Path, identity: ArchiveIdentity
) -> tuple[Path, Path, Path]:
    """Resolve the admitted archive path beneath a raw-data root."""
    return _destination(raw_root, identity)


def _measure(path: Path) -> tuple[int, str]:
    digest = hashlib.sha256()
    size = 0
    try:
        with path.open("rb") as stream:
            while chunk := stream.read(_CHUNK_SIZE):
                size += len(chunk)
                digest.update(chunk)
    except OSError as error:
        raise AcquisitionError(f"could not verify archive {path}: {error}") from error
    return size, digest.hexdigest()


def _assert_identity(path: Path, identity: ArchiveIdentity) -> tuple[int, str]:
    size, sha256 = _measure(path)
    if size != identity.size or sha256 != identity.sha256:
        raise AcquisitionError(
            f"archive identity mismatch at {path}: expected bytes={identity.size} "
            f"sha256={identity.sha256}, observed bytes={size} sha256={sha256}; "
            "preserve or remove the mismatched file manually before retrying"
        )
    return size, sha256


@contextmanager
def _https_transport(url: str, timeout: float) -> Generator[BinaryIO, None, None]:
    request = urllib.request.Request(url, headers={"User-Agent": "mpi-acquisition/0.0.1"})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            yield cast(BinaryIO, response)
    except (OSError, urllib.error.URLError) as error:
        raise AcquisitionError(f"HTTPS acquisition failed for {url}: {error}") from error


def _prepare_version_directory(root: Path, version_dir: Path) -> None:
    try:
        version_dir.mkdir(parents=True, exist_ok=True)
        resolved_version_dir = version_dir.resolve(strict=True)
        resolved_version_dir.relative_to(root)
        if not resolved_version_dir.is_dir():
            raise AcquisitionError(f"source version destination is not a directory: {version_dir}")
    except (OSError, ValueError) as error:
        raise AcquisitionError(
            f"source version destination escapes raw root: {version_dir}"
        ) from error


def _download(
    identity: ArchiveIdentity,
    archive_path: Path,
    *,
    transport: Transport,
    timeout: float,
) -> tuple[int, str]:
    """Verify this small archive in memory, then write without overwriting."""
    if timeout <= 0:
        raise AcquisitionError("network timeout must be positive")
    try:
        with transport(identity.download_url, timeout) as response:
            content = response.read(identity.size + 1)
        size = len(content)
        if size > identity.size:
            raise AcquisitionError(f"download exceeded expected size of {identity.size} bytes")
        if size != identity.size:
            raise AcquisitionError(
                f"download was truncated: expected {identity.size} bytes, observed {size}"
            )
        sha256 = hashlib.sha256(content).hexdigest()
        if sha256 != identity.sha256:
            raise AcquisitionError(
                f"download checksum mismatch: expected {identity.sha256}, observed {sha256}"
            )
        with archive_path.open("xb") as output:
            output.write(content)
        return size, sha256
    except OSError as error:
        raise AcquisitionError(f"could not acquire archive {archive_path}: {error}") from error


def acquire_injection_molding(
    *,
    raw_root: Path = DEFAULT_RAW_ROOT,
    config_path: Path = DEFAULT_CONFIG_PATH,
    manifest_path: Path = DEFAULT_MANIFEST_PATH,
    transport: Transport = _https_transport,
    timeout: float = 30.0,
) -> AcquisitionResult:
    """Acquire or reuse the manifest-pinned Dataset 2 archive.

    The returned archive is byte-verified only. Downstream consumers must verify
    its identity again at their own read boundary.
    """
    resolved = resolve_archive_inputs(config_path, manifest_path)
    identity = resolved.identity
    root, version_dir, archive_path = _destination(raw_root, identity)

    _prepare_version_directory(root, version_dir)
    if archive_path.is_symlink():
        raise AcquisitionError(f"archive destination must not be a symbolic link: {archive_path}")
    if archive_path.exists():
        if not archive_path.is_file():
            raise AcquisitionError(f"archive destination is not a regular file: {archive_path}")
        size, sha256 = _assert_identity(archive_path, identity)
        disposition: Literal["downloaded", "reused"] = "reused"
    else:
        size, sha256 = _download(identity, archive_path, transport=transport, timeout=timeout)
        disposition = "downloaded"

    return AcquisitionResult(
        dataset=identity.dataset,
        candidate=identity.candidate,
        source_version=identity.source_version,
        archive_path=archive_path.resolve(),
        size=size,
        sha256=sha256,
        disposition=disposition,
    )
