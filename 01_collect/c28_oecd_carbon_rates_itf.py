"""OECD data via the SDMX API (no key):

1. Net effective carbon rates (OECD Taxing Energy Use / Effective Carbon Rates, 2018, 2021,
   2023): fuel excise taxes, carbon taxes, ETS prices and fossil-fuel subsidies per tonne of
   CO2, for road transport and diesel, ~70 countries. The 280 MB full file is cached outside
   Dropbox; road-transport rows are kept.
2. ITF short-term statistics: monthly/quarterly first registrations of goods road motor
   vehicles, and road vehicle-km (market size and activity outside the EU).

Output: 03_data/01_raw/oecd/necr_road_transport.csv, itf_first_registrations.csv, itf_road_traffic.csv
"""
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from config import CACHE_DIR, RAW_DIR  # noqa: E402
from helpers import download, log_download  # noqa: E402

BASE = "https://sdmx.oecd.org/public/rest/data/{df}/all?dimensionAtObservation=AllDimensions"
HDR = {"Accept": "application/vnd.sdmx.data+csv; charset=utf-8; labels=both"}
OUT = RAW_DIR / "oecd"


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    full = download(BASE.format(df="OECD.CTP.TPS,DSD_NECR@DF_NECRS,1.1"), CACHE_DIR / "oecd" / "necr.csv",
                    source="OECD net effective carbon rates", headers=HDR, timeout=1800, note="full file, cached")
    d = pd.read_csv(full, low_memory=False)
    d.columns = [c.split(":")[0] for c in d.columns]
    keep = (d.SECTOR.str.startswith(("ROAD", "_T:")) & d.UNIT_MEASURE.str.startswith("EUR_TCO2:")
            & d.STATISTICAL_OPERATION.str.startswith("MEANW") & d.PRICE_BASE.str.startswith("V:")
            & d.EMISSIONS_SOURCE.str.startswith(("DIES", "_T:", "GASO", "NGAS")))
    r = d.loc[keep, ["REF_AREA", "SECTOR", "EMISSIONS_SOURCE", "MEASURE", "TIME_PERIOD", "OBS_VALUE"]]
    r.to_csv(OUT / "necr_road_transport.csv", index=False)
    log_download("OECD net effective carbon rates (road transport subset)", BASE.format(df="DSD_NECR@DF_NECRS"),
                 OUT / "necr_road_transport.csv", "EUR/tCO2, weighted mean, current prices")
    for df, name in (("OECD.ITF,DSD_ST@DF_STREG,1.0", "itf_first_registrations.csv"),
                     ("OECD.ITF,DSD_ST@DF_STTRAFFIC,1.0", "itf_road_traffic.csv")):
        download(BASE.format(df=df), OUT / name, source="OECD ITF short-term transport statistics", headers=HDR,
                 timeout=600, overwrite=True)
    print(f"NECR road rows: {len(r):,}; countries {r.REF_AREA.nunique()}")


if __name__ == "__main__":
    main()
