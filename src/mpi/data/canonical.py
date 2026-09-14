"""Canonical manufacturing tables and source metadata."""

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
    """Source identity, field mappings and scientific limitations."""

    dataset: str
    candidate: str
    source_version: str
    archive_size: int
    archive_sha256: str
    manifest_sha256: str
    source_contract_reference: str
    citations: tuple[str, ...]
    license_name: str
    license_url: str
    scalar_lineage: tuple[FieldLineage, ...]
    signal_lineage: tuple[SignalLineage, ...]
    transformations: tuple[str, ...]
    exclusions: tuple[ExcludedUnit, ...]
    limitations: tuple[str, ...]
    retained_optional_source_groups: tuple[str, ...]
    retained_optional_process_fields: tuple[str, ...]


@dataclass(frozen=True)
class ManufacturingBundle:
    """Six ordinary Polars tables; callers use expressions to derive new tables."""

    units: pl.DataFrame
    operations: pl.DataFrame
    process_features: pl.DataFrame
    signals: pl.DataFrame
    quality: pl.DataFrame
    context: pl.DataFrame
    metadata: BundleMetadata
