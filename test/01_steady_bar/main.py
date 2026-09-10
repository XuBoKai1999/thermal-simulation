from pathlib import Path
import csv
import sys
import json

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from mpi4py import MPI

from lib import analyze, case, dump, mesh, model, solve

import geometry


case_dir = Path(__file__).resolve().parent
DUMP = {
    "directory": case_dir / "output" / "dump",
    "fields": [
        "cell_ID", "region_ID", "x", "y", "z",
        "T", "qx", "qy", "qz", "qmag",
    ],
}
mesh_path = mesh.ensure_mesh(
    case_dir / "build",
    geometry.__file__,
    geometry.build_geometry,
)
case_data = case.load_case(case_dir / "case.yaml")
semantic_tags = json.loads(
    (case_dir / "build" / "tags.json").read_text(encoding="utf-8")
)
mesh_data = mesh.load_mesh(mesh_path)
a, linear, boundary_conditions, space = model.build_model(
    mesh_data, case_data, semantic_tags
)
temperature = solve.solve(a, linear, boundary_conditions)

expected = case.load_expected(case_dir / "expected.yaml")
coordinates = space.tabulate_dof_coordinates()
owned_dofs = space.dofmap.index_map.size_local
at_midpoint = np.isclose(coordinates[:owned_dofs, 0], geometry.LENGTH / 2)
midpoint_sum = MPI.COMM_WORLD.allreduce(
    temperature.x.array[:owned_dofs][at_midpoint].sum(), op=MPI.SUM
)
midpoint_count = MPI.COMM_WORLD.allreduce(at_midpoint.sum(), op=MPI.SUM)
if midpoint_count == 0:
    raise RuntimeError("Mesh has no temperature DOFs on the midpoint section")
fem_midpoint = midpoint_sum / midpoint_count

hot = case_data["boundary_conditions"]["hot_end"]["value_K"]
cold = case_data["boundary_conditions"]["cold_end"]["value_K"]
analytic_midpoint = hot + (cold - hot) / 2
temperature_error = abs(fem_midpoint - analytic_midpoint)
temperature_passed = temperature_error <= expected["tolerances"]["temperature_K"]

derived = analyze.analyze(temperature, mesh_data, case_data, semantic_tags)
summary = derived["summary"]
cell_data = derived["cell_data"]
cell_ids, mesh_centroids = mesh.map_cell_ids(mesh_path, mesh_data.mesh)
cell_data["cell_ID"] = cell_ids
cell_count = len(cell_data["T"])
if any(len(values) != cell_count for values in cell_data.values()):
    raise RuntimeError("analyze.py returned inconsistent cell field lengths")
if not all(np.isfinite(values).all() for values in cell_data.values()):
    raise RuntimeError("analyze.py returned non-finite cell field values")
dump_centroids = np.column_stack((cell_data["x"], cell_data["y"], cell_data["z"]))
reference_centroids = np.array([mesh_centroids[int(cell_id)] for cell_id in cell_ids])
if not np.allclose(dump_centroids, reference_centroids, rtol=0.0, atol=1.0e-12):
    raise RuntimeError("cell_ID mapping centroid verification failed")

manifest = json.loads(
    (case_dir / "build" / "build.json").read_text(encoding="utf-8")
)
regions = {
    details["tag"]: name
    for name, details in semantic_tags.items()
    if details["dimension"] == mesh_data.mesh.topology.dim
}
dump_path = dump.write_dump(
    cell_data,
    DUMP["directory"],
    DUMP["fields"],
    manifest["mesh_id"],
    derived["bounds"],
    regions,
)

summary_path = case_dir / "output" / "summary.csv"
with summary_path.open("w", encoding="utf-8", newline="") as output:
    writer = csv.writer(output)
    writer.writerow(("quantity", "value"))
    for name, value in summary.items():
        if name == "regions":
            for region, statistics in value.items():
                for metric, result in statistics.items():
                    writer.writerow((f"region.{region}.{metric}", result))
        elif name == "q_avg":
            for axis, component in zip("xyz", value):
                writer.writerow((f"q_avg_{axis}", component))
        else:
            writer.writerow((name, value))
conductivity = next(iter(case_data["regions"].values()))["k"]
analytic_heat_flux = -conductivity * (cold - hot) / geometry.LENGTH
analytic_total_heat = analytic_heat_flux * geometry.WIDTH**2
flux_error = abs(summary["q_avg"][0] - analytic_heat_flux)
hot_error = abs(summary["Q_dot_hot_end"] + analytic_total_heat)
cold_error = abs(summary["Q_dot_cold_end"] - analytic_total_heat)
conservation_error = abs(
    abs(summary["Q_dot_hot_end"]) - abs(summary["Q_dot_cold_end"])
)
flux_passed = flux_error <= expected["tolerances"]["heat_flux_W_m2"]
hot_passed = hot_error <= expected["tolerances"]["total_heat_W"]
cold_passed = cold_error <= expected["tolerances"]["total_heat_W"]
conservation_passed = conservation_error <= expected["tolerances"]["total_heat_W"]

if MPI.COMM_WORLD.rank == 0:
    print("\nquantity              FEM          analytic      error")
    comparisons = [
        ("T(midpoint)", fem_midpoint, analytic_midpoint, temperature_error),
        ("q_x", summary["q_avg"][0], analytic_heat_flux, flux_error),
        ("Q_dot_hot", summary["Q_dot_hot_end"], -analytic_total_heat, hot_error),
        ("Q_dot_cold", summary["Q_dot_cold_end"], analytic_total_heat, cold_error),
    ]
    for name, fem_value, analytic_value, error in comparisons:
        print(f"{name:<20} {fem_value:<12.6g} {analytic_value:<12.6g} {error:.3g}")
    print(f"Temperature profile: {'PASS' if temperature_passed else 'FAIL'}")
    print(f"Heat flux: {'PASS' if flux_passed else 'FAIL'}")
    print(f"Hot-end total heat flow: {'PASS' if hot_passed else 'FAIL'}")
    print(f"Cold-end total heat flow: {'PASS' if cold_passed else 'FAIL'}")
    print(f"Heat-flow conservation: {'PASS' if conservation_passed else 'FAIL'}")
    print("cell_ID mapping: PASS")
    print(f"dump written: {dump_path}")
    print(f"summary written: {summary_path}")
if not all(
    (temperature_passed, flux_passed, hot_passed, cold_passed, conservation_passed)
):
    raise SystemExit(1)
