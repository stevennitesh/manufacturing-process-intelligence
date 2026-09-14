# pyright: reportMissingTypeStubs=false, reportUnknownArgumentType=false
# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false
"""Source-native validation for the pinned injection-molding Dataset 2 archive."""

from __future__ import annotations

import hashlib
import json
import re
import tempfile
import zipfile
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import BinaryIO, NoReturn, cast

import h5py
import numpy as np
import numpy.typing as npt

from mpi import __version__
from mpi.datasets.injection_molding import (
    DEFAULT_CONFIG_PATH,
    DEFAULT_MANIFEST_PATH,
    DEFAULT_RAW_ROOT,
    ArchiveIdentity,
    ResolvedArchiveInputs,
    resolve_archive_destination,
    resolve_archive_inputs,
)

HDF_MEMBER = "dataset2/dynamic_data_versuch_large.h5"
HDF_MEMBER_SIZE = 91_270_248
SCALAR_COLUMNS = (
    "Versuch",
    "mittlerer Feuchtegehalt",
    "Twkz",
    "Charge",
    "cycle_counter",
    "cycle_time",
    "Max. Spritzdruck",
    "Umschaltspritzdruck",
    "staudruck_ist",
    "einspritzzeit",
    "Massepolster",
    "dosierzeit",
    "zylinderheizzone_1",
    "zylinderheizzone_2",
    "zylinderheizzone_3",
    "zylinderheizzone_4",
    "zylinderheizzone_5",
    "zylinderheizzone_6",
    "zylinderheizzone_7",
    "zylinderheizzone_8",
    "werkzeugheizkreis_1",
    "integral_idx_0_werkzeuginnendruck_ist_state_1",
    "integral_idx_0_werkzeuginnendruck_ist_state_2",
    "integral_idx_0_werkzeuginnendruck_ist_state_8",
    "integral_idx_0_messgrafik_state_1",
    "integral_idx_0_messgrafik_state_2",
    "integral_idx_0_messgrafik_state_8",
    "integral_idx_1_messgrafik_state_1",
    "integral_idx_1_messgrafik_state_2",
    "integral_idx_1_messgrafik_state_8",
    "integral_idx_0_einspritzdruck_ist_state_1",
    "integral_idx_0_einspritzdruck_ist_state_2",
    "integral_idx_0_einspritzdruck_ist_state_8",
    "integral_idx_0_einspritzstrom_ist_state_1",
    "integral_idx_0_einspritzstrom_ist_state_2",
    "integral_idx_0_einspritzstrom_ist_state_8",
    "weight",
    "GE-GE002*",
    "GERADEHEIT-L*",
    "PT-PT002L*",
)
SCALAR_DTYPES = tuple(
    (name, "int64" if name == "Versuch" else "int32")
    if name in {"Versuch", "cycle_counter", "GE-GE002*", "GERADEHEIT-L*"}
    else (name, "float64")
    for name in SCALAR_COLUMNS
)
OPTIONAL_GROUPS = (
    "Werkzeuginnendruck",
    "Einspritzdruck_states",
    "Einspritzstrom_states",
    "Werkzeuginnendruck_states",
)
LIMITATIONS = (
    "Geometry storage units are unresolved; no geometry unit conversion was applied.",
    "Machine-native scalar and signal units are unresolved.",
    "Quality specification limits are absent; no conformance verdict was inferred.",
    "Versuch is an experiment boundary, not an authoritative production-day label.",
    "Optional cavity-pressure and state groups were inventoried but not decoded.",
)
_SIGNAL_PATTERNS = {
    "Einspritzdruck": re.compile(r"einspritzdruck_ist_(\d+)\Z"),
    "Einspritzstrom": re.compile(r"einspritzstrom_ist_(\d+)\Z"),
}


class RawValidationError(RuntimeError):
    """A pinned raw-source validation check failed."""

    def __init__(
        self,
        check_id: str,
        message: str,
        *,
        expected: object | None = None,
        observed: object | None = None,
    ) -> None:
        details = [f"check={check_id}", message]
        if expected is not None:
            details.append(f"expected={expected!r}")
        if observed is not None:
            details.append(f"observed={observed!r}")
        super().__init__("; ".join(details))
        self.check_id = check_id
        self.expected = expected
        self.observed = observed


@dataclass(frozen=True)
class ValidationCheck:
    """Structured evidence for one successful validation boundary."""

    check_id: str
    expected: str
    observed: str


@dataclass(frozen=True)
class SourceScalarTable:
    """Full source scalar/quality table in source row and field order."""

    columns: tuple[str, ...]
    values: Mapping[str, npt.NDArray[np.generic]]
    cycle_ids: tuple[int, ...]


@dataclass(frozen=True)
class SourceSignalMatrix:
    """A required source signal with explicit axis and cycle mapping."""

    group: str
    source_columns: tuple[str, ...]
    cycle_ids: tuple[int, ...]
    cycle_to_column: Mapping[int, int]
    time_seconds: npt.NDArray[np.float64]
    values: npt.NDArray[np.float64]


@dataclass(frozen=True)
class ValidatedReceiptInfo:
    """Identity-validated receipt facts carried through preparation."""

    path: Path
    downloaded_at_utc: str | None
    chronology_utc: str


@dataclass(frozen=True)
class ValidatedInjectionMoldingSource:
    """Usable source-native handoff after all pinned checks pass."""

    dataset: str
    candidate: str
    source_version: str
    archive_path: Path
    archive_size: int
    archive_sha256: str
    manifest_sha256: str
    project_version: str
    receipt_path: Path | None
    receipt_downloaded_at_utc: str | None
    scalars: SourceScalarTable
    signals: Mapping[str, SourceSignalMatrix]
    matched_cycle_ids: tuple[int, ...]
    labeled_only_cycle_ids: tuple[int, ...]
    signal_only_cycle_ids: tuple[int, ...]
    optional_groups: tuple[str, ...]
    checks: tuple[ValidationCheck, ...]
    limitations: tuple[str, ...]


@dataclass(frozen=True)
class _Expectations:
    scalar_columns: tuple[str, ...] = SCALAR_COLUMNS
    scalar_dtypes: tuple[tuple[str, str], ...] = SCALAR_DTYPES
    scalar_rows: int = 829
    signal_cycles: int = 921
    signal_rows: int = 2048
    member_size: int = HDF_MEMBER_SIZE
    missingness: tuple[tuple[str, int], ...] = (
        ("Charge", 526),
        ("Twkz", 526),
        ("mittlerer Feuchtegehalt", 303),
        ("PT-PT002L*", 303),
    )
    experiment_blocks: tuple[tuple[int, int, int, int], ...] = (
        (20, 223, 20627, 20897),
        (23, 303, 20933, 21235),
        (15, 303, 20191, 20528),
    )
    matched: int = 829
    signal_only: int = 92


def _fail(
    check_id: str,
    message: str,
    expected: object | None = None,
    observed: object | None = None,
) -> NoReturn:
    raise RawValidationError(check_id, message, expected=expected, observed=observed)


def _readonly(array: npt.NDArray[np.generic]) -> npt.NDArray[np.generic]:
    contiguous = np.ascontiguousarray(array)
    immutable = np.frombuffer(contiguous.tobytes(), dtype=contiguous.dtype).reshape(
        contiguous.shape
    )
    return immutable


def _decode_strings(dataset: h5py.Dataset) -> tuple[str, ...]:
    if dataset.ndim != 1 or dataset.dtype.kind not in {"S", "U"}:
        _fail(
            "hdf.representation", f"{dataset.name} is not a fixed string axis", "S/U", dataset.dtype
        )
    values = dataset[...].tolist()
    try:
        return tuple(
            value.decode("utf-8") if isinstance(value, bytes) else str(value) for value in values
        )
    except UnicodeError as error:
        raise RawValidationError(
            "hdf.representation", f"invalid UTF-8 in {dataset.name}"
        ) from error


def _require_dataset(group: h5py.Group, name: str, check_id: str) -> h5py.Dataset:
    item = group[name]
    if not isinstance(item, h5py.Dataset):
        _fail(
            check_id, f"{group.name}/{name} must be an HDF5 dataset", "Dataset", type(item).__name__
        )
    return item


def _read_frame(
    group: h5py.Group, check_id: str
) -> tuple[tuple[str, ...], dict[str, npt.NDArray[np.generic]]]:
    required_base = {"axis0", "axis1"}
    if not required_base.issubset(group.keys()):
        _fail(check_id, f"{group.name} lacks frame axes", required_base, set(group.keys()))
    nblocks_value = group.attrs.get("nblocks")
    if not isinstance(nblocks_value, (int, np.integer)) or int(nblocks_value) <= 0:
        _fail(check_id, f"{group.name} has invalid nblocks", "positive integer", nblocks_value)
    nblocks = int(nblocks_value)
    expected_keys = required_base | {
        item for index in range(nblocks) for item in (f"block{index}_items", f"block{index}_values")
    }
    if set(group.keys()) != expected_keys:
        _fail(
            check_id,
            f"{group.name} has unsupported fixed-frame members",
            sorted(expected_keys),
            sorted(group.keys()),
        )
    columns = _decode_strings(_require_dataset(group, "axis0", check_id))
    if len(columns) != len(set(columns)):
        _fail(check_id, f"{group.name} contains duplicate axis0 fields")
    row_axis = _require_dataset(group, "axis1", check_id)
    if row_axis.ndim != 1 or row_axis.dtype.kind not in "iu":
        _fail(check_id, f"{row_axis.name} must be a one-dimensional integer axis")
    row_count = int(row_axis.shape[0])
    by_column: dict[str, npt.NDArray[np.generic]] = {}
    block_items: list[str] = []
    for index in range(nblocks):
        items_dataset = _require_dataset(group, f"block{index}_items", check_id)
        items = _decode_strings(items_dataset)
        values_dataset = _require_dataset(group, f"block{index}_values", check_id)
        if items_dataset.ndim != 1:
            _fail(check_id, f"{group.name}/block{index}_items must be one-dimensional")
        if values_dataset.dtype.kind not in "biufc" or values_dataset.dtype.hasobject:
            _fail(
                check_id,
                f"{values_dataset.name} is not a supported numeric block",
                "numeric non-object",
                values_dataset.dtype,
            )
        if values_dataset.ndim != 2 or values_dataset.shape != (row_count, len(items)):
            _fail(
                check_id,
                f"{values_dataset.name} dimensions do not match its axes",
                (row_count, len(items)),
                values_dataset.shape,
            )
        block = values_dataset[...]
        for column_index, name in enumerate(items):
            if name in by_column:
                _fail(check_id, f"column {name!r} appears in more than one block")
            by_column[name] = _readonly(np.asarray(block[:, column_index]))
        block_items.extend(items)
    if len(block_items) != len(set(block_items)) or set(block_items) != set(columns):
        _fail(
            check_id,
            f"{group.name} block items do not cover axis0 one-to-one",
            columns,
            tuple(block_items),
        )
    return columns, by_column


def _integral_ids(values: npt.NDArray[np.generic], field: str, check_id: str) -> tuple[int, ...]:
    if values.dtype.kind not in "iu":
        _fail(check_id, f"{field} must use an integer source dtype", "integer", values.dtype)
    result = tuple(int(value) for value in values.tolist())
    if len(result) != len(set(result)) and field == "cycle_counter":
        _fail(check_id, f"{field} contains duplicate identities")
    return result


def _expected_time_grid(rows: int) -> npt.NDArray[np.float64]:
    increments = np.full(rows - 1, 0.006, dtype=np.float64)
    for destination in (512, 1024, 1536):
        if destination < rows:
            increments[destination - 1] = 0.004
    return np.concatenate((np.array([0.0]), np.cumsum(increments)))


def expected_injection_molding_time_grid(rows: int) -> npt.NDArray[np.float64]:
    """Return the pinned native Dataset 2 elapsed-time grid for a row count."""
    return _expected_time_grid(rows)


def _read_signal(group: h5py.Group, name: str, expectations: _Expectations) -> SourceSignalMatrix:
    columns, values = _read_frame(group, f"signals.{name}.representation")
    if columns.count("time") != 1 or columns[0] != "time":
        _fail(f"signals.{name}.columns", "signal frame must begin with exactly one time column")
    pattern = _SIGNAL_PATTERNS[name]
    source_columns = columns[1:]
    if any(values[column].dtype != np.dtype("float64") for column in columns):
        _fail(f"signals.{name}.dtypes", "required signal fields must retain float64 dtype")
    cycle_ids: list[int] = []
    for column in source_columns:
        match = pattern.fullmatch(column)
        if match is None:
            _fail(f"signals.{name}.columns", f"unrecognized signal column {column!r}")
        cycle_ids.append(int(match.group(1)))
    if len(cycle_ids) != expectations.signal_cycles or len(set(cycle_ids)) != len(cycle_ids):
        _fail(
            f"signals.{name}.cycles",
            "signal cycle identity count is wrong or duplicated",
            expectations.signal_cycles,
            len(set(cycle_ids)),
        )
    time = np.asarray(values["time"], dtype=np.float64)
    matrix = np.column_stack([values[column] for column in source_columns]).astype(
        np.float64, copy=False
    )
    if matrix.shape != (expectations.signal_rows, expectations.signal_cycles):
        _fail(
            f"signals.{name}.shape",
            "signal shape mismatch",
            (expectations.signal_rows, expectations.signal_cycles),
            matrix.shape,
        )
    if not np.isfinite(time).all() or not np.isfinite(matrix).all():
        _fail(f"signals.{name}.finite", "signal axis or values contain nonfinite cells")
    expected_time = _expected_time_grid(expectations.signal_rows)
    if time.shape != expected_time.shape or not np.allclose(
        time, expected_time, rtol=0.0, atol=1e-9
    ):
        mismatch = (
            int(np.flatnonzero(~np.isclose(time, expected_time, rtol=0.0, atol=1e-9))[0])
            if time.shape == expected_time.shape
            else None
        )
        _fail(
            f"signals.{name}.time_grid",
            "elapsed-time grid mismatch",
            f"{expectations.signal_rows} pinned values",
            f"shape={time.shape}, first_mismatch={mismatch}",
        )
    time = cast(npt.NDArray[np.float64], _readonly(time))
    matrix = cast(npt.NDArray[np.float64], _readonly(matrix))
    return SourceSignalMatrix(
        group=name,
        source_columns=source_columns,
        cycle_ids=tuple(cycle_ids),
        cycle_to_column=MappingProxyType({cycle: index for index, cycle in enumerate(cycle_ids)}),
        time_seconds=time,
        values=matrix,
    )


def _validate_scalars(group: h5py.Group, expectations: _Expectations) -> SourceScalarTable:
    columns, values = _read_frame(group, "scalars.representation")
    if columns != expectations.scalar_columns:
        _fail(
            "scalars.schema",
            "scalar fields or order differ from the pinned schema",
            expectations.scalar_columns,
            columns,
        )
    if any(value.shape != (expectations.scalar_rows,) for value in values.values()):
        _fail("scalars.shape", "scalar row count mismatch", expectations.scalar_rows)
    cycles = _integral_ids(values["cycle_counter"], "cycle_counter", "scalars.cycle_counter")
    experiments = _integral_ids(values["Versuch"], "Versuch", "scalars.experiments")
    observed_dtypes = tuple((name, str(values[name].dtype)) for name in columns)
    if observed_dtypes != expectations.scalar_dtypes:
        _fail(
            "scalars.dtypes",
            "scalar source dtypes differ from the pinned schema",
            expectations.scalar_dtypes,
            observed_dtypes,
        )
    expected_missing = dict(expectations.missingness)
    observed_missing: dict[str, int] = {}
    for name in columns:
        column = values[name]
        if column.dtype.kind == "f":
            missing = int(np.isnan(column).sum())
            finite_or_missing = np.isfinite(column) | np.isnan(column)
            if not finite_or_missing.all():
                _fail("scalars.finite", f"{name} contains infinite values")
        else:
            missing = 0
        if missing:
            observed_missing[name] = missing
    if observed_missing != expected_missing:
        _fail(
            "scalars.missingness",
            "source null counts differ from the pinned contract",
            expected_missing,
            observed_missing,
        )
    offset = 0
    observed_blocks: list[tuple[int, int, int, int]] = []
    for experiment, expected_rows, _, _ in expectations.experiment_blocks:
        end = offset + expected_rows
        block_experiments = experiments[offset:end]
        block_cycles = cycles[offset:end]
        if len(block_cycles) != expected_rows or set(block_experiments) != {experiment}:
            _fail("scalars.experiments", "experiment blocks differ in source order")
        observed_blocks.append(
            (experiment, len(block_cycles), min(block_cycles), max(block_cycles))
        )
        offset = end
    if offset != len(cycles) or tuple(observed_blocks) != expectations.experiment_blocks:
        _fail(
            "scalars.experiments",
            "experiment counts or cycle ranges differ",
            expectations.experiment_blocks,
            observed_blocks,
        )
    return SourceScalarTable(columns=columns, values=MappingProxyType(values), cycle_ids=cycles)


def _read_hdf(
    path: Path, expectations: _Expectations
) -> tuple[SourceScalarTable, Mapping[str, SourceSignalMatrix], tuple[str, ...]]:
    try:
        with h5py.File(path, "r") as hdf:
            expected_groups = {"scalars", "Einspritzdruck", "Einspritzstrom", *OPTIONAL_GROUPS}
            if set(hdf.keys()) != expected_groups or not all(
                isinstance(hdf[name], h5py.Group) for name in hdf
            ):
                _fail(
                    "hdf.inventory",
                    "top-level HDF5 inventory differs",
                    sorted(expected_groups),
                    sorted(hdf.keys()),
                )
            scalars = _validate_scalars(cast(h5py.Group, hdf["scalars"]), expectations)
            signals = {
                name: _read_signal(cast(h5py.Group, hdf[name]), name, expectations)
                for name in ("Einspritzdruck", "Einspritzstrom")
            }
    except RawValidationError:
        raise
    except (OSError, KeyError, ValueError) as error:
        raise RawValidationError(
            "hdf.read", f"could not safely decode {HDF_MEMBER}: {error}"
        ) from error
    return scalars, MappingProxyType(signals), OPTIONAL_GROUPS


def _copy_member(archive_stream: BinaryIO, expectations: _Expectations) -> Path:
    temporary_path: Path | None = None
    try:
        archive_stream.seek(0)
        with zipfile.ZipFile(archive_stream) as archive:
            infos = archive.infolist()
            named = [info for info in infos if info.filename == HDF_MEMBER]
            if len(named) != 1 or len(infos) != 1 or infos[0].is_dir():
                _fail(
                    "zip.member",
                    "archive must contain exactly the pinned HDF5 member",
                    [HDF_MEMBER],
                    [info.filename for info in infos],
                )
            info = named[0]
            if info.flag_bits & 0x1:
                _fail("zip.member", "encrypted ZIP members are unsupported")
            if info.file_size != expectations.member_size:
                _fail(
                    "zip.member_size",
                    "expanded member size differs",
                    expectations.member_size,
                    info.file_size,
                )
            with tempfile.NamedTemporaryFile(suffix=".h5", delete=False) as target:
                temporary_path = Path(target.name)
                copied = 0
                with archive.open(info, "r") as source:
                    while chunk := source.read(1024 * 1024):
                        copied += len(chunk)
                        if copied > expectations.member_size:
                            _fail("zip.member_size", "expanded member exceeded pinned size")
                        target.write(chunk)
            if copied != expectations.member_size:
                _fail(
                    "zip.member_size",
                    "expanded member was truncated",
                    expectations.member_size,
                    copied,
                )
            return temporary_path
    except RawValidationError:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)
        raise
    except (OSError, zipfile.BadZipFile, RuntimeError) as error:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)
        raise RawValidationError(
            "zip.read", f"could not safely read {HDF_MEMBER}: {error}"
        ) from error
    except BaseException:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)
        raise


def _measure_stream(stream: BinaryIO) -> tuple[int, str]:
    stream.seek(0)
    digest = hashlib.sha256()
    size = 0
    while chunk := stream.read(1024 * 1024):
        size += len(chunk)
        digest.update(chunk)
    return size, digest.hexdigest()


def _validated_receipt(
    receipt_path: Path | None,
    *,
    archive_path: Path,
    identity: ArchiveIdentity,
    manifest_sha256: str,
) -> ValidatedReceiptInfo | None:
    if receipt_path is None or receipt_path.is_symlink() or not receipt_path.is_file():
        return None
    try:
        resolved_receipt = receipt_path.resolve(strict=True)
        if resolved_receipt.parent != archive_path.parent / "receipts":
            return None
        raw: object = json.loads(resolved_receipt.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if not isinstance(raw, dict) or not all(isinstance(key, str) for key in raw):
        return None
    receipt = cast(dict[str, object], raw)
    expected: dict[str, object] = {
        "dataset": identity.dataset,
        "candidate": identity.candidate,
        "source_version": identity.source_version,
        "source_path": identity.source_path,
        "size": identity.size,
        "sha256": identity.sha256,
        "expected_size": identity.size,
        "expected_sha256": identity.sha256,
        "observed_size": identity.size,
        "observed_sha256": identity.sha256,
        "archive_path": str(archive_path),
        "manifest_sha256": manifest_sha256,
    }
    if any(receipt.get(field) != value for field, value in expected.items()):
        return None
    downloaded = receipt.get("downloaded_at_utc")
    verified = receipt.get("verified_at_utc")
    if isinstance(downloaded, str) and downloaded:
        return ValidatedReceiptInfo(resolved_receipt, downloaded, downloaded)
    if isinstance(verified, str) and verified:
        return ValidatedReceiptInfo(resolved_receipt, None, verified)
    return None


def _discover_validated_receipt(
    archive_path: Path,
    *,
    identity: ArchiveIdentity,
    manifest_sha256: str,
) -> ValidatedReceiptInfo | None:
    """Select a valid acquisition receipt, preferring true download chronology."""
    receipts_dir = archive_path.parent / "receipts"
    if receipts_dir.is_symlink() or not receipts_dir.is_dir():
        return None
    candidates: list[ValidatedReceiptInfo] = []
    try:
        receipt_paths = tuple(receipts_dir.glob("*.json"))
    except OSError:
        return None
    for receipt_path in receipt_paths:
        validated = _validated_receipt(
            receipt_path,
            archive_path=archive_path,
            identity=identity,
            manifest_sha256=manifest_sha256,
        )
        if validated is None:
            continue
        candidates.append(validated)
    if not candidates:
        return None
    preferred = [item for item in candidates if item.downloaded_at_utc is not None] or candidates
    return max(preferred, key=lambda item: (item.chronology_utc, str(item.path)))


def _validate_path(
    archive_path: Path,
    identity: ArchiveIdentity,
    manifest_sha256: str,
    receipt: ValidatedReceiptInfo | None,
    expectations: _Expectations,
) -> ValidatedInjectionMoldingSource:
    if archive_path.is_symlink() or not archive_path.is_file():
        _fail(
            "archive.present",
            "acquired archive is absent or not a regular file",
            identity.source_path,
            archive_path,
        )
    temporary_path: Path | None = None
    try:
        with archive_path.open("rb") as archive_stream:
            size, sha256 = _measure_stream(archive_stream)
            if (size, sha256) != (identity.size, identity.sha256):
                _fail(
                    "archive.identity",
                    "raw bytes do not match the manifest",
                    (identity.size, identity.sha256),
                    (size, sha256),
                )
            temporary_path = _copy_member(archive_stream, expectations)
            scalars, signals, optional_groups = _read_hdf(temporary_path, expectations)
    except RawValidationError:
        raise
    except OSError as error:
        raise RawValidationError(
            "archive.read", f"could not read {archive_path}: {error}"
        ) from error
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)

    pressure = signals["Einspritzdruck"]
    flow = signals["Einspritzstrom"]
    pressure_set = set(pressure.cycle_ids)
    flow_set = set(flow.cycle_ids)
    if pressure_set != flow_set:
        _fail(
            "joins.signal_sets",
            "required signal cycle sets differ",
            sorted(pressure_set),
            sorted(flow_set),
        )
    if not np.allclose(pressure.time_seconds, flow.time_seconds, rtol=0.0, atol=1e-9):
        _fail("joins.time_axes", "required signal time axes differ")
    scalar_set = set(scalars.cycle_ids)
    matched = tuple(cycle for cycle in scalars.cycle_ids if cycle in pressure_set)
    labeled_only = tuple(cycle for cycle in scalars.cycle_ids if cycle not in pressure_set)
    signal_only = tuple(cycle for cycle in pressure.cycle_ids if cycle not in scalar_set)
    observed_join = (len(matched), len(labeled_only), len(signal_only))
    expected_join = (expectations.matched, 0, expectations.signal_only)
    if observed_join != expected_join:
        _fail("joins.membership", "labeled/signal membership differs", expected_join, observed_join)

    checks = (
        ValidationCheck(
            "archive.identity",
            f"{identity.size} bytes / {identity.sha256}",
            f"{size} bytes / {sha256}",
        ),
        ValidationCheck(
            "zip.member",
            f"{HDF_MEMBER} ({expectations.member_size} bytes)",
            "present, CRC verified",
        ),
        ValidationCheck("hdf.representation", "numeric fixed-format frames", "passed"),
        ValidationCheck(
            "scalars.schema",
            f"{expectations.scalar_rows} rows / {len(expectations.scalar_columns)} fields",
            f"{len(scalars.cycle_ids)} rows / {len(scalars.columns)} fields",
        ),
        ValidationCheck(
            "scalars.missingness", str(dict(expectations.missingness)), "passed exactly"
        ),
        ValidationCheck(
            "signals.required",
            f"2 x {expectations.signal_rows} rows / {expectations.signal_cycles} cycles",
            "passed",
        ),
        ValidationCheck(
            "signals.time_grid", "0..12.276 s with pinned irregular increments", "passed"
        ),
        ValidationCheck(
            "joins.membership",
            f"{expectations.matched}/0/{expectations.signal_only}",
            f"{len(matched)}/{len(labeled_only)}/{len(signal_only)}",
        ),
        ValidationCheck(
            "scalars.experiments", str(expectations.experiment_blocks), "passed in source order"
        ),
    )
    return ValidatedInjectionMoldingSource(
        dataset=identity.dataset,
        candidate=identity.candidate,
        source_version=identity.source_version,
        archive_path=archive_path,
        archive_size=size,
        archive_sha256=sha256,
        manifest_sha256=manifest_sha256,
        project_version=__version__,
        receipt_path=receipt.path if receipt else None,
        receipt_downloaded_at_utc=receipt.downloaded_at_utc if receipt else None,
        scalars=scalars,
        signals=signals,
        matched_cycle_ids=matched,
        labeled_only_cycle_ids=labeled_only,
        signal_only_cycle_ids=signal_only,
        optional_groups=optional_groups,
        checks=checks,
        limitations=LIMITATIONS,
    )


def validate_injection_molding(
    *,
    raw_root: Path = DEFAULT_RAW_ROOT,
    config_path: Path = DEFAULT_CONFIG_PATH,
    manifest_path: Path = DEFAULT_MANIFEST_PATH,
) -> ValidatedInjectionMoldingSource:
    """Resolve and validate a local pinned archive without network access."""
    resolved = resolve_archive_inputs(config_path, manifest_path)
    return validate_resolved_injection_molding(raw_root=raw_root, resolved=resolved)


def validate_resolved_injection_molding(
    *,
    raw_root: Path,
    resolved: ResolvedArchiveInputs,
) -> ValidatedInjectionMoldingSource:
    """Validate a local archive using inputs resolved by the owning invocation."""
    identity = resolved.identity
    manifest_sha256 = resolved.manifest_sha256
    _, _, archive_path = resolve_archive_destination(raw_root, identity)
    resolved_archive = archive_path.resolve(strict=False)
    receipt = _discover_validated_receipt(
        resolved_archive,
        identity=identity,
        manifest_sha256=manifest_sha256,
    )
    return _validate_path(resolved_archive, identity, manifest_sha256, receipt, _Expectations())
