# ADR01 segmented transient workflow

ADR01 production transients use explicit fixed-timestep segments. Candidate
values are hypotheses until each segment passes a same-checkpoint `dt` versus
`dt/2` comparison.

| Segment | Absolute interval | Candidate dt | Status |
|---|---:|---:|---|
| S0 | 0–0.05 s | 0.00025 s | validated |
| S1 | 0.05–0.5 s | 0.025 s | accepted against 0.0125 s |
| S2 | 0.5–5 s | 0.1 s | accepted against 0.05 s |
| S3 | 5–50 s | 0.5 s | candidate, not validated |
| S4 | 50–420 s | 2 s; 5 s may be tested | candidate, not validated |

The accepted endpoint checkpoint of one segment is the sole start state for all
branches of the next segment. Do not substitute a dump or VTK field for the P1
checkpoint. Do not use a fine `0.00025 s` reference for every later interval;
compare the candidate dt with dt/2, adding dt/4 only when necessary.

## Run naming and cadence

Continuation directories encode purpose, absolute interval, and timestep:

```text
segment_t_0.05_to_0.5_dt_0.025/
validation_t_0.05_to_0.5_dt_0.0125/
audit_t_87_to_97_dt_1/
```

Use `--run-type segment`, `validation`, or `audit`. From-zero reference output
keeps the legacy `dt_<dt>/` name. Every saved output state also has an exact P1
`checkpoint_t_<absolute-time>.npz`; the endpoint checkpoint is always saved.
Solver dt, lightweight `--summary-every`, and heavy `--output-every` are
independent. Summary observations store scalar diagnostics, per-step Newton
iterations, and a restartable P1 checkpoint without writing dump/VTK. The
summary cadence defaults to every solver step. Full dump/VTK output should be
sparse in long segments (for example solver dt 2 s, summary every 2 s, and full
output every 10 s).

## Segment convergence

Example S1 commands:

```powershell
.\scripts\wsl-run.ps1 "python3 run/01_ADR01/main.py --restart run/01_ADR01/output/dt_0.00025/checkpoint_t_0.05.npz --run-type segment --dt 0.025 --end 0.5 --summary-every 0.025 --output-every 0.05"
.\scripts\wsl-run.ps1 "python3 run/01_ADR01/main.py --restart run/01_ADR01/output/dt_0.00025/checkpoint_t_0.05.npz --run-type validation --dt 0.0125 --end 0.5 --summary-every 0.0125 --output-every 0.05"
.\scripts\wsl-run.ps1 "python3 run/01_ADR01/workflow.py compare run/01_ADR01/output/segment_t_0.05_to_0.5_dt_0.025 run/01_ADR01/output/validation_t_0.05_to_0.5_dt_0.0125 run/01_ADR01/output/validation_s1"
```

`workflow.py compare` checks endpoint full-P1 max/L2 error, common-time GGG,
cold-stage, and sample averages, both support flows, switch flow, temperature
range, finite values, Newton iterations, wall time, and interpolated sample
failure times at 1.5/2/3 K. It writes CSV, JSON, a plot, and `report.md`.

Provisional acceptance gates are `cold_stage/sample <0.01 K` or `<1%`, and each
heat flow `<5%` relative to the finer run's maximum magnitude. GGG temperature
is explicitly informational rather than shown as an unconditional pass. Near-zero flows
therefore do not use unstable pointwise relative errors. These are engineering
screening criteria, not universal accuracy standards. Final production approval
is based primarily on interpolated failure-time convergence.

## Spot audits

After production, select reproducible checkpoints with:

```powershell
.\scripts\wsl-run.ps1 "python3 run/01_ADR01/workflow.py select-audits SUMMARY... --output AUDIT_POINTS.json --seed 20260914"
```

Selection includes each segment start, near-end boundary, maximum absolute signed
sample slope, maximum absolute second-difference curvature, points nearest failure thresholds, and
a small seeded random sample. Each audit runs coarse and fine continuations from
the same selected checkpoint and uses the same comparison utility. Spot audits
supplement rather than replace segment convergence because their starting state
may already contain accumulated production error.

## Acceptance and failure time

A segment is not accepted after solver failure, non-finite diagnostics, or a
temperature outside the current Baseline v1 expectation `[1,4] K`. Heat-flow
signs remain recorded for physical review. Failure time is the upward crossing
of sample-average temperature and is linearly interpolated between adjacent
solver output states; threshold-nearby refinement should be used when needed.

This workflow deliberately excludes MPI optimization, adaptive stepping, new
physics, and automatic execution of the 420-second production run.

## Current accepted chain

S1 passed its provisional gates. Its accepted endpoint is:

```text
output/segment_t_0.05_to_0.5_dt_0.025/checkpoint_t_0.5.npz
```

Detailed S1 CSV/JSON results, plot, reproducible audit selection, and `report.md`
are under `output/validation_s1/`.

S2 also passed its provisional gates. Its accepted endpoint is:

```text
output/segment_t_0.5_to_5_dt_0.1/checkpoint_t_5.npz
```

S2 details are under `output/validation_s2/`. S3 and S4 remain unvalidated.
