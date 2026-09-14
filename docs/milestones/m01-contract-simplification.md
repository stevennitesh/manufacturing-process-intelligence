# M1 — Portfolio-sized data contract

One current, unversioned layout: six Parquet tables and `metadata.json`.
No legacy readers, schema versions, artifact registry or migration machinery.

## Ownership

- Source manifests own admission, upstream commit and raw archive hashes.
- Raw validation owns source schema, native timestamps and cycle membership.
- Canonicalization owns table mappings, joins, null representation and units.
- Metadata carries source identity, license, lineage, transformations, exclusions
  and limitations. Research evidence stays in
  [dataset documentation](../datasets/injection-molding-source-contract.md).
- Persistence writes tables and metadata. Loading checks schema, not source science
  or generated-file checksums. Tables are ordinary Polars dataframes.

## Workflow

Acquire the pinned source, prepare it at
`data/processed/injection_molding/dataset2`, and use `load_bundle(path)`.
Preparation reuses an existing output from the configured source without raw
revalidation or exact table comparisons. Reuse does not establish freshness after
code changes; explicitly remove generated output or select a new directory to
regenerate. Existing files are never overwritten; failed writes may leave an
incomplete directory for inspection. No automatic repair or concurrent writer
support is promised.

## Scientific boundary

Preserve 829 labeled units, 92 actual exclusions, 40 scalar fields, independent
pressure/flow cycle joins and the native 2,048-point irregular grid.
Keep experiment order 20/23/15 (223/303/303), weight in grams, deferred geometry,
unknown units and null production days/specification limits. Retention does not
grant model-feature eligibility.

The [M1 summary](m01-injection-molding-ingestion.md) owns completion evidence.
[M2 audit planning](../implementation-roadmap.md) is next.
