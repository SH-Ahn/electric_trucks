"""US Census Bureau international trade API: monthly US imports and exports by HTS-10
line and partner country, 2019-01 onward, for trucks, tractors, buses, chassis,
cabs, drive-train parts, diesel engines and lithium-ion batteries.

This is the source for event studies around the Section 232 MHDV tariff
(effective 2025-11-01) and the Canada/Mexico flows behind it.

REQUIRES a free API key (https://api.census.gov/data/key_signup.html), exported as
CENSUS_API_KEY. Without it the script exits. First run 5 Oct 2026: 2019-01 to 2026-07,
about 200,000 import and 240,000 export rows.

API docs: https://www.census.gov/foreign-trade/reference/guides/Guide_to_International_Trade_Datasets.pdf
"""
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from config import CENSUS_API_KEY, RAW_DIR  # noqa: E402
from helpers import get, log_download  # noqa: E402

BASE = "https://api.census.gov/data/timeseries/intltrade/{flow}/hs"
HS6 = ["870121", "870122", "870123", "870124", "870129",            # road tractors
       "870210", "870220", "870230", "870240", "870290",            # buses
       "870421", "870422", "870423", "870441", "870442", "870443",  # diesel / hybrid trucks
       "870451", "870452", "870460", "870490",                      # petrol hybrid, electric, other
       "870600", "870710", "870790", "870840", "870850",            # chassis, bodies, gearboxes, axles
       "840820", "850760", "871620", "871631", "871639"]            # engines, Li-ion, trailers
FIELDS = {
    "imports": ["CTY_CODE", "CTY_NAME", "I_COMMODITY", "I_COMMODITY_SDESC", "GEN_VAL_MO",
                "GEN_QY1_MO", "UNIT_QY1", "CON_VAL_MO", "DUT_VAL_MO", "CAL_DUT_MO"],
    "exports": ["CTY_CODE", "CTY_NAME", "E_COMMODITY", "E_COMMODITY_SDESC", "ALL_VAL_MO",
                "QTY_1_MO", "UNIT_QY1"],
}
OUT = RAW_DIR / "census_trade"


def fetch(flow: str, hs6: str, start: str = "2019-01") -> pd.DataFrame:
    comm = "I_COMMODITY" if flow == "imports" else "E_COMMODITY"
    params = {"get": ",".join(FIELDS[flow]), "time": f"from {start}", "COMM_LVL": "HS10",
              comm: f"{hs6}*", "key": CENSUS_API_KEY}
    r = get(BASE.format(flow=flow), params=params, timeout=300, pause=0.5)
    if r.status_code == 204 or not r.text.strip():
        return pd.DataFrame()
    js = r.json()
    return pd.DataFrame(js[1:], columns=js[0])


def main() -> None:
    if not CENSUS_API_KEY:
        sys.exit("CENSUS_API_KEY not set: request a free key at "
                 "https://api.census.gov/data/key_signup.html and export it.")
    OUT.mkdir(parents=True, exist_ok=True)
    for flow in ("imports", "exports"):
        frames = []
        for hs6 in HS6:
            d = fetch(flow, hs6)
            print(f"  {flow} {hs6}: {len(d):,} rows")
            frames.append(d)
        d = pd.concat(frames, ignore_index=True)
        path = OUT / f"census_{flow}_hs10_monthly.csv.gz"
        d.to_csv(path, index=False, compression="gzip")
        log_download("US Census international trade API", BASE.format(flow=flow), path,
                     f"HS10 x country x month from 2019-01; {len(HS6)} HS6 headings")


if __name__ == "__main__":
    main()
