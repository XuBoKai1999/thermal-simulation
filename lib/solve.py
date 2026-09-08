"""Solve finite-element problems."""

from dolfinx.fem.petsc import LinearProblem


def solve(a, linear, boundary_conditions):
    problem = LinearProblem(
        a,
        linear,
        bcs=boundary_conditions,
        petsc_options_prefix="steady_bar_",
        petsc_options={"ksp_type": "preonly", "pc_type": "lu"},
    )
    temperature = problem.solve()
    temperature.name = "temperature"
    return temperature
