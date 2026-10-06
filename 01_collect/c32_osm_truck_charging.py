"""OpenStreetMap (Overpass API, no key): charging stations tagged for heavy goods vehicles
(hgv=yes/designated, or with a megawatt charging socket, socket:mcs) worldwide, and motorway
service areas and rest areas in Europe, the candidate locations for truck charging hubs
(realized vs candidate sites in a spatial-treatment design).

OSM data (c) OpenStreetMap contributors, ODbL. Coverage of the hgv tag is incomplete and
uneven across countries; use for locations, not for counts of all truck chargers.

Output: 03_data/01_raw/osm/osm_hgv_charging.csv, osm_motorway_services_europe.csv
"""
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from config import RAW_DIR  # noqa: E402
from helpers import SESSION, log_download  # noqa: E402

URL = "https://overpass-api.de/api/interpreter"
EUROPE = "(34,-25,72,45)"
QUERIES = {
    "osm_hgv_charging.csv": """[out:json][timeout:900];
(nwr["amenity"="charging_station"]["hgv"~"^(yes|designated)$"];
 nwr["amenity"="charging_station"]["socket:mcs"];);
out center tags;""",
    "osm_motorway_services_europe.csv": f"""[out:json][timeout:900];
(nwr["highway"="services"]{EUROPE}; nwr["highway"="rest_area"]{EUROPE};);
out center tags;""",
}
TAGS = ["amenity", "highway", "name", "operator", "network", "brand", "hgv", "capacity", "socket:mcs",
        "socket:type2_combo", "socket:type2_combo:output", "socket:mcs:output", "opening_hours", "access",
        "addr:country", "start_date", "fee", "toilets", "fuel:diesel"]
OUT = RAW_DIR / "osm"


def run(query: str) -> pd.DataFrame:
    r = SESSION.post(URL, data={"data": query}, timeout=1200)
    r.raise_for_status()
    rows = []
    for e in r.json()["elements"]:
        c = e.get("center", e)
        t = e.get("tags", {})
        rows.append({"osm_type": e["type"], "osm_id": e["id"], "lat": c.get("lat"), "lon": c.get("lon"),
                     **{k: t.get(k) for k in TAGS}})
    return pd.DataFrame(rows)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for name, q in QUERIES.items():
        d = run(q)
        d.to_csv(OUT / name, index=False)
        log_download("OpenStreetMap (Overpass API)", URL, OUT / name, f"{len(d):,} features; ODbL")
        print(f"{name}: {len(d):,} features")


if __name__ == "__main__":
    main()
