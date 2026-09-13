# ADR01

ADR01 is the case-local model for a simplified single-stage adiabatic
demagnetization refrigerator after demagnetization. Baseline v1 is a 3D
transient solid-conduction model; it does not include the magnetocaloric cycle,
radiation, convection, electromagnetic physics, or non-ideal ordinary contacts.

Current sources of truth:

- `geometry-requirement/`: placeholder component geometry and connectivity.
- `parameters-requirement/ADR01_material_parameters_baseline_v1.md`: canonical
  Baseline v1 material, property, and heat-switch decisions.
- `arch.md`: case architecture and responsibility boundaries.
- `steps.md`: current progress, unresolved gates, and next work.
- `requirement/` and `parameters-requirement/ADR01_papers_v4/`: research evidence;
  they are not active specifications and must not be edited as part of model implementation.

Generated geometry and validation artifacts are described in
`geometry-report.md`. Solver-facing material properties, region-wise initial
conditions, and the transient case are implemented. The first 0.05 s
early-transient smoke run is complete; numerical validation and production-time
studies continue under the repository-level `steps2.md` roadmap.

The visualization smoke configuration uses the validated solver
`dt_s=0.00025 s` with independent uniform output every `0.0025 s`; requested
times map to the nearest actual solver step without temporal interpolation.
Each run writes the initial field as `0.dump` before solving. Before regeneration,
the runner removes only old `dump/*.dump` and `summary.json` in that run's own
`output/dt_<dt>/` directory so cadence changes cannot mix stale snapshots.

For ParaView, open `output/dt_<dt>/visualization/fields.pvd`. The time series
contains the actual P1 `temperature` field plus DG0 cell `heat_flux` and
`region_ID`; ParaView can use them directly for color maps, Clip, Slice, animation,
and vector glyphs.
