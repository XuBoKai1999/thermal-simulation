# ADR01 Agent Instructions

ADR01 is one case in the parent thermal-simulation repository, not a separate
framework. Read the repository instructions, this file, `arch.md`, `steps.md`,
and the relevant canonical requirement before changing the case.

## Sources of truth

- Geometry: `geometry-requirement/`.
- Baseline v1 materials, property representations, region mapping, interfaces,
  and heat-switch decision:
  `parameters-requirement/ADR01_material_parameters_baseline_v1.md`.
- Workflow and unresolved gates: `steps.md`.
- Architecture and ownership: `arch.md`.
- `requirement/` and every paper/literature directory are evidence or research
  history, not active specifications.

Machine-readable files derived from a canonical requirement must not compete
with or silently override it.

## Operating rules

- Never invent a dimension, material, property, initial condition, boundary
  condition, interface parameter, or heat load. Keep unresolved values `TBD`.
- Never extrapolate a property outside its documented range without explicit
  approval; preserve provenance and material qualifiers.
- Do not modify, move, rename, or delete evidence files or paper directories.
- Do not edit the canonical Baseline v1 parameter document unless a human
  explicitly replaces that decision.
- Reuse the parent geometry, mesh, material, solver, analysis, and output
  interfaces. Do not create parallel frameworks or speculative abstractions.
- Do not add radiation, convection, contact resistance, magnetocaloric dynamics,
  electromagnetic physics, or other extensions without an approved requirement.
- Geometry requires interactive human approval before a thermal solve.
- Validate any genuinely necessary generic parent-library extension independently.
- Keep documentation synchronized, concise, and assigned to its proper role.
