# SoliDAIR source contract

**Status:** ready for noncommercial-research acquisition and adapter work, with
explicit semantic limitations.

**Evidence date:** 2026-09-12.

This contract selects the production portion of the authoritative 2026 SoliDAIR
Bosch release for the predictive-quality MVP. It distinguishes publisher claims,
full-file observations, proposed adapter mappings, and unresolved semantics. It
does not implement acquisition or an adapter and does not authorize broader use.

## Authority and selected release

The selected distribution is Hakan Cem Muslu's Bosch-affiliated Zenodo record
[22300180](https://zenodo.org/records/22300180),
[DOI 10.5281/zenodo.22300180](https://doi.org/10.5281/zenodo.22300180), titled
*SoliDAIR quality prediction, production, and simulation data UC BOS* and
published 2026-09-04. The associated description identifies Robert Bosch GmbH as
the original provider and the SoliDAIR Bosch use case as its project context.
The SoliDAIR project's public data-management plan independently designates the
[SoliDAIR Zenodo community](https://zenodo.org/communities/solidair/) for open,
anonymized project datasets.

Primary publisher evidence accessed 2026-09-12:

- [Zenodo record metadata](https://zenodo.org/api/records/22300180) and the
  [publisher description PDF](https://zenodo.org/api/records/22300180/files/20260904_OpenDataset%20Description%20Form.pdf/content);
- SoliDAIR deliverable
  [D1.4 Data Management Plan](https://www.solidair-project.eu/_files/ugd/a34356_7e9cd32d69c74d2f9150206cc0980eff.pdf),
  which names the project's Zenodo community; and
- the [older record metadata](https://zenodo.org/api/records/17661875) and
  [older description PDF](https://zenodo.org/api/records/17661875/files/20251006_OpenDataset%20Description%20Form.pdf/content)
  used only for release comparison.

The visible Zenodo landing page labels this release `v1`, while the API leaves
`metadata.version` unset (and separately exposes version relations). The discovery
manifest therefore retains API `version: null`, records
`landing_page_version_label: "v1"`, and uses record ID 22300180, DOI, filenames,
byte sizes, and cryptographic hashes as the stable contract identity. The
description PDF says "August 2026" while Zenodo publishes the record on
2026-09-04; this is recorded as a source-description date versus repository
publication date, not silently reconciled into a different release.

### Release selection

The earlier authoritative record [17661875](https://zenodo.org/records/17661875),
published 2025-11-20, contains a 1,000-row CSV described as 67 inputs and four
outputs. Its description warns that the released features showed very low
correlation with the EoL label. The selected 2026 record instead contains 510,050
production injectors with 30 columns, explicitly separates production from a
small hydraulic simulation table, and identifies five EoL parameters. It is the
stronger fit for the MVP's real-production, upstream-process-to-quality question.
The older record is comparison evidence, not a supported adapter input.

## Access and terms

Zenodo marks record 22300180 open. On 2026-09-12 its public API metadata and all
three file-content URLs were accessible over HTTPS without authentication,
interactive terms acceptance, or credentials. Automated acquisition is therefore
technically supported by the observed public endpoints, subject to normal network
and upstream-availability failures.

Both Zenodo metadata and the publisher PDF specify
[CC BY-NC-ND 4.0](https://creativecommons.org/licenses/by-nc-nd/4.0/). Local use
and reproduction for noncommercial research are supported, subject to the
license. Commercial use is not licensed; sharing Adapted Material is prohibited;
and the status of specific models, reports, processed tables, or other derived
artifacts must be assessed before redistribution. The precise repository boundary
and official legal-code links are maintained in [DATA_LICENSES.md](../../DATA_LICENSES.md).
Public visibility alone is not treated as broader permission.

## Release inventory and selected bundle

| File | Publisher role | Size | SHA-256 | MVP handling |
| --- | --- | ---: | --- | --- |
| `20260904_OpenDataset Description Form.pdf` | Provenance, structure, semantics, and license | 67,955 B | `acaedeebed2d83fc5525257962326aee429357e6094047eddf6370ff661d86e9` | Required documentation evidence |
| `production_data.csv` | Anonymized production-line injector measurements | 137,713,757 B | `46c18905dc9ff588ec6c764f03779916f4879b260cc47134a9e6bfe07431cb30` | Required MVP data input |
| `simulation_data.csv` | Synthetic 1D hydraulic-injector simulation | 50,490 B | `f63a06fd4d5593baf019ac1068aa1d81e9c75457827f8e57c6635a9f0a8fbdb0` | Inventory and comparison only; excluded from minimal MVP bundle |

The smallest supported production bundle is the description PDF plus
`production_data.csv`, tied to the Zenodo API metadata. The simulation CSV was
inspected because it establishes a distinct release role, but mixing its rows with
production would erase provenance and is unsupported. All downloaded bytes remain
under ignored `data/raw/solidair/`; none are version controlled.

## Publisher-declared meaning

The publisher description states:

- the production data came directly from sensor measurement systems on a
  high-volume automotive fuel-injector production line and represents raw
  manufacturing data;
- each CSV row corresponds to one injector;
- production columns are parameters from multiple manufacturing stations,
  including the End-of-Line (EoL) station;
- exactly `input_1`, `input_2`, `input_3`, `input_4`, and `input_5` correspond to
  parameters measured at EoL;
- the intended supervised task is continuous EoL-value regression from input
  features; threshold-based OK/NOK is conditional on thresholds being defined;
- names are obfuscated and numeric values transformed to protect confidential
  process information; and
- the simulation inputs include production-process data while its outputs are
  simulated EoL parameters.

The misleading `input_*` names do not override the publisher's explicit EoL
designation. Units and transformation formulas are not disclosed.

## Reproducible full-file inspection

Run from the repository root after placing byte-identical release files under
`data/raw/solidair/`:

```powershell
uv run python scripts/inspect_solidair_source.py `
  --metadata data/raw/solidair/zenodo-22300180-metadata.json `
  --csv production=data/raw/solidair/production_data.csv `
  --csv simulation=data/raw/solidair/simulation_data.csv `
  --target input_1 --target input_2 --target input_3 --target input_4 --target input_5 `
  --output artifacts/discovery/solidair/inspection.json
```

The script streams every row and emits only file identity, structure, aggregate
column observations, duplicate-row-digest counts, and a value-free trace pointer.
The generated report is local and ignored; the safe aggregate result is captured
in the discovery manifest.

| Observed property | Production | Simulation |
| --- | ---: | ---: |
| Data rows | 510,050 | 800 |
| Columns | 30 | 7 |
| Malformed-width rows | 0 | 0 |
| Blank or recognized missing-token cells | 0 | 0 |
| Non-numeric or non-finite cells | 0 | 0 |
| Repeated parsed-row SHA-256 digest occurrences | 0 | 0 |

All upstream MD5 values and byte sizes matched the Zenodo record; local SHA-256
values are in the manifest. The production header is:

```text
ratio, as, ioff, ion, bounce, closing, input_x,
input_1, input_2, input_3, input_4, input_5,
input_std_1, input_std_2, input_std_3, input_std_4, input_std_5,
pinput_1, pinput_2, pinput_3, pinput_4, pinput_5,
sd1_closing, sd2_closing, sd3_closing, sd4_closing, sd5_closing,
qh, sz, st70
```

Every production value observed in the complete scan is finite numeric and falls
between 0 and 1. This is an observation, not evidence of a particular
normalization method, physical unit, or specification interval. Simulation values
are also complete finite numerics, but not all fall in that interval.

### Actual row-to-target trace

Production data row 1 (the first row after the header) contains a finite numeric
value in every one of the 25 candidate pre-EoL fields and all five documented EoL
fields. It therefore traces one publisher-declared injector observation from
same-row process measurements to five downstream quality measurements without a
cross-file join. The source values are intentionally omitted from versioned
evidence. The raw SHA-256 plus one-based data-row number makes the trace exactly
reproducible.

This proves the mapping exists for that actual row; the full scan additionally
establishes structural completeness for this file. It does not prove that all rows
represent distinct physical injectors, that retests are absent, or that there are
no semantically duplicated measurements.

## DatasetBundle handoff

| Bundle portion | Proposed selected-release mapping | Contract boundary |
| --- | --- | --- |
| `units` | One entry per production CSV row. Derive a stable surrogate `unit_id` from selected release/file identity and one-based data-row number. | This is an observation key, not a recovered injector serial number. Store raw hash and row number separately in provenance. No batch, product type, or timestamp field is available. |
| `process_features` | Same surrogate key plus the 25 production columns other than `input_1`–`input_5`. Preserve source names and numeric values. | These are candidate pre-EoL predictors, not individually verified upstream fields. Exact station, physical meaning, unit, acquisition time, and availability relative to prediction are undisclosed; audit them for leakage before modeling. |
| `quality` | Five long-form records per unit with `characteristic` equal to each original `input_1`–`input_5` name and `value` equal to the same-row numeric value. | The publisher verifies EoL role, but not physical characteristic names or units. Preserve values as transformed source-scale measurements. Do not derive pass/fail. |
| `metadata` | Record/DOI, source URLs, API version value, landing-page `v1` label, release and file hashes, access date, license ID, original column order, publisher provenance, production/simulation role, and anonymization/transformation notice. | Preserve the distinction between API and landing-page version evidence and every semantic unknown. Split strategy remains unimplemented for M2. |

The adapter must reject a missing or duplicated header, missing EoL column,
malformed row width, nonnumeric/nonfinite value, or raw hash mismatch. The source
currently presents no missing values; no imputation or special numeric missing
code is justified. Preserve rows and original precision. A deterministic surrogate
key must not be used as a predictive feature.

## Known limitations and dependency impact

| Unknown or absent evidence | What is known | Impact and resolution owner |
| --- | --- | --- |
| Physical identity and retests | Publisher says one row is one injector; there is no serial/key column and no exact duplicate parsed row. | Adapter may create only a provenance-derived observation key. Claims about unique physical units or retest handling remain unsupported; raise if later identity evidence appears. |
| Feature timing and station assignment | Five named fields are explicitly EoL; the remaining fields come from production stations but individual station/order semantics are absent. | Adapter can preserve candidate features, but the M1 audit must flag leakage risk and M2 must not call evaluation leakage-safe without availability evidence. |
| Units and transform formulas | Values were transformed; production values are observed in `[0, 1]`. | Store transformed source-scale values and unknown units. Do not invert, rescale, or interpret effect sizes physically. |
| Batch, lot, run, product type, and timestamps | No such fields are documented or identifiable in the header. Row order has no declared chronological meaning. | M2 cannot justify grouped or temporal splits from this release; it must record the limitation rather than fabricate groups/time. |
| Specification limits | Publisher discusses thresholds conditionally but supplies none. | Continuous regression targets are supported. Pass/fail labels and specification-aware inspection policy are unsupported until authoritative limits are obtained. |
| Derived-artifact redistribution and commercial use | CC BY-NC-ND 4.0 applies; no broader permission is documented. | Resolve legal/licensing status before sharing transformed data/ambiguous derivatives or any commercial deployment. |

## Readiness verdict

The source contract is **ready for the next M1 work package for noncommercial
research**. Authority, precise release identity, public acquisition path, license,
production provenance, same-row unit-to-five-EoL mapping, input coverage, and raw
hashes are established. The acquisition implementation should support only record
22300180's PDF plus `production_data.csv` for the minimal MVP bundle and keep
simulation explicitly separate.

This verdict does not make M1 complete and does not establish leakage-safe model
features. Acquisition, immutable raw-file handling, adapter/validation,
deterministic processed data, and the comprehensive audit remain unimplemented.
The absent timing/groups/units/specification limits are explicit limitations; a
future commercial or redistributed use requires a separate license assessment.
