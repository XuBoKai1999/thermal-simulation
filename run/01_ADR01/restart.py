"""Continue ADR01 Baseline v1 from its trusted 420 s checkpoint."""

import csv
from datetime import datetime
import json
from pathlib import Path
import subprocess
import sys
from time import perf_counter

import numpy as np


CASE_DIR = Path(__file__).resolve().parent
ROOT = CASE_DIR.parents[1]
sys.path.insert(0, str(ROOT))

from lib.log import RunLog
from main import run as run_segment


PARENT_SCENARIO = "baseline-v1"
CHILD_SCENARIO = "baseline-v1-cont-420s-1800s"
RESTART_TIME_S = 420.0
DT_S = 2.0
SUMMARY_EVERY_S = 2.0
OUTPUT_EVERY_S = 10.0
PROGRESS_EVERY = 10
CONTINUITY_FIELDS = (
    "ggg_Tavg_K", "cold_stage_Tavg_K", "sample_Tavg_K",
    "support_1_heat_leak_W", "support_2_heat_leak_W", "switch_heat_flow_W",
)


def run_continuation(scenario=CHILD_SCENARIO, end_time=1800.0):
    started = perf_counter()
    started_at = datetime.now().astimezone().isoformat(timespec="seconds")
    parent_dir = CASE_DIR / "output" / PARENT_SCENARIO
    child_dir = CASE_DIR / "output" / scenario
    parent_manifest_path = parent_dir / "manifest.json"
    checkpoint_path = parent_dir / "checkpoint" / "t_420s.npz"
    parent_summary_path = parent_dir / "summary.csv"
    if child_dir.exists():
        raise FileExistsError(f"Refusing to overwrite existing continuation: {child_dir}")

    terminal_log = RunLog(PROGRESS_EVERY)
    try:
        if not parent_manifest_path.is_file():
            raise FileNotFoundError(f"Missing parent manifest: {parent_manifest_path}")
        if not checkpoint_path.is_file():
            raise FileNotFoundError(f"Missing restart checkpoint: {checkpoint_path}")
        parent = json.loads(parent_manifest_path.read_text(encoding="utf-8"))
        build = json.loads((CASE_DIR / "build" / "build.json").read_text(encoding="utf-8"))
        if parent["mesh_id"] != build["mesh_id"]:
            raise ValueError("Parent mesh_id does not match the current mesh")
        with np.load(checkpoint_path, allow_pickle=False) as checkpoint:
            if int(checkpoint["format_version"]) != 1:
                raise ValueError("Unsupported checkpoint format")
            if not np.isclose(float(checkpoint["time_s"]), RESTART_TIME_S):
                raise ValueError("Checkpoint time is not 420 s")
            if str(checkpoint["mesh_id"]) != build["mesh_id"]:
                raise ValueError("Checkpoint mesh_id does not match the current mesh")
            temperatures = checkpoint["temperature"]
            if temperatures.shape != (int(parent["temperature_dofs"]),):
                raise ValueError("Checkpoint temperature vector shape is incompatible")
            if not np.isfinite(temperatures).all():
                raise ValueError("Checkpoint temperatures are non-finite")
        if float(parent["end_s"]) < RESTART_TIME_S:
            raise ValueError("Parent trajectory does not reach 420 s")
        if float(parent["validated_through_s"]) < RESTART_TIME_S:
            raise ValueError("Parent trajectory is not validated through 420 s")
        with parent_summary_path.open(encoding="utf-8", newline="") as handle:
            parent_row = list(csv.DictReader(handle))[-1]
        if not np.isclose(float(parent_row["time_s"]), RESTART_TIME_S):
            raise ValueError("Parent summary does not end at 420 s")
    except Exception as error:
        terminal_log.event("ERROR", f"continuation compatibility | {error}")
        raise

    git_commit = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=CASE_DIR, capture_output=True,
        text=True, check=True,
    ).stdout.strip()
    git_dirty = bool(subprocess.run(
        ["git", "status", "--porcelain"], cwd=CASE_DIR, capture_output=True,
        text=True, check=True,
    ).stdout)
    child_dir.mkdir(parents=True)
    logger = RunLog(PROGRESS_EVERY, path=child_dir / "run.log")
    logger.event("START", f"continuation | {RESTART_TIME_S:g} to {end_time:g} s")
    continuity = {"status": "NOT_CHECKED"}

    def check_initial(observation):
        current = {
            "ggg_Tavg_K": observation["regions"]["ggg"]["T_avg_K"],
            "cold_stage_Tavg_K": observation["regions"]["cold_stage"]["T_avg_K"],
            "sample_Tavg_K": observation["regions"]["sample"]["T_avg_K"],
            "support_1_heat_leak_W": observation["support_1_heat_leak_W"],
            "support_2_heat_leak_W": observation["support_2_heat_leak_W"],
            "switch_heat_flow_W": observation["switch_heat_flow_W"],
        }
        failed = [
            name for name in CONTINUITY_FIELDS
            if not np.isclose(current[name], float(parent_row[name]), rtol=1e-12, atol=1e-12)
        ]
        if failed:
            continuity["status"] = "FAIL"
            logger.event("ERROR", f"restart continuity | mismatched fields={failed}")
            raise ValueError(f"Restart continuity failed: {failed}")
        continuity["status"] = "PASS"
        logger.event("PASS", "restart continuity")
        logger.event("START", "production")

    try:
        result = run_segment(
            DT_S, end_time, OUTPUT_EVERY_S, checkpoint_path, "segment",
            SUMMARY_EVERY_S, child_dir, child_dir / "dump",
            child_dir / "checkpoint", "fields.pvd", True, True, logger,
            "continuation production", PROGRESS_EVERY,
            initial_observation_check=check_initial,
        )
    except Exception as error:
        if continuity["status"] != "FAIL":
            logger.event("ERROR", f"continuation production | {error}")
        raise
    logger.event("DONE", f"production | wall={result['wall_time_s']:.1f} s")

    fields = [
        "time_s", "solver_dt_s", "ggg_Tavg_K", "cold_stage_Tavg_K",
        "sample_Tavg_K", "support_1_heat_leak_W", "support_2_heat_leak_W",
        "switch_heat_flow_W", "newton_iterations", "trajectory_validation_state",
    ]
    with (child_dir / "summary.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for observation in result["observations"]:
            writer.writerow({
                "time_s": observation["time_s"], "solver_dt_s": DT_S,
                "ggg_Tavg_K": observation["regions"]["ggg"]["T_avg_K"],
                "cold_stage_Tavg_K": observation["regions"]["cold_stage"]["T_avg_K"],
                "sample_Tavg_K": observation["regions"]["sample"]["T_avg_K"],
                "support_1_heat_leak_W": observation["support_1_heat_leak_W"],
                "support_2_heat_leak_W": observation["support_2_heat_leak_W"],
                "switch_heat_flow_W": observation["switch_heat_flow_W"],
                "newton_iterations": observation["newton_iterations"],
                "trajectory_validation_state": "NOT_PERFORMED",
            })
    (child_dir / "summary.json").unlink(missing_ok=True)
    total_wall_time = perf_counter() - started
    finished_at = datetime.now().astimezone().isoformat(timespec="seconds")
    manifest = {
        "case": parent["case"], "scenario": scenario,
        "start_s": RESTART_TIME_S, "end_s": end_time, "planned_end_s": end_time,
        "parent_scenario": PARENT_SCENARIO,
        "parent_manifest": str(parent_manifest_path),
        "restart_checkpoint": str(checkpoint_path),
        "restart_time_s": RESTART_TIME_S,
        "parent_git_commit": parent["git_commit"],
        "parent_validated_through_s": parent["validated_through_s"],
        "restart_continuity_status": continuity["status"],
        "dt_s": DT_S, "summary_every_s": SUMMARY_EVERY_S,
        "output_every_s": OUTPUT_EVERY_S,
        "validation_status": "NOT_PERFORMED",
        "validated_through_s": RESTART_TIME_S,
        "mesh_id": result["mesh_id"], "cell_count": result["cell_count"],
        "temperature_dofs": result["temperature_dofs"],
        "geometry_reference": parent["geometry_reference"],
        "initial_boundary_reference": parent["initial_boundary_reference"],
        "material_reference": parent["material_reference"],
        "materials": parent["materials"],
        "git_commit": git_commit, "git_dirty": git_dirty,
        "total_wall_time_s": total_wall_time,
        "started_at": started_at, "finished_at": finished_at,
    }
    (child_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )
    logger.event(
        "DONE", f"continuation | wall={total_wall_time:.1f} s | "
        f"validated_through_s={RESTART_TIME_S:g}"
    )
    return manifest


if __name__ == "__main__":
    print(json.dumps(run_continuation(), indent=2))
