# ADR01 Steps 2 — Visualization, Diagnostics, and Numerical Validation

> Purpose: continue from the completed ADR01 Baseline v1 early-transient smoke run.
>
> This file is intentionally written as a **step-by-step execution checklist for Codex**.  
> **Do exactly one numbered step at a time. After each step, update `chat/`, report the result, and STOP. Wait for the user to say `next` before starting the next step.**

---

# 0. Operating rules

## 0.1 Handoff-first, inspect-on-demand

Do **not** re-review the whole repository.

At the beginning of a fresh Codex session, read only:

1. the latest relevant handoff in `chat/`;
2. `run/01_ADR01/AGENTS.md`;
3. `run/01_ADR01/steps.md`;
4. this file: `steps2.md`;
5. the specific source/manual/test files needed for the current numbered step.

Do not recursively read all of `lib/`, `manual/`, `run/`, tests, papers, or git history unless a specific blocker requires it.

## 0.2 Frozen / read-only material

Do not modify:

- `run/01_ADR01/parameters-requirement/ADR01_material_parameters_baseline_v1.md`;
- ADR01 papers / PDFs / evidence archives;
- geometry dimensions unless a later human instruction explicitly changes them.

Do not restart material research.

## 0.3 Keep the current physics scope

Current ADR01 baseline remains:

- post-demagnetization transient solid conduction;
- `GGG` initially 1 K;
- all other solved solids initially 4 K;
- hot reservoir fixed at 4 K;
- other exposed boundaries adiabatic;
- ordinary solid-solid contacts are perfect thermal contacts;
- heat-switch OFF is represented by the currently approved finite-leakage thin bulk proxy;
- no MCE cycle, radiation, convection, contact resistance, sample heat load, or magnet model in the active Baseline v1 smoke case.

## 0.4 `chat/` is mandatory

After every numbered step:

- record current state;
- record decisions;
- record files changed;
- record tests/commands and pass/fail;
- record key numerical results;
- record the exact next step;
- then STOP and wait for user instruction.

Do not dump long terminal transcripts into `chat/`.

---

# Step 1 — Synchronize current documentation state

STATUS: COMPLETE

## Goal

Remove stale statements left over from before the successful smoke run and record future work without implementing it.

## Scope

Review only the currently active ADR01 descriptive files and generic manual pages directly affected by the recent implementation.

At minimum inspect:

- `run/01_ADR01/README.md`
- `run/01_ADR01/arch.md`
- `run/01_ADR01/steps.md`
- `run/01_ADR01/AGENTS.md`
- `manual/README.md`
- `manual/07-feature-status.md`
- `manual/08-api-reference.md`
- root `README.md` only if it still documents the old IC/property capabilities

## Required corrections

Make sure active docs reflect that:

- solver-facing ADR01 properties are implemented;
- the first early-transient smoke run has completed;
- `by_region` initial condition exists;
- table property `scale` / `domain` capability exists if still part of current code;
- bounded nonlinear solving exists as an available numerical option, but is not to be treated as physical validation;
- heat-switch finite-leakage proxy is implemented, not pending;
- ordinary interfaces currently use perfect thermal contact;
- ADR01 Baseline v1 ordinary contacts remain perfect;
- steady mesh-resolved thin-layer resistance is supported, while the 1D
  zero-thickness path is reference-only;
- generic 3D zero-thickness and transient interface contact resistance remain
  future work;
- superconducting magnet is omitted from current Baseline v1 simplification; a future extension may add a 4 K-anchored magnet and optional magnet heat load.

For future ADR01 interface contact resistance, document:

> Prefer a future interface-law / contact-conductance implementation over inserting many ultra-thin volumetric layers, unless a later study specifically requires thin-layer proxies.

Do not add new physics code in this step.

## Pass condition

No active documentation should still claim that ADR01 solver-facing properties or the first smoke run are unimplemented.

## Finish

Update `chat/`, report modified files, then STOP.

---

# Step 2 — Improve generic dump metadata

STATUS: COMPLETE

## Goal

Make every dump self-describing enough that a human can immediately understand approximate spatial scale, physical box size, and time information.

This is a **generic library feature**, not ADR01-only.

## Required dump-header additions

Add, in a backward-conscious and documented way:

### Physical time

Record at least:

- timestep / frame index;
- physical time;
- solver `dt` associated with the state if known.

### Simulation / mesh bounds

Add LAMMPS-like box bounds:

```text
ITEM: BOX BOUNDS
xlo xhi
ylo yhi
zlo zhi
```

Use actual mesh bounds, not assumed geometry dimensions.

### Rough spatial resolution

Because the mesh is unstructured tetrahedral, do **not** claim there is a true global `dx`.

Expose a clearly named approximate resolution metric such as:

```text
characteristic_cell_size
```

Define it explicitly and generically. Preferred definition:

\[
h_{\rm char}=\operatorname{median}_K\left(V_K^{1/3}\right),
\]

where `V_K` is the tetrahedral cell volume.

If the existing mesh infrastructure provides a better well-defined characteristic cell diameter, it may be used instead, but document the definition.

Do not label this quantity `dx` without qualification.

### Mesh identity

Keep / add a stable mesh ID if the dump format already supports one.

## Do not put full mesh statistics in every dump

Detailed mesh statistics are optional and, if useful, should be written once per mesh to a separate file such as `mesh-info.json` / existing equivalent.

Do not create that file unless it materially helps the existing architecture.

## Tests

Add/extend dump-format tests covering:

- bounds;
- characteristic size;
- time / dt metadata;
- compatibility with existing dump readers.

Update `dump-format.md` and relevant manual only as needed.

## Pass condition

A user opening one dump can immediately tell:

- the physical time;
- the solver dt;
- approximate object extent in x/y/z;
- approximate mesh cell scale;
- which mesh the fields correspond to.

## Finish

Update `chat/`, show one representative header, then STOP.

---

# Step 3 — Separate solver timestep from output cadence

STATUS: COMPLETE

## Goal

Do not tie saved snapshots to the solver timestep and do not hard-code only three observation times.

Introduce the smallest generic mechanism that supports configurable **uniform physical-time output**.

## Requirements

Keep distinct concepts:

\[
\Delta t_{\rm solve}\neq\Delta t_{\rm output}.
\]

Support at least one simple configuration equivalent to:

```yaml
output:
  every_time: <physical interval>
```

or the closest style already used by the project.

Do not build a general scheduler DSL.

The first goal is simply to request uniformly spaced physical-time snapshots independently of the numerical time step.

If output times do not coincide exactly with solver steps, choose the smallest robust strategy consistent with the existing integrator:

- write at the nearest actual step, or
- interpolate if the existing architecture already supports it.

Do not add complex temporal interpolation to the solver solely for this step.

## ADR01 smoke configuration

Prepare an ADR01 visualization run configuration that can save many uniformly spaced states without changing the previously validated solver dt.

Do not yet choose hundreds of frames blindly; only prove the mechanism works.

## Pass condition

A short ADR01 test run can use one `dt_solve` while writing snapshots at a separately configured uniform physical-time interval.

## Finish

Update `chat/`, report the exact output-cadence behavior, then STOP.

---

# Step 4 — Add ParaView-native time-series output

STATUS: COMPLETE

## Goal

Provide a high-fidelity visualization path in addition to the lightweight dump path.

Roles must remain separate:

- **dump**: lightweight analysis / scripting / reproducibility;
- **ParaView output**: interactive FEM visualization.

## Preferred implementation

Use the simplest format already supported naturally by the current FEniCSx stack, preferably one of:

- XDMF/HDF5;
- VTK/VTU/PVD;
- another existing FEniCSx-native ParaView-compatible writer already used by the repository.

Do not invent a custom visualization format.

## Fields

At minimum export a time series containing:

- mesh;
- region/material identifiers if practical;
- temperature `T`;
- heat-flux vector `q` if practical with the existing field representation.

Prefer preserving the actual FEM temperature field rather than reconstructing it from dump cell-centroid values.

If `q` requires projection to a cell/vector function space, implement the smallest correct projection/recovery consistent with the existing model.

## ParaView target capabilities

The resulting data should support:

- 3D temperature color map;
- rotation / zoom;
- Clip;
- Slice;
- time slider / animation;
- vector glyphs for heat flux if exported.

## Test

Run a short ADR01 sequence and verify that ParaView can open the time series without manual reconstruction.

Do not spend time styling ParaView scenes in this step.

## Pass condition

A user can open one generated time-series dataset in ParaView and interactively inspect `T` over time.

## Finish

Update `chat/`, state the generated files and how to open them, then STOP.

---

# Step 5 — First visualization review

**STATUS: COMPLETE**

## Goal

Use the new visualization path to inspect the already-working ADR01 physics before adding more numerical machinery.

## Run

Use the current validated baseline settings and a modest number of uniformly spaced output states over the existing early-transient interval.

Do not perform a convergence sweep in this step.

## Inspect manually / programmatically

Check for obvious spatial pathologies:

- isolated hot/cold cells;
- checkerboard patterns;
- unexpected discontinuities under perfect-contact assumptions;
- obviously asymmetric behavior where geometry should be symmetric;
- heat-flux vectors pointing in implausible directions;
- visible artifacts around the thin heat-switch proxy;
- blockiness suggesting insufficient mesh resolution.

Create only the minimum screenshots / ParaView state needed to demonstrate that visualization works.

## Pass condition

The baseline run can be inspected spatially, and no obvious visualization-level pathology is left unexplained.

## Finish

Update `chat/` with observations and screenshots/file locations, then STOP.

---

# Step 6 — Make VI solution bounds optional and disable them for diagnostic ADR01 runs

## Goal

Do not hide numerical undershoot/overshoot by forcing the solution into `[1 K, 4 K]` during diagnostic development runs.

The current PETSc VI bounds may remain available as an **explicit opt-in numerical option**, but they must not be the only way the nonlinear transient can run.

## Important distinction

Property validity domains and solution bounds are different concepts.

Do not silently:

- clamp `T`;
- clamp property evaluation;
- extrapolate property tables;
- reinterpret `[1,4] K` property validity as a physical temperature constraint.

## Required behavior

Provide a clear configuration equivalent to:

```text
solution_bounds = off
```

for diagnostic ADR01 runs.

If an unbounded nonlinear iterate/final solution leaves the valid property domain and the current property system cannot evaluate it safely:

- fail explicitly;
- report time / region / Tmin / Tmax if available;
- do not hide the event with clipping or silent extrapolation.

If a final converged field can be produced outside the approved temperature range without violating evaluation rules, record the violation rather than correcting it.

## Range diagnostics

Add a diagnostic summary containing at least:

- Tmin / Tmax;
- number or fraction of out-of-range cells/DOFs if practical;
- affected regions;
- first time of violation.

Optional ParaView visualization field may mark range violations, but do not hard-code presentation colors into the solver.

## Retain bounded mode

Keep VI bounded solving available for controlled numerical experiments and comparison.

Document that a bound-satisfying solution is not by itself proof of physical correctness.

## Pass condition

ADR01 diagnostic runs can be attempted without VI clamping, and any property-domain/range violation becomes visible as a failure or explicit diagnostic rather than being silently suppressed.

## Finish

Update `chat/`, report bounded vs unbounded behavior, then STOP.

---

# Step 7 — Add generic thermal-activity diagnostics

## Goal

Quantify how quickly a transient solution is still changing.

Do not use average heat flux alone as the definition of equilibrium, because steady states can have nonzero heat flow.

## Required metrics

Implement at least:

\[
A_{T,\max}(t)=\max\left|\frac{T^{n+1}-T^n}{\Delta t}\right|
\]

and, if straightforward,

\[
A_{T,\mathrm{RMS}}(t)
=\sqrt{\frac{1}{V}\int\left(\frac{\partial T}{\partial t}\right)^2dV}.
\]

Optionally also report a flux-activity measure such as a volume average of `|q|`, but keep it conceptually separate from transient activity.

## Uses

These quantities should support later decisions about:

- approximate steady-state time;
- output scheduling;
- plotting;
- comparison of runs.

Do not automatically stop the solver based on these metrics yet unless an existing generic stopping mechanism already exists.

## Finish

Update `chat/`, show metrics from a short ADR01 run, then STOP.

---

# Step 8 — Add automatic numerical validation report

## Goal

Each important run should produce a compact machine-readable validation summary so that numerical failures do not require manual dump inspection.

Prefer a generic format such as `validation.json` or an existing report mechanism.

Do not create multiple competing reports.

## Minimum contents

### Run metadata

- mesh ID;
- cell count;
- `h_char`;
- `dt`;
- quadrature degree;
- physical start/end time.

### Temperature / property range

- Tmin / Tmax;
- range violations;
- affected regions if available.

### Solver

- total nonlinear iterations;
- failed steps;
- convergence failures.

### Thermal activity

- max / RMS `|dT/dt|` at final time.

### Heat-flow diagnostics

Record the major ADR01 heat-flow observables already available.

Do not yet claim strict conservation from raw CG interface fluxes.

### Future hooks

Leave room for later:

- energy-balance residual;
- one-sided interface-flux mismatch;
- convergence-study metrics.

Do not implement these future hooks prematurely unless they are trivial consequences of existing code.

## Finish

Update `chat/`, show one validation report, then STOP.

---

## Step 8A — Initial-condition representation baseline audit

Before final energy-balance or engineering interpretation, quantify how an
intended discontinuous semantic `by_region` initial condition is represented in
the current continuous P1 temperature field. ADR01 is the known case: GGG is
intended to start at 1 K while its touching copper cylinder starts at 4 K.

The audit must check:

1. intended semantic `by_region` IC versus the actual FE field at `t = 0`;
2. per-region Tmin, Tmax, and average at `t = 0`;
3. ideal textual IC versus actual FE initial stored-energy difference;
4. initial interface heat-flux magnitude;
5. whether subsequent energy-balance calculations use the actual solver `t = 0`
   field rather than the idealized textual IC.

Do not interpret the `t = 0` interface heat flux as a mesh-independent engineering
heat leak. Resolve or quantify this numerical representation issue before final
energy-balance or engineering interpretation. This gate records required evidence;
it does not prescribe DG, projection, smoothing, or another solution.

---

# Step 9 — Energy-balance audit

## Goal

Check whether the transient simulation conserves energy to an acceptable numerical tolerance before making engineering interpretations.

Because `cp = cp(T)`, do not approximate stored energy merely as `rho * cp * T`.

Use a thermodynamically consistent internal-energy change:

\[
\Delta E
=\int_\Omega\rho\left[\int_{T_0}^{T}c_p(\theta)\,d\theta\right]dV,
\]

with a clearly defined reference.

Compare with net external heat entering through actual non-adiabatic boundaries over time.

Internal interface fluxes must cancel from the global balance and should not be double-counted.

## Report

At minimum provide:

- stored-energy change;
- integrated external heat input;
- absolute residual;
- relative residual;
- residual vs time if practical.

Run first on the existing baseline case.

## Pass condition

Energy residual is quantified and small enough to justify proceeding to convergence studies, or a clear numerical defect is identified.

Do not hide a poor balance.

## Finish

Update `chat/`, report the balance, then STOP.

---

# Step 10 — Interface heat-flux consistency audit

## Goal

Assess the reliability of the current interface heat-flow diagnostics for discontinuous material conductivity.

For selected interfaces, compute flux from both sides separately where feasible:

\[
Q_+,\qquad Q_-.
\]

Check the mismatch expected for a conservative interface:

\[
Q_+ + Q_- \approx 0.
\]

Prioritize:

- GGG ↔ Cu cold-chain interface;
- heat-switch ↔ Cu interface;
- support ↔ hot/cold interfaces.

Do not redesign the FEM method in this step.

The purpose is to determine whether current heat-flow numbers are adequate diagnostics or require future flux recovery / conservative postprocessing.

## Finish

Update `chat/`, report mismatch metrics, then STOP.

---

# Step 11 — Quadrature sensitivity

## Goal

Test whether the currently explicit nonlinear quadrature degree is influencing ADR01 results materially.

Use the same:

- mesh;
- initial/boundary conditions;
- material model;
- timestep;
- end time.

Compare at least:

\[
p_{\rm quad}=2,3,4.
\]

If compilation/runtime makes one degree impossible, record that explicitly rather than silently skipping it.

## Observables

At common physical times compare:

- GGG average T;
- cold-stage average T;
- sample average T;
- main heat-flow diagnostics;
- energy residual if Step 9 is available.

## Pass condition

Quantify the difference between quadrature degrees and decide whether degree 2 is sufficient for the present Baseline v1 accuracy target.

Do not call this a full convergence study by itself.

## Finish

Update `chat/`, report the comparison, then STOP.

---

# Step 12 — Timestep convergence

## Goal

Repeat / formalize the timestep refinement now that visualization and diagnostics exist.

Use a fixed mesh and accepted quadrature degree.

At minimum compare the already-used timestep sequence or a justified replacement.

Use common physical observation times.

## Required outputs

Compare:

- regional temperatures;
- important heat flows;
- thermal activity;
- energy residual.

Estimate observed refinement behavior where meaningful.

Do not call a timestep merely “converged” because plots look similar.

## Finish

Update `chat/`, state the timestep selected for later mesh study, then STOP.

---

# Step 13 — Mesh convergence

## Goal

Study spatial resolution after the output/diagnostic pipeline is trustworthy.

Do not use a fictitious global `dx`; use the actual mesh-control setting plus measured `h_char` from each generated mesh.

Prepare at least three practically affordable mesh levels if runtime permits.

For every mesh record:

- mesh-control setting;
- nodes/cells;
- measured `h_char`;
- heat-switch thickness resolution;
- relevant quality warnings if available.

Use the same accepted timestep and quadrature degree.

Compare the same observables as Step 12.

The initial-condition representation audit must also compare across mesh levels:

- the actual `t = 0` per-region Tmin, Tmax, and average;
- the ideal-textual versus actual-FE initial stored-energy discrepancy;
- the initial interface heat-flux magnitude;
- whether these representation discrepancies decrease as measured `h_char` is
  refined.

## Finish

Update `chat/`, state the mesh chosen for subsequent baseline runs, then STOP.

---

# Step 14 — Consolidated numerical-convergence summary

## Goal

Summarize the three numerical resolution axes:

\[
h,\qquad \Delta t,\qquad p_{\rm quad}.
\]

Do not necessarily run a full Cartesian 3×3×3 sweep.

Use the sequential studies from Steps 11–13, then run only a small number of cross-check cases if needed to make sure the chosen settings do not interact badly.

Produce a compact table / existing report describing:

- selected mesh / `h_char`;
- selected `dt`;
- selected quadrature degree;
- sensitivity of key observables;
- energy-balance quality;
- known limitations.

Do not create a large new report document if the existing `chat/` + validation output can carry this information cleanly.

## Finish

Update `chat/`, then STOP.

---

# Step 15 — Determine a useful visualization time horizon

## Goal

Estimate how long the ADR01 transient must be simulated to show the physically important evolution, instead of arbitrarily choosing video length from the current 0.05 s smoke run.

Use the thermal-activity metrics from Step 7 and the validated numerical settings from Steps 11–14.

Extend the simulation progressively until the system behavior is understood well enough to identify:

- fast initial cooling/equalization;
- any minimum cold-stage/sample temperature;
- subsequent warming from parasitic heat leaks;
- approximate approach toward the final 4 K equilibrium under the current simplified model.

Do not jump immediately to an extremely long run.

## Equilibrium / slow-change indicator

Use `|dT/dt|` metrics as the primary measure of how slowly the field is changing.

Flux magnitude may be reported separately but is not the generic definition of steady state.

## Finish

Update `chat/` with the recommended physical time horizon for visualization, then STOP.

---

# Step 16 — Define visualization sampling and movie plan

## Goal

Define output snapshots independently from rendered video frames.

## Linear-time product

A linear physical-time animation is required because real time perception matters.

Define a uniform physical-time sequence of saved visualization states that adequately resolves the transient without forcing one simulation snapshot per movie frame.

ParaView may interpolate between stored states when rendering, if supported and visually acceptable.

Target movie frame rate may be 24 fps, but do **not** automatically equate:

```text
24 fps × 30 s movie = 720 FEM dumps
```

unless testing shows that this many solver snapshots are actually needed.

## Log-time product

Also prepare an optional second visualization plan using a logarithmic or otherwise compressed time mapping so both fast and slow evolution are visible.

Do not replace the linear-time product with the log-time product.

## Finish

Update `chat/` with:

- physical time horizon;
- number of stored states;
- output interval / sampling strategy;
- planned linear movie duration/fps;
- optional log-time strategy.

Then STOP.

---

# Step 17 — Produce first ADR01 visualization deliverables

## Goal

Create the minimum useful visual set matching the original thermal-modeling request.

Produce, using ParaView or a reproducible postprocessing path:

1. 3D temperature distribution over time;
2. heat-flux vector visualization over temperature background;
3. at least one useful cut/slice view;
4. linear physical-time animation;
5. optional log-time animation;
6. line plot of `T_GGG`, `T_cold_stage`, `T_sample` vs time;
7. line plot of the major heat-leak paths vs time.

Do not over-style or create a large presentation system yet.

The goal is to make the physics inspectable and to satisfy the core requested observables:

- 3D temperature distribution;
- heat-flux distribution;
- major parasitic heat-leak paths;
- cold-stage temperature.

## Finish

Update `chat/` with file locations and a short interpretation, then STOP.

---

# Step 18 — Future-physics roadmap only

## Goal

Record, but do **not** implement, the next physical extensions.

Ensure active descriptive documentation has a concise future-work section including:

- finite thermal contact resistance / contact conductance;
- hardware-specific heat switch and eventual ON state;
- real geometry replacement;
- sample heat load;
- radiation if needed;
- superconducting magnet if reinstated by project requirements;
- magnet heat load / thermal compatibility if later requested;
- full magnetocaloric / ADR cycle only in a later model.

For the superconducting magnet, current Baseline v1 treatment is:

> omitted from the active simplified geometry/model.

Future possible treatment:

> a region thermally anchored to the 4 K stage, with optional magnet heat loss if later required.

Do not add the magnet now solely because it appeared in the original project email.

## Finish

Update `chat/`, report the future-work list, then STOP.

---

# Completion condition for `steps2.md`

This roadmap is complete when:

1. dump metadata are self-describing;
2. output cadence is independent of solve timestep;
3. ParaView-native time-series visualization works;
4. range violations are visible rather than hidden by mandatory VI bounds;
5. thermal-activity and validation diagnostics exist;
6. energy balance and interface-flux consistency are audited;
7. quadrature, timestep, and mesh sensitivity are quantified;
8. a physically meaningful visualization time horizon is selected;
9. linear-time and optional log-time visualization products are generated;
10. generic 3D/transient interface contact resistance, magnet, and other
    second-stage ADR01 physics are recorded as future work without hiding the
    existing steady thin-layer and 1D reference contact paths.

At no point should Codex automatically continue to the next numbered step without an explicit `next` from the user.
