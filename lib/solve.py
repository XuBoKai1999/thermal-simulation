"""Solve finite-element problems."""

from dolfinx.fem.petsc import LinearProblem


def solve(a, linear, boundary_conditions):
    problem = make_solver(a, linear, boundary_conditions, "steady_bar_")
    temperature = problem.solve()
    temperature.name = "temperature"
    return temperature


def make_solver(a, linear, boundary_conditions, prefix):
    return LinearProblem(
        a,
        linear,
        bcs=boundary_conditions,
        petsc_options_prefix=prefix,
        petsc_options={"ksp_type": "preonly", "pc_type": "lu"},
    )
