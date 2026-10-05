"""Country x year covariates for merging with sales data: macro (WDI), grid carbon
intensity and generation mix (Ember), policy interest rates (BIS), diesel prices.

Output: 03_data/02_processed/country_year_covariates.csv
        03_data/02_processed/country_month_covariates.csv (grid intensity, policy rate, diesel)
"""
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from config import PROC_DIR, RAW_DIR  # noqa: E402

WDI_NAMES = {
    "NY.GDP.MKTP.CD": "gdp_usd", "NY.GDP.MKTP.PP.KD": "gdp_ppp_const", "NY.GDP.PCAP.PP.KD": "gdppc_ppp_const",
    "SP.POP.TOTL": "population", "SP.URB.TOTL.IN.ZS": "urban_share", "NV.IND.TOTL.ZS": "industry_va_share",
    "NV.IND.MANF.ZS": "manuf_va_share", "NE.TRD.GNFS.ZS": "trade_gdp", "TM.TAX.MANF.WM.AR.ZS": "tariff_manuf_wm",
    "TM.TAX.MRCH.WM.AR.ZS": "tariff_all_wm", "FR.INR.LEND": "lending_rate", "FR.INR.RINR": "real_rate",
    "FP.CPI.TOTL.ZG": "inflation", "PA.NUS.FCRF": "fx_lcu_usd", "PA.NUS.PPP": "ppp_factor",
    "EG.IMP.CONS.ZS": "energy_import_share", "EG.ELC.ACCS.ZS": "electricity_access",
    "EN.GHG.CO2.TR.MT.CE.AR5": "co2_transport_mt", "EN.GHG.ALL.MT.CE.AR5": "ghg_total_mt",
    "EN.GHG.CO2.MT.CE.AR5": "co2_total_mt",
}
BIS_TO_ISO3 = {"XM": "EA"}  # BIS uses ISO2; euro area = XM


def ember(freq: str) -> pd.DataFrame:
    d = pd.read_csv(RAW_DIR / "ember" / f"ember_{freq}_filtered.csv.gz", low_memory=False)
    d = d[d["Area type"] == "Country or economy"]
    t = "Year" if freq == "yearly" else "Date"
    ci = d[(d["Variable"] == "CO2 intensity")][["ISO 3 code", t, "Value"]].rename(
        columns={"Value": "grid_gco2_kwh"})
    share = d[(d["Category"] == "Electricity generation") & (d["Unit"] == "%")
              & d["Variable"].isin(["Clean", "Coal", "Wind and Solar", "Renewables"])]
    share = share.pivot_table(index=["ISO 3 code", t], columns="Variable", values="Value").reset_index()
    share.columns = ["ISO 3 code", t] + [f"gen_share_{c.lower().replace(' ', '_')}" for c in share.columns[2:]]
    out = ci.merge(share, on=["ISO 3 code", t], how="outer").rename(columns={"ISO 3 code": "iso3"})
    return out.rename(columns={t: "year" if freq == "yearly" else "month"})


def main() -> None:
    w = pd.read_csv(RAW_DIR / "worldbank" / "wdi_long.csv")
    w = w.pivot_table(index=["iso3", "year"], columns="indicator", values="value").reset_index()
    w = w.rename(columns=WDI_NAMES)
    meta = pd.read_csv(RAW_DIR / "worldbank" / "wdi_countries.csv")
    meta = meta[~meta.is_aggregate][["iso3", "iso2", "name", "region", "income"]]
    e = ember("yearly")
    b = pd.read_csv(RAW_DIR / "bis" / "bis_policy_rates_monthly.csv")
    b["iso2"] = b["ref_area"].replace(BIS_TO_ISO3)
    b["year"] = b["time_period"].str[:4].astype(int)
    b = b.groupby(["iso2", "year"], as_index=False)["obs_value"].mean().rename(columns={"obs_value": "policy_rate"})
    b = b.merge(meta[["iso2", "iso3"]], on="iso2", how="left")
    d = pd.read_csv(PROC_DIR / "diesel_prices_monthly.csv", parse_dates=["month"])
    d = d.assign(year=d.month.dt.year).groupby(["iso3", "year"], as_index=False)[["diesel_usd_l"]].mean()
    out = (w.merge(meta, on="iso3", how="inner").merge(e, on=["iso3", "year"], how="left")
           .merge(b[["iso3", "year", "policy_rate"]], on=["iso3", "year"], how="left")
           .merge(d, on=["iso3", "year"], how="left"))
    out = out[out.year >= 2005].sort_values(["iso3", "year"])
    out.to_csv(PROC_DIR / "country_year_covariates.csv", index=False)

    em = ember("monthly")
    em["month"] = pd.to_datetime(em["month"])
    bm = pd.read_csv(RAW_DIR / "bis" / "bis_policy_rates_monthly.csv")
    bm["iso2"] = bm["ref_area"].replace(BIS_TO_ISO3)
    bm["month"] = pd.to_datetime(bm["time_period"])
    bm = bm.merge(meta[["iso2", "iso3"]], on="iso2", how="left")[["iso3", "month", "obs_value"]].rename(
        columns={"obs_value": "policy_rate"})
    dm = pd.read_csv(PROC_DIR / "diesel_prices_monthly.csv", parse_dates=["month"])
    m = (em.merge(bm.dropna(subset=["iso3"]), on=["iso3", "month"], how="outer")
         .merge(dm[["iso3", "month", "diesel_eur_l", "diesel_usd_l"]], on=["iso3", "month"], how="outer"))
    m = m[m.month >= "2015-01-01"].sort_values(["iso3", "month"])
    m.to_csv(PROC_DIR / "country_month_covariates.csv", index=False)
    print(f"country-year: {out.iso3.nunique()} countries, {out.year.min()}-{out.year.max()}; "
          f"grid intensity non-missing {out.grid_gco2_kwh.notna().sum():,}")
    print(f"country-month: {m.iso3.nunique()} countries, {m.month.min():%Y-%m}-{m.month.max():%Y-%m}")


if __name__ == "__main__":
    main()
