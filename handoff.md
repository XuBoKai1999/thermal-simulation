# Handoff

## Current goal

Convert the frozen ADR01 Baseline v1 parameters and approved heat-switch proxy
into the existing solver-facing property forms, after the remaining IC/BC and
runtime decisions are supplied.

## Current state

- Parent Tests 01–07 already cover the required steady/transient,
  temperature-dependent, multi-region, contact, analysis, and dump foundations.
- ADR01 has moved from geometry definition to parameterization / baseline-run
  preparation.
- The ten-component lateral-offset geometry and all 11 contacts pass automated
  checks and received human visual approval on 2026-09-12.
- Material/property research is complete. The frozen canonical specification is
  `run/01_ADR01/parameters-requirement/ADR01_material_parameters_baseline_v1.md`.
- `run/01_ADR01/parameters-requirement/material-map.yaml` is the concise current
  solver-facing mapping.
- Solver-facing property files, `case.yaml`, and the ADR01 runner do not yet exist.

## Active decisions

- Reuse `lib.materials.Property` and existing constant/function/table support.
  Keep the ADR runner explicit; add no manager, registry, plugin, or generic runner.
- Target range is 1–4 K. Preserve canonical provenance and qualifiers, and fail
  rather than silently extrapolate outside supported ranges.
- Baseline v1 fixes the component/material mapping, nominal copper RRR=100,
  RRR=50 sensitivity, GGG H=0 data, and G-10 axial-effective support model.
- Baseline v1 records a conceptual ideal-open OFF heat switch. The approved first
  numerical approximation retains the 0.5 mm switch volume and assigns finite
  effective bulk `k_off = 1.527887e-3 W/(m K)`, calibrated to
  `G_off = 60 µW/K` through the generated `19.634954 mm²` contact area.
  This is not hardware-specific. ON state and switching logic are not modeled.
- Ordinary contacts remain perfect. Radiation, convection, heat loads,
  magnetocaloric/finite-field behavior, and non-ideal contacts remain excluded.

## Unresolved implementation inputs

- Initial temperatures of all solved regions, including GGG.
- All non-hot-side boundary conditions; no fixed 1 K cold boundary is approved.
- Simulation duration and timestep.
- Output and observation cadence.

Do not infer these values from general ADR behavior.

## Next actions

1. Obtain explicit decisions for the unresolved IC/BC and runtime/output inputs.
2. Translate the frozen property representations and switch proxy into the
   existing framework-readable forms.
3. Run property-level checks for units, range, positivity, canonical checkpoints,
   interpolation, out-of-range failure, and switch-proxy conductance.
4. Build the explicit ADR01 case/runner and perform the transient smoke run,
   followed by convergence, thermal-path, and energy checks.

## Resume here

Read `AGENTS.md`, this file, `steps.md`, `arch.md`, then
`run/01_ADR01/AGENTS.md`, `run/01_ADR01/steps.md`, and the frozen Baseline v1.
Inspect only the existing property/case interfaces needed for implementation;
do not rescan material literature or redo geometry work.
