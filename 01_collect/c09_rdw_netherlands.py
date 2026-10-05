"""Netherlands RDW open vehicle register: every registered truck (EU categories N2, N3)
and bus/coach (M2, M3), with make, commercial model name, body type, weights,
first-registration dates and fuel/emission records.

This is a free, vehicle-level, make x model x date x powertrain source for one
country. It is used to (i) build a quarterly model-level panel of new
registrations like the licensed sales data, and (ii) validate that data once it
arrives.

Caveats: the open register holds vehicles currently registered plus recently
exported ones (``export_indicator`` = "Ja"); older cohorts are therefore
under-counted (survivorship). ``datum_eerste_toelating`` is the first admission
anywhere; vehicles first registered abroad (used imports) have an earlier date
than ``datum_eerste_tenaamstelling_in_nederland``.

API: Socrata SODA (https://opendata.rdw.nl), datasets m9d7-ebf2 (vehicles) and
8ys7-d773 (fuel). No key needed.
"""
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from config import RAW_DIR  # noqa: E402
from helpers import get, log_download  # noqa: E402

VEH = "https://opendata.rdw.nl/resource/m9d7-ebf2.json"
FUEL = "https://opendata.rdw.nl/resource/8ys7-d773.json"
CATEGORIES = ("N2", "N3", "M2", "M3")
FIELDS = ["kenteken", "voertuigsoort", "merk", "handelsbenaming", "inrichting",
          "europese_voertuigcategorie", "datum_eerste_toelating",
          "datum_eerste_tenaamstelling_in_nederland", "toegestane_maximum_massa_voertuig",
          "technische_max_massa_voertuig", "massa_ledig_voertuig", "maximum_massa_samenstelling",
          "aantal_cilinders", "cilinderinhoud", "aantal_zitplaatsen", "aantal_staanplaatsen",
          "aantal_wielen", "wielbasis", "lengte", "catalogusprijs", "export_indicator", "type",
          "variant", "uitvoering", "typegoedkeuringsnummer"]
PAGE = 50_000
BATCH = 400
OUT = RAW_DIR / "rdw_netherlands"
OUT.mkdir(parents=True, exist_ok=True)


def fetch_vehicles() -> pd.DataFrame:
    cats = ",".join(f"'{c}'" for c in CATEGORIES)
    frames, offset = [], 0
    while True:
        r = get(VEH, params={"$select": ",".join(FIELDS),
                             "$where": f"europese_voertuigcategorie in({cats})",
                             "$order": "kenteken", "$limit": PAGE, "$offset": offset}, timeout=300)
        chunk = pd.DataFrame(r.json())
        frames.append(chunk)
        print(f"  vehicles: {offset + len(chunk):,}")
        if len(chunk) < PAGE:
            break
        offset += PAGE
    return pd.concat(frames, ignore_index=True)


def fetch_fuel_batch(plates: list[str]) -> pd.DataFrame:
    quoted = ",".join(f"'{p}'" for p in plates)
    for attempt in range(5):
        try:
            r = get(FUEL, params={"$where": f"kenteken in({quoted})", "$limit": 5000}, timeout=120)
            return pd.DataFrame(r.json())
        except Exception:  # noqa: BLE001 - retry with back-off, then give up on this batch
            time.sleep(5 * (attempt + 1))
    print(f"  WARNING: fuel batch starting {plates[0]} failed")
    return pd.DataFrame({"kenteken": plates, "_failed": True})


def main(first_year: int = 2010) -> None:
    veh = fetch_vehicles()
    path = OUT / "rdw_vehicles_n2n3m2m3.csv.gz"
    veh.to_csv(path, index=False, compression="gzip")
    log_download("RDW open data (vehicles)", VEH, path,
                 f"europese_voertuigcategorie in {CATEGORIES}; {len(veh):,} vehicles")

    first = pd.to_numeric(veh["datum_eerste_toelating"].str[:4], errors="coerce")
    first_nl = pd.to_numeric(veh["datum_eerste_tenaamstelling_in_nederland"].str[:4], errors="coerce")
    plates = veh.loc[(first >= first_year) | (first_nl >= first_year), "kenteken"].tolist()
    batches = [plates[i:i + BATCH] for i in range(0, len(plates), BATCH)]
    print(f"fuel lookups: {len(plates):,} plates in {len(batches)} batches")
    with ThreadPoolExecutor(max_workers=4) as ex:
        fuel = pd.concat(list(ex.map(fetch_fuel_batch, batches)), ignore_index=True)
    path = OUT / "rdw_fuel_n2n3m2m3.csv.gz"
    fuel.to_csv(path, index=False, compression="gzip")
    log_download("RDW open data (fuel)", FUEL, path,
                 f"fuel/emission records for plates first registered >= {first_year}; {len(fuel):,} rows")
    print(f"done: {len(veh):,} vehicles, {len(fuel):,} fuel rows")


if __name__ == "__main__":
    main()
