from pathlib import Path
import csv
import json
import sys

import numpy as np


PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from lib import analyze, case, dump, mesh, model, solve

import geometry
import material


case_dir = Path(__file__).resolve().parent
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
residual, temperature, boundary_conditions, jacobian = model.build_nonlinear_model(
    mesh_data, case_data, semantic_tags, material
)
temperature, iterations = solve.solve_nonlinear(
    residual, temperature, boundary_conditions, jacobian, "nonlinear_bar_"
)
derived = analyze.analyze(
    temperature, mesh_data, case_data, semantic_tags, material=material
)
data = derived["cell_data"]
cell_ids, mesh_centroids = mesh.map_cell_ids(mesh_path, mesh_data.mesh)
data["cell_ID"] = cell_ids
centroids = np.column_stack((data["x"], data["y"], data["z"]))
reference = np.array([mesh_centroids[int(cell_id)] for cell_id in cell_ids])
if not np.allclose(centroids, reference, rtol=0.0, atol=1.0e-12):
    raise RuntimeError("cell_ID mapping centroid verification failed")

hot = case_data["boundary_conditions"]["hot_end"]["value_K"]
cold = case_data["boundary_conditions"]["cold_end"]["value_K"]


def kirchhoff(T):
    return material.K0 * (T + 0.5 * material.BETA * T**2)


transformed = kirchhoff(hot) + (
    kirchhoff(cold) - kirchhoff(hot)
) * data["x"] / geometry.LENGTH
analytic_temperature = (
    -1.0 + np.sqrt(1.0 + 2.0 * material.BETA * transformed / material.K0)
) / material.BETA
analytic_flux = (kirchhoff(hot) - kirchhoff(cold)) / geometry.LENGTH
temperature_error = np.max(np.abs(data["T"] - analytic_temperature))
flux_error = abs(derived["summary"]["q_avg"][0] - analytic_flux)
analytic_total_heat = analytic_flux * geometry.WIDTH**2
hot_error = abs(derived["summary"]["Q_dot_hot_end"] + analytic_total_heat)
expected = case.load_expected(case_dir / "expected.yaml")["tolerances"]

regions = {
    details["tag"]: name for name, details in semantic_tags.items()
    if details["dimension"] == mesh_data.mesh.topology.dim
}
dump_path = dump.write_dump(
    data,
    case_dir / "output" / "dump",
    ["cell_ID", "region_ID", "x", "y", "z", "T", "qx", "qy", "qz", "qmag"],
    manifest["mesh_id"],
    derived["bounds"],
    regions,
)
with (case_dir / "output" / "summary.csv").open(
    "w", encoding="utf-8", newline=""
) as output:
    writer = csv.writer(output)
    writer.writerow(("quantity", "value"))
    writer.writerow(("newton_iterations", iterations))
    writer.writerow(("temperature_max_error_K", temperature_error))
    writer.writerow(("heat_flux_error_W_m2", flux_error))
    writer.writerow(("hot_end_total_heat_error_W", hot_error))

passed = (
    temperature_error <= expected["temperature_K"]
    and flux_error <= expected["heat_flux_W_m2"]
    and hot_error <= expected["total_heat_W"]
)
print(f"Newton iterations: {iterations}")
print(f"Temperature max error: {temperature_error:.6g} K")
print(f"Heat flux error: {flux_error:.6g} W/m^2")
print(f"Hot-end total heat error: {hot_error:.6g} W")
print(f"Temperature-dependent material: {'PASS' if passed else 'FAIL'}")
print(f"dump written: {dump_path}")
if not passed:
    raise SystemExit(1)
