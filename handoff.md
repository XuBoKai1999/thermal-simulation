# Handoff

## Current goal and state

ADR01 Baseline v1 early-transient smoke milestone is complete. The placeholder
geometry is approved only for this numerical smoke run, not verified hardware.
Canonical parameters and evidence remain untouched.

`run/01_ADR01/case.yaml`, `properties.py`, and three case-local tables implement
Cu RRR100, GGG H=0, G-10 axial-effective, and the finite-leakage OFF switch proxy.
Region-wise IC sets GGG=1 K and all other solved solids=4 K. Three internal hot
contacts are fixed at 4 K; other exposed boundaries are naturally adiabatic.

## Framework changes

- `by_region` IC uses semantic cell tags, a finite `default_K`, and validated
  region overrides; uniform/split-x remain compatible.
- Tables accept optional positive `scale` and restricted `domain_K`.
- Nonlinear transient forms use degree-2 quadrature. Shared table domains produce
  PETSc VI Newton bounds; this eliminated a real 0.7709 K consistent-mass
  undershoot and prevents property extrapolation.

## Validation and results

Property checkpoints pass; switch G=6e-5 W/K, R=16666.6667 K/W, placeholder
C=9.81747704e-9 J/K, and its adjacent-Cu capacitance ratio is 4.22858e-5.
Test 02, Test 06, nonlinear transient, and Test 07 pass.

Timestep runs to 0.05 s at dt=1e-3, 5e-4, and 2.5e-4 s all converge. Select
dt=2.5e-4 s: Tmin/Tmax=1/4 K; GGG avg=1.098265 K; cylinder_3 avg=1.172854 K;
cold_stage avg=1.177916 K; sample avg=1.178020 K; switch flow=172.343 uW;
support flows=69.223/77.701 uW. Heat-flow positive means toward decreasing z
(hot to cold); GGG/cylinder_3 flow is -2.46543 mW, so heat enters GGG as expected.
Outputs are under `run/01_ADR01/output/dt_*/`.

## Current roadmap state

Root `steps2.md` Steps 1–5 are complete. Step 4 added a ParaView-native VTK/PVD
time series, separate from the ADR text dumps. ADR01 writes the actual continuous
P1 `temperature` as point data and DG0 `heat_flux` and `region_ID` as cell data.
The verified short-run entry point is
`run/01_ADR01/output/dt_0.00015/visualization/fields.pvd`; ParaView reads frames at
`t = 0` and `t = 0.0003` with all three fields. Step 5 then ran the validated
`dt=0.00025 s`, `end=0.05 s` baseline with 21 uniformly spaced states. The first
spatial review found no isolated cells, checkerboard pattern, unexpected
perfect-contact discontinuity, or implausible global heat-flow direction. The
largest support-pair average-temperature difference was about `0.00206 K`.
Known t=0 P1 IC smoothing and local thin-switch blockiness remain documented for
the planned IC audit and mesh convergence.

A separate diagnostic smoke run used `dt=0.1 s`, `end=1.0 s`, and 10 steps. It
converged in about 41 seconds with 36 total Newton iterations and stayed within
`1–4 K`. This demonstrates bounded solver convergence only: the timestep is 400x
the validated baseline and has not been accuracy-validated. No 420-second run was
started. Output is under `run/01_ADR01/output/dt_0.1/`.

A follow-up 0–1 s timestep comparison also ran `dt=0.05` and `0.025 s`, with all
runs sampled at common 0.1 s times. `0.1 vs 0.05` differs by about 0.087–0.088 K
for cold-stage/sample averages and 10.7–17.3% for the three requested heat flows,
so `dt=0.1 s` is not supported for the fast early interval. `0.05 vs 0.025`
differs by 0.0118–0.0120 K for cold-stage/sample, 5.35–5.69% for support flows,
and 0.50% for switch flow; it narrowly misses the provisional 0.01 K / 5% gates.
The next recommended check is `dt=0.0125 s` over 1 s, but it has not been started.
Tables and plot are in `run/01_ADR01/output/timestep_convergence_1s/`.

ADR01 now has minimal serial restart support in its existing runner. Each run
writes `checkpoint_final.npz` with the exact P1 vector, mesh ID, and absolute
time; `--restart` loads it and `--end` is absolute. Continuation output uses
`dt_<dt>_from_<start-time>`. A validated `t=0.05 s` checkpoint now exists at
`run/01_ADR01/output/dt_0.00025/checkpoint_final.npz`. A two-step `dt=0.1 s`
restart to `t=0.25 s` passed, produced times `0.05/0.15/0.25 s`, and its initial
GGG/cold-stage/sample averages and three heat flows exactly matched the source
run. No 5-second branch comparison or 420-second run has started.

Split-run trajectory equivalence is now verified. A continuous `0→0.10 s` run
and a `0→0.05 s` plus checkpoint restart `0.05→0.10 s` run both used
`dt=0.00025 s`. At `t=0.10 s`, all 2506 P1 values were bitwise identical
(`max_abs=0`, `L2=0`), and GGG/cold-stage/sample averages plus both support flows
and switch flow were also bitwise identical. Restart is therefore trusted for
the current frozen serial case. No long branch study or 420-second run started.

Before engineering interpretation: complete the planned visualization review,
initial-condition representation audit, mesh convergence, and energy-balance
review. Do not extend to long hold, MCE, finite field, switch ON, radiation,
convection, loads, contact resistance, or hardware geometry without approval.

Next exact action: execute `steps2.md` Step 6 only after the user says next.
