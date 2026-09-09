"""Plot spatial-and-temporal convergence from existing Test 02 dumps."""

from pathlib import Path
import csv
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import yaml


PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from lib.dump_reader import read_dump_series


def analytic_temperature(x, t, L, rho, c, k, terms=400):
    x = np.asarray(x)
    if t == 0:
        return np.where(x < L / 2, 4.0, 1.0)
    m = np.arange(1, terms + 1)[:, None]
    alpha = k / (rho * c)
    modes = 3 * (-1) ** (m + 1) / (m * np.pi)
    return 4 - 3 * x / L + np.sum(
        modes * np.sin(2 * m * np.pi * x / L)
        * np.exp(-alpha * (2 * m * np.pi / L) ** 2 * t), axis=0
    )


def analytic_heat_flux(x, t, L, rho, c, k, terms=400):
    x = np.asarray(x)
    m = np.arange(1, terms + 1)[:, None]
    alpha = k / (rho * c)
    return 3 * k / L - 6 * k / L * np.sum(
        (-1) ** (m + 1) * np.cos(2 * m * np.pi * x / L)
        * np.exp(-alpha * (2 * m * np.pi / L) ** 2 * t), axis=0
    )


def label(prefix, value):
    return f"{prefix}_{value:g}".replace(".", "p")


def cross_section_average(data, field, bins=50):
    edges = np.linspace(np.min(data["x"]), np.max(data["x"]), bins + 1)
    indices = np.clip(np.digitize(data["x"], edges) - 1, 0, bins - 1)
    means = [
        (np.mean(data["x"][indices == i]), np.mean(data[field][indices == i]))
        for i in range(bins) if np.any(indices == i)
    ]
    return np.asarray(means).T


def save(figure, path):
    if path.exists():
        path.unlink()
    figure.tight_layout()
    figure.savefig(path, dpi=180)
    plt.close(figure)


def profile_figure(runs, values, fixed, times, field, exact, L, material, output):
    varying = "dt" if fixed[0] == "dx" else "dx"
    figure, axes = plt.subplots(1, len(times), figsize=(5 * len(times), 4.2), sharey=True)
    dense_x = np.linspace(0, L, 800)
    colors = plt.cm.viridis(np.linspace(0.15, 0.85, len(values)))
    for axis, time in zip(np.atleast_1d(axes), times):
        axis.plot(
            dense_x / L, exact(dense_x, time, L, *material), "k-",
            linewidth=1.8, label="analytic",
        )
        for color, value in zip(colors, values):
            key = (fixed[1], value) if varying == "dt" else (value, fixed[1])
            data = runs[key][time]
            x, y = cross_section_average(data, field)
            unit = "s" if varying == "dt" else "m"
            axis.plot(x / L, y, "o-", color=color, markersize=3,
                      label=f"{varying}={value:g} {unit}")
        axis.set(xlabel="x/L", title=f"t={time:g} s")
        axis.grid(alpha=0.25)
    axes = np.atleast_1d(axes)
    axes[0].set_ylabel("T [K]" if field == "T" else r"$q_x$ [W/m²]")
    axes[-1].legend(fontsize=8)
    title_field = "Temperature" if field == "T" else "Heat flux"
    figure.suptitle(f"{title_field}: varying {varying}, fixed {fixed[0]}={fixed[1]:g}")
    save(figure, output)


def main():
    case_dir = Path(__file__).resolve().parent
    output = case_dir / "validation"
    output.mkdir(exist_ok=True)
    case = yaml.safe_load((case_dir / "case.yaml").read_text(encoding="utf-8"))
    mat = next(iter(case["regions"].values()))
    material = (mat["rho"], mat["cp"], mat["k"])
    rows = list(csv.DictReader(
        (case_dir / "output" / "convergence" / "runs.csv").open(encoding="utf-8")
    ))
    dx_values = sorted({float(row["dx_m"]) for row in rows}, reverse=True)
    dt_values = sorted({float(row["dt_s"]) for row in rows}, reverse=True)
    runs = {}
    for row in rows:
        dx, dt = float(row["dx_m"]), float(row["dt_s"])
        frames = read_dump_series(
            case_dir / "output" / "convergence" / label("dx", dx)
            / label("dt", dt) / "dump"
        )
        runs[(dx, dt)] = {float(meta["TIME"]): data for meta, data in frames}
    first = next(iter(runs.values()))
    first_data = next(iter(first.values()))
    L = np.ptp(first_data["x"])
    # Centroid bounds omit half a boundary cell; use the case's known geometric length.
    L = 0.1
    times = (0.0625, 0.125, 0.25, 0.5)
    finest_dx, finest_dt = min(dx_values), min(dt_values)

    profile_figure(
        runs, dt_values, ("dx", finest_dx), times, "T", analytic_temperature,
        L, material, output / "temperature_profiles_varying_dt.png",
    )
    profile_figure(
        runs, dt_values, ("dx", finest_dx), times, "qx", analytic_heat_flux,
        L, material, output / "heat_flux_profiles_varying_dt.png",
    )
    profile_figure(
        runs, dx_values, ("dt", finest_dt), times, "T", analytic_temperature,
        L, material, output / "temperature_profiles_varying_dx.png",
    )
    profile_figure(
        runs, dx_values, ("dt", finest_dt), times, "qx", analytic_heat_flux,
        L, material, output / "heat_flux_profiles_varying_dx.png",
    )

    errors = []
    for (dx, dt), frames in sorted(runs.items()):
        for time in times:
            data = frames[time]
            e_t = data["T"] - analytic_temperature(data["x"], time, L, *material)
            e_q = data["qx"] - analytic_heat_flux(data["x"], time, L, *material)
            errors.append((
                dx, dt, time, np.sqrt(np.mean(e_t**2)), np.max(np.abs(e_t)),
                np.sqrt(np.mean(e_q**2)), np.max(np.abs(e_q)),
            ))
    with (output / "convergence_errors.csv").open(
        "w", encoding="utf-8", newline=""
    ) as file:
        writer = csv.writer(file)
        writer.writerow((
            "dx_m", "dt_s", "time_s", "rmse_T", "linf_T", "rmse_q", "linf_q"
        ))
        writer.writerows(errors)

    print("profile comparisons: varying dt and varying dx")
    for name in (
        "temperature_profiles_varying_dt.png", "heat_flux_profiles_varying_dt.png",
        "temperature_profiles_varying_dx.png", "heat_flux_profiles_varying_dx.png",
        "convergence_errors.csv",
    ):
        print(output / name)


if __name__ == "__main__":
    main()
