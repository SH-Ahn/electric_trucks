"""How trucks are used: duty cycles and freight demand behind truck electrification.

fig14_freight_profile_vs_zev  2025 ZEV share of new heavy trucks vs the 2019-23 short-haul
                              share of truck-km and the average haul (European countries)
fig15_cfs_short_haul          US shipper industries: share of truck tonnage moved under
                              100 miles (CFS 2017, routed distance)
fig16_freight_activity        Germany truck-toll mileage index, monthly 2008-2026
tab_freight_profile_zev.tex   table twin of fig14, with income and fit statistics
tab_cfs_short_haul.tex        table twin of fig15, with truck mode share and private fleets
"""
import sys
from pathlib import Path

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import statsmodels.formula.api as smf

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import plot_style as ps  # noqa: E402
from config import PROC_DIR, TAB_DIR  # noqa: E402

MIN_REG = 500  # countries with at least this many new heavy trucks in 2025


def europe() -> pd.DataFrame:
    p = pd.read_csv(PROC_DIR / "eu_freight_profile_country_year.csv")
    p = p[p.iso3 != "EU27"]
    pre = p[p.year.between(2019, 2023)].groupby("iso3")[
        ["vkm_share_short_lt150", "avg_haul_km", "intl_share_tkm", "own_account_share_tkm", "vkm_mean_age"]].mean()
    z = p[p.year == 2025].set_index("iso3")[["zev_share_heavy", "reg_lorries", "reg_tractors"]]
    cov = pd.read_csv(PROC_DIR / "country_year_covariates.csv")
    inc = cov[cov.year == 2023].set_index("iso3")["gdppc_ppp_const"]
    d = pre.join(z, how="inner").join(inc, how="left")
    d["reg_heavy"] = d[["reg_lorries", "reg_tractors"]].sum(axis=1, min_count=1)
    return d[(d.reg_heavy >= MIN_REG)].dropna(subset=["zev_share_heavy", "vkm_share_short_lt150"])


def fig14(d: pd.DataFrame) -> dict:
    fits = {}
    d = d.assign(lgdp=np.log(d.gdppc_ppp_const), lhaul=np.log(d.avg_haul_km))
    for name, f in (("short", "zev_share_heavy ~ vkm_share_short_lt150"),
                    ("short_inc", "zev_share_heavy ~ vkm_share_short_lt150 + lgdp"),
                    ("haul_inc", "zev_share_heavy ~ lhaul + lgdp"), ("inc", "zev_share_heavy ~ lgdp")):
        fits[name] = smf.ols(f, data=d.dropna(subset=["gdppc_ppp_const"])).fit(cov_type="HC1")
    fig, axes = plt.subplots(1, 2, figsize=(9.2, 3.8), sharey=True)
    size = 12 + 110 * d.reg_heavy / d.reg_heavy.max()
    panels = (("vkm_share_short_lt150", 100, "Short-haul share of truck-km, 2019-23 average (%)\n(laden journeys under 150 km)",
               "(a) Short-haul freight"),
              ("avg_haul_km", 1, "Average haul, 2019-23 (km per tonne, log scale)", "(b) Haul length"))
    # Selective labels (offsets in points); every country is listed in tab_freight_profile_zev.
    nudges = ({"CHE": (-24, -3), "NLD": (6, 3), "NOR": (-24, 3), "DNK": (5, 3), "SWE": (5, -6), "GRC": (5, -2),
               "DEU": (9, -1), "AUT": (5, 2), "IRL": (5, -2), "FIN": (4, 4), "CZE": (4, -7), "FRA": (-20, 5),
               "ITA": (7, -3), "POL": (-6, 7), "ROU": (-8, 6), "LTU": (-8, 6)},
              {"CHE": (5, -2), "NLD": (5, 3), "NOR": (-24, 2), "DNK": (5, 2), "SWE": (5, -6), "GRC": (5, -2),
               "DEU": (9, -1), "AUT": (5, 2), "IRL": (-18, 3), "FRA": (-22, -4), "ITA": (-8, 6), "BEL": (-4, 7),
               "ESP": (6, 5), "POL": (6, 3), "LTU": (-16, 6)})
    for ax, (col, mult, xlab, title), nudge in zip(axes, panels, nudges):
        x = mult * d[col]
        ax.scatter(x, 100 * d.zev_share_heavy, s=size, color=ps.SLOTS[0], edgecolor="white", linewidth=1, zorder=3)
        for iso, off in nudge.items():
            if iso in d.index:
                ax.annotate(iso, (mult * d.at[iso, col], 100 * d.at[iso, "zev_share_heavy"]), xytext=off,
                            textcoords="offset points", fontsize=6.5, color=ps.INK_2)
        xs = np.linspace(x.min(), x.max(), 30)
        if col == "avg_haul_km":
            ax.set_xscale("log")
            ax.set_xticks([50, 100, 200, 400])
            ax.set_xticklabels(["50", "100", "200", "400"])
            b = np.polyfit(np.log(x), 100 * d.zev_share_heavy, 1)
            ax.plot(xs, np.polyval(b, np.log(xs)), color=ps.MUTED, linewidth=1)
        else:
            b = np.polyfit(x, 100 * d.zev_share_heavy, 1)
            ax.plot(xs, np.polyval(b, xs), color=ps.MUTED, linewidth=1)
        rho = d[[col, "zev_share_heavy"]].corr(method="spearman").iloc[0, 1]
        ax.set_xlabel(xlab)
        ax.set_title(f"{title}: rank correlation {rho:+.2f}")
        ax.grid(axis="x", visible=True)
    axes[0].set_ylabel("ZEV share of new heavy trucks, 2025 (%)")
    axes[0].set_ylim(-1.5, 24)
    fig.text(0.0, -0.07, f"Heavy trucks = road tractors + rigid lorries >3.5 t; {len(d)} countries with >= {MIN_REG} "
             "new heavy trucks in 2025; point area proportional to new registrations; unlabelled points are listed in "
             "the table twin.\nFreight by reporting (registration) country. Sources: Eurostat road_go_ta_dc, road_eqr_tracmot, road_eqr_lormot.",
             fontsize=7, color=ps.MUTED)
    fig.tight_layout()
    ps.save(fig, "fig14_freight_profile_vs_zev")
    return fits


def tab_europe(d: pd.DataFrame, fits: dict) -> None:
    t = d.sort_values("zev_share_heavy", ascending=False)
    tab = pd.DataFrame({
        "New heavy trucks 2025": t.reg_heavy,
        "ZEV share 2025 (%)": 100 * t.zev_share_heavy,
        "Short-haul truck-km (%)": 100 * t.vkm_share_short_lt150,
        "Avg haul (km)": t.avg_haul_km,
        "International tkm (%)": 100 * t.intl_share_tkm,
        "Own-account tkm (%)": 100 * t.own_account_share_tkm,
        "Fleet age (yrs)": t.vkm_mean_age,
    })
    tab.index.name = "Country"
    f1, f2, f3, f4 = fits["short"], fits["short_inc"], fits["haul_inc"], fits["inc"]
    note = (f"OLS (HC1), n = {int(f2.nobs)}: ZEV share on short-haul share {f1.params.iloc[1]:.2f} "
            f"(se {f1.bse.iloc[1]:.2f}, R2 {f1.rsquared:.2f}); adding log GDP per capita: "
            f"{f2.params['vkm_share_short_lt150']:.2f} (se {f2.bse['vkm_share_short_lt150']:.2f}), "
            f"income {f2.params['lgdp']:.3f} (se {f2.bse['lgdp']:.3f}); log haul {f3.params['lhaul']:.3f} "
            f"(se {f3.bse['lhaul']:.3f}); income alone R2 {f4.rsquared:.2f}. Freight variables are 2019-23 averages.")
    tab.to_latex(TAB_DIR / "tab_freight_profile_zev.tex", escape=True, position="htbp", float_format="%.1f",
                 formatters={"New heavy trucks 2025": "{:,.0f}".format}, label="tab:freightzev",
                 caption="Freight profile and heavy-truck ZEV share, European countries. " + note)
    print(note)


def fig15() -> pd.DataFrame:
    u = pd.read_csv(PROC_DIR / "us_cfs_truck_profile.csv", dtype={"industry": str})
    d = u[(u.level == "naics3") & (u.year == 2017) & (u.truck_tons_m >= 10)].sort_values("truck_tons_share_lt100mi")
    fig, ax = plt.subplots(figsize=(6.6, 5.4))
    y = np.arange(len(d))
    ax.barh(y, 100 * d.truck_tons_share_lt100mi, height=0.62, color=ps.SLOTS[0], edgecolor="white", linewidth=2)
    for yi, (_, r) in zip(y, d.iterrows()):
        ax.annotate(f"{100 * r.truck_tons_share_lt100mi:.0f}%  ({r.truck_tons_m:,.0f}m t)",
                    (100 * r.truck_tons_share_lt100mi, yi), xytext=(3, 0), textcoords="offset points",
                    va="center", fontsize=7, color=ps.INK_2)
    ax.set_yticks(y)
    ax.set_yticklabels(d.label, fontsize=8)
    ax.set_xlim(0, 112)
    ax.set_xticks([0, 25, 50, 75, 100])
    ax.grid(axis="y", visible=False)
    ax.grid(axis="x", visible=True)
    ax.set_xlabel("Share of the industry's truck tonnage shipped under 100 miles (%)")
    ax.set_title("Short-haul truck freight by shipper industry, US 2017")
    fig.text(0.0, -0.04, "Shipments by for-hire and company-owned truck; routed distance; industries with >= 10m "
             "truck tons; label gives truck tonnage.\nSource: US Census Commodity Flow Survey 2017 public-use file "
             "(weighted).", fontsize=7, color=ps.MUTED)
    fig.tight_layout()
    ps.save(fig, "fig15_cfs_short_haul")
    return d


def tab_cfs(d: pd.DataFrame) -> None:
    t = d.sort_values("truck_tons_share_lt100mi", ascending=False).set_index("label")
    tab = pd.DataFrame({
        "Truck tons (m)": t.truck_tons_m,
        "Truck share of tons (%)": 100 * t.truck_share_tons,
        "Under 100 mi (%)": 100 * t.truck_tons_share_lt100mi,
        "Under 250 mi (%)": 100 * t.truck_tons_share_lt250mi,
        "Ton-miles under 250 mi (%)": 100 * t.truck_tonmiles_share_lt250mi,
        "Private fleet (%)": 100 * t.private_share_truck_tons,
    })
    tab.index.name = "Shipper industry (NAICS)"
    tab.to_latex(TAB_DIR / "tab_cfs_short_haul.tex", escape=True, position="htbp", float_format="%.0f",
                 formatters={"Truck tons (m)": "{:,.0f}".format}, label="tab:cfs",
                 caption="Truck freight by shipper industry and distance, US Commodity Flow Survey 2017 "
                         "(weighted; routed distance). Private fleet = company-owned trucks' share of truck tons.")


def fig16() -> None:
    t = pd.read_csv(PROC_DIR / "de_toll_mileage_monthly.csv")
    t["month"] = pd.to_datetime(t["month"])
    fig, ax = plt.subplots(figsize=(7.2, 3.0))
    ax.plot(t.month, t.index_ksb, color=ps.SLOTS[0])
    ps.label_end(ax, t.month.iloc[-1], t.index_ksb.iloc[-1], f"{t.index_ksb.iloc[-1]:.0f}")
    lo, hi = ax.get_ylim()
    for dte, txt, top in (("2008-10-01", "Financial\ncrisis", True), ("2020-04-01", "COVID-19", False),
                          ("2023-12-01", "CO2 toll\nsurcharge", False), ("2026-02-01", "Hormuz\nclosure", False)):
        ax.axvline(pd.Timestamp(dte), color=ps.MUTED, linewidth=0.8)
        ax.annotate(txt, (pd.Timestamp(dte), hi if top else lo), xytext=(3, -4 if top else 4),
                    textcoords="offset points", va="top" if top else "bottom", fontsize=7, color=ps.MUTED)
    ax.xaxis.set_major_locator(mdates.YearLocator(2))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    ax.set_title("Heavy-truck mileage on German toll roads (index 2021 = 100, calendar and seasonally adjusted)")
    fig.text(0.0, -0.06, "Monthly mean of the daily index; trucks with 4+ axles. Source: Destatis/BALM "
             "Lkw-Maut-Fahrleistungsindex (42191).", fontsize=7, color=ps.MUTED)
    fig.tight_layout()
    ps.save(fig, "fig16_freight_activity")


def main() -> None:
    ps.use()
    d = europe()
    fits = fig14(d)
    tab_europe(d, fits)
    tab_cfs(fig15())
    fig16()


if __name__ == "__main__":
    main()
