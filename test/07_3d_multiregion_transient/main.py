"""General 3D multi-region transient framework regression."""

import json
from pathlib import Path
import sys
import tempfile

import numpy as np


PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from lib import analyze, case, dump, dump_reader, mesh, model, solve

import geometry


case_dir = Path(__file__).resolve().parent
case_data = case.load_case(case_dir / "case.yaml")
surfaces = ("heater_face", "monitor_face", "side_probe")

with tempfile.TemporaryDirectory() as directory:
    root = Path(directory)
    mesh_path = mesh.ensure_mesh(root / "build", geometry.__file__, geometry.build_geometry)
    tags = json.loads((root / "build" / "tags.json").read_text(encoding="utf-8"))
    manifest = json.loads((root / "build" / "build.json").read_text(encoding="utf-8"))
    mesh_data = mesh.load_mesh(mesh_path)
    a, linear, bcs, space, previous = model.build_transient_model(
        mesh_data, case_data, tags
    )
    if not np.allclose(previous.x.array, 1.0):
        raise AssertionError("Uniform initial condition was not applied")
    problem = solve.make_solver(a, linear, bcs, "general_3d_transient_")
    temperature = None
    for step in range(5):
        temperature = problem.solve()
        if step == 0:
            a, linear, bcs, space, previous = model.build_transient_model(
                mesh_data, case_data, tags, temperature
            )
            problem = solve.make_solver(a, linear, bcs, "general_3d_transient_")
        else:
            previous.x.array[:] = temperature.x.array
            previous.x.scatter_forward()

    coordinates = space.tabulate_dof_coordinates()
    interface = coordinates[np.isclose(coordinates[:, 0], geometry.INTERFACE)]
    if len(interface) == 0 or len(np.unique(np.round(interface, 12), axis=0)) != len(interface):
        raise AssertionError("Perfect-contact interface has disconnected coincident DOFs")

    derived = analyze.analyze(
        temperature, mesh_data, case_data, tags, heatflow_surfaces=surfaces
    )
    summary = derived["summary"]
    if set(summary["regions"]) != set(case_data["regions"]):
        raise AssertionError("Missing per-region statistics")
    for values in summary["regions"].values():
        if not (1.0 <= values["T_min_K"] <= values["T_avg_K"]
                <= values["T_max_K"] <= 4.0):
            raise AssertionError(f"Invalid region statistics: {values}")
    if not all(np.isfinite(summary[f"Q_dot_{name}"]) for name in surfaces):
        raise AssertionError("Selected-surface heat flow is not finite")

    data = derived["cell_data"]
    data["cell_ID"], _ = mesh.map_cell_ids(mesh_path, mesh_data.mesh)
    region_names = {
        details["tag"]: name for name, details in tags.items()
        if details["dimension"] == mesh_data.mesh.topology.dim
    }
    path = dump.write_dump(
        data, root / "output" / "dump",
        ["cell_ID", "region_ID", "x", "y", "z", "T", "qx", "qy", "qz", "qmag"],
        manifest["mesh_id"], derived["bounds"], region_names,
        timestep=5, time=5.0,
    )
    metadata, dumped = dump_reader.read_dump(path)
    if metadata["MESH_ID"] != manifest["mesh_id"] or len(dumped["T"]) != len(data["T"]):
        raise AssertionError("Dump round trip failed")

print("General 3D multi-region transient: PASS")
print("interface shared topology: PASS")
print("uniform IC, three semantic surfaces, region statistics, heat flow, dump: PASS")
for name, values in summary["regions"].items():
    print(name, ", ".join(f"{key}={value:.6g}" for key, value in values.items()))
for name in surfaces:
    print(f"Q_dot_{name}={summary[f'Q_dot_{name}']:.6g} W")
