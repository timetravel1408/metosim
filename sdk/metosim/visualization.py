"""Visualization helpers for simulation results.

Provides plot_field() and plot_structure() for rendering
electromagnetic field data and photonic structures from HDF5 results.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Literal, Optional, Tuple, Union

import numpy as np

try:
    import h5py

    HAS_H5PY = True
except ImportError:
    HAS_H5PY = False

try:
    import matplotlib.pyplot as plt
    import matplotlib.colors as mcolors
    from matplotlib.figure import Figure

    HAS_MPL = True
except ImportError:
    HAS_MPL = False


def _ensure_deps() -> None:
    """Check that visualisation dependencies are available."""
    if not HAS_H5PY:
        raise ImportError("h5py is required for visualization. Install: pip install h5py")
    if not HAS_MPL:
        raise ImportError("matplotlib is required for visualization. Install: pip install matplotlib")


def plot_field(
    results: Union[str, Path, Dict[str, Any]],
    component: str = "Ez",
    *,
    slice_axis: Literal["x", "y", "z"] = "z",
    slice_index: Optional[int] = None,
    freq_index: int = 0,
    cmap: str = "RdBu_r",
    vmax: Optional[float] = None,
    figsize: Tuple[float, float] = (10, 6),
    title: Optional[str] = None,
    save_path: Optional[str | Path] = None,
    show: bool = True,
) -> Optional[Figure]:
    """Plot electromagnetic field component from simulation results.

    Loads an HDF5 result file and renders a 2D slice of the specified
    field component.

    Args:
        results: Path to HDF5 file, or dict of numpy arrays.
        component: Field component to plot ('Ex', 'Ey', 'Ez', 'Hx', 'Hy', 'Hz').
        slice_axis: Axis perpendicular to the slice plane.
        slice_index: Index along slice_axis. Defaults to midpoint.
        freq_index: Frequency index for multi-frequency data.
        cmap: Matplotlib colourmap name.
        vmax: Maximum absolute value for symmetric colour scale.
        figsize: Figure size in inches.
        title: Custom title. Auto-generated if None.
        save_path: Save figure to this path if provided.
        show: Whether to display the figure.

    Returns:
        Matplotlib Figure if show=False, else None.

    Example:
        >>> plot_field("results.hdf5", component="Ez")
        >>> plot_field("results.hdf5", component="Hy", slice_axis="y", cmap="viridis")
    """
    _ensure_deps()

    # Load data
    if isinstance(results, (str, Path)):
        field_data = _load_field_from_hdf5(Path(results), component, freq_index)
    elif isinstance(results, dict):
        if component not in results:
            raise KeyError(f"Component '{component}' not found. Available: {list(results.keys())}")
        field_data = results[component]
    else:
        raise TypeError(f"Expected path or dict, got {type(results)}")

    # Take 2D slice
    axis_map = {"x": 0, "y": 1, "z": 2}
    ax_idx = axis_map[slice_axis]

    if slice_index is None:
        slice_index = field_data.shape[ax_idx] // 2

    slices = [slice(None)] * 3
    slices[ax_idx] = slice_index
    field_2d = field_data[tuple(slices)]

    # Handle complex fields
    if np.iscomplexobj(field_2d):
        field_2d = np.real(field_2d)

    # Create figure
    fig, ax = plt.subplots(1, 1, figsize=figsize)

    if vmax is None:
        vmax = np.max(np.abs(field_2d)) * 0.9

    norm = mcolors.TwoSlopeNorm(vmin=-vmax, vcenter=0, vmax=vmax)
    im = ax.imshow(
        field_2d.T,
        origin="lower",
        cmap=cmap,
        norm=norm,
        aspect="equal",
    )

    # Axis labels
    remaining_axes = [a for a in "xyz" if a != slice_axis]
    ax.set_xlabel(f"{remaining_axes[0]} (grid points)")
    ax.set_ylabel(f"{remaining_axes[1]} (grid points)")

    # Title
    if title is None:
        title = f"{component} field — {slice_axis}={slice_index} slice"
    ax.set_title(title, fontsize=12, fontweight="bold")

    plt.colorbar(im, ax=ax, label=component, shrink=0.8)
    plt.tight_layout()

    if save_path:
        fig.savefig(save_path, dpi=150, bbox_inches="tight")

    if show:
        plt.show()
        return None
    return fig


def plot_structure(
    results: Union[str, Path],
    *,
    slice_axis: Literal["x", "y", "z"] = "z",
    slice_index: Optional[int] = None,
    cmap: str = "coolwarm",
    figsize: Tuple[float, float] = (10, 6),
    show: bool = True,
) -> Optional[Figure]:
    """Plot the permittivity distribution of the simulation structure.

    Args:
        results: Path to HDF5 result file containing structure data.
        slice_axis: Axis perpendicular to the slice plane.
        slice_index: Index along slice_axis.
        cmap: Matplotlib colourmap.
        figsize: Figure size.
        show: Whether to display.

    Returns:
        Figure if show=False.
    """
    _ensure_deps()

    with h5py.File(str(results), "r") as f:
        if "structure/permittivity" not in f:
            raise KeyError("HDF5 file does not contain structure/permittivity dataset")
        eps = f["structure/permittivity"][:]

    axis_map = {"x": 0, "y": 1, "z": 2}
    ax_idx = axis_map[slice_axis]

    if slice_index is None:
        slice_index = eps.shape[ax_idx] // 2

    slices = [slice(None)] * 3
    slices[ax_idx] = slice_index
    eps_2d = np.real(eps[tuple(slices)])

    fig, ax = plt.subplots(1, 1, figsize=figsize)
    im = ax.imshow(eps_2d.T, origin="lower", cmap=cmap, aspect="equal")

    remaining_axes = [a for a in "xyz" if a != slice_axis]
    ax.set_xlabel(f"{remaining_axes[0]} (grid points)")
    ax.set_ylabel(f"{remaining_axes[1]} (grid points)")
    ax.set_title(f"Permittivity (ε_r) — {slice_axis}={slice_index}", fontsize=12, fontweight="bold")

    plt.colorbar(im, ax=ax, label="ε_r", shrink=0.8)
    plt.tight_layout()

    if show:
        plt.show()
        return None
    return fig


def _load_field_from_hdf5(
    path: Path,
    component: str,
    freq_index: int = 0,
) -> np.ndarray:
    """Load a field component from an HDF5 results file.

    Args:
        path: Path to HDF5 file.
        component: Field component name.
        freq_index: Frequency index.

    Returns:
        3D numpy array of field data.
    """
    with h5py.File(str(path), "r") as f:
        # Try direct path
        for group_name in ["fields", "monitors", "data"]:
            key = f"{group_name}/{component}"
            if key in f:
                data = f[key][:]
                # If 4D (freq, x, y, z), select frequency
                if data.ndim == 4:
                    return data[freq_index]
                return data

        raise KeyError(
            f"Field component '{component}' not found in {path}. "
            f"Available datasets: {list(_list_datasets(f))}"
        )


def _list_datasets(group: Any, prefix: str = "") -> list[str]:
    """Recursively list all datasets in an HDF5 group."""
    datasets = []
    for key in group:
        item = group[key]
        full_key = f"{prefix}/{key}" if prefix else key
        if hasattr(item, "keys"):
            datasets.extend(_list_datasets(item, full_key))
        else:
            datasets.append(full_key)
    return datasets
