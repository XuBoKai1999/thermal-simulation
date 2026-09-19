# Future Development Roadmap

## Purpose

This document records possible future directions for `thermal-simulation` after the current ADR01 workflow is stable and validated.

The priority is **not** to optimize prematurely. The current framework should first produce trustworthy, reproducible ADR results. Future work should then be driven by measured bottlenecks and verification tests.

The intended architecture remains:

```text
physics flexibility
        +
Python-first workflow
        +
compiled FEniCSx/PETSc numerical backend
        +
AI-agent-compatible project structure
```

---

## 1. Performance: Profile Before Optimizing

### Current principle

Do not assume that the simulation is slow because the framework is Python-based.

Python mainly orchestrates the model and workflow. The finite-element forms are represented through UFL and the computational kernels are compiled by the FEniCSx toolchain, while sparse linear/nonlinear algebra is handled by PETSc.

Therefore, adding Python-level JIT tools such as Numba is **not currently a priority**.

### Add performance instrumentation

A future profiling layer should separate total runtime into approximately:

```text
t_total
├── t_setup
├── t_form/JIT
├── t_solve
│   ├── assembly
│   ├── nonlinear iterations
│   └── linear solves
├── t_analysis
└── t_IO
```

For transient simulations, record at least:

- total number of time steps;
- wall time per step;
- nonlinear iterations per step;
- total nonlinear iterations;
- output/checkpoint time;
- mesh DOF count;
- solver configuration.

### Suggested benchmark matrix

Using a fixed ADR01 mesh, compare:

| Case | Purpose |
|---|---|
| Constant material properties | Numerical baseline |
| Current temperature-dependent tables | Measure nonlinear/material cost |
| Reduced table resolution | Measure UFL interpolation-expression cost |
| Output disabled/minimized | Measure I/O cost |
| Alternative PETSc solvers | Measure linear-solver cost |

Optimization should follow the measured dominant cost.

---

## 2. PETSc Solver Strategy

The current nonlinear solver uses Newton/SNES with a direct LU solve. This is a good baseline because it is robust and convenient for verification.

However, for larger meshes, repeated sparse LU factorization may become the dominant computational cost.

Possible future work:

```text
current:
Newton/SNES
    ↓
preonly + LU

future candidates:
Newton/SNES
    ↓
Krylov solver
    ↓
problem-appropriate preconditioner
```

Candidate PETSc configurations should be benchmarked rather than selected by assumption.

Do not remove the LU configuration; retain it as a robust reference/verification mode.

---

## 3. Material-Property Evaluation

Temperature-dependent material tables are currently converted into UFL expressions. This is desirable because material evaluation remains inside the compiled finite-element expression rather than becoming a Python callback at every quadrature point.

Maintain this principle for future constitutive models whenever practical:

```text
Python specification
      ↓
UFL expression
      ↓
compiled FEM kernel
```

Potential future concern: large tabulated datasets may create deeply nested piecewise expressions and increase form-compilation or quadrature-evaluation cost.

If profiling identifies this as significant, investigate alternatives such as:

- fitted analytic correlations;
- spline/polynomial representations compatible with compiled evaluation;
- reduced tables with quantified interpolation error;
- other FEniCSx-compatible coefficient representations.

Any optimization must preserve the original source data and traceability.

---

## 4. Time Integration

### Current method: Backward Euler

The current transient formulation uses implicit Backward Euler:

\[
\rho(T)c_p(T)
\frac{T^{n+1}-T^n}{\Delta t}
-
\nabla\cdot\left[k(T)\nabla T^{n+1}\right]
=0.
\]

Backward Euler is first-order accurate in time:

\[
E_t = O(\left.\Delta t\right).
\]

It should remain available permanently because it is simple, robust, strongly dissipative, and useful as a reference solver for stiff diffusion problems.

### Add BDF2

A high-priority future extension is second-order Backward Differentiation Formula (BDF2):

\[
\frac{3T^{n+1}-4T^n+T^{n-1}}{2\Delta t}.
\]

Expected temporal accuracy:

\[
E_t = O(\Delta t^2).
\]

The implementation should expose the integrator through case configuration rather than hard-coding it into ADR01, for example:

```yaml
time:
  integrator: backward_euler
```

or:

```yaml
time:
  integrator: bdf2
```

Backward Euler should be used to initialize BDF2 when the second previous state is unavailable.

### Crank–Nicolson

Crank–Nicolson may also be supported later as another second-order method:

\[
\frac{T^{n+1}-T^n}{\Delta t}
=
\frac{1}{2}
\left[
\mathcal{L}(T^{n+1})+\mathcal{L}(T^n)
\right].
\]

However, for the present thermal-diffusion use case, BDF2 is a higher priority because its dissipative behavior is likely to be more convenient for stiff transients.

---

## 5. Verification of New Time Integrators

Do not introduce BDF2 or another integrator directly into ADR01 without verification.

Use the existing transient analytical bar problem and perform temporal convergence tests.

Expected behavior:

\[
E_{BE}\propto\Delta t,
\]

\[
E_{BDF2}\propto\Delta t^2.
\]

A log-log error-versus-time-step plot should therefore approach slopes of approximately 1 and 2 respectively.

Acceptance criteria should include:

- correct convergence order;
- agreement with analytical/reference solutions;
- stable behavior over the intended material-property range;
- regression tests protecting existing Backward Euler behavior.

---

## 6. Adaptive Time Stepping

Adaptive time stepping is likely to provide more practical acceleration for ADR01 than Python-level JIT optimization.

The physical motivation is straightforward:

```text
rapid transient  -> small dt
slow evolution   -> large dt
```

The current segmented-time workflow can be regarded as a manually prescribed approximation to adaptive stepping.

### Near-term

Continue using segmented time windows with convergence/spot checks:

```text
early time     small dt
intermediate   medium dt
late time      large dt
```

This remains transparent and easy to audit.

### Future automatic controller

A future solver may expose:

```yaml
time:
  integrator: bdf2
  adaptive: true
  dt_initial_s: 0.00025
  dt_min_s: 0.00001
  dt_max_s: 0.5
  rtol: 1.0e-4
```

Possible error-control strategies include comparison between solutions of different temporal order, step doubling, or another established local-error estimator.

Conceptually:

\[
\epsilon_n > \epsilon_{target}
\Rightarrow
\Delta t_{n+1}<\Delta t_n,
\]

\[
\epsilon_n \ll \epsilon_{target}
\Rightarrow
\Delta t_{n+1}>\Delta t_n.
\]

The controller must include limits on time-step growth/shrinkage and explicit rejection/retry behavior.

---

## 7. Preserve Auditability

Performance improvements must not weaken the current verification philosophy.

For long production runs, retain mechanisms such as:

- segmented runs;
- checkpoint/restart;
- independently configurable output cadence;
- high-accuracy spot checks at selected times;
- convergence studies;
- solver statistics;
- reproducible case files.

A faster result is not useful if its numerical accuracy cannot be demonstrated.

---

## 8. Longer-Term Physics Extensions

The framework should remain capable of extending the governing equations rather than being limited to ordinary heat conduction.

Potential future terms include:

### Radiation

\[
Q_{rad}=Q_{rad}(T,T_{environment},\epsilon,\ldots)
\]

### Magnetocaloric / ADR physics

Possible state dependence may include:

\[
k=k(T,B),
\qquad
c=c(T,B),
\]

and an additional magnetic/magnetocaloric source term schematically represented as

\[
Q_{MCE}=Q_{MCE}(T,B,\dot B,\ldots).
\]

### Multiphysics coupling

Longer-term extensions may include:

```text
thermal
  ↕
magnetic
  ↕
fluid
  ↕
radiation
```

These should be added only when required by a physical problem. Avoid adding multiphysics complexity merely to expand feature count.

---

## 9. AI-Agent-Oriented Development

The project should continue to treat machine-readable project state as part of the architecture.

A preferred workflow is:

```text
literature / NIST / experimental data
              ↓
        research + citations
              ↓
    human-readable Markdown spec
              ↓
         human review
              ↓
        coding agent
              ↓
CSV / YAML / Python / tests
              ↓
      thermal-simulation
              ↓
      validated FEM result
```

The Markdown specification acts as an interface between scientific knowledge and software implementation.

The repository—not an individual AI conversation—should remain the source of truth for requirements, architecture, progress, assumptions, tests, and provenance.

---

## 10. Proposed Priority

### Now: ADR01 delivery

1. Keep the current Backward Euler solver as the trusted baseline.
2. Continue segmented time stepping and high-accuracy spot checks.
3. Add lightweight runtime profiling.
4. Finish physical validation and ADR01 deliverables.

### Next: numerical-method upgrade

1. Implement BDF2 as a selectable integrator.
2. Verify first- vs second-order temporal convergence.
3. Benchmark whether larger stable/accurate time steps reduce total runtime.
4. Profile PETSc linear/nonlinear solve cost.

### Later: automatic performance improvements

1. Adaptive time stepping.
2. PETSc Krylov/preconditioner tuning for larger meshes.
3. Material-expression optimization if profiling shows it matters.
4. MPI/scaling work when problem size justifies it.

### Future physics

1. Radiation where physically necessary.
2. Magnetic-field-dependent properties.
3. Explicit ADR/magnetocaloric terms.
4. Additional coupled physics only as required by applications.

---

## Guiding Principle

The framework should optimize for **scientific flexibility, numerical credibility, reproducibility, and agent compatibility**, not merely feature count or raw speed.

The intended progression is:

```text
make it correct
    ↓
make it verifiable
    ↓
measure the bottleneck
    ↓
make it faster
    ↓
make it more automatic
    ↓
extend the physics
```

Do not optimize an unmeasured bottleneck, and do not replace a simple verified method until the replacement has its own verification evidence.
