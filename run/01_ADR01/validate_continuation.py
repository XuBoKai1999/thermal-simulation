"""Post-validate the completed 420-1800 s continuation with dt/2."""

import csv
import json
from pathlib import Path
import shutil
import sys

import numpy as np


CASE_DIR = Path(__file__).resolve().parent
ROOT = CASE_DIR.parents[1]
sys.path.insert(0, str(ROOT))

from lib.log import RunLog
from main import run
from workflow import compare


SCENARIO = "baseline-v1-cont-420s-1800s"
VALIDATION = f"{SCENARIO}-dt-validation"
PROGRESS_EVERY = 10


def candidate_summary(scenario_dir, manifest, destination):
    observations = []
    with (scenario_dir / "summary.csv").open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    for row in rows:
        time = float(row["time_s"])
        checkpoint = scenario_dir / "checkpoint" / f"t_{time:g}s.npz"
        if not checkpoint.is_file():
            raise FileNotFoundError(f"Missing production checkpoint: {checkpoint}")
        with np.load(checkpoint, allow_pickle=False) as state:
            temperatures = state["temperature"]
            if not np.isfinite(temperatures).all():
                raise ValueError(f"Non-finite production checkpoint: {checkpoint}")
            minimum, maximum = float(temperatures.min()), float(temperatures.max())
        observations.append({
            "time_s": time,
            "T_min": minimum,
            "T_max": maximum,
            "regions": {
                "ggg": {"T_avg_K": float(row["ggg_Tavg_K"])},
                "cold_stage": {"T_avg_K": float(row["cold_stage_Tavg_K"])},
                "sample": {"T_avg_K": float(row["sample_Tavg_K"])},
            },
            "support_1_heat_leak_W": float(row["support_1_heat_leak_W"]),
            "support_2_heat_leak_W": float(row["support_2_heat_leak_W"]),
            "switch_heat_flow_W": float(row["switch_heat_flow_W"]),
            "newton_iterations": int(row["newton_iterations"]),
        })

    endpoint = scenario_dir / "checkpoint" / f"t_{float(manifest['end_s']):g}s.npz"
    destination.mkdir()
    shutil.copy2(endpoint, destination / endpoint.name)
    summary = {
        "dt_s": float(manifest["dt_s"]),
        "start_s": float(manifest["start_s"]),
        "end_s": float(manifest["end_s"]),
        "checkpoint": endpoint.name,
        "total_newton_iterations": sum(row["newton_iterations"] for row in observations),
        "wall_time_s": manifest.get("total_wall_time_s"),
        "observations": observations,
    }
    (destination / "summary.json").write_text(
        json.dumps(summary, indent=2) + "\n", encoding="utf-8"
    )


def main():
    scenario_dir = CASE_DIR / "output" / SCENARIO
    validation_dir = CASE_DIR / "output" / VALIDATION
    if validation_dir.exists():
        raise FileExistsError(f"Refusing to overwrite existing validation: {validation_dir}")
    manifest_path = scenario_dir / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if (float(manifest["start_s"]), float(manifest["end_s"]), float(manifest["dt_s"])) != (420.0, 1800.0, 2.0):
        raise ValueError("Continuation manifest is not the expected 420-1800 s, dt=2 s run")
    if manifest["restart_continuity_status"] != "PASS":
        raise ValueError("Continuation restart continuity has not passed")
    restart = CASE_DIR / manifest["restart_checkpoint"]
    if not restart.is_file():
        raise FileNotFoundError(f"Missing restart checkpoint: {restart}")

    validation_dir.mkdir(parents=True)
    logger = RunLog(PROGRESS_EVERY, path=validation_dir / "run.log")
    logger.event("START", "continuation dt/2 validation | dt=2 vs 1 s")
    try:
        candidate_dir = validation_dir / "candidate"
        reference_dir = validation_dir / "reference"
        candidate_summary(scenario_dir, manifest, candidate_dir)
        logger.event("START", "reference | 420 to 1800 s | dt=1 s")
        reference = run(
            1.0, 1800.0, 10.0, restart, "validation", 2.0,
            reference_dir, reference_dir / "dump", reference_dir / "checkpoint",
            "fields.pvd", True, True, logger, "continuation reference",
            PROGRESS_EVERY,
        )
        logger.event("DONE", f"reference | wall={reference['wall_time_s']:.1f} s")
        result = compare(
            candidate_dir, reference_dir, validation_dir, [1.5, 2.0, 3.0],
            {"temperature_abs_K": 0.01, "temperature_rel": 0.01,
             "heat_flow_rel": 0.05},
        )
        manifest["validation_status"] = "PASS" if result["accepted"] else "FAIL"
        manifest["validated_through_s"] = 1800.0 if result["accepted"] else 420.0
        manifest["validation_evidence"] = validation_dir.relative_to(CASE_DIR).as_posix()
        manifest["validation_dt_s"] = [2.0, 1.0]
        manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
        logger.event("PASS" if result["accepted"] else "WARNING",
                     "continuation dt/2 validation")
        if not result["accepted"]:
            raise SystemExit(1)
    except BaseException as error:
        if not isinstance(error, SystemExit):
            logger.event("ERROR", f"continuation dt/2 validation | {error}")
        raise


if __name__ == "__main__":
    main()
