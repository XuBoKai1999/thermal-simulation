# ADR01 Workflow and Status

## Step 0 — Freeze modeling scope

STATUS: COMPLETE

Post-demagnetization 3D transient solid conduction with zero volumetric heating.
Magnetocaloric dynamics, radiation, convection, electromagnetic physics, and
non-ideal ordinary contacts are outside Baseline v1.

## Steps 1–4 — Geometry

STATUS: GENERATED; HUMAN VISUAL APPROVAL PENDING

The ten-component placeholder geometry and 11 stable connection IDs are defined.
The conformal Gmsh mesh passes automated contact and coherence checks. Human
interactive approval of the current mesh is still required before thermal solving.

## Step 5 — Freeze baseline thermal parameters

STATUS: COMPLETE

The sole canonical specification is:

`parameters-requirement/ADR01_material_parameters_baseline_v1.md`

Material/property research is closed for Baseline v1. Do not restart it or copy
its formulas, tables, or bibliography into roadmap files.

## Step 6 — Freeze initial and boundary conditions

STATUS: INCOMPLETE

Approved:

- `hot_plate` represents an ideal fixed-temperature reservoir at 4 K.

Unresolved (`TBD`):

- initial temperatures of all solved regions, including GGG;
- all non-hot-side boundary conditions;
- simulation duration and timestep;
- output and observation cadence.

No fixed 1 K cold boundary or 1 K GGG initial condition is currently approved.

## Step 7 — Implement solver-facing properties

STATUS: NOT STARTED

Translate the canonical constant, Python-function, table, and conductance
representations into the existing framework. Do not change the frozen baseline or
assign fake bulk properties to the ideal-OFF heat switch.

## Step 8 — Property sanity checks

STATUS: NOT STARTED

Check the 1–4 K domains, units, positivity, canonical checkpoints,
interpolation behavior, and out-of-range failure for every implemented property.

## Step 9 — ADR01 transient baseline

STATUS: BLOCKED BY STEPS 2–4, 6–8

After geometry approval and IC/BC decisions, run the transient smoke case and
then perform mesh/timestep convergence, thermal-path review, and energy checks.

Further materials, finite-field or magnetocaloric behavior, real heat-switch
hardware, radiation, heat loads, and non-ideal contacts remain deferred unless
separately approved.
