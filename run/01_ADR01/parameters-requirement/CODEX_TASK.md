# ADR01 parameter-data ingestion task — research pass 0

Work in the existing `thermal-simulation` repository.

Read first:
- repository `AGENTS.md`
- `run/01_ADR01/AGENTS.md`
- `run/01_ADR01/arch.md`
- `run/01_ADR01/steps.md`
- `run/01_ADR01/geometry-requirement/`
- current material database implementation/manual
- existing `materials/nist/`

Then read:
- `run/01_ADR01/parameters-requirement/material-map.yaml`
- `run/01_ADR01/parameters-requirement/research-sources.md`

## Goal

Create clean, machine-usable ADR01 thermal-property records for `1 K <= T <= 4 K`, while preserving strict geometry-component ID → parameter-record mapping.

Do **not** run ADR FEM in this task.

## Mandatory provenance

Every numerical series or fit must retain:
- source title, authors, year;
- DOI / official URL;
- page/table/figure/equation;
- original units;
- processed units;
- source validity range;
- material grade / purity / RRR / orientation / magnetic field;
- whether values are author-tabulated, equation-generated, or digitized;
- every conversion / fit / interpolation step.

## Hard rules

1. Never extrapolate outside a source's stated validity range without explicit human approval.
2. Never silently select unresolved physical qualifiers.
3. Keep alternative copper RRR scenarios separate.
4. For OFHC copper prepare at least RRR=50 and RRR=100 `k(T)` candidates.
5. For GGG prepare a zero-field baseline record; never mix different magnetic fields.
6. If a GGG source is inaccessible, create `needs_source_pdf` metadata instead of inventing numbers.
7. For G-10 ingest:
   - Runyan/Jones conductivity fit;
   - NIST 1 K+ volumetric heat capacity table;
   - orientation / grade qualifiers.
8. For PEEK ingest the Runyan/Jones conductivity fit but leave cp incomplete unless a credible 1–4 K source is found.
9. Do not create artificial rho(T). Constant density is acceptable when that is what the source supports.
10. Keep heat switch as a `G_on(T)` / `G_off(T)` special model until hardware is identified.

## Storage

Inspect and reuse the current repository material schema first.

Prefer ADR-local processed records under:
`run/01_ADR01/parameters-requirement/`

Use root `materials/nist/` as source/cache only where appropriate. Do not create a parallel material framework.

If a generic loader extension is genuinely required:
- implement the smallest reusable extension;
- add a focused validation test;
- update the relevant manual.

## Required deliverables

Produce:
1. component-to-property coverage report;
2. machine-readable ADR01 parameter records;
3. source-preserving references/raw data;
4. cleaned 1–4 K datasets or formulas;
5. provenance metadata;
6. plots for k(T), cp(T), and rho where meaningful;
7. explicit unresolved-items list.

Classify every component as:
- `READY`
- `READY_WITH_SCENARIOS`
- `INCOMPLETE`
- `SPECIAL_MODEL`

Stop after parameter ingestion/cleaning. Do not run the ADR solver.
