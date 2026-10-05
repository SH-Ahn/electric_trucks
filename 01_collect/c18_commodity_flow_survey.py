"""US Commodity Flow Survey public-use microdata (2017 PUF, 2022 PUMS): shipment-level records
with mode (for-hire truck, private truck, rail, ...), shipment distance, weight, value,
shipper industry (NAICS) and commodity (SCTG), weighted to national totals.

Used to measure which industries' freight moves by truck over short, predictable distances
(depot-charging feasible) and which depends on long-haul trucking. The zips (0.1 GB and
0.7 GB) are cached outside Dropbox; aggregated tables are written to 03_data/01_raw/cfs/.

Source: https://www.census.gov/programs-surveys/cfs.html
"""
import sys
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from config import CACHE_DIR, RAW_DIR  # noqa: E402
from helpers import download, log_download  # noqa: E402

FILES = {
    2017: "https://www2.census.gov/programs-surveys/cfs/datasets/2017/cfs-2017-puf-csv.zip",
    2022: "https://www2.census.gov/programs-surveys/cfs/datasets/2022/cfs_2022_pums.zip",
}
DOCS = {
    "cfs_2017_puf_users_guide.pdf": "https://www2.census.gov/programs-surveys/cfs/datasets/2017/cfs_2017_puf_users_guide.pdf",
    "cfs_2022_pums_data_dictionary.xlsx": "https://www2.census.gov/programs-surveys/cfs/datasets/2022/cfs_2022_pums_data_dictionary.xlsx",
}
# Mode codes differ by vintage (2017 PUF App. A-4; 2022 PUMS data dictionary).
MODES = {
    2017: {4: "For-hire truck", 5: "Company-owned truck", 6: "Rail", 14: "Parcel/USPS/courier",
           15: "Truck and rail", 16: "Truck and water", 11: "Air", 12: "Pipeline", 8: "Inland water",
           9: "Great Lakes", 10: "Deep sea", 101: "Multiple waterways", 17: "Rail and water",
           18: "Other multiple mode", 19: "Other mode", 0: "Suppressed"},
    2022: {111: "For-hire truck", 112: "Company-owned truck", 113: "Customer pick-up", 12: "Rail",
           21: "Parcel/USPS/courier", 22: "Truck and rail", 23: "Truck and water", 14: "Air", 15: "Pipeline",
           131: "Inland water", 132: "Great Lakes", 133: "Deep sea", 16: "Other single mode",
           24: "Rail and water", 25: "Other multiple mode", 30: "Unknown"},
}
DIST_BINS = [0, 50, 100, 150, 250, 500, 1000, 100000]
DIST_LABELS = ["<50", "50-100", "100-150", "150-250", "250-500", "500-1000", ">1000"]
OUT = RAW_DIR / "cfs"
OUT.mkdir(parents=True, exist_ok=True)


def find_col(cols, *cands):
    up = {c.upper(): c for c in cols}
    for c in cands:
        if c in up:
            return up[c]
    raise KeyError(cands)


def aggregate(year: int, zpath: Path) -> pd.DataFrame:
    z = zipfile.ZipFile(zpath)
    name = next(n for n in z.namelist() if n.lower().endswith(".csv"))
    parts = []
    reader = pd.read_csv(z.open(name), chunksize=1_000_000, low_memory=False)
    for chunk in reader:
        cols = chunk.columns
        mode = find_col(cols, "MODE")
        naics = find_col(cols, "NAICS", "SECTOR")  # 2022 PUMS reports NAICS sectors only
        sctg = find_col(cols, "SCTG")
        w = find_col(cols, "WGT_FACTOR", "WGT_FACTOR_FINAL", "WGT")
        wt = find_col(cols, "SHIPMT_WGHT")
        val = find_col(cols, "SHIPMT_VALUE")
        dist = find_col(cols, "SHIPMT_DIST_ROUTED", "SHIPMT_DIST_GC")  # 2022: great-circle only
        c = pd.DataFrame({
            "mode": pd.to_numeric(chunk[mode], errors="coerce"),
            "naics": chunk[naics].astype(str).str[:3] if naics == "NAICS" else chunk[naics].astype(str),
            "sctg": chunk[sctg].astype(str).str.zfill(2).str[:2],
            "weight": pd.to_numeric(chunk[w], errors="coerce"),
            "tons": pd.to_numeric(chunk[wt], errors="coerce") / 2000.0,
            "value": pd.to_numeric(chunk[val], errors="coerce"),
            "miles": pd.to_numeric(chunk[dist], errors="coerce"),
        })
        c["dist_band"] = pd.cut(c["miles"], DIST_BINS, labels=DIST_LABELS, right=False)
        c["w_tons"] = c["weight"] * c["tons"]
        c["w_tonmiles"] = c["w_tons"] * c["miles"]
        c["w_value"] = c["weight"] * c["value"]
        parts.append(c.groupby(["mode", "naics", "sctg", "dist_band"], observed=True)
                     [["weight", "w_tons", "w_tonmiles", "w_value"]].sum().reset_index())
        print(f"  {year}: {sum(len(p) for p in parts):,} aggregated rows")
    g = pd.concat(parts).groupby(["mode", "naics", "sctg", "dist_band"], observed=True).sum().reset_index()
    g = g.rename(columns={"weight": "shipments"})
    g["mode_label"] = g["mode"].map(MODES[year]).fillna("Other")
    g["truck"] = g["mode_label"].isin(["For-hire truck", "Company-owned truck", "Customer pick-up"]).astype(int)
    g["year"] = year
    return g


def main(years=(2017, 2022)) -> None:
    for name, url in DOCS.items():
        download(url, OUT / name, source="US Census CFS documentation")
    for year in years:
        zpath = download(FILES[year], CACHE_DIR / "cfs" / Path(FILES[year]).name,
                         source="US Census Commodity Flow Survey", timeout=3600,
                         note="public-use microdata, cached outside Dropbox")
        g = aggregate(year, zpath)
        path = OUT / f"cfs_{year}_mode_naics_sctg_distance.csv"
        g.to_csv(path, index=False)
        log_download("US Census CFS (aggregated)", FILES[year], path,
                     "weighted shipments, tons, ton-miles, value by mode x NAICS3 x SCTG2 x distance band")
        print(f"{year}: {len(g):,} cells; total tons {g.w_tons.sum() / 1e9:.2f} bn")


if __name__ == "__main__":
    main(tuple(int(y) for y in sys.argv[1:]) or (2017, 2022))
