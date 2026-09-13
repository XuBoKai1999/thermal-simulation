"""Derive physical quantities from a thermal solution."""

import numpy as np
from dolfinx import fem
from mpi4py import MPI
from petsc4py import PETSc
import ufl


def analyze(
    temperature, mesh_data, case_data, semantic_tags, material=None,
    heatflow_surfaces=None,
):
    temperature.name = "temperature"
    domain = mesh_data.mesh
    if material is None:
        from .materials import conductivity_field
        properties = case_data["_region_properties"]
        temperature_dependent = [
            values["k"] for values in properties.values()
            if values is not None and not values["k"].is_constant
        ]
        if temperature_dependent:
            from .materials import property_expression
            conductivity = property_expression(
                mesh_data, case_data, semantic_tags, "k", temperature
            )
        else:
            conductivity = conductivity_field(mesh_data, case_data, semantic_tags)
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
    dx = ufl.Measure("dx", domain=domain, subdomain_data=mesh_data.cell_tags)
    normal = ufl.FacetNormal(domain)
    if heatflow_surfaces is None:
        heatflow_surfaces = case_data["boundary_conditions"]
    invalid_surfaces = [
        name for name in heatflow_surfaces
        if name not in semantic_tags
        or semantic_tags[name]["dimension"] != domain.topology.dim - 1
    ]
    if invalid_surfaces:
        raise ValueError(f"Invalid heat-flow surfaces: {invalid_surfaces}")
    surface_heat_flow = {
        name: global_integral(
            ufl.dot(heat_flux, normal) * ds(semantic_tags[name]["tag"])
        )
        for name in heatflow_surfaces
    }

    region_statistics = {}
    temperature_space = temperature.function_space
    owned = temperature_space.dofmap.index_map.size_local
    for name in case_data["regions"]:
        tag = semantic_tags[name]["tag"]
        region_volume = global_integral(1 * dx(tag))
        cells = mesh_data.cell_tags.find(tag)
        dofs = np.unique([
            dof for cell in cells for dof in temperature_space.dofmap.cell_dofs(cell)
            if dof < owned
        ])
        local = temperature.x.array[dofs]
        region_statistics[name] = {
            "T_min_K": domain.comm.allreduce(
                local.min() if len(local) else np.inf, op=MPI.MIN
            ),
            "T_max_K": domain.comm.allreduce(
                local.max() if len(local) else -np.inf, op=MPI.MAX
            ),
            "T_avg_K": global_integral(temperature * dx(tag)) / region_volume,
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
    cell_heat_flux.name = "heat_flux"
    cell_heat_flux.interpolate(
        fem.Expression(heat_flux, cell_vector.element.interpolation_points)
    )

    cell_measure = fem.Function(cell_scalar)
    cell_measure.interpolate(
        fem.Expression(ufl.CellVolume(domain), cell_scalar.element.interpolation_points)
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
    cell_region = fem.Function(cell_scalar)
    cell_region.name = "region_ID"
    for cell, region_id in enumerate(region_ids):
        cell_region.x.array[cell_scalar.dofmap.cell_dofs(cell)[0]] = region_id
    cell_region.x.scatter_forward()

    local_cell_sizes = cell_measure.x.array[:cell_count] ** (1 / domain.topology.dim)
    characteristic_cell_size = float(np.median(np.concatenate(
        domain.comm.allgather(local_cell_sizes)
    )))
    local_low = domain.geometry.x.min(axis=0)
    local_high = domain.geometry.x.max(axis=0)

    local_values = temperature.x.array[:owned]
    summary = {
        "T_min": domain.comm.allreduce(local_values.min(), op=MPI.MIN),
        "T_max": domain.comm.allreduce(local_values.max(), op=MPI.MAX),
        "T_avg": global_integral(temperature * ufl.dx) / volume,
        "q_avg": average_flux,
        "regions": region_statistics,
    }
    summary.update({f"Q_dot_{name}": value for name, value in surface_heat_flow.items()})
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
        "bounds": np.column_stack((
            domain.comm.allreduce(local_low, op=MPI.MIN),
            domain.comm.allreduce(local_high, op=MPI.MAX),
        )),
        "characteristic_cell_size": characteristic_cell_size,
        "field_functions": {
            "temperature": temperature,
            "heat_flux": cell_heat_flux,
            "region_ID": cell_region,
        },
        "summary": summary,
    }
