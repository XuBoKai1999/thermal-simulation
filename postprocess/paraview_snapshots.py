"""Render physical-time PNG snapshots from one or more PVD series."""

import argparse
import json
import math
from pathlib import Path
import xml.etree.ElementTree as ET


def load_job(path):
    text = path.read_text(encoding="utf-8")
    try:
        job = json.loads(text)
    except json.JSONDecodeError:
        try:
            import yaml
        except ImportError as error:
            raise RuntimeError("YAML jobs require PyYAML; JSON works without it") from error
        job = yaml.safe_load(text)
    if not isinstance(job, dict):
        raise ValueError("Snapshot job must be a mapping")
    for key in ("state", "sources", "times", "output_dir", "resolution"):
        if key not in job:
            raise ValueError(f"Snapshot job requires {key}")
    if len(job["resolution"]) != 2 or any(int(value) <= 0 for value in job["resolution"]):
        raise ValueError("resolution must contain two positive integers")
    if "color_range" in job:
        if "coloring" not in job or len(job["color_range"]) != 2:
            raise ValueError("color_range requires coloring and two limits")
        low, high = map(float, job["color_range"])
        if not (math.isfinite(low) and math.isfinite(high) and low < high):
            raise ValueError("color_range must be finite and increasing")
    return job


def pvd_times(path):
    times = []
    for dataset in ET.parse(path).getroot().iter("DataSet"):
        if "timestep" in dataset.attrib:
            times.append(float(dataset.attrib["timestep"]))
    if not times or not all(math.isfinite(time) for time in times):
        raise ValueError(f"PVD has no valid timesteps: {path}")
    return times


def same_time(left, right):
    return math.isclose(left, right, rel_tol=1.0e-10, abs_tol=1.0e-12)


def build_plan(job, job_dir):
    sources = []
    for value in job["sources"]:
        path = (job_dir / value).resolve()
        if not path.is_file():
            raise FileNotFoundError(path)
        sources.append((path, pvd_times(path)))
    requested = sorted(float(value) for value in job["times"])
    if not requested or not all(math.isfinite(time) for time in requested):
        raise ValueError("times must contain finite physical times")
    unique = []
    for time in requested:
        if not unique or not same_time(time, unique[-1]):
            unique.append(time)
    plan = []
    for requested_time in unique:
        matches = [
            (source, actual)
            for source, available in sources for actual in available
            if same_time(requested_time, actual)
        ]
        if not matches:
            raise ValueError(f"No source timestep matches t={requested_time:g} s")
        plan.append((matches[0][0], matches[0][1]))
    return plan


def time_name(time):
    return f"{time:.12g}".replace("-", "m").replace(".", "p").replace("+", "")


def find_reader(simple, name=None):
    if name:
        reader = simple.FindSource(name)
        if reader is None:
            raise ValueError(f"ParaView state has no source named {name!r}")
        return reader
    readers = [proxy for proxy in simple.GetSources().values()
               if proxy.GetProperty("FileName") is not None]
    if len(readers) != 1:
        raise ValueError("State must contain one file reader, or job must set reader")
    return readers[0]


def render(job_path, check_only=False):
    job_path = job_path.resolve()
    job = load_job(job_path)
    plan = build_plan(job, job_path.parent)
    output_dir = (job_path.parent / job["output_dir"]).resolve()
    targets = [output_dir / f"frame_{index:04d}_t_{time_name(time)}s.png"
               for index, (_, time) in enumerate(plan)]
    if any(path.exists() for path in targets):
        raise FileExistsError("Refusing to overwrite an existing snapshot")
    if check_only:
        for target, (source, time) in zip(targets, plan):
            print(f"{time:g} s | {source} | {target}")
        return

    from paraview import simple

    state = (job_path.parent / job["state"]).resolve()
    if not state.is_file():
        raise FileNotFoundError(state)
    simple.LoadState(str(state))
    view = simple.GetActiveView()
    if view is None:
        raise ValueError("ParaView state has no active render view")
    reader = find_reader(simple, job.get("reader"))
    scene = simple.GetAnimationScene()
    resolution = [int(value) for value in job["resolution"]]
    output_dir.mkdir(parents=True, exist_ok=True)
    current_source = None
    for target, (source, time) in zip(targets, plan):
        if source != current_source:
            reader.FileName = str(source)
            reader.UpdateVTKObjects()
            reader.UpdatePipelineInformation()
            scene.UpdateAnimationUsingDataTimeSteps()
            current_source = source
        scene.AnimationTime = time
        view.ViewTime = time
        reader.UpdatePipeline(time)
        if "color_range" in job:
            low, high = map(float, job["color_range"])
            lut = simple.GetColorTransferFunction(job["coloring"])
            lut.RescaleTransferFunction(low, high)
            if lut.GetProperty("AutomaticRescaleRangeMode") is not None:
                lut.AutomaticRescaleRangeMode = "Never"
            simple.GetOpacityTransferFunction(job["coloring"]).RescaleTransferFunction(
                low, high
            )
        simple.Render(view)
        simple.SaveScreenshot(str(target), view, ImageResolution=resolution)
        print(target)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("job", type=Path)
    parser.add_argument("--check", action="store_true",
                        help="validate and print the frame plan without ParaView")
    args = parser.parse_args()
    render(args.job, args.check)


if __name__ == "__main__":
    main()
