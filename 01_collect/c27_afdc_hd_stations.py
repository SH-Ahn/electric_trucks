"""US alternative-fuel stations that can serve medium- and heavy-duty vehicles (DOE AFDC
station locator API via NREL; DEMO_KEY works, NREL_API_KEY raises the rate limit):
electric (with DC fast and connector types), hydrogen, CNG, LNG, renewable diesel, with
location, open date, access, owner and maximum vehicle class.

Used for the charging-network questions (depot vs public, corridors) and as a demand
shifter for medium/heavy electric trucks.

Output: 03_data/01_raw/afdc/afdc_stations_md_hd.csv
"""
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from config import NREL_API_KEY, RAW_DIR  # noqa: E402
from helpers import get, log_download  # noqa: E402

URL = "https://developer.nlr.gov/api/alt-fuel-stations/v1.json"
FIELDS = ["id", "station_name", "fuel_type_code", "state", "city", "zip", "latitude", "longitude", "open_date",
          "status_code", "access_code", "facility_type", "owner_type_code", "ev_dc_fast_num", "ev_level2_evse_num",
          "ev_connector_types", "ev_network", "maximum_vehicle_class", "hy_status_link", "date_last_confirmed"]


def main() -> None:
    frames = []
    for cls in ("MD", "HD"):
        js = get(URL, params={"api_key": NREL_API_KEY, "maximum_vehicle_class": cls, "limit": "all",
                              "status": "all", "access": "all", "country": "US"}, timeout=300).json()
        d = pd.DataFrame(js.get("fuel_stations", []))
        frames.append(d.reindex(columns=FIELDS))
        print(f"  class {cls}: {len(d):,} stations")
    d = pd.concat(frames, ignore_index=True).drop_duplicates("id")
    d["ev_connector_types"] = d.ev_connector_types.apply(lambda v: ";".join(v) if isinstance(v, list) else v)
    out = RAW_DIR / "afdc" / "afdc_stations_md_hd.csv"
    out.parent.mkdir(parents=True, exist_ok=True)
    d.to_csv(out, index=False)
    log_download("DOE AFDC station locator (NREL API)", URL, out, "stations serving MD/HD vehicles, all fuels, all statuses")
    print(f"AFDC: {len(d):,} MD/HD-capable stations; fuels {d.fuel_type_code.value_counts().to_dict()}")


if __name__ == "__main__":
    main()
