"""Satellite NO2 around truck-policy and freight sites (TROPOMI monthly, 20 km means).

fig17_no2_contrasts  log NO2 gap between treated and comparison sites, monthly and 12-month
                     rolling mean: Dutch zero-emission-zone cities vs Belgian/German cities;
                     Chinese steel/port cities vs other large Chinese cities; China's vs
                     India's 25 largest steel plants; US container ports vs other large cities
tab_no2_gaps.tex     table twin: annual mean gaps

Gaps between groups difference out seasonality and common retrieval-version shifts; they do
not difference out local weather or output (e.g. steel production), so these are descriptive.
"""
import sys
from pathlib import Path

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import plot_style as ps  # noqa: E402
from config import PROC_DIR, TAB_DIR  # noqa: E402

CONTRASTS = [  # treated group, comparison group, panel title, events
    ("NL zero-emission zone city", "Comparison city (no ZE zone)",
     "(a) Dutch zero-emission-zone cities minus\nBelgian and German cities",
     [("2025-01-01", "ZE zones for\nnew trucks")]),
    ("China steel/port city", "China large city",
     "(b) Chinese steel and port cities minus\nother large Chinese cities",
     [("2019-04-01", "Steel ultra-low-\nemission policy")]),
    ("CHN top steel plant", "IND top steel plant",
     "(c) China's 25 largest steel plants minus\nIndia's 25 largest",
     [("2019-04-01", "Steel ultra-low-\nemission policy")]),
    ("US container port", "Other large city",
     "(d) US container ports minus\nother large cities (non-US)",
     [("2022-04-01", "LA/LB Clean\nTruck Fund rate")]),
]


def gaps() -> pd.DataFrame:
    d = pd.read_csv(PROC_DIR / "no2_points_monthly.csv", parse_dates=["month"])
    m = d.groupby(["month", "group"]).log_no2.mean().unstack()
    out = pd.DataFrame({title: m[a] - m[b] for a, b, title, _ in CONTRASTS})
    return out


def fig17(g: pd.DataFrame) -> None:
    fig, axes = plt.subplots(2, 2, figsize=(9.2, 6.0))
    for ax, (_, _, title, events) in zip(axes.flat, CONTRASTS):
        s = g[title].dropna()
        roll = s.rolling(12, min_periods=10).mean()
        ax.plot(s.index, s.values, color=ps.OTHER, linewidth=0.8, label="Monthly")
        ax.plot(roll.index, roll.values, color=ps.SLOTS[0], label="12-month mean")
        ps.label_end(ax, roll.index[-1], roll.values[-1], f"{roll.values[-1]:+.2f}")
        lo, hi = ax.get_ylim()
        ax.set_ylim(lo, hi + 0.2 * (hi - lo))  # headroom for event labels
        for dte, txt in events:
            ax.axvline(pd.Timestamp(dte), color=ps.MUTED, linewidth=0.8)
            ax.annotate(txt, (pd.Timestamp(dte), ax.get_ylim()[1]), xytext=(3, -3), textcoords="offset points",
                        va="top", fontsize=7, color=ps.MUTED)
        ax.set_title(title, fontsize=9)
        ax.xaxis.set_major_locator(mdates.YearLocator(2))
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
        ax.set_xlim(pd.Timestamp("2018-04-01"), pd.Timestamp("2027-06-01"))
    axes[0, 0].legend(loc="lower right")
    for ax in axes[:, 0]:
        ax.set_ylabel("Log NO2 gap (treated minus comparison)")
    fig.text(0.0, -0.05, "Tropospheric NO2 column, mean within 20 km of each site; group mean of log NO2; months "
             "with <50% valid cells dropped. Group gaps net out seasonality and retrieval-version shifts common "
             "to both groups,\nnot local weather or output. Sources: KNMI TEMIS (Sentinel-5P TROPOMI); steel plants "
             "by capacity from Climate TRACE.", fontsize=7, color=ps.MUTED)
    fig.tight_layout()
    ps.save(fig, "fig17_no2_contrasts")


def tab(g: pd.DataFrame) -> None:
    y = g[g.index < "2026-01-01"].groupby(g.index[g.index < "2026-01-01"].year).mean()
    y.columns = ["NL ZE cities - comparison", "CN steel/port - CN large", "CN plants - IN plants",
                 "US ports - other cities"]
    y.index.name = "Year"
    y.to_latex(TAB_DIR / "tab_no2_gaps.tex", escape=True, position="htbp", float_format="%.2f",
               label="tab:no2", caption="Annual mean log NO2 gap between treated and comparison sites "
                                        "(TROPOMI; 2018 covers May-December).")
    print(y.round(2).to_string())


def main() -> None:
    ps.use()
    g = gaps()
    fig17(g)
    tab(g)


if __name__ == "__main__":
    main()
