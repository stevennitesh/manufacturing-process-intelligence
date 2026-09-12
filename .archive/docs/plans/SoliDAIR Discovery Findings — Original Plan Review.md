# SoliDAIR discovery findings: original plan review

**Prepared:** 2026-09-12
**For:** the author/reviewer of *Manufacturing Quality & Process Intelligence —
Greenfield Technical Specification & Implementation Plan*
**Decision requested:** whether to continue the SoliDAIR-based MVP as planned,
continue with explicit qualifications or revised acceptance criteria, or resolve
specific evidence gaps before further implementation.

This is a standalone findings report, not an approved change to the specification.
It summarizes completed source discovery and identifies where the original
plan's intended claims exceed the evidence currently available. No raw data rows
are included. Source-contract completion establishes ingestion readiness, not
model validity or completion of the predictive-quality MVP.

## Assessment for the planner

The selected public dataset supports reproducible ingestion and experiments in
continuous EoL regression. The original specification already provides fallback
paths for unavailable specification limits and unavailable temporal/group keys.
Those facts support continuing engineering work within M1.

However, continuing the original scientific and operational claims unchanged is
not yet justified. The central issue is whether the 25 candidate predictors are
actually available before EoL testing. Their station assignments and measurement
timing are undisclosed. Anonymized transformations, absent physical identity/time
information, and restrictive licensing introduce further limits.

**Recommendation for review:** retain the architecture and milestone sequence,
but require explicit acceptance of the evidence boundaries below. In particular,
decide whether Mode B's measured prediction-error/uncertainty tradeoff satisfies
the original requirement to quantify inspection burden versus quality risk.
That equivalence is a proposal, not an established result or an approved change.

## 1. Evidence and selected distribution

The selected source is *SoliDAIR quality prediction, production, and simulation
data UC BOS*, by Hakan Cem Muslu, Bosch Sanayi Ve Ticaret A.S., published on
2026-09-04 as [Zenodo record 22300180](https://zenodo.org/records/22300180),
DOI [10.5281/zenodo.22300180](https://doi.org/10.5281/zenodo.22300180).

The landing page labels the release `v1`; the API's `metadata.version` field is
unset. The description PDF gives an August 2026 release date. We preserve those
distinct source statements and identify inputs by record, DOI, filenames, sizes,
and hashes. Public HTTPS endpoints worked without credentials during discovery.

The publisher's [dataset description](https://zenodo.org/api/records/22300180/files/20260904_OpenDataset%20Description%20Form.pdf/content)
identifies production-line sensor measurements, a separate hydraulic simulation,
anonymization, and intended EoL regression. The project's
[public data-management plan](https://www.solidair-project.eu/_files/ugd/a34356_7e9cd32d69c74d2f9150206cc0980eff.pdf)
independently identifies its Zenodo community as the distribution channel for open
anonymized datasets. This corroborates provenance; it does not validate individual
predictor availability or predictive performance.

| Inspected input | Size | Observed shape | Use in proposed MVP |
| --- | ---: | ---: | --- |
| `production_data.csv` | 137,713,757 bytes | 510,050 rows × 30 columns | Selected production input |
| `simulation_data.csv` | 50,490 bytes | 800 rows × 7 columns | Kept separate; excluded from the minimal production bundle |
| `20260904_OpenDataset Description Form.pdf` | 67,955 bytes | Publisher documentation | Required semantic/provenance evidence |

All three files matched publisher MD5 checksums and sizes. Production SHA-256:
`46c18905dc9ff588ec6c764f03779916f4879b260cc47134a9e6bfe07431cb30`.

An earlier Bosch record, [17661875](https://zenodo.org/records/17661875), was
considered. Its description states 1,000 rows, 67 inputs, four outputs, and warns
of low correlation between released features and EoL outcomes. The newer record
was selected for its larger production coverage and clearer EoL designation.
Neither larger sample size nor that comparison proves the newer release has
useful predictive signal. The records must not be treated as interchangeable
versions of the same schema.

## 2. What is verified, and what remains unknown

### Publisher-declared semantics

The publisher says each production row represents one injector and explicitly
identifies `input_1`, `input_2`, `input_3`, `input_4`, and `input_5` as EoL-station
measurements. These five fields are candidate continuous quality targets, despite
their names. For pre-EoL prediction, none should be used as an upstream predictor,
including using one EoL field to predict another.

Names were obfuscated and numeric values transformed. Physical measurement names,
units, transformation formulas, and individual station/timing assignments for
the other 25 fields are not supplied. They are **candidate predictors**, not a
verified set of pre-EoL features.

### Observations from the full CSV scan

A reproducible streaming inspection of both complete CSV files found zero
malformed-width rows, recognized missing-token cells, nonnumeric/nonfinite cells,
or repeated parsed-row SHA-256 digests. All observed production numeric values
were in `[0, 1]`. That interval is not a tolerance range and does not establish
the transformation method. Unrecognized numeric missing-value codes cannot be
ruled out by this structural check.

The first production data row contains values for all 25 candidate fields and all
five EoL fields, supporting a same-row observation-to-target mapping. No cross-file
join is required for production. Absence of repeated row digests does not establish
distinct physical injectors, absence of retests, or statistical independence.

### Material evidence gaps

| Gap | Consequence |
| --- | --- |
| Predictor timing and station assignment | We cannot certify all remaining fields are available at the intended prediction point. Correlation analysis alone cannot prove that timing. |
| Transformation formulas and how they were fitted | Metrics can be reported in released source scale, but physical interpretation is unavailable. We cannot rule out population-wide preprocessing in the publisher's transformation from the released files alone. |
| Physical identifiers and retest information | A derived key can identify a source observation, not recover injector identity or enforce physical-unit separation across splits. |
| Timestamps, batches, lots, runs, and product types | No explicit keys were found or documented. We cannot justify chronological/grouped evaluation or infer chronology from row order. |
| Authoritative specification limits | Engineering PASS/FAIL, defect escapes, and specification compliance cannot be measured from arbitrary thresholds. |
| Predictive utility | No baseline or ML model has been trained. Feature usefulness, error, interval coverage, and inspection benefit remain unmeasured. |

## 3. Implications for the original milestones

| Milestone / specification section | Supported path | Qualification or decision needed |
| --- | --- | --- |
| M1 ingestion; sections 17–21 | Deterministic acquisition/preparation into `units`, `process_features`, `quality`, and `metadata`. | Use a provenance-derived observation key and preserve unknown units/semantics. Keep simulation separate. Acquisition commands, adapter, Parquet, and full audit are still unimplemented. |
| M2 splits and baselines; section 22 | Benchmark continuous targets; the specification permits random splitting when stronger dependency information is unavailable. | Justify the fallback and disclose physical-unit overlap/dependence uncertainty. Random-split performance does not prove future-production performance. |
| M3 quality model; section 28 explainability | Compare a candidate model against baselines and report statistical feature attribution. | Verify or qualify feature availability before making upstream-prediction claims. Anonymized feature importance cannot establish physical process drivers or root causes. |
| M4 uncertainty; section 25 | Implement calibration and measure held-out coverage/width in transformed source scale. | No coverage has been measured yet. Unknown dependence and distribution shift limit deployment claims; nominal coverage is not a demonstrated production guarantee. |
| M5 decision policy; sections 26–27 | Use the already-specified Mode B, prioritizing inspection by prediction uncertainty. | No engineering auto-pass/hold decisions. Planner must define an acceptable measurable risk proxy and cost assumptions. Prediction error or interval misses are not measured defect escapes. |
| M6 presentation and release; section 30 | Present reproducible engineering, empirical results, and limitations. | Broad manufacturing/operational claims require supporting evidence. Dataset licensing must be considered before sharing data-bearing screenshots, reports, models, or derived tables. |
| M7 onward: CiP-DMD, monitoring, productionization, semiconductor transfer | No architectural conflict established by this discovery. | These datasets and milestones were not investigated. Their feasibility, licenses, and gates remain unverified; SoliDAIR findings do not validate them. |

The source-scale regression experiment remains technically possible even if
physical units are undisclosed. Its practical utility is an empirical question.
Similarly, the Mode B fallback exists in the original plan, but its compatibility
with the original business-value acceptance wording needs an explicit planner
decision rather than an implicit weakening of the gate.

## 4. License constraints

Both the selected record metadata and its description specify
[CC BY-NC-ND 4.0](https://creativecommons.org/licenses/by-nc-nd/4.0/).
The [legal code](https://creativecommons.org/licenses/by-nc-nd/4.0/legalcode.en),
section 2(a), permits reproduction and local production of Adapted Material for
noncommercial purposes but does not permit sharing Adapted Material. Sharing
licensed material is subject to attribution and other conditions. Pure technical
format changes need not themselves create Adapted Material.

Discovery proceeded as local noncommercial research. A private repository is not
by itself proof that every intended use is noncommercial. No blanket permission
is asserted for commercial deployment or redistribution of processed datasets,
trained models, reports, or data-bearing demos; the particular artifact and use
need assessment. All downloaded PDF/CSV files and generated inspection outputs
remain outside version control. These constraints apply to the dataset and do
not automatically assign its license to independently written project code.

## 5. Questions for the original planner

1. **Intended outcome:** Is an anonymized, source-scale predictive-quality research
   demonstrator sufficient, or does the MVP require physically interpretable
   engineering decisions? Which claims should the README and final demo support?
2. **Feature availability:** Must publisher confirmation of the 25 fields'
   pre-EoL availability be obtained before M2/M3, or can exploratory modeling
   proceed with explicit limitations? What evidence is required to satisfy the
   original “no obvious leakage” and upstream-prediction commitments?
3. **Evaluation:** Is the documented random-split fallback acceptable with unknown
   physical identity, retests, chronology, and publisher preprocessing? Specify
   what generalization claims are allowed and which remain unproved.
4. **M5 acceptance:** Does an inspection-rate versus held-out prediction-error or
   interval-miss tradeoff meet the intended decision-value requirement under Mode
   B? Define the exact risk metric and scenario-based cost assumptions; avoid
   equating prediction error with defective product escapes.
5. **Release/use:** Is the intended noncommercial research and presentation scope
   compatible with the license? Identify planned public artifacts requiring a
   separate permission assessment before the M6 release.
6. **Disposition:** Should we continue M1, continue only after targeted evidence
   gathering, or reconsider the primary dataset? If requirements change, identify
   the affected specification sections and gates explicitly.

## 6. Current implementation state and evidence trail

Completed: source comparison, licensing/provenance review, byte-verified local
downloads, full structural inspection, minimal bundle proposal, and source-contract
documentation. A small stdlib inspection script and two synthetic tests were
added. Ruff lint/format, Pyright, eight tests, CLI smoke checks, hash verification,
and Git-ignore/whitespace checks passed on 2026-09-12. These checks support the
discovery tooling; they are not scientific validation of a predictive model.

Not completed: production acquisition commands, adapter, preparation/Parquet,
comprehensive data audit, splitting, modeling, calibration, decision policy, or
the M1 end-to-end gate. The original specification has not been amended. The
source-contract subsystem is recorded complete with limitations; continuation of
the broader plan is the decision requested by this report.

Repository evidence (optional supporting material; the findings above stand alone):

- `docs/datasets/solidair-source-contract.md` — detailed source contract and mapping.
- `data/manifests/solidair-source-discovery.json` — identity, hashes, inspection summary.
- `scripts/inspect_solidair_source.py` — reproducible inspection command implementation.
- `tests/unit/test_inspect_solidair_source.py` — synthetic inspection checks.
- `DATA_LICENSES.md` — recorded license boundary.
- `docs/milestones/m01-solidair-ingestion.md` — scoped plan and completion evidence.

This report records findings as of the evidence date. It does not claim a model
performance result, substitute a dataset, approve a new acceptance gate, or
authorize publication of restricted data.
