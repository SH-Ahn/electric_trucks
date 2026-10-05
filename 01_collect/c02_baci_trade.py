"""CEPII BACI bilateral trade (HS6, annual), filtered to trucks, buses, tractors,
chassis, bodies, parts, trailers, engines and batteries; cars kept for comparison.

BACI reconciles exporter and importer reports from UN Comtrade. Values are in
thousand current USD, quantities in metric tonnes (no unit counts: use Comtrade
for vehicle numbers).

Versions used (release V202601):
  HS22: 2022-2024, the first nomenclature with a separate line for electric trucks (870460)
  HS17: 2017-2024, separate lines for electric buses (870240) and tractors (870124)

The zips (0.3 GB and 0.8 GB) are cached in CACHE_DIR (outside Dropbox); only the
filtered extract is written to 03_data/01_raw/baci/.

Source: http://www.cepii.fr/CEPII/en/bdd_modele/bdd_modele_item.asp?id=37
Reference: Gaulier & Zignago (2010), CEPII WP 2010-23.
"""
import sys
import zipfile
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from config import CACHE_DIR, RAW_DIR  # noqa: E402
from helpers import download, log_download  # noqa: E402

VERSION = "V202601"
URL = "https://www.cepii.fr/DATA_DOWNLOAD/baci/data/BACI_{hs}_{v}.zip"
OUT = RAW_DIR / "baci"
OUT.mkdir(parents=True, exist_ok=True)

# HS6 prefixes to keep (matched on the first 4 or 6 digits).
KEEP_PREFIXES = (
    "8701",            # tractors (870121-29 road tractors for semi-trailers, by propulsion)
    "8702",            # buses, 10+ persons, by propulsion (870240 = electric only)
    "8703",            # cars (comparison group; 870380 = electric only)
    "8704",            # goods vehicles (870421-23 diesel by GVW; 870460 = electric only, HS22)
    "8705",            # special-purpose vehicles (cranes, concrete mixers, ...)
    "8706",            # chassis fitted with engines
    "8707",            # bodies, including cabs
    "8708",            # parts and accessories of motor vehicles
    "8716",            # trailers and semi-trailers
    "840820",          # compression-ignition engines for vehicles of chapter 87
    "850760",          # lithium-ion accumulators
    "850790",          # parts of accumulators
)


def keep(code: str) -> bool:
    return code.startswith(KEEP_PREFIXES)


def filter_zip(zpath: Path, hs: str) -> pd.DataFrame:
    frames = []
    with zipfile.ZipFile(zpath) as z:
        members = sorted(m for m in z.namelist() if m.startswith(f"BACI_{hs}_Y"))
        for m in members:
            with z.open(m) as f:
                for chunk in pd.read_csv(f, dtype={"k": str}, chunksize=2_000_000):
                    chunk["k"] = chunk["k"].str.zfill(6)
                    frames.append(chunk[chunk["k"].map(keep)])
            print(f"  {hs} {m}: cumulative rows {sum(len(x) for x in frames):,}")
        for meta in z.namelist():
            if meta.startswith(("country_codes", "product_codes")):
                (OUT / meta).write_bytes(z.read(meta))
    d = pd.concat(frames, ignore_index=True)
    d.columns = ["year", "exporter", "importer", "hs6", "value_kusd", "qty_tonnes"]
    d["qty_tonnes"] = pd.to_numeric(d["qty_tonnes"], errors="coerce")
    return d


def main(versions=("HS22", "HS17")) -> None:
    for hs in versions:
        url = URL.format(hs=hs, v=VERSION)
        zpath = download(url, CACHE_DIR / "baci" / f"BACI_{hs}_{VERSION}.zip", source="CEPII BACI",
                         note="full zip cached outside Dropbox", timeout=3600)
        d = filter_zip(zpath, hs)
        path = OUT / f"baci_{hs.lower()}_{VERSION}_vehicles.csv.gz"
        d.to_csv(path, index=False, compression="gzip")
        log_download("CEPII BACI (filtered)", url, path,
                     f"HS {hs}, chapters 8701-8708, 8716, 840820, 850760/90; {len(d):,} rows")
        print(f"{hs}: {len(d):,} rows, years {d.year.min()}-{d.year.max()} -> {path.name}")


if __name__ == "__main__":
    main(tuple(sys.argv[1:]) or ("HS22", "HS17"))
