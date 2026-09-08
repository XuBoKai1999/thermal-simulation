"""Geometry definition for the steady-bar verification case."""

import gmsh


LENGTH = 0.1
WIDTH = 0.01
MESH_SIZE = 0.005


def build_geometry(mesh_path):
    gmsh.initialize()
    try:
        gmsh.model.add("steady_bar")
        left = gmsh.model.occ.addBox(0, 0, 0, LENGTH / 2, WIDTH, WIDTH)
        right = gmsh.model.occ.addBox(
            LENGTH / 2, 0, 0, LENGTH / 2, WIDTH, WIDTH
        )
        gmsh.model.occ.fragment([(3, left)], [(3, right)])
        gmsh.model.occ.synchronize()

        volumes = [tag for _, tag in gmsh.model.getEntities(3)]
        surfaces = gmsh.model.getEntities(2)

        def surfaces_at(x):
            tolerance = LENGTH * 1.0e-9
            return [
                tag
                for dim, tag in surfaces
                if abs(gmsh.model.occ.getCenterOfMass(dim, tag)[0] - x) < tolerance
            ]

        semantic_entities = {
            "bar": (3, volumes),
            "hot_end": (2, surfaces_at(0.0)),
            "cold_end": (2, surfaces_at(LENGTH)),
            "heatflow_section": (2, surfaces_at(LENGTH / 2)),
        }
        if any(not entities for _, entities in semantic_entities.values()):
            raise RuntimeError("A required semantic entity was not found")

        tags = {}
        for name, (dimension, entities) in semantic_entities.items():
            physical_tag = gmsh.model.addPhysicalGroup(dimension, entities)
            gmsh.model.setPhysicalName(dimension, physical_tag, name)
            tags[name] = {"dimension": dimension, "tag": physical_tag}
            print(name)

        gmsh.option.setNumber("Mesh.MeshSizeMin", MESH_SIZE)
        gmsh.option.setNumber("Mesh.MeshSizeMax", MESH_SIZE)
        gmsh.model.mesh.generate(3)
        gmsh.write(str(mesh_path))
        return tags
    finally:
        gmsh.finalize()
