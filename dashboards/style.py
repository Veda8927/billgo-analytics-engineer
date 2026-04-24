"""Shared style settings for all charts."""
import matplotlib.pyplot as plt

COLOR_TEXT = "#1a1a1a"
COLOR_TEXT_MUTED = "#6b7280"
COLOR_GRID = "#e5e7eb"
COLOR_ACCENT = "#1f3a5f"
COLOR_ACCENT_SOFT = "#7a8ca3"
COLOR_WARN = "#b45309"

HEATMAP_CMAP = "Blues"
SLATE_3 = ["#cbd5e1", "#7a8ca3", "#1f3a5f"]


def apply_style():
    """Apply shared matplotlib styling."""
    plt.rcParams.update({
        "font.family": "sans-serif",
        "font.sans-serif": ["-apple-system", "Helvetica Neue", "Arial", "sans-serif"],
        "font.size": 10,
        "axes.titlesize": 13,
        "axes.titleweight": "semibold",
        "axes.titlepad": 14,
        "axes.titlelocation": "left",
        "axes.labelsize": 10,
        "axes.labelcolor": COLOR_TEXT_MUTED,
        "xtick.labelsize": 9,
        "ytick.labelsize": 9,
        "xtick.color": COLOR_TEXT_MUTED,
        "ytick.color": COLOR_TEXT_MUTED,
        "axes.edgecolor": COLOR_GRID,
        "axes.linewidth": 0.8,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "grid.color": COLOR_GRID,
        "grid.linewidth": 0.6,
        "axes.axisbelow": True,
        "legend.frameon": False,
        "legend.fontsize": 9,
        "figure.facecolor": "white",
        "axes.facecolor": "white",
        "savefig.facecolor": "white",
        "savefig.dpi": 150,
        "savefig.bbox": "tight",
        "text.parse_math": False,
    })
