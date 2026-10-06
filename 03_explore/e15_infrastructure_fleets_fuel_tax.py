"""Charging infrastructure, fleet structure and fuel taxation.

fig25_infra_fleets_fuel_tax  (a) US electric charging sites that accept medium or heavy vehicles,
                             by opening year (AFDC); (b) US motor carriers and power units by fleet
                             size (FMCSA); (c) effective carbon rates on road diesel vs gasoline,
                             2023, selected countries (OECD)
"""
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import plot_style as ps  # noqa: E402
from config import PROC_DIR  # noqa: E402

SHOW = {"CHE": "Switzerland", "GBR": "United Kingdom", "DEU": "Germany", "FRA": "France", "NLD": "Netherlands",
        "SWE": "Sweden", "ESP": "Spain", "POL": "Poland", "MEX": "Mexico", "ZAF": "South Africa", "KOR": "Korea",
        "AUS": "Australia", "CAN": "Canada", "IND": "India", "CHN": "China", "TUR": "Turkiye", "JPN": "Japan",
        "ARG": "Argentina", "IDN": "Indonesia", "BRA": "Brazil", "NZL": "New Zealand", "CHL": "Chile"}


def main() -> None:
    ps.use()
    s = pd.read_csv(PROC_DIR / "us_hd_stations.csv")
    e = s[(s.fuel_group == "Electric") & s.open_year.between(2015, 2026)]
    by = e.pivot_table(index="open_year", columns="maximum_vehicle_class", values="stations", aggfunc="sum").fillna(0)
    el = s[s.fuel_group == "Electric"]
    f = pd.read_csv(PROC_DIR / "us_fleet_size_bins.csv")
    fb = f.groupby("fleet_size", sort=False)[["carriers", "power_units"]].sum()
    fb = 100 * fb / fb.sum()
    c = pd.read_csv(PROC_DIR / "carbon_rates_road_fuels.csv")
    c = c[c.year == 2023].pivot_table(index="iso3", columns="fuel", values="ECRATE")
    allc = c.dropna(subset=["DIES", "GASO"])
    c = allc.loc[allc.index.intersection(list(SHOW))].sort_values("DIES")

    fig, axes = plt.subplots(1, 3, figsize=(11.5, 3.9), gridspec_kw={"width_ratios": [1, 1.1, 1]})
    bottom = pd.Series(0.0, index=by.index)
    for cls, col, name in (("MD", ps.SLOTS[0], "Medium-duty access"), ("HD", ps.SLOTS[1], "Heavy-duty access")):
        axes[0].bar(by.index, by.get(cls, 0), bottom=bottom, color=col, width=0.7, label=name, edgecolor="white",
                    linewidth=1.0)
        bottom += by.get(cls, 0)
    axes[0].legend(loc="upper left", fontsize=7)
    axes[0].set_xticks(range(2015, 2027, 2))
    axes[0].set_title("(a) US charging sites accepting medium\nor heavy vehicles, by opening year")
    axes[0].annotate(f"{int(el.stations.sum()):,} sites: {int(el.level2_only.sum())} Level 2 only,\n"
                     f"{int(el.ccs.sum())} with CCS, {int(el.mcs.sum())} with MCS (SAE J3271)", (0.03, 0.62),
                     xycoords="axes fraction", fontsize=7, color=ps.INK_2)
    x = range(len(fb))
    axes[1].bar([i - 0.2 for i in x], fb.carriers, width=0.4, color=ps.SLOTS[0], label="Share of carriers")
    axes[1].bar([i + 0.2 for i in x], fb.power_units, width=0.4, color=ps.SLOTS[1], label="Share of power units")
    axes[1].set_xticks(list(x))
    axes[1].set_xticklabels(fb.index, fontsize=7)
    axes[1].set_xlabel("Power units per carrier")
    axes[1].legend(loc="upper right", fontsize=7)
    axes[1].set_title("(b) US active motor carriers and power\nunits by fleet size (%)")
    y = range(len(c))
    axes[2].hlines(list(y), c.DIES, c.GASO, color=ps.GRID, linewidth=2)
    axes[2].scatter(c.DIES, list(y), color=ps.SLOTS[0], s=18, zorder=3, label="Diesel")
    axes[2].scatter(c.GASO, list(y), color=ps.SLOTS[1], s=18, zorder=3, label="Gasoline")
    axes[2].set_yticks(list(y))
    axes[2].set_yticklabels([SHOW[i] for i in c.index], fontsize=7)
    axes[2].grid(axis="x", color=ps.GRID, linewidth=0.6)
    axes[2].grid(axis="y", visible=False)
    axes[2].legend(loc="lower right", fontsize=7)
    axes[2].set_xlabel("EUR per tonne of CO2")
    axes[2].set_title("(c) Effective carbon rate on road fuels,\n2023 (taxes and ETS)")
    fig.text(0.0, -0.08, "(a) AFDC stations with a maximum vehicle class of MD or HD, all statuses and access types; 2026 to date; "
             "opening year as reported. (b) Active carriers with a plausible power-unit count (see c29). (c) Fuel excise, "
             "carbon taxes and ETS\nprices per tonne of CO2; the United States is not covered. Sources: NREL/DOE AFDC; FMCSA "
             "Company Census File; OECD Effective Carbon Rates.", fontsize=7, color=ps.MUTED)
    fig.tight_layout()
    ps.save(fig, "fig25_infra_fleets_fuel_tax")
    print(by.astype(int).to_string())
    print(fb.round(1).to_string())
    print(f"carbon rates 2023: {len(allc)} countries; diesel < gasoline in {(allc.DIES < allc.GASO).sum()}; "
          f"median diesel {allc.DIES.median():.0f}, gasoline {allc.GASO.median():.0f} EUR/tCO2")


if __name__ == "__main__":
    main()
