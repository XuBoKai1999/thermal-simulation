# Handoff

## Current goal

Obtain human visual approval of the generated ADR01 Draft 0 geometry before any
material work or thermal solve.

## Current implementation state

- Test 01–07 cover steady/transient conduction, temperature-dependent properties, multi-region
  models, narrow contact models, analysis, and dump I/O.
- `materials/nist/` contains 43 index entries, 42 material pages, 38 fully normalized materials,
  1 partially normalized material, 3 manual-required materials, and 129 derived CSV tables.
- NIST data is not solver-integrated. Current `case.yaml` accepts inline/case-local constant,
  table, or Python `k/rho/cp`; it cannot select a `material.yaml` series.
- ADR01 Step 0 is human-approved and marked complete.
- `run/01_ADR01/geometry.py` generates the 10-component conformal placeholder mesh.
- Automated checks confirm all 11 declared contacts, no extra contacts, and coherent mesh output.
- `run/01_ADR01/build/mesh.msh` and `tags.json` are ready for interactive Gmsh inspection.
- Current revision places the five-part coaxial ADR chain at `(-5, 0) mm`, the sample near
  `(+5, 0) mm`, and supports at `(0, ±9) mm`; all are placeholder positions.

## Active decisions

- Keep case runners explicit; do not add a generic runner, registry, plugin, or material manager.
- Reuse `lib.materials.Property`. External material integration should resolve one explicit series
  and its derived CSV relative to the material file, while preserving existing inline syntax.
- Never infer among qualified series. OFHC copper requires an RRR choice; G-10 conductivity
  requires a direction choice.
- Never silently extrapolate outside `equation_range_K`, especially for ADR01's intended 1–4 K.
- ADR01 geometry requirements remain soft human-readable inputs; no geometry DSL is introduced.
- All current dimensions and derived contact areas are visualization placeholders.
- Human approval of the interactive geometry is required before thermal work.

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
3. Open `run/01_ADR01/build/mesh.msh` in Gmsh and complete the human visual review.
4. Only after approval, populate thermal parameters and later create the ADR runner.

## Resume here

Read `AGENTS.md`, this file, `steps.md`, `arch.md`, and
`run/01_ADR01/geometry-report.md`. Resume at the human visual-inspection gate;
do not run thermal physics before approval.
