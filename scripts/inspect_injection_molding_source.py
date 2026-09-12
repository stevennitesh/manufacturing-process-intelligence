"""Inspect the pinned scatimdata source archives without preparing a dataset."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import re
import shutil
import tempfile
import zipfile
from collections import Counter
from itertools import pairwise
from pathlib import Path
from typing import Any, BinaryIO

ARCHIVES = ("dataset1.zip", "dataset2.zip", "dataset3.zip")
NULL_TOKENS = {"", "na", "nan", "null", "none"}
DEFAULT_MANIFEST = (
    Path(__file__).resolve().parents[1] / "data" / "manifests" / "injection-molding-source.json"
)


class SourceIdentityError(ValueError):
    """Raised before parsing when local source bytes do not match the manifest."""


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def verify_archive_identities(
    source_root: Path, manifest_path: Path
) -> dict[str, dict[str, int | str]]:
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise SourceIdentityError(
            f"cannot read source manifest {manifest_path}: {error}"
        ) from error

    expected: dict[str, dict[str, int | str]] = {}
    for entry in manifest.get("files", []):
        source_path = entry.get("source_path")
        if source_path in ARCHIVES:
            if source_path in expected:
                raise SourceIdentityError(
                    f"source manifest {manifest_path} repeats identity for {source_path}"
                )
            expected[source_path] = {"bytes": entry.get("bytes"), "sha256": entry.get("sha256")}

    missing_expectations = [name for name in ARCHIVES if name not in expected]
    if missing_expectations:
        raise SourceIdentityError(
            f"source manifest {manifest_path} has no identity for: "
            f"{', '.join(missing_expectations)}"
        )

    observed: dict[str, dict[str, int | str]] = {}
    for name in ARCHIVES:
        path = source_root / name
        if not path.is_file():
            raise SourceIdentityError(f"source file is missing: {path}")
        observed[name] = {"bytes": path.stat().st_size, "sha256": sha256(path)}

    for name in ARCHIVES:
        expected_identity = expected[name]
        observed_identity = observed[name]
        if observed_identity != expected_identity:
            raise SourceIdentityError(
                f"source identity mismatch for {name}: expected "
                f"bytes={expected_identity['bytes']}, sha256={expected_identity['sha256']}; "
                f"observed bytes={observed_identity['bytes']}, "
                f"sha256={observed_identity['sha256']}"
            )
    return observed


def parse_number(value: str) -> float | None:
    normalized = value.strip().lower()
    if normalized in NULL_TOKENS:
        return None
    try:
        return float(normalized.replace(",", "."))
    except ValueError:
        return None


def summarize_numbers(values: list[float]) -> dict[str, float | int | None]:
    finite = [value for value in values if math.isfinite(value)]
    return {
        "count": len(values),
        "finite_count": len(finite),
        "min": min(finite) if finite else None,
        "max": max(finite) if finite else None,
        "mean": sum(finite) / len(finite) if finite else None,
    }


def inspect_scalar_csv(handle: BinaryIO) -> dict[str, Any]:
    text = (line.decode("utf-8-sig") for line in handle)
    reader = csv.DictReader(text)
    if reader.fieldnames is None:
        raise ValueError("scalar CSV has no header")

    row_count = 0
    malformed_rows = 0
    nulls: Counter[str] = Counter()
    non_numeric: Counter[str] = Counter()
    cycle_values: list[int] = []
    value_samples: dict[str, list[float]] = {name: [] for name in reader.fieldnames}

    for row in reader:
        row_count += 1
        if None in row:
            malformed_rows += 1
        for name in reader.fieldnames:
            raw = (row.get(name) or "").strip()
            number = parse_number(raw)
            if raw.lower() in NULL_TOKENS:
                nulls[name] += 1
            elif number is None:
                non_numeric[name] += 1
            elif len(value_samples[name]) < 100_000:
                value_samples[name].append(number)
        cycle = parse_number(row.get("cycle_counter") or "")
        if cycle is not None and cycle.is_integer():
            cycle_values.append(int(cycle))

    cycle_counts = Counter(cycle_values)
    cycle_set = set(cycle_values)
    cycle_inversions = sum(right <= left for left, right in pairwise(cycle_values))
    numeric_summaries = {
        name: summarize_numbers(values)
        for name, values in value_samples.items()
        if name in {"cycle_counter", "cycle_time", "weight", "distanceA", "distanceB"}
    }
    return {
        "shape": [row_count, len(reader.fieldnames)],
        "columns": reader.fieldnames,
        "malformed_rows": malformed_rows,
        "null_counts": dict(sorted(nulls.items())),
        "non_numeric_counts": dict(sorted(non_numeric.items())),
        "cycle_key": {
            "present_count": len(cycle_values),
            "distinct_count": len(cycle_set),
            "duplicate_value_count": sum(count - 1 for count in cycle_counts.values()),
            "min": min(cycle_set) if cycle_set else None,
            "max": max(cycle_set) if cycle_set else None,
            "gap_count_within_range": (
                max(cycle_set) - min(cycle_set) + 1 - len(cycle_set) if cycle_set else None
            ),
            "non_increasing_adjacent_count": cycle_inversions,
        },
        "selected_numeric_summaries": numeric_summaries,
        "_cycle_values": sorted(cycle_set),
    }


def inspect_timeseries_csv(handle: BinaryIO) -> dict[str, Any]:
    text = (line.decode("utf-8-sig") for line in handle)
    reader = csv.reader(text)
    header = next(reader, None)
    if not header or header[0] != "time":
        raise ValueError("time-series CSV must start with a time column")

    cycle_labels = header[1:]
    cycle_counts = Counter(cycle_labels)
    time_values: list[float] = []
    null_cells = 0
    malformed_rows = 0
    for row in reader:
        if len(row) != len(header):
            malformed_rows += 1
            continue
        time = parse_number(row[0])
        if time is None:
            malformed_rows += 1
        else:
            time_values.append(time)
        null_cells += sum(value.strip().lower() in NULL_TOKENS for value in row[1:])

    rounded_deltas = [round(right - left, 12) for left, right in pairwise(time_values)]
    delta_counts = Counter(rounded_deltas)
    dominant_delta = delta_counts.most_common(1)[0][0] if delta_counts else None
    return {
        "shape": [len(time_values), len(header)],
        "cycle_column_count": len(cycle_labels),
        "cycle_distinct_count": len(cycle_counts),
        "cycle_duplicate_count": sum(count - 1 for count in cycle_counts.values()),
        "cycle_min": min(map(int, cycle_labels)) if cycle_labels else None,
        "cycle_max": max(map(int, cycle_labels)) if cycle_labels else None,
        "time_min_seconds": min(time_values) if time_values else None,
        "time_max_seconds": max(time_values) if time_values else None,
        "dominant_time_step_seconds": dominant_delta,
        "distinct_time_step_counts": dict(sorted(delta_counts.items())),
        "null_signal_cells": null_cells,
        "malformed_rows": malformed_rows,
        "_cycle_values": sorted(map(int, cycle_labels)),
    }


def join_summary(left: list[int], right: list[int]) -> dict[str, int]:
    left_set = set(left)
    right_set = set(right)
    return {
        "left_distinct": len(left_set),
        "right_distinct": len(right_set),
        "matched": len(left_set & right_set),
        "left_only": len(left_set - right_set),
        "right_only": len(right_set - left_set),
    }


def inspect_csv_archive(path: Path, dataset_number: int) -> dict[str, Any]:
    prefix = f"dataset{dataset_number}/ds{dataset_number}_"
    members = {
        "scalar_and_quality": f"{prefix}scalar_and_quality.csv",
        "injection_flow": f"{prefix}timeseries_injectionflow.csv",
        "injection_pressure": f"{prefix}timeseries_injectionpressure.csv",
    }
    with zipfile.ZipFile(path) as archive:
        with archive.open(members["scalar_and_quality"]) as handle:
            scalar = inspect_scalar_csv(handle)
        trajectories: dict[str, Any] = {}
        for role in ("injection_flow", "injection_pressure"):
            with archive.open(members[role]) as handle:
                trajectories[role] = inspect_timeseries_csv(handle)

    scalar_cycles = scalar.pop("_cycle_values")
    flow_cycles = trajectories["injection_flow"].pop("_cycle_values")
    pressure_cycles = trajectories["injection_pressure"].pop("_cycle_values")
    return {
        "members": members,
        "scalar_and_quality": scalar,
        "trajectories": trajectories,
        "joins": {
            "scalar_to_injection_flow": join_summary(scalar_cycles, flow_cycles),
            "scalar_to_injection_pressure": join_summary(scalar_cycles, pressure_cycles),
            "injection_flow_to_pressure": join_summary(flow_cycles, pressure_cycles),
        },
    }


def decoded_strings(dataset: Any) -> list[str]:
    return [
        value.decode("utf-8") if isinstance(value, bytes) else str(value)
        for value in dataset[...].tolist()
    ]


def hdf_frame_columns(group: Any) -> list[str]:
    return decoded_strings(group["axis0"])


def hdf_frame_column(group: Any, name: str) -> Any:
    for block_number in range(int(group.attrs["nblocks"])):
        items = decoded_strings(group[f"block{block_number}_items"])
        if name in items:
            return group[f"block{block_number}_values"][:, items.index(name)]
    raise KeyError(name)


def count_hdf_nulls(group: Any) -> tuple[int, dict[str, int]]:
    import numpy as np

    total = 0
    by_column: dict[str, int] = {}
    for block_number in range(int(group.attrs["nblocks"])):
        items = decoded_strings(group[f"block{block_number}_items"])
        values = group[f"block{block_number}_values"][...]
        if not np.issubdtype(values.dtype, np.floating):
            continue
        counts = np.isnan(values).sum(axis=0)
        for name, count in zip(items, counts.tolist(), strict=True):
            if count:
                by_column[name] = int(count)
                total += int(count)
    return total, by_column


def cycle_from_signal_column(name: str) -> int | None:
    match = re.search(r"_(\d+)$", name)
    return int(match.group(1)) if match else None


def inspect_hdf_archive(path: Path) -> dict[str, Any]:
    try:
        import h5py
        import numpy as np
    except ImportError as error:
        raise SystemExit(
            "dataset2 inspection requires h5py; run with `uv run --with h5py==3.16.0 ...`"
        ) from error

    member = "dataset2/dynamic_data_versuch_large.h5"
    temporary_path: Path | None = None
    try:
        with (
            zipfile.ZipFile(path) as archive,
            archive.open(member) as source,
            tempfile.NamedTemporaryFile(suffix=".h5", delete=False) as target,
        ):
            temporary_path = Path(target.name)
            shutil.copyfileobj(source, target)

        with h5py.File(temporary_path, "r") as hdf:
            scalars = hdf["scalars"]
            scalar_columns = hdf_frame_columns(scalars)
            scalar_cycles_array = hdf_frame_column(scalars, "cycle_counter")
            scalar_cycles = [int(value) for value in scalar_cycles_array.tolist()]
            scalar_shape = [int(scalars["axis1"].shape[0]), len(scalar_columns)]
            scalar_null_total, scalar_null_by_column = count_hdf_nulls(scalars)
            scalar_cycle_counts = Counter(scalar_cycles)
            scalar_cycle_inversions = sum(right <= left for left, right in pairwise(scalar_cycles))

            experiment_values = hdf_frame_column(scalars, "Versuch")
            experiment_groups: dict[str, dict[str, int]] = {}
            for experiment in np.unique(experiment_values):
                mask = experiment_values == experiment
                group_cycles = scalar_cycles_array[mask]
                experiment_groups[str(int(experiment))] = {
                    "rows": int(mask.sum()),
                    "cycle_min": int(group_cycles.min()),
                    "cycle_max": int(group_cycles.max()),
                }

            selected_columns: dict[str, Any] = {}
            for name in (
                "Versuch",
                "mittlerer Feuchtegehalt",
                "Twkz",
                "Charge",
                "weight",
                "GE-GE002*",
                "GERADEHEIT-L*",
                "PT-PT002L*",
            ):
                values = hdf_frame_column(scalars, name)
                finite = values[np.isfinite(values)]
                selected_columns[name] = {
                    "dtype": str(values.dtype),
                    "null_count": int(np.isnan(values).sum())
                    if np.issubdtype(values.dtype, np.floating)
                    else 0,
                    "distinct_finite_count": int(np.unique(finite).size),
                    "min": float(finite.min()) if finite.size else None,
                    "max": float(finite.max()) if finite.size else None,
                    "mean": float(finite.mean()) if finite.size else None,
                }

            trajectory_groups: dict[str, Any] = {}
            trajectory_cycles: dict[str, list[int]] = {}
            for name in ("Einspritzdruck", "Einspritzstrom", "Werkzeuginnendruck"):
                group = hdf[name]
                columns = hdf_frame_columns(group)
                cycles = [
                    cycle
                    for column in columns
                    if (cycle := cycle_from_signal_column(column)) is not None
                ]
                time_values = hdf_frame_column(group, "time")
                rounded_time_deltas = np.round(np.diff(time_values), decimals=12)
                delta_values, delta_counts = np.unique(rounded_time_deltas, return_counts=True)
                delta_count_map = {
                    str(float(delta)): int(count)
                    for delta, count in zip(delta_values, delta_counts, strict=True)
                }
                dominant_step = float(delta_values[int(delta_counts.argmax())])
                null_total, _ = count_hdf_nulls(group)
                trajectory_cycles[name] = cycles
                trajectory_groups[name] = {
                    "shape": [int(group["axis1"].shape[0]), len(columns)],
                    "cycle_column_count": len(cycles),
                    "cycle_distinct_count": len(set(cycles)),
                    "cycle_duplicate_count": len(cycles) - len(set(cycles)),
                    "cycle_min": min(cycles),
                    "cycle_max": max(cycles),
                    "time_min_seconds": float(time_values.min()),
                    "time_max_seconds": float(time_values.max()),
                    "dominant_time_step_seconds": dominant_step,
                    "distinct_time_step_counts": delta_count_map,
                    "null_signal_cells": null_total,
                }

            state_groups: dict[str, Any] = {}
            for name in (
                "Einspritzdruck_states",
                "Einspritzstrom_states",
                "Werkzeuginnendruck_states",
            ):
                group = hdf[name]
                columns = hdf_frame_columns(group)
                cycles = [
                    cycle
                    for column in columns
                    if (cycle := cycle_from_signal_column(column)) is not None
                ]
                values = group["block0_values"][...]
                state_groups[name] = {
                    "shape": [int(values.shape[0]), int(values.shape[1])],
                    "cycle_column_count": len(cycles),
                    "distinct_state_values": sorted(map(int, np.unique(values).tolist())),
                }

        pressure_cycles = trajectory_cycles["Einspritzdruck"]
        flow_cycles = trajectory_cycles["Einspritzstrom"]
        cavity_cycles = trajectory_cycles["Werkzeuginnendruck"]
        return {
            "member": member,
            "scalar_and_quality": {
                "shape": scalar_shape,
                "columns": scalar_columns,
                "null_cell_count": scalar_null_total,
                "null_counts": scalar_null_by_column,
                "cycle_key": {
                    "present_count": len(scalar_cycles),
                    "distinct_count": len(scalar_cycle_counts),
                    "duplicate_value_count": sum(
                        count - 1 for count in scalar_cycle_counts.values()
                    ),
                    "min": min(scalar_cycles),
                    "max": max(scalar_cycles),
                    "non_increasing_adjacent_count": scalar_cycle_inversions,
                },
                "experiment_groups": experiment_groups,
                "selected_column_summaries": selected_columns,
            },
            "trajectories": trajectory_groups,
            "states": state_groups,
            "joins": {
                "scalar_to_injection_pressure": join_summary(scalar_cycles, pressure_cycles),
                "scalar_to_injection_flow": join_summary(scalar_cycles, flow_cycles),
                "scalar_to_cavity_pressure": join_summary(scalar_cycles, cavity_cycles),
                "injection_pressure_to_flow": join_summary(pressure_cycles, flow_cycles),
                "injection_pressure_to_cavity_pressure": join_summary(
                    pressure_cycles, cavity_cycles
                ),
            },
        }
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)


def archive_members(path: Path) -> list[dict[str, Any]]:
    with zipfile.ZipFile(path) as archive:
        return [
            {
                "path": info.filename,
                "uncompressed_bytes": info.file_size,
                "compressed_bytes": info.compress_size,
            }
            for info in archive.infolist()
            if not info.is_dir()
        ]


def inspect(source_root: Path, manifest_path: Path = DEFAULT_MANIFEST) -> dict[str, Any]:
    observed_identities = verify_archive_identities(source_root, manifest_path)
    result: dict[str, Any] = {
        "source_root": str(source_root),
        "manifest": str(manifest_path),
        "archives": {},
        "datasets": {},
    }
    for name in ARCHIVES:
        path = source_root / name
        result["archives"][name] = {
            **observed_identities[name],
            "members": archive_members(path),
        }
    result["datasets"]["dataset1"] = inspect_csv_archive(source_root / "dataset1.zip", 1)
    result["datasets"]["dataset2"] = inspect_hdf_archive(source_root / "dataset2.zip")
    result["datasets"]["dataset3"] = inspect_csv_archive(source_root / "dataset3.zip", 3)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "source_root", type=Path, help="directory containing dataset1.zip to dataset3.zip"
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        default=DEFAULT_MANIFEST,
        help="source manifest containing expected archive sizes and SHA-256 hashes",
    )
    args = parser.parse_args()
    try:
        result = inspect(args.source_root.resolve(), args.manifest.resolve())
    except SourceIdentityError as error:
        parser.error(str(error))
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
