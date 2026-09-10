"""Two-region 3D composite rod for transient material regression."""

import gmsh


LENGTH = 0.1
INTERFACE = 0.05
WIDTH = 0.01


def build_geometry(mesh_path, mesh_size):
    gmsh.initialize()
    try:
        gmsh.model.add("multi_region_transient")
        left = gmsh.model.occ.addBox(0, 0, 0, INTERFACE, WIDTH, WIDTH)
        right = gmsh.model.occ.addBox(
            INTERFACE, 0, 0, LENGTH - INTERFACE, WIDTH, WIDTH
        )
        gmsh.model.occ.fragment([(3, left)], [(3, right)])
        gmsh.model.occ.synchronize()
        volumes = gmsh.model.getEntities(3)
        by_region = {"material_a_region": [], "material_b_region": []}
        for dimension, tag in volumes:
            x = gmsh.model.occ.getCenterOfMass(dimension, tag)[0]
            key = "material_a_region" if x < INTERFACE else "material_b_region"
            by_region[key].append(tag)
        surfaces = gmsh.model.getEntities(2)

        def surfaces_at(x):
            return [
                tag for dimension, tag in surfaces
                if abs(gmsh.model.occ.getCenterOfMass(dimension, tag)[0] - x) < 1e-10
            ]

        entities = {
            **{name: (3, tags) for name, tags in by_region.items()},
            "hot_end": (2, surfaces_at(0.0)),
            "cold_end": (2, surfaces_at(LENGTH)),
        }
        tags = {}
        for name, (dimension, members) in entities.items():
            if not members:
                raise RuntimeError(f"Missing semantic entity {name}")
            physical_tag = gmsh.model.addPhysicalGroup(dimension, members)
            gmsh.model.setPhysicalName(dimension, physical_tag, name)
            tags[name] = {"dimension": dimension, "tag": physical_tag}
        gmsh.option.setNumber("Mesh.MeshSizeMin", mesh_size)
        gmsh.option.setNumber("Mesh.MeshSizeMax", mesh_size)
        gmsh.model.mesh.generate(3)
        gmsh.write(str(mesh_path))
        return tags
    finally:
        gmsh.finalize()
