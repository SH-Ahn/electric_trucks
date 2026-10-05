"""Eurostat: EU/EFTA road-vehicle registrations and stocks by motor energy, non-household
electricity prices, road freight activity and truck GHG emissions.

API: SDMX 3.0 (https://ec.europa.eu/eurostat/api/dissemination/sdmx/3.0/...), CSV 2.0.
Output: 03_data/01_raw/eurostat/<dataset>.csv
"""
import io
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from config import RAW_DIR  # noqa: E402
from helpers import get, log_download  # noqa: E402

BASE = "https://ec.europa.eu/eurostat/api/dissemination/sdmx/3.0/data/dataflow/ESTAT/{code}/1.0/*"
OUT = RAW_DIR / "eurostat"
OUT.mkdir(parents=True, exist_ok=True)

# dataset code -> (filters, description)
DATASETS = {
    # New registrations (flows), 2013-2025
    "road_eqr_lormot": ({}, "New lorries by type of motor energy (vehicle: >3.5 t and <=3.5 t)"),
    "road_eqr_tracmot": ({}, "New road tractors by type of motor energy"),
    "road_eqr_busmot": ({}, "New motor coaches, buses and trolley buses by type of motor energy"),
    "road_eqr_lorrit": ({}, "New lorries and their load capacity by permissible maximum gross weight"),
    # Stocks
    "road_eqs_lormot": ({}, "Lorries by type of motor energy (stock)"),
    "road_eqs_roaene": ({}, "Road tractors by type of motor energy (stock)"),
    "road_eqs_busmot": ({}, "Buses and coaches by type of motor energy (stock)"),
    "road_eqs_lorroa": ({}, "Lorries and road tractors by age (stock)"),
    # Energy prices: non-household electricity (semi-annual), bands relevant for depots
    "nrg_pc_205": ({"nrg_cons": "MWH500-1999,MWH2000-19999,MWH20000-69999", "currency": "EUR,PPS"},
                   "Electricity prices for non-household consumers, semi-annual, from 2007"),
    # Road freight activity (tonne-km) by reporting country
    "road_go_ta_tott": ({}, "Summary of annual road freight transport by type of operation and transport"),
    # GHG inventory: heavy-duty trucks and buses (CRF 1.A.3.b.iii), road transport, transport, total
    "env_air_gge": ({"src_crf": "CRF1A3B3,CRF1A3B,CRF1A3,TOTX4_MEMO", "airpol": "GHG,CO2",
                     "unit": "MIO_T"},
                    "GHG emissions by source sector (UNFCCC CRF), million tonnes CO2e"),
}


def fetch(code: str, filters: dict) -> pd.DataFrame:
    params = {f"c[{k}]": v for k, v in filters.items()}
    params.update({"format": "csvdata", "formatVersion": "2.0", "compress": "false"})
    r = get(BASE.format(code=code), params=params, timeout=300, pause=0.5)
    return pd.read_csv(io.StringIO(r.text), low_memory=False)


def main() -> None:
    for code, (filters, desc) in DATASETS.items():
        try:
            d = fetch(code, filters)
        except Exception as e:  # noqa: BLE001
            print(f"FAIL {code}: {e}")
            continue
        path = OUT / f"{code}.csv"
        d.to_csv(path, index=False)
        log_download("Eurostat", BASE.format(code=code), path, desc)
        span = f"{d.TIME_PERIOD.min()}-{d.TIME_PERIOD.max()}" if "TIME_PERIOD" in d else ""
        print(f"ok   {code:18s} {len(d):>8,} rows {span}")


if __name__ == "__main__":
    main()
