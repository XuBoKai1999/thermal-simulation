# ADR01 Workflow and Status

## Completed

- [x] Baseline scope frozen: post-demagnetization 3D transient solid conduction,
  zero volumetric heating, and no added physics.
- [x] Ten-component placeholder geometry and 11 stable connection IDs defined.
- [x] Conformal Gmsh geometry generated and automated contact/coherence checks passed.
- [x] Material/property research completed and frozen in
  `parameters-requirement/ADR01_material_parameters_baseline_v1.md`.
- [x] Obsolete parameter research notes and task prompts retired.

## Current gates

- [ ] Record human interactive approval of the current generated geometry.
- [ ] Resolve the complete initial temperature field (`TBD`).
- [ ] Resolve all boundary conditions other than the approved ideal fixed-4 K
  hot reservoir (`TBD`); no fixed 1 K cold boundary is currently established.

## Next implementation work

1. Translate the canonical constant/function/table/conductance representations
   into the existing framework-readable case files without changing the baseline.
2. Run property-level range, unit, positivity, checkpoint, and interpolation checks.
3. Verify how the ideal-OFF heat-switch path is represented without assigning it
   fake bulk properties or double-counting resistance.
4. After all gates above are approved, assemble and verify the first ADR01
   transient baseline.

Material research is closed for Baseline v1. Radiation, convection, non-ideal
contact resistance, finite-field/magnetocaloric behavior, real heat-switch
hardware, and additional material families remain deferred unless separately
approved.
