"""Tidy panels for infrastructure, fleet structure, fuel taxation and market size.

1. US alternative-fuel stations that accept medium or heavy vehicles (AFDC) by opening year,
   state, fuel group and maximum vehicle class, with connector counts for electric sites.
2. US motor-carrier fleet structure (FMCSA census): carriers, power units, drivers, short-haul
   share and miles per power unit by fleet-size bin, for-hire vs private.
3. OECD effective carbon rates on road diesel and gasoline (EUR per tonne of CO2, 2018, 2021,
   2023): fuel excise, carbon tax, ETS, total, and net of fossil-fuel subsidies.
4. ITF first registrations of goods road motor vehicles by country and year (annual series,
   or the sum of monthly/quarterly series when no annual series exists).

Output (03_data/02_processed/): us_hd_stations.csv, us_fleet_size_bins.csv,
        carbon_rates_road_fuels.csv, itf_goods_vehicle_registrations.csv
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from config import PROC_DIR, RAW_DIR  # noqa: E402

FUEL_GROUP = {"ELEC": "Electric", "HY": "Hydrogen", "CNG": "Natural gas", "LNG": "Natural gas",
              "RD": "Renewable diesel, biodiesel", "BD": "Renewable diesel, biodiesel", "LPG": "Propane",
              "E85": "Ethanol (E85)"}
BINS = [0, 1, 5, 10, 50, 100, 1000, np.inf]
BIN_LABELS = ["1", "2-5", "6-10", "11-50", "51-100", "101-1,000", ">1,000"]


def stations() -> pd.DataFrame:
    a = pd.read_csv(RAW_DIR / "afdc" / "afdc_stations_md_hd.csv", low_memory=False)
    a["fuel_group"] = a.fuel_type_code.map(FUEL_GROUP)
    a["open_year"] = pd.to_datetime(a.open_date, errors="coerce").dt.year
    conn = a.ev_connector_types.fillna("")
    a["ccs"] = conn.str.contains("J1772COMBO").astype(int)
    a["mcs"] = conn.str.contains("J3271").astype(int)
    a["nacs"] = conn.str.contains("TESLA|J3400", regex=True).astype(int)
    a["level2_only"] = ((a.fuel_type_code == "ELEC") & ~conn.str.contains("COMBO|CHADEMO|TESLA|J3271|J3400",
                                                                            regex=True)).astype(int)
    a["stations"] = 1
    keys = ["open_year", "state", "fuel_group", "maximum_vehicle_class", "access_code", "status_code"]
    return (a.groupby(keys, dropna=False)[["stations", "ev_dc_fast_num", "ev_level2_evse_num", "ccs", "mcs", "nacs",
                                           "level2_only"]].sum().reset_index())


def fleets() -> pd.DataFrame:
    f = pd.read_csv(RAW_DIR / "fmcsa" / "fmcsa_fleet_size_distribution.csv")
    f = f[f.power_units > 0].copy()
    f["fleet_size"] = pd.cut(f.power_units, BINS, labels=BIN_LABELS)
    f["pu"] = f.power_units * f.carriers
    g = f.groupby(["carrier_type", "fleet_size"], observed=True)[
        ["carriers", "pu", "trucks", "drivers", "drivers_within_100mi", "drivers_beyond_100mi", "carriers_mileage",
         "miles"]].sum().reset_index().rename(columns={"pu": "power_units"})
    mi = f[f.carriers_mileage > 0].assign(pu_m=lambda x: x.power_units * x.carriers_mileage)
    g = g.merge(mi.groupby(["carrier_type", "fleet_size"], observed=True).pu_m.sum().rename("power_units_mileage")
                .reset_index(), on=["carrier_type", "fleet_size"], how="left")
    g["miles_per_power_unit"] = g.miles / g.power_units_mileage
    g["short_haul_driver_share"] = g.drivers_within_100mi / (g.drivers_within_100mi + g.drivers_beyond_100mi)
    return g


def carbon_rates() -> pd.DataFrame:
    n = pd.read_csv(RAW_DIR / "oecd" / "necr_road_transport.csv")
    for c in ("REF_AREA", "EMISSIONS_SOURCE", "MEASURE"):
        n[c] = n[c].str.split(":").str[0].str.strip()
    n = n[n.REF_AREA.str.fullmatch(r"[A-Z]{3}") & ~n.REF_AREA.isin({"ODA", "W_X", "E_O", "G20", "OECD"})]
    return (n.pivot_table(index=["REF_AREA", "TIME_PERIOD", "EMISSIONS_SOURCE"], columns="MEASURE", values="OBS_VALUE")
            .reset_index().rename(columns={"REF_AREA": "iso3", "TIME_PERIOD": "year", "EMISSIONS_SOURCE": "fuel"}))


def registrations() -> pd.DataFrame:
    i = pd.read_csv(RAW_DIR / "oecd" / "itf_first_registrations.csv", low_memory=False)
    i.columns = [c.split(":")[0] for c in i.columns]
    i = i[i.VEHICLE_TYPE.str.startswith("GV")].copy()
    i["iso3"] = i.REF_AREA.str.split(":").str[0]
    i["freq"] = i.FREQ.str[0]
    i["year"] = i.TIME_PERIOD.astype(str).str[:4].astype(int)
    out = []
    for (iso, yr), g in i.groupby(["iso3", "year"]):
        for f, need in (("A", 1), ("Q", 4), ("M", 12)):
            s = g[g.freq == f]
            if len(s) >= need:
                out.append({"iso3": iso, "year": yr, "goods_vehicles": s.OBS_VALUE.sum(), "source_freq": f})
                break
    return pd.DataFrame(out)


def main() -> None:
    for name, df in (("us_hd_stations", stations()), ("us_fleet_size_bins", fleets()),
                     ("carbon_rates_road_fuels", carbon_rates()),
                     ("itf_goods_vehicle_registrations", registrations())):
        df.to_csv(PROC_DIR / f"{name}.csv", index=False)
        print(f"{name}: {len(df):,} rows")


if __name__ == "__main__":
    main()
