from pathlib import Path
import csv
import json
import sys

import numpy as np
import yaml


PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from lib import analyze, case, dump, mesh, model, solve

import geometry


case_dir = Path(__file__).resolve().parent
dump_directory = case_dir / "output" / "dump"
early_dump_end = 20
dump_fields = [
    "cell_ID", "region_ID", "x", "y", "z",
    "T", "qx", "qy", "qz", "qmag",
]

mesh_path = mesh.ensure_mesh(
    case_dir / "build", geometry.__file__, geometry.build_geometry
)
case_data = case.load_case(case_dir / "case.yaml")
semantic_tags = json.loads(
    (case_dir / "build" / "tags.json").read_text(encoding="utf-8")
)
manifest = json.loads(
    (case_dir / "build" / "build.json").read_text(encoding="utf-8")
)
mesh_data = mesh.load_mesh(mesh_path)
cell_ids, mesh_centroids = mesh.map_cell_ids(mesh_path, mesh_data.mesh)
regions = {
    details["tag"]: name
    for name, details in semantic_tags.items()
    if details["dimension"] == mesh_data.mesh.topology.dim
}

a, linear, boundary_conditions, _, previous = model.build_transient_model(
    mesh_data, case_data, semantic_tags
)
problem = solve.make_solver(
    a, linear, boundary_conditions, "transient_bar_"
)
for old_dump in dump_directory.glob("*.dump"):
    old_dump.unlink()


def write_snapshot(temperature, timestep):
    derived = analyze.analyze(temperature, mesh_data, case_data, semantic_tags)
    data = derived["cell_data"]
    data["cell_ID"] = cell_ids
    centroids = np.column_stack((data["x"], data["y"], data["z"]))
    reference = np.array([mesh_centroids[int(cell_id)] for cell_id in cell_ids])
    if not np.allclose(centroids, reference, rtol=0.0, atol=1.0e-12):
        raise RuntimeError("cell_ID mapping centroid verification failed")
    dump.write_dump(
        data,
        dump_directory,
        dump_fields,
        manifest["mesh_id"],
        derived["bounds"],
        regions,
        timestep=timestep,
        time=timestep * case_data["time"]["dt_s"],
    )
    return derived


write_snapshot(previous, 0)
dt = case_data["time"]["dt_s"]
end = case_data["time"]["end_s"]
steps = round(end / dt)
if not np.isclose(steps * dt, end):
    raise ValueError("time.end_s must be an integer multiple of time.dt_s")

final = None
for timestep in range(1, steps + 1):
    temperature = problem.solve()
    temperature.name = "temperature"
    if timestep == 1:
        a, linear, boundary_conditions, _, previous = model.build_transient_model(
            mesh_data, case_data, semantic_tags, temperature
        )
        problem = solve.make_solver(
            a, linear, boundary_conditions, "transient_bar_"
        )
    else:
        previous.x.array[:] = temperature.x.array
        previous.x.scatter_forward()
    if timestep <= early_dump_end or timestep == steps:
        final = write_snapshot(previous, timestep)

steady = 4.0 + (1.0 - 4.0) * final["cell_data"]["x"] / geometry.LENGTH
steady_error = np.max(np.abs(final["cell_data"]["T"] - steady))
tolerance = yaml.safe_load(
    (case_dir / "expected.yaml").read_text(encoding="utf-8")
)["steady_temperature_tolerance_K"]

with (case_dir / "output" / "summary.csv").open(
    "w", encoding="utf-8", newline=""
) as output:
    writer = csv.writer(output)
    writer.writerow(("quantity", "value"))
    writer.writerow(("final_time_s", end))
    writer.writerow(("final_steady_max_error_K", steady_error))

print(f"dump files: {early_dump_end + 2}")
print(f"final timestep: {steps}, time: {end:g} s")
print(f"final steady max error: {steady_error:.6g} K")
print(f"Final dump near steady: {'PASS' if steady_error <= tolerance else 'FAIL'}")
if steady_error > tolerance:
    raise SystemExit(1)
