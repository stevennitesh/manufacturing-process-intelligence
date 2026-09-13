# pyright: reportMissingTypeStubs=false, reportPrivateUsage=false
# pyright: reportUnknownMemberType=false
from __future__ import annotations

import hashlib
import zipfile
from collections.abc import Mapping
from dataclasses import replace
from pathlib import Path
from types import MappingProxyType
from typing import cast

import h5py
import numpy as np
import polars as pl
import pytest

from mpi import __version__
from mpi.data.canonical import ManufacturingBundle
from mpi.datasets.injection_molding import ArchiveIdentity
from mpi.datasets.injection_molding_canonicalization import (
    SOURCE_VERSION,
    CanonicalizationError,
    _CanonicalExpectations,
    _canonicalize_validated,
)
from mpi.datasets.injection_molding_validation import (
    HDF_MEMBER,
    SCALAR_COLUMNS,
    SCALAR_DTYPES,
    SourceSignalMatrix,
    ValidatedInjectionMoldingSource,
    _Expectations,
    _expected_time_grid,
    _validate_path,
)

EXPECTED_CONTEXT = {
    "Versuch": "experiment_id",
    "mittlerer Feuchtegehalt": "mean_moisture_content",
    "Twkz": "mold_temperature",
    "Charge": "source_charge_code",
}
EXPECTED_PROCESS = {
    "cycle_time": "cycle_duration",
    "Max. Spritzdruck": "maximum_injection_pressure",
    "Umschaltspritzdruck": "switchover_injection_pressure",
    "staudruck_ist": "actual_back_pressure",
    "einspritzzeit": "injection_time",
    "Massepolster": "melt_cushion",
    "dosierzeit": "dosing_time",
    "zylinderheizzone_1": "barrel_heating_zone_1",
    "zylinderheizzone_2": "barrel_heating_zone_2",
    "zylinderheizzone_3": "barrel_heating_zone_3",
    "zylinderheizzone_4": "barrel_heating_zone_4",
    "zylinderheizzone_5": "barrel_heating_zone_5",
    "zylinderheizzone_6": "barrel_heating_zone_6",
    "zylinderheizzone_7": "barrel_heating_zone_7",
    "zylinderheizzone_8": "barrel_heating_zone_8",
    "werkzeugheizkreis_1": "mold_heating_circuit_1",
    "integral_idx_0_werkzeuginnendruck_ist_state_1": (
        "integral_idx_0_actual_cavity_pressure_state_1"
    ),
    "integral_idx_0_werkzeuginnendruck_ist_state_2": (
        "integral_idx_0_actual_cavity_pressure_state_2"
    ),
    "integral_idx_0_werkzeuginnendruck_ist_state_8": (
        "integral_idx_0_actual_cavity_pressure_state_8"
    ),
    "integral_idx_0_messgrafik_state_1": "integral_idx_0_measurement_trace_state_1",
    "integral_idx_0_messgrafik_state_2": "integral_idx_0_measurement_trace_state_2",
    "integral_idx_0_messgrafik_state_8": "integral_idx_0_measurement_trace_state_8",
    "integral_idx_1_messgrafik_state_1": "integral_idx_1_measurement_trace_state_1",
    "integral_idx_1_messgrafik_state_2": "integral_idx_1_measurement_trace_state_2",
    "integral_idx_1_messgrafik_state_8": "integral_idx_1_measurement_trace_state_8",
    "integral_idx_0_einspritzdruck_ist_state_1": "integral_idx_0_actual_injection_pressure_state_1",
    "integral_idx_0_einspritzdruck_ist_state_2": "integral_idx_0_actual_injection_pressure_state_2",
    "integral_idx_0_einspritzdruck_ist_state_8": "integral_idx_0_actual_injection_pressure_state_8",
    "integral_idx_0_einspritzstrom_ist_state_1": "integral_idx_0_actual_injection_flow_state_1",
    "integral_idx_0_einspritzstrom_ist_state_2": "integral_idx_0_actual_injection_flow_state_2",
    "integral_idx_0_einspritzstrom_ist_state_8": "integral_idx_0_actual_injection_flow_state_8",
}
EXPECTED_QUALITY = ("weight", "GE-GE002*", "GERADEHEIT-L*", "PT-PT002L*")
EXPECTED_MAPPING = {
    **{name: ("context", destination) for name, destination in EXPECTED_CONTEXT.items()},
    "cycle_counter": ("units", "cycle_counter"),
    **{name: ("process_features", destination) for name, destination in EXPECTED_PROCESS.items()},
    **{name: ("quality", name) for name in EXPECTED_QUALITY},
}


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


def _validated_fixture(
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
        missingness=(("Charge", 1), ("Twkz", 1), ("mittlerer Feuchtegehalt", 1), ("PT-PT002L*", 1)),
        experiment_blocks=((20, 1, 100, 100), (23, 1, 101, 101)),
        matched=2,
        signal_only=1,
    )
    source = _validate_path(archive_path, identity, "a" * 64, None, raw_expectations)
    source = replace(source, project_version=__version__)
    canonical_expectations = _CanonicalExpectations(
        scalar_rows=2,
        signal_cycles=3,
        signal_samples=513,
        signal_only=1,
        quality_nulls=1,
        experiment_blocks=((20, 1), (23, 1)),
        scalar_missingness=(
            ("Charge", 1),
            ("Twkz", 1),
            ("mittlerer Feuchtegehalt", 1),
            ("PT-PT002L*", 1),
        ),
        context_nulls=(
            ("source_charge_code", 1),
            ("mold_temperature", 1),
            ("mean_moisture_content", 1),
        ),
    )
    return source, canonical_expectations


def _canonicalize_fixture(
    source: ValidatedInjectionMoldingSource,
    expectations: _CanonicalExpectations,
    *,
    mapping: Mapping[str, tuple[str, str]] = EXPECTED_MAPPING,
) -> ManufacturingBundle:
    return _canonicalize_validated(
        source,
        expectations=expectations,
        mapping=mapping,
        production=False,
    )


def test_real_validator_handoff_maps_keys_values_nulls_lineage_and_evidence(tmp_path: Path) -> None:
    source, expectations = _validated_fixture(tmp_path)
    scalar_snapshots = {name: value.copy() for name, value in source.scalars.values.items()}

    bundle = _canonicalize_fixture(source, expectations)

    assert bundle.units["cycle_counter"].to_list() == [100, 101]
    assert bundle.units["source_row_index"].to_list() == [0, 1]
    assert bundle.units["batch_id"].null_count() == 2
    assert bundle.units.schema["production_time"] == pl.Datetime("us")
    assert bundle.operations["machine_id"].null_count() == 2
    assert bundle.context["experiment_id"].to_list() == [20, 23]
    assert bundle.context["production_day"].null_count() == 2
    assert bundle.context["mean_moisture_content"].to_list() == [0.086, None]
    assert bundle.process_features["cycle_duration"].to_list() == cast(
        list[float], source.scalars.values["cycle_time"].tolist()
    )
    assert "weight" not in bundle.process_features.columns
    assert bundle.quality["characteristic"].to_list() == list(EXPECTED_QUALITY) * 2
    assert bundle.quality.filter(pl.col("characteristic") == "weight")[
        "measurement_unit"
    ].to_list() == ["g", "g"]
    assert (
        bundle.quality.filter(pl.col("characteristic") != "weight")["measurement_unit"].null_count()
        == 6
    )
    assert bundle.quality["lower_spec"].null_count() == 8
    unit_100 = bundle.signals.filter(pl.col("unit_id").str.ends_with("/100"))
    assert unit_100["injection_pressure"].to_list() == pytest.approx(
        (100 * 100.0 + np.arange(513)).tolist()
    )
    assert unit_100["injection_flow"].to_list() == pytest.approx(
        (100 * 1_000.0 + np.arange(513)).tolist()
    )
    assert unit_100["elapsed_time_seconds"][512] - unit_100["elapsed_time_seconds"][
        511
    ] == pytest.approx(0.004)
    assert [
        (item.source_name, (item.canonical_section, item.canonical_name))
        for item in bundle.metadata.scalar_lineage
    ] == [(name, EXPECTED_MAPPING[name]) for name in SCALAR_COLUMNS]
    evidence_states = {item.subject: item.state for item in bundle.metadata.evidence}
    assert evidence_states["material"] == "documented_fact"
    assert evidence_states["experiment_to_paper_day"] == "inference"
    assert evidence_states["experiment_15_moisture"] == "discrepancy"
    assert evidence_states["mvp_target"] == "project_policy"
    evidence = {item.subject: item for item in bundle.metadata.evidence}
    assert evidence["optical_measurement_equipment"].quantities[0].value == 8.0
    assert evidence["optical_measurement_equipment"].quantities[0].unit == "um"
    assert evidence["weight_measurement_equipment"].quantities[0].value == 2.0
    assert evidence["weight_measurement_equipment"].quantities[0].unit == "mg"
    assert evidence["hot_runner_export_crosswalk"].state == "inference"
    assert dict(evidence["hot_runner_export_crosswalk"].details)["confirmed"] == "false"
    assert "hot_runner_crosswalk" not in dict(evidence["paper_scalar_feature_set"].details)
    assert [
        (item.source_experiment_id, item.proposed_paper_day)
        for item in evidence["experiment_to_paper_day"].associations
    ] == [(20, 2), (23, 3), (15, 1)]
    discrepancy_runs = evidence["experiment_15_moisture"].runs
    assert {(item.experiment_id, item.value_source) for item in discrepancy_runs} == {
        (15, "released_raw"),
        (15, "paper"),
    }
    assert [(item.count, item.value, item.unit) for item in discrepancy_runs] == [
        (89, 0.050, None),
        (89, 0.066, "%"),
        (98, 0.100, None),
        (98, 0.097, "%"),
        (116, 0.150, None),
        (116, 0.150, "%"),
    ]
    assert all(item.source_section for item in bundle.metadata.evidence)
    assert all("#" in item.source_reference for item in bundle.metadata.evidence)
    assert bundle.metadata.exclusions[0].cycle_counter == 102
    assert bundle.metadata.exclusions[0].reason == "no_released_scalar_quality_row"
    for name, snapshot in scalar_snapshots.items():
        np.testing.assert_array_equal(source.scalars.values[name], snapshot)


def test_bundle_tables_are_copy_on_access_and_mapping_is_deterministic(tmp_path: Path) -> None:
    source, expectations = _validated_fixture(tmp_path)
    first = _canonicalize_fixture(source, expectations)
    second = _canonicalize_fixture(source, expectations)

    external = first.units
    external[0, "product_family"] = "changed"
    assert external["product_family"].to_list() == ["changed", "stacking box"]
    assert first.units["product_family"].to_list() == ["stacking box", "stacking box"]
    assert first.units is not first.units
    for table_name in ("units", "operations", "process_features", "signals", "quality", "context"):
        assert getattr(first, table_name).equals(getattr(second, table_name))
    assert first.metadata == second.metadata


def test_bundle_owns_values_even_if_a_caller_constructs_mutable_handoff_arrays(
    tmp_path: Path,
) -> None:
    source, expectations = _validated_fixture(tmp_path)
    scalar_values = dict(source.scalars.values)
    mutable_weight = scalar_values["weight"].copy()
    scalar_values["weight"] = mutable_weight
    pressure = source.signals["Einspritzdruck"]
    mutable_pressure = pressure.values.copy()
    mutable_source = replace(
        source,
        scalars=replace(source.scalars, values=MappingProxyType(scalar_values)),
        signals=MappingProxyType(
            {
                **source.signals,
                "Einspritzdruck": replace(pressure, values=mutable_pressure),
            }
        ),
    )

    bundle = _canonicalize_fixture(mutable_source, expectations)
    original_weight = bundle.quality.filter(pl.col("characteristic") == "weight")["measured_value"][
        0
    ]
    original_pressure = bundle.signals["injection_pressure"][0]
    mutable_weight[0] = -1.0
    mutable_pressure[0, pressure.cycle_to_column[100]] = -1.0

    assert (
        bundle.quality.filter(pl.col("characteristic") == "weight")["measured_value"][0]
        == original_weight
    )
    assert bundle.signals["injection_pressure"][0] == original_pressure


def test_rejects_equal_but_corrupted_signal_time_axes(tmp_path: Path) -> None:
    source, expectations = _validated_fixture(tmp_path)
    corrupted_signals = {
        group: replace(signal, time_seconds=np.zeros_like(signal.time_seconds))
        for group, signal in source.signals.items()
    }
    corrupted = replace(source, signals=MappingProxyType(corrupted_signals))

    with pytest.raises(CanonicalizationError, match=r"check=handoff\.time"):
        _canonicalize_fixture(corrupted, expectations)


def test_rejects_relocated_quality_null_even_when_aggregate_count_matches(tmp_path: Path) -> None:
    source, expectations = _validated_fixture(tmp_path)
    values = dict(source.scalars.values)
    weight = values["weight"].copy()
    geometry = values["PT-PT002L*"].copy()
    weight[0] = np.nan
    geometry[1] = 5.0
    values["weight"] = weight
    values["PT-PT002L*"] = geometry
    corrupted = replace(source, scalars=replace(source.scalars, values=MappingProxyType(values)))

    with pytest.raises(CanonicalizationError, match=r"check=handoff\.missingness"):
        _canonicalize_fixture(corrupted, expectations)


def test_rejects_nonfinite_process_scalar(tmp_path: Path) -> None:
    source, expectations = _validated_fixture(tmp_path)
    values = dict(source.scalars.values)
    cycle_time = values["cycle_time"].copy()
    cycle_time[0] = np.inf
    values["cycle_time"] = cycle_time
    corrupted = replace(source, scalars=replace(source.scalars, values=MappingProxyType(values)))

    with pytest.raises(CanonicalizationError, match=r"check=handoff\.scalars"):
        _canonicalize_fixture(corrupted, expectations)


def test_rejects_interleaved_experiment_rows_with_unchanged_group_counts(tmp_path: Path) -> None:
    source, expectations = _validated_fixture(tmp_path)
    values = {name: np.concatenate((value, value)) for name, value in source.scalars.values.items()}
    values["cycle_counter"] = np.asarray([100, 101, 103, 104], dtype=np.int32)
    values["Versuch"] = np.asarray([20, 23, 20, 23], dtype=np.int64)
    corrupted = replace(
        source,
        scalars=replace(
            source.scalars,
            values=MappingProxyType(values),
            cycle_ids=(100, 101, 103, 104),
        ),
        matched_cycle_ids=(100, 101, 103, 104),
    )
    expanded_expectations = replace(
        expectations,
        scalar_rows=4,
        experiment_blocks=((20, 2), (23, 2)),
        scalar_missingness=(
            ("Charge", 2),
            ("Twkz", 2),
            ("mittlerer Feuchtegehalt", 2),
            ("PT-PT002L*", 2),
        ),
    )

    with pytest.raises(CanonicalizationError, match=r"check=handoff\.experiments"):
        _canonicalize_fixture(corrupted, expanded_expectations)


@pytest.mark.parametrize(
    ("change", "check_id"),
    [
        ("identity", "handoff.identity"),
        ("missing_membership", "handoff.membership"),
        ("duplicate_membership", "handoff.membership"),
        ("bad_signal_map", "handoff.signals"),
        ("missing_signal_reference", "handoff.membership"),
    ],
)
def test_inconsistent_validated_handoffs_reject_the_whole_result(
    tmp_path: Path, change: str, check_id: str
) -> None:
    source, expectations = _validated_fixture(tmp_path)
    if change == "identity":
        changed = replace(source, candidate="dataset1")
    elif change == "missing_membership":
        changed = replace(source, matched_cycle_ids=(100,))
    elif change == "duplicate_membership":
        changed = replace(source, signal_only_cycle_ids=(102, 102))
    else:
        pressure = source.signals["Einspritzdruck"]
        if change == "bad_signal_map":
            bad_pressure = replace(
                pressure, cycle_to_column=MappingProxyType({102: 0, 100: 1, 101: 1})
            )
            changed = replace(
                source,
                signals=MappingProxyType({**source.signals, "Einspritzdruck": bad_pressure}),
            )
        else:
            changed_signals: dict[str, SourceSignalMatrix] = {}
            for group, signal in source.signals.items():
                prefix = "einspritzdruck_ist" if group == "Einspritzdruck" else "einspritzstrom_ist"
                changed_signals[group] = replace(
                    signal,
                    cycle_ids=(102, 100, 999),
                    cycle_to_column=MappingProxyType({102: 0, 100: 1, 999: 2}),
                    source_columns=tuple(f"{prefix}_{cycle}" for cycle in (102, 100, 999)),
                )
            changed = replace(
                source,
                signals=MappingProxyType(changed_signals),
            )
    with pytest.raises(CanonicalizationError, match=rf"check={check_id}"):
        _canonicalize_fixture(changed, expectations)


@pytest.mark.parametrize(
    ("mutation", "check_id"),
    [
        ("missing", "mapping.coverage"),
        ("extra", "mapping.coverage"),
        ("duplicate", "mapping.destinations"),
        ("reserved", "mapping.reserved"),
        ("target_owner", "mapping.partition"),
        ("renamed", "mapping.names"),
    ],
)
def test_mapping_contract_rejects_incomplete_colliding_or_semantic_changes(
    tmp_path: Path, mutation: str, check_id: str
) -> None:
    source, expectations = _validated_fixture(tmp_path)
    mapping = dict(EXPECTED_MAPPING)
    if mutation == "missing":
        del mapping["cycle_time"]
    elif mutation == "extra":
        mapping["unexpected"] = ("process_features", "unexpected")
    elif mutation == "duplicate":
        mapping["cycle_time"] = mapping["Max. Spritzdruck"]
    elif mutation == "reserved":
        mapping["cycle_time"] = ("process_features", "unit_id")
    elif mutation == "target_owner":
        mapping["weight"] = ("process_features", "part_weight")
    else:
        mapping["cycle_time"] = ("process_features", "cycle_time_seconds")
    with pytest.raises(CanonicalizationError, match=rf"check={check_id}"):
        _canonicalize_fixture(source, expectations, mapping=mapping)
