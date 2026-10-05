"""Trade facts from CEPII BACI (values in current USD).

fig06_trade_exporters   (a) electric bus exports by exporter group, 2017-2024
                        (b) electric road-tractor exports by exporter, 2024
                        (c) heavy diesel truck (>20 t) exports, China vs Mexico vs Germany
tab_etruck_exporters_2024.tex   exporters of HS 870460 with unit values (van vs truck mix)
"""
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import plot_style as ps  # noqa: E402
from config import PROC_DIR, TAB_DIR  # noqa: E402
from countries import EU27  # noqa: E402

NAMES = {"CHN": "China", "POL": "Poland", "SWE": "Sweden", "BEL": "Belgium", "DEU": "Germany",
         "FRA": "France", "USA": "United States", "NLD": "Netherlands", "MEX": "Mexico", "ITA": "Italy",
         "TUR": "Turkiye", "CAN": "Canada", "GBR": "United Kingdom", "ESP": "Spain", "KOR": "Korea"}


def main() -> None:
    ps.use()
    e = pd.read_csv(PROC_DIR / "trade_exporter_year.csv")
    fig, axes = plt.subplots(1, 3, figsize=(10.5, 3.4))

    ax = axes[0]
    b = e[e.category == "e_bus"].copy()
    b["grp"] = b.exporter_iso3.map(lambda x: "China" if x == "CHN" else ("EU-27" if x in EU27 else "Rest of world"))
    b = b.pivot_table(index="year", columns="grp", values="value_usd", aggfunc="sum") / 1e9
    for grp, col in (("China", ps.REGION_COLORS["China"]), ("EU-27", ps.REGION_COLORS["Europe"]),
                     ("Rest of world", ps.OTHER)):
        ax.plot(b.index, b[grp], color=col, marker="o", markersize=3.5, label=grp)
        ps.label_end(ax, b.index[-1], b[grp].iloc[-1], f"{b[grp].iloc[-1]:.1f}")
    ax.set_title("(a) Electric bus exports (USD bn)")
    ax.set_xlim(2017, 2025.2)
    ax.legend(loc="upper left")

    ax = axes[1]
    t = e[(e.category == "e_tractor") & (e.year == 2024)].nlargest(8, "value_usd").iloc[::-1]
    ax.barh([NAMES.get(i, i) for i in t.exporter_iso3], t.value_usd / 1e6, color=ps.SLOTS[0], height=0.65,
            edgecolor="white", linewidth=1)
    for y, v in enumerate(t.value_usd / 1e6):
        ax.annotate(f"{v:,.0f}", (v, y), xytext=(3, 0), textcoords="offset points", va="center",
                    fontsize=7, color=ps.INK_2)
    ax.grid(axis="y", visible=False)
    ax.grid(axis="x", visible=True)
    ax.set_title("(b) Electric road tractor exports, 2024 (USD m)")

    ax = axes[2]
    h = e[e.category == "diesel_truck_gt20t"].pivot_table(index="year", columns="exporter_iso3", values="value_usd") / 1e9
    for iso, col, dy in (("CHN", ps.SLOTS[0], 0), ("MEX", ps.SLOTS[1], 6), ("DEU", ps.SLOTS[2], -6)):
        ax.plot(h.index, h[iso], color=col, marker="o", markersize=3.5, label=NAMES[iso])
        ps.label_end(ax, h.index[-1], h[iso].iloc[-1], f"{h[iso].iloc[-1]:.1f}", dy=dy)
    ax.set_title("(c) Diesel truck >20 t exports (USD bn)")
    ax.set_xlim(2017, 2025.2)
    ax.legend(loc="upper left")
    fig.text(0.0, -0.04, "HS 870240 (buses, electric only), 870124 (road tractors, electric only), 870423 (diesel "
             "goods vehicles >20 t). Source: CEPII BACI V202601.", fontsize=7, color=ps.MUTED)
    fig.tight_layout()
    ps.save(fig, "fig06_trade_exporters")

    f = pd.read_csv(PROC_DIR / "trade_flows_hs6.csv.gz")
    x = f[(f.category == "e_truck") & (f.year == 2024)]
    g = x.groupby("exporter_iso3")[["value_usd", "qty_tonnes"]].sum()
    g["usd_per_kg"] = g.value_usd / (g.qty_tonnes * 1000)
    top_dest = (x.groupby(["exporter_iso3", "importer_iso3"])["value_usd"].sum().reset_index()
                .sort_values("value_usd", ascending=False).groupby("exporter_iso3").head(3)
                .groupby("exporter_iso3")["importer_iso3"].agg(", ".join))
    g["top destinations"] = top_dest
    g["world share (%)"] = 100 * g.value_usd / g.value_usd.sum()
    g = g.sort_values("value_usd", ascending=False).head(10)
    g["value (USD m)"] = g.value_usd / 1e6
    g.index = [NAMES.get(i, i) for i in g.index]
    g.index.name = "Exporter"
    g[["value (USD m)", "world share (%)", "usd_per_kg", "top destinations"]].rename(
        columns={"usd_per_kg": "USD per kg"}).to_latex(TAB_DIR / "tab_etruck_exporters_2024.tex", escape=True, position="htbp", float_format="%.1f", label="tab:etruckexp",
        caption="Exporters of all-electric goods vehicles (HS 870460), 2024")
    print(g[["value (USD m)", "world share (%)", "usd_per_kg", "top destinations"]].round(1))


if __name__ == "__main__":
    main()
