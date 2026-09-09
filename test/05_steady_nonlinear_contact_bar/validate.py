"""Plot Test 05 profiles and mesh convergence from existing output."""

from pathlib import Path
import csv
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))
from lib.dump_reader import read_dump, read_dump_series

import material


case_dir = Path(__file__).resolve().parent
output = case_dir / "output"
validation = case_dir / "validation"
validation.mkdir(exist_ok=True)
rows = list(csv.DictReader((output / "convergence.csv").open(encoding="utf-8")))


def exact_temperature(x, left):
    y = (1.5 + 1.5**3 / 13 - 25 * x) if left else (
        -0.5 - 0.5**3 / 13 - 25 * (x - 0.05)
    )
    root = np.sqrt((13 * y / 2) ** 2 + (13 / 3) ** 3)
    return 2.5 + np.cbrt(13 * y / 2 + root) + np.cbrt(13 * y / 2 - root)


figure, axes = plt.subplots(1, 3, figsize=(14, 4.2))
colors = plt.cm.viridis(np.linspace(0.1, 0.85, len(rows)))
x_left, x_right = np.linspace(0, 0.05, 400), np.linspace(0.05, 0.1, 400)
axes[0].plot(x_left, exact_temperature(x_left, True), "k-", label="analytic")
axes[0].plot(x_right, exact_temperature(x_right, False), "k-")
axes[1].axhline(250, color="black", label="analytic")
for color, row in zip(colors, rows):
    dx = float(row["dx_m"])
    _, data = read_dump(output / f"dx_{dx:g}".replace(".", "p") / "dump" / "0.dump")
    order = np.argsort(data["x"])
    axes[0].plot(data["x"][order], data["T"][order], "o", ms=3, color=color,
                 label=f"dx={dx:g} m")
    axes[1].plot(data["x"][order], data["qx"][order], "o", ms=3, color=color,
                 label=f"dx={dx:g} m")
    axes[2].plot(data["x"][order], material.phi(data["T"][order]), "o", ms=3,
                 color=color, label=f"dx={dx:g} m")
axes[0].set(xlabel="x [m]", ylabel="T [K]", title="Temperature and contact jump")
axes[1].set(xlabel="x [m]", ylabel=r"$q_x$ [W/m²]", title="Heat-flux continuity")
axes[2].set(xlabel="x [m]", ylabel=r"$\Phi(T)$ [W/m]", title="Kirchhoff transform")
for axis in axes:
    axis.grid(alpha=0.25)
    axis.legend(fontsize=7)
figure.tight_layout()
figure.savefig(validation / "profiles_comparison.png", dpi=180)
plt.close(figure)

dx = np.array([float(row["dx_m"]) for row in rows])
figure, axes = plt.subplots(1, 2, figsize=(9, 4))
axes[0].loglog(dx, [float(row["rmse_T_K"]) for row in rows], "o-")
axes[1].loglog(dx, [float(row["rmse_q_W_m2"]) for row in rows], "o-")
axes[0].set(xlabel="dx [m]", ylabel="T RMSE [K]", title="Temperature convergence")
axes[1].set(xlabel="dx [m]", ylabel=r"$q_x$ RMSE [W/m²]", title="Heat-flux convergence")
for axis in axes:
    axis.grid(alpha=0.25, which="both")
    axis.invert_xaxis()
figure.tight_layout()
figure.savefig(validation / "mesh_convergence.png", dpi=180)
plt.close(figure)

print(validation / "profiles_comparison.png")
print(validation / "mesh_convergence.png")

# Finest dx/dt transient reference compared with the exact steady endpoint.
frames = read_dump_series(output / "transient" / "dump")
selected = {float(meta["TIME"]): data for meta, data in frames}
times = (0.0, 0.5, 2.0, 10.0, 50.0, 200.0, 500.0)
colors = plt.cm.plasma(np.linspace(0.05, 0.9, len(times)))
figure, axes = plt.subplots(1, 2, figsize=(11, 4.5))
axes[0].plot(x_left, exact_temperature(x_left, True), "k--", label="exact steady")
axes[0].plot(x_right, exact_temperature(x_right, False), "k--")
axes[1].axhline(250, color="black", linestyle="--", label="exact steady")
for color, time in zip(colors, times):
    data = selected[time]
    order = np.argsort(data["x"])
    axes[0].plot(data["x"][order], data["T"][order], "o-", ms=2.5,
                 color=color, label=f"t={time:g} s")
    if time > 0:
        axes[1].plot(data["x"][order], data["qx"][order], "o-", ms=2.5,
                     color=color, label=f"t={time:g} s")
axes[0].set(xlabel="x [m]", ylabel="T [K]", title="Transient temperature")
axes[1].set(xlabel="x [m]", ylabel=r"$q_x$ [W/m²]", title="Transient heat flux")
for axis in axes:
    axis.grid(alpha=0.25)
    axis.legend(fontsize=7, ncol=2)
figure.tight_layout()
figure.savefig(validation / "transient_profiles.png", dpi=180)
plt.close(figure)

history = list(csv.DictReader((output / "transient_summary.csv").open(encoding="utf-8")))
time = np.array([float(row["time_s"]) for row in history])
figure, axes = plt.subplots(1, 2, figsize=(9, 4))
axes[0].semilogx(time[1:], [float(row["T_left_K"]) for row in history[1:]], "o-",
                 label=r"$T_L$")
axes[0].semilogx(time[1:], [float(row["T_right_K"]) for row in history[1:]], "o-",
                 label=r"$T_R$")
axes[0].axhline(3, color="black", linestyle="--")
axes[0].axhline(2, color="black", linestyle="--")
axes[1].semilogx(time[1:], [float(row["jump_K"]) for row in history[1:]], "o-")
axes[1].axhline(1, color="black", linestyle="--", label="exact steady")
axes[0].set(xlabel="time [s]", ylabel="T [K]", title="Interface temperatures")
axes[1].set(xlabel="time [s]", ylabel=r"$T_L-T_R$ [K]", title="Contact jump")
for axis in axes:
    axis.grid(alpha=0.25, which="both")
    axis.legend(fontsize=8)
figure.tight_layout()
figure.savefig(validation / "transient_interface_evolution.png", dpi=180)
plt.close(figure)
print(validation / "transient_profiles.png")
print(validation / "transient_interface_evolution.png")

early_temperature_times = (0.0, 0.125, 0.5, 2.0, 10.0)
early_flux_times = early_temperature_times[1:]

figure, axis = plt.subplots(figsize=(8, 5))
axis.plot(x_left, exact_temperature(x_left, True), "k--", linewidth=1.6,
          label="exact steady")
axis.plot(x_right, exact_temperature(x_right, False), "k--", linewidth=1.6)
for color, instant in zip(
    plt.cm.plasma(np.linspace(0.05, 0.9, len(early_temperature_times))),
    early_temperature_times,
):
    data = selected[instant]
    order = np.argsort(data["x"])
    axis.plot(data["x"][order], data["T"][order], "o-", ms=3,
              color=color, label=f"t={instant:g} s")
axis.set(xlabel="x [m]", ylabel="T [K]", title="Early transient temperature profiles")
axis.grid(alpha=0.25)
axis.legend(fontsize=8)
figure.tight_layout()
figure.savefig(validation / "early_temperature_profiles.png", dpi=180)
plt.close(figure)

figure, axis = plt.subplots(figsize=(8, 5))
axis.axhline(250, color="black", linestyle="--", linewidth=1.6,
             label="exact steady")
for color, instant in zip(
    plt.cm.plasma(np.linspace(0.15, 0.9, len(early_flux_times))), early_flux_times
):
    data = selected[instant]
    order = np.argsort(data["x"])
    axis.plot(data["x"][order], data["qx"][order], "o-", ms=3,
              color=color, label=f"t={instant:g} s")
axis.set(xlabel="x [m]", ylabel=r"$q_x$ [W/m²]",
         title="Early transient heat-flux profiles")
axis.grid(alpha=0.25)
axis.legend(fontsize=8)
figure.tight_layout()
figure.savefig(validation / "early_heat_flux_profiles.png", dpi=180)
plt.close(figure)

print(validation / "early_temperature_profiles.png")
print(validation / "early_heat_flux_profiles.png")

# Fixed-time numerical convergence slice: finest dx/dt is the reference curve.
slice_root = output / "slice_0p125"
slice_runs = list(csv.DictReader((slice_root / "runs.csv").open(encoding="utf-8")))
reference_key = (0.00125, 0.015625)
styles = {0.125: ":", 0.0625: "-.", 0.03125: "--", 0.015625: "-"}
dx_values = (0.01, 0.005, 0.0025, 0.00125)
colors = dict(zip(dx_values, plt.cm.viridis(np.linspace(0.05, 0.85, 4))))
slice_data = {}
for row in slice_runs:
    dx_i, dt_i = float(row["dx_m"]), float(row["dt_s"])
    frames = read_dump_series(
        slice_root / f"dx_{dx_i:g}".replace(".", "p")
        / f"dt_{dt_i:g}".replace(".", "p") / "dump"
    )
    slice_data[(dx_i, dt_i)] = frames[-1][1]

reference_data = slice_data[reference_key]
slice_errors = []
for (dx_i, dt_i), data in sorted(slice_data.items()):
    errors = []
    for field in ("T", "qx"):
        reference_values = np.empty_like(data[field])
        for left in (True, False):
            target = data["x"] < 0.05 if left else data["x"] > 0.05
            source = reference_data["x"] < 0.05 if left else reference_data["x"] > 0.05
            order = np.argsort(reference_data["x"][source])
            reference_values[target] = np.interp(
                data["x"][target], reference_data["x"][source][order],
                reference_data[field][source][order],
            )
        errors.append(np.sqrt(np.mean((data[field] - reference_values) ** 2)))
    slice_errors.append((dx_i, dt_i, errors[0], errors[1]))
with (slice_root / "errors_vs_finest.csv").open(
    "w", encoding="utf-8", newline=""
) as file:
    writer = csv.writer(file)
    writer.writerow(("dx_m", "dt_s", "rmse_T_vs_finest_K", "rmse_qx_vs_finest_W_m2"))
    writer.writerows(slice_errors)

for field, ylabel, title, filename in (
    ("T", "T [K]", "T profiles at t=0.125 s", "slice_0p125_temperature_comparison.png"),
    ("qx", r"$q_x$ [W/m²]", "Heat-flux profiles at t=0.125 s",
     "slice_0p125_heat_flux_comparison.png"),
):
    figure, axis = plt.subplots(figsize=(10, 5.5))
    for (dx_i, dt_i), data in sorted(slice_data.items(), reverse=True):
        order = np.argsort(data["x"])
        reference = (dx_i, dt_i) == reference_key
        axis.plot(
            data["x"][order], data[field][order],
            color="black" if reference else colors[dx_i],
            linestyle="-" if reference else styles[dt_i],
            linewidth=2.8 if reference else 1.1,
            marker="o", markersize=3 if reference else 2,
            alpha=1.0 if reference else 0.72,
            label=("reference: " if reference else "")
            + f"dx={dx_i:g}, dt={dt_i:g}",
        )
    axis.set(xlabel="x [m]", ylabel=ylabel, title=title)
    axis.grid(alpha=0.25)
    axis.legend(fontsize=7, ncol=2, loc="best")
    figure.tight_layout()
    figure.savefig(validation / filename, dpi=180)
    plt.close(figure)
    print(validation / filename)
