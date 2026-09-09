"""Small reusable plotting helpers for post-processing field data."""

import matplotlib.pyplot as plt


def plot_heatmap(x, y, values, path, *, ylabel, color_label, vmin=None,
                 vmax=None, cmap="viridis"):
    figure, axis = plt.subplots(figsize=(7, 4.5))
    image = axis.pcolormesh(
        x, y, values, shading="nearest", cmap=cmap, vmin=vmin, vmax=vmax
    )
    axis.set(xlabel="x/L", ylabel=ylabel)
    figure.colorbar(image, ax=axis, label=color_label)
    figure.tight_layout()
    figure.savefig(path, dpi=180)
    plt.close(figure)
