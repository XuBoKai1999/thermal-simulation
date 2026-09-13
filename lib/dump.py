"""Serialize prepared cell fields in ADR dump format v2."""

from pathlib import Path

import numpy as np


UNITS = {
    "x": "m",
    "y": "m",
    "z": "m",
    "T": "K",
    "qx": "W/m^2",
    "qy": "W/m^2",
    "qz": "W/m^2",
    "qmag": "W/m^2",
}


def write_dump(
    data, directory, fields, mesh_id, bounds, regions, timestep=0, time=0.0,
    solver_dt=None, characteristic_cell_size=None,
):
    if "cell_ID" not in fields:
        raise ValueError("cell_ID is required")
    unknown = [field for field in fields if field not in data]
    if unknown:
        raise ValueError(f"Unknown or unavailable dump fields: {unknown}")

    row_count = len(data["cell_ID"])
    if any(len(data[field]) != row_count for field in fields):
        raise ValueError("Dump fields have inconsistent lengths")
    if any(not np.isfinite(np.asarray(data[field])).all() for field in fields):
        raise ValueError("Dump fields contain NaN or Inf")
    for name, value in (
        ("solver_dt", solver_dt),
        ("characteristic_cell_size", characteristic_cell_size),
    ):
        if value is not None and (not np.isfinite(value) or value <= 0):
            raise ValueError(f"{name} must be finite and positive")

    order = np.argsort(data["cell_ID"])
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{timestep}.dump"
    units = " ".join(f"{field}={UNITS[field]}" for field in fields if field in UNITS)
    lines = [
        "ITEM: FORMAT_VERSION",
        "2",
        "ITEM: TIMESTEP",
        str(timestep),
        "ITEM: TIME",
        repr(float(time)),
        "ITEM: SOLVER_DT",
        "unknown" if solver_dt is None else repr(float(solver_dt)),
        "ITEM: CHARACTERISTIC_CELL_SIZE",
        ("unknown" if characteristic_cell_size is None
         else repr(float(characteristic_cell_size))),
        "ITEM: MESH_ID",
        mesh_id,
        "ITEM: NUMBER OF CELLS",
        str(row_count),
        "ITEM: BOX BOUNDS",
        *(f"{low:.16g} {high:.16g}" for low, high in bounds),
    ]
    if "region_ID" in fields:
        lines.extend(["ITEM: REGIONS", str(len(regions))])
        lines.extend(f"{region_id} {name}" for region_id, name in sorted(regions.items()))
    lines.extend(["ITEM: UNITS", units or "-", f"ITEM: FIELDS {' '.join(fields)}"])

    integer_fields = {"cell_ID", "region_ID"}
    for index in order:
        lines.append(
            " ".join(
                str(int(data[field][index]))
                if field in integer_fields
                else f"{float(data[field][index]):.16g}"
                for field in fields
            )
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    return path
