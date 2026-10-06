"""Policy patterns linking trade exposure, technical regulation and adoption.

fig26_tbt_exposure_policy  (a) EV, battery and charging TBT notifications (2021-2025) against
                           imports of electric vehicles from China in 2023, by importer;
                           (b) battery-electric share of new trucks >7.5 t in Jul 2024-Jun 2025
                           by European country, by whether a national purchase incentive or a
                           CO2-differentiated toll was in force (policy database, 2024Q4)
"""
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import plot_style as ps  # noqa: E402
from config import PROC_DIR  # noqa: E402
from countries import EU27  # noqa: E402

EV_HS = [870380, 870240, 870460]  # electric cars, buses, trucks
NAMES = {"EUU": "EU", "GBR": "UK", "AUS": "Australia", "THA": "Thailand", "CAN": "Canada", "ISR": "Israel",
         "ARE": "UAE", "NOR": "Norway", "KOR": "Korea", "BRA": "Brazil", "JPN": "Japan", "USA": "US", "CHL": "Chile",
         "MEX": "Mexico", "UZB": "Uzbekistan", "RUS": "Russia", "IND": "India", "TUR": "Turkiye", "NZL": "New Zealand",
         "HKG": "Hong Kong", "KGZ": "Kyrgyzstan", "JOR": "Jordan", "MYS": "Malaysia", "CHE": "Switzerland",
         "SAU": "Saudi Arabia", "PHL": "Philippines", "TWN": "Chinese Taipei", "EGY": "Egypt", "IDN": "Indonesia", "VNM": "Viet Nam", "ZAF": "South Africa"}
EUROPE = {"NOR": "Norway", "SWE": "Sweden", "NLD": "Netherlands", "DEU": "Germany", "FIN": "Finland",
          "FRA": "France", "AUT": "Austria", "DNK": "Denmark", "BEL": "Belgium", "ESP": "Spain", "CZE": "Czechia",
          "HUN": "Hungary", "POL": "Poland", "IRL": "Ireland", "ROU": "Romania", "SVK": "Slovakia", "PRT": "Portugal",
          "SVN": "Slovenia", "BGR": "Bulgaria", "LTU": "Lithuania", "GRC": "Greece", "HRV": "Croatia",
          "LVA": "Latvia", "EST": "Estonia", "LUX": "Luxembourg"}


def exposure() -> pd.DataFrame:
    tr = pd.read_csv(PROC_DIR / "trade_flows_hs6.csv.gz", usecols=["year", "exporter_iso3", "importer_iso3", "hs6",
                                                                     "value_usd"])
    ev = tr[tr.hs6.isin(EV_HS) & (tr.year == 2023)].copy()
    ev["importer"] = np.where(ev.importer_iso3.isin(EU27), "EUU", ev.importer_iso3)
    ev = ev[~((ev.importer == "EUU") & ev.exporter_iso3.isin(EU27))]  # extra-EU imports only
    x = pd.DataFrame({"from_china": ev[ev.exporter_iso3 == "CHN"].groupby("importer").value_usd.sum(),
                      "total": ev.groupby("importer").value_usd.sum()}).fillna(0)
    t = pd.read_csv(PROC_DIR / "tbt_vehicle_member_year.csv")
    n = t[t.year.between(2021, 2025)].groupby("iso3").ev_battery_charging.sum()
    x["ev_tbt"] = n.reindex(x.index).fillna(0)
    return x[x.total > 50e6]


def adoption() -> pd.DataFrame:
    r = pd.read_csv(PROC_DIR / "eu_hdv_registrations.csv")
    t = r[(r.segment == "Truck") & r.mass_class.isin(["7.5-16t", "16-26t", ">26t"]) & (r.period == 2024)]
    g = t.groupby("iso3").agg(n=("vehicles", "sum"),
                              bev=("vehicles", lambda s: s[t.loc[s.index, "powertrain"] == "Battery electric"].sum()))
    g["share"] = 100 * g.bev / g.n
    p = pd.read_csv(PROC_DIR / "policy_long_active.csv")
    nat = p[(p.quarter == "2024Q4") & ~p.policy_id.str.startswith(("EU_", "INT_", "GLB_")) &
            p.family.isin(["purchase_incentive", "road_charging_advantage"])]
    g["national_policy"] = g.index.isin(nat.country.unique())
    return g[(g.n >= 1000) & g.index.isin(list(EUROPE)) & (g.index != "ITA")].sort_values("share")


def main() -> None:
    ps.use()
    x = exposure()
    a = adoption()
    fig, axes = plt.subplots(1, 2, figsize=(10.2, 4.2), gridspec_kw={"width_ratios": [1.15, 1]})
    any_tbt = x.ev_tbt > 0
    axes[0].scatter(x.from_china[any_tbt] / 1e6, x.ev_tbt[any_tbt], s=22, color=ps.SLOTS[0], label="Notified >=1",
                    edgecolor="white", linewidth=0.5, zorder=3)
    axes[0].scatter(x.from_china[~any_tbt] / 1e6, x.ev_tbt[~any_tbt], s=22, color=ps.OTHER, label="None notified",
                    edgecolor="white", linewidth=0.5, zorder=3)
    lab = x[(x.ev_tbt >= 5) | ((x.from_china >= 2e9) & any_tbt)]
    for iso, r in lab.iterrows():
        axes[0].annotate(NAMES.get(iso, iso), (r.from_china / 1e6, r.ev_tbt), xytext=(3, 2), textcoords="offset points",
                         fontsize=6.5, color=ps.INK_2)
    axes[0].set_xscale("log")
    axes[0].set_xlabel("Imports of electric vehicles from China, 2023 (USD million, log scale)")
    axes[0].set_ylabel("Notifications 2021-2025")
    axes[0].legend(loc="upper left", fontsize=7)
    axes[0].grid(axis="x", color=ps.GRID, linewidth=0.6)
    axes[0].set_title("(a) TBT notifications on EVs, batteries and\ncharging vs imports of Chinese EVs")
    cols = np.where(a.national_policy, ps.SLOTS[0], ps.OTHER)
    axes[1].barh([EUROPE[i] for i in a.index], a.share, color=cols, height=0.65)
    for i, (sh, n) in enumerate(zip(a.share, a.n)):
        axes[1].annotate(f"{sh:.1f}%", (sh, i), xytext=(3, 0), textcoords="offset points", va="center", fontsize=6.5,
                         color=ps.INK_2)
    axes[1].tick_params(axis="y", labelsize=7)
    axes[1].grid(axis="x", color=ps.GRID, linewidth=0.6)
    axes[1].grid(axis="y", visible=False)
    axes[1].set_xlim(0, a.share.max() * 1.2)
    from matplotlib.patches import Patch
    axes[1].legend(handles=[Patch(color=ps.SLOTS[0], label="National purchase incentive or CO2 toll"),
                            Patch(color=ps.OTHER, label="Neither")], loc="lower right", fontsize=7)
    axes[1].set_title("(b) Battery-electric share of new trucks >7.5 t,\nJul 2024-Jun 2025 (%)")
    fig.text(0.0, -0.08, "(a) Importers with more than USD 50 million of EV imports (HS 8703.80, 8702.40, 8704.60) in 2023; "
             "the EU is one importer (extra-EU trade). No notifications from Norway, Hong Kong,\nJordan, Uzbekistan, "
             "Kyrgyzstan or Russia despite large imports. (b) Countries with at least 1,000 new trucks >7.5 t; Italy omitted (no electric flag in 2024-25). "
             "Policies in force in 2024Q4 from the project's\npolicy database, which may miss smaller national schemes. "
             "Sources: BACI; WTO ePing; EEA; own coding.",
             fontsize=7, color=ps.MUTED)
    fig.tight_layout()
    ps.save(fig, "fig26_tbt_exposure_policy")
    x["tercile"] = pd.qcut(x.from_china.rank(method="first"), 3, labels=["low", "mid", "high"])
    print(x.groupby("tercile", observed=True).agg(n=("ev_tbt", "size"), any_tbt=("ev_tbt", lambda s: (s > 0).mean()),
                                                  mean_tbt=("ev_tbt", "mean")).round(2).to_string())
    print(a.groupby("national_policy")[["share", "bev", "n"]].apply(
        lambda g: pd.Series({"countries": len(g), "mean_share": g.share.mean(),
                             "pooled_share": 100 * g.bev.sum() / g.n.sum()})).round(2).to_string())


if __name__ == "__main__":
    main()
