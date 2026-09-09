"""Read ADR Thermal LAMMPS-like cell dumps."""

from pathlib import Path

import numpy as np


def read_dump(path):
    lines = Path(path).read_text(encoding="utf-8").splitlines()
    metadata = {}
    index = 0
    fields = None
    while index < len(lines):
        header = lines[index]
        if not header.startswith("ITEM: "):
            raise ValueError(f"Expected ITEM header at line {index + 1}")
        key = header[6:]
        index += 1
        if key.startswith("FIELDS "):
            fields = key.split()[1:]
            break
        if key == "BOUNDS":
            metadata[key] = np.array(
                [[float(value) for value in lines[index + axis].split()]
                 for axis in range(3)]
            )
            index += 3
        elif key == "REGIONS":
            count = int(lines[index])
            index += 1
            metadata[key] = {
                int(lines[index + row].split(maxsplit=1)[0]):
                lines[index + row].split(maxsplit=1)[1]
                for row in range(count)
            }
            index += count
        else:
            if index >= len(lines):
                raise ValueError(f"Missing value for ITEM: {key}")
            metadata[key] = lines[index]
            index += 1

    if fields is None:
        raise ValueError("Dump has no FIELDS header")
    rows = [line.split() for line in lines[index:] if line.strip()]
    if len(rows) != int(metadata["NUMBER OF CELLS"]):
        raise ValueError("NUMBER OF CELLS does not match data rows")
    if any(len(row) != len(fields) for row in rows):
        raise ValueError("Data row does not match FIELDS")
    values = np.asarray(rows, dtype=float)
    return metadata, {
        field: values[:, column] for column, field in enumerate(fields)
    }


def read_dump_series(directory):
    paths = list(Path(directory).glob("*.dump"))
    frames = [read_dump(path) for path in paths]
    frames.sort(key=lambda frame: float(frame[0]["TIME"]))
    if not frames:
        raise ValueError(f"No dump files found in {directory}")
    mesh_ids = {metadata["MESH_ID"] for metadata, _ in frames}
    if len(mesh_ids) != 1:
        raise ValueError("Dump series contains more than one MESH_ID")
    return frames
