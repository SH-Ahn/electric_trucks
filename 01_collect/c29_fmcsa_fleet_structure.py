"""US motor-carrier fleet structure from the FMCSA Company Census File (data.transportation.gov
Socrata API, no key): active carriers aggregated by number of power units, with trucks,
drivers operating within and beyond 100 miles, self-reported annual mileage (MCS-150), and
private vs for-hire status.

Self-reported power units contain keying errors (e.g. 599,994 units with 4 drivers). A carrier
is kept if it reports at most 10 power units or at most 3 power units per driver; the
mileage aggregate also requires a 2023+ MCS-150 mileage year and 1,000-250,000 miles per unit.

Only aggregates are downloaded; the census contains names and contact details, which are
neither requested nor stored.

Output: 03_data/01_raw/fmcsa/fmcsa_fleet_size_distribution.csv
"""
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from config import RAW_DIR  # noqa: E402
from helpers import get, log_download  # noqa: E402

URL = "https://data.transportation.gov/resource/az4n-8mr2.json"
OUT = RAW_DIR / "fmcsa"
PLAUSIBLE = "(power_units::number <= 10 or power_units::number <= 3 * total_drivers::number)"


def main() -> None:
    frames = []
    for kind, cond in (("for_hire", "classdef like '%AUTHORIZED FOR HIRE%'"),
                       ("private_only", "classdef like '%PRIVATE PROPERTY%' and classdef not like '%AUTHORIZED FOR HIRE%'")):
        where = f"status_code='A' and {cond} and {PLAUSIBLE}"
        q = {"$select": ("power_units::number as power_units, count(*) as carriers, sum(truck_units::number) as trucks, "
                         "sum(total_drivers::number) as drivers, "
                         "sum(interstate_within_100_miles::number + intrastate_within_100_miles::number) as drivers_within_100mi, "
                         "sum(interstate_beyond_100_miles::number + intrastate_beyond_100_miles::number) as drivers_beyond_100mi"),
             "$where": where, "$group": "power_units::number", "$limit": 50000}
        d = pd.DataFrame(get(URL, params=q, timeout=600).json())
        q = {"$select": ("power_units::number as power_units, count(*) as carriers_mileage, "
                         "sum(mcs150_mileage::number) as miles"),
             "$where": (f"{where} and mcs150_mileage_year::number >= 2023 and "
                        "mcs150_mileage::number between 1000 * power_units::number and 250000 * power_units::number"),
             "$group": "power_units::number", "$limit": 50000}
        m = pd.DataFrame(get(URL, params=q, timeout=600).json())
        d = d.merge(m, on="power_units", how="left")
        d["carrier_type"] = kind
        frames.append(d)
        print(f"  {kind}: {len(d):,} fleet-size cells")
    d = pd.concat(frames, ignore_index=True)
    for c in ("power_units", "carriers", "trucks", "drivers", "drivers_within_100mi", "drivers_beyond_100mi",
              "carriers_mileage", "miles"):
        d[c] = pd.to_numeric(d[c], errors="coerce")
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / "fmcsa_fleet_size_distribution.csv"
    d.sort_values(["carrier_type", "power_units"]).to_csv(path, index=False)
    log_download("FMCSA Company Census File (aggregated)", URL, path, "active carriers by power units, for-hire vs private")
    print(f"FMCSA: {int(d.carriers.sum()):,} active carriers, {int(d.power_units.mul(d.carriers).sum()):,} power units")


if __name__ == "__main__":
    main()
