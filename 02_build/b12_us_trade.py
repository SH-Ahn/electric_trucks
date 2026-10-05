"""US truck, bus and parts trade by segment, partner and month (US Census, HS10), with
units, customs value, dutiable value and calculated duties, so that effective tariff rates
and border unit values can be followed around the Section 232 truck tariff (Nov 2025).

Segments follow the HS10 lines: road tractors (new by GVW, used, electric), trucks by
gross weight and body (cab chassis vs complete truck), electric trucks and buses, chassis,
bodies, parts, diesel engines, lithium-ion batteries and trailers. Units are vehicles
(`NO`) for 8701, 8702 and 8704; other lines report values only.

Output: 03_data/02_processed/us_trade_segment_partner_month.csv
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from config import PROC_DIR, RAW_DIR  # noqa: E402

SRC = RAW_DIR / "census_trade"


def segment(hs: str) -> str:
    if hs.startswith("87012"):
        if hs.endswith("80"):
            return "Road tractor, used"
        return "Road tractor, electric" if hs.startswith("870124") else "Road tractor, new"
    if hs.startswith("870421"):
        return "Truck <=5 t"
    if hs.startswith("87042211"):
        return "Cab chassis 5-20 t"
    if hs.startswith("87042251"):
        return "Complete truck 5-20 t"
    if hs.startswith("870423"):
        return "Truck >20 t"
    if hs.startswith("870460"):
        return "Electric truck"
    if hs.startswith("8704"):
        return "Truck, hybrid or other"
    if hs.startswith("870240"):
        return "Electric bus"
    if hs.startswith("8702"):
        return "Bus, other"
    return {"8706": "Chassis with engine", "8707": "Bodies and cabs", "8708": "Parts",
            "8408": "Diesel engines", "8507": "Lithium-ion batteries", "8716": "Trailers"}.get(hs[:4], "Other")


def load(flow: str) -> pd.DataFrame:
    d = pd.read_csv(SRC / f"census_{flow}_hs10_monthly.csv.gz", low_memory=False,
                    dtype={"CTY_CODE": str, "I_COMMODITY": str, "E_COMMODITY": str})
    d = d[d.CTY_CODE.str.fullmatch(r"[1-9]\d{3}", na=False)]  # countries; codes starting 0 are groupings
    if flow == "imports":
        d = d.rename(columns={"I_COMMODITY": "hs10", "CON_VAL_MO": "value", "GEN_QY1_MO": "units",
                              "DUT_VAL_MO": "dutiable", "CAL_DUT_MO": "duty"})
    else:
        d = d.rename(columns={"E_COMMODITY": "hs10", "ALL_VAL_MO": "value", "QTY_1_MO": "units"})
        d["dutiable"] = np.nan
        d["duty"] = np.nan
    for c in ("value", "units", "dutiable", "duty"):
        d[c] = pd.to_numeric(d[c], errors="coerce")
    d["units"] = d["units"].where(d["UNIT_QY1"] == "NO")
    d["segment"] = d["hs10"].map(segment)
    d["flow"] = flow
    return d.rename(columns={"CTY_NAME": "partner", "time": "month"})


def main() -> None:
    d = pd.concat([load("imports"), load("exports")], ignore_index=True)
    g = (d.groupby(["flow", "segment", "partner", "month"])[["value", "units", "dutiable", "duty"]]
         .sum(min_count=1).reset_index())
    g["unit_value"] = g.value / g.units.where(g.units > 0)
    g["dutiable_share"] = g.dutiable / g.value.where(g.value > 0)
    g["effective_tariff"] = g.duty / g.value.where(g.value > 0)
    g.to_csv(PROC_DIR / "us_trade_segment_partner_month.csv", index=False)
    imp = g[(g.flow == "imports") & g.month.str.startswith("2024")]
    print(f"{len(g):,} rows, {g.month.min()}-{g.month.max()}; 2024 imports of new road tractors: "
          f"{imp[imp.segment == 'Road tractor, new'].units.sum():,.0f} units")


if __name__ == "__main__":
    main()
