"""Verify the complete real Dataset 2 validator-to-canonicalizer handoff."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import polars as pl

from mpi.datasets.injection_molding_canonicalization import canonicalize_injection_molding
from mpi.datasets.injection_molding_persistence import load_bundle
from mpi.datasets.injection_molding_validation import SCALAR_COLUMNS, validate_injection_molding

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
    "integral_idx_0_einspritzdruck_ist_state_1": (
        "integral_idx_0_actual_injection_pressure_state_1"
    ),
    "integral_idx_0_einspritzdruck_ist_state_2": (
        "integral_idx_0_actual_injection_pressure_state_2"
    ),
    "integral_idx_0_einspritzdruck_ist_state_8": (
        "integral_idx_0_actual_injection_pressure_state_8"
    ),
    "integral_idx_0_einspritzstrom_ist_state_1": ("integral_idx_0_actual_injection_flow_state_1"),
    "integral_idx_0_einspritzstrom_ist_state_2": ("integral_idx_0_actual_injection_flow_state_2"),
    "integral_idx_0_einspritzstrom_ist_state_8": ("integral_idx_0_actual_injection_flow_state_8"),
}
EXPECTED_QUALITY = ("weight", "GE-GE002*", "GERADEHEIT-L*", "PT-PT002L*")
EXPECTED_MAPPING = {
    **{name: ("context", destination) for name, destination in EXPECTED_CONTEXT.items()},
    "cycle_counter": ("units", "cycle_counter"),
    **{name: ("process_features", destination) for name, destination in EXPECTED_PROCESS.items()},
    **{name: ("quality", name) for name in EXPECTED_QUALITY},
}


def _assert_equal_with_nulls(canonical: pl.Series, source: np.ndarray) -> None:
    observed = canonical.to_numpy(allow_copy=True)
    if source.dtype.kind == "f":
        np.testing.assert_allclose(
            observed.astype(float), source, rtol=0.0, atol=0.0, equal_nan=True
        )
    else:
        np.testing.assert_array_equal(observed, source)


def verify(raw_root: Path, artifact: Path | None = None) -> dict[str, object]:
    source = validate_injection_molding(raw_root=raw_root)
    canonical = canonicalize_injection_molding(source)
    if artifact is None:
        bundle = canonical
    else:
        bundle = load_bundle(artifact)
        for name in (
            "units",
            "operations",
            "process_features",
            "signals",
            "quality",
            "context",
        ):
            assert getattr(bundle, name).equals(getattr(canonical, name))
        observed_metadata = bundle.metadata
        expected_metadata = canonical.metadata
        assert (
            observed_metadata.dataset,
            observed_metadata.candidate,
            observed_metadata.source_version,
            observed_metadata.archive_size,
            observed_metadata.archive_sha256,
            observed_metadata.scalar_lineage,
            observed_metadata.signal_lineage,
            observed_metadata.exclusions,
        ) == (
            expected_metadata.dataset,
            expected_metadata.candidate,
            expected_metadata.source_version,
            expected_metadata.archive_size,
            expected_metadata.archive_sha256,
            expected_metadata.scalar_lineage,
            expected_metadata.signal_lineage,
            expected_metadata.exclusions,
        )
    units = bundle.units
    operations = bundle.operations
    process = bundle.process_features
    context = bundle.context
    quality = bundle.quality
    signals = bundle.signals

    np.testing.assert_array_equal(
        units["cycle_counter"].to_numpy(), source.scalars.values["cycle_counter"]
    )
    np.testing.assert_array_equal(units["source_row_index"].to_numpy(), np.arange(829))
    unit_ids = units["unit_id"].to_list()
    operation_ids = operations["operation_id"].to_list()
    assert process["unit_id"].to_list() == unit_ids
    assert context["unit_id"].to_list() == unit_ids
    assert operations["unit_id"].to_list() == unit_ids
    assert process["operation_id"].to_list() == operation_ids
    assert context["operation_id"].to_list() == operation_ids

    for source_name, canonical_name in EXPECTED_CONTEXT.items():
        _assert_equal_with_nulls(context[canonical_name], source.scalars.values[source_name])
    for source_name, canonical_name in EXPECTED_PROCESS.items():
        _assert_equal_with_nulls(process[canonical_name], source.scalars.values[source_name])
    for characteristic in EXPECTED_QUALITY:
        observed = quality.filter(pl.col("characteristic") == characteristic)["measured_value"]
        _assert_equal_with_nulls(observed, source.scalars.values[characteristic])

    pressure = source.signals["Einspritzdruck"]
    flow = source.signals["Einspritzstrom"]
    pressure_indices = [pressure.cycle_to_column[cycle] for cycle in source.scalars.cycle_ids]
    flow_indices = [flow.cycle_to_column[cycle] for cycle in source.scalars.cycle_ids]
    observed_pressure = signals["injection_pressure"].to_numpy().reshape(829, 2048)
    observed_flow = signals["injection_flow"].to_numpy().reshape(829, 2048)
    observed_time = signals["elapsed_time_seconds"].to_numpy().reshape(829, 2048)
    np.testing.assert_array_equal(observed_pressure, pressure.values[:, pressure_indices].T)
    np.testing.assert_array_equal(observed_flow, flow.values[:, flow_indices].T)
    np.testing.assert_array_equal(observed_time, np.tile(pressure.time_seconds, (829, 1)))
    assert signals.group_by("unit_id", maintain_order=True).len()["unit_id"].to_list() == unit_ids

    lineage = {
        item.source_name: (item.canonical_section, item.canonical_name)
        for item in bundle.metadata.scalar_lineage
    }
    assert tuple(lineage) == SCALAR_COLUMNS
    assert lineage == EXPECTED_MAPPING
    table_counts = {
        name: getattr(bundle, name).height
        for name in ("units", "operations", "process_features", "signals", "quality", "context")
    }
    assert table_counts == {
        "units": 829,
        "operations": 829,
        "process_features": 829,
        "signals": 1_697_792,
        "quality": 3_316,
        "context": 829,
    }
    assert quality["measured_value"].null_count() == 303
    assert (
        quality.filter(pl.col("characteristic") == "PT-PT002L*")["measured_value"].null_count()
        == 303
    )
    assert context.select(
        pl.col("source_charge_code").null_count(),
        pl.col("mold_temperature").null_count(),
        pl.col("mean_moisture_content").null_count(),
    ).row(0) == (526, 526, 303)
    assert context["experiment_id"].rle().struct.field("value").to_list() == [20, 23, 15]
    assert context["experiment_id"].rle().struct.field("len").to_list() == [223, 303, 303]
    assert context["production_day"].null_count() == 829
    assert quality["lower_spec"].null_count() == 3_316
    assert quality["upper_spec"].null_count() == 3_316
    assert [item.cycle_counter for item in bundle.metadata.exclusions] == list(
        source.signal_only_cycle_ids
    )
    assert {item.reason for item in bundle.metadata.exclusions} == {
        "no_released_scalar_quality_row"
    }
    admitted_ids = set(unit_ids)
    assert not admitted_ids.intersection(item.unit_id for item in bundle.metadata.exclusions)

    return {
        "status": "passed",
        "source": {
            "version": source.source_version,
            "archive_bytes": source.archive_size,
            "archive_sha256": source.archive_sha256,
        },
        "tables": table_counts,
        "scalar_fields_compared": len(SCALAR_COLUMNS),
        "scalar_cells_compared": 829 * len(SCALAR_COLUMNS),
        "trajectory_channels_compared_by_cycle_key": ["injection_pressure", "injection_flow"],
        "trajectory_values_compared_per_channel": 829 * 2048,
        "trajectory_time_values_compared": 829 * 2048,
        "quality_nulls": quality["measured_value"].null_count(),
        "exclusions": len(bundle.metadata.exclusions),
        "durable_artifact_compared": str(artifact.resolve()) if artifact else None,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "raw_root",
        nargs="?",
        type=Path,
        default=Path("data/raw/injection_molding"),
    )
    parser.add_argument(
        "artifact",
        nargs="?",
        type=Path,
        help="Optional prepared artifact to load and compare exactly.",
    )
    arguments = parser.parse_args()
    print(json.dumps(verify(arguments.raw_root, arguments.artifact), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
