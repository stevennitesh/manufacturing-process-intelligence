# pyright: reportMissingTypeStubs=false, reportPrivateUsage=false
# pyright: reportUnknownMemberType=false
from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from typing import cast

import numpy as np
import polars as pl
import pytest

from mpi.data.canonical import ManufacturingBundle
from mpi.datasets.injection_molding_canonicalization import (
    CanonicalizationError,
    _validate_bundle,
)
from mpi.datasets.injection_molding_validation import (
    SCALAR_COLUMNS,
)
from tests.unit.injection_molding_helpers import canonicalize_fixture, validated_fixture

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


def _with_table(bundle: ManufacturingBundle, name: str, table: pl.DataFrame) -> ManufacturingBundle:
    tables = {
        candidate: table if candidate == name else getattr(bundle, candidate)
        for candidate in (
            "units",
            "operations",
            "process_features",
            "signals",
            "quality",
            "context",
        )
    }
    return ManufacturingBundle(metadata=bundle.metadata, **tables)


def test_handoff_preserves_limitations(
    tmp_path: Path,
) -> None:
    source, expectations = validated_fixture(tmp_path)
    changed = replace(
        source,
        limitations=("Same source limitation, revised wording.",),
    )

    bundle = canonicalize_fixture(changed, expectations)

    assert bundle.metadata.limitations == ("Same source limitation, revised wording.",)


def test_real_validator_handoff_maps_keys_values_nulls_lineage_and_evidence(tmp_path: Path) -> None:
    source, expectations = validated_fixture(tmp_path)
    scalar_snapshots = {name: value.copy() for name, value in source.scalars.values.items()}

    bundle = canonicalize_fixture(source, expectations)

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
    assert bundle.metadata.exclusions[0].cycle_counter == 102
    assert bundle.metadata.exclusions[0].reason == "no_released_scalar_quality_row"
    for name, snapshot in scalar_snapshots.items():
        np.testing.assert_array_equal(source.scalars.values[name], snapshot)


@pytest.mark.parametrize(
    ("mutation", "check_id"),
    [
        ("duplicate_key", "bundle.keys"),
        ("misaligned_reference", "bundle.references"),
        ("changed_time_grid", "bundle.signals"),
        ("wrong_weight_unit", "bundle.quality"),
        ("fabricated_day", "bundle.context"),
        ("changed_exclusion", "bundle.exclusions"),
    ],
)
def test_scientific_bundle_discriminators_remain_owned_by_canonical_validation(
    tmp_path: Path, mutation: str, check_id: str
) -> None:
    source, expectations = validated_fixture(tmp_path)
    bundle = canonicalize_fixture(source, expectations)
    if mutation == "duplicate_key":
        table = bundle.units.with_columns(
            pl.when(pl.col("source_row_index") == 1)
            .then(pl.lit("injection_molding/dataset2/100"))
            .otherwise(pl.col("unit_id"))
            .alias("unit_id")
        )
        changed = _with_table(bundle, "units", table)
    elif mutation == "misaligned_reference":
        table = bundle.process_features.with_columns(
            pl.col("operation_id").reverse().alias("operation_id")
        )
        changed = _with_table(bundle, "process_features", table)
    elif mutation == "changed_time_grid":
        table = bundle.signals.with_columns(
            pl.when(pl.col("sample_index") == 1)
            .then(pl.col("elapsed_time_seconds") + 0.001)
            .otherwise(pl.col("elapsed_time_seconds"))
            .alias("elapsed_time_seconds")
        )
        changed = _with_table(bundle, "signals", table)
    elif mutation == "wrong_weight_unit":
        table = bundle.quality.with_columns(
            pl.when(pl.col("characteristic") == "weight")
            .then(pl.lit(None, dtype=pl.String))
            .otherwise(pl.col("measurement_unit"))
            .alias("measurement_unit")
        )
        changed = _with_table(bundle, "quality", table)
    elif mutation == "fabricated_day":
        table = bundle.context.with_columns(pl.lit(1, dtype=pl.Int64).alias("production_day"))
        changed = _with_table(bundle, "context", table)
    else:
        metadata = replace(
            bundle.metadata,
            exclusions=(replace(bundle.metadata.exclusions[0], reason="unknown"),),
        )
        changed = ManufacturingBundle(
            units=bundle.units,
            operations=bundle.operations,
            process_features=bundle.process_features,
            signals=bundle.signals,
            quality=bundle.quality,
            context=bundle.context,
            metadata=metadata,
        )

    with pytest.raises(CanonicalizationError, match=rf"check={check_id}"):
        _validate_bundle(changed, expectations)
