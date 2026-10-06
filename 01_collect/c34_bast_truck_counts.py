"""Germany's automatic traffic counting stations on motorways and federal roads (BASt,
Jahresauswertung, all years 2003-2024; no key): average daily traffic of all motor vehicles
and of heavy vehicles (>3.5 t, 'Schwerverkehr'), weekday values, heavy-vehicle shares and
station coordinates (WGS84).

Used to measure where truck traffic is concentrated (for charging-site placement and
spatial designs) and how heavy-truck flows evolve by corridor.

Output: 03_data/01_raw/bast/bast_counting_stations_annual.csv
"""
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from config import CACHE_DIR, RAW_DIR  # noqa: E402
from helpers import download, log_download  # noqa: E402

URL = ("https://www.bast.de/DE/Themen/Digitales/HF_1/Massnahmen/verkehrszaehlung/Daten/2024_1/Jawe2024.csv"
       "?view=renderTcDataExportCSVAlleJahre")
KEEP = ["Jahr", "DZ_Nr", "DZ_Name", "Land_Code", "Str_Kl", "Str_Nr", "Anz_Fs_Q", "DTV_Kfz_MobisSo_Q",
        "DTV_Kfz_W_Q", "DTV_SV_MobisSo_Q", "DTV_SV_W_Q", "pSV_MobisSo_Q", "pSV_W_Q", "DTV_Lzg_Ri1", "DTV_Lzg_Ri2",
        "DTV_Sat_Ri1", "DTV_Sat_Ri2", "Koor_WGS84_N", "Koor_WGS84_E"]
OUT = RAW_DIR / "bast"


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    f = download(URL, CACHE_DIR / "bast" / "Jawe_all_years.csv", source="BASt counting stations", timeout=900,
                 overwrite="--refresh" in sys.argv)
    d = pd.read_csv(f, sep=";", encoding="latin1", decimal=",", thousands=".", low_memory=False)[KEEP]
    d.columns = ["year", "station", "name", "state", "road_class", "road_no", "lanes", "aadt_all", "aadt_all_weekday",
                 "aadt_heavy", "aadt_heavy_weekday", "heavy_share", "heavy_share_weekday", "aadt_lorry_trailer_r1",
                 "aadt_lorry_trailer_r2", "aadt_semitrailer_r1", "aadt_semitrailer_r2", "lat", "lon"]
    path = OUT / "bast_counting_stations_annual.csv"
    d.to_csv(path, index=False)
    log_download("BASt automatic counting stations (subset)", URL, path, "station x year; heavy-vehicle AADT")
    m = d[d.road_class == "A"]
    print(f"BASt: {len(d):,} station-years, {d.year.min()}-{d.year.max()}; motorway heavy AADT 2024 median "
          f"{m[m.year == 2024].aadt_heavy.median():,.0f}")


if __name__ == "__main__":
    main()
