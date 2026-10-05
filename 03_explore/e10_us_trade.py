"""US truck trade around the Section 232 tariff (US Census HS10, monthly).

fig18_us_truck_imports_232   (a) US imports of medium and heavy trucks by origin, units per
                             month; (b) effective tariff (duties / customs value) by origin
fig19_batteries_used_trucks  (a) US lithium-ion battery imports by origin, half-years;
                             (b) US exports of used road tractors, January-July of each year
tab_us_trade_232.tex         before/after Section 232 by segment and origin: units, border
                             unit value, dutiable share, effective tariff
"""
import sys
from pathlib import Path

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import plot_style as ps  # noqa: E402
from config import PROC_DIR, TAB_DIR  # noqa: E402

ORIGINS = {"MEXICO": ("Mexico", ps.SLOTS[1]), "CANADA": ("Canada", ps.SLOTS[0]), "JAPAN": ("Japan", ps.SLOTS[2])}
MHD = ["Road tractor, new", "Cab chassis 5-20 t", "Truck >20 t"]  # complete trucks 5-20 t: see fig20 (reclassified pickups)
PRE = ("2025-03", "2025-10")   # after the IEEPA tariffs began, before Section 232 (1 Nov 2025)
POST = ("2025-12", "2026-07")  # skips the transition month


def load() -> pd.DataFrame:
    d = pd.read_csv(PROC_DIR / "us_trade_segment_partner_month.csv")
    d["date"] = pd.to_datetime(d.month)
    return d


def fig18(d: pd.DataFrame) -> None:
    m = d[(d.flow == "imports") & d.segment.isin(MHD) & d.partner.isin(ORIGINS) & (d.month >= "2023-01")]
    u = m.groupby(["date", "partner"]).units.sum().unstack()
    r = m[m.month >= "2025-01"].groupby(["date", "partner"])[["duty", "value"]].sum()
    r = (r.duty / r.value).unstack()
    fig, axes = plt.subplots(1, 2, figsize=(9.2, 3.6))
    for iso, (name, col) in ORIGINS.items():
        axes[0].plot(u.index, u[iso] / 1e3, color=col, label=name)
        ps.label_end(axes[0], u.index[-1], u[iso].iloc[-1] / 1e3, name)
        axes[1].plot(r.index, 100 * r[iso], color=col, marker="o", markersize=3, label=name)
        ps.label_end(axes[1], r.index[-1], 100 * r[iso].iloc[-1], f"{name} {100 * r[iso].iloc[-1]:.0f}%")
    axes[0].set_title("(a) US imports of medium and heavy trucks\n(thousand vehicles per month)")
    axes[1].set_title("(b) Effective tariff: duties / customs value (%)")
    for ax in axes:
        ax.axvline(pd.Timestamp("2025-11-01"), color=ps.MUTED, linewidth=0.8)
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    axes[0].annotate("Sec. 232\ntruck tariff", (pd.Timestamp("2025-11-01"), axes[0].get_ylim()[1]), xytext=(-3, -3),
                     textcoords="offset points", ha="right", va="top", fontsize=7, color=ps.MUTED)
    axes[0].set_xlim(pd.Timestamp("2023-01-01"), pd.Timestamp("2027-04-01"))
    axes[1].set_xlim(pd.Timestamp("2025-01-01"), pd.Timestamp("2026-12-15"))
    axes[1].xaxis.set_major_locator(mdates.MonthLocator(bymonth=[1, 7]))
    axes[1].xaxis.set_major_formatter(mdates.DateFormatter("%b %Y"))
    axes[0].xaxis.set_major_locator(mdates.YearLocator())
    fig.text(0.0, -0.05, "Medium and heavy = new road tractors, cab chassis 5-20 t GVW, trucks >20 t "
             "(HS 8701.21-.29 new, 8704.22.11, 8704.23). Imports for consumption.\nSource: US Census Bureau international "
             "trade API, HS10.", fontsize=7, color=ps.MUTED)
    fig.tight_layout()
    ps.save(fig, "fig18_us_truck_imports_232")


def fig19(d: pd.DataFrame) -> None:
    b = d[(d.flow == "imports") & (d.segment == "Lithium-ion batteries") & (d.month < "2026-07")].copy()
    b["half"] = b.date.dt.year.astype(str) + "H" + ((b.date.dt.month > 6) + 1).astype(str)
    grp = {"CHINA": "China", "KOREA, SOUTH": "Korea and Japan", "JAPAN": "Korea and Japan",
           "VIETNAM": "Southeast Asia", "MALAYSIA": "Southeast Asia", "THAILAND": "Southeast Asia",
           "INDONESIA": "Southeast Asia", "PHILIPPINES": "Southeast Asia", "CAMBODIA": "Southeast Asia"}
    b["origin"] = b.partner.map(grp).fillna("Rest of world")
    bt = b.groupby(["half", "origin"]).value.sum().unstack() / 1e9
    e = d[(d.flow == "exports") & (d.segment == "Road tractor, used") & (d.date.dt.month <= 7)]
    dest = {"MEXICO": "Mexico", "GUATEMALA": "Central America", "HONDURAS": "Central America",
            "EL SALVADOR": "Central America", "COSTA RICA": "Central America", "NICARAGUA": "Central America",
            "PANAMA": "Central America", "BELIZE": "Central America", "CANADA": "Canada"}
    e = e.assign(dest=e.partner.map(dest).fillna("Other"))
    et = e.groupby([e.date.dt.year, "dest"]).units.sum().unstack() / 1e3
    fig, axes = plt.subplots(1, 2, figsize=(9.2, 3.6))
    cols = {"China": ps.SLOTS[0], "Korea and Japan": ps.SLOTS[1], "Southeast Asia": ps.SLOTS[2],
            "Rest of world": ps.OTHER}
    x = range(len(bt))
    for name, col in cols.items():
        axes[0].plot(list(x), bt[name], color=col, marker="o", markersize=3, label=name)
        ps.label_end(axes[0], len(bt) - 1, bt[name].iloc[-1], name)
    axes[0].set_xticks(list(x)[::2])
    axes[0].set_xticklabels(bt.index[::2], fontsize=7)
    axes[0].set_xlim(-0.5, len(bt) + 2.8)
    axes[0].set_title("(a) US lithium-ion battery imports by origin\n(USD billion per half-year)")
    dcols = {"Mexico": ps.SLOTS[1], "Central America": ps.SLOTS[3], "Canada": ps.SLOTS[0], "Other": ps.OTHER}
    bottom = pd.Series(0.0, index=et.index)
    for name, col in dcols.items():
        if name in et:
            axes[1].bar(et.index, et[name].fillna(0), bottom=bottom, color=col, label=name, width=0.7,
                        edgecolor="white", linewidth=1.5)
            bottom += et[name].fillna(0)
    for yr, tot in bottom.items():
        axes[1].annotate(f"{tot:.1f}k", (yr, tot), xytext=(0, 3), textcoords="offset points", ha="center",
                         fontsize=7, color=ps.INK_2)
    axes[1].set_title("(b) US exports of used road tractors,\nJanuary-July (thousand vehicles)")
    axes[1].legend(loc="upper left", fontsize=7)
    fig.text(0.0, -0.05, "Batteries: HS 8507.60, imports for consumption, 2019H1-2026H1. Used tractors: HS 8701.21-.29 "
             "statistical suffix 80 (used).\nSource: US Census Bureau international trade API.", fontsize=7,
             color=ps.MUTED)
    fig.tight_layout()
    ps.save(fig, "fig19_batteries_used_trucks")


def fig20() -> None:
    from config import RAW_DIR
    r = pd.read_csv(RAW_DIR / "census_trade" / "census_imports_hs10_monthly.csv.gz", low_memory=False,
                    dtype={"I_COMMODITY": str})
    r = r[(r.CTY_NAME == "MEXICO") & r.I_COMMODITY.isin(["8704210100", "8704225120"]) & (r.time >= "2024-01")]
    r["units"] = pd.to_numeric(r.GEN_QY1_MO, errors="coerce")
    t = r.pivot_table(index=pd.to_datetime(r.time), columns="I_COMMODITY", values="units", aggfunc="sum") / 1e3
    fig, ax = plt.subplots(figsize=(7.2, 3.2))
    for code, name, col in (("8704210100", "Diesel trucks <=5 t GVW", ps.SLOTS[0]),
                            ("8704225120", "Diesel trucks 5-9 t GVW (complete)", ps.SLOTS[1])):
        ax.plot(t.index, t[code], color=col, label=name)
        ps.label_end(ax, t.index[-1], t[code].iloc[-1], name.split(" (")[0])
    for dte, txt in (("2025-04-01", "Sec. 232 autos and\nlight trucks"), ("2025-11-01", "Sec. 232\nMHD trucks")):
        ax.axvline(pd.Timestamp(dte), color=ps.MUTED, linewidth=0.8)
        ax.annotate(txt, (pd.Timestamp(dte), ax.get_ylim()[1]), xytext=(3, -3), textcoords="offset points",
                    va="top", fontsize=7, color=ps.MUTED)
    ax.set_xlim(t.index[0], pd.Timestamp("2027-03-01"))
    ax.set_title("US imports of diesel trucks from Mexico by declared weight class (thousand per month)")
    fig.text(0.0, -0.06, "HS 8704.21.01.00 vs 8704.22.51.20. Effective tariff on the 5-9 t line: ~0.5% Apr-Oct 2025, "
             "9-15% from Nov 2025; on the <=5 t line ~6%. Source: US Census.", fontsize=7, color=ps.MUTED)
    fig.tight_layout()
    ps.save(fig, "fig20_mexico_truck_reclassification")


def table(d: pd.DataFrame) -> pd.DataFrame:
    segs = MHD + ["Complete truck 5-20 t", "Electric truck", "Bus, other", "Electric bus"]
    m = d[(d.flow == "imports") & d.segment.isin(segs) & d.partner.isin(ORIGINS)]
    rows = []
    for (seg, iso), g in m.groupby(["segment", "partner"]):
        out = {"Segment": seg, "Origin": ORIGINS[iso][0]}
        for tag, (a, b) in (("pre", PRE), ("post", POST)):
            w = g[(g.month >= a) & (g.month <= b)]
            n = w.month.nunique() or 1
            out[f"units_{tag}"] = w.units.sum() / n
            out[f"uv_{tag}"] = w.value.sum() / w.units.sum() / 1e3 if w.units.sum() > 0 else float("nan")
            out[f"rate_{tag}"] = 100 * w.duty.sum() / w.value.sum() if w.value.sum() > 0 else float("nan")
        out["dutiable_post"] = 100 * g[(g.month >= POST[0]) & (g.month <= POST[1])].pipe(
            lambda w: w.dutiable.sum() / w.value.sum() if w.value.sum() > 0 else float("nan"))
        rows.append(out)
    t = pd.DataFrame(rows)
    t = t[t.units_pre + t.units_post >= 20]
    t["Change in units (%)"] = 100 * (t.units_post / t.units_pre - 1)
    tab = t.set_index(["Segment", "Origin"])[["units_pre", "units_post", "Change in units (%)", "uv_pre", "uv_post",
                                              "rate_pre", "rate_post", "dutiable_post"]]
    tab.columns = ["Units/mo pre", "Units/mo post", "Change (%)", "Unit value pre (k$)", "Unit value post (k$)",
                   "Tariff pre (%)", "Tariff post (%)", "Dutiable post (%)"]
    tab.to_latex(TAB_DIR / "tab_us_trade_232.tex", escape=True, position="htbp", float_format="%.0f",
                 label="tab:ustrade", caption="US imports of trucks and buses before (Mar-Oct 2025) and after "
                 "(Dec 2025-Jul 2026) the Section 232 tariff: monthly units, border unit value (customs value per "
                 "vehicle), effective tariff (duties / customs value) and dutiable share of value. Source: US Census, HS10.")
    return tab


def main() -> None:
    ps.use()
    d = load()
    fig18(d)
    fig19(d)
    fig20()
    print(table(d).round(1).to_string())


if __name__ == "__main__":
    main()
