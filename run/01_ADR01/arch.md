# ADR01 Architecture

## Scope

ADR01 models the post-demagnetization transient thermal response of a simplified
single-stage ADR using 3D solid conduction:

$$
\rho(T)c_p(T)\frac{\partial T}{\partial t}
=\nabla\cdot\left(k(T)\nabla T\right),
\qquad \dot q'''=0.
$$

Baseline v1 excludes the magnetocaloric cycle, superconducting magnet,
electromagnetic solve, radiation, convection, internal heating, and non-ideal
ordinary contacts.

## Authority and data flow

```text
requirement evidence (read-only history)
    -> canonical geometry + Baseline v1 parameter specifications
    -> case-local geometry.py / future solver-facing parameter files
    -> future case.yaml and main.py using parent lib/
    -> build/ and output/
```

- `geometry-requirement/` owns component shape, placement, IDs, and connection IDs.
- `parameters-requirement/ADR01_material_parameters_baseline_v1.md` is the sole
  human-readable authority for Baseline v1 material/property mapping, source
  provenance, representations, sensitivity choices, ordinary contacts, and the
  heat-switch model.
- `parameters-requirement/material-map.yaml` is only a concise machine-readable
  derivative of that baseline.
- `geometry.py` translates the soft geometry requirement into the existing Gmsh
  workflow. Future `case.yaml` and `main.py` must use existing parent interfaces.
- `requirement/` and paper directories preserve research evidence and do not
  define active solver behavior.

## Model roles

The geometry contains `hot_plate`, the five-part coaxial ADR chain
(`cylinder_1`, `heat_switch`, `cylinder_2`, `ggg`, `cylinder_3`), `cold_stage`,
`sample`, and two supports. The canonical parameter baseline assigns the thermal
material or special model for each identical component ID.

`hot_plate` is visualization/attachment geometry representing an ideal fixed
4 K reservoir rather than a solved material region. `heat_switch` is geometry
but Baseline v1 treats its thermal path as ideal OFF, not as a bulk solid.
Ordinary declared contacts use perfect contact. Detailed formulas, tables,
citations, and qualifiers remain only in the canonical baseline document.

## Geometry and interfaces

Requirement coordinates are in millimetres and generated mesh coordinates are in
metres. OCC fragmentation creates conformal shared surfaces. Component IDs are
dimension-3 physical groups; the 11 stable connection IDs are dimension-2 groups.
Contact area is derived from geometry. `geometry-report.md` records validation and
the interactive inspection command.

## Unresolved solver inputs

Baseline v1 does not define the complete initial temperature field or all
non-hot-side boundary conditions. In particular, no fixed 1 K cold boundary or
GGG initial temperature is currently approved. These remain `TBD` until a human
decision is recorded. No thermal solve may infer them.
