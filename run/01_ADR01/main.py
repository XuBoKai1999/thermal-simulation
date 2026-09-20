"""Run the ADR01 Baseline v1 early post-demagnetization transient."""

from argparse import ArgumentParser
from copy import deepcopy
import json
from pathlib import Path
import sys
from time import perf_counter

import numpy as np
from dolfinx import fem, io
from mpi4py import MPI
import ufl


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from lib import analyze, case, dump, log, materials, mesh, model, solve

import geometry


CASE_DIR = Path(__file__).resolve().parent


def load_checkpoint(path, function, mesh_id):
    """Restore a serial P1 state and return its absolute simulation time."""
    with np.load(path, allow_pickle=False) as checkpoint:
        if int(checkpoint["format_version"]) != 1:
            raise ValueError("Unsupported checkpoint format")
        if str(checkpoint["mesh_id"]) != mesh_id:
            raise ValueError("Checkpoint mesh_id does not match the loaded mesh")
        values = checkpoint["temperature"]
        time = float(checkpoint["time_s"])
    if values.shape != function.x.array.shape or not np.isfinite(values).all():
        raise ValueError("Checkpoint temperature vector is incompatible or non-finite")
    if not np.isfinite(time) or time < 0:
        raise ValueError("Checkpoint time must be finite and non-negative")
    function.x.array[:] = values
    function.x.scatter_forward()
    return time


def save_checkpoint(path, function, mesh_id, time):
    """Save the exact serial P1 state needed by an ADR01 continuation."""
    if function.function_space.mesh.comm.size != 1:
        raise NotImplementedError("ADR01 checkpoint output currently supports serial runs only")
    np.savez(
        path, format_version=1, mesh_id=mesh_id, time_s=time,
        temperature=function.x.array,
    )


def internal_axial_flow(temperature, mesh_data, case_data, tags, surface):
    """Return heat flow toward decreasing z across a horizontal internal facet."""
    conductivity = materials.property_expression(
        mesh_data, case_data, tags, "k", temperature
    )
    heat_flux_z = -conductivity * ufl.grad(temperature)[2]
    measure = ufl.Measure("dS", domain=mesh_data.mesh, subdomain_data=mesh_data.facet_tags)
    local = fem.assemble_scalar(fem.form(-ufl.avg(heat_flux_z) * measure(tags[surface]["tag"])))
    return mesh_data.mesh.comm.allreduce(local, op=MPI.SUM)


def run(
    dt, end_time=0.05, output_every=None, restart_from=None, run_type="segment",
    summary_every=None, output_dir=None, dump_dir=None, checkpoint_dir=None,
    visualization_name="fields.pvd", physical_time_names=False, clean_output=True,
    logger=None, label=None, progress_every=10, log_path=None, terminal=True,
    initial_observation_check=None,
):
    started = perf_counter()
    logger = logger or log.RunLog(progress_every, terminal, log_path)
    label = label or run_type
    case_data = deepcopy(case.load_case(CASE_DIR / "case.yaml"))
    case_data["time"].update(dt_s=dt, end_s=end_time)
    if output_every is not None:
        if not np.isfinite(output_every) or output_every <= 0:
            raise ValueError("output interval must be finite and positive")
        case_data["output"]["every_time_s"] = output_every
    if summary_every is None:
        summary_every = dt
    if not np.isfinite(summary_every) or summary_every <= 0:
        raise ValueError("summary interval must be finite and positive")
    mesh_path = mesh.ensure_mesh(
        CASE_DIR / "build", geometry.__file__, geometry.build_geometry
    )
    tags = json.loads((CASE_DIR / "build/tags.json").read_text(encoding="utf-8"))
    manifest = json.loads((CASE_DIR / "build/build.json").read_text(encoding="utf-8"))
    mesh_data = mesh.load_mesh(mesh_path)
    residual, temperature, bcs, jacobian, previous = (
        model.build_nonlinear_transient_model(mesh_data, case_data, tags)
    )
    start_time = 0.0
    if restart_from is not None:
        start_time = load_checkpoint(restart_from, previous, manifest["mesh_id"])
        temperature.x.array[:] = previous.x.array
        temperature.x.scatter_forward()
    duration = end_time - start_time
    if duration <= 0:
        raise ValueError("end time must be later than checkpoint time")
    step_count = round(duration / dt)
    if not np.isclose(step_count * dt, duration):
        raise ValueError("run duration must be an integer number of timesteps")

    observations = []
    total_iterations = 0
    schedule_case = deepcopy(case_data)
    schedule_case["time"]["end_s"] = duration
    wanted_steps = set(case.output_timesteps(schedule_case))
    summary_case = deepcopy(schedule_case)
    summary_case["output"]["every_time_s"] = summary_every
    summary_steps = set(case.output_timesteps(summary_case)) | wanted_steps
    output_name = (
        f"dt_{dt:.8g}" if restart_from is None else
        f"{run_type}_t_{start_time:.8g}_to_{end_time:.8g}_dt_{dt:.8g}"
    )
    output_dir = Path(output_dir) if output_dir else CASE_DIR / "output" / output_name
    dump_dir = Path(dump_dir) if dump_dir else output_dir / "dump"
    checkpoint_dir = Path(checkpoint_dir) if checkpoint_dir else output_dir
    checkpoint_dir.mkdir(parents=True, exist_ok=True)
    if clean_output and dump_dir.exists():
        for old_dump in dump_dir.glob("*.dump"):
            old_dump.unlink()
    summary_path = output_dir / "summary.json"
    if clean_output:
        summary_path.unlink(missing_ok=True)
    visualization_dir = output_dir / "visualization"
    if clean_output and visualization_dir.exists():
        for old_output in visualization_dir.glob(f"{Path(visualization_name).stem}*"):
            if old_output.suffix in {".pvd", ".pvtu", ".vtu"}:
                old_output.unlink()
    visualization_dir.mkdir(parents=True, exist_ok=True)

    cell_ids, _ = mesh.map_cell_ids(mesh_path, mesh_data.mesh)
    region_names = {
        details["tag"]: name for name, details in tags.items()
        if details["dimension"] == mesh_data.mesh.topology.dim
    }

    vtk = io.VTKFile(mesh_data.mesh.comm, visualization_dir / visualization_name, "w")

    def summarize(state, time, iterations):
        state.name = "temperature"
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
        summary.update(
            time_s=time, newton_iterations=iterations,
            cumulative_newton_iterations=total_iterations,
        )
        if summary["T_min"] < 1.0 - 1.0e-10 or summary["T_max"] > 4.0 + 1.0e-10:
            raise RuntimeError(
                f"Temperature range [{summary['T_min']}, {summary['T_max']}] K "
                f"violates ADR01 Baseline v1 expectation at t={time} s"
            )
        return derived, summary

    def write_heavy(derived, step, time):
        derived["cell_data"]["cell_ID"] = cell_ids
        dump.write_dump(
            derived["cell_data"], dump_dir,
            ["cell_ID", "region_ID", "x", "y", "z", "T", "qx", "qy", "qz", "qmag"],
            manifest["mesh_id"], derived["bounds"], region_names,
            timestep=step, time=time, solver_dt=dt,
            characteristic_cell_size=derived["characteristic_cell_size"],
            filename=f"t_{time:.8g}s.dump" if physical_time_names else None,
        )
        fields = derived["field_functions"]
        vtk.write_function(
            [fields["temperature"], fields["heat_flux"], fields["region_ID"]], time
        )

    derived, summary = summarize(previous, start_time, 0)
    if initial_observation_check is not None:
        initial_observation_check(summary)
    observations.append(summary)
    save_checkpoint(
        checkpoint_dir / f"t_{start_time:.8g}s.npz" if physical_time_names else
        output_dir / f"checkpoint_t_{start_time:.8g}.npz",
        previous, manifest["mesh_id"], start_time,
    )
    write_heavy(derived, 0, start_time)

    for step in range(1, step_count + 1):
        temperature, iterations = solve.solve_nonlinear(
            residual, temperature, bcs, jacobian, f"adr01_dt_{dt:g}_"
        )
        total_iterations += iterations
        previous.x.array[:] = temperature.x.array
        previous.x.scatter_forward()
        time = start_time + step * dt
        logger.progress(step, step_count, time, dt, iterations, label)
        if step not in summary_steps:
            continue
        derived, summary = summarize(temperature, time, iterations)
        observations.append(summary)
        save_checkpoint(
            checkpoint_dir / f"t_{time:.8g}s.npz" if physical_time_names else
            output_dir / f"checkpoint_t_{time:.8g}.npz",
            temperature, manifest["mesh_id"], time,
        )
        if step in wanted_steps:
            write_heavy(derived, step, time)
    vtk.close()

    checkpoint_path = (
        checkpoint_dir / f"t_{end_time:.8g}s.npz" if physical_time_names else
        output_dir / f"checkpoint_t_{end_time:.8g}.npz"
    )
    save_checkpoint(checkpoint_path, previous, manifest["mesh_id"], end_time)

    result = {
        "mesh_id": manifest["mesh_id"],
        "cell_count": mesh_data.mesh.topology.index_map(
            mesh_data.mesh.topology.dim
        ).size_global,
        "temperature_dofs": temperature.function_space.dofmap.index_map.size_global,
        "dt_s": dt,
        "run_type": run_type,
        "start_s": start_time,
        "end_s": end_time,
        "restart_from": None if restart_from is None else str(restart_from),
        "checkpoint": str(checkpoint_path),
        "output_every_s": case_data.get("output", {}).get("every_time_s"),
        "summary_every_s": summary_every,
        "output_steps": [0, *sorted(wanted_steps)],
        "output_times_s": [
            start_time, *(start_time + step * dt for step in sorted(wanted_steps))
        ],
        "summary_times_s": [
            start_time, *(start_time + step * dt for step in sorted(summary_steps))
        ],
        "steps": step_count,
        "total_newton_iterations": total_iterations,
        "wall_time_s": perf_counter() - started,
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
    parser.add_argument("--summary-every", type=float)
    parser.add_argument("--progress-every", type=int, default=10)
    parser.add_argument("--log", type=Path)
    parser.add_argument("--no-terminal", action="store_true")
    parser.add_argument("--restart", type=Path)
    parser.add_argument(
        "--run-type", choices=("segment", "validation", "audit"), default="segment"
    )
    args = parser.parse_args()
    run(
        args.dt, args.end, args.output_every, args.restart, args.run_type,
        args.summary_every, progress_every=args.progress_every, log_path=args.log,
        terminal=not args.no_terminal,
    )
