# ADR01 Workflow and Status

## Step 0 — Freeze modeling scope

STATUS: COMPLETE

Post-demagnetization 3D transient solid conduction with zero volumetric heating.
Magnetocaloric dynamics, radiation, convection, electromagnetic physics, and
non-ideal ordinary contacts are outside Baseline v1.

## Steps 1–4 — Geometry

STATUS: COMPLETE

The ten-component placeholder geometry and 11 stable connection IDs are defined.
The conformal Gmsh mesh passes automated contact and coherence checks. The current
lateral-offset geometry received human visual approval on 2026-09-12.

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

Translate the canonical constant, Python-function, and table representations into
the existing framework. Implement the approved heat-switch approximation as the
existing thin volume with geometry-calibrated
$k_{\rm off}=1.527887\times10^{-3}\ \mathrm{W/(m\,K)}$, targeting finite
$G_{\rm off}=60\ \mu\mathrm{W/K}$. This is a pending numerical proxy for the
conceptual ideal-open baseline, not a new material measurement. Do not implement
the ON state or switching logic.

## Step 8 — Property sanity checks

STATUS: NOT STARTED

Check the 1–4 K domains, units, positivity, canonical checkpoints,
interpolation behavior, and out-of-range failure for every implemented property.
Also verify that the bulk switch proxy reproduces its target conductance using
the generated thickness and shared contact area.

## Step 9 — ADR01 transient baseline

STATUS: BLOCKED BY STEPS 6–8

After IC/BC decisions and property verification, run the transient smoke case
and then perform mesh/timestep convergence, thermal-path review, and energy checks.

Further materials, finite-field or magnetocaloric behavior, heat-switch ON state
or switching logic, hardware-specific switch data, radiation, heat loads, and
non-ideal contacts remain deferred unless separately approved.
