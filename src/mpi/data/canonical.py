"""Typed, protected canonical manufacturing-bundle handoff."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import polars as pl

EvidenceState = Literal[
    "documented_fact",
    "observed_fact",
    "inference",
    "discrepancy",
    "project_policy",
    "unresolved",
]


@dataclass(frozen=True)
class FieldLineage:
    """One source scalar field's sole canonical owner."""

    source_group: str
    source_name: str
    canonical_section: str
    canonical_name: str
    source_dtype: str
    canonical_dtype: str
    unit: str | None
    unit_status: Literal["documented", "unresolved", "not_applicable"]
    representation_change: str | None = None


@dataclass(frozen=True)
class SignalLineage:
    """Reversible source-channel mapping for one canonical signal."""

    source_group: str
    source_time_field: str
    source_column_pattern: str
    canonical_field: str
    canonical_time_field: str
    source_dtype: str
    canonical_dtype: str
    time_unit: str
    unit: str | None
    unit_status: Literal["documented", "unresolved"]


@dataclass(frozen=True)
class ExcludedUnit:
    """A source signal identity intentionally excluded from admitted tables."""

    unit_id: str
    cycle_counter: int
    reason: str


@dataclass(frozen=True)
class EvidenceQuantity:
    """One named numeric quantity with its own declared unit."""

    name: str
    value: float
    unit: str


@dataclass(frozen=True)
class EvidenceRun:
    """A contiguous observed or published run bound to an experiment and field."""

    experiment_id: int
    field: str
    count: int
    value: float
    unit: str | None
    value_source: Literal["released_raw", "paper"]


@dataclass(frozen=True)
class EvidenceAssociation:
    """An explicitly non-authoritative proposed identity association."""

    source_experiment_id: int
    proposed_paper_day: int
    basis: str


@dataclass(frozen=True)
class EvidenceRecord:
    """Structured semantic evidence with explicit epistemic state and scope."""

    subject: str
    state: EvidenceState
    dataset_scope: str
    source_reference: str
    source_section: str
    details: tuple[tuple[str, str], ...] = ()
    quantities: tuple[EvidenceQuantity, ...] = ()
    runs: tuple[EvidenceRun, ...] = ()
    associations: tuple[EvidenceAssociation, ...] = ()


@dataclass(frozen=True)
class BundleMetadata:
    """Immutable provenance, lineage, evidence and policy bound to a bundle."""

    dataset: str
    candidate: str
    source_version: str
    archive_size: int
    archive_sha256: str
    manifest_sha256: str
    validator_version: str
    adapter_version: str
    schema_version: str
    mapping_version: str
    project_version: str
    verified_receipt_path: str | None
    source_contract_reference: str
    citations: tuple[str, ...]
    license_name: str
    license_url: str
    scalar_lineage: tuple[FieldLineage, ...]
    signal_lineage: tuple[SignalLineage, ...]
    transformations: tuple[str, ...]
    table_counts: tuple[tuple[str, int], ...]
    exclusions: tuple[ExcludedUnit, ...]
    evidence: tuple[EvidenceRecord, ...]
    validation_checks: tuple[tuple[str, str, str], ...]
    limitations: tuple[str, ...]
    retained_optional_source_groups: tuple[str, ...]
    retained_optional_process_fields: tuple[str, ...]


class ManufacturingBundle:
    """Complete canonical tables with copy-on-access protection.

    Polars dataframes are cloned on ingestion and on every public access. This
    prevents a consumer from mutating the bundle's passed-check table handles.
    Polars' immutable Arrow buffers make cloning inexpensive while subsequent
    dataframe replacement remains isolated from the stored bundle.
    """

    __slots__ = (
        "__context",
        "__metadata",
        "__operations",
        "__process_features",
        "__quality",
        "__signals",
        "__units",
    )

    def __init__(
        self,
        *,
        units: pl.DataFrame,
        operations: pl.DataFrame,
        process_features: pl.DataFrame,
        signals: pl.DataFrame,
        quality: pl.DataFrame,
        context: pl.DataFrame,
        metadata: BundleMetadata,
    ) -> None:
        self.__units = units.clone()
        self.__operations = operations.clone()
        self.__process_features = process_features.clone()
        self.__signals = signals.clone()
        self.__quality = quality.clone()
        self.__context = context.clone()
        self.__metadata = metadata

    @property
    def units(self) -> pl.DataFrame:
        return self.__units.clone()

    @property
    def operations(self) -> pl.DataFrame:
        return self.__operations.clone()

    @property
    def process_features(self) -> pl.DataFrame:
        return self.__process_features.clone()

    @property
    def signals(self) -> pl.DataFrame:
        return self.__signals.clone()

    @property
    def quality(self) -> pl.DataFrame:
        return self.__quality.clone()

    @property
    def context(self) -> pl.DataFrame:
        return self.__context.clone()

    @property
    def metadata(self) -> BundleMetadata:
        return self.__metadata
