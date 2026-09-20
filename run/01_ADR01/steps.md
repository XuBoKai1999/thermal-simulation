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
$G_{\rm off}=60\ \mu\mathrm{W/K}$. This implemented numerical proxy represents the
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
selected smoke timestep; the segmented production trajectory now reaches 420 s.
Mesh-convergence and engineering validation remain future work.

Further materials, finite-field or magnetocaloric behavior, heat-switch ON state
or switching logic, hardware-specific switch data, radiation, heat loads, and
non-ideal contacts remain deferred unless separately approved.

Ordinary interfaces currently use perfect thermal contact. For future finite
contact resistance, prefer an interface-law / contact-conductance implementation
over inserting many ultra-thin volumetric layers, unless a later study specifically
requires thin-layer proxies.

The superconducting magnet is omitted from the active Baseline v1 simplified
geometry/model. A future extension may add a 4 K-anchored magnet and an optional
magnet heat load.

## Unified trajectory workflow

STATUS: IMPLEMENTED; FULL 0-420 S RUN COMPLETE

`baseline-v1.yaml` defines the five contiguous fixed-step intervals.
`workflow.py run` produces one scenario directory, automatically evaluates each
interval after S0 against `dt/2`, supports warn/strict failure handling, and
records local and accumulated trajectory validity. S0 is the accepted baseline;
S1-S4 pass the current provisional gates through 420 s.

## Long-time continuation

STATUS: ENTRY POINT IMPLEMENTED; 420-1800 S PRODUCTION NOT STARTED

`restart.py` validates the completed `baseline-v1` lineage and 420 s checkpoint,
checks restart-time scalar continuity without advancing a timestep, and delegates
the exploratory continuation to `main.run()`. A two-timestep 420-424 s regression
passed. The planned child is `baseline-v1-cont-420s-1800s` with dt 2 s; its
`validated_through_s` remains 420 because no new timestep refinement is performed.
