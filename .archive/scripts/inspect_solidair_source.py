"""Stream a SoliDAIR CSV release into a safe, aggregate discovery report."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

MISSING_TOKENS = frozenset({"", "na", "n/a", "nan", "none", "null"})


@dataclass
class ColumnStats:
    """Aggregate observations for one CSV column."""

    blank_or_token_missing: int = 0
    non_numeric: int = 0
    non_finite_numeric: int = 0
    finite_numeric: int = 0
    minimum: float | None = None
    maximum: float | None = None

    def observe(self, value: str) -> None:
        stripped = value.strip()
        if stripped.lower() in MISSING_TOKENS:
            self.blank_or_token_missing += 1
            return
        try:
            numeric = float(stripped)
        except ValueError:
            self.non_numeric += 1
            return
        if not math.isfinite(numeric):
            self.non_finite_numeric += 1
            return
        self.finite_numeric += 1
        self.minimum = numeric if self.minimum is None else min(self.minimum, numeric)
        self.maximum = numeric if self.maximum is None else max(self.maximum, numeric)

    def as_dict(self) -> dict[str, int | float | None]:
        return {
            "blank_or_token_missing": self.blank_or_token_missing,
            "non_numeric": self.non_numeric,
            "non_finite_numeric": self.non_finite_numeric,
            "finite_numeric": self.finite_numeric,
            "minimum": self.minimum,
            "maximum": self.maximum,
        }


def file_hash(path: Path, algorithm: str) -> str:
    """Hash a file without loading it into memory."""
    digest = hashlib.new(algorithm)
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def inspect_csv(path: Path, target_columns: Sequence[str]) -> dict[str, Any]:
    """Return structural and aggregate evidence for one CSV file."""
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.reader(handle)
        try:
            header = next(reader)
        except StopIteration as error:
            raise ValueError(f"CSV has no header: {path}") from error

        if not header or len(set(header)) != len(header):
            raise ValueError(f"CSV header is empty or contains duplicate names: {path}")

        missing_targets = sorted(set(target_columns) - set(header))
        if missing_targets:
            raise ValueError(f"CSV is missing target columns {missing_targets}: {path}")

        target_indexes = {header.index(name) for name in target_columns}
        feature_indexes = [index for index in range(len(header)) if index not in target_indexes]
        column_stats = [ColumnStats() for _ in header]
        row_digests: set[bytes] = set()
        duplicate_row_digest_occurrences = 0
        malformed_rows = 0
        row_count = 0
        trace_row_number: int | None = None

        for row_count, row in enumerate(reader, start=1):
            if len(row) != len(header):
                malformed_rows += 1
                continue

            for stats, value in zip(column_stats, row, strict=True):
                stats.observe(value)

            digest = hashlib.sha256("\x1f".join(row).encode("utf-8")).digest()
            if digest in row_digests:
                duplicate_row_digest_occurrences += 1
            else:
                row_digests.add(digest)

            if trace_row_number is None:
                targets_present = all(
                    row[index].strip().lower() not in MISSING_TOKENS for index in target_indexes
                )
                features_present = any(
                    row[index].strip().lower() not in MISSING_TOKENS for index in feature_indexes
                )
                if targets_present and features_present:
                    trace_row_number = row_count

    return {
        "filename": path.name,
        "bytes": path.stat().st_size,
        "md5": file_hash(path, "md5"),
        "sha256": file_hash(path, "sha256"),
        "row_count": row_count,
        "column_count": len(header),
        "columns": header,
        "target_columns": list(target_columns),
        "candidate_feature_columns": [header[index] for index in feature_indexes],
        "malformed_row_count": malformed_rows,
        "duplicate_row_digest_occurrences": duplicate_row_digest_occurrences,
        "duplicate_detection": "SHA-256 digest of the parsed row values in source order",
        "column_observations": {
            name: stats.as_dict() for name, stats in zip(header, column_stats, strict=True)
        },
        "trace": {
            "data_row_number": trace_row_number,
            "meaning": (
                "First structurally valid row with every declared target and at least one "
                "candidate feature present; values intentionally omitted."
            ),
        },
    }


def parse_named_path(value: str) -> tuple[str, Path]:
    """Parse NAME=PATH arguments."""
    name, separator, raw_path = value.partition("=")
    if not separator or not name or not raw_path:
        raise argparse.ArgumentTypeError("expected NAME=PATH")
    return name, Path(raw_path)


def build_report(
    metadata_path: Path,
    csv_inputs: Sequence[tuple[str, Path]],
    target_columns: Sequence[str],
) -> dict[str, Any]:
    """Combine Zenodo record identity with aggregate CSV inspection evidence."""
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    upstream_files = {
        item["key"]: {
            "bytes": item["size"],
            "checksum": item["checksum"],
            "download_url": item["links"]["self"],
        }
        for item in metadata["files"]
    }
    inspected = {name: inspect_csv(path, target_columns) for name, path in csv_inputs}
    for item in inspected.values():
        upstream = upstream_files.get(item["filename"])
        if upstream is None:
            raise ValueError(f"{item['filename']} is absent from the Zenodo record")
        expected_md5 = upstream["checksum"].removeprefix("md5:")
        item["zenodo_md5_matches"] = item["md5"] == expected_md5
        item["zenodo_size_matches"] = item["bytes"] == upstream["bytes"]

    return {
        "report_schema": "solidair-source-inspection/v1",
        "record": {
            "id": metadata["id"],
            "doi": metadata["doi"],
            "title": metadata["metadata"]["title"],
            "publication_date": metadata["metadata"]["publication_date"],
            "version": metadata["metadata"].get("version"),
            "license": metadata["metadata"]["license"]["id"],
            "access_right": metadata["metadata"]["access_right"],
            "metadata_sha256": file_hash(metadata_path, "sha256"),
            "files": upstream_files,
        },
        "inspection_scope": (
            "Complete streaming scan of listed CSV inputs; no row values are emitted. "
            "Semantic roles come from the separately cited publisher description."
        ),
        "csv": inspected,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--metadata", required=True, type=Path)
    parser.add_argument("--csv", action="append", required=True, type=parse_named_path)
    parser.add_argument("--target", action="append", required=True)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    report = build_report(args.metadata, args.csv, args.target)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
