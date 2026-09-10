"""Material-property loading and region-field construction."""

import csv
import importlib.util
from pathlib import Path

import numpy as np
from dolfinx import fem
import ufl


PROPERTY_NAMES = ("k", "rho", "cp")


class Property:
    """A positive scalar property evaluated from temperature and future state."""

    def __init__(self, source, evaluator, domain=None):
        self.source = source
        self._evaluator = evaluator
        self.domain = domain

    @property
    def is_constant(self):
        return self.source == "constant"

    def evaluate(self, T=None, **state):
        value = self._evaluator(T, **state)
        numeric_input = T is None or isinstance(
            T, (int, float, np.number, np.ndarray)
        )
        if numeric_input:
            try:
                array = np.asarray(value, dtype=float)
            except (TypeError, ValueError) as error:
                raise ValueError("Material property must return numeric values") from error
            if not np.isfinite(array).all():
                raise ValueError("Material property returned a non-finite value")
            if (array <= 0).any():
                raise ValueError("Material property must be positive")
        return value


def _constant(value, name):
    if not isinstance(value, (int, float)) or not np.isfinite(value) or value <= 0:
        raise ValueError(f"{name} constant value must be finite and positive")
    return Property("constant", lambda T=None, **state: value)


def _table(definition, base_dir, name):
    for field in ("file", "x", "y"):
        if not isinstance(definition.get(field), str) or not definition[field]:
            raise ValueError(f"{name} table requires a non-empty {field}")
    path = base_dir / definition["file"]
    try:
        with path.open(encoding="utf-8", newline="") as file:
            rows = list(csv.DictReader(file))
    except OSError as error:
        raise ValueError(f"Cannot read {name} table {path}: {error}") from error
    try:
        x = np.asarray([float(row[definition["x"]]) for row in rows])
        y = np.asarray([float(row[definition["y"]]) for row in rows])
    except (KeyError, TypeError, ValueError) as error:
        raise ValueError(
            f"Invalid {name} table columns {definition['x']}/{definition['y']} in {path}"
        ) from error
    if len(x) < 2 or not np.isfinite(x).all() or not np.isfinite(y).all():
        raise ValueError(f"{name} table requires at least two finite rows")
    order = np.argsort(x)
    x, y = x[order], y[order]
    if (np.diff(x) <= 0).any():
        raise ValueError(f"{name} table temperature values must be unique")
    if (y <= 0).any():
        raise ValueError(f"{name} table values must be positive")

    def evaluate(T=None, **state):
        if T is None:
            raise ValueError(f"{name} table requires temperature T")
        if isinstance(T, (int, float, np.number, np.ndarray)):
            values = np.asarray(T, dtype=float)
            if not np.isfinite(values).all():
                raise ValueError(f"{name} temperature input must be finite")
            if (values < x[0]).any() or (values > x[-1]).any():
                raise ValueError(
                    f"{name} temperature is outside table domain [{x[0]}, {x[-1]}] K"
                )
            return np.interp(values, x, y)
        expression = y[-1]
        for index in range(len(x) - 2, -1, -1):
            line = y[index] + (y[index + 1] - y[index]) * (
                T - x[index]
            ) / (x[index + 1] - x[index])
            expression = ufl.conditional(T <= x[index + 1], line, expression)
        return expression

    return Property("table", evaluate, (float(x[0]), float(x[-1])))


def _python(definition, base_dir, name):
    for field in ("file", "function"):
        if not isinstance(definition.get(field), str) or not definition[field]:
            raise ValueError(f"{name} python property requires a non-empty {field}")
    path = base_dir / definition["file"]
    try:
        spec = importlib.util.spec_from_file_location(
            f"thermal_material_{path.stem}_{id(definition)}", path
        )
        if spec is None or spec.loader is None:
            raise ImportError("no Python module loader")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
    except Exception as error:
        raise ValueError(f"Cannot import {name} property from {path}: {error}") from error
    function = getattr(module, definition["function"], None)
    if not callable(function):
        raise ValueError(
            f"Python property {name} function {definition['function']!r} is missing"
        )
    return Property("python", lambda T=None, **state: function(T, **state))


def load_property(definition, base_dir, name="property"):
    """Load a constant, CSV table, or local Python material property."""
    base_dir = Path(base_dir)
    if isinstance(definition, (int, float)):
        return _constant(definition, name)
    if not isinstance(definition, dict):
        raise ValueError(f"{name} must be a number or property mapping")
    source = definition.get("type")
    if source == "constant":
        return _constant(definition.get("value"), name)
    if source == "table":
        return _table(definition, base_dir, name)
    if source == "python":
        return _python(definition, base_dir, name)
    raise ValueError(f"{name} has unsupported property type {source!r}")


def load_region_properties(case_data, base_dir):
    """Resolve region -> material -> property definitions once at case load."""
    material_definitions = case_data.get("materials", {})
    if not isinstance(material_definitions, dict):
        raise ValueError("materials must be a mapping")
    resolved = {}
    contact_regions = {
        contact["region"]: contact["thickness_m"] / contact["resistance_m2K_W"]
        for contact in case_data.get("contacts", {}).values()
    }
    for region_name, region in case_data["regions"].items():
        reference = region.get("material")
        if reference == "local":
            resolved[region_name] = None
            continue
        if reference is not None:
            if reference not in material_definitions:
                raise ValueError(f"Region {region_name} names unknown material {reference!r}")
            definitions = material_definitions[reference]
        else:
            definitions = region
        if not isinstance(definitions, dict):
            raise ValueError(f"Material for region {region_name} must be a mapping")
        properties = {
            prop_name: load_property(value, base_dir, f"{region_name}.{prop_name}")
            for prop_name, value in definitions.items() if prop_name in PROPERTY_NAMES
        }
        if region_name in contact_regions:
            properties["k"] = _constant(contact_regions[region_name], f"{region_name}.k")
        resolved[region_name] = properties
    return resolved


def validate(material, names):
    missing = [name for name in names if not callable(getattr(material, name, None))]
    if missing:
        raise ValueError(f"Local material must define callable: {', '.join(missing)}")


def property_field(mesh_data, case_data, semantic_tags, name):
    """Build one piecewise-constant DG0 property field from region tags."""
    domain = mesh_data.mesh
    space = fem.functionspace(domain, ("DG", 0))
    field = fem.Function(space)
    field.x.array[:] = np.nan
    for region_name, properties in case_data["_region_properties"].items():
        if properties is None or name not in properties:
            continue
        prop = properties[name]
        if not prop.is_constant:
            raise ValueError(f"{region_name}.{name} is temperature-dependent")
        value = prop.evaluate()
        tag = semantic_tags[region_name]["tag"]
        for cell in mesh_data.cell_tags.find(tag):
            field.x.array[space.dofmap.cell_dofs(cell)[0]] = value
    owned = space.dofmap.index_map.size_local
    if not np.isfinite(field.x.array[:owned]).all():
        raise ValueError(f"Every mesh cell must have a constant {name} property")
    field.x.scatter_forward()
    return field


def conductivity_field(mesh_data, case_data, semantic_tags):
    return property_field(mesh_data, case_data, semantic_tags, "k")
