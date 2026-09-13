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
- [x] Human interactive approval of `run/01_ADR01/build/mesh.msh` recorded on 2026-09-12.
- [x] Material/property research completed and Baseline v1 frozen in
  `run/01_ADR01/parameters-requirement/ADR01_material_parameters_baseline_v1.md`.
- [x] Placeholder geometry, region-wise IC, fixed-4 K reservoir contacts, and
  adiabatic remaining outer boundaries approved for the smoke run.
- [x] Baseline v1 properties, finite-leakage switch proxy, property validation,
  timestep comparison, and 0.05 s early-transient smoke run completed.

## Next ADR01 gates

1. Perform mesh convergence and energy-balance review before treating results as
   more than an early-transient numerical smoke test.
2. Add longer-duration or hardware-specific studies only after separate approval.

Do not restart material research or add new physics before an approved requirement.
Detailed case progress is maintained in `run/01_ADR01/steps.md`.
