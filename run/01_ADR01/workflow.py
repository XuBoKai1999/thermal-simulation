"""Compare ADR01 timestep branches and select reproducible local audit points."""

from argparse import ArgumentParser
import csv
import json
from pathlib import Path
import random
import shutil
import subprocess
import tempfile
import xml.etree.ElementTree as ET

import matplotlib.pyplot as plt
import numpy as np
import yaml


CASE_DIR = Path(__file__).resolve().parent


TEMPERATURES = {
    "ggg_Tavg_K": lambda row: row["regions"]["ggg"]["T_avg_K"],
    "cold_stage_Tavg_K": lambda row: row["regions"]["cold_stage"]["T_avg_K"],
    "sample_Tavg_K": lambda row: row["regions"]["sample"]["T_avg_K"],
}
FLOWS = {
    "support_1_W": lambda row: row["support_1_heat_leak_W"],
    "support_2_W": lambda row: row["support_2_heat_leak_W"],
    "switch_W": lambda row: row["switch_heat_flow_W"],
}
METRICS = {**TEMPERATURES, **FLOWS}


def metric_gate(name, max_absolute, scale, tolerances):
    """Return relative error, gate result, and classification."""
    near_zero = name in FLOWS and scale <= 1.0e-12
    relative = None if near_zero else max_absolute / scale
    if name == "ggg_Tavg_K":
        return relative, None, "informational"
    if name in TEMPERATURES:
        passed = (max_absolute < tolerances.get("temperature_abs_K", 0.01)
                  or relative < tolerances.get("temperature_rel", 0.01))
        return relative, passed, "acceptance"
    if near_zero:
        return None, None, "near_zero_absolute_diagnostic"
    return relative, relative < tolerances.get("heat_flow_rel", 0.05), "acceptance"


def load_run(directory):
    directory = Path(directory)
    summary = json.loads((directory / "summary.json").read_text(encoding="utf-8"))
    checkpoint_path = Path(summary["checkpoint"])
    if not checkpoint_path.exists():
        checkpoint_path = directory / checkpoint_path.name
    checkpoint = np.load(checkpoint_path, allow_pickle=False)
    return directory, summary, checkpoint


def failure_time(observations, threshold):
    """Return the linearly interpolated upward sample-temperature crossing."""
    points = [(row["time_s"], TEMPERATURES["sample_Tavg_K"](row))
              for row in observations]
    if points[0][1] >= threshold:
        return points[0][0]
    for (t0, value0), (t1, value1) in zip(points, points[1:]):
        if value0 < threshold <= value1:
            return t0 + (threshold - value0) * (t1 - t0) / (value1 - value0)
    return None


def sanity(summary):
    values = [value for row in summary["observations"]
              for name in METRICS for value in (METRICS[name](row),)]
    minimum = min(row["T_min"] for row in summary["observations"])
    maximum = max(row["T_max"] for row in summary["observations"])
    return {
        "finite": bool(np.isfinite(values).all()),
        "temperature_range_K": [minimum, maximum],
        "range_pass": minimum >= 1.0 - 1.0e-10 and maximum <= 4.0 + 1.0e-10,
    }


def compare(coarse_dir, fine_dir, output_dir, thresholds, tolerances=None):
    coarse_dir, coarse, coarse_checkpoint = load_run(coarse_dir)
    fine_dir, fine, fine_checkpoint = load_run(fine_dir)
    if not (np.isclose(coarse["start_s"], fine["start_s"])
            and np.isclose(coarse["end_s"], fine["end_s"])):
        raise ValueError("Compared runs must have identical absolute start/end times")
    if str(coarse_checkpoint["mesh_id"]) != str(fine_checkpoint["mesh_id"]):
        raise ValueError("Compared runs must use the same mesh_id")

    coarse_rows = {round(row["time_s"], 12): row for row in coarse["observations"]}
    fine_rows = {round(row["time_s"], 12): row for row in fine["observations"]}
    times = sorted(set(coarse_rows) & set(fine_rows))
    if len(times) < 2:
        raise ValueError("Compared runs need at least two common output times")

    comparison_rows = []
    errors = []
    for name, get_value in METRICS.items():
        coarse_values = np.array([get_value(coarse_rows[time]) for time in times])
        fine_values = np.array([get_value(fine_rows[time]) for time in times])
        differences = np.abs(coarse_values - fine_values)
        for time, coarse_value, fine_value, difference in zip(
                times, coarse_values, fine_values, differences):
            comparison_rows.append([
                time, name, coarse_value, fine_value, difference,
            ])
        max_absolute = float(differences.max())
        scale = float(np.max(np.abs(fine_values)))
        tolerances = tolerances or {}
        relative, passed, gate = metric_gate(name, max_absolute, scale, tolerances)
        errors.append({
            "metric": name,
            "max_absolute_difference": max_absolute,
            "relative_to_fine_max": relative,
            "gate": gate,
            "pass": passed,
        })

    coarse_vector = coarse_checkpoint["temperature"]
    fine_vector = fine_checkpoint["temperature"]
    if coarse_vector.shape != fine_vector.shape:
        raise ValueError("Endpoint P1 vectors have different shapes")
    field_difference = coarse_vector - fine_vector
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    with (output_dir / "common_time_comparison.csv").open(
            "w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["time_s", "metric", "coarse", "fine", "absolute_difference"])
        writer.writerows(comparison_rows)
    with (output_dir / "error_summary.csv").open(
            "w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=errors[0])
        writer.writeheader()
        writer.writerows(errors)

    failure = {
        str(threshold): {
            "coarse_s": failure_time(coarse["observations"], threshold),
            "fine_s": failure_time(fine["observations"], threshold),
        }
        for threshold in thresholds
    }
    for values in failure.values():
        coarse_time, fine_time = values["coarse_s"], values["fine_s"]
        values["relative_difference"] = (
            abs(coarse_time - fine_time) / fine_time
            if coarse_time is not None and fine_time not in (None, 0) else None
        )

    result = {
        "coarse": str(coarse_dir),
        "fine": str(fine_dir),
        "interval_s": [coarse["start_s"], coarse["end_s"]],
        "dt_s": [coarse["dt_s"], fine["dt_s"]],
        "common_times_s": times,
        "endpoint_full_P1": {
            "dofs": coarse_vector.size,
            "max_absolute_difference_K": float(np.max(np.abs(field_difference))),
            "l2_difference_K": float(np.linalg.norm(field_difference)),
        },
        "metric_errors": errors,
        "failure_times": failure,
        "sanity": {"coarse": sanity(coarse), "fine": sanity(fine)},
        "newton_iterations": [coarse["total_newton_iterations"],
                              fine["total_newton_iterations"]],
        "wall_time_s": [coarse.get("wall_time_s"), fine.get("wall_time_s")],
    }
    result["accepted"] = bool(
        all(row["pass"] is not False for row in errors)
        and all(item["finite"] and item["range_pass"]
                for item in result["sanity"].values())
    )
    (output_dir / "summary.json").write_text(
        json.dumps(result, indent=2) + "\n", encoding="utf-8"
    )

    fig, axes = plt.subplots(2, 1, figsize=(10, 9), sharex=True)
    styles = ((coarse, "--"), (fine, "-"))
    for summary, style in styles:
        rows = {round(row["time_s"], 12): row for row in summary["observations"]}
        for name, get_value in TEMPERATURES.items():
            axes[0].plot(times, [get_value(rows[time]) for time in times], style,
                         label=f"{name}, dt={summary['dt_s']:g} s")
        for name, get_value in FLOWS.items():
            axes[1].plot(times, [1e6 * get_value(rows[time]) for time in times], style,
                         label=f"{name}, dt={summary['dt_s']:g} s")
    axes[0].set_ylabel("Region-average temperature [K]")
    axes[1].set_ylabel("Heat flow [uW]")
    axes[1].set_xlabel("Absolute time [s]")
    for axis in axes:
        axis.grid(True, alpha=0.3)
        axis.legend(fontsize=8, ncol=2)
    fig.tight_layout()
    fig.savefig(output_dir / "comparison.png", dpi=180)
    plt.close(fig)

    lines = [
        "# ADR01 segment convergence",
        "",
        f"Interval: `{coarse['start_s']:g}–{coarse['end_s']:g} s`; "
        f"dt: `{coarse['dt_s']:g}` vs `{fine['dt_s']:g} s`.",
        "",
        f"Accepted under provisional gates: **{result['accepted']}**.",
        "",
        "| Metric | Max absolute difference | Relative to finer max | Pass |",
        "|---|---:|---:|---:|",
        *(f"| {row['metric']} | {row['max_absolute_difference']:.8g} | "
          f"{row['relative_to_fine_max']:.3%} | "
          f"{row['pass'] if row['pass'] is not None else 'informational'} |"
          if row["relative_to_fine_max"] is not None else
          f"| {row['metric']} | {row['max_absolute_difference']:.8g} | near zero | informational |"
          for row in errors),
        "",
        f"Endpoint full P1: max `{result['endpoint_full_P1']['max_absolute_difference_K']:.8g} K`, "
        f"L2 `{result['endpoint_full_P1']['l2_difference_K']:.8g} K`.",
    ]
    (output_dir / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return result


def audit_candidates(rows, thresholds, rng, random_count, seed):
    times = np.array([row["time_s"] for row in rows])
    sample = np.array([TEMPERATURES["sample_Tavg_K"](row) for row in rows])
    candidates = [(0, "segment_start")]
    if len(rows) > 2:
        candidates.append((len(rows) - 2, "near_segment_end"))
    slopes = np.diff(sample) / np.diff(times)
    candidates.append((int(np.argmax(np.abs(slopes))), "max_abs_sample_slope"))
    if len(rows) > 2:
        curvature = np.abs(np.diff(slopes) / np.diff(times[:-1]))
        candidates.append((int(np.argmax(curvature)) + 1,
                           "max_abs_sample_curvature"))
    for threshold in thresholds:
        candidates.append((int(np.argmin(np.abs(sample - threshold))),
                           f"nearest_threshold_{threshold:g}_K"))
    interior = list(range(1, len(rows) - 1))
    for index in rng.sample(interior, min(random_count, len(interior))):
        candidates.append((index, f"random_seed_{seed}"))
    return candidates


def select_audits(summary_paths, output, seed, random_count, thresholds):
    rng = random.Random(seed)
    selected = {}
    for summary_path in map(Path, summary_paths):
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
        rows = summary["observations"]
        if len(rows) < 2:
            raise ValueError(f"{summary_path} needs at least two observations")
        times = np.array([row["time_s"] for row in rows])
        candidates = audit_candidates(rows, thresholds, rng, random_count, seed)
        for index, reason in candidates:
            time = float(times[index])
            key = (str(summary_path), time)
            selected.setdefault(key, {
                "summary": str(summary_path),
                "time_s": time,
                "checkpoint": str(
                    summary_path.parent / f"checkpoint_t_{time:.8g}.npz"
                ),
                "reasons": [],
            })["reasons"].append(reason)
    result = {"seed": seed, "points": list(selected.values())}
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return result


def load_plan(path):
    """Load and validate a complete physical-trajectory execution plan."""
    path = Path(path)
    plan = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(plan, dict) or not isinstance(plan.get("scenario"), str):
        raise ValueError("plan requires a scenario string")
    scenario = plan["scenario"]
    if not scenario or Path(scenario).name != scenario or scenario in {".", ".."}:
        raise ValueError("scenario must be a non-empty directory name")
    segments = plan.get("segments")
    if not isinstance(segments, list) or not segments:
        raise ValueError("plan requires at least one segment")
    previous_end = None
    for index, segment in enumerate(segments):
        if not isinstance(segment, dict):
            raise ValueError(f"segment {index} must be a mapping")
        try:
            start, end, dt, cadence = map(
                float, (segment["start_s"], segment["end_s"], segment["dt_s"],
                        segment["output_every_s"])
            )
        except (KeyError, TypeError, ValueError) as error:
            raise ValueError(f"segment {index} has invalid numeric fields") from error
        if not np.isfinite([start, end, dt, cadence]).all():
            raise ValueError(f"segment {index} values must be finite")
        if index == 0 and not np.isclose(start, 0.0):
            raise ValueError("first segment must start at 0")
        if previous_end is not None and not np.isclose(start, previous_end):
            raise ValueError(f"segment {index} is not contiguous")
        if end <= start or dt <= 0 or cadence <= 0:
            raise ValueError(f"segment {index} requires end>start, dt>0, output cadence>0")
        if not np.isclose(round((end - start) / dt) * dt, end - start):
            raise ValueError(f"segment {index} duration is not an integer number of timesteps")
        if not np.isclose(round(cadence / dt) * dt, cadence):
            raise ValueError(f"segment {index} output cadence is not timestep-compatible")
        previous_end = end
    validation = plan.get("validation", {})
    if validation.get("mode", "warn") not in {"warn", "strict"}:
        raise ValueError("validation mode must be warn or strict")
    factor = float(validation.get("reference_dt_factor", 0.5))
    if not np.isfinite(factor) or factor <= 0 or factor >= 1:
        raise ValueError("reference_dt_factor must be between 0 and 1")
    for key in ("temperature_abs_K", "temperature_rel", "heat_flow_rel"):
        value = float(validation.get(key, {"temperature_abs_K": .01,
                                           "temperature_rel": .01,
                                           "heat_flow_rel": .05}[key]))
        if not np.isfinite(value) or value <= 0:
            raise ValueError(f"validation {key} must be finite and positive")
    return plan


def _write_production_summary(path, rows):
    fields = ["time_s", "segment", "solver_dt_s", "ggg_Tavg_K",
              "cold_stage_Tavg_K", "sample_Tavg_K", "support_1_heat_leak_W",
              "support_2_heat_leak_W", "switch_heat_flow_W", "newton_iterations",
              "trajectory_validation_state"]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def _merge_visualization(sources, destination):
    destination.mkdir(parents=True, exist_ok=True)
    datasets, seen_times = [], set()
    for segment_index, pvd in enumerate(sources):
        prefix = f"segment_{segment_index}_"
        root = ET.parse(pvd).getroot()
        for dataset in root.findall("./Collection/DataSet"):
            time = round(float(dataset.attrib["timestep"]), 12)
            if time in seen_times:
                continue
            seen_times.add(time)
            source_pvtu = pvd.parent / dataset.attrib["file"]
            target_pvtu = destination / (prefix + source_pvtu.name)
            pvtu = ET.parse(source_pvtu)
            for piece in pvtu.getroot().iter("Piece"):
                source_vtu = source_pvtu.parent / piece.attrib["Source"]
                target_vtu = destination / (prefix + source_vtu.name)
                shutil.copy2(source_vtu, target_vtu)
                piece.attrib["Source"] = target_vtu.name
            pvtu.write(target_pvtu, encoding="utf-8", xml_declaration=True)
            datasets.append({**dataset.attrib, "file": target_pvtu.name})
    vtk = ET.Element("VTKFile", type="Collection", version="1.0")
    collection = ET.SubElement(vtk, "Collection")
    for attributes in datasets:
        ET.SubElement(collection, "DataSet", attributes)
    ET.ElementTree(vtk).write(destination / "fields.pvd", encoding="utf-8",
                              xml_declaration=True)


def run_plan(plan_path, runner=None):
    """Execute production and dt-refinement branches as one simulation."""
    plan_path = Path(plan_path)
    plan = load_plan(plan_path)  # fail before importing the FEM runner
    if runner is None:
        from main import run as runner
    scenario_dir = CASE_DIR / "output" / plan["scenario"]
    if scenario_dir.exists():
        raise FileExistsError(f"Refusing to overwrite existing simulation: {scenario_dir}")
    scenario_dir.mkdir(parents=True)
    shutil.copy2(plan_path, scenario_dir / "plan.yaml")
    dump_dir, checkpoint_dir = scenario_dir / "dump", scenario_dir / "checkpoint"
    validation_root = scenario_dir / "validation"
    validation = plan.get("validation", {})
    mode = validation.get("mode", "warn")
    factor = float(validation.get("reference_dt_factor", 0.5))
    thresholds = validation.get("sample_temperature_thresholds_K", [1.5, 2.0, 3.0])
    rows, segment_records, pvd_sources, log_lines, validation_lines = [], [], [], [], []
    upstream_valid = True
    validated_through = 0.0
    restart = None
    stopped = False
    seen_times = set()
    for index, segment in enumerate(plan["segments"]):
        start, end, dt = map(float, (segment["start_s"], segment["end_s"], segment["dt_s"]))
        interval = f"{start:.8g}_to_{end:.8g}"
        evidence = validation_root / interval
        candidate_dir, reference_dir = evidence / "candidate", evidence / "reference"
        candidate = runner(
            dt, end, float(segment["output_every_s"]), restart, "segment", dt,
            candidate_dir, dump_dir, checkpoint_dir, "fields.pvd", True, index == 0,
        )
        reference = runner(
            dt * factor, end, float(segment["output_every_s"]), restart,
            "validation", dt * factor, reference_dir, None, None, "fields.pvd", True,
        )
        comparison = compare(candidate_dir, reference_dir, evidence, thresholds, validation)
        local_pass = comparison["accepted"]
        if local_pass and upstream_valid:
            state = "VALIDATED"
            validated_through = end
        elif local_pass:
            state = "LOCAL_PASS_BUT_UPSTREAM_UNVALIDATED"
        else:
            state = "LOCAL_VALIDATION_FAILED"
            upstream_valid = False
        segment_records.append({**segment, "local_validation_pass": local_pass,
                                "trajectory_validation_state": state})
        validation_lines.append(f"{start:g} to {end:g} s: {state}")
        if not local_pass:
            failed = [item["metric"] for item in comparison["metric_errors"]
                      if item["pass"] is False]
            warning = f"WARNING: validation failed for {start:g} to {end:g} s: {failed}"
            print(warning)
            log_lines.append(warning)
        for observation in candidate["observations"]:
            time = round(float(observation["time_s"]), 12)
            if time in seen_times:
                continue
            seen_times.add(time)
            rows.append({
                "time_s": observation["time_s"], "segment": index,
                "solver_dt_s": dt,
                **{name: getter(observation) for name, getter in TEMPERATURES.items()},
                "support_1_heat_leak_W": observation["support_1_heat_leak_W"],
                "support_2_heat_leak_W": observation["support_2_heat_leak_W"],
                "switch_heat_flow_W": observation["switch_heat_flow_W"],
                "newton_iterations": observation["newton_iterations"],
                "trajectory_validation_state": state,
            })
        pvd_sources.append(candidate_dir / "visualization" / "fields.pvd")
        restart = Path(candidate["checkpoint"])
        if not local_pass and mode == "strict":
            stopped = True
            log_lines.append("Strict mode stopped before downstream production; try a smaller timestep.")
            break
    _write_production_summary(scenario_dir / "summary.csv", rows)
    _merge_visualization(pvd_sources, scenario_dir / "visualization")
    (scenario_dir / "run.log").write_text("\n".join(log_lines) + "\n", encoding="utf-8")
    (scenario_dir / "validation.log").write_text(
        "\n".join(validation_lines) + "\n", encoding="utf-8"
    )
    case_data = yaml.safe_load((CASE_DIR / "case.yaml").read_text(encoding="utf-8"))
    last = candidate
    git_sha = subprocess.run(["git", "rev-parse", "HEAD"], cwd=CASE_DIR,
                             capture_output=True, text=True, check=True).stdout.strip()
    dirty = bool(subprocess.run(["git", "status", "--porcelain"], cwd=CASE_DIR,
                                capture_output=True, text=True, check=True).stdout)
    manifest = {
        "case": "ADR01 Baseline v1", "scenario": plan["scenario"],
        "start_s": 0.0, "end_s": float(last["end_s"]),
        "planned_end_s": float(plan["segments"][-1]["end_s"]),
        "mesh_id": last.get("mesh_id"), "cell_count": last.get("cell_count"),
        "temperature_dofs": last.get("temperature_dofs"),
        "geometry_reference": "geometry-requirement/",
        "initial_boundary_reference": "case.yaml",
        "material_reference": "parameters-requirement/ADR01_material_parameters_baseline_v1.md",
        "materials": list(case_data["materials"]),
        "copper_model": "OFHC_Cu_RRR100", "ggg_model": "GGG_H0",
        "support_model": "G10_FR4_axial_effective",
        "heat_switch_off_model": "Heat_switch_OFF_proxy",
        "heat_switch_off_conductance_W_K": 6.0e-5,
        "segments": segment_records, "validation": validation,
        "git_commit": git_sha, "git_dirty": dirty,
        "final_trajectory_validation_state": segment_records[-1]["trajectory_validation_state"],
        "validated_through_s": validated_through, "stopped_early": stopped,
    }
    (scenario_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )
    return manifest


def self_test():
    rows = [
        {"time_s": 1.0, "regions": {"sample": {"T_avg_K": 1.0}}},
        {"time_s": 3.0, "regions": {"sample": {"T_avg_K": 2.0}}},
    ]
    assert failure_time(rows, 1.5) == 2.0
    assert failure_time(rows, 3.0) is None
    samples = [0.0, 3.0, 4.0, 2.0]
    audit_rows = [
        {"time_s": float(index),
         "regions": {"sample": {"T_avg_K": value}}}
        for index, value in enumerate(samples)
    ]
    candidates = audit_candidates(
        audit_rows, (), random.Random(7), 2, 7
    )
    assert (2, "max_abs_sample_curvature") in candidates
    assert all(index not in (0, 3) for index, reason in candidates
               if reason.startswith("random_seed_"))
    assert metric_gate("switch_W", 0.0, 0.0, {}) == (
        None, None, "near_zero_absolute_diagnostic"
    )
    assert _trajectory_states([True, False, True]) == (
        ["VALIDATED", "LOCAL_VALIDATION_FAILED",
         "LOCAL_PASS_BUT_UPSTREAM_UNVALIDATED"], 1
    )
    assert len(load_plan(CASE_DIR / "baseline-v1.yaml")["segments"]) == 5
    with tempfile.NamedTemporaryFile("w", suffix=".yaml", delete=False) as handle:
        handle.write("scenario: bad\nsegments: [{start_s: 1, end_s: 2, dt_s: 1, output_every_s: 1}]\n")
        invalid_path = Path(handle.name)
    try:
        try:
            load_plan(invalid_path)
            raise AssertionError("invalid plan accepted")
        except ValueError:
            pass
    finally:
        invalid_path.unlink()
    print("workflow self-test: PASS")


def _trajectory_states(local_results):
    """Small pure helper used to regression-test accumulated validity."""
    states, upstream_valid, validated_count = [], True, 0
    for passed in local_results:
        if passed and upstream_valid:
            states.append("VALIDATED")
            validated_count += 1
        elif passed:
            states.append("LOCAL_PASS_BUT_UPSTREAM_UNVALIDATED")
        else:
            states.append("LOCAL_VALIDATION_FAILED")
            upstream_valid = False
    return states, validated_count


if __name__ == "__main__":
    parser = ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    comparison = subparsers.add_parser("compare")
    comparison.add_argument("coarse")
    comparison.add_argument("fine")
    comparison.add_argument("output")
    comparison.add_argument("--threshold", type=float, action="append",
                            default=[1.5, 2.0, 3.0])
    audits = subparsers.add_parser("select-audits")
    audits.add_argument("summaries", nargs="+")
    audits.add_argument("--output", required=True)
    audits.add_argument("--seed", type=int, default=20260914)
    audits.add_argument("--random-count", type=int, default=2)
    audits.add_argument("--threshold", type=float, action="append",
                        default=[1.5, 2.0, 3.0])
    subparsers.add_parser("self-test")
    run_command = subparsers.add_parser("run")
    run_command.add_argument("plan")
    args = parser.parse_args()
    if args.command == "compare":
        print(json.dumps(compare(args.coarse, args.fine, args.output,
                                 args.threshold), indent=2))
    elif args.command == "select-audits":
        print(json.dumps(select_audits(args.summaries, args.output, args.seed,
                                       args.random_count, args.threshold), indent=2))
    elif args.command == "self-test":
        self_test()
    else:
        print(json.dumps(run_plan(args.plan), indent=2))
