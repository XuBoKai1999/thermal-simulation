"""Define the steady-conduction finite-element problem."""

from dolfinx import fem
from mpi4py import MPI
from petsc4py import PETSc
import ufl


def build_model(mesh_data, case_data, semantic_tags):
    domain = mesh_data.mesh
    facet_tags = mesh_data.facet_tags
    space = fem.functionspace(domain, ("Lagrange", 1))
    trial = ufl.TrialFunction(space)
    test = ufl.TestFunction(space)

    region = next(iter(case_data["regions"].values()))
    conductivity = fem.Constant(domain, PETSc.ScalarType(region["k"]))
    a = ufl.inner(conductivity * ufl.grad(trial), ufl.grad(test)) * ufl.dx
    source = fem.Constant(domain, PETSc.ScalarType(0.0))
    linear = source * test * ufl.dx

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

    return a, linear, boundary_conditions, space
