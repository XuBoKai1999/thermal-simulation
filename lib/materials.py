"""Minimal contract helpers for case-local temperature-dependent materials."""

import numpy as np
from dolfinx import fem


def validate(material, names):
    missing = [name for name in names if not callable(getattr(material, name, None))]
    if missing:
        raise ValueError(f"Local material must define callable: {', '.join(missing)}")


def conductivity_field(mesh_data, case_data, semantic_tags):
    domain = mesh_data.mesh
    space = fem.functionspace(domain, ("DG", 0))
    conductivity = fem.Function(space)
    conductivity.x.array[:] = np.nan
    contacts = {
        contact["region"]: contact["thickness_m"] / contact["resistance_m2K_W"]
        for contact in case_data.get("contacts", {}).values()
    }
    for name, region in case_data["regions"].items():
        value = contacts.get(name, region.get("k"))
        tag = semantic_tags[name]["tag"]
        for cell in mesh_data.cell_tags.find(tag):
            conductivity.x.array[space.dofmap.cell_dofs(cell)[0]] = value
    owned = space.dofmap.index_map.size_local
    if not np.isfinite(conductivity.x.array[:owned]).all():
        raise ValueError("Every mesh cell must belong to a configured material region")
    conductivity.x.scatter_forward()
    return conductivity
