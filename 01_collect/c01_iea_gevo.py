"""IEA Global EV Data Explorer (Global EV Outlook 2026 edition).

EV sales, stock and sales/stock shares by country or region, mode (cars, vans,
buses, trucks) and powertrain (BEV, PHEV, FCEV), 2010-2025, plus the GEVO 2026
projections. IEA "trucks" = medium (3.5-15 t GVW) + heavy (>15 t) freight trucks;
"buses" = 10+ seats, urban and intercity.

Source: https://www.iea.org/data-and-statistics/data-tools/global-ev-data-explorer
Output: 03_data/01_raw/iea_gevo/iea_gevo2026_{historical,projections}.csv
"""
import io
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from config import RAW_DIR  # noqa: E402
from helpers import get, log_download  # noqa: E402

API = "https://api.iea.org/evs"
OUT = RAW_DIR / "iea_gevo"
OUT.mkdir(parents=True, exist_ok=True)


def fetch(**params) -> pd.DataFrame:
    r = get(API, params={"csv": "true", **params}, pause=0.3)
    if not r.text.startswith("region"):
        return pd.DataFrame()
    return pd.read_csv(io.StringIO(r.text))


def main() -> None:
    hist = pd.concat([fetch(year=y) for y in range(2010, 2026)], ignore_index=True)
    hist = hist.drop_duplicates()
    path = OUT / "iea_gevo2026_historical.csv"
    hist.to_csv(path, index=False)
    log_download("IEA GEVO 2026 data explorer", f"{API}?csv=true&year=2010..2025", path,
                 "all regions/modes/parameters, historical")
    print(f"historical: {len(hist):,} rows, {hist.region.nunique()} regions -> {path}")

    proj = []
    for cat in ("Projection-STEPS", "Projection-CPS", "Projection-APS"):
        for y in (2026, 2027, 2028, 2029, 2030, 2035):
            d = fetch(year=y, category=cat)
            if not d.empty:
                proj.append(d)
    if proj:
        proj = pd.concat(proj, ignore_index=True).drop_duplicates()
        path = OUT / "iea_gevo2026_projections.csv"
        proj.to_csv(path, index=False)
        log_download("IEA GEVO 2026 data explorer", f"{API}?csv=true&category=Projection-*", path,
                     "scenario projections")
        print(f"projections: {len(proj):,} rows, categories {sorted(proj.category.unique())}")


if __name__ == "__main__":
    main()
