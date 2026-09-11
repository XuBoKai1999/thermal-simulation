"""Build and validate the approved ADR01 placeholder inspection geometry."""

from argparse import ArgumentParser
import json
from pathlib import Path

import gmsh


MM = 1e-3
MESH_SIZE = 2.0 * MM

CYLINDERS_MM = {
    "hot_plate": ((0.0, 0.0), 96.0, 100.0, 25.4),
    "cylinder_1": ((-5.0, 0.0), 64.5, 96.0, 5.0),
    "heat_switch": ((-5.0, 0.0), 64.0, 64.5, 6.0),
    "cylinder_2": ((-5.0, 0.0), 54.0, 64.0, 5.0),
    "ggg": ((-5.0, 0.0), 34.0, 54.0, 9.0),
    "cylinder_3": ((-5.0, 0.0), 4.0, 34.0, 5.0),
    "cold_stage": ((0.0, 0.0), 0.0, 4.0, 25.4),
    "support_1": ((0.0, -9.0), 4.0, 96.0, 2.5),
    "support_2": ((0.0, 9.0), 4.0, 96.0, 2.5),
}

BOXES_MM = {
    "sample": (2.0, 8.0, -3.0, 3.0, 4.0, 10.0),
}

EDGES = {
    "edge_hot_cylinder_1": frozenset(("hot_plate", "cylinder_1")),
    "edge_cylinder_1_heat_switch": frozenset(("cylinder_1", "heat_switch")),
    "edge_heat_switch_cylinder_2": frozenset(("heat_switch", "cylinder_2")),
    "edge_cylinder_2_ggg": frozenset(("cylinder_2", "ggg")),
    "edge_ggg_cylinder_3": frozenset(("ggg", "cylinder_3")),
    "edge_cylinder_3_cold_stage": frozenset(("cylinder_3", "cold_stage")),
    "edge_cold_stage_sample": frozenset(("cold_stage", "sample")),
    "edge_hot_support_1": frozenset(("hot_plate", "support_1")),
    "edge_support_1_cold_stage": frozenset(("support_1", "cold_stage")),
    "edge_hot_support_2": frozenset(("hot_plate", "support_2")),
    "edge_support_2_cold_stage": frozenset(("support_2", "cold_stage")),
}


def _add_solids():
    solids = {}
    for name, ((x, y), z0, z1, diameter) in CYLINDERS_MM.items():
        solids[name] = gmsh.model.occ.addCylinder(
            x * MM, y * MM, z0 * MM, 0, 0, (z1 - z0) * MM, diameter * MM / 2
        )
    for name, (x0, x1, y0, y1, z0, z1) in BOXES_MM.items():
        solids[name] = gmsh.model.occ.addBox(
            x0 * MM, y0 * MM, z0 * MM,
            (x1 - x0) * MM, (y1 - y0) * MM, (z1 - z0) * MM,
        )
    return solids


def _shared_surfaces(volume_owner):
    contacts = {}
    for _, surface in gmsh.model.getEntities(2):
        adjacent, _ = gmsh.model.getAdjacencies(2, surface)
        owners = frozenset(volume_owner[int(tag)] for tag in adjacent)
        if len(owners) == 2:
            contacts.setdefault(owners, []).append(surface)
    return contacts


def build_geometry(mesh_path, mesh_size=MESH_SIZE):
    """Write a conformal tagged mesh and return parent-compatible tag metadata."""
    gmsh.initialize()
    try:
        gmsh.model.add("ADR01_placeholder_geometry")
        solids = _add_solids()
        names = list(solids)
        _, output_map = gmsh.model.occ.fragment(
            [(3, solids[names[0]])], [(3, solids[name]) for name in names[1:]]
        )
        gmsh.model.occ.synchronize()

        component_volumes = {
            name: [tag for dimension, tag in mapped if dimension == 3]
            for name, mapped in zip(names, output_map)
        }
        if any(len(tags) != 1 for tags in component_volumes.values()):
            raise RuntimeError(
                "Overlapping or split components: "
                + repr({k: v for k, v in component_volumes.items() if len(v) != 1})
            )
        volume_owner = {
            tag: name for name, tags in component_volumes.items() for tag in tags
        }
        contacts = _shared_surfaces(volume_owner)
        expected = set(EDGES.values())
        if set(contacts) != expected:
            missing = sorted(expected - set(contacts), key=sorted)
            extra = sorted(set(contacts) - expected, key=sorted)
            raise RuntimeError(f"Contact mismatch; missing={missing}, extra={extra}")

        tags = {}
        for name, members in component_volumes.items():
            physical = gmsh.model.addPhysicalGroup(3, members)
            gmsh.model.setPhysicalName(3, physical, name)
            tags[name] = {"dimension": 3, "tag": physical}
        for edge_id, pair in EDGES.items():
            physical = gmsh.model.addPhysicalGroup(2, contacts[pair])
            gmsh.model.setPhysicalName(2, physical, edge_id)
            area = sum(gmsh.model.occ.getMass(2, surface) for surface in contacts[pair])
            tags[edge_id] = {"dimension": 2, "tag": physical, "area_m2": area}

        gmsh.option.setNumber("Mesh.MeshSizeMin", min(mesh_size, 0.25 * MM))
        gmsh.option.setNumber("Mesh.MeshSizeMax", mesh_size)
        gmsh.model.mesh.generate(3)
        mesh_path = Path(mesh_path)
        mesh_path.parent.mkdir(parents=True, exist_ok=True)
        gmsh.write(str(mesh_path))
        return tags
    finally:
        gmsh.finalize()


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--mesh", type=Path, default=Path(__file__).parent / "build/mesh.msh")
    parser.add_argument("--view", action="store_true", help="open the generated mesh in Gmsh")
    args = parser.parse_args()
    tags = build_geometry(args.mesh)
    tags_path = args.mesh.with_name("tags.json")
    tags_path.write_text(json.dumps(tags, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"validated {len(CYLINDERS_MM) + len(BOXES_MM)} components and {len(EDGES)} contacts")
    for edge_id in EDGES:
        print(f"{edge_id}: {tags[edge_id]['area_m2'] / MM**2:.6f} mm^2")
    print(f"interactive mesh: {args.mesh.resolve()}")
    if args.view:
        gmsh.initialize()
        try:
            gmsh.open(str(args.mesh))
            gmsh.fltk.run()
        finally:
            gmsh.finalize()


if __name__ == "__main__":
    main()
