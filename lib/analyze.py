"""Derive physical quantities from a thermal solution."""

import numpy as np
from dolfinx import fem
from mpi4py import MPI
from petsc4py import PETSc
import ufl


def analyze(temperature, mesh_data, case_data, semantic_tags, material=None):
    domain = mesh_data.mesh
    if material is None:
        from .materials import conductivity_field
        properties = case_data["_region_properties"]
        temperature_dependent = [
            values["k"] for values in properties.values()
            if values is not None and not values["k"].is_constant
        ]
        conductivity = (
            temperature_dependent[0].evaluate(temperature)
            if temperature_dependent
            else conductivity_field(mesh_data, case_data, semantic_tags)
        )
    else:
        conductivity = material.k(temperature)
    if temperature.function_space.element.basix_element.degree == 0:
        heat_flux = fem.Constant(
            domain, np.zeros(domain.geometry.dim, dtype=PETSc.ScalarType)
        )
    else:
        heat_flux = -conductivity * ufl.grad(temperature)

    def global_integral(expression):
        local = fem.assemble_scalar(fem.form(expression))
        return domain.comm.allreduce(local, op=MPI.SUM)

    volume = global_integral(1 * ufl.dx(domain=domain))
    average_flux = [
        global_integral(heat_flux[i] * ufl.dx(domain=domain)) / volume
        for i in range(domain.geometry.dim)
    ]

    ds = ufl.Measure("ds", domain=domain, subdomain_data=mesh_data.facet_tags)
    normal = ufl.FacetNormal(domain)
    surface_heat_flow = {
        name: global_integral(
            ufl.dot(heat_flux, normal) * ds(semantic_tags[name]["tag"])
        )
        for name in ("hot_end", "cold_end")
    }

    cell_scalar = fem.functionspace(domain, ("DG", 0))
    cell_vector = fem.functionspace(
        domain, ("DG", 0, (domain.geometry.dim,))
    )
    cell_temperature = fem.Function(cell_scalar)
    cell_temperature.interpolate(
        fem.Expression(temperature, cell_scalar.element.interpolation_points)
    )
    cell_heat_flux = fem.Function(cell_vector)
    cell_heat_flux.interpolate(
        fem.Expression(heat_flux, cell_vector.element.interpolation_points)
    )

    cell_count = domain.topology.index_map(domain.topology.dim).size_local
    geometry_dofmap = domain.geometry.dofmap
    centroids = np.array(
        [
            domain.geometry.x[geometry_dofmap[cell]].mean(axis=0)
            for cell in range(cell_count)
        ]
    )
    temperature_values = np.array(
        [
            cell_temperature.x.array[cell_scalar.dofmap.cell_dofs(cell)[0]]
            for cell in range(cell_count)
        ]
    )
    heat_flux_values = np.array(
        [
            cell_heat_flux.x.array[
                cell_vector.dofmap.cell_dofs(cell)[0] * cell_vector.dofmap.bs :
                (cell_vector.dofmap.cell_dofs(cell)[0] + 1) * cell_vector.dofmap.bs
            ]
            for cell in range(cell_count)
        ]
    )
    region_ids = np.zeros(cell_count, dtype=np.int32)
    owned_tag_mask = mesh_data.cell_tags.indices < cell_count
    region_ids[mesh_data.cell_tags.indices[owned_tag_mask]] = mesh_data.cell_tags.values[
        owned_tag_mask
    ]

    owned = temperature.function_space.dofmap.index_map.size_local
    local_values = temperature.x.array[:owned]
    summary = {
        "T_min": domain.comm.allreduce(local_values.min(), op=MPI.MIN),
        "T_max": domain.comm.allreduce(local_values.max(), op=MPI.MAX),
        "T_avg": global_integral(temperature * ufl.dx) / volume,
        "q_avg": average_flux,
        "Q_dot_hot_end": surface_heat_flow["hot_end"],
        "Q_dot_cold_end": surface_heat_flow["cold_end"],
    }
    return {
        "cell_data": {
            "region_ID": region_ids,
            "x": centroids[:, 0],
            "y": centroids[:, 1],
            "z": centroids[:, 2],
            "T": temperature_values,
            "qx": heat_flux_values[:, 0],
            "qy": heat_flux_values[:, 1],
            "qz": heat_flux_values[:, 2],
            "qmag": np.linalg.norm(heat_flux_values, axis=1),
        },
        "bounds": np.column_stack(
            (domain.geometry.x.min(axis=0), domain.geometry.x.max(axis=0))
        ),
        "summary": summary,
    }
