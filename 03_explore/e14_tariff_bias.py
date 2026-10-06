"""Environmental bias in vehicle tariffs: applied MFN tariffs on electric versus diesel
vehicles across countries (WITS TRAINS; latest year per country, 2022-2023 for HS 2022 lines).

fig24_tariff_bias  (a) share of countries where the electric line's tariff is lower, equal
                   or higher than the diesel counterpart, by vehicle type; (b) electric vs
                   medium/heavy diesel truck tariffs by country
tab_tariff_bias.tex  mean tariffs, gaps and shares by vehicle type

Also prints a transposition check: whether the new electric-truck line (HS 2022) took the rate
of the residual "other trucks" line (870490) that held electric trucks before 2022.
"""
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import plot_style as ps  # noqa: E402
from config import PROC_DIR, RAW_DIR, TAB_DIR  # noqa: E402

PAIRS = {"truck": "Trucks (vs diesel >5 t)", "tractor": "Road tractors", "bus": "Buses", "car": "Cars",
         "input": "Li-ion battery vs diesel engine"}
SIGNS = {"electric lower": ps.SLOTS[0], "equal": ps.OTHER, "electric higher": ps.SLOTS[1]}
LABEL = {"USA": "United States", "EUU": "EU", "CHN": "China", "IND": "India", "BRA": "Brazil", "VNM": "Viet Nam",
         "MEX": "Mexico", "IDN": "Indonesia", "THA": "Thailand", "KOR": "Korea", "JPN": "Japan", "AUS": "Australia",
         "ZAF": "South Africa", "TUR": "Turkiye", "CAN": "Canada", "ARG": "Argentina", "EGY": "Egypt",
         "PHL": "Philippines", "MYS": "Malaysia", "CHL": "Chile", "COL": "Colombia", "NGA": "Nigeria"}


def transposition() -> pd.DataFrame:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "02_build"))
    from b16_tariff_gaps import WITS_EXTRA
    from countries import iso3_from_m49
    w = pd.read_csv(RAW_DIR / "wits_tariffs" / "mfn_tariffs_vehicles.csv")
    w["iso3"] = w.reporter_m49.map(lambda c: WITS_EXTRA.get(int(c)) or iso3_from_m49(c))
    t = w.pivot_table(index=["iso3", "year"], columns="hs6", values="mfn_simple_avg").reset_index()
    new = t[t[870460].notna()].sort_values("year").groupby("iso3").first()  # first HS 2022 year
    old = t[t[870490].notna() & t[870460].isna()].sort_values("year").groupby("iso3").last()  # last HS 2017 year
    x = pd.DataFrame({"electric": new[870460], "diesel": new[[870422, 870423]].mean(axis=1),
                      "other_before": old[870490]}).dropna()
    x["equal_other_before"] = (x.electric - x.other_before).abs() <= 0.5
    x["equal_diesel"] = (x.electric - x.diesel).abs() <= 0.5
    x["electric_higher"] = x.electric > x.diesel + 0.5
    print(f"transposition ({len(x)} countries): electric = old 'other' line {x.equal_other_before.mean():.0%}, "
          f"= diesel {x.equal_diesel.mean():.0%}; where electric > diesel ({x.electric_higher.sum()}): "
          f"= old 'other' {x[x.electric_higher].equal_other_before.mean():.0%}")
    return x


def main() -> None:
    ps.use()
    d = pd.read_csv(PROC_DIR / "tariff_gaps_country_year.csv")
    last = d.sort_values("year").groupby(["iso3", "pair"]).tail(1)
    sh = last.groupby("pair").sign.value_counts(normalize=True).unstack().reindex(list(PAIRS))[list(SIGNS)] * 100
    n = last.groupby("pair").size().reindex(list(PAIRS))
    t = last[last.pair == "truck"]

    fig, axes = plt.subplots(1, 2, figsize=(9.6, 3.9), gridspec_kw={"width_ratios": [1.15, 1]})
    left = pd.Series(0.0, index=sh.index)
    ypos = range(len(sh))[::-1]
    for s, col in SIGNS.items():
        axes[0].barh(list(ypos), sh[s], left=left, color=col, height=0.6, label=s.capitalize(), edgecolor="white",
                     linewidth=1.5)
        for y, v, l0 in zip(ypos, sh[s], left):
            if v >= 8:
                axes[0].annotate(f"{v:.0f}%", (l0 + v / 2, y), ha="center", va="center", fontsize=7,
                                 color="white" if s != "equal" else ps.INK)
        left += sh[s]
    axes[0].set_yticks(list(ypos))
    axes[0].set_yticklabels([f"{PAIRS[p]} (n={n[p]})" for p in sh.index], fontsize=7.5)
    axes[0].set_xlim(0, 100)
    axes[0].grid(False)
    axes[0].legend(loc="upper center", bbox_to_anchor=(0.45, -0.08), ncol=3, fontsize=7)
    axes[0].set_title("(a) Electric line's MFN tariff relative to the\ndiesel counterpart (% of countries)")
    axes[1].scatter(t.tariff_conventional, t.tariff_electric, s=14, color=ps.SLOTS[0], alpha=0.75,
                    edgecolor="white", linewidth=0.5)
    lim = max(t.tariff_conventional.max(), t.tariff_electric.max()) + 3
    axes[1].plot([0, lim], [0, lim], color=ps.MUTED, linewidth=0.8, linestyle="--")
    axes[1].annotate("equal tariffs", (33, 33), xytext=(6, -8), textcoords="offset points", fontsize=7,
                     color=ps.MUTED, ha="left")
    show = t[t.iso3.isin(["USA", "EUU", "CHN", "IND", "BRA", "VNM", "MEX", "IDN", "THA", "KOR", "TUR", "ZAF", "ARG",
                          "EGY", "AUS", "PHL"])]
    show = show.groupby(["tariff_conventional", "tariff_electric"]).iso3.agg(
        lambda s: ", ".join(LABEL.get(i, i) for i in sorted(s))).reset_index()  # coincident points share a label
    for _, r in show.iterrows():
        right = r.tariff_conventional > 0.8 * lim
        dy = -8 if r.iso3 == "Philippines" else 2
        axes[1].annotate(r.iso3, (r.tariff_conventional, r.tariff_electric), xytext=(-3 if right else 3, dy),
                         textcoords="offset points", fontsize=6.5, color=ps.INK_2, ha="right" if right else "left")
    axes[1].set_xlim(-1, lim)
    axes[1].set_ylim(-1, lim)
    axes[1].set_xlabel("Diesel trucks >5 t (HS 8704.22-.23), %")
    axes[1].set_ylabel("Electric trucks (HS 8704.60), %")
    axes[1].grid(axis="x", color=ps.GRID, linewidth=0.6)
    axes[1].set_title("(b) Electric vs diesel truck tariffs\nby country (simple averages)")
    fig.text(0.0, -0.1, "Applied MFN tariffs, simple average of national tariff lines within each HS6 code, latest "
             "year available (2023; 2022 for some). Equal = within 0.5 percentage points. The EU is one reporter.\n"
             "Source: World Bank WITS/UNCTAD TRAINS; own calculations.", fontsize=7, color=ps.MUTED)
    fig.tight_layout()
    ps.save(fig, "fig24_tariff_bias")

    g = last.groupby("pair").agg(n=("iso3", "size"), electric=("tariff_electric", "mean"),
                                 conventional=("tariff_conventional", "mean"), gap=("gap", "mean"),
                                 median_gap=("gap", "median")).reindex(list(PAIRS))
    tab = g.join(sh.round(0))
    tab.index = [PAIRS[p] for p in tab.index]
    tab.columns = ["Countries", "Electric (%)", "Diesel (%)", "Mean gap (pp)", "Median gap (pp)", "Electric lower (%)",
                   "Equal (%)", "Electric higher (%)"]
    tab.to_latex(TAB_DIR / "tab_tariff_bias.tex", float_format="%.1f", position="htbp", label="tab:tariffbias",
                 escape=True,
                 caption="Applied MFN tariffs on electric and diesel vehicles, latest year per country (WITS TRAINS, "
                 "simple averages of national lines).")
    print(tab.round(1).to_string())
    cov = pd.read_csv(PROC_DIR / "country_year_covariates.csv", usecols=["iso3", "year", "income"]).dropna()
    inc = cov.sort_values("year").groupby("iso3").income.last()
    t = t.assign(income=t.iso3.map(inc).fillna("not classified (EU, territories)"))
    print(t.groupby("income").sign.value_counts(normalize=True).unstack().round(2).to_string())
    print(t.loc[t.iso3.isin(LABEL), ["iso3", "year", "tariff_electric", "tariff_conventional", "gap"]].round(1).to_string())
    transposition()


if __name__ == "__main__":
    main()
