# ADR01 Architecture

## 1. Purpose

ADR01 is a simplified 3D transient thermal model of a single-stage ADR
assembly.

The initial baseline solves solid heat conduction only.

The first baseline intentionally excludes:

- magnetocaloric dynamics;
- electromagnetic simulation;
- radiation;
- convection;
- internal heat generation;
- non-ideal contact resistance.

These effects may be added later when required.

---

## 2. Governing Equation

For each volumetric solid:

$$
\rho(T)c_p(T)\frac{\partial T}{\partial t}
=
\nabla\cdot\left(k(T)\nabla T\right)
+
\dot q'''
$$

Initial baseline:

$$
\dot q''' = 0
$$

Heat flux:

$$
\mathbf q=-k(T)\nabla T
$$

---

## 3. Model Layers

ADR01 is separated into four conceptual layers:

    raw evidence
        ->
    requirements
        ->
    executable model
        ->
    results

Raw internal source files are not required to live in the tracked
repository.

---

## 4. Directory Structure

Expected ADR01 structure:

    run/01_ADR01/
    ├── AGENTS.md
    ├── arch.md
    ├── steps.md
    │
    ├── geometry-requirement/
    │   ├── README.md
    │   ├── assembly.yaml
    │   ├── connections.yaml
    │   └── components/
    │       └── <component-id>.yaml
    │
    ├── parameters-requirement/
    │   ├── README.md
    │   ├── boundaries.yaml
    │   ├── interfaces.yaml
    │   ├── components/
    │   │   └── <component-id>.yaml
    │   └── data/
    │       └── <case-local-property-data>
    │
    ├── geometry.py
    ├── case.yaml
    ├── main.py
    └── output/

Only create files when they become necessary.

---

## 5. Geometry Requirements

`geometry-requirement/` is the source of truth for physical geometry.

It answers:

- what components exist;
- what shape each component has;
- its dimensions;
- its position;
- its orientation;
- which components physically connect.

It does not contain thermal conductivity, heat capacity,
contact resistance, or boundary conditions.

---

## 6. Geometry Translation

`geometry-requirement/` deliberately remains a soft, human-readable requirement,
not a strict geometry DSL. ADR01 translates the approved placeholder cylinders
and box directly into its case-local `geometry.py` using the existing Gmsh Python
API. Requirement coordinates are in millimetres; the generated mesh uses metres
to remain compatible with the parent simulation workflow.

All solids are fragmented together to create shared, conformal interfaces for the
later perfect-contact baseline. Component IDs become dimension-3 physical-group
names and the 11 stable edge IDs become dimension-2 physical-group names on the
corresponding shared surfaces. No parent-level geometry abstraction is added.

---

## 7. Assembly

The current draft component inventory and placement are held in
`geometry-requirement/draft-geometry.yaml`. Splitting it into an assembly file and
per-component files is unnecessary for this first soft-requirement cycle.

---

## 8. Connections

`geometry-requirement/connections.yaml` defines physical connectivity.

A connection is a geometric edge.

Example concept:

    edge_id
    component_a
    surface_a
    component_b
    surface_b

The connection specification answers:

    WHO touches WHOM, and WHERE?

It does not define the thermal contact resistance.

The geometry builder verifies each declared edge against shared Gmsh surfaces and
fails on a missing edge, unintended component contact, or overlapping volumes.

Contact area should normally be calculated from generated geometry.

---

## 9. Thermal Component Parameters

`parameters-requirement/components/` defines bulk thermal properties.

Typical properties include:

$$
k(T)
$$

$$
c_p(T)
$$

$$
\rho(T)
$$

or constant approximations when explicitly approved.

Properties may be represented by:

- scalar;
- equation;
- table;
- cleaned local data file;
- existing compatible repository material source.

Each production parameter must preserve provenance.

---

## 10. Interfaces

`parameters-requirement/interfaces.yaml` assigns thermal physics to
geometric edges.

Supported conceptual interface models are:

### Perfect contact

$$
T_1=T_2
$$

with normal heat-flux continuity.

This is the default ADR01 baseline.

### Total thermal resistance

$$
\dot Q=\frac{T_1-T_2}{R_{\rm th}}
$$

with:

$$
R_{\rm th}\quad [\mathrm{K/W}]
$$

### Area-specific thermal resistance

$$
q''=\frac{T_1-T_2}{R''_{\rm th}}
$$

with:

$$
R''_{\rm th}\quad [\mathrm{m^2\,K/W}]
$$

and:

$$
R_{\rm th}=\frac{R''_{\rm th}}{A_c}
$$

### Conductance

$$
\dot Q=G(T_1-T_2)
$$

### Switchable conductance

$$
G=
\begin{cases}
G_{\rm on}, & \text{ON}\\
G_{\rm off}, & \text{OFF}
\end{cases}
$$

for a simplified heat-switch model.

A heat switch must not be represented simultaneously as both an
equivalent volumetric conductor and an independent conductance edge.

---

## 11. Boundary Conditions

Boundary conditions are stored under `parameters-requirement/`.

Initial baseline:

### Hot reservoir

$$
T_{\rm hot}=4~\mathrm{K}
$$

### Cold boundary

$$
T_{\rm cold}=1~\mathrm{K}
$$

### Other exposed surfaces

$$
-k\nabla T\cdot\mathbf n=0
$$

unless explicitly specified otherwise.

An ideal fixed-temperature reservoir may remain outside the solved
volumetric domain.

---

## 12. Heat Sources

The governing model allows conceptually:

$$
\dot q''' \neq 0
$$

but the first baseline uses:

$$
\dot q'''=0
$$

Future ADR requirements may include:

- sample heat dissipation;
- magnet heat loss;
- optical load;
- other deposited power.

Possible generic future forms include:

### Volumetric source

$$
\dot q''' \quad [\mathrm{W/m^3}]
$$

### Total power assigned to a volume

$$
P\quad[\mathrm W],
\qquad
\dot q'''=\frac{P}{V}
$$

### Surface heat flux

$$
q''\quad[\mathrm{W/m^2}]
$$

These are future framework extensions and must not block the first
baseline.

---

## 13. Material Data Policy

Case-local material data is allowed.

ADR01 does not require all material data to be promoted to root
`materials/`.

Root `materials/` should be searched for possible existing candidates,
but candidate reuse requires checking:

- exact material identity;
- source;
- valid temperature range;
- qualifiers;
- suitability for $1$–$4~\mathrm{K}$.

NIST or any other database is not automatically preferred over a
peer-reviewed paper or project-specific dataset.

The simulation must make parameter provenance visible and auditable.

---

## 14. Executable Model

Requirements are translated into:

    geometry.py
    case.yaml
    main.py

The exact implementation must reuse the parent repository's existing
interfaces.

`geometry.py` builds the geometry and mesh.

`case.yaml` contains solver-facing physical configuration.

`main.py` orchestrates execution and should remain small.

---

## 15. Visualization

Geometry verification occurs before solving.

Minimum initial requirement:

- interactive 3D rotation;
- zoom / pan;
- distinguishable components / regions;
- visibility of generated component placement and interfaces.

Existing tools such as Gmsh or ParaView are acceptable initially.

Future inspection may expose:

- selected component metadata;
- material properties;
- interface thermal model;
- contact resistance / conductance;
- temperature field;
- heat-flux field;
- time evolution.

Custom visualization belongs in the parent library only after ADR01
demonstrates a reusable need.

---

## 16. Baseline ADR01 Model

The first valid ADR01 solve uses:

    3D transient solid conduction
    fixed hot temperature = 4 K
    fixed cold temperature = 1 K
    other outer surfaces = adiabatic
    q''' = 0
    all ordinary interfaces = perfect contact

The purpose of this baseline is to validate:

- geometry;
- connectivity;
- region assignment;
- boundary assignment;
- bulk thermal behavior;
- heat-flow paths;
- numerical stability.

Non-ideal contact, heat switch states, and heat loads are later stages.
