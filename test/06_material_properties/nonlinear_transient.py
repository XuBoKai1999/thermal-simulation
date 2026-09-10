"""Regression for multi-region temperature-dependent transient conduction."""

from copy import deepcopy
import json
from pathlib import Path
import sys
import tempfile

import numpy as np


PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from lib import analyze, case, mesh, model, solve

import geometry


case_dir = Path(__file__).resolve().parent
base_case = case.load_case(case_dir / "nonlinear_case.yaml")


def run(dt, end_time):
    with tempfile.TemporaryDirectory() as directory:
        build = Path(directory)
        mesh_path = mesh.ensure_mesh(
            build, geometry.__file__,
            lambda path: geometry.build_geometry(path, 0.01),
            cache_key="mesh_size=0.01",
        )
        tags = json.loads((build / "tags.json").read_text(encoding="utf-8"))
        mesh_data = mesh.load_mesh(mesh_path)
        case_data = deepcopy(base_case)
        case_data["time"]["dt_s"] = dt
        case_data["time"]["end_s"] = end_time
        residual, temperature, bcs, jacobian, previous = (
            model.build_nonlinear_transient_model(mesh_data, case_data, tags)
        )
        iterations = 0
        for _ in range(round(end_time / dt)):
            temperature, count = solve.solve_nonlinear(
                residual, temperature, bcs, jacobian,
                "nonlinear_transient_",
            )
            iterations += count
            previous.x.array[:] = temperature.x.array
            previous.x.scatter_forward()
        derived = analyze.analyze(temperature, mesh_data, case_data, tags)
        coordinates = temperature.function_space.tabulate_dof_coordinates()
        owned = temperature.function_space.dofmap.index_map.size_local
        sample = temperature.x.array[:owned][
            np.argmin(np.abs(coordinates[:owned, 0] - 0.025))
        ]
        return sample, derived["cell_data"], iterations


reference, _, _ = run(0.25, 10.0)
time_errors = [abs(run(dt, 10.0)[0] - reference) for dt in (1.0, 0.5, 0.25)]
_, final, iterations = run(10.0, 3000.0)

# k(T)=10T, so the steady Kirchhoff transform is proportional to T^2.
hot, cold = 4.0, 1.0
analytic = np.sqrt(hot**2 + (cold**2 - hot**2) * final["x"] / geometry.LENGTH)
steady_error = np.max(np.abs(final["T"] - analytic))

if time_errors[1] > time_errors[0] or time_errors[2] > 1e-12:
    raise AssertionError(f"Unexpected time-step refinement errors: {time_errors}")
if steady_error > 3e-2:
    raise AssertionError(f"Long-time steady error is {steady_error} K")

print("Temperature-dependent multi-region transient: PASS")
print("time-step refinement errors:", ", ".join(f"{e:.6g}" for e in time_errors))
print(f"long-time steady max error: {steady_error:.6g} K")
print(f"total Newton iterations in long run: {iterations}")
