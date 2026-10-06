"""European Alternative Fuels Observatory (EAFO, European Commission; no key): chart data for the
EU27 and 34 European countries, downloaded from the CSV files behind the EAFO country pages.

Kept: public recharging points under AFIR (AC and DC by power class, incl. ultra-fast >=350 kW),
recharging points dedicated to or exclusively for heavy-duty vehicles (AFIR reporting from 2026),
hydrogen, CNG/LNG and LPG stations, new registrations and fleets of alternative-fuel trucks
(N2/N3) and buses (M2/M3), and the country comparison of HDV infrastructure and AF truck fleets.

Output: 03_data/01_raw/eafo/eafo_charts_long.csv (country x chart x period x series)
"""
import io
import sys
import time
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from config import RAW_DIR  # noqa: E402
from helpers import SESSION, log_download  # noqa: E402

BASE = "https://alternative-fuels-observatory.ec.europa.eu/sites/default/files/csv/{slug}/{chart}.csv"
UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/126.0 Safari/537.36"}
SLUGS = ["european-union-eu27", "austria", "belgium", "bulgaria", "croatia", "cyprus", "czech-republic", "denmark",
         "estonia", "finland", "france", "germany", "greece", "hungary", "iceland", "ireland", "italy", "latvia",
         "liechtenstein", "lithuania", "luxembourg", "malta", "netherlands", "norway", "poland", "portugal", "romania",
         "slovakia", "slovenia", "spain", "sweden", "switzerland", "turkey", "united-kingdom"]
CHARTS = ["recharging_points_afir", "ac_public_recharging_points_afir", "dc_public_recharging_points_afir",
          "eu_27_hdv", "h2_refuelling_stations", "cng_lng_refuelling_stations", "lpg_refuelling_stations",
          "new_registrations_n2_n3", "new_registrations_m2_m3", "fleet_n2_n3_total_number", "fleet_m2_m3_total_number",
          "market_share_new_registrations_n2_n3", "market_share_new_registrations_m2_m3"]
EU_ONLY = ["countries_overview_of_hdv_infrastructure", "fleet_overview_of_af_trucks_n2_n3",
           "fleet_overview_of_af_buses_m2_m3", "countries_overview_of_recharging_stations"]
OUT = RAW_DIR / "eafo"


def fetch(slug: str, chart: str) -> pd.DataFrame | None:
    r = SESSION.get(BASE.format(slug=slug, chart=chart), headers=UA, timeout=60)
    if r.status_code != 200 or r.text.lstrip().startswith("<"):
        return None
    d = pd.read_csv(io.StringIO(r.content.decode("utf-8-sig")))
    if d.empty:
        return None
    key = d.columns[0]
    long = d.melt(id_vars=key, var_name="series", value_name="value").rename(columns={key: "period"})
    long["period_type"] = key
    long.insert(0, "chart", chart)
    long.insert(0, "slug", slug)
    return long


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    frames, missing = [], 0
    for slug in SLUGS:
        for chart in CHARTS + (EU_ONLY if slug == "european-union-eu27" else []):
            d = fetch(slug, chart)
            if d is None:
                missing += 1
            else:
                frames.append(d)
            time.sleep(0.2)
    d = pd.concat(frames, ignore_index=True)
    d["value"] = pd.to_numeric(d.value, errors="coerce")
    path = OUT / "eafo_charts_long.csv"
    d.to_csv(path, index=False)
    log_download("European Alternative Fuels Observatory (chart CSVs)", BASE, path,
                 f"{len(SLUGS)} pages x {len(CHARTS)} charts; {missing} not published")
    print(f"EAFO: {len(d):,} rows, {d.slug.nunique()} pages, {d.chart.nunique()} charts; {missing} chart-pages missing")


if __name__ == "__main__":
    main()
