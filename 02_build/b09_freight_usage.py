"""Freight-use panels: how trucks are used, for duty-cycle heterogeneity in truck demand.

1. Europe, country x year (Eurostat road freight; the reporting country is where the truck is
   registered, so these line up with registrations): distance-class shares of vehicle-km and
   tonne-km, international and cabotage shares, own-account share, empty running, fleet age,
   average haul and load, and goods mix, merged with zero-emission registration shares. Plus a
   country x quarter freight-activity series (tonne-km). Laden-weight classes (road_go_ta_mplw)
   are not used: Belgium and Italy classify by the tractor's own weight, others by the
   combination.
2. Europe, goods x distance (NST 2007): the share of each commodity's tonne-km hauled
   under 150 km and under 300 km.
3. United States, shipper industry x distance (Commodity Flow Survey 2017, 2022): truck share
   of tonnage and the short-haul share of truck tonnage. 2017 uses routed miles and 2022
   great-circle miles, so short-haul shares are higher in 2022 by construction.
4. United States, distance band x year (Freight Analysis Framework 5.7.1, 2018-2024): truck
   tons, ton-miles and value, and truck share of all modes, domestic and trade flows.
5. Germany truck-toll mileage index (2021 = 100), monthly (raw and calendar/seasonally adjusted).

Output: 03_data/02_processed/eu_freight_profile_country_year.csv
        03_data/02_processed/eu_freight_activity_country_quarter.csv
        03_data/02_processed/eu_freight_goods_distance.csv
        03_data/02_processed/us_cfs_truck_profile.csv
        03_data/02_processed/us_faf_truck_distance_year.csv
        03_data/02_processed/de_toll_mileage_monthly.csv
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from config import PROC_DIR, RAW_DIR  # noqa: E402
from countries import EU27, EUROSTAT_GEO  # noqa: E402

EF = RAW_DIR / "eurostat_freight"
SHORT = ["KM_LT50", "KM50-149"]
MEDIUM = ["KM150-299", "KM300-499"]
LONG = ["KM500-999", "KM1000-1999", "KM2000-5999", "KM_GE6000"]
AGE_MID = {"Y_LT2": 1.0, "Y2": 2.5, "Y3": 3.5, "Y4": 4.5, "Y5": 5.5, "Y6": 6.5, "Y7": 7.5, "Y8": 8.5,
           "Y9": 9.5, "Y10-14": 12.5, "Y_GE15": 17.5}
GOODS = {  # NST 2007 divisions grouped by how the freight is hauled
    "agri_food": ["GT01", "GT04"], "mining_construction": ["GT03", "GT09"],
    "metals_machinery": ["GT10", "GT11", "GT12"], "chem_fuel": ["GT02", "GT07", "GT08"],
    "wood_paper_textile": ["GT05", "GT06"], "waste": ["GT14"], "parcels_grouped": ["GT15", "GT18"],
}
GOODS_LABEL = {
    "GT01": "Agriculture, forestry, fish", "GT02": "Coal, crude oil, gas", "GT03": "Ores, quarrying",
    "GT04": "Food, beverages", "GT05": "Textiles, leather", "GT06": "Wood, paper, print",
    "GT07": "Refined petroleum", "GT08": "Chemicals, plastics", "GT09": "Non-metallic minerals",
    "GT10": "Basic and fabricated metals", "GT11": "Machinery", "GT12": "Transport equipment",
    "GT13": "Furniture, other manufactures", "GT14": "Waste, secondary raw materials",
    "GT15": "Mail, parcels", "GT16": "Empty containers, pallets", "GT17": "Removals",
    "GT18": "Grouped goods", "GT19": "Unidentifiable goods", "GT20": "Other goods",
}
# 2017 PUF reports NAICS 3-digit; 2022 PUMS reports sectors only.
NAICS3_TO_SECTOR = {"212": "21", "423": "42", "424": "42", "454": "44-45", "493": "48-49", "511": "51",
                    "551": "55"}
SECTOR_LABEL = {"21": "Mining", "31-33": "Manufacturing", "42": "Wholesale", "44-45": "Retail (non-store)",
                "48-49": "Warehousing", "51": "Publishing", "55": "Corporate offices"}
NAICS3_LABEL = {"212": "Mining", "311": "Food", "312": "Beverages", "313": "Textile mills",
                "314": "Textile products", "315": "Apparel", "316": "Leather", "321": "Wood products",
                "322": "Paper", "323": "Printing", "324": "Petroleum and coal", "325": "Chemicals",
                "326": "Plastics and rubber", "327": "Non-metallic minerals", "331": "Primary metals",
                "332": "Fabricated metals", "333": "Machinery", "334": "Computers, electronics",
                "335": "Electrical equipment", "336": "Transportation equipment", "337": "Furniture",
                "339": "Miscellaneous manufacturing", "423": "Wholesale durable", "424": "Wholesale non-durable",
                "454": "Non-store retail", "493": "Warehousing", "511": "Publishing", "551": "Corporate offices"}
CFS_SHORT = ["<50", "50-100"]  # under 100 miles (160 km): within a day's return trip on one charge
FAF_DIST = {1: "<100", 2: "100-249", 3: "250-499", 4: "500-749", 5: "750-999", 6: "1000-1499",
            7: "1500-2000", 8: ">2000"}  # miles (FAF5_metadata.xlsx)
FAF_TRADE = {1: "Domestic", 2: "Import", 3: "Export"}


def eurostat(code: str, **filters) -> pd.DataFrame:
    d = pd.read_csv(EF / f"{code}.csv", low_memory=False)
    for k, v in filters.items():
        d = d[d[k] == v]
    d = d[d.geo.isin(EUROSTAT_GEO)]
    d["iso3"] = d.geo.map(EUROSTAT_GEO)
    return d.rename(columns={"TIME_PERIOD": "year", "OBS_VALUE": "value"})


def wide(d: pd.DataFrame, col: str) -> pd.DataFrame:
    w = d.pivot_table(index=["iso3", "year"], columns=col, values="value", aggfunc="first")
    w.columns.name = None
    return w


def eu_profile() -> pd.DataFrame:
    dc = eurostat("road_go_ta_dc", tra_type="TOTAL")
    vkm, tkm, ton = (wide(dc[dc.unit == u], "distance") for u in ("MIO_VKM", "MIO_TKM", "THS_T"))
    out = pd.DataFrame({"vkm_mio": vkm["TOTAL"], "tkm_mio": tkm["TOTAL"], "tonnes_ths": ton["TOTAL"]})
    for name, cls in (("short_lt150", SHORT), ("medium_150_499", MEDIUM), ("long_ge500", LONG)):
        out[f"vkm_share_{name}"] = vkm.reindex(columns=cls).sum(axis=1, min_count=1) / vkm["TOTAL"]
        out[f"tkm_share_{name}"] = tkm.reindex(columns=cls).sum(axis=1, min_count=1) / tkm["TOTAL"]
    out["avg_haul_km"] = tkm["TOTAL"] * 1e3 / ton["TOTAL"]

    own = wide(eurostat("road_go_ta_dc", distance="TOTAL", unit="MIO_TKM"), "tra_type")
    out["own_account_share_tkm"] = own["OWN"] / own["TOTAL"]

    op = eurostat("road_go_ta_tott", tra_type="TOTAL")
    t, v = wide(op[op.unit == "MIO_TKM"], "tra_oper"), wide(op[op.unit == "MIO_VKM"], "tra_oper")
    out["intl_share_tkm"] = t["LINTL"] / t["LOADED"]
    out["cabotage_crosstrade_share_tkm"] = (t["LINTL_CAB"].fillna(0) + t["LINTL_CTRD"].fillna(0)) / t["LOADED"]
    out["empty_share_vkm"] = v["EMPTY"] / v["TOTAL"]
    out["avg_load_t"] = t["LOADED"] / v["LOADED"]

    age = wide(eurostat("road_go_ta_agev", unit="MIO_VKM"), "age")
    known = age.reindex(columns=list(AGE_MID)).sum(axis=1, min_count=1)
    out["vkm_share_age_ge10"] = age.reindex(columns=["Y10-14", "Y_GE15"]).sum(axis=1, min_count=1) / known
    out["vkm_mean_age"] = sum(age.get(k, 0).fillna(0) * m for k, m in AGE_MID.items()) / known

    g = wide(eurostat("road_go_ta_tg", tra_type="TOTAL", unit="MIO_TKM"), "nst07")
    for name, codes in GOODS.items():
        out[f"goods_share_{name}"] = g.reindex(columns=codes).sum(axis=1, min_count=1) / g["TOTAL"]

    out = out.reset_index()
    reg = pd.read_csv(PROC_DIR / "eurostat_new_registrations_fuel.csv")
    reg = reg[reg.segment.isin(["Lorries >3.5 t", "Road tractors"])]
    reg = reg.pivot_table(index=["iso3", "year"], columns="segment", values=["total", "zev", "zev_share"])
    reg.columns = [f"{v}_{'lorries' if s.startswith('Lorries') else 'tractors'}" for v, s in reg.columns]
    reg = reg.rename(columns=lambda c: c.replace("total_", "reg_").replace("zev_lorries", "reg_zev_lorries")
                     .replace("zev_tractors", "reg_zev_tractors").replace("zev_share_", "zev_share_"))
    reg = reg.reset_index()
    both = reg[["reg_lorries", "reg_tractors"]].sum(axis=1, min_count=1)
    reg["zev_share_heavy"] = reg[["reg_zev_lorries", "reg_zev_tractors"]].sum(axis=1, min_count=1) / both
    out = out.merge(reg, on=["iso3", "year"], how="left")
    out["eu27_member"] = out.iso3.isin(EU27).astype(int)
    return out.sort_values(["iso3", "year"])


def eu_quarterly() -> pd.DataFrame:
    q = eurostat("road_go_tq_tott", tra_type="TOTAL", unit="MIO_TKM")
    q = q[q.tra_oper.isin(["TOTAL", "LINTL", "LNAT"])]
    q = q.pivot_table(index=["iso3", "year"], columns="tra_oper", values="value", aggfunc="first").reset_index()
    q.columns.name = None
    q = q.rename(columns={"year": "quarter", "TOTAL": "tkm_mio", "LINTL": "tkm_intl_mio", "LNAT": "tkm_nat_mio"})
    q["quarter"] = pd.PeriodIndex(q["quarter"].str.replace("-", ""), freq="Q").astype(str)
    q = q.sort_values(["iso3", "quarter"])
    q["tkm_yoy"] = q.groupby("iso3")["tkm_mio"].pct_change(4, fill_method=None)
    return q


def eu_goods_distance() -> pd.DataFrame:
    d = eurostat("road_go_ta_dctg", unit="MIO_TKM")
    d = d.pivot_table(index=["iso3", "year", "nst07"], columns="distance", values="value", aggfunc="first")
    d.columns.name = None
    out = pd.DataFrame({"tkm_mio": d["TOTAL"]})
    out["tkm_share_lt150"] = d.reindex(columns=SHORT).sum(axis=1, min_count=1) / d["TOTAL"]
    out["tkm_share_lt300"] = d.reindex(columns=SHORT + ["KM150-299"]).sum(axis=1, min_count=1) / d["TOTAL"]
    out = out.reset_index()
    out["goods"] = out.nst07.map(GOODS_LABEL).fillna(out.nst07)
    return out


def us_cfs() -> pd.DataFrame:
    frames = []
    for year, measure in ((2017, "routed"), (2022, "great-circle")):
        c = pd.read_csv(RAW_DIR / "cfs" / f"cfs_{year}_mode_naics_sctg_distance.csv", dtype={"naics": str})
        c = c[c["mode"] != 0]  # suppressed mode
        if year == 2017:
            c["sector"] = c.naics.map(NAICS3_TO_SECTOR).fillna("31-33")
            levels = (("sector", "sector"), ("naics3", "naics"))
        else:
            c["sector"] = c.naics
            levels = (("sector", "sector"),)
        for level, col in levels:
            g = c.groupby([col, "truck", "mode_label", "dist_band"], observed=True)[["w_tons", "w_tonmiles"]].sum()
            g = g.reset_index().rename(columns={col: "industry"})
            all_tons = g.groupby("industry").w_tons.sum()
            tr = g[g.truck == 1]
            truck_tons = tr.groupby("industry").w_tons.sum()
            res = pd.DataFrame({
                "tons_all_modes_m": all_tons / 1e6,
                "truck_tons_m": truck_tons / 1e6,
                "truck_tonmiles_bn": tr.groupby("industry").w_tonmiles.sum() / 1e9,
                "truck_share_tons": truck_tons / all_tons,
                "truck_tons_share_lt100mi": tr[tr.dist_band.isin(CFS_SHORT)].groupby("industry").w_tons.sum() / truck_tons,
                "truck_tons_share_lt250mi": tr[tr.dist_band.isin(CFS_SHORT + ["100-150", "150-250"])]
                .groupby("industry").w_tons.sum() / truck_tons,
                "truck_tonmiles_share_lt250mi": tr[tr.dist_band.isin(CFS_SHORT + ["100-150", "150-250"])]
                .groupby("industry").w_tonmiles.sum() / tr.groupby("industry").w_tonmiles.sum(),
                "private_share_truck_tons": tr[tr.mode_label == "Company-owned truck"].groupby("industry").w_tons.sum() / truck_tons,
            }).reset_index()
            res["level"], res["year"], res["distance_measure"] = level, year, measure
            res["label"] = res.industry.map(SECTOR_LABEL if level == "sector" else NAICS3_LABEL)
            frames.append(res)
    return pd.concat(frames, ignore_index=True)


def us_faf() -> pd.DataFrame:
    f = pd.read_csv(RAW_DIR / "faf5" / "faf5_mode_sctg_distance_2018_2024.csv")
    keys = ["year", "trade_type", "dist_band"]
    allm = f.groupby(keys)[["tons", "tmiles", "value"]].sum()
    truck = f[f.dms_mode == 1].groupby(keys)[["tons", "tmiles", "value"]].sum()
    out = truck.add_prefix("truck_").join(allm.add_prefix("all_")).reset_index()
    out = out.rename(columns=lambda c: c.replace("tons", "kt").replace("tmiles", "mtonmiles").replace("value", "usd_m"))
    out["truck_share_kt"] = out.truck_kt / out.all_kt
    out["truck_share_mtonmiles"] = out.truck_mtonmiles / out.all_mtonmiles
    out["dist_band"] = out.dist_band.map(FAF_DIST)
    out["trade_type"] = out.trade_type.map(FAF_TRADE)
    return out


def de_toll() -> pd.DataFrame:
    d = pd.read_excel(RAW_DIR / "germany_toll_index" / "lkw_maut_fahrleistungsindex.xlsx", sheet_name="csv-42191-b01")
    d.columns = ["stat", "area", "date", "week", "weekday", "adjustment", "index"]
    d["date"] = pd.to_datetime(d["date"])
    d["series"] = np.where(d.adjustment.str.contains("KSB"), "index_ksb", "index_raw")
    d["index"] = pd.to_numeric(d["index"], errors="coerce")
    m = d.groupby([d.date.dt.to_period("M").astype(str).rename("month"), "series"])["index"].mean().unstack()
    m.columns.name = None
    m = m.reset_index()
    m["ksb_yoy"] = m["index_ksb"].pct_change(12, fill_method=None)
    return m


def main() -> None:
    p = eu_profile()
    p.to_csv(PROC_DIR / "eu_freight_profile_country_year.csv", index=False)
    q = eu_quarterly()
    q.to_csv(PROC_DIR / "eu_freight_activity_country_quarter.csv", index=False)
    g = eu_goods_distance()
    g.to_csv(PROC_DIR / "eu_freight_goods_distance.csv", index=False)
    u = us_cfs()
    u.to_csv(PROC_DIR / "us_cfs_truck_profile.csv", index=False)
    f = us_faf()
    f.to_csv(PROC_DIR / "us_faf_truck_distance_year.csv", index=False)
    t = de_toll()
    t.to_csv(PROC_DIR / "de_toll_mileage_monthly.csv", index=False)
    last = p[(p.year == 2024) & p.eu27_member.eq(1)]
    print(f"EU profile: {p.iso3.nunique()} countries, {p.year.min()}-{p.year.max()}; "
          f"2024 short-haul vkm share (median) {last.vkm_share_short_lt150.median():.2f}, "
          f"international tkm share {last.intl_share_tkm.median():.2f}")
    print(f"EU quarterly: {q.iso3.nunique()} countries, {q.quarter.min()}-{q.quarter.max()}")
    f24 = f[f.year == 2024].groupby("dist_band", sort=False)[["truck_kt", "truck_mtonmiles"]].sum()
    print(f"US CFS: {len(u)} industry-year rows; toll index {t.month.min()}-{t.month.max()}")
    print(f"FAF 2024 truck tons under 250 miles: {f24.loc[['<100', '100-249'], 'truck_kt'].sum() / f24.truck_kt.sum():.2f}; "
          f"ton-miles {f24.loc[['<100', '100-249'], 'truck_mtonmiles'].sum() / f24.truck_mtonmiles.sum():.2f}")


if __name__ == "__main__":
    main()
