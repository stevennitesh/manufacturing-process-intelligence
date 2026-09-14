"""Typed, protected canonical manufacturing-bundle handoff."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import polars as pl


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
class BundleMetadata:
    """The sole provenance, lineage, research-context and policy record."""

    dataset: str
    candidate: str
    source_version: str
    archive_size: int
    archive_sha256: str
    manifest_sha256: str
    project_version: str
    verified_receipt_path: str | None
    source_repository_url: str | None
    prepared_at_utc: str | None
    acquisition_time_utc: str | None
    acquisition_time_source: str | None
    acquisition_time_unavailable_reason: str | None
    git_commit: str | None
    git_dirty: bool | None
    git_unavailable_reason: str | None
    source_contract_reference: str
    citations: tuple[str, ...]
    license_name: str
    license_url: str
    scalar_lineage: tuple[FieldLineage, ...]
    signal_lineage: tuple[SignalLineage, ...]
    transformations: tuple[str, ...]
    exclusions: tuple[ExcludedUnit, ...]
    research_context: tuple[dict[str, object], ...]
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
