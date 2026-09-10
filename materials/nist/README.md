# NIST Cryogenic Materials Database

Source-preserving mirror of the official NIST Cryogenic Materials Database. Original
`source.html` snapshots are authoritative and contain only one injected `<base>` tag for
working links. Metadata records both the official response checksum and snapshot checksum; generated CSV files
are derived caches restricted to each NIST equation range. No external densities or
extrapolated values are included.

## Ingestion summary

- Index URL: https://trc.nist.gov/cryogenics/materials/materialproperties.htm
- Index entries discovered: 43
- General material pages downloaded: 42
- Failed downloads: 0
- Fully normalized: 38
- Partially normalized: 1
- Manual required: 3
- Derived CSV files: 129
- Worst validated interpolation metric: 0.098745%

## Property series counts

- linear_expansion: 37
- specific_heat: 29
- thermal_conductivity: 52
- thermal_expansion_coefficient: 2
- youngs_modulus: 12

## Manual-required or failed pages

- Kevlar-49 Fiber: manual_required — k-1-1-1: equation is image-only; coefficients preserved but not evaluated
- Kevlar-49 Composite: manual_required — k-1-1-1: equation is image-only; coefficients preserved but not evaluated
- Silicon: manual_required — alpha-1-1-1: equation is image-only; coefficients preserved but not evaluated

## Solver integration

The database exists, but `case.yaml` external material references are not implemented.
Select and review a series explicitly before copying it into a case-local solver input.
