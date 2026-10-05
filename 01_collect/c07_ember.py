"""Ember electricity data: generation mix, demand and power-sector CO2 intensity by
country, yearly (2000-2025) and monthly (2015-2026).

Used to compute the grid carbon intensity faced by electric trucks and the
well-to-wheel emissions avoided per e-truck by country and year.

The full long-format files (50-70 MB) are cached outside Dropbox; a filtered
extract is written to 03_data/01_raw/ember/.

Source: https://ember-energy.org/data/ (CC-BY-4.0)
"""
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from config import CACHE_DIR, RAW_DIR  # noqa: E402
from helpers import download, log_download  # noqa: E402

BASE = "https://storage.googleapis.com/emb-prod-bkt-publicdata/public-downloads/"
FILES = {"yearly": "yearly_full_release_long_format.csv",
         "monthly": "monthly_full_release_long_format.csv"}
KEEP_CATEGORIES = {"Power sector emissions", "Electricity generation", "Electricity demand",
                   "Electricity prices", "Electricity imports"}
OUT = RAW_DIR / "ember"
OUT.mkdir(parents=True, exist_ok=True)


def main() -> None:
    for freq, fname in FILES.items():
        cache = download(BASE + fname, CACHE_DIR / "ember" / fname, source="Ember", overwrite=True)
        d = pd.read_csv(cache, low_memory=False)
        d = d[d["Category"].isin(KEEP_CATEGORIES)]
        path = OUT / f"ember_{freq}_filtered.csv.gz"
        d.to_csv(path, index=False, compression="gzip")
        log_download("Ember (filtered)", BASE + fname, path, f"categories: {sorted(KEEP_CATEGORIES)}")
        t = "Year" if "Year" in d else "Date"
        print(f"{freq}: {len(d):,} rows, {d['Area'].nunique()} areas, {d[t].min()} - {d[t].max()}")


if __name__ == "__main__":
    main()
