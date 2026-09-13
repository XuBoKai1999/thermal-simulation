"""Run the ADR01 Baseline v1 early post-demagnetization transient."""

from argparse import ArgumentParser
from copy import deepcopy
import json
from pathlib import Path
import sys

import numpy as np
from dolfinx import fem
from mpi4py import MPI
import ufl


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from lib import analyze, case, dump, materials, mesh, model, solve

import geometry


CASE_DIR = Path(__file__).resolve().parent
def internal_axial_flow(temperature, mesh_data, case_data, tags, surface):
    """Return heat flow toward decreasing z across a horizontal internal facet."""
    conductivity = materials.property_expression(
        mesh_data, case_data, tags, "k", temperature
    )
    heat_flux_z = -conductivity * ufl.grad(temperature)[2]
    measure = ufl.Measure("dS", domain=mesh_data.mesh, subdomain_data=mesh_data.facet_tags)
    local = fem.assemble_scalar(fem.form(-ufl.avg(heat_flux_z) * measure(tags[surface]["tag"])))
    return mesh_data.mesh.comm.allreduce(local, op=MPI.SUM)


def run(dt, end_time=0.05, output_every=None):
    case_data = deepcopy(case.load_case(CASE_DIR / "case.yaml"))
    case_data["time"].update(dt_s=dt, end_s=end_time)
    if output_every is not None:
        if not np.isfinite(output_every) or output_every <= 0:
            raise ValueError("output interval must be finite and positive")
        case_data["output"]["every_time_s"] = output_every
    step_count = round(end_time / dt)
    if not np.isclose(step_count * dt, end_time):
        raise ValueError("end time must be an integer number of timesteps")

    mesh_path = mesh.ensure_mesh(
        CASE_DIR / "build", geometry.__file__, geometry.build_geometry
    )
    tags = json.loads((CASE_DIR / "build/tags.json").read_text(encoding="utf-8"))
    manifest = json.loads((CASE_DIR / "build/build.json").read_text(encoding="utf-8"))
    mesh_data = mesh.load_mesh(mesh_path)
    residual, temperature, bcs, jacobian, previous = (
        model.build_nonlinear_transient_model(mesh_data, case_data, tags)
    )
    observations = []
    total_iterations = 0
    wanted_steps = set(case.output_timesteps(case_data))
    output_dir = CASE_DIR / "output" / f"dt_{dt:.8g}"
    dump_dir = output_dir / "dump"
    if dump_dir.exists():
        for old_dump in dump_dir.glob("*.dump"):
            old_dump.unlink()
    summary_path = output_dir / "summary.json"
    summary_path.unlink(missing_ok=True)

    cell_ids, _ = mesh.map_cell_ids(mesh_path, mesh_data.mesh)
    region_names = {
        details["tag"]: name for name, details in tags.items()
        if details["dimension"] == mesh_data.mesh.topology.dim
    }

    def write_snapshot(state, step, time):
        derived = analyze.analyze(
            state, mesh_data, case_data, tags, heatflow_surfaces=()
        )
        summary = derived["summary"]
        summary["switch_heat_flow_W"] = internal_axial_flow(
            state, mesh_data, case_data, tags, "edge_heat_switch_cylinder_2"
        )
        summary["ggg_to_cylinder_3_heat_flow_W"] = internal_axial_flow(
            state, mesh_data, case_data, tags, "edge_ggg_cylinder_3"
        )
        summary["support_1_heat_leak_W"] = internal_axial_flow(
            state, mesh_data, case_data, tags, "edge_support_1_cold_stage"
        )
        summary["support_2_heat_leak_W"] = internal_axial_flow(
            state, mesh_data, case_data, tags, "edge_support_2_cold_stage"
        )
        observations.append({"time_s": time, **summary})
        derived["cell_data"]["cell_ID"] = cell_ids
        dump.write_dump(
            derived["cell_data"], dump_dir,
            ["cell_ID", "region_ID", "x", "y", "z", "T", "qx", "qy", "qz", "qmag"],
            manifest["mesh_id"], derived["bounds"], region_names,
            timestep=step, time=time, solver_dt=dt,
            characteristic_cell_size=derived["characteristic_cell_size"],
        )

    write_snapshot(previous, 0, 0.0)

    for step in range(1, step_count + 1):
        temperature, iterations = solve.solve_nonlinear(
            residual, temperature, bcs, jacobian, f"adr01_dt_{dt:g}_"
        )
        total_iterations += iterations
        previous.x.array[:] = temperature.x.array
        previous.x.scatter_forward()
        if step not in wanted_steps:
            continue
        time = step * dt
        write_snapshot(temperature, step, time)

    result = {
        "dt_s": dt,
        "end_s": end_time,
        "output_every_s": case_data.get("output", {}).get("every_time_s"),
        "output_steps": [0, *sorted(wanted_steps)],
        "steps": step_count,
        "total_newton_iterations": total_iterations,
        "heat_flow_sign": "positive toward decreasing z (hot side toward cold side)",
        "observations": observations,
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(
        json.dumps(result, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(result))
    return result


if __name__ == "__main__":
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--dt", type=float, default=5e-4)
    parser.add_argument("--end", type=float, default=0.05)
    parser.add_argument("--output-every", type=float)
    args = parser.parse_args()
    run(args.dt, args.end, args.output_every)
