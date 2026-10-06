"""CEPII BACI bilateral trade in energy products (HS17, 2017-2024), from the cached BACI zip:
crude oil (2709), refined petroleum products incl. diesel and gas oil (271000: BACI pools all
of heading 2710 into one code), LNG (271111), natural gas (271121) and coal (2701).

Used to measure each importer's exposure to origin-specific supply shocks (e.g. the 2026
closure of the Strait of Hormuz) by its pre-shock import shares by origin, the shares of a
shift-share design for diesel and electricity prices.

Output: 03_data/01_raw/baci/baci_hs17_V202601_energy.csv.gz
"""
import sys
import zipfile
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from config import CACHE_DIR, RAW_DIR  # noqa: E402
from helpers import download, log_download  # noqa: E402

VERSION = "V202601"
URL = f"https://www.cepii.fr/DATA_DOWNLOAD/baci/data/BACI_HS17_{VERSION}.zip"
KEEP = ("2709", "2710", "271111", "271121", "2701")
OUT = RAW_DIR / "baci"


def main() -> None:
    zpath = download(URL, CACHE_DIR / "baci" / f"BACI_HS17_{VERSION}.zip", source="CEPII BACI",
                     note="full zip cached outside Dropbox", timeout=3600)
    frames = []
    with zipfile.ZipFile(zpath) as z:
        for m in sorted(x for x in z.namelist() if x.startswith("BACI_HS17_Y")):
            with z.open(m) as f:
                for chunk in pd.read_csv(f, dtype={"k": str}, chunksize=2_000_000):
                    chunk["k"] = chunk["k"].str.zfill(6)
                    frames.append(chunk[chunk["k"].str.startswith(KEEP)])
    d = pd.concat(frames, ignore_index=True)
    d.columns = ["year", "exporter", "importer", "hs6", "value_kusd", "qty_tonnes"]
    d["qty_tonnes"] = pd.to_numeric(d["qty_tonnes"], errors="coerce")
    path = OUT / f"baci_hs17_{VERSION}_energy.csv.gz"
    d.to_csv(path, index=False, compression="gzip")
    log_download("CEPII BACI (energy products)", URL, path, f"HS17 {', '.join(KEEP)}; {len(d):,} rows")
    print(f"energy trade: {len(d):,} rows, {d.year.min()}-{d.year.max()}; "
          f"{d.groupby('hs6').value_kusd.sum().div(1e6).round(0).to_dict()} (USD bn)")


if __name__ == "__main__":
    main()
