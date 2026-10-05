"""Eurostat road freight statistics: how trucks are used, by reporting country.

Distance class, type of operation (national / international / cabotage), type of transport
(hire-or-reward vs own account), operator industry (NACE), maximum laden weight, vehicle age,
and type of goods. These describe each country's duty-cycle mix, which shapes the feasibility
and economics of electric trucks (e.g. long-haul international haulage vs urban distribution).

Output: 03_data/01_raw/eurostat_freight/<dataset>.csv
"""
import io
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from config import RAW_DIR  # noqa: E402
from helpers import get, log_download  # noqa: E402

BASE = "https://ec.europa.eu/eurostat/api/dissemination/sdmx/3.0/data/dataflow/ESTAT/{code}/1.0/*"
DATASETS = {
    "road_go_ta_dc": "Road freight by distance class and type of transport (t, tkm, vkm), annual",
    "road_go_ta_tott": "Road freight by type of operation and type of transport, annual",
    "road_go_tq_tott": "Road freight by type of operation and type of transport, quarterly",
    "road_go_ta_nace": "Road freight by NACE activity of the vehicle operator, annual",
    "road_go_ta_mplw": "Road freight by maximum permissible laden weight of vehicle, annual",
    "road_go_ta_agev": "Road freight by age of vehicle, annual",
    "road_go_ta_tg": "Road freight by type of goods (NST 2007) and type of transport, annual",
    "road_go_ta_dctg": "Road freight by distance class and type of goods, annual",
}
OUT = RAW_DIR / "eurostat_freight"
OUT.mkdir(parents=True, exist_ok=True)


def main() -> None:
    for code, desc in DATASETS.items():
        try:
            r = get(BASE.format(code=code), params={"format": "csvdata", "formatVersion": "2.0",
                                                    "compress": "false"}, timeout=600, pause=0.5)
            d = pd.read_csv(io.StringIO(r.text), low_memory=False)
        except Exception as e:  # noqa: BLE001
            print(f"FAIL {code}: {e}")
            continue
        path = OUT / f"{code}.csv"
        d.to_csv(path, index=False)
        log_download("Eurostat road freight", BASE.format(code=code), path, desc)
        print(f"ok   {code:16s} {len(d):>9,} rows {d.TIME_PERIOD.min()}-{d.TIME_PERIOD.max()}")


if __name__ == "__main__":
    main()
