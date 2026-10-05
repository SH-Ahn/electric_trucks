"""Global adoption facts from the IEA panel.

fig01_etruck_sales_region   (a) electric-truck sales, China vs rest of world, 2015-2025
                            (b) EV share of truck sales: China, Europe, World
fig02_country_shares_2025   EV share of new truck and bus sales by country, 2025
tab_country_shares_2025.tex table twin of fig02
"""
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import plot_style as ps  # noqa: E402
from config import PROC_DIR, TAB_DIR  # noqa: E402


def main() -> None:
    ps.use()
    d = pd.read_csv(PROC_DIR / "iea_ev_region_year.csv")
    t = d[d["mode"] == "Trucks"]
    sales = t.pivot_table(index="year", columns="region", values="ev_sales").loc[2015:2025]
    other = sales["World"] - sales["China"] - sales["Europe"] - sales["Canada"].fillna(0)
    share = t.pivot_table(index="year", columns="region", values="ev_sales_share").loc[2015:2025]

    fig, axes = plt.subplots(1, 2, figsize=(9.2, 3.4))
    ax = axes[0]
    yrs = sales.index.values
    parts = [("China", sales["China"], ps.REGION_COLORS["China"]),
             ("Europe", sales["Europe"], ps.REGION_COLORS["Europe"]),
             ("US, Canada & rest of world", other + sales["Canada"].fillna(0), ps.OTHER)]
    bottom = 0
    for lab, v, c in parts:
        ax.bar(yrs, v / 1e3, bottom=bottom, color=c, width=0.72, edgecolor="white", linewidth=1, label=lab)
        bottom = bottom + v.fillna(0) / 1e3
    for y in (2017, 2020, 2025):
        ax.annotate(f"{sales.loc[y, 'World'] / 1e3:,.0f}k", (y, sales.loc[y, "World"] / 1e3),
                    xytext=(0, 3), textcoords="offset points", ha="center", fontsize=8, color=ps.INK_2)
    ax.set_title("(a) Electric truck sales (thousand)")
    ax.legend(loc="upper left")
    ax.set_xticks(yrs[::2])

    ax = axes[1]
    for reg, lab in (("China", "China"), ("Europe", "Europe"), ("World", "World")):
        col = ps.REGION_COLORS.get(reg, ps.SLOTS[2])
        s = share[reg].dropna()
        ax.plot(s.index, s.values, color=col, marker="o", markersize=3.5, label=lab)
        ps.label_end(ax, s.index[-1], s.values[-1], f"{lab} {s.values[-1]:.0f}%")
    ax.set_title("(b) EV share of new truck sales (%)")
    ax.set_xlim(2015, 2027.6)
    ax.set_xticks(range(2015, 2026, 2))
    ax.legend(loc="upper left")
    fig.text(0.0, -0.04, "Trucks = medium (3.5-15 t) and heavy (>15 t) freight trucks. Source: IEA Global EV "
             "Data Explorer (GEVO 2026); the API has no US truck series, so the US is in the residual.",
             fontsize=7, color=ps.MUTED)
    fig.tight_layout()
    ps.save(fig, "fig01_etruck_sales_region")

    c = d[(d.year == 2025) & d.is_country & d["mode"].isin(["Trucks", "Buses"])]
    c = c.pivot_table(index="region", columns="mode", values="ev_sales_share").dropna(subset=["Trucks"])
    c = c.sort_values("Trucks")
    fig, ax = plt.subplots(figsize=(6.4, 4.4))
    yy = range(len(c))
    ax.hlines(yy, 0, c[["Trucks", "Buses"]].max(axis=1), color=ps.GRID, linewidth=1)
    ax.plot(c["Trucks"], yy, "o", color=ps.SLOTS[0], label="Trucks", markersize=6,
            markeredgecolor="white", markeredgewidth=1, zorder=3)
    ax.plot(c["Buses"], yy, "o", color=ps.SLOTS[1], label="Buses", markersize=6,
            markeredgecolor="white", markeredgewidth=1, zorder=3)
    for i, (reg, row) in enumerate(c.iterrows()):
        small = row.Trucks < 3
        ax.annotate(f"{row.Trucks:.0f}%" if row.Trucks >= 1 else f"{row.Trucks:.2f}%",
                    (row.Trucks, i), xytext=(7, 5) if small else (-6, 0), textcoords="offset points",
                    ha="left" if small else "right", va="center", fontsize=7, color=ps.INK_2)
    ax.set_yticks(list(yy), c.index)
    ax.grid(axis="y", visible=False)
    ax.grid(axis="x", visible=True)
    ax.set_xlabel("EV share of new sales, 2025 (%)")
    ax.set_title("EV share of new truck and bus sales by country, 2025")
    ax.legend(loc="lower right")
    fig.tight_layout()
    ps.save(fig, "fig02_country_shares_2025")

    tab = c.sort_values("Trucks", ascending=False)[["Trucks", "Buses"]]
    tab.columns = ["Trucks (%)", "Buses (%)"]
    tab.index.name = "Country"
    tab.to_latex(TAB_DIR / "tab_country_shares_2025.tex", escape=True, position="htbp", float_format="%.1f", na_rep="--",
                 caption="EV share of new truck and bus sales, 2025 (IEA)", label="tab:shares2025")
    print(sales[["China", "Europe", "World"]].tail(6))
    print(c.round(1).to_string())


if __name__ == "__main__":
    main()
