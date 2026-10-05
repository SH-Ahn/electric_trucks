"""Model-level registration panels from national registries (free analogues of the
licensed sales data): Netherlands (RDW, vehicle-level) and United Kingdom (DfT).

Outputs (03_data/02_processed/):
  nl_registrations_model_quarter.csv  quarter x segment x make x model x powertrain x GVW band x new/used
  uk_registrations_model_quarter.csv  quarter x body type x make x model x fuel (new registrations)
  uk_hgv_new_by_gvw_fuel.csv          year x GVW band x fuel (HGVs >3.5 t first used that year)
  oem_groups.csv                      make -> OEM group, HQ region, incumbent flag (manual mapping)

NL caveats: the open register keeps vehicles currently registered plus recent exports,
so cohorts before ~2018 are under-counted (survivorship). A vehicle is "new" if its
first registration in the Netherlands is within 90 days of its first admission anywhere.
"""
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from config import PROC_DIR, RAW_DIR  # noqa: E402

# make -> (OEM group, HQ region, incumbent in European diesel trucks/buses before 2018)
OEM = {
    "DAF": ("PACCAR", "US/EU", 1), "PETERBILT": ("PACCAR", "US", 1), "KENWORTH": ("PACCAR", "US", 1),
    "VOLVO": ("Volvo Group", "Europe", 1), "RENAULT": ("Volvo Group", "Europe", 1),
    "RENAULT TRUCKS": ("Volvo Group", "Europe", 1), "MACK": ("Volvo Group", "Europe", 1),
    "SCANIA": ("Traton", "Europe", 1), "MAN": ("Traton", "Europe", 1), "VOLKSWAGEN": ("Traton", "Europe", 1),
    "INTERNATIONAL": ("Traton", "Europe", 1),
    "MERCEDES-BENZ": ("Daimler Truck", "Europe", 1), "FUSO": ("Daimler Truck", "Europe", 1),
    "SETRA": ("Daimler Truck", "Europe", 1), "FREIGHTLINER": ("Daimler Truck", "Europe", 1),
    "UNIMOG": ("Daimler Truck", "Europe", 1),
    "IVECO": ("Iveco Group", "Europe", 1), "IVECO BUS": ("Iveco Group", "Europe", 1),
    "MAGIRUS-DEUTZ": ("Iveco Group", "Europe", 1),
    "FORD": ("Ford", "US", 1), "ISUZU": ("Isuzu", "Japan", 1), "HINO": ("Toyota/Hino", "Japan", 1),
    "VDL": ("VDL", "Europe", 1), "VDL BERKHOF": ("VDL", "Europe", 1), "VAN HOOL": ("Van Hool", "Europe", 1),
    "SOLARIS": ("CAF/Solaris", "Europe", 1), "IRIZAR": ("Irizar", "Europe", 1),
    "BYD": ("BYD", "China", 0), "YUTONG": ("Yutong", "China", 0), "HIGER": ("Higer", "China", 0),
    "KING LONG": ("King Long", "China", 0), "GOLDEN DRAGON": ("Golden Dragon", "China", 0),
    "ZHONGTONG": ("Zhongtong", "China", 0), "MAXUS": ("SAIC", "China", 0), "SANY": ("Sany", "China", 0),
    "WINDROSE": ("Windrose", "China", 0), "XCMG": ("XCMG", "China", 0), "FOTON": ("Foton", "China", 0),
    "EBUSCO": ("Ebusco", "Europe", 0), "TESLA": ("Tesla", "US", 0), "QUANTRON": ("Quantron", "Europe", 0),
    "EMOSS": ("Emoss", "Europe", 0), "VOLTA": ("Volta", "Europe", 0), "NIKOLA": ("Nikola", "US", 0),
    "HYZON": ("Hyzon", "US", 0), "DAIMLER": ("Daimler Truck", "Europe", 1),
}


def nl_powertrain(fuels: set[str]) -> str:
    if "Waterstof" in fuels:
        return "Fuel cell / hydrogen"
    if "Elektriciteit" in fuels:
        return "Battery electric" if fuels <= {"Elektriciteit"} else "Hybrid / PHEV"
    if fuels & {"LNG", "CNG"}:
        return "Gas"
    if "Diesel" in fuels:
        return "Diesel"
    if fuels & {"Benzine", "LPG", "Alcohol"}:
        return "Petrol / other"
    return "Unknown"


def gvw_band(kg: float) -> str:
    if pd.isna(kg):
        return "unknown"
    t = kg / 1000
    for hi, lab in ((7.5, "3.5-7.5 t"), (12, "7.5-12 t"), (16, "12-16 t"), (26, "16-26 t")):
        if t <= hi:
            return lab
    return ">26 t"


def build_nl() -> pd.DataFrame:
    v = pd.read_csv(RAW_DIR / "rdw_netherlands" / "rdw_vehicles_n2n3m2m3.csv.gz", dtype=str)
    f = pd.read_csv(RAW_DIR / "rdw_netherlands" / "rdw_fuel_n2n3m2m3.csv.gz", dtype=str,
                    usecols=["kenteken", "brandstof_omschrijving"])
    pt = f.groupby("kenteken")["brandstof_omschrijving"].agg(lambda s: set(s.dropna())).map(nl_powertrain)
    v["powertrain"] = v["kenteken"].map(pt).fillna("No fuel record")
    v["first_any"] = pd.to_datetime(v["datum_eerste_toelating"], format="%Y%m%d", errors="coerce")
    v["first_nl"] = pd.to_datetime(v["datum_eerste_tenaamstelling_in_nederland"], format="%Y%m%d", errors="coerce")
    v = v[v["first_nl"] >= "2010-01-01"]
    v["new_vehicle"] = ((v["first_nl"] - v["first_any"]).dt.days <= 90).astype(int)
    v["quarter"] = v["first_nl"].dt.to_period("Q").astype(str)
    v["make"] = v["merk"].str.upper().str.strip().replace({"MERCEDES BENZ": "MERCEDES-BENZ"})
    v["model"] = v["handelsbenaming"].str.upper().str.strip()
    v["gvw_kg"] = pd.to_numeric(v["toegestane_maximum_massa_voertuig"], errors="coerce")
    v["gvw_band"] = v["gvw_kg"].map(gvw_band)
    cat = v["europese_voertuigcategorie"]
    v["segment"] = "Rigid truck N2"
    v.loc[cat == "N3", "segment"] = "Rigid truck N3"
    v.loc[(cat == "N3") & (v["inrichting"] == "opleggertrekker"), "segment"] = "Tractor N3"
    v.loc[(cat == "N2") & (v["inrichting"] == "opleggertrekker"), "segment"] = "Tractor N2"
    v.loc[cat.isin(["M2", "M3"]), "segment"] = "Bus/coach " + cat
    v["exported"] = (v["export_indicator"] == "Ja").astype(int)
    g = (v.groupby(["quarter", "segment", "make", "model", "powertrain", "gvw_band", "new_vehicle"],
                   dropna=False).agg(registrations=("kenteken", "size"), exported=("exported", "sum"))
         .reset_index())
    g["country"] = "NLD"
    return g


def build_uk() -> tuple[pd.DataFrame, pd.DataFrame]:
    d = pd.read_csv(RAW_DIR / "dft_uk" / "df_VEH0160_UK.csv")
    d = d[d["BodyType"].isin(["Heavy goods vehicles", "Buses and coaches", "Light goods vehicles"])]
    qcols = [c for c in d.columns if c[:4].isdigit()]
    d[qcols] = d[qcols].apply(pd.to_numeric, errors="coerce")
    long = d.melt(id_vars=["BodyType", "Make", "GenModel", "Model", "Fuel"], value_vars=qcols,
                  var_name="quarter", value_name="registrations")
    long = long[long["registrations"] > 0]
    long["quarter"] = long["quarter"].str.replace(" ", "")
    long["country"] = "GBR"
    w = pd.read_csv(RAW_DIR / "dft_uk" / "df_VEH0520.csv", low_memory=False)
    w = w[w["Geography"] == "United Kingdom"]
    ycols = [c for c in w.columns if c.isdigit()]
    w[ycols] = w[ycols].apply(pd.to_numeric, errors="coerce")
    w["YearFirstUsed"] = pd.to_numeric(w["YearFirstUsed"], errors="coerce")
    rows = []
    for y in ycols:
        sub = w[w["YearFirstUsed"] == int(y)]
        rows.append(sub.groupby(["MaximumGrossWeightBand", "Fuel"])[y].sum().rename("vehicles")
                    .reset_index().assign(year=int(y)))
    hgv = pd.concat(rows, ignore_index=True)
    return long, hgv


def main() -> None:
    nl = build_nl()
    nl.to_csv(PROC_DIR / "nl_registrations_model_quarter.csv", index=False)
    uk, hgv = build_uk()
    uk.to_csv(PROC_DIR / "uk_registrations_model_quarter.csv", index=False)
    hgv.to_csv(PROC_DIR / "uk_hgv_new_by_gvw_fuel.csv", index=False)
    pd.DataFrame([(k, *v) for k, v in OEM.items()],
                 columns=["make", "oem_group", "hq_region", "incumbent"]).to_csv(PROC_DIR / "oem_groups.csv", index=False)
    new = nl[nl.new_vehicle == 1]
    tab = new.assign(year=new.quarter.str[:4]).pivot_table(index="year", columns="powertrain",
                                                           values="registrations", aggfunc="sum").fillna(0)
    print("NL new N2/N3/M2/M3 registrations by powertrain:\n", tab.loc["2018":].astype(int))
    u = uk[uk.BodyType == "Heavy goods vehicles"].assign(year=lambda x: x.quarter.str[:4])
    print("UK new HGV registrations by fuel:\n",
          u.pivot_table(index="year", columns="Fuel", values="registrations", aggfunc="sum").fillna(0).astype(int).tail(8))


if __name__ == "__main__":
    main()
