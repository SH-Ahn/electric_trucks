"""Technical barriers to trade in road vehicles (WTO TBT notifications, ePing).

fig21_tbt_vehicles  (a) regular TBT notifications on road vehicles, parts, batteries and
                    charging per year, by topic; (b) members notifying most measures on
                    EVs, batteries and charging, 2015-2026
"""
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import plot_style as ps  # noqa: E402
from config import PROC_DIR  # noqa: E402

TOPICS = {"safety_type_approval": ("Safety and type approval", ps.SLOTS[0]),
          "emissions_fuel_economy": ("Emissions and fuel economy", ps.SLOTS[1]),
          "ev_battery_charging": ("EVs, batteries, charging", ps.SLOTS[2]),
          "cyber_connectivity": ("Cyber and connectivity", ps.SLOTS[3])}


def main() -> None:
    ps.use()
    d = pd.read_csv(PROC_DIR / "tbt_vehicle_notifications.csv")
    r = d[(d.type == "Regular notification") & d.year.between(2000, 2025)]
    t = r.groupby("year")[list(TOPICS)].sum()
    e = d[(d.type == "Regular notification") & (d.ev_battery_charging == 1) & (d.year >= 2015)]
    top = e.member.replace({"United States of America": "United States", "Korea, Republic of": "Korea",
                            "Saudi Arabia, Kingdom of": "Saudi Arabia"}).value_counts().head(10).sort_values()
    fig, axes = plt.subplots(1, 2, figsize=(9.2, 3.6), gridspec_kw={"width_ratios": [1.5, 1]})
    ys = ps.spread([t[k].iloc[-1] for k in TOPICS], 4)
    for (k, (name, col)), y in zip(TOPICS.items(), ys):
        axes[0].plot(t.index, t[k], color=col, label=name)
        axes[0].annotate(name, (t.index[-1], y), xytext=(4, 0), textcoords="offset points", va="center",
                         fontsize=7, color=ps.INK_2)
    axes[0].set_xlim(2000, 2033)
    axes[0].set_xticks(range(2000, 2026, 5))
    axes[0].set_title("(a) TBT notifications on road vehicles\nper year, by topic")
    axes[1].barh(top.index, top.values, color=ps.SLOTS[2], height=0.6)
    for i, v in enumerate(top.values):
        axes[1].annotate(str(v), (v, i), xytext=(3, 0), textcoords="offset points", va="center", fontsize=7,
                         color=ps.INK_2)
    axes[1].grid(axis="y", visible=False)
    axes[1].grid(axis="x", visible=True)
    axes[1].tick_params(axis="y", labelsize=8)
    axes[1].set_title("(b) Notifications on EVs, batteries\nand charging, 2015-2026")
    fig.text(0.0, -0.05, "Regular notifications (no addenda) under the WTO TBT Agreement on HS 8701-8708, 8716, 8507, "
             "chargers and cables, or ICS 43 (road vehicles); topics by keywords, not exclusive.\nSource: WTO ePing.",
             fontsize=7, color=ps.MUTED)
    fig.tight_layout()
    ps.save(fig, "fig21_tbt_vehicles")
    print(t.tail(6).to_string())


if __name__ == "__main__":
    main()
