"""Plot transient temperature and heat-flux profiles from existing dumps."""

from pathlib import Path
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import yaml


PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from lib.dump_reader import read_dump_series


def analytic_temperature(x, t, L, rho, c, k, tolerance=1.0e-13):
    x = np.asarray(x, dtype=float)
    if t == 0:
        return np.where(x < L / 2, 4.0, 1.0)
    alpha = k / (rho * c)
    beta = alpha * (2 * np.pi / L) ** 2 * t
    terms = max(1, int(np.ceil(np.sqrt(-np.log(tolerance) / beta))))
    result = 4.0 - 3.0 * x / L
    for m in range(1, terms + 1):
        result += (3 * (-1) ** (m + 1) / (m * np.pi)
                   * np.sin(2 * m * np.pi * x / L) * np.exp(-beta * m * m))
    return result


def analytic_heat_flux(x, t, L, rho, c, k, tolerance=1.0e-13):
    if t <= 0:
        raise ValueError("Heat flux is not compared at t=0")
    x = np.asarray(x, dtype=float)
    alpha = k / (rho * c)
    beta = alpha * (2 * np.pi / L) ** 2 * t
    terms = max(1, int(np.ceil(np.sqrt(-np.log(tolerance) / beta))))
    series = np.zeros_like(x)
    for m in range(1, terms + 1):
        series += ((-1) ** (m + 1) * np.cos(2 * m * np.pi * x / L)
                   * np.exp(-beta * m * m))
    return 3 * k / L - 6 * k / L * series


def cross_section_average(data, edges, field):
    bins = np.clip(np.digitize(data["x"], edges) - 1, 0, len(edges) - 2)
    x = []
    values = []
    for index in range(len(edges) - 1):
        selected = bins == index
        if np.any(selected):
            x.append(np.mean(data["x"][selected]))
            values.append(np.mean(data[field][selected]))
    return np.asarray(x), np.asarray(values)


def main():
    case_dir = Path(__file__).resolve().parent
    output = case_dir / "validation"
    output.mkdir(exist_ok=True)
    case = yaml.safe_load((case_dir / "case.yaml").read_text(encoding="utf-8"))
    material = next(iter(case["regions"].values()))
    rho, c, k = (material[name] for name in ("rho", "cp", "k"))
    frames = read_dump_series(case_dir / "output" / "dump")
    by_time = {float(metadata["TIME"]): data for metadata, data in frames}
    selected_times = [time for time in (0, 1, 2, 5, 10, 20, 500) if time in by_time]
    L = float(frames[0][0]["BOUNDS"][0, 1] - frames[0][0]["BOUNDS"][0, 0])
    dense_x = np.linspace(0, L, 800)
    edges = np.linspace(0, L, 41)
    colors = plt.cm.plasma(np.linspace(0.05, 0.9, len(selected_times)))

    figure, axis = plt.subplots(figsize=(8, 5.2))
    for color, time in zip(colors, selected_times):
        data = by_time[time]
        x, temperature = cross_section_average(data, edges, "T")
        axis.plot(dense_x / L, analytic_temperature(dense_x, time, L, rho, c, k),
                  color=color, linewidth=1.8, label=f"analytic {time:g} s")
        axis.scatter(x / L, temperature, color=color, s=18,
                     label=f"simulation {time:g} s")
    axis.plot(dense_x / L, 4 - 3 * dense_x / L, "k--", linewidth=1.5,
              label="steady analytic")
    axis.set(xlabel="x/L", ylabel="T [K]", title="Transient temperature profiles")
    axis.grid(alpha=0.25)
    axis.legend(ncol=2, fontsize=7)
    figure.tight_layout()
    figure.savefig(output / "temperature_profiles_comparison.png", dpi=180)
    plt.close(figure)

    q_times = [time for time in selected_times if time > 0]
    figure, axis = plt.subplots(figsize=(8, 5.2))
    for color, time in zip(colors[1:], q_times):
        data = by_time[time]
        x, heat_flux = cross_section_average(data, edges, "qx")
        axis.plot(dense_x / L, analytic_heat_flux(dense_x, time, L, rho, c, k),
                  color=color, linewidth=1.8, label=f"analytic {time:g} s")
        axis.scatter(x / L, heat_flux, color=color, s=18,
                     label=f"dump qx {time:g} s")
    axis.axhline(3 * k / L, color="k", linestyle="--", linewidth=1.5,
                 label="steady analytic")
    axis.set(xlabel="x/L", ylabel=r"$q_x$ [W/m²]",
             title="Transient heat-flux profiles")
    axis.ticklabel_format(axis="y", style="plain", useOffset=False)
    axis.grid(alpha=0.25)
    axis.legend(ncol=2, fontsize=7)
    figure.tight_layout()
    figure.savefig(output / "heat_flux_profiles_comparison.png", dpi=180)
    plt.close(figure)

    print("selected times:", ", ".join(f"{time:g}" for time in selected_times), "s")
    print(output / "temperature_profiles_comparison.png")
    print(output / "heat_flux_profiles_comparison.png")


if __name__ == "__main__":
    main()
