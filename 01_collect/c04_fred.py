"""FRED (St. Louis Fed) series for the US truck market, fuel prices and macro controls.

No API key needed: uses the public fredgraph CSV endpoint. Series that fail to
download (renamed or discontinued) are reported and skipped.

Output: 03_data/01_raw/fred/fred_series_long.csv (series_id, date, value) and
        03_data/01_raw/fred/fred_series_meta.csv
"""
import io
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from config import RAW_DIR  # noqa: E402
from helpers import get, log_download  # noqa: E402

SERIES = {
    # Truck market (BEA / Fed / BLS)
    "HTRUCKSSAAR": "Motor vehicle retail sales: heavy weight trucks (>14,000 lb GVW), millions, SAAR (BEA)",
    "HTRUCKSNSA": "Motor vehicle retail sales: heavy weight trucks, thousands, NSA (BEA)",
    "IPG33612S": "Industrial production: heavy duty truck manufacturing (NAICS 33612), index, SA",
    "IPG3361T3S": "Industrial production: motor vehicles and parts, index, SA",
    "PCU336120336120": "PPI by industry: heavy duty truck manufacturing, index",
    "PCU3361203361201": "PPI: heavy duty truck manufacturing, primary products, index",
    "PCU336211336211": "PPI by industry: motor vehicle body manufacturing, index",
    "PCU336350336350": "PPI by industry: motor vehicle transmission and power train parts, index",
    "TRUCKD11": "ATA truck tonnage index, SA",
    "TSIFRGHT": "Freight transportation services index (BTS), SA",
    "CES4348400001": "All employees: truck transportation, thousands, SA",
    # Freight markets (derived demand for trucks)
    "FRGSHPUSM649NCIS": "Cass Freight Index: shipments, NSA",
    "FRGEXPUSM649NCIS": "Cass Freight Index: expenditures, NSA",
    "PCU484121484121": "PPI by industry: general freight trucking, long-distance truckload",
    "PCU484122484122": "PPI by industry: general freight trucking, long-distance less-than-truckload",
    "RAILFRTCARLOADSD11": "Rail freight carloads, SA",
    # Energy prices
    "GASDESW": "US No. 2 diesel retail price, all types, USD/gal, weekly (EIA)",
    "DDFUELUSGULF": "US Gulf Coast ultra-low-sulfur No. 2 diesel spot price, USD/gal, daily (EIA)",
    "MCOILBRENTEU": "Brent crude oil price, USD/bbl, monthly (EIA)",
    "MCOILWTICO": "WTI crude oil price, USD/bbl, monthly (EIA)",
    "APU000072610": "Average price: electricity per kWh, US city average, USD (BLS)",
    "APU000074714": "Average price: gasoline, unleaded regular, USD/gal (BLS)",
    "PNGASEUUSDM": "Natural gas price, EU (TTF), USD/MMBtu, monthly (IMF)",
    "PNGASUSUSDM": "Natural gas price, US Henry Hub, USD/MMBtu, monthly (IMF)",
    # Macro, rates and exchange rates
    "FEDFUNDS": "Effective federal funds rate, percent, monthly",
    "DPRIME": "Bank prime loan rate, percent",
    "EXCAUS": "CAD per USD, monthly",
    "EXMXUS": "MXN per USD, monthly",
    "EXCHUS": "CNY per USD, monthly",
    "EXUSEU": "USD per EUR, monthly",
    "EXJPUS": "JPY per USD, monthly",
    "EXINUS": "INR per USD, monthly",
    "CPIAUCSL": "US CPI, all items, SA",
    "INDPRO": "US industrial production index, SA",
}

OUT = RAW_DIR / "fred"
OUT.mkdir(parents=True, exist_ok=True)


def main() -> None:
    frames, meta = [], []
    for sid, desc in SERIES.items():
        url = f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={sid}"
        try:
            r = get(url, pause=0.5)
            d = pd.read_csv(io.StringIO(r.text))
            d.columns = ["date", "value"]
            d["value"] = pd.to_numeric(d["value"], errors="coerce")
            d["series_id"] = sid
            frames.append(d.dropna(subset=["value"]))
            meta.append({"series_id": sid, "description": desc, "first": d.date.min(),
                         "last": d.date.max(), "n_obs": len(d)})
            print(f"ok   {sid:18s} {d.date.min()} - {d.date.max()}")
        except Exception as e:  # noqa: BLE001 - report and continue
            print(f"FAIL {sid:18s} {e}")
            meta.append({"series_id": sid, "description": desc, "first": None, "last": None,
                         "n_obs": 0})
    long = pd.concat(frames, ignore_index=True)[["series_id", "date", "value"]]
    path = OUT / "fred_series_long.csv"
    long.to_csv(path, index=False)
    pd.DataFrame(meta).to_csv(OUT / "fred_series_meta.csv", index=False)
    log_download("FRED", "https://fred.stlouisfed.org/graph/fredgraph.csv?id=<series>", path,
                 f"{len(frames)} series")


if __name__ == "__main__":
    main()
