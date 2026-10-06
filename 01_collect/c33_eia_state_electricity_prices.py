"""US electricity prices by state, sector and month (EIA-861M sales and revenue, 2010 to the
latest month; no key): commercial, industrial and transportation prices in cents/kWh, for the
cost of depot charging across states, alongside AFDC stations and FMCSA fleet structure.

Output: 03_data/01_raw/eia/eia_price_state_sector_monthly.csv (state x month x sector)
"""
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from config import CACHE_DIR, RAW_DIR  # noqa: E402
from helpers import download, log_download  # noqa: E402

URL = "https://www.eia.gov/electricity/data/state/xls/861m/HS861M%202010-.xlsx"
SECTORS = ["RESIDENTIAL", "COMMERCIAL", "INDUSTRIAL", "TRANSPORTATION", "TOTAL"]
OUT = RAW_DIR / "eia"


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    x = download(URL, CACHE_DIR / "eia" / "HS861M_2010-.xlsx", source="EIA-861M", overwrite=True)
    raw = pd.read_excel(x, header=None, skiprows=3)
    base = raw.iloc[:, :4].copy()
    base.columns = ["year", "month", "state", "data_status"]
    frames = []
    for k, sec in enumerate(SECTORS):
        blk = raw.iloc[:, 4 + 4 * k: 8 + 4 * k].copy()
        blk.columns = ["revenue_kusd", "sales_mwh", "customers", "price_cents_kwh"]
        frames.append(pd.concat([base, blk], axis=1).assign(sector=sec.lower()))
    d = pd.concat(frames, ignore_index=True)
    d = d[pd.to_numeric(d.year, errors="coerce").notna()]
    for c in ("year", "month", "revenue_kusd", "sales_mwh", "customers", "price_cents_kwh"):
        d[c] = pd.to_numeric(d[c], errors="coerce")
    path = OUT / "eia_price_state_sector_monthly.csv"
    d.to_csv(path, index=False)
    log_download("EIA-861M state sales and revenue (tidy)", URL, path, "cents/kWh by state, sector, month")
    old = OUT / "eia_avgprice_state_annual.csv"
    if old.exists():
        old.unlink()  # superseded annual file (ended in 2020)
    print(f"EIA: {len(d):,} rows, {int(d.year.min())}-{int(d.year.max())}, {d.state.nunique()} states")


if __name__ == "__main__":
    main()
