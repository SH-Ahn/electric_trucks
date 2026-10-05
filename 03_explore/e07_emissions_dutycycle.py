"""Environmental payoff by grid, and which US trucks are technically easy to electrify.

fig12_co2_per_km_grid   operational CO2 per km of a 40 t battery-electric tractor on each country's
                        2025 grid vs a diesel tractor (tank-to-wheel and well-to-wheel)
fig13_vius_duty_cycle   US trucks (VIUS 2021): share with >=90% of annual miles within 100 miles
                        of home base, by GVWR class and vehicle type
tab_co2_per_km.tex      table twin of fig12

Parameters: BEV 1.20 kWh/km at the wheel + 10% charging losses; diesel 31 L/100 km,
2.68 kg CO2/L tank-to-wheel, x1.21 well-to-wheel (upstream ~21%). Grid intensity is the
annual average (Ember), not marginal emissions; battery manufacturing is excluded.
"""
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import plot_style as ps  # noqa: E402
from config import PROC_DIR, TAB_DIR  # noqa: E402

KWH_PER_KM = 1.20 / 0.90
DIESEL_TTW = 0.31 * 2.68 * 1000  # g CO2 per km
DIESEL_WTW = DIESEL_TTW * 1.21
COUNTRIES = ["NOR", "SWE", "CHE", "FRA", "BRA", "CAN", "GBR", "ESP", "NLD", "DEU", "USA", "MEX", "JPN", "KOR",
             "AUS", "CHN", "POL", "IDN", "IND", "ZAF"]
NAMES = {"NOR": "Norway", "SWE": "Sweden", "CHE": "Switzerland", "FRA": "France", "BRA": "Brazil",
         "CAN": "Canada", "GBR": "United Kingdom", "ESP": "Spain", "NLD": "Netherlands", "DEU": "Germany",
         "USA": "United States", "MEX": "Mexico", "JPN": "Japan", "KOR": "Korea", "AUS": "Australia",
         "CHN": "China", "POL": "Poland", "IDN": "Indonesia", "IND": "India", "ZAF": "South Africa"}


def co2_figure() -> None:
    cy = pd.read_csv(PROC_DIR / "country_year_covariates.csv")
    g = cy[cy.iso3.isin(COUNTRIES)].dropna(subset=["grid_gco2_kwh"])
    g = g.sort_values("year").groupby("iso3").tail(1).set_index("iso3")
    g["bev_g_km"] = g.grid_gco2_kwh * KWH_PER_KM
    g = g.sort_values("bev_g_km")
    fig, ax = plt.subplots(figsize=(6.6, 4.8))
    yy = range(len(g))
    ax.barh(list(yy), g.bev_g_km, color=ps.SLOTS[0], height=0.65, edgecolor="white", linewidth=1,
            label="Battery-electric, average grid")
    for y, (iso, r) in zip(yy, g.iterrows()):
        ax.annotate(f"{r.bev_g_km:,.0f}", (r.bev_g_km, y), xytext=(3, 0), textcoords="offset points",
                    va="center", fontsize=7, color=ps.INK_2)
    ax.set_ylim(-2.2, len(g) - 0.4)
    ax.set_xlim(0, 1250)
    for x, lab, side in ((DIESEL_TTW, "Diesel, tank-to-wheel", -1), (DIESEL_WTW, "Diesel, well-to-wheel", 1)):
        ax.axvline(x, color=ps.SLOTS[1], linewidth=1.2)
        ax.annotate(f"{lab}\n{x:,.0f} g/km", (x, -1.6), xytext=(4 * side, 0), textcoords="offset points",
                    ha="left" if side > 0 else "right", va="center", fontsize=7, color=ps.INK_2)
    ax.set_yticks(list(yy), [f"{NAMES[i]} ({int(r.year)})" for i, r in g.iterrows()])
    ax.grid(axis="y", visible=False)
    ax.grid(axis="x", visible=True)
    ax.set_xlabel("Operational CO2 of a 40 t tractor (g per km)")
    sav = 100 * (1 - g.bev_g_km / DIESEL_WTW)
    ax.set_title(f"Operational CO2 savings vs diesel range from {sav.min():.0f}% to {sav.max():.0f}% by grid")
    fig.text(0.0, -0.05, "BEV 1.2 kWh/km + 10% charging loss x Ember average grid intensity; diesel 31 L/100 km. "
             "Excludes battery manufacturing.", fontsize=7, color=ps.MUTED)
    fig.tight_layout()
    ps.save(fig, "fig12_co2_per_km_grid")
    t = g[["year", "grid_gco2_kwh", "bev_g_km"]].copy()
    t["saving_vs_diesel_wtw_pct"] = 100 * (1 - t.bev_g_km / DIESEL_WTW)
    t.index = [NAMES[i] for i in t.index]
    t.index.name = "Country"
    t.columns = ["Grid year", "Grid gCO2/kWh", "BEV gCO2/km", "Saving vs diesel WTW (%)"]
    t.to_latex(TAB_DIR / "tab_co2_per_km.tex", escape=True, position="htbp", float_format="%.0f", label="tab:co2km",
               caption="Operational CO2 per km of a battery-electric 40 t tractor by grid, vs diesel "
                       f"({DIESEL_TTW:.0f} g/km tank-to-wheel, {DIESEL_WTW:.0f} g/km well-to-wheel)")
    print(t.round(0).to_string())


def vius_figure() -> None:
    v = pd.read_csv(PROC_DIR / "vius_duty_cycle_by_class.csv", dtype={"gvwr_class": str})
    v = v[v.gvwr_class.isin(["3", "4", "5", "6", "7", "8"])].copy()
    v["label"] = "Class " + v.gvwr_class + "\n" + v.vehicle_type.map({"SU": "single-unit", "TT": "tractor"})
    v = v.sort_values(["vehicle_type", "gvwr_class"])
    fig, ax = plt.subplots(figsize=(6.6, 3.4))
    cols = [ps.SLOTS[0] if t == "SU" else ps.SLOTS[1] for t in v.vehicle_type]
    ax.bar(range(len(v)), 100 * v.share_trucks_90pct_within_100mi, color=cols, width=0.65, edgecolor="white",
           linewidth=1)
    for x, (_, r) in enumerate(v.iterrows()):
        ax.annotate(f"{100 * r.share_trucks_90pct_within_100mi:.0f}%\n{r.mean_annual_miles / 1000:.0f}k mi/yr",
                    (x, 100 * r.share_trucks_90pct_within_100mi), xytext=(0, 3), textcoords="offset points",
                    ha="center", fontsize=7, color=ps.INK_2)
    ax.set_xticks(range(len(v)), v.label, fontsize=7)
    ax.set_ylim(0, 110)
    ax.set_ylabel("Trucks with >=90% of miles\nwithin 100 miles of base (%)")
    ax.set_title("Most US medium and heavy rigid trucks run local duty cycles; Class 8 tractors do not")
    from matplotlib.patches import Patch
    ax.legend(handles=[Patch(color=ps.SLOTS[0], label="Single-unit trucks"),
                       Patch(color=ps.SLOTS[1], label="Truck tractors")], loc="upper right", ncol=2)
    fig.text(0.0, -0.05, "Weighted by VIUS tabulation weights; trucks with some commercial use. Source: US Census "
             "Vehicle Inventory and Use Survey 2021 PUF.", fontsize=7, color=ps.MUTED)
    fig.tight_layout()
    ps.save(fig, "fig13_vius_duty_cycle")


def main() -> None:
    ps.use()
    co2_figure()
    vius_figure()


if __name__ == "__main__":
    main()
