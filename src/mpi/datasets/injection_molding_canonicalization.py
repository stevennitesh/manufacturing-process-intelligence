# pyright: reportMissingTypeStubs=false
"""Canonical mapping for validated injection-molding Dataset 2."""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from itertools import groupby
from typing import Final, NoReturn, cast

import numpy as np
import numpy.typing as npt
import polars as pl

from mpi import __version__
from mpi.data.canonical import (
    BundleMetadata,
    EvidenceAssociation,
    EvidenceQuantity,
    EvidenceRecord,
    EvidenceRun,
    ExcludedUnit,
    FieldLineage,
    ManufacturingBundle,
    SignalLineage,
)
from mpi.datasets.injection_molding_validation import (
    LIMITATIONS,
    OPTIONAL_GROUPS,
    SCALAR_COLUMNS,
    SCALAR_DTYPES,
    VALIDATOR_VERSION,
    SourceSignalMatrix,
    ValidatedInjectionMoldingSource,
    expected_injection_molding_time_grid,
)

ADAPTER_VERSION: Final = "1"
SCHEMA_VERSION: Final = "1"
MAPPING_VERSION: Final = "1"
SOURCE_VERSION: Final = "7bd35941d75c97a3f276439377dc430ab47402be"
SOURCE_CONTRACT_REFERENCE: Final = (
    "docs/datasets/injection-molding-source-contract.md#canonical-bundle-handoff"
)
_DATASET_SCOPE: Final = "injection_molding/dataset2"
_UNIT_PREFIX: Final = f"{_DATASET_SCOPE}/"
_TIME_TOLERANCE: Final = 1e-9
_QUALITY_FIELDS: Final = ("weight", "GE-GE002*", "GERADEHEIT-L*", "PT-PT002L*")
_VALIDATION_CHECK_IDS: Final = (
    "archive.identity",
    "zip.member",
    "hdf.representation",
    "scalars.schema",
    "scalars.missingness",
    "signals.required",
    "signals.time_grid",
    "joins.membership",
    "scalars.experiments",
    "archive.stability",
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
_RESERVED_BY_SECTION: Final = {
    "units": {
        "unit_id",
        "source_row_index",
        "product_family",
        "material",
        "batch_id",
        "production_time",
    },
    "process_features": {"unit_id", "operation_id"},
    "context": {"unit_id", "operation_id", "production_day"},
    "quality": {
        "unit_id",
        "operation_id",
        "measured_value",
        "measurement_unit",
        "lower_spec",
        "upper_spec",
    },
}


class CanonicalizationError(RuntimeError):
    """The validated-source handoff cannot produce one trustworthy bundle."""

    def __init__(self, check_id: str, message: str) -> None:
        super().__init__(f"check={check_id}; {message}")
        self.check_id = check_id


@dataclass(frozen=True)
class _CanonicalExpectations:
    scalar_rows: int = 829
    signal_cycles: int = 921
    signal_samples: int = 2048
    signal_only: int = 92
    quality_nulls: int = 303
    experiment_blocks: tuple[tuple[int, int], ...] = ((20, 223), (23, 303), (15, 303))
    scalar_missingness: tuple[tuple[str, int], ...] = (
        ("Charge", 526),
        ("Twkz", 526),
        ("mittlerer Feuchtegehalt", 303),
        ("PT-PT002L*", 303),
    )
    context_nulls: tuple[tuple[str, int], ...] = (
        ("source_charge_code", 526),
        ("mold_temperature", 526),
        ("mean_moisture_content", 303),
    )


def _fail(check_id: str, message: str) -> NoReturn:
    raise CanonicalizationError(check_id, message)


def _validate_mapping(mapping: Mapping[str, tuple[str, str]]) -> None:
    expected = set(SCALAR_COLUMNS)
    observed = set(mapping)
    if observed != expected or len(mapping) != len(SCALAR_COLUMNS):
        _fail(
            "mapping.coverage",
            "scalar map must cover exactly 40 source fields; "
            f"missing={sorted(expected - observed)!r}, "
            f"extra={sorted(observed - expected)!r}",
        )
    destinations: set[tuple[str, str]] = set()
    for source in SCALAR_COLUMNS:
        section, name = mapping[source]
        if section not in {"units", "context", "process_features", "quality"}:
            _fail("mapping.section", f"unsupported section {section!r} for {source!r}")
        destination = (section, name)
        if destination in destinations:
            _fail("mapping.destinations", f"duplicate canonical destination {destination!r}")
        if name in _RESERVED_BY_SECTION[section]:
            _fail("mapping.reserved", f"{source!r} collides with reserved {section}.{name}")
        destinations.add(destination)
    if len(_PROCESS_MAP) != 31 or len(_CONTEXT_MAP) != 4 or len(_QUALITY_FIELDS) != 4:
        _fail(
            "mapping.partition",
            "scalar partition must be 1 identity + 4 context + 31 process + 4 quality",
        )
    wrong_owners = {
        source: destination
        for source, destination in mapping.items()
        if destination[0] != SCALAR_MAPPING[source][0]
    }
    if wrong_owners:
        _fail("mapping.partition", f"source fields have incorrect value owners: {wrong_owners!r}")
    wrong_names = {
        source: destination
        for source, destination in mapping.items()
        if destination[1] != SCALAR_MAPPING[source][1]
    }
    if wrong_names:
        _fail(
            "mapping.names",
            f"canonical destinations differ from mapping version 1: {wrong_names!r}",
        )


def _as_unit_id(cycle: int) -> str:
    return f"{_UNIT_PREFIX}{cycle}"


def _array(source: ValidatedInjectionMoldingSource, name: str) -> npt.NDArray[np.generic]:
    try:
        return source.scalars.values[name]
    except KeyError:
        _fail("handoff.scalars", f"source scalar values omit {name!r}")


def _check_signal(
    signal: SourceSignalMatrix,
    *,
    group: str,
    expectations: _CanonicalExpectations,
) -> None:
    if signal.group != group:
        _fail("handoff.signals", f"signal key {group!r} contains group {signal.group!r}")
    if len(signal.cycle_ids) != expectations.signal_cycles or len(set(signal.cycle_ids)) != len(
        signal.cycle_ids
    ):
        _fail("handoff.signals", f"{group} cycle identities are incomplete or duplicated")
    expected_map = {cycle: index for index, cycle in enumerate(signal.cycle_ids)}
    if dict(signal.cycle_to_column) != expected_map:
        _fail("handoff.signals", f"{group} cycle-to-column mapping is inconsistent")
    prefix = "einspritzdruck_ist" if group == "Einspritzdruck" else "einspritzstrom_ist"
    expected_columns = tuple(f"{prefix}_{cycle}" for cycle in signal.cycle_ids)
    if signal.source_columns != expected_columns:
        _fail("handoff.signals", f"{group} source columns do not encode its cycle identities")
    if signal.values.dtype != np.dtype("float64") or signal.values.shape != (
        expectations.signal_samples,
        expectations.signal_cycles,
    ):
        _fail("handoff.signals", f"{group} value shape or dtype is unsupported")
    if signal.time_seconds.dtype != np.dtype("float64") or signal.time_seconds.shape != (
        expectations.signal_samples,
    ):
        _fail("handoff.signals", f"{group} time shape or dtype is unsupported")
    if not np.isfinite(signal.values).all() or not np.isfinite(signal.time_seconds).all():
        _fail("handoff.signals", f"{group} contains nonfinite signal values")
    native_time = expected_injection_molding_time_grid(expectations.signal_samples)
    if not np.allclose(signal.time_seconds, native_time, rtol=0.0, atol=_TIME_TOLERANCE):
        _fail("handoff.time", f"{group} does not preserve the native elapsed-time grid")


def _validate_handoff(
    source: ValidatedInjectionMoldingSource,
    expectations: _CanonicalExpectations,
    mapping: Mapping[str, tuple[str, str]],
    *,
    production: bool,
) -> tuple[int, ...]:
    _validate_mapping(mapping)
    identity = (source.dataset, source.candidate, source.source_version, source.validator_version)
    expected_identity = ("injection_molding", "dataset2", SOURCE_VERSION, VALIDATOR_VERSION)
    if identity != expected_identity:
        _fail("handoff.identity", f"unsupported validated source identity {identity!r}")
    if production and source.project_version != __version__:
        _fail("handoff.identity", "validated source project version is not current")
    if tuple(check.check_id for check in source.checks) != _VALIDATION_CHECK_IDS:
        _fail("handoff.validation_evidence", "validated source checks are incomplete or reordered")
    if source.limitations != LIMITATIONS:
        _fail("handoff.validation_evidence", "validated source limitations differ")
    if source.archive_size <= 0 or re.fullmatch(r"[0-9a-f]{64}", source.archive_sha256) is None:
        _fail("handoff.identity", "archive identity is incomplete")
    if re.fullmatch(r"[0-9a-f]{64}", source.manifest_sha256) is None:
        _fail("handoff.identity", "manifest identity is incomplete")
    if source.scalars.columns != SCALAR_COLUMNS or set(source.scalars.values) != set(
        SCALAR_COLUMNS
    ):
        _fail("handoff.scalars", "scalar columns do not match the supported 40-field schema")
    if len(source.scalars.cycle_ids) != expectations.scalar_rows:
        _fail("handoff.membership", "scalar row count differs from the canonical contract")
    expected_dtypes = dict(SCALAR_DTYPES)
    expected_missingness = dict(expectations.scalar_missingness)
    for name in SCALAR_COLUMNS:
        value = _array(source, name)
        if value.shape != (expectations.scalar_rows,) or str(value.dtype) != expected_dtypes[name]:
            _fail("handoff.scalars", f"unsupported shape or dtype for scalar {name!r}")
        if value.dtype.kind == "f":
            missing = int(np.isnan(value).sum())
            if not (np.isfinite(value) | np.isnan(value)).all():
                _fail("handoff.scalars", f"scalar {name!r} contains infinite values")
        else:
            missing = 0
        expected_missing = expected_missingness.get(name, 0)
        if missing != expected_missing:
            _fail(
                "handoff.missingness",
                f"scalar {name!r} has {missing} missing values; expected {expected_missing}",
            )
    cycles = tuple(int(value) for value in _array(source, "cycle_counter").tolist())
    if cycles != source.scalars.cycle_ids or len(set(cycles)) != len(cycles):
        _fail("handoff.membership", "cycle identities are duplicated or inconsistent")
    if source.matched_cycle_ids != cycles or source.labeled_only_cycle_ids:
        _fail("handoff.membership", "admitted scalar membership is inconsistent")
    experiments = tuple(int(value) for value in _array(source, "Versuch").tolist())
    observed_blocks = tuple(
        (experiment, sum(1 for _ in members)) for experiment, members in groupby(experiments)
    )
    if observed_blocks != expectations.experiment_blocks:
        _fail(
            "handoff.experiments",
            f"experiment rows are not the required contiguous source blocks: {observed_blocks!r}",
        )
    if len(source.signal_only_cycle_ids) != expectations.signal_only or len(
        set(source.signal_only_cycle_ids)
    ) != len(source.signal_only_cycle_ids):
        _fail("handoff.membership", "signal-only membership is incomplete or duplicated")
    if set(source.signals) != {"Einspritzdruck", "Einspritzstrom"}:
        _fail("handoff.signals", "required signal groups must be exact")
    pressure = source.signals["Einspritzdruck"]
    flow = source.signals["Einspritzstrom"]
    _check_signal(pressure, group="Einspritzdruck", expectations=expectations)
    _check_signal(flow, group="Einspritzstrom", expectations=expectations)
    if set(pressure.cycle_ids) != set(flow.cycle_ids):
        _fail("handoff.signals", "pressure and flow cycle sets differ")
    expected_signal_set = set(cycles) | set(source.signal_only_cycle_ids)
    if set(pressure.cycle_ids) != expected_signal_set:
        _fail("handoff.membership", "signals do not exactly cover admitted and excluded identities")
    if not np.allclose(pressure.time_seconds, flow.time_seconds, rtol=0.0, atol=_TIME_TOLERANCE):
        _fail("handoff.time", "pressure and flow time axes differ")
    if source.optional_groups != OPTIONAL_GROUPS:
        _fail("handoff.optional_groups", "optional source-group inventory differs")
    return cycles


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


def _evidence() -> tuple[EvidenceRecord, ...]:
    contract_path = "docs/datasets/injection-molding-source-contract.md"
    return (
        EvidenceRecord(
            subject="material",
            state="documented_fact",
            dataset_scope=_DATASET_SCOPE,
            source_reference=f"{contract_path}#paper-supported-material-and-measurement-context",
            source_section="Paper sections 2.1 and 2.2.3",
            details=(
                ("manufacturer", "BASF"),
                ("grade", "Ultramid B3EG6"),
                ("polymer", "PA6-GF30"),
                ("scope", "dataset constant, not per-row genealogy"),
            ),
        ),
        EvidenceRecord(
            subject="machine",
            state="documented_fact",
            dataset_scope=_DATASET_SCOPE,
            source_reference=f"{contract_path}#source-declared-manufacturing-meaning",
            source_section="Paper section 2.1",
            details=(
                ("model", "Arburg Allrounder 520E 1500-800"),
                ("scope", "shared experimental equipment, not machine_id"),
            ),
        ),
        EvidenceRecord(
            subject="optical_measurement_equipment",
            state="documented_fact",
            dataset_scope=_DATASET_SCOPE,
            source_reference=f"{contract_path}#paper-supported-material-and-measurement-context",
            source_section="Paper section 2.1",
            details=(
                ("model", "Keyence IM-7020"),
                ("quality_limit", "false"),
            ),
            quantities=(EvidenceQuantity("maximum_measurement_deviation", 8.0, "um"),),
        ),
        EvidenceRecord(
            subject="weight_measurement_equipment",
            state="documented_fact",
            dataset_scope=_DATASET_SCOPE,
            source_reference=f"{contract_path}#paper-supported-material-and-measurement-context",
            source_section="Paper section 2.1",
            details=(
                ("model", "Sartorius Entris BCE323i-1S"),
                ("quality_limit", "false"),
            ),
            quantities=(EvidenceQuantity("maximum_linearity_deviation", 2.0, "mg"),),
        ),
        EvidenceRecord(
            subject="experiment_context",
            state="observed_fact",
            dataset_scope=_DATASET_SCOPE,
            source_reference=f"{contract_path}#chronology-experiments-and-availability",
            source_section="Released HDF5 scalar table",
            details=(
                ("source_order", "20,23,15"),
                ("row_counts", "223,303,303"),
                ("canonical_day_labels", "all null"),
            ),
        ),
        EvidenceRecord(
            subject="experiment_20_context",
            state="observed_fact",
            dataset_scope=f"{_DATASET_SCOPE}/experiment/20",
            source_reference=(
                f"{contract_path}#intervention-alignment-evidence--inferred-not-a-day-assignment"
            ),
            source_section="Released HDF5 scalar table grouped in source order",
            details=(
                ("mold_temperature", "all null"),
                ("source_charge_code", "all null"),
            ),
            runs=tuple(
                EvidenceRun(20, "mean_moisture_content", count, value, None, "released_raw")
                for count, value in ((76, 0.086), (86, 0.180), (61, 0.046))
            ),
        ),
        EvidenceRecord(
            subject="experiment_23_context",
            state="observed_fact",
            dataset_scope=f"{_DATASET_SCOPE}/experiment/23",
            source_reference=(
                f"{contract_path}#intervention-alignment-evidence--inferred-not-a-day-assignment"
            ),
            source_section="Released HDF5 scalar table grouped in source order",
            details=(("mean_moisture_content", "all null"),),
            runs=(
                EvidenceRun(23, "mold_temperature", 99, 80.0, None, "released_raw"),
                EvidenceRun(23, "mold_temperature", 103, 90.0, None, "released_raw"),
                EvidenceRun(23, "mold_temperature", 101, 70.0, None, "released_raw"),
                EvidenceRun(23, "source_charge_code", 152, 1.0, None, "released_raw"),
                EvidenceRun(23, "source_charge_code", 151, 2.0, None, "released_raw"),
            ),
        ),
        EvidenceRecord(
            subject="experiment_to_paper_day",
            state="inference",
            dataset_scope=_DATASET_SCOPE,
            source_reference=(
                f"{contract_path}#intervention-alignment-evidence--inferred-not-a-day-assignment"
            ),
            source_section="Project comparison of released runs with paper Table 2",
            details=(("authority", "run-length comparison only; not canonical labels"),),
            associations=tuple(
                EvidenceAssociation(experiment, day, "matching intervention run lengths")
                for experiment, day in ((20, 2), (23, 3), (15, 1))
            ),
        ),
        EvidenceRecord(
            subject="experiment_15_moisture",
            state="discrepancy",
            dataset_scope=f"{_DATASET_SCOPE}/experiment/15",
            source_reference=(
                f"{contract_path}#intervention-alignment-evidence--inferred-not-a-day-assignment"
            ),
            source_section="Released HDF5 scalar table versus paper Table 2",
            details=(("canonical_action", "preserve raw values; no backfill"),),
            runs=(
                EvidenceRun(15, "mean_moisture_content", 89, 0.050, None, "released_raw"),
                EvidenceRun(15, "mean_moisture_content", 89, 0.066, "%", "paper"),
                EvidenceRun(15, "mean_moisture_content", 98, 0.100, None, "released_raw"),
                EvidenceRun(15, "mean_moisture_content", 98, 0.097, "%", "paper"),
                EvidenceRun(15, "mean_moisture_content", 116, 0.150, None, "released_raw"),
                EvidenceRun(15, "mean_moisture_content", 116, 0.150, "%", "paper"),
            ),
        ),
        EvidenceRecord(
            subject="paper_scalar_feature_set",
            state="documented_fact",
            dataset_scope=_DATASET_SCOPE,
            source_reference=f"{contract_path}#published-feature-set-versus-retained-source-columns",
            source_section="Paper sections 2.2.1, 2.2.3 and 3.2",
            details=(
                ("count", "12"),
                ("moisture_used", "false"),
                ("direct_export_correspondences", "11"),
                (
                    "conceptual_features",
                    "maximum injection pressure; switchover injection pressure; melt cushion; "
                    "injection time; hot-runner temperature; barrel heating zones 2-8",
                ),
            ),
        ),
        EvidenceRecord(
            subject="hot_runner_export_crosswalk",
            state="inference",
            dataset_scope=_DATASET_SCOPE,
            source_reference=f"{contract_path}#published-feature-set-versus-retained-source-columns",
            source_section="Project name comparison; no publisher crosswalk located",
            details=(
                ("source_field", "werkzeugheizkreis_1"),
                ("proposed_concept", "hot-runner temperature"),
                ("confirmed", "false"),
            ),
        ),
        EvidenceRecord(
            subject="geometry_scale",
            state="inference",
            dataset_scope=_DATASET_SCOPE,
            source_reference=f"{contract_path}#target-agreement-and-disagreement",
            source_section="Project full-population comparison with published summary",
            details=(("canonical_action", "native values and null units"),),
            quantities=(
                EvidenceQuantity("GE-GE002*_scaled_mean", 101.559141, "native_value x 0.001"),
                EvidenceQuantity(
                    "GE-GE002*_scaled_population_variance",
                    0.00680747,
                    "(native_value x 0.001)^2",
                ),
            ),
        ),
        EvidenceRecord(
            subject="mvp_target",
            state="project_policy",
            dataset_scope=_DATASET_SCOPE,
            source_reference=f"{contract_path}#accepted-mvp-use-and-claim-boundary",
            source_section="Project accepted MVP policy",
            details=(
                ("target", "weight"),
                ("unit", "g"),
                ("geometry", "retained but deferred"),
                ("modeling_boundary", "process-derived predictors only; allowlist deferred to M3"),
            ),
        ),
        EvidenceRecord(
            subject="published_release_completeness",
            state="unresolved",
            dataset_scope=_DATASET_SCOPE,
            source_reference=f"{contract_path}#accepted-mvp-use-and-claim-boundary",
            source_section="Published repository and bounded follow-up search",
            details=(
                ("known", "pinned published release"),
                ("not_claimed", "complete original laboratory database"),
            ),
        ),
        EvidenceRecord(
            subject="production_days_and_spec_limits",
            state="unresolved",
            dataset_scope=_DATASET_SCOPE,
            source_reference=f"{contract_path}#canonical-bundle-handoff",
            source_section="Canonical source-gap contract",
            details=(
                ("production_day", "null"),
                ("lower_spec", "null"),
                ("upper_spec", "null"),
            ),
        ),
    )


def _canonicalize_validated(
    source: ValidatedInjectionMoldingSource,
    *,
    expectations: _CanonicalExpectations,
    mapping: Mapping[str, tuple[str, str]] = SCALAR_MAPPING,
    production: bool,
) -> ManufacturingBundle:
    cycles = _validate_handoff(source, expectations, mapping, production=production)
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

    expected_experiments = tuple(
        (int(experiment), int(count))
        for experiment, count in context.group_by("experiment_id", maintain_order=True).len().rows()
    )
    if expected_experiments != expectations.experiment_blocks:
        _fail("bundle.experiments", f"experiment order/counts differ: {expected_experiments!r}")
    if quality["measured_value"].null_count() != expectations.quality_nulls:
        _fail("bundle.quality", "quality null count differs from the contract")
    observed_context_nulls = tuple(
        (name, context[name].null_count()) for name, _ in expectations.context_nulls
    )
    if observed_context_nulls != expectations.context_nulls:
        _fail("bundle.context", "context null counts differ from the contract")
    table_counts = (
        ("units", units.height),
        ("operations", operations.height),
        ("process_features", process_features.height),
        ("signals", signals.height),
        ("quality", quality.height),
        ("context", context.height),
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
        manifest_sha256=source.manifest_sha256,
        validator_version=source.validator_version,
        adapter_version=ADAPTER_VERSION,
        schema_version=SCHEMA_VERSION,
        mapping_version=MAPPING_VERSION,
        project_version=source.project_version,
        verified_receipt_path=str(source.receipt_path) if source.receipt_path else None,
        source_contract_reference=SOURCE_CONTRACT_REFERENCE,
        citations=(
            "Bogedale et al. (2023), Online Prediction of Molded Part Quality in the "
            "Injection Molding Process Using High-Resolution Time Series, "
            "https://doi.org/10.3390/polym15040978",
            f"https://github.com/sc4t1m/scatimdata/tree/{source.source_version}",
        ),
        license_name="CC BY 4.0",
        license_url="https://creativecommons.org/licenses/by/4.0/legalcode.en",
        scalar_lineage=_build_lineage(mapping),
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
        transformations=(
            "source-order projection to admitted scalar cycle identities",
            "key-based pressure and flow lookup using independent source mappings",
            "source NaN converted to typed canonical null",
            "integer geometry widened exactly to nullable Float64",
            "pressure elapsed-time axis selected after pressure/flow agreement at "
            f"atol={_TIME_TOLERANCE}",
            "no imputation, unit conversion, geometry conversion, resampling, "
            "normalization or source repair",
        ),
        table_counts=table_counts,
        exclusions=exclusions,
        evidence=_evidence(),
        validation_checks=tuple(
            (check.check_id, check.expected, check.observed) for check in source.checks
        ),
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


def _validate_bundle(bundle: ManufacturingBundle, expectations: _CanonicalExpectations) -> None:
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
            _fail("bundle.schema", f"{name} schema differs from version {SCHEMA_VERSION}")
    unit_ids = tables["units"]["unit_id"]
    if unit_ids.null_count() or unit_ids.n_unique() != expectations.scalar_rows:
        _fail("bundle.keys", "unit IDs must be nonnull and unique")
    operation_ids = tables["operations"]["operation_id"]
    if operation_ids.null_count() or operation_ids.n_unique() != expectations.scalar_rows:
        _fail("bundle.keys", "operation IDs must be nonnull and unique")
    unit_set = set(cast(list[str], unit_ids.to_list()))
    operation_set = set(cast(list[str], operation_ids.to_list()))
    expected_operation_ids = [f"{unit_id}/injection_molding" for unit_id in unit_ids]
    if tables["operations"]["unit_id"].to_list() != unit_ids.to_list() or (
        operation_ids.to_list() != expected_operation_ids
    ):
        _fail("bundle.references", "operations do not map one-to-one to units in source order")
    for name in ("process_features", "context"):
        if tables[name]["unit_id"].to_list() != unit_ids.to_list() or (
            tables[name]["operation_id"].to_list() != operation_ids.to_list()
        ):
            _fail("bundle.references", f"{name} unit/operation rows are not aligned")
    for name, table in tables.items():
        if (
            "unit_id" in table.columns
            and set(cast(list[str], table["unit_id"].unique().to_list())) != unit_set
        ):
            _fail("bundle.references", f"{name} unit references differ")
        if (
            "operation_id" in table.columns
            and set(cast(list[str], table["operation_id"].unique().to_list())) != operation_set
        ):
            _fail("bundle.references", f"{name} operation references differ")
    expected_rows = expectations.scalar_rows
    if (
        tuple(
            tables[name].height for name in ("units", "operations", "process_features", "context")
        )
        != (expected_rows,) * 4
    ):
        _fail("bundle.counts", "unit-grain table counts differ")
    if tables["signals"].height != expected_rows * expectations.signal_samples:
        _fail("bundle.counts", "signal row count differs")
    if tables["quality"].height != expected_rows * len(_QUALITY_FIELDS):
        _fail("bundle.counts", "quality row count differs")
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
    if set(_QUALITY_FIELDS) & set(tables["process_features"].columns):
        _fail("bundle.leakage", "quality target leaked into process features")
    if (
        tables["quality"]["lower_spec"].null_count() != tables["quality"].height
        or tables["quality"]["upper_spec"].null_count() != tables["quality"].height
    ):
        _fail("bundle.quality", "source-absent specification limits must remain null")
    if tables["context"]["production_day"].null_count() != expected_rows:
        _fail("bundle.context", "source-absent production days must remain null")
    excluded_ids = {item.unit_id for item in bundle.metadata.exclusions}
    if len(excluded_ids) != expectations.signal_only or unit_set & excluded_ids:
        _fail("bundle.exclusions", "excluded signal-only IDs are incomplete or admitted")


def canonicalize_injection_molding(
    source: ValidatedInjectionMoldingSource,
) -> ManufacturingBundle:
    """Map a pinned, production-validated Dataset 2 source into memory."""
    return _canonicalize_validated(
        source,
        expectations=_CanonicalExpectations(),
        production=True,
    )
