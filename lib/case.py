"""Load and validate simulation cases."""

from pathlib import Path

import yaml

from . import materials


def load_case(path):
    path = Path(path)
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("case.yaml must contain a mapping")
    model_type = data.get("model", {}).get("type")
    if model_type not in {"steady_conduction", "transient_conduction"}:
        raise ValueError("Unsupported model.type")

    regions = data.get("regions", {})
    if not regions:
        raise ValueError("regions must contain at least one material region")
    contacts = data.get("contacts", {})
    if not isinstance(contacts, dict):
        raise ValueError("contacts must be a mapping")
    contact_regions = set()
    for name, contact in contacts.items():
        if contact.get("type") != "thin_layer_resistance":
            raise ValueError(f"{name} must use thin_layer_resistance")
        if contact.get("region") not in regions:
            raise ValueError(f"{name}.region must name a configured region")
        for field in ("resistance_m2K_W", "thickness_m"):
            if not isinstance(contact.get(field), (int, float)) or contact[field] <= 0:
                raise ValueError(f"{name}.{field} must be positive")
        contact_regions.add(contact["region"])
    local_regions = []
    for name, region in regions.items():
        local_material = region.get("material") == "local"
        if local_material:
            local_regions.append(name)
    if local_regions and (len(regions) != 1 or contacts):
        raise ValueError("Local material requires one region and no contacts in v1")
    data["_region_properties"] = materials.load_region_properties(data, path.parent)
    for region_name, properties in data["_region_properties"].items():
        if properties is None:
            continue
        if "k" not in properties:
            raise ValueError(f"Region {region_name} requires k")
        required = ("k", "rho", "cp") if model_type == "transient_conduction" else ("k",)
        missing = [name for name in required if name not in properties]
        if missing:
            raise ValueError(f"Region {region_name} requires {', '.join(missing)}")
        if model_type == "transient_conduction" and any(
            not properties[name].is_constant for name in required
        ):
            raise ValueError(
                "temperature-dependent property in transient model is not yet supported"
            )
    temperature_dependent_k = [
        name for name, properties in data["_region_properties"].items()
        if properties is not None and not properties["k"].is_constant
    ]
    if temperature_dependent_k and (len(regions) != 1 or contacts):
        raise ValueError(
            "Temperature-dependent conductivity supports one region and no contacts"
        )
    if model_type == "transient_conduction":
        if contacts:
            raise ValueError("Transient conduction does not support contacts")
        if local_regions:
            raise ValueError(
                "temperature-dependent property in transient model is not yet supported"
            )
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
    temperatures = [condition["value_K"] for condition in conditions.values()]
    if model_type == "transient_conduction":
        initial = data["time"]["initial_condition"]
        temperatures.extend((initial["left_T_K"], initial["right_T_K"]))
    for region_name, properties in data["_region_properties"].items():
        if properties is None:
            continue
        for property_name, prop in properties.items():
            if not prop.is_constant:
                for temperature in temperatures:
                    try:
                        prop.evaluate(temperature)
                    except Exception as error:
                        raise ValueError(
                            f"Invalid {region_name}.{property_name} at {temperature} K: {error}"
                        ) from error
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
