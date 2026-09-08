"""Load and validate simulation cases."""

from pathlib import Path

import yaml


def load_case(path):
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("case.yaml must contain a mapping")
    if data.get("model", {}).get("type") != "steady_conduction":
        raise ValueError("Only model.type=steady_conduction is supported")

    regions = data.get("regions", {})
    if len(regions) != 1:
        raise ValueError("Stage 2 requires exactly one material region")
    conductivity = next(iter(regions.values())).get("k")
    if not isinstance(conductivity, (int, float)) or conductivity <= 0:
        raise ValueError("Region conductivity k must be positive")

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
