"""European adoption and its candidate drivers (Eurostat registrations, energy prices).

fig03_eu_zev_share_segments  ZEV share of new road tractors and of rigid lorries >3.5 t,
                             2018-2025; Switzerland, Netherlands, Germany highlighted
fig04_energy_cost_vs_zev     2025 ZEV share of new heavy trucks vs electricity/diesel
                             per-km energy-cost ratio (one point per country)
fig05_diesel_price_shock     diesel prices 2019-2026: EU with/without taxes; EU vs US index
tab_eu_drivers_2025.tex      table twin of fig04
"""
import sys
from pathlib import Path

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import plot_style as ps  # noqa: E402
from config import PROC_DIR, TAB_DIR  # noqa: E402

HIGHLIGHT = {"CHE": ("Switzerland", ps.SLOTS[0]), "NLD": ("Netherlands", ps.SLOTS[1]),
             "DEU": ("Germany", ps.SLOTS[2])}


def fig03(reg: pd.DataFrame) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(9.2, 3.5), sharey=False)
    for ax, seg in zip(axes, ("Road tractors", "Lorries >3.5 t")):
        s = reg[(reg.segment == seg) & (reg.year >= 2018) & (reg.total >= 300)]
        for iso, g in s.groupby("iso3"):
            if iso not in HIGHLIGHT:
                ax.plot(g.year, 100 * g.zev_share, color=ps.OTHER, linewidth=0.8, alpha=0.6, zorder=1)
        for iso, (name, col) in HIGHLIGHT.items():
            g = s[s.iso3 == iso]
            if g.empty:
                continue
            ax.plot(g.year, 100 * g.zev_share, color=col, marker="o", markersize=3.5, label=name, zorder=3)
            ps.label_end(ax, g.year.iloc[-1], 100 * g.zev_share.iloc[-1],
                         f"{name} {100 * g.zev_share.iloc[-1]:.0f}%")
        ax.set_xlim(2018, 2027.9)
        ax.set_xticks(range(2018, 2026, 1))
        ax.tick_params(axis="x", labelsize=7)
        ax.set_title(f"({'a' if seg == 'Road tractors' else 'b'}) {seg}: ZEV share of new registrations (%)")
    axes[0].plot([], [], color=ps.OTHER, linewidth=0.8, label="Other European countries")
    axes[0].legend(loc="upper left")
    fig.text(0.0, -0.04, "ZEV = battery-electric + fuel-cell. Countries with >=300 new registrations a year. "
             "Source: Eurostat road_eqr_tracmot, road_eqr_lormot.", fontsize=7, color=ps.MUTED)
    fig.tight_layout()
    ps.save(fig, "fig03_eu_zev_share_segments")


def fig04(reg: pd.DataFrame, gap: pd.DataFrame) -> pd.DataFrame:
    heavy = (reg[(reg.year == 2025) & reg.segment.isin(["Road tractors", "Lorries >3.5 t"])]
             .groupby("iso3")[["zev", "total"]].sum())
    heavy = heavy[heavy.total >= 500]
    heavy["zev_share"] = 100 * heavy.zev / heavy.total
    g = gap[gap.period.str.startswith("2025")].groupby("iso3")[
        ["elec_to_diesel_cost_ratio", "diesel_eur_100km", "elec_eur_100km"]].mean()
    d = heavy.join(g, how="inner").dropna(subset=["elec_to_diesel_cost_ratio"])
    fig, ax = plt.subplots(figsize=(6.2, 4.0))
    ax.scatter(d.elec_to_diesel_cost_ratio, d.zev_share, s=28, color=ps.SLOTS[0],
               edgecolor="white", linewidth=1, zorder=3)
    nudge = {"BGR": (4, -9), "HRV": (6, 7), "POL": (-6, -10), "SVK": (4, 4), "LTU": (4, -8),
             "EST": (2, 5)}
    for iso, r in d.iterrows():
        ax.annotate(iso, (r.elec_to_diesel_cost_ratio, r.zev_share), xytext=nudge.get(iso, (4, 2)),
                    textcoords="offset points", fontsize=7, color=ps.INK_2)
    b = np.polyfit(d.elec_to_diesel_cost_ratio, d.zev_share, 1)
    xs = np.linspace(d.elec_to_diesel_cost_ratio.min(), d.elec_to_diesel_cost_ratio.max(), 20)
    ax.plot(xs, np.polyval(b, xs), color=ps.MUTED, linewidth=1)
    rho = d[["elec_to_diesel_cost_ratio", "zev_share"]].corr().iloc[0, 1]
    ax.set_xlabel("Electric / diesel energy cost per km, 2025 (industrial power, diesel ex-VAT)")
    ax.set_ylabel("ZEV share of new heavy trucks, 2025 (%)")
    ax.set_title(f"Energy-cost advantage explains little of the cross-country gap (r = {rho:.2f})")
    ax.grid(axis="x", visible=True)
    fig.text(0.0, -0.06, "Heavy trucks = road tractors + rigid lorries >3.5 t (Eurostat). Energy cost: 31 L/100 km "
             "diesel vs 120 kWh/100 km electric; electricity band 2-20 GWh/yr excl. VAT.", fontsize=7, color=ps.MUTED)
    fig.tight_layout()
    ps.save(fig, "fig04_energy_cost_vs_zev")
    return d


def fig05() -> None:
    w = pd.read_csv(PROC_DIR / "diesel_prices_eu_weekly.csv", parse_dates=["date"])
    eu = w[(w.iso3 == "EU27") & (w.date >= "2019-01-01")].sort_values("date")
    m = pd.read_csv(PROC_DIR / "diesel_prices_monthly.csv", parse_dates=["month"])
    m = m[m.month >= "2019-01-01"]
    fig, axes = plt.subplots(1, 2, figsize=(9.2, 3.4))
    ax = axes[0]
    ax.plot(eu.date, eu.diesel_eur_l, color=ps.SLOTS[0], label="With taxes")
    ax.plot(eu.date, eu.diesel_net_eur_l, color=ps.SLOTS[1], label="Net of taxes")
    ax.set_title("(a) EU-27 diesel price, weekly (EUR per litre)")
    ax.legend(loc="upper left")
    ax2 = axes[1]
    base = {}
    for iso, lab, col in (("EU27", "EU-27 (EUR)", ps.SLOTS[0]), ("USA", "United States (USD)", ps.SLOTS[2])):
        s = m[m.iso3 == iso].set_index("month")["diesel_eur_l" if iso == "EU27" else "diesel_usd_l"].dropna()
        base[iso] = s.loc["2026-01-01"]
        idx = 100 * s / base[iso]
        ax2.plot(idx.index, idx.values, color=col, label=lab)
        ps.label_end(ax2, idx.index[-1], idx.values[-1], f"{idx.values[-1]:.0f}")
    ax2.axhline(100, color=ps.BASELINE, linewidth=0.8)
    ax2.set_title("(b) Diesel price index, Jan 2026 = 100 (monthly)")
    ax2.legend(loc="upper left")
    for a in axes:
        for dte, txt in (("2022-02-24", "Ukraine\ninvasion"), ("2026-02-01", "Hormuz\nclosure")):
            a.axvline(pd.Timestamp(dte), color=ps.MUTED, linewidth=0.8)
            a.annotate(txt, (pd.Timestamp(dte), a.get_ylim()[0]), xytext=(3, 4), textcoords="offset points",
                       fontsize=7, color=ps.MUTED)
        a.xaxis.set_major_locator(mdates.YearLocator(2))
        a.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    fig.text(0.0, -0.04, "Sources: EC Weekly Oil Bulletin (EU-27 weighted average); US EIA No. 2 diesel retail "
             "price via FRED (GASDESW).", fontsize=7, color=ps.MUTED)
    fig.tight_layout()
    ps.save(fig, "fig05_diesel_price_shock")


def main() -> None:
    ps.use()
    reg = pd.read_csv(PROC_DIR / "eurostat_new_registrations_fuel.csv")
    gap = pd.read_csv(PROC_DIR / "energy_cost_gap_eu_semi.csv")
    fig03(reg)
    d = fig04(reg, gap)
    fig05()
    pol = pd.read_csv(PROC_DIR / "policy_country_quarter.csv")
    p25 = pol[pol.quarter == "2025Q4"].set_index("iso3")
    d["purchase_incentive"] = p25["purchase_incentive"].reindex(d.index).fillna(0).astype(int)
    d["road_charging_adv"] = p25["road_charging_advantage"].reindex(d.index).fillna(0).astype(int)
    tab = d.sort_values("zev_share", ascending=False)[
        ["total", "zev_share", "diesel_eur_100km", "elec_eur_100km", "elec_to_diesel_cost_ratio",
         "purchase_incentive", "road_charging_adv"]]
    tab.columns = ["New heavy trucks", "ZEV share (%)", "Diesel EUR/100km", "Electric EUR/100km",
                   "Cost ratio", "Purchase incentive", "Road-charge advantage"]
    tab.index.name = "Country"
    tab.to_latex(TAB_DIR / "tab_eu_drivers_2025.tex", escape=True, position="htbp", float_format="%.2f",
                 formatters={"New heavy trucks": "{:,.0f}".format}, label="tab:eudrivers",
                 caption="Heavy-truck ZEV shares and energy-cost gap, European countries, 2025")
    print(tab.round(2).to_string())


if __name__ == "__main__":
    main()
