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

Root `steps2.md` Steps 1–4 are complete. Step 4 added a ParaView-native VTK/PVD
time series, separate from the ADR text dumps. ADR01 writes the actual continuous
P1 `temperature` as point data and DG0 `heat_flux` and `region_ID` as cell data.
The verified short-run entry point is
`run/01_ADR01/output/dt_0.00015/visualization/fields.pvd`; ParaView reads frames at
`t = 0` and `t = 0.0003` with all three fields.

Before engineering interpretation: complete the planned visualization review,
initial-condition representation audit, mesh convergence, and energy-balance
review. Do not extend to long hold, MCE, finite field, switch ON, radiation,
convection, loads, contact resistance, or hardware geometry without approval.

Next exact action: execute `steps2.md` Step 5 only after the user says next.
