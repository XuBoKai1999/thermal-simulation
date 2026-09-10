"""Regression for constant-property, multi-region transient conduction."""

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
base_case = case.load_case(case_dir / "case.yaml")


def run(mesh_size, dt, end_time):
    with tempfile.TemporaryDirectory() as directory:
        build = Path(directory)
        mesh_path = mesh.ensure_mesh(
            build, geometry.__file__,
            lambda path: geometry.build_geometry(path, mesh_size),
            cache_key=f"mesh_size={mesh_size}",
        )
        tags = json.loads((build / "tags.json").read_text(encoding="utf-8"))
        mesh_data = mesh.load_mesh(mesh_path)
        case_data = deepcopy(base_case)
        case_data["time"]["dt_s"] = dt
        case_data["time"]["end_s"] = end_time
        a, linear, bcs, space, previous = model.build_transient_model(
            mesh_data, case_data, tags
        )
        problem = solve.make_solver(a, linear, bcs, "multi_region_transient_")
        temperature = None
        for step in range(1, round(end_time / dt) + 1):
            temperature = problem.solve()
            if step == 1:
                a, linear, bcs, space, previous = model.build_transient_model(
                    mesh_data, case_data, tags, temperature
                )
                problem = solve.make_solver(
                    a, linear, bcs, "multi_region_transient_"
                )
            else:
                previous.x.array[:] = temperature.x.array
                previous.x.scatter_forward()
        coordinates = space.tabulate_dof_coordinates()
        owned = space.dofmap.index_map.size_local
        interface_coordinates = coordinates[:owned][
            np.isclose(coordinates[:owned, 0], geometry.INTERFACE)
        ]
        if len(interface_coordinates) == 0 or len(np.unique(
            np.round(interface_coordinates, 12), axis=0
        )) != len(interface_coordinates):
            raise AssertionError("Interface contains disconnected coincident nodes")
        derived = analyze.analyze(temperature, mesh_data, case_data, tags)
        sample = temperature.x.array[:owned][
            np.argmin(np.abs(coordinates[:owned, 0] - 0.025))
        ]
        return sample, derived["cell_data"]


reference, _ = run(0.005, 0.5, 10.0)
space_errors = []
for dx in (0.02, 0.01, 0.005):
    value, _ = run(dx, 0.5, 10.0)
    space_errors.append(abs(value - reference))
time_errors = []
for dt in (2.0, 1.0, 0.5):
    value, _ = run(0.005, dt, 10.0)
    time_errors.append(abs(value - reference))

_, final = run(0.005, 10.0, 3000.0)
x = final["x"]
steady_flux = (4.0 - 1.0) / (0.05 / 10.0 + 0.05 / 20.0)
interface_temperature = 4.0 - steady_flux * 0.05 / 10.0
analytic = np.where(
    x <= 0.05,
    4.0 - steady_flux * x / 10.0,
    interface_temperature - steady_flux * (x - 0.05) / 20.0,
)
steady_error = np.max(np.abs(final["T"] - analytic))

if space_errors[1] > space_errors[0] or space_errors[2] > 1e-12:
    raise AssertionError(f"Unexpected mesh refinement errors: {space_errors}")
if time_errors[1] > time_errors[0] or time_errors[2] > 1e-12:
    raise AssertionError(f"Unexpected time-step refinement errors: {time_errors}")
if steady_error > 2e-4:
    raise AssertionError(f"Long-time steady error is {steady_error} K")

print("Multi-region transient: PASS")
print("space refinement errors:", ", ".join(f"{e:.6g}" for e in space_errors))
print("time-step refinement errors:", ", ".join(f"{e:.6g}" for e in time_errors))
print(f"long-time steady max error: {steady_error:.6g} K")
