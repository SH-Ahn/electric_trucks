"""Tidy IEA EV panel: region x year x mode with EV sales/stock by powertrain, shares and
implied total market size (EV sales / EV sales share).

Input : 03_data/01_raw/iea_gevo/iea_gevo2026_historical.csv
Output: 03_data/02_processed/iea_ev_region_year.csv
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from config import PROC_DIR, RAW_DIR  # noqa: E402
from countries import iso3_from_name  # noqa: E402

MODES = ["Trucks", "Buses", "Vans", "Cars"]
KEEP = {("EV sales", "EV"): "ev_sales", ("EV sales", "BEV"): "bev_sales",
        ("EV sales", "PHEV"): "phev_sales", ("EV sales", "FCEV"): "fcev_sales",
        ("EV sales share", "EV"): "ev_sales_share", ("EV stock", "EV"): "ev_stock",
        ("EV stock", "BEV"): "bev_stock", ("EV stock share", "EV"): "ev_stock_share"}


def main() -> None:
    d = pd.read_csv(RAW_DIR / "iea_gevo" / "iea_gevo2026_historical.csv")
    d = d[d["mode"].isin(MODES)]
    d["var"] = [KEEP.get((p, pt)) for p, pt in zip(d["parameter"], d["powertrain"])]
    d = d.dropna(subset=["var"])
    w = d.pivot_table(index=["region", "year", "mode"], columns="var", values="value",
                      aggfunc="first").reset_index()
    w.columns.name = None
    w["iso3"] = w["region"].map(iso3_from_name)
    w["is_country"] = w["iso3"].notna()
    share = w["ev_sales_share"] / 100
    w["total_sales_implied"] = np.where(share > 0, w["ev_sales"] / share, np.nan)
    w.loc[share < 0.005, "total_sales_implied"] = np.nan  # too noisy when share is rounded to <0.5%
    stock_share = w["ev_stock_share"] / 100
    w["total_stock_implied"] = np.where(stock_share > 0, w["ev_stock"] / stock_share, np.nan)
    w.loc[stock_share < 0.005, "total_stock_implied"] = np.nan
    cols = ["region", "iso3", "is_country", "year", "mode", "ev_sales", "bev_sales", "phev_sales",
            "fcev_sales", "ev_sales_share", "total_sales_implied", "ev_stock", "bev_stock",
            "ev_stock_share", "total_stock_implied"]
    w = w[cols].sort_values(["mode", "region", "year"])
    path = PROC_DIR / "iea_ev_region_year.csv"
    w.to_csv(path, index=False)
    t = w[(w["mode"] == "Trucks") & w["is_country"]]
    print(f"saved {path.name}: {len(w):,} rows; trucks: {t.iso3.nunique()} countries, "
          f"years {t.year.min()}-{t.year.max()}")
    unmatched = sorted(set(w.loc[~w.is_country, "region"]))
    print("aggregates/unmatched regions:", unmatched)


if __name__ == "__main__":
    main()
