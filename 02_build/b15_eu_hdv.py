"""EU heavy-duty registrations and certified truck configurations (EEA CO2 monitoring data,
July 2021-June 2025).

Registrations are kept for trucks (N2, N3, including off-road G and special-purpose S
variants) and buses (M2, M3). Makes are harmonised and mapped to OEM groups. VECTO
sub-groups are mapped to duty cycles: rigid trucks (groups 4, 9) and tractors (5, 10) are
assigned to urban delivery (UD), regional delivery (RD) or long haul (LH) by cab and power
under Regulation (EU) 2019/1242; other groups are medium rigids, construction trucks or buses.

Input : 03_data/01_raw/eea_hdv/eea_hdv_registrations.csv, eea_hdv_vecto_groups.csv
Output: 03_data/02_processed/eu_hdv_registrations.csv   (period x month x iso3 x segment x mass class x
                                                         powertrain x make)
        03_data/02_processed/eu_hdv_vecto_subgroups.csv (period x iso3 x sub-group x duty cycle x powertrain x make)
"""
import re
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from config import PROC_DIR, RAW_DIR  # noqa: E402
from countries import EUROSTAT_GEO  # noqa: E402

MAKES = {r"^MERCEDES": "MERCEDES-BENZ", r"^SCANIA": "SCANIA", r"^MAN\b": "MAN", r"^IVECO": "IVECO",
         r"^FUSO": "FUSO", r"^(VOLKSWAGEN|VW\b)": "VOLKSWAGEN", r"^RENAULT": "RENAULT", r"^DAF": "DAF",
         r"^VOLVO": "VOLVO", r"^FORD": "FORD", r"^ISUZU": "ISUZU", r"^BYD": "BYD", r"^SOLARIS": "SOLARIS",
         r"^SETRA": "SETRA", r"^(EVOBUS|DAIMLER)": "MERCEDES-BENZ", r"^YUTONG": "YUTONG", r"^VDL": "VDL",
         r"^IRIZAR": "IRIZAR", r"^EBUSCO": "EBUSCO", r"^HYUNDAI": "HYUNDAI", r"^TESLA": "TESLA", r"^MAXUS": "MAXUS"}
GROUP_TYPE = {"4": "Rigid", "9": "Rigid", "5": "Tractor", "10": "Tractor"}
MISSION = {"UD": "urban delivery", "RD": "regional delivery", "LH": "long haul"}


def make_name(m: str) -> str:
    for rx, name in MAKES.items():
        if re.match(rx, m):
            return name
    return m


def duty_cycle(sg: str) -> str:
    m = re.match(r"^(?:group )?([A-Z]?\d+[a-z]?\d*)(?:-([A-Z]{2}))?", str(sg))
    if not m:
        return "Other"
    main, mission = m.group(1), m.group(2)
    if main in GROUP_TYPE:
        return f"{GROUP_TYPE[main]}, {MISSION.get(mission, 'unassigned')}"
    if main in {"1s", "1", "2", "3", "53", "54"}:
        return "Medium rigid (<16 t)"
    if main in {"11", "12", "16"}:
        return "Construction (6x4, 8x4)"
    if main.startswith(("3", "P3", "4")):
        return "Bus or coach"
    return "Other"


def main() -> None:
    oem = pd.read_csv(PROC_DIR / "oem_groups.csv").drop_duplicates("make").set_index("make").oem_group
    iso = lambda s: s.map({**EUROSTAT_GEO, "GR": "GRC"}).fillna(s)  # noqa: E731
    r = pd.read_csv(RAW_DIR / "eea_hdv" / "eea_hdv_registrations.csv", dtype={"make": str})
    cat = r.category.fillna("").str.upper().str[:2]
    r["segment"] = cat.map({"N2": "Truck", "N3": "Truck", "M2": "Bus", "M3": "Bus"})
    r = r[r.segment.notna() & r.period.between(2021, 2024)].copy()
    r["category"] = cat[r.index]
    r["make"] = r.make.fillna("").map(make_name)
    r["oem_group"] = r.make.map(oem).fillna("Other")
    r["iso3"] = iso(r.ms)
    keys = ["period", "month", "iso3", "segment", "category", "mass_class", "powertrain", "make", "oem_group"]
    r = r.groupby(keys, dropna=False)[["vehicles", "co2_n", "co2_sum"]].sum().reset_index()
    r.to_csv(PROC_DIR / "eu_hdv_registrations.csv", index=False)

    v = pd.read_csv(RAW_DIR / "eea_hdv" / "eea_hdv_vecto_groups.csv", dtype={"make": str})
    v = v[v.period.between(2021, 2024)].copy()
    v["duty_cycle"] = v.subgroup.map(duty_cycle)
    v["make"] = v.make.fillna("").map(make_name)
    v["oem_group"] = v.make.map(oem).fillna("Other")
    v["iso3"] = iso(v.ms)
    keys = ["period", "iso3", "subgroup", "duty_cycle", "powertrain", "sleeper_cab", "make", "oem_group"]
    v = v.groupby(keys, dropna=False)[["vehicles", "mass_kg_sum", "power_kw_sum", "battery_n",
                                       "battery_kwh_sum"]].sum().reset_index()
    v.to_csv(PROC_DIR / "eu_hdv_vecto_subgroups.csv", index=False)

    t = r[(r.segment == "Truck") & r.mass_class.isin(["7.5-16t", "16-26t", ">26t"])]
    t = t.pivot_table(index="period", columns="powertrain", values="vehicles", aggfunc="sum").fillna(0)
    print("trucks >7.5 t, BEV share (%):", (100 * t["Battery electric"] / t.sum(axis=1)).round(2).to_dict())
    z = v.pivot_table(index="duty_cycle", columns="powertrain", values="vehicles", aggfunc="sum").fillna(0)
    z["zev_share"] = 100 * z["Zero emission"] / z.sum(axis=1)
    print(z.round(1).sort_values("Combustion", ascending=False).to_string())


if __name__ == "__main__":
    main()
