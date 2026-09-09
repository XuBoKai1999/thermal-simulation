"""Disconnected 1D halves sharing a geometric contact location."""

import gmsh


LENGTH = 0.1
CONTACT_X = 0.05


def build_geometry(mesh_path, dx):
    gmsh.initialize()
    try:
        gmsh.model.add("steady_nonlinear_contact_bar")

        def half(start, stop):
            coordinates = [start + i * dx for i in range(round((stop - start) / dx) + 1)]
            points = [gmsh.model.geo.addPoint(x, 0, 0) for x in coordinates]
            return points, [
                gmsh.model.geo.addLine(a, b) for a, b in zip(points[:-1], points[1:])
            ]

        left_points, left_cells = half(0.0, CONTACT_X)
        right_points, right_cells = half(CONTACT_X, LENGTH)
        gmsh.model.geo.synchronize()
        entities = {
            "hot_half": (1, left_cells),
            "cold_half": (1, right_cells),
            "hot_end": (0, [left_points[0]]),
            "contact_left": (0, [left_points[-1]]),
            "contact_right": (0, [right_points[0]]),
            "cold_end": (0, [right_points[-1]]),
        }
        tags = {}
        for name, (dimension, members) in entities.items():
            tag = gmsh.model.addPhysicalGroup(dimension, members)
            gmsh.model.setPhysicalName(dimension, tag, name)
            tags[name] = {"dimension": dimension, "tag": tag}
        gmsh.model.mesh.generate(1)
        gmsh.write(str(mesh_path))
        return tags
    finally:
        gmsh.finalize()
