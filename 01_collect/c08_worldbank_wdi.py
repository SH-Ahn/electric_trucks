"""World Bank World Development Indicators: macro, trade, energy and emissions controls
by country and year, plus country metadata (ISO codes, region, income group).

Source: https://api.worldbank.org/v2 (no key needed)
Output: 03_data/01_raw/worldbank/wdi_long.csv, wdi_countries.csv
"""
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from config import RAW_DIR  # noqa: E402
from helpers import get, log_download  # noqa: E402

INDICATORS = {
    "NY.GDP.MKTP.CD": "GDP, current USD",
    "NY.GDP.MKTP.PP.KD": "GDP, PPP, constant 2021 international $",
    "NY.GDP.PCAP.PP.KD": "GDP per capita, PPP, constant 2021 international $",
    "SP.POP.TOTL": "Population, total",
    "SP.URB.TOTL.IN.ZS": "Urban population, % of total",
    "NV.IND.TOTL.ZS": "Industry (incl. construction), value added, % of GDP",
    "NV.IND.MANF.ZS": "Manufacturing, value added, % of GDP",
    "NE.TRD.GNFS.ZS": "Trade, % of GDP",
    "TM.TAX.MANF.WM.AR.ZS": "Tariff rate, applied, weighted mean, manufactured products, %",
    "TM.TAX.MRCH.WM.AR.ZS": "Tariff rate, applied, weighted mean, all products, %",
    "FR.INR.LEND": "Lending interest rate, %",
    "FR.INR.RINR": "Real interest rate, %",
    "FP.CPI.TOTL.ZG": "Inflation, consumer prices, annual %",
    "PA.NUS.FCRF": "Official exchange rate, LCU per USD, period average",
    "PA.NUS.PPP": "PPP conversion factor, GDP, LCU per international $",
    "EG.IMP.CONS.ZS": "Energy imports, net, % of energy use",
    "EG.ELC.ACCS.ZS": "Access to electricity, % of population",
    "EN.GHG.CO2.TR.MT.CE.AR5": "CO2 emissions from transport (energy), Mt CO2e",
    "EN.GHG.ALL.MT.CE.AR5": "Total GHG emissions excluding LULUCF, Mt CO2e",
    "EN.GHG.CO2.MT.CE.AR5": "CO2 emissions, total excluding LULUCF, Mt CO2e",
}
API = "https://api.worldbank.org/v2"
OUT = RAW_DIR / "worldbank"
OUT.mkdir(parents=True, exist_ok=True)


def fetch_indicator(code: str) -> pd.DataFrame:
    rows, page = [], 1
    while True:
        r = get(f"{API}/country/all/indicator/{code}",
                params={"format": "json", "date": "2000:2026", "per_page": 20000, "page": page},
                pause=0.3)
        js = r.json()
        if len(js) < 2 or js[1] is None:
            break
        rows += [{"iso3": x["countryiso3code"], "country": x["country"]["value"],
                  "indicator": code, "year": int(x["date"]), "value": x["value"]} for x in js[1]]
        if page >= js[0]["pages"]:
            break
        page += 1
    return pd.DataFrame(rows)


def main() -> None:
    frames = []
    for code, desc in INDICATORS.items():
        try:
            d = fetch_indicator(code)
            frames.append(d)
            print(f"ok   {code:28s} {d['value'].notna().sum():>6,} non-missing")
        except Exception as e:  # noqa: BLE001
            print(f"FAIL {code}: {e}")
    wdi = pd.concat(frames, ignore_index=True)
    wdi = wdi[wdi["iso3"].astype(bool)]
    path = OUT / "wdi_long.csv"
    wdi.to_csv(path, index=False)
    pd.Series(INDICATORS, name="description").rename_axis("indicator").to_csv(OUT / "wdi_indicators.csv")
    log_download("World Bank WDI", f"{API}/country/all/indicator/<code>", path, f"{len(frames)} indicators")

    js = get(f"{API}/country", params={"format": "json", "per_page": 400}).json()[1]
    meta = pd.DataFrame([{"iso3": c["id"], "iso2": c["iso2Code"], "name": c["name"],
                          "region": c["region"]["value"], "income": c["incomeLevel"]["value"],
                          "is_aggregate": c["region"]["value"] == "Aggregates"} for c in js])
    meta.to_csv(OUT / "wdi_countries.csv", index=False)
    print(f"countries: {len(meta)} ({(~meta.is_aggregate).sum()} economies)")


if __name__ == "__main__":
    main()
