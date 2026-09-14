# pyright: reportMissingTypeStubs=false
"""Canonical mapping for validated injection-molding Dataset 2."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Final, NoReturn, cast

import numpy as np
import numpy.typing as npt
import polars as pl

from mpi.data.canonical import (
    BundleMetadata,
    ExcludedUnit,
    FieldLineage,
    ManufacturingBundle,
    SignalLineage,
)
from mpi.datasets.injection_molding_validation import (
    SCALAR_COLUMNS,
    SCALAR_DTYPES,
    ValidatedInjectionMoldingSource,
    expected_injection_molding_time_grid,
)

SOURCE_VERSION: Final = "7bd35941d75c97a3f276439377dc430ab47402be"
SOURCE_CONTRACT_REFERENCE: Final = (
    "docs/datasets/injection-molding-source-contract.md#canonical-bundle-handoff"
)
_DATASET_SCOPE: Final = "injection_molding/dataset2"
_UNIT_PREFIX: Final = f"{_DATASET_SCOPE}/"
_TIME_TOLERANCE: Final = 1e-9
_QUALITY_FIELDS: Final = ("weight", "GE-GE002*", "GERADEHEIT-L*", "PT-PT002L*")
_TRANSFORMATIONS: Final = (
    "source-order projection to admitted scalar cycle identities",
    "key-based pressure and flow lookup using independent source mappings",
    "source NaN converted to typed canonical null",
    "integer geometry widened exactly to nullable Float64",
    "pressure elapsed-time axis selected after pressure/flow agreement at atol=1e-09",
    "no imputation, unit conversion, geometry conversion, resampling, "
    "normalization or source repair",
)
_CONTEXT_MAP: Final = {
    "Versuch": "experiment_id",
    "mittlerer Feuchtegehalt": "mean_moisture_content",
    "Twkz": "mold_temperature",
    "Charge": "source_charge_code",
}
_PROCESS_MAP: Final = {
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
SCALAR_MAPPING: Final = {
    **{name: ("context", canonical) for name, canonical in _CONTEXT_MAP.items()},
    "cycle_counter": ("units", "cycle_counter"),
    **{name: ("process_features", canonical) for name, canonical in _PROCESS_MAP.items()},
    **{name: ("quality", name) for name in _QUALITY_FIELDS},
}
_INTEGRAL_FIELDS: Final = tuple(
    canonical for source, canonical in _PROCESS_MAP.items() if source.startswith("integral_")
)


class CanonicalizationError(RuntimeError):
    """The validated-source handoff cannot produce one trustworthy bundle."""

    def __init__(self, check_id: str, message: str) -> None:
        super().__init__(f"check={check_id}; {message}")
        self.check_id = check_id


@dataclass(frozen=True)
class _CanonicalExpectations:
    scalar_rows: int = 829
    signal_samples: int = 2048
    signal_only: int = 92


def _fail(check_id: str, message: str) -> NoReturn:
    raise CanonicalizationError(check_id, message)


def _as_unit_id(cycle: int) -> str:
    return f"{_UNIT_PREFIX}{cycle}"


def _array(source: ValidatedInjectionMoldingSource, name: str) -> npt.NDArray[np.generic]:
    try:
        return source.scalars.values[name]
    except KeyError:
        _fail("handoff.scalars", f"source scalar values omit {name!r}")


def _validate_handoff(
    source: ValidatedInjectionMoldingSource,
) -> tuple[int, ...]:
    identity = (source.dataset, source.candidate, source.source_version)
    expected_identity = ("injection_molding", "dataset2", SOURCE_VERSION)
    if identity != expected_identity:
        _fail("handoff.identity", f"unsupported validated source identity {identity!r}")
    return source.scalars.cycle_ids


def _nullable_series(
    name: str,
    values: npt.NDArray[np.generic],
    dtype: type[pl.DataType],
) -> pl.Series:
    if values.dtype.kind == "f":
        return pl.Series(name, values.copy(), dtype=dtype, nan_to_null=True)
    return pl.Series(name, values.copy(), dtype=dtype)


def _build_lineage(mapping: Mapping[str, tuple[str, str]]) -> tuple[FieldLineage, ...]:
    source_dtypes = dict(SCALAR_DTYPES)
    result: list[FieldLineage] = []
    for source_name in SCALAR_COLUMNS:
        section, canonical_name = mapping[source_name]
        source_dtype = source_dtypes[source_name]
        canonical_dtype = (
            "Float64"
            if section == "quality"
            else "Int64"
            if source_name == "cycle_counter"
            else {
                "int32": "Int32",
                "int64": "Int64",
                "float64": "Float64",
            }[source_dtype]
        )
        unit = "g" if source_name == "weight" else None
        result.append(
            FieldLineage(
                source_group="scalars",
                source_name=source_name,
                canonical_section=section,
                canonical_name=canonical_name,
                source_dtype=source_dtype,
                canonical_dtype=canonical_dtype,
                unit=unit,
                unit_status=(
                    "documented"
                    if unit
                    else "not_applicable"
                    if source_name in {"Versuch", "Charge", "cycle_counter"}
                    else "unresolved"
                ),
                representation_change=(
                    "exact integer widened to nullable Float64 in long-form quality"
                    if section == "quality" and source_dtype.startswith("int")
                    else "exact source integer widened to canonical Int64"
                    if source_name == "cycle_counter"
                    else "source NaN represented as canonical null"
                    if source_name in {"mittlerer Feuchtegehalt", "Twkz", "Charge", "PT-PT002L*"}
                    else None
                ),
            )
        )
    return tuple(result)


def _canonicalize_validated(
    source: ValidatedInjectionMoldingSource,
    *,
    expectations: _CanonicalExpectations,
) -> ManufacturingBundle:
    cycles = _validate_handoff(source)
    rows = len(cycles)
    unit_ids = [_as_unit_id(cycle) for cycle in cycles]
    operation_ids = [f"{unit_id}/injection_molding" for unit_id in unit_ids]
    units = pl.DataFrame(
        {
            "unit_id": pl.Series(unit_ids, dtype=pl.String),
            "cycle_counter": pl.Series(cycles, dtype=pl.Int64),
            "source_row_index": pl.Series(range(rows), dtype=pl.UInt32),
            "product_family": pl.Series(["stacking box"] * rows, dtype=pl.String),
            "material": pl.Series(["BASF Ultramid B3EG6 (PA6-GF30)"] * rows, dtype=pl.String),
            "batch_id": pl.Series("batch_id", [None] * rows, dtype=pl.String),
            "production_time": pl.Series("production_time", [None] * rows, dtype=pl.Datetime("us")),
        }
    )
    operations = pl.DataFrame(
        {
            "operation_id": pl.Series(operation_ids, dtype=pl.String),
            "unit_id": pl.Series(unit_ids, dtype=pl.String),
            "process_stage": pl.Series(["injection_molding"] * rows, dtype=pl.String),
            "machine_id": pl.Series("machine_id", [None] * rows, dtype=pl.String),
            "start_time": pl.Series("start_time", [None] * rows, dtype=pl.Datetime("us")),
            "end_time": pl.Series("end_time", [None] * rows, dtype=pl.Datetime("us")),
        }
    )
    process_columns: dict[str, pl.Series] = {
        "unit_id": pl.Series(unit_ids, dtype=pl.String),
        "operation_id": pl.Series(operation_ids, dtype=pl.String),
    }
    for source_name, canonical_name in _PROCESS_MAP.items():
        process_columns[canonical_name] = _nullable_series(
            canonical_name, _array(source, source_name), pl.Float64
        )
    process_features = pl.DataFrame(process_columns)
    context = pl.DataFrame(
        {
            "unit_id": pl.Series(unit_ids, dtype=pl.String),
            "operation_id": pl.Series(operation_ids, dtype=pl.String),
            "experiment_id": _nullable_series("experiment_id", _array(source, "Versuch"), pl.Int64),
            "mean_moisture_content": _nullable_series(
                "mean_moisture_content", _array(source, "mittlerer Feuchtegehalt"), pl.Float64
            ),
            "mold_temperature": _nullable_series(
                "mold_temperature", _array(source, "Twkz"), pl.Float64
            ),
            "source_charge_code": _nullable_series(
                "source_charge_code", _array(source, "Charge"), pl.Float64
            ),
            "production_day": pl.Series("production_day", [None] * rows, dtype=pl.Int64),
        }
    )
    quality_values = np.column_stack(
        [_array(source, characteristic) for characteristic in _QUALITY_FIELDS]
    ).astype(np.float64, copy=False)
    quality = pl.DataFrame(
        {
            "unit_id": pl.Series(unit_ids, dtype=pl.String)
            .repeat_by(len(_QUALITY_FIELDS))
            .explode(empty_as_null=True),
            "operation_id": pl.Series(operation_ids, dtype=pl.String)
            .repeat_by(len(_QUALITY_FIELDS))
            .explode(empty_as_null=True),
            "characteristic": pl.Series(list(_QUALITY_FIELDS) * rows, dtype=pl.String),
            "measured_value": pl.Series(
                "measured_value",
                quality_values.reshape(-1).copy(),
                dtype=pl.Float64,
                nan_to_null=True,
            ),
            "measurement_unit": pl.Series(
                "measurement_unit", ["g", None, None, None] * rows, dtype=pl.String
            ),
            "lower_spec": pl.Series(
                "lower_spec", [None] * (rows * len(_QUALITY_FIELDS)), dtype=pl.Float64
            ),
            "upper_spec": pl.Series(
                "upper_spec", [None] * (rows * len(_QUALITY_FIELDS)), dtype=pl.Float64
            ),
        }
    )

    pressure = source.signals["Einspritzdruck"]
    flow = source.signals["Einspritzstrom"]
    pressure_indices = [pressure.cycle_to_column[cycle] for cycle in cycles]
    flow_indices = [flow.cycle_to_column[cycle] for cycle in cycles]
    samples = expectations.signal_samples
    signal_unit_ids = (
        pl.Series(unit_ids, dtype=pl.String).repeat_by(samples).explode(empty_as_null=True)
    )
    signal_operation_ids = (
        pl.Series(operation_ids, dtype=pl.String).repeat_by(samples).explode(empty_as_null=True)
    )
    signals = pl.DataFrame(
        {
            "unit_id": signal_unit_ids,
            "operation_id": signal_operation_ids,
            "sample_index": pl.Series(
                np.tile(np.arange(samples, dtype=np.uint32), rows), dtype=pl.UInt32
            ),
            "elapsed_time_seconds": pl.Series(
                np.tile(pressure.time_seconds, rows), dtype=pl.Float64
            ),
            "injection_pressure": pl.Series(
                np.asarray(pressure.values[:, pressure_indices].T).reshape(-1).copy(),
                dtype=pl.Float64,
            ),
            "injection_flow": pl.Series(
                np.asarray(flow.values[:, flow_indices].T).reshape(-1).copy(),
                dtype=pl.Float64,
            ),
        }
    )

    exclusions = tuple(
        ExcludedUnit(_as_unit_id(cycle), cycle, "no_released_scalar_quality_row")
        for cycle in source.signal_only_cycle_ids
    )
    metadata = BundleMetadata(
        dataset=source.dataset,
        candidate=source.candidate,
        source_version=source.source_version,
        archive_size=source.archive_size,
        archive_sha256=source.archive_sha256,
        source_contract_reference=SOURCE_CONTRACT_REFERENCE,
        citations=(
            "Bogedale et al. (2023), Online Prediction of Molded Part Quality in the "
            "Injection Molding Process Using High-Resolution Time Series, "
            "https://doi.org/10.3390/polym15040978",
            f"https://github.com/sc4t1m/scatimdata/tree/{source.source_version}",
        ),
        license_name="CC BY 4.0",
        license_url="https://creativecommons.org/licenses/by/4.0/legalcode.en",
        scalar_lineage=_build_lineage(SCALAR_MAPPING),
        signal_lineage=(
            SignalLineage(
                "Einspritzdruck",
                "time",
                "einspritzdruck_ist_<cycle_counter>",
                "injection_pressure",
                "elapsed_time_seconds",
                "float64",
                "Float64",
                "s",
                None,
                "unresolved",
            ),
            SignalLineage(
                "Einspritzstrom",
                "time",
                "einspritzstrom_ist_<cycle_counter>",
                "injection_flow",
                "elapsed_time_seconds",
                "float64",
                "Float64",
                "s",
                None,
                "unresolved",
            ),
        ),
        transformations=_TRANSFORMATIONS,
        exclusions=exclusions,
        limitations=source.limitations,
        retained_optional_source_groups=source.optional_groups,
        retained_optional_process_fields=_INTEGRAL_FIELDS,
    )
    bundle = ManufacturingBundle(
        units=units,
        operations=operations,
        process_features=process_features,
        signals=signals,
        quality=quality,
        context=context,
        metadata=metadata,
    )
    _validate_bundle(bundle, expectations)
    return bundle


def validate_bundle_schema(bundle: ManufacturingBundle) -> None:
    """Check table columns and dtypes without repeating the source audit."""
    tables = {
        "units": bundle.units,
        "operations": bundle.operations,
        "process_features": bundle.process_features,
        "signals": bundle.signals,
        "quality": bundle.quality,
        "context": bundle.context,
    }
    expected_schemas: dict[str, list[tuple[str, str]]] = {
        "units": [
            ("unit_id", "String"),
            ("cycle_counter", "Int64"),
            ("source_row_index", "UInt32"),
            ("product_family", "String"),
            ("material", "String"),
            ("batch_id", "String"),
            ("production_time", "Datetime(time_unit='us', time_zone=None)"),
        ],
        "operations": [
            ("operation_id", "String"),
            ("unit_id", "String"),
            ("process_stage", "String"),
            ("machine_id", "String"),
            ("start_time", "Datetime(time_unit='us', time_zone=None)"),
            ("end_time", "Datetime(time_unit='us', time_zone=None)"),
        ],
        "process_features": [
            ("unit_id", "String"),
            ("operation_id", "String"),
            *((name, "Float64") for name in _PROCESS_MAP.values()),
        ],
        "signals": [
            ("unit_id", "String"),
            ("operation_id", "String"),
            ("sample_index", "UInt32"),
            ("elapsed_time_seconds", "Float64"),
            ("injection_pressure", "Float64"),
            ("injection_flow", "Float64"),
        ],
        "quality": [
            ("unit_id", "String"),
            ("operation_id", "String"),
            ("characteristic", "String"),
            ("measured_value", "Float64"),
            ("measurement_unit", "String"),
            ("lower_spec", "Float64"),
            ("upper_spec", "Float64"),
        ],
        "context": [
            ("unit_id", "String"),
            ("operation_id", "String"),
            ("experiment_id", "Int64"),
            ("mean_moisture_content", "Float64"),
            ("mold_temperature", "Float64"),
            ("source_charge_code", "Float64"),
            ("production_day", "Int64"),
        ],
    }
    for name, table in tables.items():
        observed_schema = [(field, str(dtype)) for field, dtype in table.schema.items()]
        if observed_schema != expected_schemas[name]:
            _fail("bundle.schema", f"{name} schema differs from the Dataset 2 contract")


def _validate_bundle(
    bundle: ManufacturingBundle,
    expectations: _CanonicalExpectations,
) -> None:
    validate_bundle_schema(bundle)
    tables = {
        name: getattr(bundle, name)
        for name in ("units", "operations", "process_features", "signals", "quality", "context")
    }
    expected_rows = expectations.scalar_rows
    if (
        tuple(
            tables[name].height for name in ("units", "operations", "process_features", "context")
        )
        != (expected_rows,) * 4
        or tables["signals"].height != expected_rows * expectations.signal_samples
        or tables["quality"].height != expected_rows * len(_QUALITY_FIELDS)
    ):
        _fail("bundle.counts", "canonical table counts differ")
    unit_ids = tables["units"]["unit_id"]
    cycle_counters = tables["units"]["cycle_counter"]
    source_indices = tables["units"]["source_row_index"]
    if cycle_counters.null_count():
        _fail("bundle.keys", "cycle counters must be complete")
    cycle_values = cast(list[int], cycle_counters.to_list())
    unit_values = cast(list[str], unit_ids.to_list())
    expected_unit_ids = [_as_unit_id(cycle) for cycle in cycle_values]
    if (
        unit_values != expected_unit_ids
        or len(set(unit_values)) != expected_rows
        or source_indices.to_list() != list(range(expected_rows))
    ):
        _fail("bundle.keys", "unit IDs or source row indices differ from cycle/source order")
    operation_ids = tables["operations"]["operation_id"]
    operation_values = cast(list[str], operation_ids.to_list())
    expected_operation_ids = [f"{unit_id}/injection_molding" for unit_id in unit_values]
    if tables["operations"]["unit_id"].to_list() != unit_values or (
        operation_values != expected_operation_ids
    ):
        _fail("bundle.references", "operations do not map one-to-one to units in source order")
    for name in ("process_features", "context"):
        if tables[name]["unit_id"].to_list() != unit_values or (
            tables[name]["operation_id"].to_list() != operation_values
        ):
            _fail("bundle.references", f"{name} unit/operation rows are not aligned")
    expected_quality_units = unit_ids.repeat_by(len(_QUALITY_FIELDS)).explode(empty_as_null=True)
    expected_quality_operations = operation_ids.repeat_by(len(_QUALITY_FIELDS)).explode(
        empty_as_null=True
    )
    if not tables["quality"]["unit_id"].equals(expected_quality_units) or not tables["quality"][
        "operation_id"
    ].equals(expected_quality_operations):
        _fail("bundle.references", "quality rows are not aligned to units and operations")
    if tables["quality"]["characteristic"].to_list() != list(_QUALITY_FIELDS) * expected_rows:
        _fail("bundle.quality", "quality characteristic order differs")
    expected_signal_units = unit_ids.repeat_by(expectations.signal_samples).explode(
        empty_as_null=True
    )
    expected_signal_operations = operation_ids.repeat_by(expectations.signal_samples).explode(
        empty_as_null=True
    )
    if not tables["signals"]["unit_id"].equals(expected_signal_units) or not tables["signals"][
        "operation_id"
    ].equals(expected_signal_operations):
        _fail("bundle.references", "signal rows are not aligned to units and operations")
    expected_samples = pl.Series(
        np.tile(np.arange(expectations.signal_samples, dtype=np.uint32), expected_rows),
        dtype=pl.UInt32,
    )
    if not tables["signals"]["sample_index"].equals(expected_samples):
        _fail("bundle.signals", "sample indices are not complete in unit/source order")
    expected_time = np.tile(
        expected_injection_molding_time_grid(expectations.signal_samples), expected_rows
    )
    observed_time = tables["signals"]["elapsed_time_seconds"].to_numpy()
    if not np.allclose(observed_time, expected_time, rtol=0.0, atol=_TIME_TOLERANCE):
        _fail("bundle.signals", "elapsed-time values differ from the native grid")
    excluded_ids = {item.unit_id for item in bundle.metadata.exclusions}
    excluded_cycles = {item.cycle_counter for item in bundle.metadata.exclusions}
    if (
        len(bundle.metadata.exclusions) != expectations.signal_only
        or len(excluded_ids) != expectations.signal_only
        or len(excluded_cycles) != expectations.signal_only
        or set(unit_values) & excluded_ids
    ):
        _fail("bundle.exclusions", "excluded signal-only IDs are incomplete or admitted")
    expected_exclusion_shape = tuple(
        (
            item.unit_id,
            _as_unit_id(item.cycle_counter),
            item.reason,
        )
        for item in bundle.metadata.exclusions
    )
    if any(
        unit_id != derived_id or reason != "no_released_scalar_quality_row"
        for unit_id, derived_id, reason in expected_exclusion_shape
    ):
        _fail("bundle.exclusions", "excluded cycle identities or reasons are inconsistent")


def canonicalize_injection_molding(
    source: ValidatedInjectionMoldingSource,
) -> ManufacturingBundle:
    """Map a pinned, production-validated Dataset 2 source into memory."""
    return _canonicalize_validated(
        source,
        expectations=_CanonicalExpectations(),
    )
