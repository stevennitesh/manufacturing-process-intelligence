# Dataset licenses and redistribution

No third-party datasets are version controlled in this repository.

Before adding a dataset adapter or download command:

1. record the authoritative source URL, version, access date, and license or terms;
2. document whether automated download and local processing are permitted;
3. document whether raw or derived data may be redistributed;
4. keep raw, interim, and processed data outside Git unless redistribution is explicitly permitted;
5. commit only acquisition instructions, schemas, manifests, and small synthetic test fixtures.

## High-resolution injection molding — candidate MVP source

- **Candidate authority:** the publisher-maintained
  [scatimdata repository](https://github.com/sc4t1m/scatimdata), associated with
  Bogedale et al., [Online Prediction of Molded Part Quality in the Injection
  Molding Process Using High-Resolution Time Series](https://doi.org/10.3390/polym15040978).
- **Admission status:** not yet admitted. M1 must freeze the exact source identity,
  file roles, hashes, joins, acquisition method, and terms before download or adapter
  implementation.
- **Stated license:** the publisher repository states
  [CC BY 4.0](https://github.com/sc4t1m/scatimdata#license). This must be verified
  against the exact files selected in the M1 source contract.
- **Repository policy:** raw and prepared data remain outside Git. Only the verified
  source contract, acquisition manifest, schemas, instructions, and synthetic fixtures
  may be version controlled.

## SoliDAIR — evaluated and retired

SoliDAIR was evaluated for the former MVP and was not admitted because the released
production data did not satisfy the required process-to-physical-quality contract.
Its source contract, discovery manifest, inspection utility, tests, and findings are
preserved under `.archive/` as non-authoritative historical evidence. Local raw
SoliDAIR files, when present, live under `data/raw/_archive/solidair/`; they remain
ignored and must not be used by active code, tests, or claims.

The former source was published under CC BY-NC-ND 4.0. Archiving project metadata
does not broaden those terms, authorize commercial use, or authorize redistribution
of adapted material.
