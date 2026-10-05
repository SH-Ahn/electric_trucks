"""North American truck trade and sales around the 2025-26 policy shocks.

fig07_north_america  (a) Canada's monthly exports and imports of medium and heavy trucks,
                         buses and other motor vehicles (CAD bn), 2023-2026
                     (b) US heavy-weight truck retail sales (SAAR, thousand), 2019-2026
"""
import sys
from pathlib import Path

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import plot_style as ps  # noqa: E402
from config import PROC_DIR  # noqa: E402

EVENTS = [("2025-09-30", "45W credit\nends"), ("2025-11-01", "Sec. 232\ntruck tariff")]


def mark(ax, events, ymax_frac=0.97) -> None:
    """Event lines; labels alternate left/right of their line so adjacent events don't collide."""
    for i, (d, txt) in enumerate(events):
        x = pd.Timestamp(d)
        ax.axvline(x, color=ps.MUTED, linewidth=0.8)
        y = ax.get_ylim()[0] + (ax.get_ylim()[1] - ax.get_ylim()[0]) * ymax_frac
        left = (len(events) - 1 - i) % 2 == 1
        ax.annotate(txt, (x, y), xytext=(-3 if left else 3, 0), textcoords="offset points",
                    ha="right" if left else "left", va="top", fontsize=7, color=ps.MUTED)


def main() -> None:
    ps.use()
    t = pd.read_csv(PROC_DIR / "canada_vehicle_trade_monthly.csv")
    t = t[t["product"].str.startswith("Medium and heavy")]
    t["month"] = pd.to_datetime(t["month"])
    t = t[t.month >= "2023-01-01"].pivot_table(index="month", columns="flow", values="value_cad") / 1e9
    us = pd.read_csv(PROC_DIR / "us_monthly_series.csv", parse_dates=["month"])
    us = us[us.month >= "2019-01-01"].set_index("month")["HTRUCKSSAAR"] * 1000

    fig, axes = plt.subplots(1, 2, figsize=(9.2, 3.4))
    ax = axes[0]
    ax.plot(t.index, t["Export"], color=ps.SLOTS[0], label="Exports (mostly to US)")
    ax.plot(t.index, t["Import"], color=ps.SLOTS[1], label="Imports")
    oct25, nov25 = t.loc["2025-10-01", "Export"], t.loc["2025-11-01", "Export"]
    ax.annotate(f"Oct 2025: {oct25:.2f}", (pd.Timestamp("2025-10-01"), oct25), xytext=(-60, 10),
                textcoords="offset points", fontsize=7, color=ps.INK_2)
    ax.annotate(f"Nov 2025: {nov25:.2f}", (pd.Timestamp("2025-11-01"), nov25), xytext=(4, -12),
                textcoords="offset points", fontsize=7, color=ps.INK_2)
    ax.set_ylim(0, t.max().max() * 1.35)
    mark(ax, EVENTS[1:], ymax_frac=0.8)
    ax.set_title("(a) Canada: medium/heavy trucks and buses, CAD bn per month")
    ax.legend(loc="upper left", ncol=2)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    ax.xaxis.set_major_locator(mdates.YearLocator())

    ax = axes[1]
    ax.plot(us.index, us.values, color=ps.SLOTS[0])
    ax.set_ylim(0, us.max() * 1.15)
    mark(ax, EVENTS)
    ps.label_end(ax, us.index[-1], us.values[-1], f"{us.values[-1]:.0f}k")
    ax.set_title("(b) US heavy truck sales (>14,000 lb), thousand, SAAR")
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    fig.text(0.0, -0.04, "Sources: Statistics Canada table 12-10-0163 (customs basis, unadjusted); "
             "BEA via FRED (HTRUCKSSAAR).", fontsize=7, color=ps.MUTED)
    fig.tight_layout()
    ps.save(fig, "fig07_north_america")
    pre = t.loc["2024-01-01":"2025-09-01", "Export"].mean()
    post = t.loc["2025-11-01":, "Export"].mean()
    print(f"Canada MHDV exports: mean Jan24-Sep25 {pre:.2f}bn, Nov25-latest {post:.2f}bn ({post / pre - 1:+.0%})")
    print(us.loc["2024-01-01":].resample("QS").mean().round(0).to_string())


if __name__ == "__main__":
    main()
