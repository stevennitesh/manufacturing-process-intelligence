from __future__ import annotations

import hashlib
import io
import json
from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path
from typing import BinaryIO

import pytest

from mpi.datasets import injection_molding
from mpi.datasets.injection_molding import AcquisitionError, acquire_injection_molding

_VERSION = "7bd35941d75c97a3f276439377dc430ab47402be"
_REPOSITORY = "https://github.com/sc4t1m/scatimdata"
_DOWNLOAD_URL = f"https://raw.githubusercontent.com/sc4t1m/scatimdata/{_VERSION}/dataset2.zip"


def _write_inputs(
    root: Path,
    content: bytes,
    *,
    dataset: str = "injection_molding",
    version: str = _VERSION,
    source_path: str = "dataset2.zip",
    download_url: str = _DOWNLOAD_URL,
    admitted: bool = True,
    expected_content: bytes | None = None,
) -> tuple[Path, Path]:
    config_path = root / "config.yaml"
    manifest_path = root / "manifest.json"
    config_path.write_text(
        "\n".join(
            [
                f"dataset: {dataset}",
                "stage: mvp",
                "enabled: false",
                f"source_url: {_REPOSITORY}",
                f"version: {version}",
                "",
            ]
        ),
        encoding="utf-8",
    )
    identity_content = content if expected_content is None else expected_content
    manifest = {
        "dataset": "injection_molding",
        "source": {
            "repository_url": _REPOSITORY,
            "source_version": _VERSION,
        },
        "files": [
            {
                "candidate": "dataset2",
                "source_path": source_path,
                "immutable_download_url": download_url,
                "bytes": len(identity_content),
                "sha256": hashlib.sha256(identity_content).hexdigest(),
                "admitted": admitted,
            }
        ],
    }
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    return config_path, manifest_path


def _bytes_transport(content: bytes) -> injection_molding.Transport:
    @contextmanager
    def transport(url: str, timeout: float) -> Generator[BinaryIO, None, None]:
        assert url == _DOWNLOAD_URL
        assert timeout > 0
        yield io.BytesIO(content)

    return transport


def _failing_transport(message: str = "network unavailable") -> injection_molding.Transport:
    @contextmanager
    def transport(url: str, timeout: float) -> Generator[BinaryIO, None, None]:
        del url, timeout
        raise AcquisitionError(message)
        yield io.BytesIO()  # pragma: no cover

    return transport


def _acquire(
    tmp_path: Path,
    content: bytes,
    *,
    transport: injection_molding.Transport | None = None,
    expected_content: bytes | None = None,
):
    config_path, manifest_path = _write_inputs(tmp_path, content, expected_content=expected_content)
    return acquire_injection_molding(
        raw_root=tmp_path / "raw",
        config_path=config_path,
        manifest_path=manifest_path,
        transport=transport or _bytes_transport(content),
    )


def test_download_returns_typed_handoff_and_atomic_receipt(tmp_path: Path) -> None:
    content = b"synthetic dataset 2 archive"

    result = _acquire(tmp_path, content)

    assert result.disposition == "downloaded"
    assert result.archive_path.read_bytes() == content
    assert not list(result.archive_path.parent.glob("*.part"))
    receipt = json.loads(result.receipt_path.read_text(encoding="utf-8"))
    assert receipt["archive_path"] == str(result.archive_path)
    assert receipt["observed_size"] == result.size == len(content)
    assert receipt["observed_sha256"] == result.sha256 == hashlib.sha256(content).hexdigest()
    assert receipt["disposition"] == result.disposition
    assert receipt["downloaded_at_utc"] <= receipt["verified_at_utc"]


def test_matching_archive_is_reused_without_network_or_false_download_time(tmp_path: Path) -> None:
    content = b"offline reusable bytes"
    downloaded = _acquire(tmp_path, content)
    original_stat = downloaded.archive_path.stat()
    config_path = tmp_path / "config.yaml"
    manifest_path = tmp_path / "manifest.json"

    reused = acquire_injection_molding(
        raw_root=tmp_path / "raw",
        config_path=config_path,
        manifest_path=manifest_path,
        transport=_failing_transport(),
    )

    assert reused.disposition == "reused"
    assert reused.archive_path.stat().st_mtime_ns == original_stat.st_mtime_ns
    assert reused.receipt_path != downloaded.receipt_path
    receipt = json.loads(reused.receipt_path.read_text(encoding="utf-8"))
    assert "downloaded_at_utc" not in receipt
    assert receipt["disposition"] == "reused"


def test_manifest_config_mismatch_fails_before_destination_effects(tmp_path: Path) -> None:
    config_path, manifest_path = _write_inputs(tmp_path, b"bytes", dataset="other")
    raw_root = tmp_path / "raw"

    with pytest.raises(AcquisitionError, match="does not match configuration"):
        acquire_injection_molding(
            raw_root=raw_root,
            config_path=config_path,
            manifest_path=manifest_path,
            transport=_failing_transport(),
        )

    assert not raw_root.exists()


@pytest.mark.parametrize(
    ("source_path", "download_url"),
    [
        ("../dataset2.zip", _DOWNLOAD_URL),
        ("/dataset2.zip", _DOWNLOAD_URL),
        ("dataset2.zip", "https://github.com/sc4t1m/scatimdata/raw/main/dataset2.zip"),
    ],
)
def test_invalid_manifest_path_or_url_fails_before_writes(
    tmp_path: Path, source_path: str, download_url: str
) -> None:
    config_path, manifest_path = _write_inputs(
        tmp_path, b"bytes", source_path=source_path, download_url=download_url
    )

    with pytest.raises(AcquisitionError):
        acquire_injection_molding(
            raw_root=tmp_path / "raw",
            config_path=config_path,
            manifest_path=manifest_path,
            transport=_failing_transport(),
        )

    assert not (tmp_path / "raw").exists()


def test_existing_mismatch_is_preserved_without_network(tmp_path: Path) -> None:
    content = b"expected"
    config_path, manifest_path = _write_inputs(tmp_path, content)
    archive = tmp_path / "raw" / f"scatimdata-{_VERSION}" / "dataset2.zip"
    archive.parent.mkdir(parents=True)
    archive.write_bytes(b"different")

    with pytest.raises(AcquisitionError, match="preserve or remove"):
        acquire_injection_molding(
            raw_root=tmp_path / "raw",
            config_path=config_path,
            manifest_path=manifest_path,
            transport=_failing_transport(),
        )

    assert archive.read_bytes() == b"different"


@pytest.mark.parametrize(
    ("transport_content", "match"),
    [
        (b"short", "truncated"),
        (b"expected-plus-too-long", "exceeded expected size"),
        (b"same-size-bad", "checksum mismatch"),
    ],
)
def test_bad_download_never_publishes_or_leaves_owned_partial(
    tmp_path: Path, transport_content: bytes, match: str
) -> None:
    expected = b"same-size-ok!"
    config_path, manifest_path = _write_inputs(tmp_path, expected)

    with pytest.raises(AcquisitionError, match=match):
        acquire_injection_molding(
            raw_root=tmp_path / "raw",
            config_path=config_path,
            manifest_path=manifest_path,
            transport=_bytes_transport(transport_content),
        )

    version_dir = tmp_path / "raw" / f"scatimdata-{_VERSION}"
    assert not (version_dir / "dataset2.zip").exists()
    assert not list(version_dir.glob("*.part"))


def test_http_failure_does_not_publish_archive(tmp_path: Path) -> None:
    config_path, manifest_path = _write_inputs(tmp_path, b"expected")

    with pytest.raises(AcquisitionError, match="HTTP 503"):
        acquire_injection_molding(
            raw_root=tmp_path / "raw",
            config_path=config_path,
            manifest_path=manifest_path,
            transport=_failing_transport("HTTP 503"),
        )

    assert not (tmp_path / "raw" / f"scatimdata-{_VERSION}" / "dataset2.zip").exists()


def test_interruption_removes_only_owned_partial(tmp_path: Path) -> None:
    content = b"expected"
    config_path, manifest_path = _write_inputs(tmp_path, content)

    class InterruptedStream(io.BytesIO):
        def read(self, size: int | None = -1) -> bytes:
            del size
            raise KeyboardInterrupt

    @contextmanager
    def interrupting_transport(url: str, timeout: float) -> Generator[BinaryIO, None, None]:
        del url, timeout
        yield InterruptedStream()

    with pytest.raises(KeyboardInterrupt):
        acquire_injection_molding(
            raw_root=tmp_path / "raw",
            config_path=config_path,
            manifest_path=manifest_path,
            transport=interrupting_transport,
        )

    version_dir = tmp_path / "raw" / f"scatimdata-{_VERSION}"
    assert not (version_dir / "dataset2.zip").exists()
    assert not list(version_dir.glob("*.part"))


def test_existing_legacy_lock_is_unrelated_and_preserved(tmp_path: Path) -> None:
    content = b"expected"
    config_path, manifest_path = _write_inputs(tmp_path, content)
    version_dir = tmp_path / "raw" / f"scatimdata-{_VERSION}"
    version_dir.mkdir(parents=True)
    lock = version_dir / ".acquisition.lock"
    lock.write_text("other-owner", encoding="utf-8")

    result = acquire_injection_molding(
        raw_root=tmp_path / "raw",
        config_path=config_path,
        manifest_path=manifest_path,
        transport=_bytes_transport(content),
    )

    assert result.disposition == "downloaded"
    assert lock.read_text(encoding="utf-8") == "other-owner"
    assert (version_dir / "dataset2.zip").read_bytes() == content
