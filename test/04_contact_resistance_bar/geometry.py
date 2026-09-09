"""Three-region bar with a mesh-resolved thin contact layer."""

import gmsh


LENGTH = 0.1
WIDTH = 0.01
CONTACT_THICKNESS = 0.001
LEFT_LENGTH = (LENGTH - CONTACT_THICKNESS) / 2
RIGHT_START = LEFT_LENGTH + CONTACT_THICKNESS
MESH_SIZE = 0.0025


def build_geometry(mesh_path):
    gmsh.initialize()
    try:
        gmsh.model.add("contact_resistance_bar")
        boxes = [
            gmsh.model.occ.addBox(0, 0, 0, LEFT_LENGTH, WIDTH, WIDTH),
            gmsh.model.occ.addBox(
                LEFT_LENGTH, 0, 0, CONTACT_THICKNESS, WIDTH, WIDTH
            ),
            gmsh.model.occ.addBox(
                RIGHT_START, 0, 0, LENGTH - RIGHT_START, WIDTH, WIDTH
            ),
        ]
        gmsh.model.occ.fragment([(3, boxes[0])], [(3, tag) for tag in boxes[1:]])
        gmsh.model.occ.synchronize()
        volumes = gmsh.model.getEntities(3)
        volume_by_position = {}
        for dimension, tag in volumes:
            x = gmsh.model.occ.getCenterOfMass(dimension, tag)[0]
            name = "left" if x < LEFT_LENGTH else (
                "right" if x > RIGHT_START else "contact_layer"
            )
            volume_by_position[name] = [tag]
        surfaces = gmsh.model.getEntities(2)

        def surfaces_at(x):
            tolerance = LENGTH * 1.0e-9
            return [
                tag for dimension, tag in surfaces
                if abs(gmsh.model.occ.getCenterOfMass(dimension, tag)[0] - x)
                < tolerance
            ]

        entities = {
            **{name: (3, tags) for name, tags in volume_by_position.items()},
            "hot_end": (2, surfaces_at(0.0)),
            "cold_end": (2, surfaces_at(LENGTH)),
        }
        if set(volume_by_position) != {"left", "contact_layer", "right"}:
            raise RuntimeError("Could not identify all three volume regions")
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
