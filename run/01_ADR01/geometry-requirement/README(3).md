# ADR01 Geometry Requirement — Draft 0

## Status

**DRAFT / PLACEHOLDER GEOMETRY**

This geometry is only for the first Codex interpretation → 3D build → visual inspection cycle.

The dimensions in this draft are **not engineering dimensions** and must not be presented as measured ADR hardware dimensions.

Known scale information currently used:

- nominal disk diameter: about **1 inch = 25.4 mm**;
- total assembly height: about **100 mm**.

The source schematic is not drawn to a single reliable scale. Its apparent horizontal and vertical proportions cannot simultaneously satisfy both known dimensions. Therefore the schematic is used mainly for:

- component order;
- connectivity;
- rough relative size;
- rough placement.

The numerical dimensions below are deliberately chosen placeholders that fit inside a roughly
`25.4 mm × 25.4 mm × 100 mm` envelope.

---

## 1. Modeling Intent

The first geometry contains **10 named geometry components**:

1. `hot_plate`
2. `cylinder_1`
3. `heat_switch`
4. `cylinder_2`
5. `ggg`
6. `cylinder_3`
7. `cold_stage`
8. `sample`
9. `support_1`
10. `support_2`

The superconducting magnet is intentionally omitted from this baseline geometry.

The hot plate is included as geometry so that the assembly can be inspected visually and the
central path / supports have a clear attachment location. In the first thermal model it may be
treated as an ideal fixed-$4\,\mathrm{K}$ reservoir rather than as an independently solved thermal
body.

---

## 2. Coordinate Convention

Use a right-handed Cartesian coordinate system.

- units: `mm`
- `+z`: from cold stage toward hot plate
- cold-stage bottom: approximately `z = 0 mm`
- hot-plate top: approximately `z = 100 mm`
- plate centers: `x = 0`, `y = 0`
- main ADR thermal path: laterally offset near `x = -5 mm`, `y = 0`
- dummy sample: on the opposite side near `x = +5 mm`, `y = 0`

This convention is for the draft only. Codex may translate the requirement into whatever geometry
API the parent repository already uses.

The five components `cylinder_1`, `heat_switch`, `cylinder_2`, `ggg`, and `cylinder_3` form one
coaxial ADR chain. They must share one `center_xy` and move together whenever the placeholder chain
position is revised. The chain is intentionally not coaxial with the hot and cold plates.

---

## 3. Important Design Rule: Region ↔ Parameter Mapping

Every geometry component has a stable component ID.

That ID is the key used later by the thermal-parameter requirement.

Conceptually:

```text
geometry-requirement:
    component id = ggg

            ↓ same ID

parameters-requirement:
    component id = ggg
    k(T)
    c_p(T)
    density(T) or density
    provenance / citation
    valid temperature range
```

For ordinary solid regions, the later parameter search should target thermal-property data valid
over **1 K to 4 K**.

The same rule applies to every region.

Exceptions are allowed when the physics itself is different:

- `hot_plate`: primarily a fixed-temperature boundary/reservoir in the baseline;
- `heat_switch`: may ultimately be represented by $G_{\rm on}/G_{\rm off}$ or an equivalent
  resistance/conductance rather than by an intrinsic material $k(T)$.

Do not force an inappropriate `$k,c_p,\rho$` model onto a component whose thermal model is
explicitly an interface/conductance model.

---

## 4. Edge ↔ Interface Mapping

Every physical connection has a stable `edge_id` in `connections.yaml`.

Later, the thermal interface requirement must refer to the same `edge_id`.

Conceptually:

```text
geometry edge
    edge_c3_cold_stage

            ↓ same ID

parameter/interface definition
    edge_c3_cold_stage
    perfect contact / R_th / R''_th / G / switchable G
    source / citation / assumption
```

The first baseline uses **perfect contact** for ordinary contacts.

Non-ideal contact resistance is a later stage.

---

## 5. Heat-Switch Representation

For this first geometry-only draft, `heat_switch` is drawn as a very thin cylindrical disk so the
topology is visually obvious.

This is only a geometric placeholder.

Later thermal modeling may replace it with an equivalent connection using:

- $G_{\rm on}$;
- $G_{\rm off}$;
- or an equivalent thermal resistance.

Do not simultaneously count both a bulk heat-switch resistance and an additional edge resistance.

---

## 6. Codex Task for This Draft

Codex should:

1. inspect the parent `thermal-simulation` repository first;
2. read the existing root-level `AGENTS.md`, architecture, manuals, geometry code, tests, and
   output conventions;
3. interpret `draft-geometry.yaml` and `connections.yaml`;
4. use the existing geometry/Gmsh workflow where possible;
5. generate a first 3D assembly;
6. generate mesh/region tags only as needed for inspection;
7. provide an interactive 3D view using the existing toolchain, preferably Gmsh or ParaView;
8. preserve all component IDs and edge IDs;
9. report every interpretation or assumption it had to make;
10. report missing framework capability before adding broad new abstractions.

Codex is free to translate this soft requirement format into the representation already accepted by
the repository.

**Do not build a new geometry DSL just to parse this draft.**

If a missing generic capability is actually required, implement the smallest useful version and
validate it separately.

---

## 7. Required Geometry Check

Before thermal solving, visually check at minimum:

- the total assembly is recognizable;
- the main central chain is continuous;
- `cylinder_1 → heat_switch → cylinder_2 → ggg → cylinder_3 → cold_stage`;
- both supports connect the hot-plate level to the cold stage;
- the sample sits on the cold stage without intersecting the central thermal bus;
- no unintended overlaps or gaps exist at intended contacts;
- all ten component IDs are identifiable;
- all declared edges correspond to real geometric contacts.

This geometry is expected to be revised after the first visual inspection.
