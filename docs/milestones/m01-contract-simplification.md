# M1 — Portfolio-sized data contract

One current, unversioned artifact layout. No legacy readers, schema-version
fields, adapters or migration machinery. This replaces the pre-release cleanup
plans; there are no deployed artifact consumers.

## Ownership

- Source manifests own admission, upstream commit and archive hashes.
- Raw validation owns source schema, native timestamps and cycle membership.
- Canonicalization owns six tables and scientific invariants.
- Metadata owns provenance, lineage, actual exclusions and research context.
- Packaged JSON preserves all 15 research records without executable constructors.
- The artifact manifest contains only required payload names and hashes.
- Loading needs no network, raw files, configuration, Git or current research file.

Upstream source commits and the Python package version are provenance, not artifact
schema versions. Future roadmap releases do not impose data compatibility.

## Workflow

Acquire the pinned source, prepare it at
`data/processed/injection_molding/dataset2`, and use `load_bundle(path)`.
The folder contains six Parquet tables, `metadata.json` and `manifest.json`.
Extra analyst notes are allowed. Equivalent output reuses existing files unchanged;
different or corrupt output fails without automatic repair or overwrite.

No versioned output folders or old-schema recovery paths are maintained. Retired
generated copies are removed in the explicit clean cutover; raw evidence remains.
Preparation recreates the current artifact from that raw source.

## Scientific boundary and verification

Preserve all 829 labeled units, 92 actual exclusions, 40 scalar fields, pressure
and flow joined independently by cycle, and the released 2,048-point irregular grid.
Retain experiment order 20/23/15 (223/303/303), weight in grams, deferred geometry,
unknown units and null production days/specification limits. Retention is not
model feature eligibility.

Independent full-source comparison established exact scalar and trajectory values,
nulls, lineage, exclusions and research context. The unversioned cutover changes
artifact labeling, not scientific transformations. Verify ordinary preparation,
standalone loading, unchanged reuse and configured checks.

The [M1 summary](m01-injection-molding-ingestion.md) and
[roadmap](../implementation-roadmap.md) own progress. M2 audit planning is next.
