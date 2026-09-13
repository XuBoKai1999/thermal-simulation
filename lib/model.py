"""Define the steady-conduction finite-element problem."""

import numpy as np
from dolfinx import fem
from mpi4py import MPI
from petsc4py import PETSc
import ufl

from . import materials


def _set_initial_values(function, initial, cell_tags=None, semantic_tags=None):
    if initial["type"] == "uniform":
        function.x.array[:] = initial["value_K"]
    elif initial["type"] == "split_x":
        x = function.function_space.tabulate_dof_coordinates()[:, 0]
        function.x.array[:] = np.where(
            x < initial["split_x_m"], initial["left_T_K"], initial["right_T_K"]
        )
    else:
        function.x.array[:] = initial["default_K"]
        for name, value in initial["regions"].items():
            for cell in cell_tags.find(semantic_tags[name]["tag"]):
                function.x.array[function.function_space.dofmap.cell_dofs(cell)] = value
    function.x.scatter_forward()


def build_model(mesh_data, case_data, semantic_tags):
    domain = mesh_data.mesh
    space = fem.functionspace(domain, ("Lagrange", 1))
    boundary_conditions = build_boundary_conditions(
        space, mesh_data.facet_tags, case_data, semantic_tags
    )
    trial = ufl.TrialFunction(space)
    test = ufl.TestFunction(space)

    conductivity = materials.conductivity_field(
        mesh_data, case_data, semantic_tags
    )
    a = ufl.inner(conductivity * ufl.grad(trial), ufl.grad(test)) * ufl.dx
    source = fem.Constant(domain, PETSc.ScalarType(0.0))
    linear = source * test * ufl.dx

    return a, linear, boundary_conditions, space


def build_nonlinear_model(mesh_data, case_data, semantic_tags, material=None):
    if material is not None:
        materials.validate(material, ("k",))
    domain = mesh_data.mesh
    space = fem.functionspace(domain, ("Lagrange", 1))
    boundary_conditions = build_boundary_conditions(
        space, mesh_data.facet_tags, case_data, semantic_tags
    )
    temperature = fem.Function(space)
    temperature.x.array[:] = np.mean([
        condition["value_K"]
        for condition in case_data["boundary_conditions"].values()
    ])
    fem.set_bc(temperature.x.array, boundary_conditions)
    temperature.x.scatter_forward()
    test = ufl.TestFunction(space)
    if material is None:
        properties = next(iter(case_data["_region_properties"].values()))
        conductivity = properties["k"].evaluate(temperature)
    else:
        conductivity = material.k(temperature)
    if material is None:
        temperature._properties = [("k", properties["k"], None)]
    residual = ufl.inner(
        conductivity * ufl.grad(temperature), ufl.grad(test)
    ) * ufl.dx
    jacobian = ufl.derivative(residual, temperature)
    return residual, temperature, boundary_conditions, jacobian


def build_boundary_conditions(space, facet_tags, case_data, semantic_tags):
    domain = space.mesh
    boundary_conditions = []
    facet_dimension = domain.topology.dim - 1
    for name, condition in case_data["boundary_conditions"].items():
        tag = semantic_tags[name]["tag"]
        facets = facet_tags.find(tag)
        facet_count = domain.comm.allreduce(len(facets), op=MPI.SUM)
        if facet_count == 0:
            raise ValueError(f"Mesh has no facets tagged {name}")
        dofs = fem.locate_dofs_topological(space, facet_dimension, facets)
        value = PETSc.ScalarType(condition["value_K"])
        boundary_conditions.append(fem.dirichletbc(value, dofs, space))

    return boundary_conditions


def build_transient_model(mesh_data, case_data, semantic_tags, previous=None):
    domain = mesh_data.mesh
    space = fem.functionspace(domain, ("Lagrange", 1))
    boundary_conditions = build_boundary_conditions(
        space, mesh_data.facet_tags, case_data, semantic_tags
    )
    trial = ufl.TrialFunction(space)
    test = ufl.TestFunction(space)
    if previous is None:
        initial_space = fem.functionspace(domain, ("DG", 0))
        previous = fem.Function(initial_space)
        _set_initial_values(
            previous, case_data["time"]["initial_condition"],
            mesh_data.cell_tags, semantic_tags,
        )

    dt = case_data["time"]["dt_s"]
    density = materials.property_field(mesh_data, case_data, semantic_tags, "rho")
    heat_capacity = materials.property_field(mesh_data, case_data, semantic_tags, "cp")
    conductivity = materials.conductivity_field(mesh_data, case_data, semantic_tags)
    rho_cp_over_dt = density * heat_capacity / dt
    a = (
        rho_cp_over_dt * trial * test * ufl.dx
        + ufl.inner(conductivity * ufl.grad(trial), ufl.grad(test)) * ufl.dx
    )
    linear = rho_cp_over_dt * previous * test * ufl.dx
    return a, linear, boundary_conditions, space, previous


def build_nonlinear_transient_model(
    mesh_data, case_data, semantic_tags, previous=None
):
    """Build backward Euler conduction with region-wise properties p(T)."""
    domain = mesh_data.mesh
    space = fem.functionspace(domain, ("Lagrange", 1))
    boundary_conditions = build_boundary_conditions(
        space, mesh_data.facet_tags, case_data, semantic_tags
    )
    if previous is None:
        initial_space = fem.functionspace(domain, ("DG", 0))
        initial_field = fem.Function(initial_space)
        _set_initial_values(
            initial_field, case_data["time"]["initial_condition"],
            mesh_data.cell_tags, semantic_tags,
        )
        previous = fem.Function(space)
        previous.interpolate(
            fem.Expression(initial_field, space.element.interpolation_points)
        )
        fem.set_bc(previous.x.array, boundary_conditions)
        previous.x.scatter_forward()

    temperature = fem.Function(space)
    temperature.x.array[:] = previous.x.array
    fem.set_bc(temperature.x.array, boundary_conditions)
    temperature.x.scatter_forward()
    test = ufl.TestFunction(space)
    coefficients = {
        name: materials.property_expression(
            mesh_data, case_data, semantic_tags, name, temperature
        )
        for name in ("k", "rho", "cp")
    }
    dt = case_data["time"]["dt_s"]
    dx = ufl.Measure("dx", domain=domain, metadata={"quadrature_degree": 2})
    residual = (
        coefficients["rho"] * coefficients["cp"]
        * (temperature - previous) / dt * test * dx
        + ufl.inner(
            coefficients["k"] * ufl.grad(temperature), ufl.grad(test)
        ) * dx
    )
    jacobian = ufl.derivative(residual, temperature)
    temperature._properties = []
    domains = []
    for region, properties in case_data["_region_properties"].items():
        if properties is None:
            continue
        cells = mesh_data.cell_tags.find(semantic_tags[region]["tag"])
        dofs = np.unique([
            dof for cell in cells for dof in space.dofmap.cell_dofs(cell)
        ])
        for name, prop in properties.items():
            temperature._properties.append((f"{region}.{name}", prop, dofs))
            if prop.domain is not None:
                domains.append(prop.domain)
    if domains:
        temperature._bounds = (
            max(domain[0] for domain in domains),
            min(domain[1] for domain in domains),
        )
    return residual, temperature, boundary_conditions, jacobian, previous
