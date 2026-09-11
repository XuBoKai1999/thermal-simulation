# Handoff

## Current goal

Prepare the repository for ADR01 without expanding the FEM framework prematurely. The immediate
prerequisite is to connect an explicitly selected NIST property series to the existing `Property`
system, then obtain the physical inventory needed for ADR01.

## Current implementation state

- Test 01–07 cover steady/transient conduction, temperature-dependent properties, multi-region
  models, narrow contact models, analysis, and dump I/O.
- `materials/nist/` contains 43 index entries, 42 material pages, 38 fully normalized materials,
  1 partially normalized material, 3 manual-required materials, and 129 derived CSV tables.
- NIST data is not solver-integrated. Current `case.yaml` accepts inline/case-local constant,
  table, or Python `k/rho/cp`; it cannot select a `material.yaml` series.
- ADR01 has planning documents only. No ADR geometry, case, material assignment, runner, or result
  exists yet.

## Active decisions

- Keep case runners explicit; do not add a generic runner, registry, plugin, or material manager.
- Reuse `lib.materials.Property`. External material integration should resolve one explicit series
  and its derived CSV relative to the material file, while preserving existing inline syntax.
- Never infer among qualified series. OFHC copper requires an RRR choice; G-10 conductivity
  requires a direction choice.
- Never silently extrapolate outside `equation_range_K`, especially for ADR01's intended 1–4 K.
- ADR01 begins only after its geometry, semantic regions, materials, contacts, and BC locations are
  known. The first baseline remains fixed-temperature boundaries, adiabatic remainder, perfect
  internal contact, and no added physics unless required.

## Known gaps and risks

- The initial NIST candidates do not provide a complete 1–4 K solver-ready set:
  - OFHC copper `k/cp` start at 4 K, `k` has RRR variants, and density is absent.
  - G-10 `k` starts at 10 K (normal) or 12 K (warp), `cp` starts at 4 K, and density is absent.
  - Aluminum 6061-T6 `k` covers 1–300 K, `cp` starts at 4 K, and density is absent.
  - Stainless Steel 304 `k/cp` start at 4 K and density is absent.
- Heat loads/fluxes, time-dependent BCs, convection, radiation, heat switches, anisotropic
  conductivity, transient contact resistance, and general 3D zero-thickness contact are absent.
- Dump cell-ID mapping is serial-only. Mesh cache fingerprints only the geometry file plus caller
  `cache_key`.
- Preserve the existing user changes to `AGENTS.md` and `run/01_ADR01/ADR01_steps.md`.

## Immediate next actions

1. Implement the smallest explicit NIST-series reference accepted by `case.yaml`, with a focused
   loader regression and documentation update.
2. Decide sources for missing density and sub-4 K properties; do not present extrapolated NIST fits
   as validated data.
3. Obtain the ADR01 physical inventory in `run/01_ADR01/ADR01_steps.md` Stage 3.
4. After that gate, build and visually review geometry/tags before adding the ADR runner.

## Resume here

Read `AGENTS.md`, this file, `steps.md`, and `arch.md`, then inspect `lib/materials.py`,
`lib/case.py`, the four initial NIST candidate `material.yaml` files, `test/test_nist_materials.py`,
and `run/01_ADR01/ADR01_steps.md`.

