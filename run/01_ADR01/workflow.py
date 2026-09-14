"""Compare ADR01 timestep branches and select reproducible local audit points."""

from argparse import ArgumentParser
import csv
import json
from pathlib import Path
import random

import matplotlib.pyplot as plt
import numpy as np


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


def load_run(directory):
    directory = Path(directory)
    summary = json.loads((directory / "summary.json").read_text(encoding="utf-8"))
    checkpoint = np.load(
        directory / Path(summary["checkpoint"]).name, allow_pickle=False
    )
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


def compare(coarse_dir, fine_dir, output_dir, thresholds):
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
        relative = max_absolute / scale if scale else None
        passed = (
            None if name == "ggg_Tavg_K" else
            (max_absolute < 0.01 or relative < 0.01) if name in TEMPERATURES else
            relative < 0.05
        )
        errors.append({
            "metric": name,
            "max_absolute_difference": max_absolute,
            "relative_to_fine_max": relative,
            "gate": "informational" if passed is None else "acceptance",
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
    print("workflow self-test: PASS")


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
    args = parser.parse_args()
    if args.command == "compare":
        print(json.dumps(compare(args.coarse, args.fine, args.output,
                                 args.threshold), indent=2))
    elif args.command == "select-audits":
        print(json.dumps(select_audits(args.summaries, args.output, args.seed,
                                       args.random_count, args.threshold), indent=2))
    else:
        self_test()
