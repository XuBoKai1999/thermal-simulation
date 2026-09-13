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
lateral-offset placeholder geometry is human-approved for the Baseline v1 numerical
smoke run. This approval does not verify actual hardware dimensions.

## Step 5 — Freeze baseline thermal parameters

STATUS: COMPLETE

The sole canonical specification is:

`parameters-requirement/ADR01_material_parameters_baseline_v1.md`

Material/property research is closed for Baseline v1. Do not restart it or copy
its formulas, tables, or bibliography into roadmap files.

## Step 6 — Freeze initial and boundary conditions

STATUS: COMPLETE

Approved for the first post-demagnetization smoke transient:

- initial temperature is 1 K in `ggg` and 4 K in every other solved solid;
- `ggg` is a finite-heat-capacity body, not a fixed-temperature boundary;
- `hot_plate` is an ideal fixed-temperature reservoir at 4 K, applied at its
  thermal contacts;
- all other exposed outer surfaces use the natural zero-normal-flux condition;
- ordinary solid-solid contacts remain perfect.

Timestep selection and output cadence are implementation/validation choices for
the approved 0.05 s early-transient smoke run.

## Step 7 — Implement solver-facing properties

STATUS: COMPLETE

Translate the canonical constant, Python-function, and table representations into
the existing framework. Implement the approved heat-switch approximation as the
existing thin volume with geometry-calibrated
$k_{\rm off}=1.527887\times10^{-3}\ \mathrm{W/(m\,K)}$, targeting finite
$G_{\rm off}=60\ \mu\mathrm{W/K}$. This is a pending numerical proxy for the
conceptual ideal-open baseline, not a new material measurement. Do not implement
the ON state or switching logic.

## Step 8 — Property sanity checks

STATUS: COMPLETE

Check the 1–4 K domains, units, positivity, canonical checkpoints,
interpolation behavior, and out-of-range failure for every implemented property.
Also verify that the bulk switch proxy reproduces its target conductance using
the generated thickness and shared contact area.

## Step 9 — ADR01 transient baseline

STATUS: COMPLETE FOR EARLY-TRANSIENT SMOKE RUN

After solver-facing implementation and property verification, compare the approved
smoke-run timesteps, run the transient case, and review thermal paths and energy.

The 0.05 s runs at 1.0, 0.5, and 0.25 ms completed. The 0.25 ms result is the
selected smoke timestep; production-duration, mesh-convergence, and engineering
validation remain future work.

Further materials, finite-field or magnetocaloric behavior, heat-switch ON state
or switching logic, hardware-specific switch data, radiation, heat loads, and
non-ideal contacts remain deferred unless separately approved.
