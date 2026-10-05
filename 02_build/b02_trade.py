"""Bilateral vehicle trade panels from CEPII BACI (values in USD, quantities in tonnes).

Electric goods vehicles (870460) exist only from HS 2022, so they come from the HS22
release (2022-2024). Electric buses (870240), electric road tractors (870124) and
electric cars (870380) are consistent in the HS17 release (2017-2024).

Outputs (03_data/02_processed/):
  trade_flows_hs6.csv.gz     exporter x importer x year x HS6 with category and unit value
  trade_exporter_year.csv    exports by exporter x category x year (+ world share)
  trade_importer_year.csv    imports by importer x category x year (+ share from China)
"""
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from config import PROC_DIR, RAW_DIR  # noqa: E402
from countries import iso3_from_m49  # noqa: E402

CATEGORY = {
    "870460": "e_truck", "870240": "e_bus", "870124": "e_tractor", "870380": "e_car",
    "870421": "diesel_truck_le5t", "870422": "diesel_truck_5_20t", "870423": "diesel_truck_gt20t",
    "870441": "hybrid_diesel_truck_le5t", "870442": "hybrid_diesel_truck_5_20t",
    "870443": "hybrid_diesel_truck_gt20t", "870451": "hybrid_petrol_truck_le5t",
    "870452": "hybrid_petrol_truck_gt5t", "870431": "petrol_truck_le5t", "870432": "petrol_truck_gt5t",
    "870490": "other_truck", "870410": "dumper_offroad",
    "870121": "diesel_tractor", "870122": "hybrid_diesel_tractor", "870123": "hybrid_petrol_tractor",
    "870129": "other_tractor", "870210": "diesel_bus", "870220": "hybrid_diesel_bus",
    "870230": "hybrid_petrol_bus", "870290": "other_bus", "870600": "chassis_with_engine",
    "840820": "diesel_engine_vehicle", "850760": "li_ion_battery", "850790": "battery_parts",
}


def classify(hs6: str) -> str:
    if hs6 in CATEGORY:
        return CATEGORY[hs6]
    if hs6.startswith("8703"):
        return "car_other"
    if hs6.startswith("8705"):
        return "special_purpose_vehicle"
    if hs6.startswith("8707"):
        return "bodies_cabs"
    if hs6.startswith("8708"):
        return "vehicle_parts"
    if hs6.startswith("8716"):
        return "trailers"
    if hs6.startswith("8701"):
        return "tractor_other"
    return "other"


def load(hs: str, categories: set[str] | None = None) -> pd.DataFrame:
    d = pd.read_csv(RAW_DIR / "baci" / f"baci_{hs}_V202601_vehicles.csv.gz", dtype={"hs6": str})
    d["hs6"] = d["hs6"].str.zfill(6)
    d["category"] = d["hs6"].map(classify)
    if categories:
        d = d[d["category"].isin(categories)]
    d["exporter_iso3"] = d["exporter"].map(iso3_from_m49)
    d["importer_iso3"] = d["importer"].map(iso3_from_m49)
    d["source"] = f"BACI_{hs.upper()}"
    return d


def main() -> None:
    hs22 = load("hs22")
    hs17_only = {"e_bus", "e_tractor", "e_car", "diesel_bus", "diesel_tractor", "hybrid_diesel_bus",
                 "chassis_with_engine", "diesel_truck_le5t", "diesel_truck_5_20t",
                 "diesel_truck_gt20t", "li_ion_battery", "trailers", "vehicle_parts", "bodies_cabs",
                 "car_other", "diesel_engine_vehicle", "other_truck"}
    hs17 = load("hs17", hs17_only)
    hs17 = hs17[hs17["year"] < 2022]  # 2022+ taken from the HS22 release
    flows = pd.concat([hs17, hs22], ignore_index=True)
    flows["value_usd"] = flows["value_kusd"] * 1000
    flows["uv_usd_per_kg"] = flows["value_usd"] / (flows["qty_tonnes"] * 1000)
    keep = ["year", "exporter_iso3", "importer_iso3", "hs6", "category", "value_usd", "qty_tonnes",
            "uv_usd_per_kg", "source"]
    flows = flows[keep]
    flows.to_csv(PROC_DIR / "trade_flows_hs6.csv.gz", index=False, compression="gzip")

    exp = (flows.groupby(["exporter_iso3", "category", "year"], as_index=False)
           [["value_usd", "qty_tonnes"]].sum())
    world = exp.groupby(["category", "year"])["value_usd"].transform("sum")
    exp["world_export_share"] = exp["value_usd"] / world
    exp.to_csv(PROC_DIR / "trade_exporter_year.csv", index=False)

    imp = (flows.groupby(["importer_iso3", "category", "year"], as_index=False)
           [["value_usd", "qty_tonnes"]].sum())
    from_chn = (flows[flows["exporter_iso3"] == "CHN"]
                .groupby(["importer_iso3", "category", "year"])["value_usd"].sum()
                .rename("value_from_china_usd"))
    imp = imp.merge(from_chn, on=["importer_iso3", "category", "year"], how="left")
    imp["value_from_china_usd"] = imp["value_from_china_usd"].fillna(0)
    imp["china_share"] = imp["value_from_china_usd"] / imp["value_usd"]
    imp.to_csv(PROC_DIR / "trade_importer_year.csv", index=False)

    s = exp[exp.category.isin(["e_truck", "e_bus", "e_car"])].groupby(["category", "year"])["value_usd"].sum() / 1e9
    print("world exports, USD bn:\n", s.unstack(0).round(2))
    print(f"flows: {len(flows):,} rows; missing ISO3 exporters: "
          f"{flows.exporter_iso3.isna().mean():.3%}")


if __name__ == "__main__":
    main()
