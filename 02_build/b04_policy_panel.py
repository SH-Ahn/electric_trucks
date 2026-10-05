"""Country x quarter policy panel from the hand-curated policy database.

Each policy is active in a quarter if it starts on or before the quarter's last day
and has not ended before the quarter's first day. EU-level measures are assigned
to all EU27 members; multi-country rows (e.g. USMCA) are split. Instruments are
grouped into families used as regressors/controls in event studies.

Input : 03_data/01_raw/policy/policy_database.csv (+ mou_signatories.csv)
Output: 03_data/02_processed/policy_country_quarter.csv (one row per iso3 x quarter)
        03_data/02_processed/policy_long_active.csv     (iso3 x quarter x policy_id)
"""
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from config import PROC_DIR, RAW_DIR  # noqa: E402
from countries import EU27  # noqa: E402

FAMILY = {
    "purchase_incentive": {"purchase_tax_credit", "purchase_rebate", "purchase_grant", "purchase_voucher",
                           "purchase_subsidy", "scrappage_subsidy", "purchase_tax_exemption",
                           "corporate_tax_deduction", "accelerated_depreciation", "vat_differential",
                           "fiscal_incentive_and_procurement", "demonstration_subsidy",
                           "demonstration_programme"},
    "co2_fuel_standard": {"co2_fleet_standard", "co2_fuel_economy_standard"},
    "zev_requirement": {"zev_sales_mandate", "fleet_mandate", "ice_sales_phaseout",
                        "public_procurement_mandate", "public_fleet_electrification",
                        "industrial_decarbonisation_target", "public_procurement_support"},
    "road_charging_advantage": {"road_charging_exemption", "road_charging_co2", "zero_emission_zone"},
    "weight_allowance": {"weight_allowance"},
    "charging_infrastructure": {"charging_infrastructure_mandate", "charging_infrastructure_funding",
                                "infrastructure_tax_credit", "infrastructure_pilot"},
    "carbon_or_fuel_price": {"carbon_price_fuel", "fuel_carbon_standard"},
    "pollutant_standard": {"pollutant_emission_standard"},
    "pledge_target": {"pledge_target"},
    "disclosure_accounting": {"emissions_accounting_rule"},
    "vehicle_tax": {"excise_tax"},
    "industrial_policy": {"procurement_resilience_criteria"},
}
TRADE_INSTRUMENTS = {"tariff_national_security", "tariff_retaliatory", "tariff_emergency", "surtax",
                     "tariff_mfn_increase", "non_tariff_fee", "import_restriction", "countervailing_duty",
                     "tariff_reduction", "tariff_rate_quota", "rules_of_origin",
                     "trade_agreement_review"}


# EU acts that only enable member-state measures (e.g. optional toll exemptions) are kept at
# EU level; binding EU rules (CO2 standards, AFIR, CVD, ETS2, weights) apply to all EU27.
EU_ENABLING_ONLY = {"road_charging_co2", "road_charging_exemption", "emissions_accounting_rule"}


def expand_iso3(s: str, instrument: str = "") -> list[str]:
    out = []
    for code in str(s).split(";"):
        code = code.strip()
        out += EU27 if code == "EUU" and instrument not in EU_ENABLING_ONLY else [code]
    return out


def main(first="2015Q1", last="2027Q4") -> None:
    p = pd.read_csv(RAW_DIR / "policy" / "policy_database.csv", dtype=str)
    p = p[p["status"] != "proposed"]
    p["start"] = pd.to_datetime(p["start_date"], errors="coerce")
    p["end"] = pd.to_datetime(p["end_date"], errors="coerce")
    p = p.dropna(subset=["start"])
    p["iso3_list"] = [expand_iso3(i, inst) for i, inst in zip(p["iso3"], p["instrument"])]
    p = p.explode("iso3_list").rename(columns={"iso3_list": "country"})
    p = p[p["country"] != "WLD"]
    q = pd.period_range(first, last, freq="Q")
    grid = pd.DataFrame({"quarter": q, "q_start": q.start_time, "q_end": q.end_time})
    long = p.merge(grid, how="cross")
    active = (long["start"] <= long["q_end"]) & (long["end"].isna() | (long["end"] >= long["q_start"]))
    long = long[active]
    long["family"] = "other"
    for fam, inst in FAMILY.items():
        long.loc[long["instrument"].isin(inst), "family"] = fam
    trade = long["instrument"].isin(TRADE_INSTRUMENTS)
    long.loc[trade & (long["zev_effect"] == "-"), "family"] = "trade_barrier"
    long.loc[trade & (long["zev_effect"] == "+"), "family"] = "trade_liberalisation"
    long.loc[trade & (long["zev_effect"] == "0"), "family"] = "trade_other"
    rollback = {"deregulation", "executive_order", "co2_fleet_standard_flexibility"}
    long.loc[long["instrument"].isin(rollback), "family"] = "regulatory_rollback"
    keep = ["country", "quarter", "policy_id", "family", "instrument", "vehicle_scope", "zev_effect",
            "intensity_value", "intensity_unit"]
    long[keep].to_csv(PROC_DIR / "policy_long_active.csv", index=False)

    panel = (long.assign(n=1).pivot_table(index=["country", "quarter"], columns="family", values="n",
                                          aggfunc="sum", fill_value=0).reset_index())
    panel.columns.name = None
    fams = [c for c in panel.columns if c not in ("country", "quarter")]
    panel[fams] = (panel[fams] > 0).astype(int)
    panel["n_pro_zev_policies"] = (long[long.zev_effect == "+"].groupby(["country", "quarter"]).size()
                                   .reindex(pd.MultiIndex.from_frame(panel[["country", "quarter"]]),
                                            fill_value=0).values)
    mou = pd.read_csv(RAW_DIR / "policy" / "mou_signatories.csv").groupby("iso3")["year_joined"].min()
    panel["mou_signatory"] = (panel["quarter"].dt.year >= panel["country"].map(mou)).astype(int)
    panel = panel.rename(columns={"country": "iso3"})
    panel["quarter"] = panel["quarter"].astype(str)
    panel.to_csv(PROC_DIR / "policy_country_quarter.csv", index=False)
    print(f"policy panel: {panel.iso3.nunique()} countries x {panel.quarter.nunique()} quarters; "
          f"families: {fams}")
    print(panel[panel.quarter == "2026Q2"].set_index("iso3")[fams].sum().sort_values(ascending=False))


if __name__ == "__main__":
    main()
