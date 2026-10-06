"""EU heavy-duty vehicle CO2 monitoring data (EEA, Regulation (EU) 2018/956 and 2019/1242). No key.

The 2024-2025 release is cumulative: member-state registrations from July 2021 to June 2025
(reporting periods run July-June; earlier releases are subsets). Two vehicle-level files are
aggregated; VINs are hashed by the EEA and nothing identifying is kept:

1. Member-state registrations: every new truck, bus and trailer registered in the EU (+ IS, NO),
   with make, category (N2, N3, M2, M3, O), fuel, electric/hybrid flags, permissible mass and
   registration date -> counts by country x month x category x mass class x powertrain x make.
2. Manufacturer VECTO records for certified trucks: vehicle sub-group (duty cycle: 4-RD regional
   delivery, 5-LH long haul, ...), zero-emission flag, sleeper cab, axle configuration, rated
   power and battery capacity, linked to the registration country and month through the hashed
   VIN -> counts and sums by period x country x sub-group x powertrain x make.

The ~3 GB of zipped CSVs are cached outside Dropbox.
Source: https://sdi.eea.europa.eu/datastore/public/eea_t_co2-emission-hdv_p_2024-2025_v01_r00
Output: 03_data/01_raw/eea_hdv/eea_hdv_registrations.csv, eea_hdv_vecto_groups.csv,
        eea_hdv_mass_distribution.csv (exact permissible mass, for bunching at weight thresholds)
Run with --mass to rebuild only the mass distribution.
"""
import base64
import sys
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from config import CACHE_DIR, RAW_DIR  # noqa: E402
from helpers import download, log_download  # noqa: E402

BASE = "https://sdi.eea.europa.eu/datashare/public.php/webdav/eea_t_co2-emission-hdv_p_{y}-{y1}_v01_r00/hdv_{y}_{f}.zip"
AUTH = {"Authorization": "Basic " + base64.b64encode(b"sptXqwkQr5g7Bp5:").decode()}  # public share token
RELEASE = 2024  # cumulative release
OUT = RAW_DIR / "eea_hdv"
KEYS = ["period", "ms", "make", "category", "subgroup", "powertrain", "sleeper_cab", "axles"]


def fetch(y: int, f: str) -> Path:
    return download(BASE.format(y=y, y1=y + 1, f=f), CACHE_DIR / "eea_hdv" / f"hdv_{y}_{f}.zip",
                    source="EEA HDV CO2 monitoring", headers=AUTH, timeout=3600, note="cached outside Dropbox")


def chunks(path: Path, cols: list[str]):
    with zipfile.ZipFile(path) as z:
        name = z.namelist()[0]
        sep = ";" if z.open(name).readline().decode("utf-8-sig").count(";") > 5 else ","
        with z.open(name) as fh:
            yield from pd.read_csv(fh, sep=sep, usecols=lambda c: c.lstrip("﻿") in cols, dtype=str,
                                   encoding="utf-8-sig", chunksize=500_000, low_memory=False)


def truthy(s: pd.Series) -> pd.Series:
    return s.fillna("").str.strip().str.lower().isin({"1", "true", "yes", "y"})


def powertrain(electric, hybrid, fuel) -> pd.Series:
    fuel = fuel.fillna("").str.lower()
    out = np.select([electric, fuel.str.contains("hydrogen|h2"), hybrid,
                     fuel.str.contains("lng|cng|gas|methane"), fuel.str.contains("diesel|ci"), fuel.eq("")],
                    ["Battery electric", "Hydrogen", "Hybrid", "Gas", "Diesel", "Unknown"], "Other")
    return pd.Series(out, index=fuel.index)


def mass_class(kg: pd.Series) -> pd.Series:
    return pd.cut(kg, [0, 3500, 7500, 16000, 26000, 1e6], labels=["<=3.5t", "3.5-7.5t", "7.5-16t", "16-26t", ">26t"])


def period_of(month: pd.Series) -> pd.Series:
    """Reporting period (July-June) named by its first year."""
    dt = pd.to_datetime(month, format="%Y-%m", errors="coerce")
    return (dt.dt.year - (dt.dt.month < 7)).astype("Int64")


def registrations() -> tuple[pd.DataFrame, pd.DataFrame]:
    cols = ["vehicle_id", "MS", "Mk", "Electric", "Hybrid", "FT", "VehicleCategoryCode", "TechnPermMaxLadenMass",
            "RegistrationDateClean", "SpecificCO2Emissions"]
    parts = []
    for c in chunks(fetch(RELEASE, "memberstate_vehicle"), cols):
        c.columns = [x.lstrip("\ufeff") for x in c.columns]
        kg = pd.to_numeric(c.TechnPermMaxLadenMass, errors="coerce")
        kg = kg.where(kg > 100, kg * 1000)  # a few records report tonnes
        parts.append(pd.DataFrame({
            "vehicle_id": c.vehicle_id, "ms": c.MS.str.strip(), "category": c.VehicleCategoryCode.str.strip(),
            "make": c.Mk.str.strip().str.upper(),
            "month": pd.to_datetime(c.RegistrationDateClean, errors="coerce").dt.strftime("%Y-%m"),
            "mass_class": mass_class(kg).astype(str),
            "powertrain": powertrain(c.Electric.str.strip().str.lower().eq("yes"),
                                     c.Hybrid.str.strip().str.lower().eq("yes"), c.FT),
            "co2": pd.to_numeric(c.SpecificCO2Emissions, errors="coerce")}))
    d = pd.concat(parts, ignore_index=True).drop_duplicates("vehicle_id", keep="last")
    d["period"] = period_of(d.month)
    keys = ["period", "ms", "month", "category", "mass_class", "powertrain", "make"]
    agg = (d.groupby(keys, dropna=False).agg(vehicles=("co2", "size"), co2_n=("co2", "count"), co2_sum=("co2", "sum"))
           .reset_index())
    return agg, d[["vehicle_id", "ms", "month", "period"]]


def vecto(ids: pd.DataFrame) -> pd.DataFrame:
    bat = {}
    for c in chunks(fetch(RELEASE, "battery"), ["Vehicle_id", "TotalStorageCapacity"]):
        c.columns = [x.lstrip("\ufeff") for x in c.columns]
        s = pd.to_numeric(c.TotalStorageCapacity, errors="coerce").groupby(c.Vehicle_id).sum()
        bat.update(s.to_dict())
    cols = ["Vehicle_id", "Make", "VehicleCategory", "VehicleGroupCO2", "VehicleGroup", "ZeroEmissionVehicle",
            "HybridElectricHDV", "SleeperCab", "AxleConfiguration", "Engine_RatedPower",
            "SumNetPower", "TechnicalPermissibleMaximumLadenMass", "TechnicalPermissibleMaximumLadenMass_unit"]
    reg = ids.set_index("vehicle_id")
    seen: set[str] = set()
    out = []
    for c in chunks(fetch(RELEASE, "vehicle"), cols):
        c.columns = [x.lstrip("\ufeff") for x in c.columns]
        c = c.drop_duplicates("Vehicle_id")
        c = c[~c.Vehicle_id.isin(seen)]
        seen.update(c.Vehicle_id)
        zev = truthy(c.ZeroEmissionVehicle)
        mass = pd.to_numeric(c.TechnicalPermissibleMaximumLadenMass, errors="coerce")
        mass = mass.where(c.TechnicalPermissibleMaximumLadenMass_unit.fillna("kg").str.strip() != "t", mass * 1000)
        power = pd.to_numeric(c.Engine_RatedPower, errors="coerce").fillna(pd.to_numeric(c.SumNetPower, errors="coerce"))
        grp = c.VehicleGroupCO2.fillna("").str.strip()
        grp = grp.where(~grp.isin({"", "N/A", "NULL"}), "group " + c.VehicleGroup.fillna("?").str.strip())
        r = reg.reindex(c.Vehicle_id)
        d = pd.DataFrame({"period": r.period.values, "ms": r.ms.values, "make": c.Make.str.strip().str.upper(),
                          "category": c.VehicleCategory, "subgroup": grp,
                          # fuel type is in a separate table from VECTO 0.10 on; ZEV vs hybrid vs combustion suffices
                          "powertrain": np.select([zev, truthy(c.HybridElectricHDV)], ["Zero emission", "Hybrid"],
                                                  "Combustion"),
                          "sleeper_cab": truthy(c.SleeperCab).astype(int), "axles": c.AxleConfiguration,
                          "mass_kg": mass, "power_kw": power,
                          "battery_kwh": c.Vehicle_id.map(bat)})
        out.append(d.groupby(KEYS, dropna=False)
                   .agg(vehicles=("mass_kg", "size"), mass_kg_sum=("mass_kg", "sum"), power_kw_sum=("power_kw", "sum"),
                        battery_n=("battery_kwh", "count"), battery_kwh_sum=("battery_kwh", "sum")).reset_index())
    return pd.concat(out).groupby(KEYS, dropna=False).sum().reset_index()


def mass_distribution() -> pd.DataFrame:
    """Counts by period x category x powertrain x exact permissible mass (kg), trucks and vans."""
    cols = ["vehicle_id", "Electric", "Hybrid", "FT", "VehicleCategoryCode", "TechnPermMaxLadenMass",
            "RegistrationDateClean"]
    parts = []
    for c in chunks(fetch(RELEASE, "memberstate_vehicle"), cols):
        c.columns = [x.lstrip("\ufeff") for x in c.columns]
        cat = c.VehicleCategoryCode.fillna("").str.upper().str[:2]
        c = c[cat.isin(["N1", "N2", "N3"])]
        kg = pd.to_numeric(c.TechnPermMaxLadenMass, errors="coerce")
        parts.append(pd.DataFrame({
            "vehicle_id": c.vehicle_id, "category": cat[c.index], "mass_kg": kg.where(kg > 100, kg * 1000).round(),
            "month": pd.to_datetime(c.RegistrationDateClean, errors="coerce").dt.strftime("%Y-%m"),
            "powertrain": powertrain(c.Electric.str.strip().str.lower().eq("yes"),
                                     c.Hybrid.str.strip().str.lower().eq("yes"), c.FT)}))
    d = pd.concat(parts, ignore_index=True).drop_duplicates("vehicle_id", keep="last")
    d["period"] = period_of(d.month)
    return d.groupby(["period", "category", "powertrain", "mass_kg"]).size().rename("vehicles").reset_index()


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    m = mass_distribution()
    m.to_csv(OUT / "eea_hdv_mass_distribution.csv", index=False)
    log_download("EEA HDV CO2 monitoring (mass distribution)", BASE, OUT / "eea_hdv_mass_distribution.csv",
                 "period x category x powertrain x permissible mass (kg)")
    if "--mass" in sys.argv:
        return
    reg, ids = registrations()
    reg.to_csv(OUT / "eea_hdv_registrations.csv", index=False)
    log_download("EEA HDV CO2 monitoring (aggregated registrations)", BASE, OUT / "eea_hdv_registrations.csv",
                 "member state x month x category x mass class x powertrain x make, Jul 2021-Jun 2025")
    vec = vecto(ids)
    vec.to_csv(OUT / "eea_hdv_vecto_groups.csv", index=False)
    log_download("EEA HDV CO2 monitoring (aggregated VECTO records)", BASE, OUT / "eea_hdv_vecto_groups.csv",
                 "period x country x sub-group x powertrain x make, with mass, power and battery capacity sums")
    t = reg[reg.category.isin(["N2", "N3"])].pivot_table(index="period", columns="powertrain", values="vehicles",
                                                         aggfunc="sum")
    print(t.to_string())
    print(vec.groupby(["period", "powertrain"], dropna=False).vehicles.sum().unstack().to_string())


if __name__ == "__main__":
    main()
