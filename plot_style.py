"""House style for static figures (matplotlib), following the dataviz reference palette.

Categorical slots are assigned in fixed order and follow the entity, never its
rank. The 8-slot light palette passes the validator (worst adjacent CVD dE 9.1);
scatter/small-multiple charts use at most the first three slots. Slots 3-5 are
below 3:1 contrast on the light surface, so figures carry direct labels and the
underlying numbers are tabulated in the research-design document.
"""
from __future__ import annotations

import matplotlib as mpl
import matplotlib.pyplot as plt

from config import FIG_DIR

SURFACE = "#fcfcfb"
INK = "#0b0b0b"
INK_2 = "#52514e"
MUTED = "#898781"
GRID = "#e1e0d9"
BASELINE = "#c3c2b7"

SLOTS = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#4a3aa7", "#e34948"]
OTHER = "#b5b3ab"  # neutral for "Other"/de-emphasised series

# Fixed entity -> colour assignments used across figures.
REGION_COLORS = {"China": SLOTS[0], "Europe": SLOTS[1], "US & Canada": SLOTS[2],
                 "Rest of world": OTHER}
POWERTRAIN_COLORS = {"Battery electric": SLOTS[0], "Diesel": OTHER, "Other": "#d6d4cc"}


def use() -> None:
    mpl.rcParams.update({
        "figure.facecolor": "white", "axes.facecolor": "white", "savefig.facecolor": "white",
        "font.family": "sans-serif",
        "font.sans-serif": ["Helvetica Neue", "Helvetica", "Arial", "DejaVu Sans"],
        "font.size": 9, "axes.titlesize": 10, "axes.titleweight": "bold", "axes.titlelocation": "left",
        "axes.labelsize": 9, "axes.labelcolor": INK_2, "axes.edgecolor": BASELINE,
        "axes.linewidth": 0.8, "axes.spines.top": False, "axes.spines.right": False,
        "axes.grid": True, "axes.grid.axis": "y", "axes.axisbelow": True, "grid.color": GRID, "grid.linewidth": 0.6,
        "grid.linestyle": "-", "xtick.color": MUTED, "ytick.color": MUTED,
        "xtick.labelcolor": INK_2, "ytick.labelcolor": INK_2, "xtick.major.size": 0,
        "ytick.major.size": 0, "lines.linewidth": 1.6, "lines.markersize": 5,
        "legend.frameon": False, "legend.fontsize": 8, "text.color": INK,
        "axes.prop_cycle": mpl.cycler(color=SLOTS), "figure.dpi": 150, "savefig.dpi": 300,
        "savefig.bbox": "tight", "pdf.fonttype": 42,
    })


def save(fig, name: str) -> None:
    """Save as PDF (for LaTeX) and PNG (for quick viewing) in 04_output/01_figure."""
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIG_DIR / f"{name}.pdf")
    fig.savefig(FIG_DIR / f"{name}.png")
    plt.close(fig)


def spread(values, min_gap: float) -> list[float]:
    """Nudge label y-positions apart (in data units) so stacked labels don't overlap."""
    order = sorted(range(len(values)), key=lambda i: values[i])
    out = list(values)
    for k in range(1, len(order)):
        prev, cur = order[k - 1], order[k]
        if out[cur] - out[prev] < min_gap:
            out[cur] = out[prev] + min_gap
    return out


def label_end(ax, x, y, text, color=INK_2, dx=4, dy=0, **kw) -> None:
    """Direct label at a line end, in text ink (not series colour)."""
    ax.annotate(text, (x, y), xytext=(dx, dy), textcoords="offset points", va="center",
                fontsize=8, color=color, **kw)
