# Handoff

## Current goal and state

ADR01 now has a plan-driven continuous-trajectory workflow. The sole new input
is `run/01_ADR01/baseline-v1.yaml`; run it with
`python3 run/01_ADR01/workflow.py run run/01_ADR01/baseline-v1.yaml` through the
WSL wrapper. It validates the plan before FEM setup, executes the accepted S0
bootstrap, then each later production interval plus a same-start `dt/2`
reference, and creates one
`output/<scenario>/` trajectory with a manifest, production CSV, logs,
physical-time dumps/checkpoints, merged PVD, and nested validation evidence.

Warn/strict handling, near-zero-flow diagnostics, and accumulated validity are
implemented. The complete `baseline-v1` trajectory has run from 0 to 420 s:
S0 is the accepted baseline, S1–S4 all pass the current provisional timestep
validation, and `validated_through_s = 420`. Scenario-level output is under
`run/01_ADR01/output/baseline-v1/`.

Shared runtime logging now lives in `lib/log.py`. ADR01 prints first/every-N/final
solver-step progress to the terminal (default N=10) and plan-driven runs append
and immediately flush the same stream to `output/<scenario>/run.log`. The
manifest includes total workflow wall time and start/finish timestamps.

Generic ParaView snapshot generation lives in
`postprocess/paraview_snapshots.py`, outside the simulation engine. A saved
ParaView `.pvsm` supplies camera/display/LUT/scalar-bar state; a JSON/YAML job
selects physical times across multiple PVD files, resolution, and an optional
fixed color range. Frames are globally time-sorted and duplicate times are removed.

Long-time restart orchestration is implemented in `run/01_ADR01/restart.py`.
It verifies the `baseline-v1` manifest, 420 s checkpoint format/time/mesh/vector,
parent validation boundary, and exact restart-time scalar continuity before
delegating to `main.run()`. A 420-424 s regression passed without modifying the
parent. Python callers now receive the `main.run()` result without an unsolicited
JSON print; the direct CLI still prints it. Child manifests store portable
case-relative parent paths plus both the parent commit and dirty state. The
`baseline-v1-cont-420s-1800s` production continuation completed, but remains
exploratory: `validation_status = NOT_PERFORMED` and `validated_through_s = 420`.
`run/01_ADR01/validate_continuation.py` is ready to reuse that production result,
run a same-checkpoint dt 1 s reference, and call `workflow.compare()`; it has not
been executed.

The earlier ADR01 Baseline v1 smoke milestone remains complete. The placeholder
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
the validated baseline and has not been accuracy-validated. Output is under
`run/01_ADR01/output/dt_0.1/`.

A follow-up 0–1 s timestep comparison also ran `dt=0.05` and `0.025 s`, with all
runs sampled at common 0.1 s times. `0.1 vs 0.05` differs by about 0.087–0.088 K
for cold-stage/sample averages and 10.7–17.3% for the three requested heat flows,
so `dt=0.1 s` is not supported for the fast early interval. `0.05 vs 0.025`
differs by 0.0118–0.0120 K for cold-stage/sample, 5.35–5.69% for support flows,
and 0.50% for switch flow; it narrowly misses the provisional 0.01 K / 5% gates.
The next recommended check is `dt=0.0125 s` over 1 s, but it has not been started.
Tables and plot are in `run/01_ADR01/output/timestep_convergence_1s/`.

ADR01 now has minimal serial restart support in its existing runner. Each run
writes `checkpoint_t_<absolute-time>.npz` with the exact P1 vector, mesh ID, and absolute
time; `--restart` loads it and `--end` is absolute. Continuation output uses
`dt_<dt>_from_<start-time>`. A validated `t=0.05 s` checkpoint now exists at
`run/01_ADR01/output/dt_0.00025/checkpoint_t_0.05.npz`. Time-qualified names
prevent later runs with the same dt and a different end time from replacing it. A two-step `dt=0.1 s`
restart to `t=0.25 s` passed, produced times `0.05/0.15/0.25 s`, and its initial
GGG/cold-stage/sample averages and three heat flows exactly matched the source
run. The later 0.5–5 s S2 branch comparison is accepted.

The checkpoint collision identified after the split-run test is resolved. The
validated source run was regenerated to `t=0.05 s`; its checkpoint metadata is
format v1, time 0.05 s, 2506 finite P1 values in `[1,4] K`. The ambiguous stale
`output/dt_0.00025/checkpoint_final.npz` was removed. Future end times use distinct
`checkpoint_t_<absolute-time>.npz` names.

ADR01 now has a case-local segmented production/validation workflow documented
in `run/01_ADR01/segmented-workflow.md`; `output/README.md` keeps guidance beside
generated data. Continuation names encode run type, absolute interval, and dt.
`workflow.py` compares common-time region/flow metrics and endpoint full-P1
vectors, extracts interpolated failure times, and reproducibly selects stratified
spot-audit checkpoints. No adaptive controller or MPI layer was added.

S1 (`0.05→0.5 s`) is accepted: candidate dt 0.025 s versus 0.0125 s differed by
0.002282/0.002285 K for cold-stage/sample averages, 0.826/0.913% for support
flows, and 0.081% for switch flow. Endpoint full-P1 max/L2 differences were
0.004299 K / 0.037384 K. Both runs passed finite and `[1,4] K` sanity checks.
The accepted endpoint is
`run/01_ADR01/output/segment_t_0.05_to_0.5_dt_0.025/checkpoint_t_0.5.npz`.
S2, S3, and S4 are also accepted under the current provisional gates.

Before S2, workflow cadence was corrected: `--summary-every` now independently
controls lightweight scalar observations and P1 checkpoints (default every
solver step), while `--output-every` controls only dump/VTK. Audit curvature uses
signed slopes, random points exclude endpoints, and GGG is explicitly an
informational metric. The cadence regression and expanded self-test pass.

S2 (`0.5→5 s`) is accepted: dt 0.1 versus 0.05 s differed by 0.0003704 K for
cold-stage/sample averages, 0.460–0.463% for support flows, and 0.0236% for
switch flow. Endpoint full-P1 max/L2 differences were 0.001478/0.016361 K.
Both runs passed finite/range sanity checks and locate the sample minimum at
`t=0.6 s` near 1.0715–1.0717 K. The candidate stores 46 scalar/checkpoint states
but only 10 heavy PVD frames, demonstrating cadence separation. Accepted endpoint:
`run/01_ADR01/output/segment_t_0.5_to_5_dt_0.1/checkpoint_t_5.npz`.
The scenario-level run subsequently validated S3 and S4 through 420 s.

Split-run trajectory equivalence is now verified. A continuous `0→0.10 s` run
and a `0→0.05 s` plus checkpoint restart `0.05→0.10 s` run both used
`dt=0.00025 s`. At `t=0.10 s`, all 2506 P1 values were bitwise identical
(`max_abs=0`, `L2=0`), and GGG/cold-stage/sample averages plus both support flows
and switch flow were also bitwise identical. Restart is therefore trusted for
the current frozen serial case and underpins the completed segmented trajectory.

Before engineering interpretation: complete the planned visualization review,
initial-condition representation audit, mesh convergence, and energy-balance
review. Do not extend to long hold, MCE, finite field, switch ON, radiation,
convection, loads, contact resistance, or hardware geometry without approval.

Next exact action: run `python3 run/01_ADR01/validate_continuation.py` through the
WSL wrapper to compare the completed 420-1800 s dt 2 s trajectory against a dt 1 s
reference. Do not rerun either completed production trajectory. The pre-existing
`steps2.md` Step 6 remains the next unrelated roadmap implementation step.
