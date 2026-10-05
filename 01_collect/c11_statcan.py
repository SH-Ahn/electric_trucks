"""Statistics Canada tables (WDS full-table CSV downloads, no key).

23-10-0308  Vehicle registrations by vehicle type (incl. Class 7, Class 8, buses) and
            fuel type (diesel, gasoline, BEV, PHEV, HEV), by province, annual 2017-
12-10-0163  International merchandise trade by NAPCS commodity, monthly 1988- (filtered
            to motor vehicles: "Medium and heavy trucks, buses and other motor vehicles",
            light vehicles, engines and parts). No partner split, but Canada's truck
            exports go almost entirely to the US.
20-10-0085  New motor vehicle sales, monthly (units and dollars; trucks incl. light trucks)

Source: https://www150.statcan.gc.ca/t1/wds/rest/getFullTableDownloadCSV/<pid>/en
"""
import io
import sys
import zipfile
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from config import RAW_DIR  # noqa: E402
from helpers import get, log_download  # noqa: E402

WDS = "https://www150.statcan.gc.ca/t1/wds/rest/getFullTableDownloadCSV/{pid}/en"
TABLES = {
    "23100308": None,
    "12100163": "North American Product Classification System (NAPCS)",
    "20100085": None,
}
# NAPCS labels carry bracketed codes (e.g. "... [C162]"), so match on the label text.
NAPCS_KEEP = ("Total of all merchandise|Motor vehicles and parts|Passenger cars and light trucks|"
              "Medium and heavy trucks, buses, and other motor vehicles|"
              "Tires; motor vehicle engines and motor vehicle parts|Motor vehicle engines and motor vehicle parts")
OUT = RAW_DIR / "statcan"
OUT.mkdir(parents=True, exist_ok=True)


def main() -> None:
    for pid, filter_col in TABLES.items():
        zip_url = get(WDS.format(pid=pid)).json()["object"]
        z = zipfile.ZipFile(io.BytesIO(get(zip_url, timeout=600).content))
        name = next(n for n in z.namelist() if n.endswith(".csv") and "MetaData" not in n)
        d = pd.read_csv(z.open(name), low_memory=False)
        if filter_col:
            d = d[d[filter_col].str.contains(NAPCS_KEEP, regex=True, na=False)]
        path = OUT / f"statcan_{pid}.csv"
        d.to_csv(path, index=False)
        log_download("Statistics Canada", zip_url, path, f"table {pid}; {len(d):,} rows")
        print(f"ok   {pid}: {len(d):,} rows, {d.REF_DATE.min()} - {d.REF_DATE.max()}")


if __name__ == "__main__":
    main()
