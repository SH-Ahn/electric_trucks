"""Policy timeline (2019-2030) from the hand-curated policy database.

fig11_policy_timeline   one row per jurisdiction; bars show when each instrument family is in
                        force (open-ended policies drawn to 2030); x marks regulatory rollbacks
tab_policy_summary.tex  counts of policies by domain and instrument family
"""
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.lines import Line2D
from matplotlib.patches import Patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import plot_style as ps  # noqa: E402
from config import RAW_DIR, TAB_DIR  # noqa: E402

ROWS = [("United States (federal)", "USA", "national"), ("California", "USA", "subnational"),
        ("Canada (federal)", "CAN", "national"), ("Mexico", "MEX", "national"),
        ("European Union", "EUU", "supranational"), ("Germany", "DEU", "national"),
        ("Netherlands", "NLD", "national"), ("Austria", "AUT", "national"), ("Switzerland", "CHE", "national"),
        ("United Kingdom", "GBR", "national"), ("China", "CHN", "national"), ("India", "IND", "national"),
        ("Brazil", "BRA", "national")]
TODAY = pd.Timestamp("2026-10-05")
FAMILIES = [
    ("Purchase incentive", {"purchase_tax_credit", "purchase_rebate", "purchase_grant", "purchase_voucher",
                            "purchase_subsidy", "scrappage_subsidy", "purchase_tax_exemption",
                            "corporate_tax_deduction", "accelerated_depreciation"}),
    ("CO2 / fuel-economy standard", {"co2_fleet_standard", "co2_fuel_economy_standard"}),
    ("ZEV mandate, zone or procurement", {"zev_sales_mandate", "fleet_mandate", "zero_emission_zone",
                                          "public_procurement_mandate", "ice_sales_phaseout"}),
    ("Road-charge advantage", {"road_charging_exemption", "road_charging_co2"}),
    ("Trade barrier", {"tariff_national_security", "tariff_retaliatory", "surtax", "tariff_mfn_increase",
                       "non_tariff_fee", "countervailing_duty"}),
]
X0, X1 = pd.Timestamp("2019-01-01"), pd.Timestamp("2030-12-31")


def main() -> None:
    ps.use()
    p = pd.read_csv(RAW_DIR / "policy" / "policy_database.csv", dtype=str)
    p = p[p.status != "proposed"].copy()
    p["start"] = pd.to_datetime(p.start_date, errors="coerce")
    p["end"] = pd.to_datetime(p.end_date, errors="coerce")
    # Open-ended standards, mandates, charges and tariffs are drawn to 2030; open-ended spending
    # programmes only to today, since their funding horizon is unknown.
    spending = p.instrument.isin(FAMILIES[0][1])
    p.loc[p.end.isna() & spending, "end"] = TODAY
    p["end"] = p["end"].fillna(X1)
    p = p.dropna(subset=["start"])

    fig, ax = plt.subplots(figsize=(9.4, 6.2))
    lane_h = 0.15
    for r, (name, iso, level) in enumerate(ROWS):
        sel = p[p.iso3.str.split(";").map(lambda xs: iso in xs)]
        sel = sel[sel.level == level] if level != "national" else sel[sel.level.isin(["national", "supranational"])
                                                                          & ~sel.iso3.eq("EUU")]
        # Truck-focused chart: drop car-only and bus-only measures and programmes of uncertain status.
        sel = sel[~sel.vehicle_scope.isin(["LDV", "bus"]) & (sel.status != "uncertain")]
        for k, (fam, inst) in enumerate(FAMILIES):
            f = sel[sel.instrument.isin(inst) & (sel.zev_effect != "+" if fam == "Trade barrier" else True)]
            y = r + (k - 2) * lane_h
            for _, row in f.iterrows():
                s, e = max(row.start, X0), min(row.end, X1)
                if e <= s or e <= X0 or s >= X1:  # e.g. repealed before taking effect
                    continue
                ax.barh(y, (e - s).days, left=s, height=lane_h * 0.9, color=ps.SLOTS[k], linewidth=0)
        rb = sel[sel.instrument.isin({"deregulation", "co2_fleet_standard_flexibility"})
                 | (sel.status.isin(["repealed", "revoked"]) & (sel.zev_effect == "+"))]
        for _, row in rb.iterrows():
            when = row.start if row.instrument in ("deregulation", "co2_fleet_standard_flexibility") else row.end
            if X0 <= when <= X1:
                ax.plot(when, r, marker="x", color=ps.INK, markersize=6, markeredgewidth=1.5, zorder=4)
    ax.set_yticks(range(len(ROWS)), [r[0] for r in ROWS])
    ax.invert_yaxis()
    ax.set_xlim(X0, X1)
    ax.axvline(TODAY, color=ps.MUTED, linewidth=0.8)
    ax.annotate("Oct 2026", (TODAY, -0.6), ha="center", fontsize=7, color=ps.MUTED)
    ax.grid(axis="y", visible=False)
    ax.grid(axis="x", visible=True)
    handles = [Patch(color=ps.SLOTS[k], label=fam) for k, (fam, _) in enumerate(FAMILIES)]
    handles.append(Line2D([], [], marker="x", color=ps.INK, linestyle="", label="Repeal, revocation or relaxation"))
    ax.legend(handles=handles, loc="upper center", bbox_to_anchor=(0.45, -0.05), ncol=3)
    ax.set_title("Truck-electrification policy instruments in force, by jurisdiction")
    fig.text(0.0, -0.06, "Truck-relevant measures only (car-only and bus-only measures omitted). Open-ended rules "
             "drawn to 2030; open-ended spending programmes to Oct 2026.\nSource: project policy database "
             "(03_data/01_raw/policy/policy_database.csv), 105 policies with sources.", fontsize=7, color=ps.MUTED)
    fig.tight_layout()
    ps.save(fig, "fig11_policy_timeline")

    fam_of = {inst: fam for fam, insts in FAMILIES for inst in insts}
    fam_of.update({"weight_allowance": "Weight allowance", "charging_infrastructure_mandate": "Charging infrastructure",
                   "charging_infrastructure_funding": "Charging infrastructure",
                   "infrastructure_tax_credit": "Charging infrastructure", "infrastructure_pilot": "Charging infrastructure",
                   "carbon_price_fuel": "Carbon price / fuel standard", "fuel_carbon_standard": "Carbon price / fuel standard",
                   "pollutant_emission_standard": "Pollutant standard", "rules_of_origin": "Rules of origin / agreements",
                   "trade_agreement_review": "Rules of origin / agreements", "tariff_rate_quota": "Trade liberalisation",
                   "tariff_reduction": "Trade liberalisation", "deregulation": "Deregulation / rollback",
                   "executive_order": "Deregulation / rollback", "co2_fleet_standard_flexibility": "Deregulation / rollback",
                   "pledge_target": "Pledge / target"})
    allp = pd.read_csv(RAW_DIR / "policy" / "policy_database.csv", dtype=str)
    allp["family"] = allp.instrument.map(fam_of).fillna("Other instruments")
    summ = pd.crosstab(allp.family, allp.domain)
    summ["Total"] = summ.sum(axis=1)
    eff = pd.crosstab(allp.family, allp.zev_effect).reindex(columns=["+", "-", "0"], fill_value=0)
    eff.columns = ["Pro-ZEV", "Anti-ZEV", "Neutral"]
    summ = summ.join(eff).sort_values("Total", ascending=False)
    summ.columns = [c.replace("_", " ").capitalize() if c.islower() else c for c in summ.columns]
    summ.index.name = "Instrument family"
    summ.to_latex(TAB_DIR / "tab_policy_summary.tex", escape=True, position="htbp", label="tab:policysummary",
                  caption="Policy database: number of policies by instrument family, domain and direction of "
                          "effect on zero-emission trucks")
    print(summ.to_string())


if __name__ == "__main__":
    main()
