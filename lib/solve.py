"""Solve finite-element problems."""

from dolfinx.fem.petsc import LinearProblem, NonlinearProblem


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


def solve_nonlinear(residual, temperature, boundary_conditions, jacobian, prefix):
    problem = NonlinearProblem(
        residual,
        temperature,
        bcs=boundary_conditions,
        J=jacobian,
        petsc_options_prefix=prefix,
        petsc_options={
            "snes_type": "newtonls",
            "snes_rtol": 1.0e-10,
            "snes_atol": 1.0e-12,
            "snes_max_it": 50,
            "snes_error_if_not_converged": True,
            "ksp_type": "preonly",
            "pc_type": "lu",
            "ksp_error_if_not_converged": True,
        },
    )
    solution = problem.solve()
    owned = solution.function_space.dofmap.index_map.size_local
    local = solution.x.array[:owned]
    for name, prop, indices in getattr(solution, "_properties", []):
        try:
            prop.evaluate(local if indices is None else solution.x.array[indices])
        except ValueError as error:
            raise ValueError(f"Invalid {name} at solved temperature: {error}") from error
    solution.name = "temperature"
    return solution, problem.solver.getIterationNumber()
