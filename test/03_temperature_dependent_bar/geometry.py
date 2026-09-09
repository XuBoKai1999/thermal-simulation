"""Geometry for the temperature-dependent material verification bar."""

import gmsh


LENGTH = 0.1
WIDTH = 0.01
MESH_SIZE = 0.005


def build_geometry(mesh_path):
    gmsh.initialize()
    try:
        gmsh.model.add("temperature_dependent_bar")
        gmsh.model.occ.addBox(0, 0, 0, LENGTH, WIDTH, WIDTH)
        gmsh.model.occ.synchronize()
        volumes = [tag for _, tag in gmsh.model.getEntities(3)]
        surfaces = gmsh.model.getEntities(2)

        def surfaces_at(x):
            tolerance = LENGTH * 1.0e-9
            return [
                tag for dim, tag in surfaces
                if abs(gmsh.model.occ.getCenterOfMass(dim, tag)[0] - x) < tolerance
            ]

        entities = {
            "bar": (3, volumes),
            "hot_end": (2, surfaces_at(0.0)),
            "cold_end": (2, surfaces_at(LENGTH)),
        }
        if any(not tags for _, tags in entities.values()):
            raise RuntimeError("A required semantic entity was not found")
        semantic_tags = {}
        for name, (dimension, tags) in entities.items():
            physical_tag = gmsh.model.addPhysicalGroup(dimension, tags)
            gmsh.model.setPhysicalName(dimension, physical_tag, name)
            semantic_tags[name] = {"dimension": dimension, "tag": physical_tag}
        gmsh.option.setNumber("Mesh.MeshSizeMin", MESH_SIZE)
        gmsh.option.setNumber("Mesh.MeshSizeMax", MESH_SIZE)
        gmsh.model.mesh.generate(3)
        gmsh.write(str(mesh_path))
        return semantic_tags
    finally:
        gmsh.finalize()
