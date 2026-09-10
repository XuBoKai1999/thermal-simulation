"""Two conformally connected cuboids with general semantic surface names."""

import gmsh


LENGTH = 0.06
INTERFACE = 0.03
WIDTH = 0.02
HEIGHT = 0.01


def build_geometry(mesh_path, mesh_size=0.01):
    gmsh.initialize()
    try:
        gmsh.model.add("general_3d_transient")
        left = gmsh.model.occ.addBox(0, 0, 0, INTERFACE, WIDTH, HEIGHT)
        right = gmsh.model.occ.addBox(
            INTERFACE, 0, 0, LENGTH - INTERFACE, WIDTH, HEIGHT
        )
        gmsh.model.occ.fragment([(3, left)], [(3, right)])
        gmsh.model.occ.synchronize()
        volumes = gmsh.model.getEntities(3)
        regions = {"heated_block": [], "passive_block": []}
        for dimension, tag in volumes:
            x = gmsh.model.occ.getCenterOfMass(dimension, tag)[0]
            regions["heated_block" if x < INTERFACE else "passive_block"].append(tag)
        surfaces = gmsh.model.getEntities(2)

        def at(axis, coordinate):
            return [
                tag for dimension, tag in surfaces
                if abs(gmsh.model.occ.getCenterOfMass(dimension, tag)[axis]
                       - coordinate) < 1e-10
            ]

        entities = {
            **{name: (3, tags) for name, tags in regions.items()},
            "heater_face": (2, at(0, 0.0)),
            "monitor_face": (2, at(0, LENGTH)),
            "side_probe": (2, at(1, 0.0)),
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
