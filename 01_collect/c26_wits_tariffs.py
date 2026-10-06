"""MFN applied tariffs (UNCTAD TRAINS via the World Bank WITS API, no key) for clean and
dirty versions of the same vehicle: electric vs diesel trucks and road tractors (separate
electric lines from HS 2022), buses and cars (from HS 2017), plus the residual "other" truck
and car lines (870490, 870390) that held electric vehicles before HS 2022, lithium-ion
batteries, chargers and diesel engines, for all reporters, 2017-2024.

Used to test for an "environmental bias" in vehicle trade policy (Shapiro 2021): are
tariffs on electric trucks lower or higher than on their diesel counterparts?

Output: 03_data/01_raw/wits_tariffs/mfn_tariffs_vehicles.csv (reporter x HS6 x year)
"""
import re
import sys
import time
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from config import RAW_DIR  # noqa: E402
from helpers import get, log_download  # noqa: E402

BASE = "https://wits.worldbank.org/API/V1/SDMX/V21/datasource/TRN/reporter/all/partner/000/product/{p}/year/{y}/datatype/reported"
PRODUCTS = {
    "870421": "Truck diesel <=5t", "870422": "Truck diesel 5-20t", "870423": "Truck diesel >20t",
    "870441": "Truck diesel-hybrid <=5t", "870442": "Truck diesel-hybrid 5-20t", "870443": "Truck diesel-hybrid >20t",
    "870460": "Truck electric", "870490": "Truck other (electric before HS 2022)", "870121": "Tractor diesel", "870122": "Tractor diesel-hybrid", "870124": "Tractor electric",
    "870210": "Bus diesel", "870220": "Bus diesel-hybrid", "870240": "Bus electric",
    "870323": "Car petrol 1.5-3l", "870332": "Car diesel 1.5-2.5l", "870380": "Car electric", "870390": "Car other",
    "850760": "Li-ion batteries", "850440": "Static converters (chargers)", "840820": "Diesel engines for vehicles",
}
OUT = RAW_DIR / "wits_tariffs"


def main(years=range(2017, 2025)) -> None:
    rows = []
    for y in years:
        try:
            x = get(BASE.format(p=";".join(PRODUCTS), y=y), timeout=600, pause=1).text
        except Exception as e:  # noqa: BLE001 - year not yet published in TRAINS
            print(f"  {y}: not available ({e.__class__.__name__})")
            continue
        for attrs, body in re.findall(r"<Series ([^>]*)>(.*?)</Series>", x, re.S):
            a = dict(re.findall(r'(\w+)="([^"]*)"', attrs))
            for o in re.findall(r"<Obs ([^/]*)/>", body):
                ob = dict(re.findall(r'(\w+)="([^"]*)"', o))
                rows.append({"reporter_m49": a["REPORTER"], "hs6": a["PRODUCTCODE"], "year": int(ob["TIME_PERIOD"]),
                             "mfn_simple_avg": float(ob["OBS_VALUE"]), "min_rate": float(ob.get("MIN_RATE", "nan")),
                             "max_rate": float(ob.get("MAX_RATE", "nan")), "n_lines": int(ob.get("TOTALNOOFLINES", 0)),
                             "nomenclature": ob.get("NOMENCODE")})
        print(f"  {y}: {sum(r['year'] == y for r in rows):,} reporter-lines")
        time.sleep(1)
    d = pd.DataFrame(rows)
    d["product"] = d.hs6.map(PRODUCTS)
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / "mfn_tariffs_vehicles.csv"
    d.to_csv(path, index=False)
    log_download("WITS/UNCTAD TRAINS MFN tariffs", BASE, path, f"{len(PRODUCTS)} HS6 lines, all reporters, {min(years)}-{max(years)}")
    print(f"WITS: {len(d):,} rows, {d.reporter_m49.nunique()} reporters")


if __name__ == "__main__":
    main()
