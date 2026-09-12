# Handoff

## Current goal

Prepare ADR01 for solver-facing property implementation while retaining the
geometry-approval and IC/BC gates.

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
- Material/property research is complete. The frozen canonical specification is
  `run/01_ADR01/parameters-requirement/ADR01_material_parameters_baseline_v1.md`.

## Active decisions

- Keep case runners explicit; do not add a generic runner, registry, plugin, or material manager.
- Reuse `lib.materials.Property` and the existing case-local constant/function/table forms.
- Baseline v1 fixes nominal copper RRR and the G-10 axial-effective interpretation; do not reopen
  those material decisions during implementation.
- Never silently extrapolate outside `equation_range_K`, especially for ADR01's intended 1–4 K.
- ADR01 geometry requirements remain soft human-readable inputs; no geometry DSL is introduced.
- All current dimensions and derived contact areas are visualization placeholders.
- Human approval of the interactive geometry is required before thermal work.
- Baseline v1 preserves a conceptual ideal-open OFF heat switch. The approved first solver
  approximation is the existing 0.5 mm switch volume with finite-leakage effective bulk
  `k_off = 1.527887e-3 W/(m K)`, calibrated to `G_off = 60 µW/K` using the generated
  `19.634954 mm²` shared contact area. It is not hardware-specific; ON is not modeled.

## Known gaps and risks

- Heat loads/fluxes, time-dependent BCs, convection, radiation, heat switches, anisotropic
  conductivity, transient contact resistance, and general 3D zero-thickness contact are absent.
- Initial temperatures, non-hot-side boundary conditions, duration/timestep, and output cadence
  remain unresolved. No fixed 1 K cold boundary or GGG initial temperature is approved.
- Dump cell-ID mapping is serial-only. Mesh cache fingerprints only the geometry file plus caller
  `cache_key`.
- Preserve the existing user changes to `AGENTS.md` and `run/01_ADR01/ADR01_steps.md`.

## Immediate next actions

1. Open `run/01_ADR01/build/mesh.msh` in Gmsh and complete the human visual review.
2. Freeze the unresolved IC/BC and runtime/output decisions.
3. Translate Baseline v1 properties and the approved switch proxy into existing solver-facing
   forms, then run property-level sanity checks.
4. Only after the gates above, create and verify the ADR transient baseline.

## Resume here

Read `AGENTS.md`, this file, `steps.md`, `arch.md`, and
`run/01_ADR01/geometry-report.md`. Resume at the human visual-inspection gate;
do not run thermal physics before approval.
