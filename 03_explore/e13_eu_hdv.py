"""EU heavy-duty registrations by country, duty cycle and manufacturer (EEA CO2 monitoring).

fig23_eu_hdv  (a) battery-electric share of new trucks >7.5 t by quarter and country group;
              (b) zero-emission share of certified trucks by VECTO duty cycle, Jul 2024-Jun 2025;
              (c) battery-electric share of new trucks >7.5 t by OEM group, Jul 2024-Jun 2025
tab_eu_hdv_duty_cycle.tex  zero-emission share, count and mean battery capacity by duty cycle
"""
import sys
from pathlib import Path

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import plot_style as ps  # noqa: E402
from config import PROC_DIR, TAB_DIR  # noqa: E402

GROUPS = {"Nordics (DK, FI, NO, SE)": (["DNK", "FIN", "NOR", "SWE"], ps.SLOTS[2]),
          "Netherlands": (["NLD"], ps.SLOTS[3]), "Germany": (["DEU"], ps.SLOTS[0]),
          "France": (["FRA"], ps.SLOTS[1]), "Rest of EU": ([], ps.OTHER)}
HEAVY = ["7.5-16t", "16-26t", ">26t"]
CYCLES = ["Tractor, regional delivery", "Rigid, urban delivery", "Rigid, regional delivery", "Rigid, long haul",
          "Medium rigid (<16 t)", "Construction (6x4, 8x4)", "Tractor, long haul"]


def main() -> None:
    ps.use()
    r = pd.read_csv(PROC_DIR / "eu_hdv_registrations.csv")
    t = r[(r.segment == "Truck") & r.mass_class.isin(HEAVY)].copy()
    t["bev"] = t.vehicles.where(t.powertrain == "Battery electric", 0)
    t["quarter"] = pd.PeriodIndex(t.month, freq="Q")
    t["grp"] = "Rest of EU"
    for g, (isos, _) in GROUPS.items():
        t.loc[t.iso3.isin(isos), "grp"] = g
    q = t.groupby(["quarter", "grp"])[["bev", "vehicles"]].sum()
    q = (100 * q.bev / q.vehicles).unstack()
    v = pd.read_csv(PROC_DIR / "eu_hdv_vecto_subgroups.csv")
    v = v[v.period == 2024]
    z = v.groupby(["duty_cycle", "powertrain"]).vehicles.sum().unstack().fillna(0)
    z["n"] = z.sum(axis=1)
    z["zev"] = 100 * z["Zero emission"] / z.n
    b = v[v.powertrain == "Zero emission"].groupby("duty_cycle")[["battery_kwh_sum", "battery_n"]].sum()
    z["kwh"] = b.battery_kwh_sum / b.battery_n
    z = z.loc[CYCLES]
    o = t[t.period == 2024].groupby("oem_group")[["bev", "vehicles"]].sum()
    o = o[o.vehicles > 1000].assign(share=lambda x: 100 * x.bev / x.vehicles).sort_values("share")

    fig, axes = plt.subplots(1, 3, figsize=(11.5, 3.9), gridspec_kw={"width_ratios": [1.3, 1.1, 0.9]})
    x = q.index.to_timestamp()
    ys = ps.spread([q[g].iloc[-1] for g in GROUPS], 0.45)
    for (g, (_, col)), y in zip(GROUPS.items(), ys):
        axes[0].plot(x, q[g], color=col, marker="o", markersize=3, label=g)
        axes[0].annotate(g, (x[-1], y), xytext=(4, 0), textcoords="offset points", va="center", fontsize=7,
                         color=ps.INK_2)
    axes[0].set_xlim(x[0], x[-1] + pd.Timedelta(days=330))
    axes[0].xaxis.set_major_locator(mdates.YearLocator())
    axes[0].xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    axes[0].set_title("(a) Battery-electric share of new trucks\n>7.5 t by quarter (%)")
    axes[1].barh(range(len(z)), z.zev, color=ps.SLOTS[0], height=0.6)
    for i, (share, n, kwh) in enumerate(zip(z.zev, z.n, z.kwh)):
        axes[1].annotate(f"{share:.1f}%  (n={n:,.0f}; {kwh:.0f} kWh)", (share, i), xytext=(3, 0),
                         textcoords="offset points", va="center", fontsize=6.5, color=ps.INK_2)
    axes[1].set_yticks(range(len(z)))
    axes[1].set_yticklabels(z.index, fontsize=7.5)
    axes[1].set_xlim(0, 40)
    axes[1].grid(axis="x", color=ps.GRID, linewidth=0.6)
    axes[1].grid(axis="y", visible=False)
    axes[1].set_title("(b) Zero-emission share of certified\ntrucks by duty cycle, 2024-25 (%)")
    axes[2].barh(o.index, o.share, color=ps.SLOTS[0], height=0.6)
    for i, (share, n) in enumerate(zip(o.share, o.vehicles)):
        axes[2].annotate(f"{share:.1f}%", (share, i), xytext=(3, 0), textcoords="offset points", va="center",
                         fontsize=7, color=ps.INK_2)
    axes[2].set_xlim(0, o.share.max() * 1.3)
    axes[2].grid(axis="x", color=ps.GRID, linewidth=0.6)
    axes[2].grid(axis="y", visible=False)
    axes[2].set_title("(c) Battery-electric share of new\ntrucks >7.5 t by OEM group, 2024-25 (%)")
    fig.text(0.0, -0.07, "New registrations in the EU27, Iceland and Norway, July 2021-June 2025 (reporting periods run "
             "July-June). (b) VECTO sub-groups assigned under Regulation (EU) 2019/1242 from axle configuration, cab "
             "and power;\nn = certified trucks; kWh = mean battery capacity of zero-emission trucks. Italy's 2024-25 "
             "records carry no electric flag. Source: EEA, CO2 emissions from heavy-duty vehicles; own aggregation.",
             fontsize=7, color=ps.MUTED)
    fig.tight_layout()
    ps.save(fig, "fig23_eu_hdv")
    tab = z[["zev", "n", "kwh"]].rename(columns={"zev": "Zero-emission share (%)", "n": "Certified trucks",
                                                 "kwh": "Mean battery (kWh)"})
    tab.index.name = "Duty cycle (VECTO)"
    tab.columns.name = None
    tab["Certified trucks"] = tab["Certified trucks"].astype(int)
    tab.to_latex(TAB_DIR / "tab_eu_hdv_duty_cycle.tex", float_format="%.1f", position="htbp", label="tab:euduty",
                 escape=True,
                 caption="Zero-emission share of new certified trucks by VECTO duty cycle in the EU, July 2024-June "
                 "2025. Source: EEA heavy-duty CO2 monitoring data.")
    print(q.round(2).to_string())
    print(z.round(1).to_string())
    print(o.round(2).to_string())


if __name__ == "__main__":
    main()
