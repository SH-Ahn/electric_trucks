"""North America panels: Canadian MHDV trade and registrations by fuel (StatCan), US
monthly truck-market series (FRED), and US duty-cycle heterogeneity (VIUS 2021).

Outputs (03_data/02_processed/):
  canada_vehicle_trade_monthly.csv     month x flow x product (CAD, customs basis, unadjusted)
  canada_registrations_fuel.csv        year x province x vehicle type x fuel
  us_monthly_series.csv                month x FRED series (wide)
  vius_duty_cycle_by_class.csv         GVWR class x vehicle type: weighted trucks, miles,
                                       share of mileage within 100 miles of home base
"""
import sys
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from config import PROC_DIR, RAW_DIR  # noqa: E402

NAPCS = "North American Product Classification System (NAPCS)"


def canada() -> None:
    t = pd.read_csv(RAW_DIR / "statcan" / "statcan_12100163.csv")
    t = t[(t["Basis"] == "Customs") & (t["Seasonal adjustment"] == "Unadjusted")]
    t = t.rename(columns={"REF_DATE": "month", "Trade": "flow", NAPCS: "product", "VALUE": "value"})
    t["product"] = t["product"].str.replace(r"\s*\[.*\]$", "", regex=True)
    t["value_cad"] = t["value"] * 10 ** t["SCALAR_ID"].fillna(0).map({0: 0, 3: 3, 6: 6}).fillna(0)
    t = t.groupby(["month", "flow", "product"], as_index=False)["value_cad"].sum()
    t.to_csv(PROC_DIR / "canada_vehicle_trade_monthly.csv", index=False)

    r = pd.read_csv(RAW_DIR / "statcan" / "statcan_23100308.csv")
    r = r.rename(columns={"REF_DATE": "year", "GEO": "geo", "Vehicle Type": "vehicle_type",
                          "Fuel Type": "fuel", "VALUE": "vehicles"})
    r[["year", "geo", "vehicle_type", "fuel", "vehicles"]].to_csv(
        PROC_DIR / "canada_registrations_fuel.csv", index=False)


def us_fred() -> None:
    f = pd.read_csv(RAW_DIR / "fred" / "fred_series_long.csv", parse_dates=["date"])
    m = (f.set_index("date").groupby("series_id")["value"].resample("MS").mean()
         .unstack(0).reset_index().rename(columns={"date": "month"}))
    m = m[m.month >= "2000-01-01"]
    m.to_csv(PROC_DIR / "us_monthly_series.csv", index=False)


def vius() -> None:
    z = zipfile.ZipFile(RAW_DIR / "vius" / "vius_2021_puf_csv.zip")
    d = pd.read_csv(z.open("vius_2021_puf.csv"), low_memory=False, dtype=str)
    num = ["TABWEIGHT", "MILESANNL", "RO_0_50", "RO_51_100", "RO_101_200", "RO_201_500", "RO_GT500"]
    for c in num:
        d[c] = pd.to_numeric(d[c], errors="coerce")
    d = d[d["BUSRELATED"] == "1"]  # some commercial activity
    ro = ["RO_0_50", "RO_51_100", "RO_101_200", "RO_201_500", "RO_GT500"]
    d[ro] = d[ro] / 100  # distance-band shares are reported in percent
    d["class"] = d["GVWR_CLASS"].replace({"2A": "2a", "2B": "2b"})
    d["within100"] = d["RO_0_50"] + d["RO_51_100"]
    d["local_90"] = (d["within100"] >= 0.9).astype(float).where(d["within100"].notna())
    d["electric"] = (d["FUELTYPE"] == "35").astype(float)

    def wavg(x, col):
        ok = x[col].notna()
        return np.average(x.loc[ok, col], weights=x.loc[ok, "TABWEIGHT"]) if ok.any() else np.nan

    rows = []
    for (cls, vt), g in d.groupby(["class", "VEHTYPE"]):
        rows.append({"gvwr_class": cls, "vehicle_type": vt, "trucks_weighted": g["TABWEIGHT"].sum(),
                     "n_obs": len(g), "mean_annual_miles": wavg(g, "MILESANNL"),
                     "share_miles_within_100mi": wavg(g, "within100"),
                     "share_trucks_90pct_within_100mi": wavg(g, "local_90"),
                     "share_electric": wavg(g, "electric")})
    out = pd.DataFrame(rows)
    out.to_csv(PROC_DIR / "vius_duty_cycle_by_class.csv", index=False)
    print(out[out.gvwr_class.isin(["3", "4", "5", "6", "7", "8"])].round(3).to_string(index=False))


def main() -> None:
    canada()
    us_fred()
    vius()


if __name__ == "__main__":
    main()
