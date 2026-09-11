from __future__ import annotations

from pathlib import Path


def save_spatial_domains(
    x,
    y,
    domains,
    output: Path,
    title: str,
    point_size: float,
) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np
    from matplotlib.colors import BoundaryNorm
    from matplotlib.lines import Line2D

    unique_domains = np.sort(np.unique(domains))
    domain_indices = np.searchsorted(unique_domains, domains)
    colour_map = plt.get_cmap("tab20", len(unique_domains))
    norm = BoundaryNorm(
        np.arange(-0.5, len(unique_domains) + 0.5, 1),
        ncolors=len(unique_domains),
    )

    ratio = np.ptp(y) / max(float(np.ptp(x)), 1e-12)
    figure, axis = plt.subplots(figsize=(10, max(4, min(10, 8 * ratio + 1))))
    axis.scatter(
        x,
        y,
        c=domain_indices,
        cmap=colour_map,
        norm=norm,
        s=point_size,
        rasterized=True,
    )
    axis.set_aspect("equal")
    axis.invert_yaxis()
    axis.set_title(title)
    handles = [
        Line2D(
            [],
            [],
            color=colour_map(i),
            marker="o",
            linestyle="",
            label=str(domain),
            markersize=6,
        )
        for i, domain in enumerate(unique_domains)
    ]
    axis.legend(
        handles=handles,
        title="Domains",
        loc="upper left",
        bbox_to_anchor=(1.02, 1),
        frameon=False,
    )
    figure.savefig(output, dpi=150, bbox_inches="tight")
    plt.close(figure)
