"""Heavy-duty and freight policies worldwide (IEA Policies database, tagged in b14).

fig22_iea_heavy_policies  (a) new heavy-duty/freight policies per year by instrument group;
                          (b) first year of each instrument group for the countries with the
                          most heavy-duty/freight policies (policy sequencing)
tab_policy_sequencing.tex share of countries whose first heavy-duty purchase incentive
                          precedes their first standard or mandate, and similar pairs
"""
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import plot_style as ps  # noqa: E402
from config import PROC_DIR, TAB_DIR  # noqa: E402

# exclusive groups, assigned in this priority order (a policy with several themes goes to the first)
GROUPS = {
    "Standards and mandates": (["vehicle_standard", "zev_mandate_phaseout"], ps.SLOTS[0]),
    "Pricing and road access": (["fuel_tax_carbon_price", "road_pricing_access"], ps.SLOTS[1]),
    "Purchase incentives, procurement": (["vehicle_purchase_incentive", "public_procurement_fleet"], ps.SLOTS[2]),
    "Charging, hydrogen, fuels, grid": (["charging_infrastructure", "hydrogen", "alternative_fuels", "grid_power"],
                                        ps.SLOTS[3]),
    "Industry, trade, minerals": (["trade_industrial", "battery_industry", "critical_minerals"], ps.SLOTS[6]),
}
OTHER = "Rail, urban, other"
NAMES = {"USA": "United States", "CAN": "Canada", "DEU": "Germany", "CHN": "China", "FRA": "France",
         "GBR": "United Kingdom", "JPN": "Japan", "KOR": "Korea", "IND": "India", "NLD": "Netherlands",
         "SWE": "Sweden", "ESP": "Spain", "ITA": "Italy", "NOR": "Norway", "AUS": "Australia", "PRT": "Portugal",
         "AUT": "Austria", "CHE": "Switzerland", "NZL": "New Zealand", "CHL": "Chile", "BRA": "Brazil",
         "DNK": "Denmark", "FIN": "Finland", "BEL": "Belgium", "IRL": "Ireland", "POL": "Poland", "LTU": "Lithuania",
         "CZE": "Czechia", "ISR": "Israel", "MEX": "Mexico", "IDN": "Indonesia", "THA": "Thailand", "ZAF": "South Africa"}


def load() -> pd.DataFrame:
    p = pd.read_csv(PROC_DIR / "iea_policies_themes.csv", low_memory=False)
    p = p[(p.heavy_freight == 1) & (p.status != "Announced")]
    p["group"] = OTHER
    for g, (cols, _) in reversed(list(GROUPS.items())):
        p.loc[p[cols].sum(axis=1) > 0, "group"] = g
    return p


def sequencing(p: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    long = p.assign(iso3=p.iso3.fillna("").str.split(";")).explode("iso3")
    long["iso3"] = long.iso3.str.strip()
    long = long[(long.iso3.str.len() == 3) & long.year.notna()]
    first = long[long.group != OTHER].groupby(["iso3", "group"]).year.min().unstack()
    n = long.groupby("iso3").size()
    pairs = [("Purchase incentives, procurement", "Standards and mandates"),
             ("Purchase incentives, procurement", "Pricing and road access"),
             ("Charging, hydrogen, fuels, grid", "Standards and mandates"),
             ("Standards and mandates", "Pricing and road access")]
    rows = []
    for a, b in pairs:
        both = first[[a, b]].dropna()
        rows.append({"First instrument": a, "Second instrument": b, "Countries with both": len(both),
                     "First earlier (%)": 100 * (both[a] < both[b]).mean(),
                     "Same year (%)": 100 * (both[a] == both[b]).mean(),
                     "Later (%)": 100 * (both[a] > both[b]).mean()})
    tab = pd.DataFrame(rows).set_index(["First instrument", "Second instrument"])
    tab.to_latex(TAB_DIR / "tab_policy_sequencing.tex", float_format="%.0f", position="htbp", escape=True,
                 label="tab:sequencing", caption="Order of adoption of heavy-duty and freight policy instruments: "
                 "among countries with both instruments in the IEA Policies database, the share whose first measure "
                 "of the first type precedes, coincides with or follows the first measure of the second type.")
    return first.join(n.rename("n")), tab


def main() -> None:
    ps.use()
    p = load()
    y = p[p.year.between(2010, 2025)].groupby(["year", "group"]).size().unstack(fill_value=0)
    order = list(GROUPS) + [OTHER]
    first, tab = sequencing(p)
    top = first[first.n >= 8].sort_values("n", ascending=False).head(16).iloc[::-1]

    fig, axes = plt.subplots(1, 2, figsize=(9.6, 4.4), gridspec_kw={"width_ratios": [1.25, 1]})
    bottom = pd.Series(0.0, index=y.index)
    for g in order:
        col = GROUPS[g][1] if g in GROUPS else ps.OTHER
        axes[0].bar(y.index, y.get(g, 0), bottom=bottom, color=col, width=0.75, label=g, edgecolor="white",
                    linewidth=1.0)
        bottom += y.get(g, 0)
    for yr, tot in bottom.items():
        if yr in (2015, 2020, 2021, 2024):
            axes[0].annotate(f"{tot:.0f}", (yr, tot), xytext=(0, 2), textcoords="offset points", ha="center",
                             fontsize=7, color=ps.INK_2)
    axes[0].legend(loc="upper left", fontsize=7)
    axes[0].set_title("(a) New heavy-duty and freight policies per year,\nby instrument group")
    axes[0].set_xticks(range(2010, 2026, 5))
    marks = {"Purchase incentives, procurement": "o", "Charging, hydrogen, fuels, grid": "s",
             "Standards and mandates": "D", "Pricing and road access": "^"}
    for g, m in marks.items():
        axes[1].scatter(top[g], range(len(top)), marker=m, s=28, color=GROUPS[g][1], label=g, zorder=3,
                        edgecolor="white", linewidth=0.8)
    axes[1].set_yticks(range(len(top)))
    axes[1].set_yticklabels([NAMES.get(i, i) for i in top.index], fontsize=7.5)
    axes[1].grid(axis="x", color=ps.GRID, linewidth=0.6)
    axes[1].set_xlim(1985, 2027)
    axes[1].legend(loc="lower left", fontsize=6.5, handletextpad=0.2)
    axes[1].set_title("(b) First year of each instrument, countries\nwith the most heavy-duty/freight policies")
    fig.text(0.0, -0.06, "Policies whose title or description names trucks, lorries, buses, heavy-duty or commercial "
             "vehicles, freight or logistics (562 of 13,200), excluding announced-only measures. A policy with several "
             "themes is counted\nonce, in the first group listed. Source: IEA Policies database (accessed Oct 2026); "
             "own tagging.", fontsize=7, color=ps.MUTED)
    fig.tight_layout()
    ps.save(fig, "fig22_iea_heavy_policies")
    print(y.loc[[2015, 2020, 2021, 2024, 2025]].to_string())
    print(tab.round(0).to_string())
    print(p.group.value_counts().to_string())


if __name__ == "__main__":
    main()
