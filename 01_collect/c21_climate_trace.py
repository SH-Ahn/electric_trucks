"""Climate TRACE (remote-sensing and model based emissions inventory, API v6, no key).

1. Country road-transportation emissions (CO2e) by year, all countries, 2015-2025.
2. Asset-level heavy-industry sites that generate short-haul heavy freight (the first
   market for electric trucks in China): iron and steel, cement, coal mining, iron mining,
   with coordinates, capacity and activity, for major truck markets.

Source: https://climatetrace.org (CC BY 4.0)
"""
import sys
import time
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from config import RAW_DIR  # noqa: E402
from helpers import get, log_download  # noqa: E402

API = "https://api.climatetrace.org/v6"
SUBSECTORS = ["iron-and-steel", "cement", "coal-mining", "iron-mining"]
COUNTRIES = ["CHN", "IND", "USA", "AUS", "BRA", "ZAF", "IDN", "MEX", "DEU", "POL", "TUR", "RUS", "VNM",
             "THA", "KOR", "JPN", "CAN", "CHL"]
OUT = RAW_DIR / "climate_trace"
OUT.mkdir(parents=True, exist_ok=True)


def road_emissions() -> pd.DataFrame:
    """The API returns a world total unless countries are listed; small batches avoid gateway timeouts."""
    iso = [c["alpha3"] for c in get(f"{API}/definitions/countries").json()]
    rows = []
    for year in range(2015, 2026):
        for k in range(0, len(iso), 10):
            js = get(f"{API}/country/emissions", params={"since": year, "to": year, "sectors": "transportation",
                                                         "subsectors": "road-transportation",
                                                         "countries": ",".join(iso[k:k + 10])}, pause=0.5, timeout=300).json()
            js = js if isinstance(js, list) else [js]
            for r in js:
                rows.append({"iso3": r["country"], "year": year, "road_co2e_t": r["emissions"].get("co2e_100yr"),
                             "road_co2_t": r["emissions"].get("co2")})
        print(f"  road emissions {year}: {sum(r['year'] == year for r in rows)} countries")
    return pd.DataFrame(rows)


def assets() -> pd.DataFrame:
    rows = []
    for sub in SUBSECTORS:
        for iso in COUNTRIES:
            offset = 0
            while True:
                js = get(f"{API}/assets", params={"subsectors": sub, "countries": iso, "limit": 1000,
                                                  "offset": offset}, pause=0.3).json()
                batch = js.get("assets") or []
                for a in batch:
                    lon, lat = (a.get("Centroid") or {}).get("Geometry", [None, None])
                    em = next((e for e in a.get("EmissionsSummary") or [] if e.get("Gas") == "co2e_100yr"), {})
                    rows.append({"asset_id": a.get("Id"), "name": a.get("Name"), "iso3": a.get("Country"),
                                 "subsector": sub, "asset_type": a.get("AssetType"), "lon": lon, "lat": lat,
                                 "activity": em.get("Activity"), "activity_units": em.get("ActivityUnits"),
                                 "capacity": em.get("Capacity"), "co2e_t": em.get("EmissionsQuantity")})
                if len(batch) < 1000:
                    break
                offset += 1000
            time.sleep(0.2)
        print(f"  assets {sub}: {sum(r['subsector'] == sub for r in rows):,}")
    return pd.DataFrame(rows)


def main() -> None:
    r = road_emissions()
    p = OUT / "climate_trace_road_transport_by_country.csv"
    r.to_csv(p, index=False)
    log_download("Climate TRACE API v6", f"{API}/country/emissions", p, "road-transportation CO2e by country-year")
    a = assets()
    p = OUT / "climate_trace_heavy_industry_assets.csv"
    a.to_csv(p, index=False)
    log_download("Climate TRACE API v6", f"{API}/assets", p, f"{SUBSECTORS} in {len(COUNTRIES)} countries")
    print(f"done: {len(r):,} country-years, {len(a):,} assets")


if __name__ == "__main__":
    main()
