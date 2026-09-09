"""Run the nonlinear zero-thickness-contact mesh-convergence benchmark."""

from pathlib import Path
import csv
import json
import sys

import gmsh
import numpy as np
import yaml


PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from lib import contact, dump, mesh

import geometry
import material


case_dir = Path(__file__).resolve().parent
case_data = yaml.safe_load((case_dir / "case.yaml").read_text(encoding="utf-8"))
mesh_sizes = (0.01, 0.005, 0.0025, 0.00125)
contact_h = 250.0
fields = ["cell_ID", "region_ID", "x", "y", "z", "T", "qx", "qy", "qz", "qmag"]


def label(value):
    return f"dx_{value:g}".replace(".", "p")


def exact_temperature(x):
    x = np.asarray(x)
    left = x < geometry.CONTACT_X
    y = np.where(
        left,
        1.5 + 1.5**3 / 13 - 25 * x,
        -0.5 - 0.5**3 / 13 - 25 * (x - geometry.CONTACT_X),
    )
    discriminant = np.sqrt((13 * y / 2) ** 2 + (13 / 3) ** 3)
    theta = np.cbrt(13 * y / 2 + discriminant) + np.cbrt(13 * y / 2 - discriminant)
    return 2.5 + theta


def gmsh_cell_ids(mesh_path):
    gmsh.initialize()
    try:
        gmsh.open(str(mesh_path))
        node_tags, coordinates, _ = gmsh.model.mesh.getNodes()
        points = dict(zip(map(int, node_tags), coordinates.reshape((-1, 3))))
        _, element_tags, element_nodes = gmsh.model.mesh.getElements(1)
        cells = []
        for tags, nodes in zip(element_tags, element_nodes):
            for tag, pair in zip(tags, nodes.reshape((-1, 2))):
                cells.append((np.mean([points[int(i)][0] for i in pair]), int(tag)))
        return np.array([tag for _, tag in sorted(cells)], dtype=np.int64)
    finally:
        gmsh.finalize()


rows = []
mesh_records = {}
for dx in mesh_sizes:
    build_dir = case_dir / "build" / label(dx)
    mesh_path = mesh.ensure_mesh(
        build_dir, geometry.__file__, lambda path: geometry.build_geometry(path, dx),
        cache_key=f"dx={dx:.17g}",
    )
    count = round(geometry.CONTACT_X / dx)
    x_left = np.linspace(0, geometry.CONTACT_X, count + 1)
    x_right = np.linspace(geometry.CONTACT_X, geometry.LENGTH, count + 1)
    result = contact.solve_steady_rod(
        x_left, x_right, material.k, contact_h, 4.0, 1.0
    )
    ids = gmsh_cell_ids(mesh_path)
    if len(ids) != len(result["cell_x"]):
        raise RuntimeError("mesh.msh and solver cell counts differ")
    exact_T = exact_temperature(result["cell_x"])
    error_T = np.sqrt(np.mean((result["cell_T"] - exact_T) ** 2))
    error_q = np.sqrt(np.mean((result["cell_q"] - 250.0) ** 2))
    jump = result["T_left"] - result["T_right"]
    mean_q = np.mean(result["cell_q"])
    interface_q = result["conservative_q"][len(x_left) - 2]
    contact_residual = interface_q - contact_h * jump
    manifest = json.loads((build_dir / "build.json").read_text(encoding="utf-8"))
    data = {
        "cell_ID": ids,
        "region_ID": np.where(result["cell_x"] < geometry.CONTACT_X, 1, 2),
        "x": result["cell_x"], "y": np.zeros_like(ids), "z": np.zeros_like(ids),
        "T": result["cell_T"], "qx": result["cell_q"],
        "qy": np.zeros_like(result["cell_q"]), "qz": np.zeros_like(result["cell_q"]),
        "qmag": np.abs(result["cell_q"]),
    }
    dump.write_dump(
        data, case_dir / "output" / label(dx) / "dump", fields,
        manifest["mesh_id"], ((0, geometry.LENGTH), (0, 0), (0, 0)),
        {1: "hot_half", 2: "cold_half"},
    )
    rows.append((
        dx, len(ids), result["T_left"], result["T_right"], jump, mean_q,
        contact_residual, error_T, error_q, result["iterations"],
    ))
    mesh_records[dx] = (ids, manifest, result, x_left, x_right)

output = case_dir / "output"
output.mkdir(exist_ok=True)
with (output / "convergence.csv").open("w", encoding="utf-8", newline="") as file:
    writer = csv.writer(file)
    writer.writerow((
        "dx_m", "cells", "T_left_K", "T_right_K", "jump_K", "mean_qx_W_m2",
        "contact_residual_W_m2", "rmse_T_K", "rmse_q_W_m2", "newton_iterations",
    ))
    writer.writerows(rows)

expected = yaml.safe_load((case_dir / "expected.yaml").read_text(encoding="utf-8"))["tolerances"]
finest = rows[-1]
passed = (
    abs(finest[2] - 3) < expected["interface_temperature_K"]
    and abs(finest[3] - 2) < expected["interface_temperature_K"]
    and abs(finest[6]) < expected["contact_residual_W_m2"]
    and finest[7] < expected["finest_temperature_K"]
    and finest[8] < expected["finest_heat_flux_W_m2"]
)
print(f"finest T_left/T_right: {finest[2]:.12g} / {finest[3]:.12g} K")
print(f"finest mean qx: {finest[5]:.12g} W/m^2")
print(f"finest T/q RMSE: {finest[7]:.6g} K / {finest[8]:.6g} W/m^2")
print(f"Nonlinear zero-thickness contact: {'PASS' if passed else 'FAIL'}")
if not passed:
    raise SystemExit(1)

# One common early-time slice for a dx-by-dt numerical convergence comparison.
slice_time = 0.125
slice_steps = (0.125, 0.0625, 0.03125, 0.015625)
slice_rows = []
for dx in mesh_sizes:
    ids_i, manifest_i, basis, left_nodes, right_nodes = mesh_records[dx]
    for dt_i in slice_steps:
        state = np.concatenate((np.full(len(left_nodes), 4.0), np.full(len(right_nodes), 1.0)))
        for _ in range(round(slice_time / dt_i)):
            state = contact.advance_transient_rod(
                left_nodes, right_nodes, state, material.k, contact_h, 100000.0,
                dt_i, 4.0, 1.0,
            )
        cell_T = np.array([(state[a] + state[b]) / 2 for a, b in basis["elements"]])
        cell_q = np.array([
            -material.k((state[a] + state[b]) / 2)
            * (state[b] - state[a]) / (basis["x"][b] - basis["x"][a])
            for a, b in basis["elements"]
        ])
        zeros = np.zeros_like(cell_q)
        data = {
            "cell_ID": ids_i,
            "region_ID": np.where(basis["cell_x"] < 0.05, 1, 2),
            "x": basis["cell_x"], "y": zeros, "z": zeros, "T": cell_T,
            "qx": cell_q, "qy": zeros, "qz": zeros, "qmag": np.abs(cell_q),
        }
        slice_dir = (
            output / "slice_0p125" / label(dx)
            / f"dt_{dt_i:g}".replace(".", "p") / "dump"
        )
        dump.write_dump(
            data, slice_dir, fields, manifest_i["mesh_id"],
            ((0, geometry.LENGTH), (0, 0), (0, 0)),
            {1: "hot_half", 2: "cold_half"},
            timestep=round(slice_time / dt_i), time=slice_time,
        )
        slice_rows.append((dx, dt_i, len(ids_i)))
with (output / "slice_0p125" / "runs.csv").open(
    "w", encoding="utf-8", newline=""
) as file:
    writer = csv.writer(file)
    writer.writerow(("dx_m", "dt_s", "cells"))
    writer.writerows(slice_rows)
print(f"0.125 s convergence slice: {len(slice_rows)} runs")

# Finest dx/dt transient reference; it approaches the independently verified steady state.
transient = case_data["transient"]
dt = transient["dt_s"]
dump_times = (0.0, 0.125, 0.5, 2.0, 10.0, 50.0, 100.0, 200.0, 500.0)
directory = output / "transient" / "dump"
for old_dump in directory.glob("*.dump"):
    old_dump.unlink()
previous = np.concatenate((
    np.full(len(x_left), transient["initial_left_K"]),
    np.full(len(x_right), transient["initial_right_K"]),
))
wanted = {round(time / dt): time for time in dump_times}
transient_rows = []


def write_transient(values, timestep, time):
    cell_T = np.array([(values[a] + values[b]) / 2 for a, b in result["elements"]])
    cell_q = np.array([
        -material.k((values[a] + values[b]) / 2)
        * (values[b] - values[a]) / (result["x"][b] - result["x"][a])
        for a, b in result["elements"]
    ])
    zeros = np.zeros_like(cell_q)
    data = {
        "cell_ID": ids, "region_ID": np.where(result["cell_x"] < 0.05, 1, 2),
        "x": result["cell_x"], "y": zeros, "z": zeros, "T": cell_T,
        "qx": cell_q, "qy": zeros, "qz": zeros, "qmag": np.abs(cell_q),
    }
    dump.write_dump(
        data, directory, fields, manifest["mesh_id"],
        ((0, geometry.LENGTH), (0, 0), (0, 0)), {1: "hot_half", 2: "cold_half"},
        timestep=timestep, time=time,
    )
    left_T, right_T = values[len(x_left) - 1], values[len(x_left)]
    transient_rows.append((time, left_T, right_T, left_T - right_T,
                           contact_h * (left_T - right_T)))


write_transient(previous, 0, 0.0)
for timestep in range(1, round(transient["end_s"] / dt) + 1):
    previous = contact.advance_transient_rod(
        x_left, x_right, previous, material.k, contact_h,
        transient["rho_kg_m3"] * transient["cp_J_kgK"], dt, 4.0, 1.0,
    )
    if timestep in wanted:
        write_transient(previous, timestep, wanted[timestep])

with (output / "transient_summary.csv").open(
    "w", encoding="utf-8", newline=""
) as file:
    writer = csv.writer(file)
    writer.writerow(("time_s", "T_left_K", "T_right_K", "jump_K", "contact_q_W_m2"))
    writer.writerows(transient_rows)
print(f"transient reference: dx={mesh_sizes[-1]:g} m, dt={dt:g} s")
print(f"transient dumps: {len(transient_rows)}, final time={dump_times[-1]:g} s")
