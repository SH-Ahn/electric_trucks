"""Freight Analysis Framework 5 (FAF5.7.1): US freight flows by origin-destination region,
mode, commodity (SCTG2) and distance band, annual 2018-2024 (tons, ton-miles, value).

Gives the size and geography of truck freight by distance band and commodity, i.e. the
derived-demand side of the truck market. The zip is cached outside Dropbox; aggregated
tables are written to 03_data/01_raw/faf5/.

Source: https://faf.ornl.gov/faf5/
"""
import sys
import zipfile
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from config import CACHE_DIR, RAW_DIR  # noqa: E402
from helpers import download, log_download  # noqa: E402

URL = "https://faf.ornl.gov/faf5/Data/Download_Files/FAF5.7.1_2018-2024.zip"
GUIDE = "https://faf.ornl.gov/faf5/data/FAF5%20User%20Guide.pdf"
UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/126.0 Safari/537.36"}  # ORNL resets connections from non-browser clients
OUT = RAW_DIR / "faf5"
OUT.mkdir(parents=True, exist_ok=True)


def main() -> None:
    download(GUIDE, OUT / "FAF5_User_Guide.pdf", source="FAF5 documentation", headers=UA)
    zpath = download(URL, CACHE_DIR / "faf5" / "FAF5.7.1_2018-2024.zip", source="FAF5 (ORNL/BTS)",
                     headers=UA, timeout=3600, note="regional O-D database, cached outside Dropbox")
    z = zipfile.ZipFile(zpath)
    name = next(n for n in z.namelist() if n.lower().endswith(".csv"))
    d = pd.read_csv(z.open(name), low_memory=False)
    year_cols = [c for c in d.columns if c.split("_")[-1].isdigit() and c.split("_")[0] in ("tons", "value", "tmiles")]
    keys = [c for c in ("dms_mode", "sctg2", "dist_band", "trade_type") if c in d.columns]
    g = d.groupby(keys)[year_cols].sum().reset_index()
    long = g.melt(id_vars=keys, value_vars=year_cols, var_name="var_year", value_name="amount")
    long[["measure", "year"]] = long["var_year"].str.rsplit("_", n=1, expand=True)
    long = long.pivot_table(index=keys + ["year"], columns="measure", values="amount").reset_index()
    path = OUT / "faf5_mode_sctg_distance_2018_2024.csv"
    long.to_csv(path, index=False)
    log_download("FAF5.7.1 (aggregated)", URL, path, "tons (kt), value (USD m), ton-miles (m) by mode x SCTG2 x distance band")
    print(f"FAF5: {len(long):,} rows; columns {list(long.columns)}")


if __name__ == "__main__":
    main()
