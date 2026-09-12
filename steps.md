# Thermal Simulation Roadmap

> 原則：如無必要勿增實體。一次完成並驗證一個真正需要的能力。

## Framework status

- [x] Test 01–07 cover steady/transient conduction, temperature-dependent
  properties, multi-region models, narrow contact models, analysis, dump I/O,
  and convergence regressions.
- [x] User manual and framework-readiness review completed.
- [x] Source-preserving NIST material mirror, derived tables, listing CLI, and
  database regressions completed.

## ADR01 current status

- [x] Modeling scope and ten-component placeholder geometry defined.
- [x] Tagged conformal geometry generated; automated contact/coherence checks pass.
- [ ] Human interactive approval of `run/01_ADR01/build/mesh.msh`.
- [x] Material/property research completed and Baseline v1 frozen in
  `run/01_ADR01/parameters-requirement/ADR01_material_parameters_baseline_v1.md`.
- [ ] Initial temperatures and remaining boundary conditions frozen; only the
  ideal fixed-4 K hot reservoir is currently approved.

## Next ADR01 gates

1. Record human approval of the current geometry.
2. Resolve the initial-condition field, non-hot-side boundary conditions,
   simulation duration/timestep, and output cadence.
3. Translate Baseline v1 properties into existing framework-readable constant,
   function, and table forms; implement the approved geometry-calibrated finite-
   leakage bulk OFF proxy for the heat-switch volume.
4. Run property-level domain, unit, checkpoint, interpolation, positivity, and
   out-of-range checks.
5. Assemble the ADR01 transient smoke run, then perform mesh/timestep convergence,
   thermal-path review, and energy sanity checks.

Do not restart material research or add new physics before an approved requirement.
Detailed case progress is maintained in `run/01_ADR01/steps.md`.
