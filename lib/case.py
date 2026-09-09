"""Load and validate simulation cases."""

from pathlib import Path

import yaml


def load_case(path):
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("case.yaml must contain a mapping")
    model_type = data.get("model", {}).get("type")
    if model_type not in {"steady_conduction", "transient_conduction"}:
        raise ValueError("Unsupported model.type")

    regions = data.get("regions", {})
    if len(regions) != 1:
        raise ValueError("Stage 2 requires exactly one material region")
    conductivity = next(iter(regions.values())).get("k")
    if not isinstance(conductivity, (int, float)) or conductivity <= 0:
        raise ValueError("Region conductivity k must be positive")
    if model_type == "transient_conduction":
        region = next(iter(regions.values()))
        for name in ("rho", "cp"):
            if not isinstance(region.get(name), (int, float)) or region[name] <= 0:
                raise ValueError(f"Region {name} must be positive")
        time = data.get("time", {})
        for name in ("dt_s", "end_s"):
            if not isinstance(time.get(name), (int, float)) or time[name] <= 0:
                raise ValueError(f"time.{name} must be positive")
        initial = time.get("initial_condition", {})
        for name in ("split_x_m", "left_T_K", "right_T_K"):
            if not isinstance(initial.get(name), (int, float)):
                raise ValueError(f"time.initial_condition.{name} must be numeric")

    conditions = data.get("boundary_conditions", {})
    if len(conditions) != 2:
        raise ValueError("Stage 2 requires exactly two boundary conditions")
    for name, condition in conditions.items():
        if condition.get("type") != "fixed_temperature":
            raise ValueError(f"{name} must be a fixed_temperature condition")
        if not isinstance(condition.get("value_K"), (int, float)):
            raise ValueError(f"{name}.value_K must be numeric")
    return data


def load_expected(path):
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    tolerances = data.get("tolerances", {}) if isinstance(data, dict) else {}
    required = {"temperature_K", "heat_flux_W_m2", "total_heat_W"}
    if set(tolerances) != required:
        raise ValueError(f"expected.yaml tolerances must be {sorted(required)}")
    if any(
        not isinstance(value, (int, float)) or value <= 0
        for value in tolerances.values()
    ):
        raise ValueError("All tolerances must be positive numbers")
    return data
