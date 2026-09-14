# Dataset licenses and redistribution

No third-party datasets are version controlled in this repository.

Before adding a dataset adapter or download command:

1. record the authoritative source URL, version, access date, and license or terms;
2. document whether automated download and local processing are permitted;
3. document whether raw or derived data may be redistributed;
4. keep raw, interim, and processed data outside Git unless redistribution is explicitly permitted;
5. commit only acquisition instructions, schemas, manifests, and small synthetic test fixtures.

## High-resolution injection molding — admitted MVP source

- **Candidate authority:** the publisher-maintained
  [scatimdata repository](https://github.com/sc4t1m/scatimdata), associated with
  Bogedale et al., [Online Prediction of Molded Part Quality in the Injection
  Molding Process Using High-Resolution Time Series](https://doi.org/10.3390/polym15040978).
- **Admission status:** Dataset 2's 829 labeled cycles are admitted with limitations
  at commit `7bd35941d75c97a3f276439377dc430ab47402be`. The
  [source contract](docs/datasets/injection-molding-source-contract.md) owns the
  selection, join, chronology, units, and claim boundaries; the
  [manifest](data/manifests/injection-molding-source.json) owns exact hashes.
- **Verified license:** the pinned publisher README applies
  [CC BY 4.0](https://github.com/sc4t1m/scatimdata/blob/7bd35941d75c97a3f276439377dc430ab47402be/README.md#license)
  to the dataset. Raw and derived redistribution is permitted with the license's
  attribution, license/source link, and modification-notice conditions.
- **Repository policy:** raw and prepared data remain outside Git. Only the verified
  source contract, acquisition manifest, schemas, instructions, and synthetic fixtures
  may be version controlled. This project policy is intentionally stricter than the
  source license.

## SoliDAIR — evaluated and retired

SoliDAIR was evaluated for the former MVP and was not admitted because the released
production data did not satisfy the required process-to-physical-quality contract.
Its source contract, discovery manifest, inspection utility, tests, and findings are
preserved in Git history at commit `60e3c25`, not in the current tree. Local raw
SoliDAIR files, when present, live under `data/raw/_archive/solidair/`; they remain
ignored and must not be used by active code, tests, or claims.

The former source was published under CC BY-NC-ND 4.0. Retaining project history
does not broaden those terms, authorize commercial use, or authorize redistribution
of adapted material.
