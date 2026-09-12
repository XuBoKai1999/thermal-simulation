# ADR01

ADR01 is the case-local model for a simplified single-stage adiabatic
demagnetization refrigerator after demagnetization. Baseline v1 is a 3D
transient solid-conduction model; it does not include the magnetocaloric cycle,
radiation, convection, electromagnetic physics, or non-ideal ordinary contacts.

Current sources of truth:

- `geometry-requirement/`: placeholder component geometry and connectivity.
- `parameters-requirement/ADR01_material_parameters_baseline_v1.md`: canonical
  Baseline v1 material, property, and heat-switch decisions.
- `arch.md`: case architecture and responsibility boundaries.
- `steps.md`: current progress, unresolved gates, and next work.
- `requirement/` and `parameters-requirement/ADR01_papers_v4/`: research evidence;
  they are not active specifications and must not be edited as part of model implementation.

Generated geometry and validation artifacts are described in
`geometry-report.md`. Solver-facing parameter files and the transient case have
not yet been implemented.
