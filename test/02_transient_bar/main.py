"""Run a spatial-and-temporal convergence study for the transient bar."""

from copy import deepcopy
from pathlib import Path
import csv
import json
import sys

import numpy as np


PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from lib import analyze, case, dump, mesh, model, solve

import geometry


case_dir = Path(__file__).resolve().parent
output_root = case_dir / "output" / "convergence"
mesh_sizes = (0.01, 0.005, 0.0025)
time_steps = (0.0625, 0.03125, 0.015625)
comparison_times = (0.0, 0.0625, 0.125, 0.25, 0.5)
dump_fields = [
    "cell_ID", "region_ID", "x", "y", "z",
    "T", "qx", "qy", "qz", "qmag",
]
base_case = case.load_case(case_dir / "case.yaml")


def number_label(prefix, value):
    return f"{prefix}_{value:g}".replace(".", "p")


def prepare_mesh(dx):
    build_dir = case_dir / "build" / number_label("dx", dx)
    mesh_path = mesh.ensure_mesh(
        build_dir,
        geometry.__file__,
        lambda path: geometry.build_geometry(path, dx),
        cache_key=f"mesh_size={dx:.17g}",
    )
    semantic_tags = json.loads(
        (build_dir / "tags.json").read_text(encoding="utf-8")
    )
    manifest = json.loads(
        (build_dir / "build.json").read_text(encoding="utf-8")
    )
    mesh_data = mesh.load_mesh(mesh_path)
    cell_ids, centroids = mesh.map_cell_ids(mesh_path, mesh_data.mesh)
    regions = {
        details["tag"]: name
        for name, details in semantic_tags.items()
        if details["dimension"] == mesh_data.mesh.topology.dim
    }
    return mesh_path, mesh_data, semantic_tags, manifest, cell_ids, centroids, regions


def run(dx, dt, end_time, dump_times):
    (_, mesh_data, semantic_tags, manifest, cell_ids,
     mesh_centroids, regions) = prepare_mesh(dx)
    case_data = deepcopy(base_case)
    case_data["time"]["dt_s"] = dt
    case_data["time"]["end_s"] = end_time
    directory = (
        output_root / number_label("dx", dx) / number_label("dt", dt) / "dump"
    )
    for old_dump in directory.glob("*.dump"):
        old_dump.unlink()

    def write_snapshot(temperature, timestep, time):
        derived = analyze.analyze(temperature, mesh_data, case_data, semantic_tags)
        data = derived["cell_data"]
        data["cell_ID"] = cell_ids
        actual = np.column_stack((data["x"], data["y"], data["z"]))
        expected = np.array([mesh_centroids[int(i)] for i in cell_ids])
        if not np.allclose(actual, expected, rtol=0.0, atol=1.0e-12):
            raise RuntimeError("cell_ID mapping centroid verification failed")
        dump.write_dump(
            data, directory, dump_fields, manifest["mesh_id"], derived["bounds"],
            regions, timestep=timestep, time=time,
        )
        return derived

    a, linear, bcs, _, previous = model.build_transient_model(
        mesh_data, case_data, semantic_tags
    )
    problem = solve.make_solver(a, linear, bcs, "transient_bar_")
    write_snapshot(previous, 0, 0.0)
    steps = round(end_time / dt)
    wanted = {round(time / dt) for time in dump_times}
    final = None
    for timestep in range(1, steps + 1):
        temperature = problem.solve()
        temperature.name = "temperature"
        if timestep == 1:
            a, linear, bcs, _, previous = model.build_transient_model(
                mesh_data, case_data, semantic_tags, temperature
            )
            problem = solve.make_solver(a, linear, bcs, "transient_bar_")
        else:
            previous.x.array[:] = temperature.x.array
            previous.x.scatter_forward()
        if timestep in wanted:
            final = write_snapshot(previous, timestep, timestep * dt)
    return final, len(cell_ids)


output_root.mkdir(parents=True, exist_ok=True)
rows = []
for dx in mesh_sizes:
    for dt in time_steps:
        _, cell_count = run(
            dx, dt, max(comparison_times), comparison_times
        )
        rows.append((dx, dt, max(comparison_times), len(comparison_times), cell_count))
with (output_root / "runs.csv").open("w", encoding="utf-8", newline="") as file:
    writer = csv.writer(file)
    writer.writerow(("dx_m", "dt_s", "end_s", "number_of_dumps", "number_of_cells"))
    writer.writerows(rows)

print("mesh sizes:", ", ".join(f"{dx:g}" for dx in mesh_sizes), "m")
print("time steps:", ", ".join(f"{dt:g}" for dt in time_steps), "s")
print("comparison times:", ", ".join(f"{t:g}" for t in comparison_times), "s")
print("Early-transient space-time runs: PASS")
