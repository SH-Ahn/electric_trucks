"""Market structure of electric vs diesel trucks and buses from model-level registries.

Incumbents are defined from the data: makes with >=1% of the segment's diesel registrations
in the pre-period (NL 2016-2018, UK 2015-2018). Everything else is an entrant.

fig08_entrant_shares        entrant share of new registrations, battery-electric vs diesel,
                            2023-2026, by market (NL trucks, NL buses, UK HGVs, UK buses)
fig09_nl_segment_bev_share  BEV share of new registrations by segment, Netherlands, quarterly
fig10_rank_reversal         market share of the large incumbents in diesel vs battery-electric
                            trucks (NL, UK), 2023-2026
tab_market_structure.tex    HHI, top makes and entrant shares by market and powertrain
"""
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import plot_style as ps  # noqa: E402
from config import PROC_DIR, TAB_DIR  # noqa: E402

MAKE_ALIASES = {"MERCEDES": "MERCEDES-BENZ", "RENAULT TRUCKS": "RENAULT", "IVECO BUS": "IVECO",
                "DAF TRUCKS": "DAF", "MAN TRUCKS": "MAN",
                "VDL BERKHOF": "VDL", "ALEXANDER DENNIS LIMITED": "ALEXANDER DENNIS"}


def incumbents(d: pd.DataFrame, pre: tuple[int, int]) -> set[str]:
    p = d[(d.powertrain == "Diesel") & d.year.between(*pre)]
    s = p.groupby("make")["n"].sum()
    return set(s[s / s.sum() >= 0.01].index)


def summarise(d: pd.DataFrame, market: str, pre: tuple[int, int], post=(2023, 2026)) -> dict:
    inc = incumbents(d, pre)
    out = {"market": market}
    for pt in ("Battery electric", "Diesel"):
        x = d[(d.powertrain == pt) & d.year.between(*post)].groupby("make")["n"].sum()
        sh = x / x.sum()
        out[f"{pt}_n"] = int(x.sum())
        out[f"{pt}_entrant_share"] = float(sh[~sh.index.isin(inc)].sum())
        out[f"{pt}_hhi"] = float((100 * sh) .pow(2).sum())
        out[f"{pt}_top3"] = ", ".join(f"{m.title()} {100 * v:.0f}%" for m, v in sh.nlargest(3).items())
    return out


def load_nl() -> dict[str, pd.DataFrame]:
    nl = pd.read_csv(PROC_DIR / "nl_registrations_model_quarter.csv")
    nl = nl[nl.new_vehicle == 1].copy()
    nl["year"] = nl.quarter.str[:4].astype(int)
    nl["make"] = nl.make.replace(MAKE_ALIASES)
    nl = nl.rename(columns={"registrations": "n"})
    trucks = nl[nl.segment.str.contains("truck|Tractor")]
    buses = nl[nl.segment.str.startswith("Bus")]
    return {"Netherlands - trucks": trucks, "Netherlands - buses": buses, "_all": nl}


def load_uk() -> dict[str, pd.DataFrame]:
    uk = pd.read_csv(PROC_DIR / "uk_registrations_model_quarter.csv")
    uk["year"] = uk.quarter.str[:4].astype(int)
    uk["make"] = uk.Make.str.upper().replace(MAKE_ALIASES)
    uk["powertrain"] = uk.Fuel.replace({"Battery electric": "Battery electric", "Diesel": "Diesel"})
    uk = uk.rename(columns={"registrations": "n"})
    return {"UK - heavy goods vehicles": uk[uk.BodyType == "Heavy goods vehicles"],
            "UK - buses and coaches": uk[uk.BodyType == "Buses and coaches"]}


def rank_reversal(markets: dict[str, pd.DataFrame], post=(2023, 2026)) -> None:
    makes = ["DAF", "SCANIA", "VOLVO", "MERCEDES-BENZ", "MAN", "IVECO", "RENAULT"]
    hl = {"DAF": ps.SLOTS[0], "MERCEDES-BENZ": ps.SLOTS[1]}
    fig, axes = plt.subplots(1, 2, figsize=(8.0, 3.6), sharey=True)
    rows = []
    for ax, (name, d) in zip(axes, markets.items()):
        d = d[d.year.between(*post)]
        sh = {}
        for pt in ("Diesel", "Battery electric"):
            x = d[d.powertrain == pt].groupby("make")["n"].sum()
            sh[pt] = 100 * x / x.sum()
        left = [sh["Diesel"].get(m, 0.0) for m in makes]
        right = [sh["Battery electric"].get(m, 0.0) for m in makes]
        ly, ry = ps.spread(left, 1.4), ps.spread(right, 1.4)
        for m, a, b, la, rb in zip(makes, left, right, ly, ry):
            rows.append((name, m, a, b))
            col = hl.get(m, ps.OTHER)
            lw = 2.0 if m in hl else 1.0
            ax.plot([0, 1], [a, b], color=col, linewidth=lw, marker="o", markersize=4, zorder=3 if m in hl else 2)
            ink = ps.INK if m in hl else ps.MUTED
            ax.annotate(f"{m.title()} {a:.0f}%", (0, la), xytext=(-6, 0), textcoords="offset points",
                        ha="right", va="center", fontsize=7, color=ink)
            ax.annotate(f"{b:.0f}% {m.title()}", (1, rb), xytext=(6, 0), textcoords="offset points",
                        ha="left", va="center", fontsize=7, color=ink)
        ax.set_xticks([0, 1], ["Diesel", "Battery-electric"])
        ax.set_xlim(-0.55, 1.55)
        ax.set_title(name)
        ax.grid(False)
        ax.spines["left"].set_visible(False)
        ax.tick_params(axis="y", labelleft=False)
    fig.suptitle("Market shares of large incumbents, new registrations 2023-2026 (%)", x=0.01, ha="left",
                 fontsize=10, fontweight="bold")
    fig.text(0.0, -0.04, "Shares within each powertrain. DAF and Mercedes-Benz highlighted. Sources: RDW open "
             "data; DfT VEH0160.", fontsize=7, color=ps.MUTED)
    fig.tight_layout()
    ps.save(fig, "fig10_rank_reversal")
    pd.DataFrame(rows, columns=["market", "make", "diesel_share", "bev_share"]).to_csv(
        TAB_DIR / "rank_reversal_shares.csv", index=False)


def main() -> None:
    ps.use()
    nl, uk = load_nl(), load_uk()
    rows = [summarise(nl["Netherlands - trucks"], "Netherlands - trucks", (2016, 2018)),
            summarise(nl["Netherlands - buses"], "Netherlands - buses", (2016, 2018)),
            summarise(uk["UK - heavy goods vehicles"], "UK - heavy goods vehicles", (2015, 2018)),
            summarise(uk["UK - buses and coaches"], "UK - buses and coaches", (2015, 2018))]
    s = pd.DataFrame(rows).set_index("market")
    print(s.round(3).to_string())

    fig, ax = plt.subplots(figsize=(6.6, 3.4))
    x = np.arange(len(s))
    w = 0.36
    ax.bar(x - w / 2, 100 * s["Battery electric_entrant_share"], w, color=ps.SLOTS[0],
           label="Battery-electric", edgecolor="white", linewidth=1)
    ax.bar(x + w / 2, 100 * s["Diesel_entrant_share"], w, color=ps.OTHER, label="Diesel",
           edgecolor="white", linewidth=1)
    for i, (be, di) in enumerate(zip(s["Battery electric_entrant_share"], s["Diesel_entrant_share"])):
        ax.annotate(f"{100 * be:.0f}%", (i - w / 2, 100 * be), xytext=(0, 3), textcoords="offset points",
                    ha="center", fontsize=7, color=ps.INK_2)
        ax.annotate(f"{100 * di:.0f}%", (i + w / 2, 100 * di), xytext=(0, 3), textcoords="offset points",
                    ha="center", fontsize=7, color=ps.INK_2)
    ax.set_xticks(x, [m.replace(" - ", "\n") for m in s.index])
    ax.set_ylabel("Entrant share of new registrations (%)")
    ax.set_ylim(0, 52)
    ax.set_title("Entrants sell far more of the electric than the diesel market (2023-2026)")
    ax.legend(loc="upper right")
    fig.text(0.0, -0.08, "Entrant = make with <1% of the segment's diesel registrations in 2016-18 (NL) or "
             "2015-18 (UK). Sources: RDW open data; DfT VEH0160.", fontsize=7, color=ps.MUTED)
    fig.tight_layout()
    ps.save(fig, "fig08_entrant_shares")

    a = nl["_all"].copy()
    a["seg"] = a.segment.replace({"Tractor N2": "Rigid truck N2"})
    q = a.pivot_table(index="quarter", columns=["seg", "powertrain"], values="n", aggfunc="sum").fillna(0)
    q = q.loc[:str(pd.Timestamp.today().to_period("Q") - 1)]  # drop the incomplete current quarter
    fig, ax = plt.subplots(figsize=(7.2, 3.4))
    order = [("Rigid truck N2", "Rigid trucks and heavy vans 3.5-12 t (N2)", ps.SLOTS[0]),
             ("Rigid truck N3", "Rigid trucks >12 t (N3)", ps.SLOTS[1]),
             ("Tractor N3", "Tractor units (N3)", ps.SLOTS[2]),
             ("Bus/coach M3", "Buses and coaches (M3)", ps.SLOTS[3])]
    for seg, lab, col in order:
        tot = q[seg].sum(axis=1)
        bev = q[seg].get("Battery electric", 0)
        sh = (100 * bev / tot).loc["2019Q1":]
        sh = sh.rolling(2, min_periods=1).mean()
        xs = pd.PeriodIndex(sh.index, freq="Q").to_timestamp()
        ax.plot(xs, sh.values, color=col, label=lab)
        ps.label_end(ax, xs[-1], sh.values[-1], f"{sh.values[-1]:.0f}%")
    ax.axvline(pd.Timestamp("2025-01-01"), color=ps.MUTED, linewidth=0.8)
    ax.annotate("Zero-emission\nzones start", (pd.Timestamp("2025-01-01"), 95), xytext=(-3, 0),
                textcoords="offset points", ha="right", va="top", fontsize=7, color=ps.MUTED)
    ax.set_ylim(0, 100)
    ax.set_title("Netherlands: battery-electric share of new registrations by segment (%)")
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.1), ncol=2)
    fig.text(0.0, -0.13, "Two-quarter moving average; new vehicles only (first Dutch registration within 90 "
             "days of first admission). Source: RDW open data.", fontsize=7, color=ps.MUTED)
    fig.tight_layout()
    ps.save(fig, "fig09_nl_segment_bev_share")

    rank_reversal({"Netherlands - trucks": nl["Netherlands - trucks"], "UK - HGVs": uk["UK - heavy goods vehicles"]})

    s[["Battery electric_top3", "Diesel_top3"]].to_csv(TAB_DIR / "market_structure_top3.csv")
    tab = s[["Battery electric_n", "Battery electric_entrant_share", "Battery electric_hhi",
             "Diesel_n", "Diesel_entrant_share", "Diesel_hhi"]].copy()
    for c in ("Battery electric_entrant_share", "Diesel_entrant_share"):
        tab[c] = 100 * tab[c]
    tab.columns = ["BEV units", "BEV entrant share (%)", "BEV HHI", "Diesel units", "Diesel entrant share (%)",
                   "Diesel HHI"]
    tab.index.name = "Market"
    tab.to_latex(TAB_DIR / "tab_market_structure.tex", escape=True, position="htbp", float_format="%.0f", label="tab:mktstructure",
                 caption="Market structure of electric and diesel new registrations, 2023-2026")


if __name__ == "__main__":
    main()
