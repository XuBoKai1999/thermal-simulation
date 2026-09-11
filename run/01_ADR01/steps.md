# ADR01 Development Steps

## Step 0 — Freeze the Modeling Contract

STATUS: COMPLETE

Human-approved on 2026-09-11. The decisions below are frozen for the first
geometry and inspection cycle; all dimensions remain visualization placeholders.

This step was completed by explicit human approval before geometry implementation.

### 0.1 Freeze baseline physics

Baseline model:

$$
\rho c_p\frac{\partial T}{\partial t}
=
\nabla\cdot(k\nabla T)
$$

with:

$$
\dot q'''=0
$$

Initial simplifications:

- 3D solid conduction only;
- transient;
- hot reservoir fixed at $4~\mathrm{K}$;
- cold boundary fixed at $1~\mathrm{K}$;
- other external surfaces adiabatic;
- ordinary interfaces perfect;
- no radiation;
- no convection;
- no magnetocaloric dynamics;
- no electromagnetic solve.

### 0.2 Freeze component inventory

Identify which physical components are represented as volumetric solids.

At minimum review:

- GGG / magnetic refrigerant;
- Cu thermal bus;
- cold stage;
- low-k supports;
- dummy sample;
- superconducting magnet;
- heat switch;
- any structural plate required for a real heat path.

Decide whether the $4~\mathrm{K}$ hot plate and $1~\mathrm{K}$ cold reservoir are:

- solved solids; or
- ideal fixed-temperature reservoirs outside the solved domain.

Approved inventory: `hot_plate`, `cylinder_1`, `heat_switch`, `cylinder_2`, `ggg`,
`cylinder_3`, `cold_stage`, `sample`, `support_1`, and `support_2`. The
superconducting magnet is omitted. `hot_plate` remains visible geometry and later
acts as the ideal fixed-$4~\mathrm{K}$ reservoir/boundary.

### 0.3 Freeze geometry contract

Define the exact declarative schema used by
`geometry-requirement/`.

Freeze:

- units;
- coordinate system;
- primitive definitions;
- position representation;
- orientation representation;
- semantic surface naming;
- assembly rules;
- connection representation.

No strict geometry DSL is frozen or introduced. `geometry-requirement/` remains a
soft, human-readable source of truth translated into the parent repository's
existing case-local Gmsh workflow. The current draft uses only cylinders and one
box. Its numeric dimensions are approved solely as visualization placeholders;
no physical dimension may be inferred from the schematic.

### 0.4 Freeze edge contract

Define the exact relation between:

    geometry connection
        ↔
    thermal interface

Each geometric connection requires a stable `edge_id`.

Thermal interface data references that `edge_id`.

For the first baseline every ordinary edge uses:

    perfect contact

The schema must reserve later support for:

- K/W resistance;
- m² K/W area-specific resistance;
- W/K conductance;
- switchable conductance.

The 11 `edge_id` values in `geometry-requirement/connections.yaml` are accepted as
stable identifiers. Geometry generation must verify their real contacts and
report gaps, overlaps, or extra contacts without silently changing the draft.
Ordinary interfaces are later modeled as perfect contact. `heat_switch` is only a
thin geometry placeholder; a later model may instead use $G_{on}/G_{off}$ or an
equivalent resistance/conductance, without double counting.

### 0.5 Freeze parameter provenance schema

Define how every real physical parameter records:

- value / table / equation;
- units;
- valid temperature range;
- citation;
- DOI / URL;
- page / table / figure / equation;
- material qualifiers;
- data-processing history.

Do not begin material-data collection before this schema is fixed.

Approved mapping: each geometry component ID maps to the identical later
parameter component ID. Production data must preserve value representation,
units, citation/provenance, validity range, processing history, and material
qualifiers. Ordinary solids later require $k(T)$, $c_p(T)$, and density over
$1$--$4~\mathrm{K}$. Material research is outside the geometry task.

### 0.6 Freeze visualization gate

Agree that generated geometry must undergo interactive 3D inspection
before the first thermal solve.

Define the minimum geometry inspection output and approval procedure.

Approved gate: generate a tagged 3D geometry/mesh that Gmsh or ParaView can open
interactively for rotation, zoom, pan, region identification, and interface
inspection. Record automated connectivity checks and assumptions. Human geometry
approval is mandatory before any thermal solve.

### Step 0 completion criteria

Step 0 is complete only when:

- the baseline PDE and simplifications are agreed;
- component inventory is agreed;
- the declarative geometry schema is unambiguous;
- node / edge IDs are unambiguous;
- parameter provenance format is agreed;
- the geometry inspection gate is agreed.

Only then change:

    STATUS: INCOMPLETE

to:

    STATUS: COMPLETE

---

## Step 1 — Audit Existing Parent Capabilities

STATUS: COMPLETE

The existing case-local Gmsh `build_geometry(mesh_path)` workflow, OCC fragment,
physical groups, and `.msh` inspection path cover the draft without parent changes.

Codex starts here only after Step 0 is complete.

Inspect the parent repository and determine:

- what geometry functionality already exists;
- what material formats already exist;
- what BCs already exist;
- what transient solver features already exist;
- what visualization outputs already exist;
- what can be reused unchanged.

Produce a short gap report.

Do not modify code yet unless required to demonstrate a trivial existing
capability.

---

## Step 2 — Implement the Minimal Geometry Contract

STATUS: COMPLETE

Implemented as a direct soft-requirement translation in `geometry.py`; no DSL or
generic geometry helper was introduced.

Implement only the Step 0 geometry contract needed by ADR01.

Prefer reusable parent-level geometry capability if the feature is truly
generic.

Do not build a broad CAD DSL.

Add minimal independent tests for each newly introduced geometry primitive
or semantic-surface rule.

---

## Step 3 — Populate Geometry Requirements

STATUS: COMPLETE FOR DRAFT 0

Draft 0 remains in `draft-geometry.yaml` and `connections.yaml`. The proposed
assembly/per-component split was not created because it adds no value yet.

Create:

    geometry-requirement/

Populate component geometry using only known information.

Unknown values remain:

    TBD

Do not estimate dimensions from schematic drawings.

Populate:

    assembly.yaml
    connections.yaml
    components/*.yaml

---

## Step 4 — Generate and Inspect the 3D Geometry

STATUS: AWAITING HUMAN VISUAL APPROVAL

The first mesh is generated and automated component/contact/coherence checks pass.
Open `build/mesh.msh` interactively in Gmsh and record human approval before Step 5
or any thermal solve.

Generate the ADR assembly and mesh.

Provide interactive 3D inspection.

Verify:

- component placement;
- orientation;
- dimensions;
- physical connectivity;
- semantic surfaces;
- region tags;
- boundary tags;
- contact surfaces.

Do not run thermal simulation until human approval is obtained.

---

## Step 5 — Populate Baseline Thermal Parameters

Create:

    parameters-requirement/

For the first smoke run, explicitly documented placeholder constants may
be used only when their purpose is numerical / structural verification.

Do not present placeholder properties as physical ADR results.

For real baseline material data, collect:

$$
k(T),\qquad c_p(T),\qquad \rho
$$

with provenance and valid temperature range.

Check root `materials/` for candidates, but do not automatically select
them.

---

## Step 6 — Run the Zero-Source Perfect-Contact Baseline

Run:

    fixed hot T = 4 K
    fixed cold T = 1 K
    other exposed surfaces = adiabatic
    q''' = 0
    interfaces = perfect contact

Inspect:

- $T(\mathbf x,t)$;
- $\mathbf q(\mathbf x,t)$;
- major thermal paths;
- region temperatures;
- heat flow into the fixed-temperature boundaries.

Perform basic mesh and timestep convergence checks.

This is the first physically interpretable ADR01 baseline.

---

## Step 7 — Replace Placeholder Material Data

Research and clean case-appropriate low-temperature data.

Priority is provenance and validity in the actual ADR temperature range,
not source prestige.

Possible sources include:

- peer-reviewed papers;
- NIST;
- manufacturer cryogenic data;
- other traceable technical sources.

For every selected dataset:

- preserve citation;
- preserve original validity range;
- preserve material qualifiers;
- record cleaning / fitting / interpolation.

Re-run convergence if strongly nonlinear properties change numerical
behavior.

---

## Step 8 — Introduce Non-Ideal Interfaces

Only after the perfect-contact baseline is stable.

For selected edges, research or estimate physically defensible interface
models.

Possible models:

- total contact resistance;
- area-specific contact resistance;
- conductance.

Contact resistance may depend on:

- clamping force;
- bolt preload;
- surface finish;
- oxide;
- plating;
- real contact area;
- temperature.

Unknown contact physics must remain explicit assumptions.

Perform sensitivity studies when a unique experimental value is not
available.

---

## Step 9 — Implement Heat-Switch Behavior

Represent the heat switch using one approved model only.

Possible simplified model:

$$
G=G_{\rm on}
$$

or

$$
G=G_{\rm off}
$$

depending on switch state.

Verify ON and OFF cases separately.

Do not double-count switch resistance through both a bulk equivalent
solid and an independent edge conductance.

---

## Step 10 — Add Generic Heat-Source Support When Needed

This step is not required for the first baseline.

Audit parent-framework support first.

If absent and required by ADR analysis, implement generic support for
one or more of:

### Volumetric heating

$$
\dot q''' \quad [\mathrm{W/m^3}]
$$

### Total deposited power

$$
P\quad[\mathrm W]
$$

assigned to a region, with conversion to volumetric generation when
appropriate.

### Surface heat flux

$$
q''\quad[\mathrm{W/m^2}]
$$

Potential ADR uses:

- dummy sample heat load;
- magnet heat loss;
- optical heating;
- electronic dissipation.

Add an independent validation test before using the capability in the
full ADR model.

---

## Step 11 — Extended ADR Studies

After the preceding model is stable, consider only if required:

- heat-load-driven cold-stage temperature;
- contact-resistance sensitivity;
- heat-switch switching sequence;
- time-dependent heat sources;
- radiation;
- optical / DC / RF thermal loads;
- magnetocaloric refrigerator dynamics;
- temperature- and field-dependent GGG properties.

These are extensions, not prerequisites for the first ADR baseline.
