"""Plot one ADR thermal dump without running the FEM solver."""

import argparse
from pathlib import Path
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from lib.dump_reader import read_dump


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
