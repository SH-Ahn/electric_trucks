"""Remote-sensing and inventory panels: satellite NO2 around truck-policy sites, heavy-industry
freight generators, and modelled road-transport emissions.

1. NO2 point x month (TROPOMI via TEMIS, 20 km means): level, 12-month rolling mean, and the
   rolling mean indexed to 2019 = 100, with steel-plant capacity from Climate TRACE. TROPOMI
   retrieval upgrades (v2.x, 2021) raised polluted-area columns, so only within-period contrasts
   between treated and comparison groups are meaningful, not raw trends.
2. Group x month means of the index, for the event-study style figures.
3. Heavy-industry freight generators by country (Climate TRACE assets): site counts, output and
   CO2e for steel, cement, coal mining and iron-ore mining.
4. Road-transport CO2e by country-year (Climate TRACE, modelled from activity proxies; does not
   capture fuel switching well, e.g. China's falling diesel demand after 2023).

Output: 03_data/02_processed/no2_points_monthly.csv
        03_data/02_processed/no2_groups_monthly.csv
        03_data/02_processed/heavy_industry_country.csv
        03_data/02_processed/road_emissions_country_year.csv
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from config import PROC_DIR, RAW_DIR  # noqa: E402

CT = RAW_DIR / "climate_trace"


def no2() -> tuple[pd.DataFrame, pd.DataFrame]:
    d = pd.read_csv(RAW_DIR / "tropomi" / "no2_points_monthly.csv")
    d["month"] = pd.to_datetime(d["month"])
    d = d.sort_values(["point_id", "month"])
    d.loc[d.valid_cells < 0.5 * d.cells, "no2_1e13"] = np.nan  # mostly cloud/snow-masked months
    d["log_no2"] = np.log(d.no2_1e13.where(d.no2_1e13 > 0))
    d["no2_r12"] = d.groupby("point_id").no2_1e13.transform(lambda s: s.rolling(12, min_periods=10).mean())
    base = d[d.month.dt.year == 2019].groupby("point_id").no2_1e13.mean()
    d["no2_index_2019"] = 100 * d.no2_r12 / d.point_id.map(base)
    a = pd.read_csv(CT / "climate_trace_heavy_industry_assets.csv")
    a = a[a.subsector == "iron-and-steel"][["name", "iso3", "capacity", "co2e_t"]]
    a = a.rename(columns={"capacity": "steel_capacity_t", "co2e_t": "plant_co2e_t"})
    d = d.merge(a.assign(name=a.name.str.slice(0, 60)).drop_duplicates(["name", "iso3"]),
                on=["name", "iso3"], how="left")
    g = d.groupby(["group", "month"]).agg(no2_index_2019=("no2_index_2019", "mean"),
                                          no2_1e13=("no2_1e13", "mean"), points=("point_id", "nunique"))
    return d, g.reset_index()


def heavy_industry() -> pd.DataFrame:
    a = pd.read_csv(CT / "climate_trace_heavy_industry_assets.csv")
    g = a.groupby(["iso3", "subsector"]).agg(sites=("asset_id", "nunique"), output_t=("activity", "sum"),
                                             co2e_t=("co2e_t", "sum")).reset_index()
    w = g.pivot_table(index="iso3", columns="subsector", values=["sites", "output_t"])
    w.columns = [f"{v}_{s.replace('-', '_')}" for v, s in w.columns]
    return w.reset_index()


def main() -> None:
    d, g = no2()
    d.to_csv(PROC_DIR / "no2_points_monthly.csv", index=False)
    g.to_csv(PROC_DIR / "no2_groups_monthly.csv", index=False)
    h = heavy_industry()
    h.to_csv(PROC_DIR / "heavy_industry_country.csv", index=False)
    r = pd.read_csv(CT / "climate_trace_road_transport_by_country.csv")
    r.to_csv(PROC_DIR / "road_emissions_country_year.csv", index=False)
    last = g[g.month == g.month.max() - pd.DateOffset(months=1)].set_index("group").no2_index_2019.round(0)
    print(f"NO2: {d.point_id.nunique()} points, {d.month.min():%Y-%m} to {d.month.max():%Y-%m}")
    print(last.to_string())
    print(f"heavy industry: {len(h)} countries; road emissions: {r.iso3.nunique()} countries, "
          f"{r.year.min()}-{r.year.max()}")


if __name__ == "__main__":
    main()
