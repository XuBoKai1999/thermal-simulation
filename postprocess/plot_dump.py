"""Plot one ADR thermal dump without running the FEM solver."""

import argparse
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
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
                [[float(value) for value in lines[index + axis].split()] for axis in range(3)]
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
    return metadata, {field: values[:, column] for column, field in enumerate(fields)}


def plot_field(data, field, ylabel, path, time):
    if "x" not in data or field not in data:
        raise ValueError(f"Dump must contain x and {field}")
    figure, axis = plt.subplots(figsize=(7, 4))
    axis.scatter(data["x"], data[field], s=10)
    axis.set(xlabel="x (m)", ylabel=ylabel, title=f"{field} at t = {time} s")
    field_values = data[field]
    span = np.ptp(field_values)
    scale = max(abs(field_values.mean()), 1.0)
    if span < scale * 1.0e-8:
        margin = scale * 0.01
        axis.set_ylim(field_values.mean() - margin, field_values.mean() + margin)
    axis.ticklabel_format(axis="y", style="plain", useOffset=False)
    axis.grid(alpha=0.3)
    figure.tight_layout()
    figure.savefig(path, dpi=160)
    plt.close(figure)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dump", type=Path)
    parser.add_argument("-o", "--output-dir", type=Path)
    args = parser.parse_args()

    metadata, data = read_dump(args.dump)
    output_dir = args.output_dir or args.dump.parent.parent / "plots"
    output_dir.mkdir(parents=True, exist_ok=True)
    plot_field(data, "T", "T (K)", output_dir / "temperature.png", metadata["TIME"])
    plot_field(
        data,
        "qmag",
        "|q| (W/m²)",
        output_dir / "heat_flux_magnitude.png",
        metadata["TIME"],
    )
    print(output_dir / "temperature.png")
    print(output_dir / "heat_flux_magnitude.png")


if __name__ == "__main__":
    main()
