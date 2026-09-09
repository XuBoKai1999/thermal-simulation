"""Define the steady-conduction finite-element problem."""

from dolfinx import fem
from mpi4py import MPI
from petsc4py import PETSc
import ufl


def build_model(mesh_data, case_data, semantic_tags):
    domain = mesh_data.mesh
    space = fem.functionspace(domain, ("Lagrange", 1))
    boundary_conditions = build_boundary_conditions(
        space, mesh_data.facet_tags, case_data, semantic_tags
    )
    trial = ufl.TrialFunction(space)
    test = ufl.TestFunction(space)

    region = next(iter(case_data["regions"].values()))
    conductivity = fem.Constant(domain, PETSc.ScalarType(region["k"]))
    a = ufl.inner(conductivity * ufl.grad(trial), ufl.grad(test)) * ufl.dx
    source = fem.Constant(domain, PETSc.ScalarType(0.0))
    linear = source * test * ufl.dx

    return a, linear, boundary_conditions, space


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
        initial = case_data["time"]["initial_condition"]
        x = initial_space.tabulate_dof_coordinates()[:, 0]
        previous.x.array[:] = [
            initial["left_T_K"] if coordinate < initial["split_x_m"]
            else initial["right_T_K"]
            for coordinate in x
        ]
        previous.x.scatter_forward()

    region = next(iter(case_data["regions"].values()))
    dt = case_data["time"]["dt_s"]
    rho_cp_over_dt = fem.Constant(
        domain, PETSc.ScalarType(region["rho"] * region["cp"] / dt)
    )
    conductivity = fem.Constant(domain, PETSc.ScalarType(region["k"]))
    a = (
        rho_cp_over_dt * trial * test * ufl.dx
        + ufl.inner(conductivity * ufl.grad(trial), ufl.grad(test)) * ufl.dx
    )
    linear = rho_cp_over_dt * previous * test * ufl.dx
    return a, linear, boundary_conditions, space, previous
