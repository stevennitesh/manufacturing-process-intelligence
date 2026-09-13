# pyright: reportMissingTypeStubs=false, reportUnknownArgumentType=false
# pyright: reportUnknownMemberType=false, reportPrivateUsage=false, reportIndexIssue=false
from __future__ import annotations

import hashlib
import io
import json
import tempfile
import zipfile
from collections.abc import Generator
from contextlib import contextmanager
from dataclasses import replace
from pathlib import Path
from typing import Protocol, cast

import h5py
import numpy as np
import pytest

from mpi.datasets import injection_molding_validation
from mpi.datasets.injection_molding import (
    ArchiveIdentity,
    acquire_injection_molding,
)
from mpi.datasets.injection_molding_validation import (
    HDF_MEMBER,
    RawValidationError,
    _Expectations,
    _validate_acquired,
    _validate_path,
)


class _NamedTemporary(Protocol):
    name: str


def _write_frame(
    hdf: h5py.File,
    name: str,
    columns: tuple[str, ...],
    values: np.ndarray,
) -> None:
    group = hdf.create_group(name)
    group.attrs["nblocks"] = 1
    group.create_dataset("axis0", data=np.asarray(columns, dtype="S64"))
    group.create_dataset("axis1", data=np.arange(values.shape[0]))
    group.create_dataset("block0_items", data=np.asarray(columns, dtype="S64"))
    group.create_dataset("block0_values", data=values)


def _write_scalars(
    hdf: h5py.File,
    scalar_cycles: tuple[int, ...],
    experiments: tuple[int, ...],
    fractional: bool,
    nullable_context: bool,
) -> None:
    group = hdf.create_group("scalars")
    columns = ("Versuch", "cycle_counter", "context", "weight")
    group.create_dataset("axis0", data=np.asarray(columns, dtype="S64"))
    group.create_dataset("axis1", data=np.arange(len(scalar_cycles)))
    group.attrs["nblocks"] = 3
    group.create_dataset("block0_items", data=np.asarray(("context", "weight"), dtype="S64"))
    context = np.asarray((np.nan, 5.0) if nullable_context else (4.0, 5.0))
    group.create_dataset(
        "block0_values",
        data=np.column_stack((context, np.arange(len(scalar_cycles), dtype=np.float64) + 1.0)),
    )
    group.create_dataset("block1_items", data=np.asarray(("Versuch",), dtype="S64"))
    group.create_dataset("block1_values", data=np.asarray(experiments, dtype=np.int32)[:, None])
    cycle_values = np.asarray(scalar_cycles, dtype=np.float64 if fractional else np.int64)
    if fractional:
        cycle_values[0] = 20.5
    group.create_dataset("block2_items", data=np.asarray(("cycle_counter",), dtype="S64"))
    group.create_dataset("block2_values", data=cycle_values[:, None])


def _write_source(
    root: Path,
    *,
    scalar_cycles: tuple[int, ...] = (20, 21),
    experiments: tuple[int, ...] = (7, 8),
    pressure_cycles: tuple[int, ...] = (22, 20, 21),
    flow_cycles: tuple[int, ...] = (21, 22, 20),
    times: tuple[float, ...] = (0.0, 0.006, 0.012, 0.018),
    fractional_cycle: bool = False,
    missing_member: bool = False,
    duplicate_member: bool = False,
    external_link: bool = False,
    malformed_signal_block: bool = False,
    unexpected_signal_column: bool = False,
    missing_weight: bool = False,
    duplicate_decoded_cycle: bool = False,
    nullable_context: bool = False,
    malformed_axis_group: bool = False,
    external_numeric_storage: bool = False,
) -> tuple[Path, ArchiveIdentity, _Expectations]:
    hdf_path = root / "source.h5"
    with h5py.File(hdf_path, "w") as hdf:
        _write_scalars(hdf, scalar_cycles, experiments, fractional_cycle, nullable_context)
        if missing_weight:
            scalars = cast(h5py.Group, hdf["scalars"])
            cast(h5py.Dataset, scalars["block0_values"])[0, 1] = np.nan
        for group, prefix, cycles in (
            ("Einspritzdruck", "einspritzdruck_ist", pressure_cycles),
            ("Einspritzstrom", "einspritzstrom_ist", flow_cycles),
        ):
            columns = ("time", *(f"{prefix}_{cycle}" for cycle in cycles))
            signal = np.column_stack(
                (
                    np.asarray(times),
                    *(np.full(len(times), cycle, dtype=np.float64) for cycle in cycles),
                )
            )
            _write_frame(hdf, group, columns, signal)
        if malformed_signal_block:
            del hdf["Einspritzdruck"]["block0_items"]
        if unexpected_signal_column:
            hdf["Einspritzdruck"]["axis0"][1] = b"mystery_22"
            hdf["Einspritzdruck"]["block0_items"][1] = b"mystery_22"
        if duplicate_decoded_cycle:
            hdf["Einspritzdruck"]["axis0"][1] = b"einspritzdruck_ist_020"
            hdf["Einspritzdruck"]["block0_items"][1] = b"einspritzdruck_ist_020"
        if malformed_axis_group:
            pressure = cast(h5py.Group, hdf["Einspritzdruck"])
            del pressure["axis0"]
            pressure.create_group("axis0")
        if external_numeric_storage:
            pressure = cast(h5py.Group, hdf["Einspritzdruck"])
            shape = cast(tuple[int, ...], cast(h5py.Dataset, pressure["block0_values"]).shape)
            del pressure["block0_values"]
            pressure.create_dataset(
                "block0_values",
                shape=shape,
                dtype=np.float64,
                external=[("unavailable-payload.bin", 0, int(np.prod(shape)) * 8)],
            )
        for name in (
            "Werkzeuginnendruck",
            "Einspritzdruck_states",
            "Einspritzstrom_states",
            "Werkzeuginnendruck_states",
        ):
            hdf.create_group(name)
        if external_link:
            hdf["external"] = h5py.ExternalLink("other.h5", "/payload")

    archive_path = root / "dataset2.zip"
    member_size = hdf_path.stat().st_size
    with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        if not missing_member:
            archive.write(hdf_path, HDF_MEMBER)
            if duplicate_member:
                with pytest.warns(UserWarning, match="Duplicate name"):
                    archive.writestr(HDF_MEMBER, hdf_path.read_bytes())
        else:
            archive.write(hdf_path, "wrong.h5")
    content = archive_path.read_bytes()
    identity = ArchiveIdentity(
        dataset="injection_molding",
        candidate="dataset2",
        repository_url="https://github.com/sc4t1m/scatimdata",
        source_version="7bd35941d75c97a3f276439377dc430ab47402be",
        source_path="dataset2.zip",
        download_url="https://example.invalid/dataset2.zip",
        size=len(content),
        sha256=hashlib.sha256(content).hexdigest(),
    )
    expectations = _Expectations(
        scalar_columns=("Versuch", "cycle_counter", "context", "weight"),
        scalar_dtypes=(
            ("Versuch", "int32"),
            ("cycle_counter", "int64"),
            ("context", "float64"),
            ("weight", "float64"),
        ),
        scalar_rows=2,
        signal_cycles=3,
        signal_rows=4,
        member_size=member_size,
        missingness=(("context", 1),) if nullable_context else (),
        experiment_blocks=((7, 1, 20, 20), (8, 1, 21, 21)),
        matched=2,
        signal_only=1,
    )
    return archive_path, identity, expectations


def _validate_fixture(archive_path: Path, identity: ArchiveIdentity, expectations: _Expectations):
    return _validate_path(archive_path, identity, "manifest-hash", None, expectations)


def _track_production_extracts(monkeypatch: pytest.MonkeyPatch) -> list[Path]:
    created: list[Path] = []
    real_named_temporary_file = tempfile.NamedTemporaryFile

    def tracked_named_temporary_file(*, suffix: str = "", delete: bool = True) -> _NamedTemporary:
        handle = real_named_temporary_file(suffix=suffix, delete=delete)
        created.append(Path(handle.name))
        return cast(_NamedTemporary, handle)

    monkeypatch.setattr(
        injection_molding_validation.tempfile,
        "NamedTemporaryFile",
        tracked_named_temporary_file,
    )
    return created


def test_source_native_result_preserves_shuffled_cycle_mappings_after_cleanup(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    archive_path, identity, expectations = _write_source(tmp_path)
    extracts = _track_production_extracts(monkeypatch)

    result = _validate_fixture(archive_path, identity, expectations)

    assert result.matched_cycle_ids == (20, 21)
    assert result.signal_only_cycle_ids == (22,)
    pressure = result.signals["Einspritzdruck"]
    flow = result.signals["Einspritzstrom"]
    assert pressure.values[0, pressure.cycle_to_column[20]] == 20
    assert flow.values[0, flow.cycle_to_column[20]] == 20
    assert result.scalars.values["weight"].tolist() == [1.0, 2.0]
    assert not pressure.values.flags.writeable
    assert not result.scalars.values["weight"].flags.writeable
    with pytest.raises(ValueError, match="cannot set WRITEABLE flag"):
        pressure.values.flags.writeable = True
    assert len(extracts) == 1
    assert all(not path.exists() for path in extracts)


def test_allowed_nullable_context_is_preserved_without_imputation(tmp_path: Path) -> None:
    archive_path, identity, expectations = _write_source(tmp_path, nullable_context=True)

    result = _validate_fixture(archive_path, identity, expectations)

    assert np.isnan(result.scalars.values["context"][0])
    assert result.scalars.values["context"][1] == 5.0


def test_acquisition_result_reaches_validation_and_is_reconciled(tmp_path: Path) -> None:
    archive_path, identity, expectations = _write_source(tmp_path)
    content = archive_path.read_bytes()
    config_path = tmp_path / "config.yaml"
    manifest_path = tmp_path / "manifest.json"
    config_path.write_text(
        "\n".join(
            (
                "dataset: injection_molding",
                "stage: mvp",
                "enabled: false",
                "source_url: https://github.com/sc4t1m/scatimdata",
                f"version: {identity.source_version}",
                "",
            )
        ),
        encoding="utf-8",
    )
    download_url = (
        "https://raw.githubusercontent.com/sc4t1m/scatimdata/"
        f"{identity.source_version}/dataset2.zip"
    )
    manifest_path.write_text(
        json.dumps(
            {
                "dataset": "injection_molding",
                "source": {
                    "repository_url": identity.repository_url,
                    "source_version": identity.source_version,
                },
                "files": [
                    {
                        "candidate": "dataset2",
                        "source_path": "dataset2.zip",
                        "immutable_download_url": download_url,
                        "bytes": len(content),
                        "sha256": hashlib.sha256(content).hexdigest(),
                        "admitted": True,
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    @contextmanager
    def transport(url: str, timeout: float) -> Generator[io.BytesIO, None, None]:
        assert url == download_url
        assert timeout > 0
        yield io.BytesIO(content)

    raw_root = tmp_path / "raw"
    acquisition = acquire_injection_molding(
        raw_root=raw_root,
        config_path=config_path,
        manifest_path=manifest_path,
        transport=transport,
    )
    acquired_identity = replace(identity, download_url=download_url)
    manifest_sha256 = hashlib.sha256(manifest_path.read_bytes()).hexdigest()

    result = _validate_acquired(
        acquisition,
        identity=acquired_identity,
        expected_path=acquisition.archive_path,
        manifest_sha256=manifest_sha256,
        expectations=expectations,
    )

    assert result.receipt_path == acquisition.receipt_path
    unrelated_receipt = acquisition.receipt_path.parent / "acquisition-unrelated.json"
    unrelated_receipt.write_text("{}", encoding="utf-8")
    unrelated_result = _validate_path(
        acquisition.archive_path,
        acquired_identity,
        manifest_sha256,
        unrelated_receipt,
        expectations,
    )
    assert unrelated_result.receipt_path is None
    stale = replace(acquisition, sha256="0" * 64)
    with pytest.raises(RawValidationError, match=r"check=handoff\.identity"):
        _validate_acquired(
            stale,
            identity=acquired_identity,
            expected_path=acquisition.archive_path,
            manifest_sha256=manifest_sha256,
            expectations=expectations,
        )
    receipt_bytes = acquisition.receipt_path.read_bytes()
    acquisition.archive_path.write_bytes(content + b"changed-after-acquisition")
    with pytest.raises(RawValidationError, match=r"check=archive\.identity"):
        _validate_acquired(
            acquisition,
            identity=acquired_identity,
            expected_path=acquisition.archive_path,
            manifest_sha256=manifest_sha256,
            expectations=expectations,
        )
    assert acquisition.receipt_path.read_bytes() == receipt_bytes
    assert acquisition.archive_path.read_bytes().endswith(b"changed-after-acquisition")


def test_local_validation_does_not_discover_unrelated_receipt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    archive_path, identity, expectations = _write_source(tmp_path)
    content = archive_path.read_bytes()
    config_path = tmp_path / "local-config.yaml"
    manifest_path = tmp_path / "local-manifest.json"
    raw_root = tmp_path / "local-raw"
    version_dir = raw_root / f"scatimdata-{identity.source_version}"
    receipts_dir = version_dir / "receipts"
    receipts_dir.mkdir(parents=True)
    (version_dir / "dataset2.zip").write_bytes(content)
    (receipts_dir / "acquisition-ffffffff.json").write_text("{}", encoding="utf-8")
    config_path.write_text(
        "\n".join(
            (
                "dataset: injection_molding",
                "stage: mvp",
                "enabled: false",
                "source_url: https://github.com/sc4t1m/scatimdata",
                f"version: {identity.source_version}",
                "",
            )
        ),
        encoding="utf-8",
    )
    download_url = (
        "https://raw.githubusercontent.com/sc4t1m/scatimdata/"
        f"{identity.source_version}/dataset2.zip"
    )
    manifest_path.write_text(
        json.dumps(
            {
                "dataset": "injection_molding",
                "source": {
                    "repository_url": identity.repository_url,
                    "source_version": identity.source_version,
                },
                "files": [
                    {
                        "candidate": "dataset2",
                        "source_path": "dataset2.zip",
                        "immutable_download_url": download_url,
                        "bytes": len(content),
                        "sha256": hashlib.sha256(content).hexdigest(),
                        "admitted": True,
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    def fixture_expectations() -> _Expectations:
        return expectations

    monkeypatch.setattr(injection_molding_validation, "_Expectations", fixture_expectations)
    result = injection_molding_validation.validate_injection_molding(
        raw_root=raw_root,
        config_path=config_path,
        manifest_path=manifest_path,
    )

    assert result.receipt_path is None


def test_changed_archive_is_rejected_before_zip_read_and_preserved(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    archive_path, identity, expectations = _write_source(tmp_path)
    changed = archive_path.read_bytes() + b"changed"
    archive_path.write_bytes(changed)

    def fail_if_zip_parser_runs(*_args: object, **_kwargs: object) -> Path:
        pytest.fail("ZIP parser reached before identity rejection")

    monkeypatch.setattr(
        injection_molding_validation,
        "_copy_member",
        fail_if_zip_parser_runs,
    )

    with pytest.raises(RawValidationError, match=r"check=archive\.identity"):
        _validate_fixture(archive_path, identity, expectations)

    assert archive_path.read_bytes() == changed


@pytest.mark.parametrize("kind", ["missing", "duplicate"])
def test_requires_exactly_one_named_member(tmp_path: Path, kind: str) -> None:
    archive_path, identity, expectations = _write_source(
        tmp_path,
        missing_member=kind == "missing",
        duplicate_member=kind == "duplicate",
    )
    with pytest.raises(RawValidationError, match=r"check=zip\.member"):
        _validate_fixture(archive_path, identity, expectations)


def test_rejects_fractional_source_identity(tmp_path: Path) -> None:
    archive_path, identity, expectations = _write_source(tmp_path, fractional_cycle=True)
    with pytest.raises(RawValidationError, match=r"check=scalars\.cycle_counter"):
        _validate_fixture(archive_path, identity, expectations)


def test_rejects_equal_count_but_mismatched_signal_sets(tmp_path: Path) -> None:
    archive_path, identity, expectations = _write_source(tmp_path, flow_cycles=(21, 23, 20))
    with pytest.raises(RawValidationError, match=r"check=joins\.signal_sets"):
        _validate_fixture(archive_path, identity, expectations)


def test_rejects_duplicate_signal_identity(tmp_path: Path) -> None:
    archive_path, identity, expectations = _write_source(tmp_path, pressure_cycles=(22, 20, 20))
    with pytest.raises(RawValidationError, match=r"check=signals\.Einspritzdruck\.representation"):
        _validate_fixture(archive_path, identity, expectations)


def test_rejects_duplicate_decoded_cycle_identity(tmp_path: Path) -> None:
    archive_path, identity, expectations = _write_source(tmp_path, duplicate_decoded_cycle=True)
    with pytest.raises(RawValidationError, match=r"check=signals\.Einspritzdruck\.cycles"):
        _validate_fixture(archive_path, identity, expectations)


def test_rejects_unrecognized_signal_column(tmp_path: Path) -> None:
    archive_path, identity, expectations = _write_source(tmp_path, unexpected_signal_column=True)
    with pytest.raises(RawValidationError, match=r"check=signals\.Einspritzdruck\.columns"):
        _validate_fixture(archive_path, identity, expectations)


def test_rejects_malformed_fixed_format_block_and_cleans_extract(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    archive_path, identity, expectations = _write_source(tmp_path, malformed_signal_block=True)
    extracts = _track_production_extracts(monkeypatch)
    with pytest.raises(RawValidationError, match=r"check=signals\.Einspritzdruck\.representation"):
        _validate_fixture(archive_path, identity, expectations)
    assert len(extracts) == 1
    assert all(not path.exists() for path in extracts)


def test_rejects_missing_quality_target(tmp_path: Path) -> None:
    archive_path, identity, expectations = _write_source(tmp_path, missing_weight=True)
    with pytest.raises(RawValidationError, match=r"check=scalars\.missingness"):
        _validate_fixture(archive_path, identity, expectations)


def test_rejects_grid_mismatch(tmp_path: Path) -> None:
    archive_path, identity, expectations = _write_source(tmp_path, times=(0.0, 0.006, 0.013, 0.019))
    with pytest.raises(RawValidationError, match="time_grid"):
        _validate_fixture(archive_path, identity, expectations)


def test_rejects_experiment_order_change(tmp_path: Path) -> None:
    archive_path, identity, expectations = _write_source(tmp_path, experiments=(8, 7))
    with pytest.raises(RawValidationError, match=r"check=scalars\.experiments"):
        _validate_fixture(archive_path, identity, expectations)


def test_rejects_external_links(tmp_path: Path) -> None:
    archive_path, identity, expectations = _write_source(tmp_path, external_link=True)
    with pytest.raises(RawValidationError, match=r"check=hdf\.external_links"):
        _validate_fixture(archive_path, identity, expectations)


def test_rejects_group_where_fixed_frame_requires_dataset(tmp_path: Path) -> None:
    archive_path, identity, expectations = _write_source(tmp_path, malformed_axis_group=True)

    with pytest.raises(RawValidationError, match=r"check=signals\.Einspritzdruck\.representation"):
        _validate_fixture(archive_path, identity, expectations)


def test_rejects_external_numeric_storage_before_payload_access(tmp_path: Path) -> None:
    archive_path, identity, expectations = _write_source(tmp_path, external_numeric_storage=True)

    with pytest.raises(RawValidationError, match=r"check=hdf\.external_storage"):
        _validate_fixture(archive_path, identity, expectations)


def test_owned_extract_is_cleaned_on_handled_interruption(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    archive_path, identity, expectations = _write_source(tmp_path)
    extracts = _track_production_extracts(monkeypatch)

    def interrupt_reader(*_args: object, **_kwargs: object) -> None:
        raise KeyboardInterrupt

    monkeypatch.setattr(injection_molding_validation, "_read_hdf", interrupt_reader)
    with pytest.raises(KeyboardInterrupt):
        _validate_fixture(archive_path, identity, expectations)
    assert len(extracts) == 1
    assert all(not path.exists() for path in extracts)


def test_archive_mutation_during_validation_reaches_stability_check(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    archive_path, identity, expectations = _write_source(tmp_path)
    original_reader = injection_molding_validation._read_hdf
    original_bytes = archive_path.read_bytes()

    def mutating_reader(path: Path, expectations: _Expectations):
        result = original_reader(path, expectations)
        archive_path.write_bytes(original_bytes + b"changed-during-validation")
        return result

    monkeypatch.setattr(injection_molding_validation, "_read_hdf", mutating_reader)
    with pytest.raises(RawValidationError, match=r"check=archive\.stability"):
        _validate_fixture(archive_path, identity, expectations)
    assert archive_path.read_bytes().endswith(b"changed-during-validation")
