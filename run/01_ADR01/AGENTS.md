# ADR01 Agent Instructions

## 1. Scope

This directory is one simulation case inside the parent
`thermal-simulation` repository.

ADR01 is NOT an independent simulation framework.

Before modifying implementation:

1. inspect the repository-level `AGENTS.md`;
2. inspect the repository architecture and manuals;
3. inspect existing geometry, material, solver, output, and test interfaces;
4. reuse existing parent-repository capabilities whenever possible.

Do not create a second solver, mesh framework, material framework,
output system, or duplicated utility layer inside ADR01.

Do not create a nested Git repository.

---

## 2. Step 0 Gate

`steps.md` Step 0 is a human design stage.

Do NOT proceed to implementation until Step 0 is explicitly marked:

    STATUS: COMPLETE

If Step 0 is not complete, only report missing decisions.
Do not guess or silently choose them.

---

## 3. Sources of Truth

ADR01 has two primary requirement layers:

    geometry-requirement/
    parameters-requirement/

They describe the intended physical model.

Generated implementation such as:

    geometry.py
    case.yaml
    main.py

must be derived from those requirements.

Generated implementation must not silently introduce geometry,
parameters, interfaces, boundary conditions, or physical assumptions
that are absent from the requirements.

---

## 4. Unknown Means Unknown

Never convert unknown information into an estimate without explicit approval.

Use:

    TBD

for missing dimensions, materials, thermal properties,
contact properties, loads, or boundary data.

Do not infer dimensions by measuring a schematic image.

Do not infer a contact resistance merely from the names of two materials.

Do not extrapolate a material property outside its supported temperature
range unless explicitly approved.

---

## 5. Geometry Rules

Geometry requirements describe actual 3D solids and their placement.

The geometry representation must use a repository-defined declarative
geometry contract established in Step 0.

The contract must define, at minimum:

- coordinate system;
- units;
- primitive geometry representation;
- position and orientation;
- semantic surfaces;
- component IDs;
- connection IDs.

Avoid ambiguous directional words such as:

    top
    bottom
    left
    right

unless they are merely human-readable labels.

Machine-readable geometry must use explicit coordinates, vectors,
primitive-local surface names, or equivalent unambiguous definitions.

Geometry must be reproducible from the requirement files alone.

---

## 6. Node and Edge Meaning

A volumetric component is a node of the physical model.

Examples:

- GGG refrigerant;
- thermal bus;
- cold stage;
- support;
- sample;
- magnet, if modeled as a solid.

A physical connection between two components is an edge.

Geometry defines:

- which components connect;
- which surfaces participate;
- the actual geometric contact region.

Thermal parameters define the physics of that edge.

Possible interface models include:

- perfect contact;
- total thermal resistance, K/W;
- area-specific thermal resistance, m² K/W;
- thermal conductance, W/K;
- switchable thermal conductance.

Do not confuse bulk material resistance with contact resistance.

Bulk conduction is solved by the PDE from geometry and $k(T)$.

---

## 7. Contact Area

Contact area should normally be derived from the actual geometry.

Do not duplicate contact area as an independent manually-entered number
unless there is a documented reason.

If a manual effective contact area is required, clearly mark it as an
assumption and preserve its source or rationale.

---

## 8. Heat Switch

A heat switch may be represented either as:

1. a volumetric solid with an equivalent thermal property; or
2. a thermal connection with conductance $G_{\rm on}$ / $G_{\rm off}$.

Do not use both representations simultaneously.

The chosen representation must be explicitly stated in the requirements.

---

## 9. Material and Thermal Parameters

Parameters used in a production simulation must preserve provenance.

For every externally sourced physical property, record when applicable:

- material identity and grade;
- property name;
- units;
- valid temperature range;
- source citation;
- DOI or URL;
- page / table / figure / equation;
- experimental qualifiers such as RRR, purity, orientation,
  treatment, pressure, or surface condition;
- cleaning, digitization, fitting, interpolation, or conversion method.

Root-level `materials/` is a candidate data source, not an authority.

Before reusing a root material dataset:

1. inspect its provenance;
2. inspect its valid temperature range;
3. inspect material qualifiers;
4. report whether it is suitable for ADR01.

Do not automatically select a NIST dataset merely because one exists.

ADR-local datasets may remain inside ADR01 if they are case-specific.
Promote data to root `materials/` only when reuse is justified.

---

## 10. Temperature-Range Rule

The intended ADR range is approximately $1~\mathrm{K}$ to $4~\mathrm{K}$.

A temperature-dependent property must not be used outside its stated
valid range without explicit approval.

If coverage is insufficient, report:

    DATA GAP

Do not silently extrapolate.

---

## 11. Boundary Conditions

Boundary conditions belong to the physical parameter specification.

Examples include:

- fixed temperature;
- adiabatic boundary;
- prescribed heat flux, if later implemented.

For the first baseline model:

- the hot reservoir is fixed at $4~\mathrm{K}$;
- the cold boundary is fixed at $1~\mathrm{K}$;
- unspecified external surfaces are adiabatic;
- volumetric heat generation is zero;
- contact interfaces are perfect unless otherwise specified.

A fixed-temperature ideal reservoir does not require bulk material
properties if it is not represented as a volumetric simulation domain.

---

## 12. Heat Sources

The first ADR baseline uses:

$$
\dot q''' = 0
$$

Do not implement heat-source support merely to run the first baseline.

However, ADR01 may later require generic source support for:

- sample heat load;
- magnet heat loss;
- other deposited power.

Before implementing such support, audit the parent framework first.

Prefer generic reusable source models rather than ADR-specific hacks.

Potential future representations include:

- volumetric heat generation, W/m³;
- total deposited power, W;
- surface heat flux, W/m².

Implementation must be driven by an actual ADR requirement.

---

## 13. Visualization Gate

Geometry must be visually verified before physics solving.

Required workflow:

    requirements
        ->
    generated geometry / mesh
        ->
    interactive 3D inspection
        ->
    human approval
        ->
    thermal solve

The first implementation may use Gmsh / ParaView or another existing
interactive 3D viewer.

Do not build a custom viewer before the geometry and simulation workflow
demonstrates that one is needed.

Desired later inspection capability may include:

- rotate / zoom / pan;
- component picking;
- component ID and material display;
- interface information;
- contact model display;
- temperature field;
- heat-flux field.

Reusable visualization capability should only be promoted to the parent
`lib/` after proving its usefulness in ADR01.

---

## 14. Parent-Library Changes

ADR01 may reveal missing generic functionality.

Do not immediately modify `lib/`.

First demonstrate that the capability is:

1. required by ADR01;
2. physically and numerically well defined;
3. generic beyond one hard-coded ADR component.

Only then implement it in the parent framework with tests and
documentation.

---

## 15. Verification

Every newly introduced generic capability must have a minimal validation
case independent of the full ADR assembly whenever practical.

Examples:

- declarative cylinder geometry;
- semantic surface generation;
- interface conductance;
- volumetric heat source;
- prescribed surface heat flux.

Do not use the full ADR model as the only test of a new framework feature.

---

## 16. Documentation

When implementation changes the real workflow, update the relevant
repository documentation.

Do not create redundant ADR documentation if existing files can be
updated instead.

Keep ADR01 documentation focused on:

- requirements;
- assumptions;
- unresolved data;
- model state;
- verification state.
