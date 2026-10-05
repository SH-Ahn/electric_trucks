"""Energy-price panels: diesel (EU Weekly Oil Bulletin, US EIA via FRED) and
non-household electricity (Eurostat), plus an indicative per-km energy-cost gap
between a diesel and a battery-electric 40 t tractor.

Outputs (03_data/02_processed/):
  diesel_prices_eu_weekly.csv     iso3 x week: EUR/L with and without taxes, tax wedge
  diesel_prices_monthly.csv       iso3 x month: EU countries + USA, EUR/L and USD/L (net of VAT for EU)
  electricity_prices_eu_semi.csv  iso3 x half-year: non-household EUR/kWh by consumption band
  energy_cost_gap_eu_semi.csv     iso3 x half-year: diesel vs electric EUR/100 km (parametric)

Per-km assumptions (documented, adjustable): 40 t long-haul tractor diesel 31 L/100 km;
battery-electric 120 kWh/100 km (ICCT/T&E real-world range 110-135). Firms recover VAT,
so the comparison uses diesel net of VAT and electricity excluding VAT and recoverable taxes.
"""
import re
import sys
from pathlib import Path

import openpyxl
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from config import PROC_DIR, RAW_DIR  # noqa: E402

DIESEL_L_PER_100KM = 31.0
ELEC_KWH_PER_100KM = 120.0
ISO2_TO_3 = {"AT": "AUT", "BE": "BEL", "BG": "BGR", "CY": "CYP", "CZ": "CZE", "DE": "DEU",
             "DK": "DNK", "EE": "EST", "ES": "ESP", "FI": "FIN", "FR": "FRA", "GR": "GRC",
             "EL": "GRC", "HR": "HRV", "HU": "HUN", "IE": "IRL", "IT": "ITA", "LT": "LTU",
             "LU": "LUX", "LV": "LVA", "MT": "MLT", "NL": "NLD", "PL": "POL", "PT": "PRT",
             "RO": "ROU", "SE": "SWE", "SI": "SVN", "SK": "SVK", "UK": "GBR", "NO": "NOR",
             "IS": "ISL", "LI": "LIE", "CH": "CHE", "TR": "TUR", "RS": "SRB", "ME": "MNE",
             "MK": "MKD", "AL": "ALB", "BA": "BIH", "XK": "XKX", "UA": "UKR", "MD": "MDA",
             "GE": "GEO", "EU": "EU27", "EA": "EA", "EU27_2020": "EU27", "EA20": "EA"}
COL = re.compile(r"^([A-Z]{2,3})_price_(with|wo)_tax_diesel$")


def oil_bulletin() -> pd.DataFrame:
    wb = openpyxl.load_workbook(RAW_DIR / "eu_oil_bulletin" / "oil_bulletin_history.xlsx",
                                read_only=True)
    frames = []
    for sheet, tax in (("Prices with taxes", "with"), ("Prices wo taxes", "wo")):
        rows = list(wb[sheet].iter_rows(values_only=True))
        hdr = rows[0]
        cols = {i: COL.match(h).group(1) for i, h in enumerate(hdr)
                if isinstance(h, str) and COL.match(h)}
        recs = [(r[0], cols[i], r[i]) for r in rows[3:] if hasattr(r[0], "year")
                for i in cols if isinstance(r[i], (int, float))]
        d = pd.DataFrame(recs, columns=["date", "ctr", f"diesel_{tax}_tax_eur_1000l"])
        frames.append(d.set_index(["date", "ctr"]))
    d = pd.concat(frames, axis=1).reset_index()
    d["iso3"] = d["ctr"].map(ISO2_TO_3).fillna(d["ctr"])
    d["diesel_eur_l"] = d["diesel_with_tax_eur_1000l"] / 1000
    d["diesel_net_eur_l"] = d["diesel_wo_tax_eur_1000l"] / 1000
    d["tax_wedge_eur_l"] = d["diesel_eur_l"] - d["diesel_net_eur_l"]
    d["date"] = pd.to_datetime(d["date"])
    return d[["iso3", "date", "diesel_eur_l", "diesel_net_eur_l", "tax_wedge_eur_l"]].sort_values(["iso3", "date"])


def vat_rates() -> pd.Series:
    """Latest standard VAT on diesel by country, from the Oil Bulletin VAT sheet."""
    wb = openpyxl.load_workbook(RAW_DIR / "eu_oil_bulletin" / "oil_bulletin_history.xlsx", read_only=True)
    out, ctr = {}, None
    for r in wb["VAT"].iter_rows(min_row=5, values_only=True):
        if isinstance(r[0], str) and r[0].endswith("_"):
            ctr = r[0][:-1]
        if ctr and isinstance(r[3], (int, float)) and ctr not in out:
            out[ctr] = r[3] / 100
    return pd.Series({ISO2_TO_3.get(k, k): v for k, v in out.items()}, name="vat_diesel")


def fred_monthly() -> pd.DataFrame:
    f = pd.read_csv(RAW_DIR / "fred" / "fred_series_long.csv", parse_dates=["date"])
    us = f[f.series_id == "GASDESW"].set_index("date")["value"].resample("MS").mean() / 3.78541
    eur = f[f.series_id == "EXUSEU"].set_index("date")["value"].resample("MS").mean()
    d = pd.DataFrame({"diesel_usd_l": us, "usd_per_eur": eur}).dropna(subset=["diesel_usd_l"])
    return d


def main() -> None:
    w = oil_bulletin()
    w.to_csv(PROC_DIR / "diesel_prices_eu_weekly.csv", index=False)

    m = (w.assign(month=w["date"].dt.to_period("M").dt.to_timestamp())
         .groupby(["iso3", "month"], as_index=False)[["diesel_eur_l", "diesel_net_eur_l", "tax_wedge_eur_l"]].mean())
    vat = vat_rates()
    m["vat_diesel"] = m["iso3"].map(vat)
    m["diesel_ex_vat_eur_l"] = m["diesel_eur_l"] / (1 + m["vat_diesel"])
    fx = fred_monthly()
    m = m.merge(fx[["usd_per_eur"]], left_on="month", right_index=True, how="left")
    m["diesel_usd_l"] = m["diesel_eur_l"] * m["usd_per_eur"]
    us = fx.reset_index().rename(columns={"date": "month"})
    us["iso3"] = "USA"
    us["diesel_eur_l"] = us["diesel_usd_l"] / us["usd_per_eur"]
    m = pd.concat([m, us[["iso3", "month", "diesel_usd_l", "diesel_eur_l", "usd_per_eur"]]],
                  ignore_index=True)
    m.to_csv(PROC_DIR / "diesel_prices_monthly.csv", index=False)

    e = pd.read_csv(RAW_DIR / "eurostat" / "nrg_pc_205.csv")
    e = e[(e["tax"] == "X_VAT") & (e["currency"] == "EUR") & (e["unit"] == "KWH")]
    e = e.rename(columns={"geo": "iso2", "TIME_PERIOD": "period", "OBS_VALUE": "eur_kwh"})
    e["iso3"] = e["iso2"].map(ISO2_TO_3).fillna(e["iso2"])
    e = e.pivot_table(index=["iso3", "period"], columns="nrg_cons", values="eur_kwh").reset_index()
    e.columns.name = None
    e = e.rename(columns={"MWH500-1999": "elec_eur_kwh_500_2000mwh",
                          "MWH2000-19999": "elec_eur_kwh_2000_20000mwh",
                          "MWH20000-69999": "elec_eur_kwh_20000_70000mwh"})
    e.to_csv(PROC_DIR / "electricity_prices_eu_semi.csv", index=False)

    m["period"] = m["month"].dt.year.astype(str) + "-S" + ((m["month"].dt.month > 6) + 1).astype(str)
    dsemi = m.groupby(["iso3", "period"], as_index=False)["diesel_ex_vat_eur_l"].mean()
    g = dsemi.merge(e, on=["iso3", "period"], how="inner")
    g["diesel_eur_100km"] = g["diesel_ex_vat_eur_l"] * DIESEL_L_PER_100KM
    g["elec_eur_100km"] = g["elec_eur_kwh_2000_20000mwh"] * ELEC_KWH_PER_100KM
    g["elec_to_diesel_cost_ratio"] = g["elec_eur_100km"] / g["diesel_eur_100km"]
    g["saving_eur_100km"] = g["diesel_eur_100km"] - g["elec_eur_100km"]
    g.to_csv(PROC_DIR / "energy_cost_gap_eu_semi.csv", index=False)
    last = g[g.period == g.period.max()].sort_values("elec_to_diesel_cost_ratio")
    print(f"weekly diesel: {w.iso3.nunique()} areas, {w.date.min():%Y-%m} to {w.date.max():%Y-%m}")
    print(f"energy-cost gap {g.period.max()}:\n",
          last[["iso3", "diesel_eur_100km", "elec_eur_100km", "elec_to_diesel_cost_ratio"]].round(2).to_string(index=False))


if __name__ == "__main__":
    main()
