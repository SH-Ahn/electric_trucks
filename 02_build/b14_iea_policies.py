"""IEA Policies database (13,200 energy and climate policies, all countries) tagged by theme,
with a flag for measures that concern heavy-duty vehicles or road freight.

Themes come from the IEA's own topic, technology and policy-type fields and from patterns
in the title and description. A policy can carry several themes. The `heavy_freight` flag
marks measures that name trucks (not light trucks), lorries, buses, heavy-duty or commercial
vehicles, freight or logistics.

Input : 03_data/01_raw/iea_policies/iea_policies.csv.gz
Output: 03_data/02_processed/iea_policies_themes.csv      (one row per policy)
        03_data/02_processed/iea_policy_country_year.csv  (iso3 x year x theme counts of new policies)
"""
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from config import PROC_DIR, RAW_DIR  # noqa: E402

HEAVY = (r"heavy[- ]duty|(?<!light )(?<!light-duty )(?<!pickup )\btrucks?\b|lorr(?:y|ies)|\bHGVs?\b|\bHDVs?\b|"
         r"\bbus(?:es)?\b|freight|logistic|haulage|commercial vehicle|goods vehicle|drayage|truck fleet|"
         r"commercial fleet|fleet operator|tractor[- ]trailer|semi[- ]trailer|delivery vehicle")
# theme: (regex on title + description, {IEA fields that imply the theme})
THEMES = {
    "vehicle_purchase_incentive": (r"purchase|rebate|subsid|incentive|grant|voucher|tax credit|tax exemption|"
                                   r"registration tax|bonus|feebate|scrappage",
                                   {"Grants for demand", "Low-emissions and efficient transport spending programmes"}),
    "vehicle_standard": (r"fuel (?:economy|efficiency|consumption) standard|emission standard|CO2 standard|"
                         r"\bEuro [IVX0-9]+\b|Bharat Stage|China [IVX0-9]+ |greenhouse gas emission standard|"
                         r"phase[- ]?(?:2|3)|vehicle efficiency", {"Fuel efficiency standards"}),
    "zev_mandate_phaseout": (r"zero[- ]emission vehicle (?:mandate|requirement|target|sales)|\bZEV\b|"
                             r"phase[- ]out of (?:internal combustion|ICE|diesel|petrol)|ban on (?:new )?(?:diesel|petrol|ICE)|"
                             r"advanced clean (?:trucks|fleets)|new energy vehicle credit|dual[- ]credit", set()),
    "charging_infrastructure": (r"charging|charge point|chargers?\b|recharging|EVSE|megawatt",
                                {"Charging infrastructure spending programmes", "Electric charging infrastructure"}),
    "hydrogen": (r"hydrogen|fuel[- ]cell|\bH2\b", {"Hydrogen", "Hydrogen strategy", "Hydrogen spending programmes",
                                                 "Hydrogen electrolysis technologies"}),
    "alternative_fuels": (r"biodiesel|renewable diesel|\bHVO\b|biofuel|biomethane|\bLNG\b|\bCNG\b|natural gas vehicle|"
                          r"low[- ]carbon fuel standard|blending mandate|e-fuel", set()),
    "fuel_tax_carbon_price": (r"carbon tax|carbon price|emissions? trading|\bETS\b|fuel tax|excise|fuel levy|"
                              r"fuel subsid|diesel subsid|price cap on (?:diesel|fuel)|fuel price",
                              {"Carbon pricing instruments", "Fuel taxes", "Energy and fuel taxes"}),
    "road_pricing_access": (r"\btolls?\b|road (?:user )?charg|road pricing|congestion charg|low[- ]emission zone|"
                            r"zero[- ]emission zone|clean air zone|access restriction|vignette|distance[- ]based|"
                            r"weight (?:limit|allowance)", set()),
    "grid_power": (r"\bgrid\b|transmission|distribution network|interconnection|demand charge|electricity tariff|"
                   r"time[- ]of[- ]use|connection (?:cost|capacity)",
                   {"Electricity networks spending programmes"}),
    "land_use_urban": (r"urban planning|land[- ]use|zoning|spatial plan|warehouse|logistics (?:hub|centre|center|park)|"
                       r"depot|indirect source|truck parking|city logistics|last[- ]mile", {"GABC - Urban Planning"}),
    "rail_modal_shift": (r"\brail|modal shift|intermodal|inland waterway|combined transport",
                         {"Rail infrastructure spending programmes"}),
    "critical_minerals": (r"critical mineral|lithium|cobalt|nickel|graphite|rare earth", {"Critical Minerals"}),
    "battery_industry": (r"battery (?:manufactur|production|cell|recycl|supply chain|gigafactor)|gigafactor|"
                         r"battery passport|battery regulation", {"Battery technologies", "Battery storage spending programmes"}),
    "trade_industrial": (r"tariff|import dut|customs dut|local content|domestic content|made in|rules of origin|"
                         r"export (?:ban|restriction)|anti[- ]dumping|countervailing|manufacturing (?:incentive|subsid)",
                         {"Tariffs and duties", "Preferential trade agreements", "Grants for supply"}),
    "public_procurement_fleet": (r"public procurement|government fleet|public fleet|clean vehicles directive|"
                                 r"procurement of (?:electric|zero)", set()),
}
FIELDS = ("topics", "technologies", "policy_types", "tags")


def main() -> None:
    p = pd.read_csv(RAW_DIR / "iea_policies" / "iea_policies.csv.gz", dtype=str)
    text = (p.title.fillna("") + " " + p.description.fillna(""))
    labels = p[list(FIELDS)].fillna("").agg(";".join, axis=1).str.split(";").apply(lambda x: {s.strip() for s in x})
    transport = (p.topics.fillna("").str.contains("Transport") |
                 p.technologies.fillna("").str.contains("Transport|Road vehicles|Vehicle|Battery electric|charging",
                                                        regex=True) |
                 text.str.contains(r"vehicle|transport|truck|\bbus|freight|mobility", case=False, regex=True))
    p["transport"] = transport.astype(int)
    p["heavy_freight"] = (text.str.contains(HEAVY, case=False, regex=True) |
                          p.technologies.fillna("").str.contains("Commercial vehicles|Heavy", regex=True)).astype(int)
    for th, (rx, fields) in THEMES.items():
        p[th] = (text.str.contains(rx, case=False, regex=True) | labels.apply(lambda s: bool(s & fields))).astype(int)
    # vehicle purchase incentives and standards only count for transport measures
    for th in ("vehicle_purchase_incentive", "vehicle_standard", "zev_mandate_phaseout", "public_procurement_fleet"):
        p[th] *= p.transport
    p["year"] = pd.to_numeric(p.year, errors="coerce")
    p.to_csv(PROC_DIR / "iea_policies_themes.csv", index=False)

    long = p.assign(iso3=p.iso3.fillna("").str.split(";")).explode("iso3")
    long = long[long.iso3.str.len() == 3]
    cols = ["transport", "heavy_freight"] + list(THEMES)
    cy = long.groupby(["iso3", "year"])[cols].sum()
    cy["policies"] = long.groupby(["iso3", "year"]).size()
    hf = long[long.heavy_freight == 1].groupby(["iso3", "year"])[list(THEMES)].sum().add_prefix("hf_")
    cy = cy.join(hf).fillna(0).astype(int).reset_index()
    cy.to_csv(PROC_DIR / "iea_policy_country_year.csv", index=False)
    print(f"{len(p):,} policies; transport {p.transport.sum():,}; heavy/freight {p.heavy_freight.sum():,}")
    print(p[p.heavy_freight == 1][list(THEMES)].sum().sort_values(ascending=False).to_string())


if __name__ == "__main__":
    main()
