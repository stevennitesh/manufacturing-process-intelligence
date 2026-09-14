# pyright: reportMissingTypeStubs=false, reportPrivateUsage=false, reportUnknownMemberType=false
"""Small synthetic-source builders shared by Dataset 2 unit tests."""

from __future__ import annotations

import hashlib
import zipfile
from dataclasses import replace
from pathlib import Path

import h5py
import numpy as np

from mpi import __version__
from mpi.data.canonical import ManufacturingBundle
from mpi.datasets.injection_molding import ArchiveIdentity
from mpi.datasets.injection_molding_canonicalization import (
    SOURCE_VERSION,
    _CanonicalExpectations,
    _canonicalize_validated,
)
from mpi.datasets.injection_molding_validation import (
    HDF_MEMBER,
    SCALAR_COLUMNS,
    SCALAR_DTYPES,
    ValidatedInjectionMoldingSource,
    _Expectations,
    _expected_time_grid,
    _validate_path,
)


def _write_mixed_frame(
    hdf: h5py.File,
    name: str,
    columns: tuple[str, ...],
    values: dict[str, np.ndarray],
) -> None:
    group = hdf.create_group(name)
    group.create_dataset("axis0", data=np.asarray(columns, dtype="S64"))
    group.create_dataset("axis1", data=np.arange(len(next(iter(values.values())))))
    blocks: list[tuple[str, list[str]]] = []
    for dtype in ("float64", "int64", "int32"):
        members = [column for column in columns if str(values[column].dtype) == dtype]
        if members:
            blocks.append((dtype, members))
    group.attrs["nblocks"] = len(blocks)
    for index, (_, members) in enumerate(blocks):
        group.create_dataset(f"block{index}_items", data=np.asarray(members, dtype="S64"))
        group.create_dataset(
            f"block{index}_values", data=np.column_stack([values[item] for item in members])
        )


def _write_signal_frame(
    hdf: h5py.File,
    group_name: str,
    prefix: str,
    cycles: tuple[int, ...],
    multiplier: float,
    times: np.ndarray,
) -> None:
    columns = ("time", *(f"{prefix}_{cycle}" for cycle in cycles))
    values = {
        "time": times,
        **{
            f"{prefix}_{cycle}": cycle * multiplier + np.arange(len(times), dtype=np.float64)
            for cycle in cycles
        },
    }
    _write_mixed_frame(hdf, group_name, columns, values)


def validated_fixture(
    tmp_path: Path,
) -> tuple[ValidatedInjectionMoldingSource, _CanonicalExpectations]:
    cycles = (100, 101)
    values: dict[str, np.ndarray] = {}
    for index, (name, dtype) in enumerate(SCALAR_DTYPES):
        values[name] = np.asarray([index + 0.25, index + 1.25], dtype=dtype)
    values["Versuch"] = np.asarray([20, 23], dtype=np.int64)
    values["cycle_counter"] = np.asarray(cycles, dtype=np.int32)
    values["mittlerer Feuchtegehalt"] = np.asarray([0.086, np.nan])
    values["Twkz"] = np.asarray([np.nan, 80.0])
    values["Charge"] = np.asarray([np.nan, 1.0])
    values["weight"] = np.asarray([58.125, 58.25])
    values["GE-GE002*"] = np.asarray([101_500, 101_600], dtype=np.int32)
    values["GERADEHEIT-L*"] = np.asarray([25, 26], dtype=np.int32)
    values["PT-PT002L*"] = np.asarray([4.5, np.nan])
    hdf_path = tmp_path / "source.h5"
    times = _expected_time_grid(513)
    with h5py.File(hdf_path, "w") as hdf:
        _write_mixed_frame(hdf, "scalars", SCALAR_COLUMNS, values)
        _write_signal_frame(
            hdf, "Einspritzdruck", "einspritzdruck_ist", (102, 100, 101), 100.0, times
        )
        _write_signal_frame(
            hdf, "Einspritzstrom", "einspritzstrom_ist", (101, 102, 100), 1_000.0, times
        )
        for name in (
            "Werkzeuginnendruck",
            "Einspritzdruck_states",
            "Einspritzstrom_states",
            "Werkzeuginnendruck_states",
        ):
            hdf.create_group(name)
    archive_path = tmp_path / "dataset2.zip"
    with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.write(hdf_path, HDF_MEMBER)
    archive_bytes = archive_path.read_bytes()
    identity = ArchiveIdentity(
        dataset="injection_molding",
        candidate="dataset2",
        repository_url="https://github.com/sc4t1m/scatimdata",
        source_version=SOURCE_VERSION,
        source_path="dataset2.zip",
        download_url="https://example.invalid/dataset2.zip",
        size=len(archive_bytes),
        sha256=hashlib.sha256(archive_bytes).hexdigest(),
    )
    raw_expectations = _Expectations(
        scalar_rows=2,
        signal_cycles=3,
        signal_rows=513,
        member_size=hdf_path.stat().st_size,
        missingness=(
            ("Charge", 1),
            ("Twkz", 1),
            ("mittlerer Feuchtegehalt", 1),
            ("PT-PT002L*", 1),
        ),
        experiment_blocks=((20, 1, 100, 100), (23, 1, 101, 101)),
        matched=2,
        signal_only=1,
    )
    source = _validate_path(archive_path, identity, "a" * 64, None, raw_expectations)
    source = replace(source, project_version=__version__)
    canonical_expectations = _CanonicalExpectations(
        scalar_rows=2,
        signal_samples=513,
        signal_only=1,
        quality_nulls=1,
        experiment_blocks=((20, 1), (23, 1)),
        context_nulls=(
            ("source_charge_code", 1),
            ("mold_temperature", 1),
            ("mean_moisture_content", 1),
        ),
    )
    return source, canonical_expectations


def canonicalize_fixture(
    source: ValidatedInjectionMoldingSource,
    expectations: _CanonicalExpectations,
) -> ManufacturingBundle:
    return _canonicalize_validated(source, expectations=expectations)
