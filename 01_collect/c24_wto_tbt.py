"""WTO TBT notifications (ePing bulk file, all SPS/TBT notifications since 1995, no key):
technical regulations and conformity-assessment procedures that WTO members notify for
motor vehicles, trucks, buses, parts, batteries and charging equipment.

Each notification has the notifying member, date, products (HS, ICS codes), objectives,
proposed adoption and entry-into-force dates, and whether the measure conforms to the
relevant international standard, which allows counts of new technical barriers by country,
product and topic, and a measure of divergence from international (e.g. UNECE) standards.

The 45 MB workbook is cached outside Dropbox; the vehicle-related subset is written to
03_data/01_raw/wto_tbt/.

Source: https://eping.wto.org (WTO/ITC/UN DESA ePing), bulk file NotificationExcelFiles/Notification_EN.xlsx
"""
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from config import CACHE_DIR, RAW_DIR  # noqa: E402
from helpers import download, log_download  # noqa: E402

URL = "https://eping.wto.org/NotificationExcelFiles/Notification_EN.xlsx"
UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/126.0 Safari/537.36"}
HS_PREFIXES = ("8701", "8702", "8703", "8704", "8705", "8706", "8707", "8708", "8716",  # vehicles, parts, trailers
               "8507", "850440", "8544", "8408", "4011", "2710")                       # batteries, chargers, cables, engines, tyres, fuels
ICS_PREFIXES = ("43.", "29.220", "27.190")  # road vehicles; batteries; (fuel cells)
KEYWORDS = (r"(?:motor vehicle|road vehicle|truck|lorry|lorries|heavy[- ]duty|commercial vehicle|\bbus\b|buses|tractor|"
            r"trailer|electric vehicle|\bEVs?\b|charging|charger|traction batter|lithium|homologation|type[- ]approval|"
            r"vehicle emission|exhaust emission|fuel (?:consumption|economy)|tyre|tire)")
OUT = RAW_DIR / "wto_tbt"


def main() -> None:
    path = download(URL, CACHE_DIR / "wto" / "Notification_EN.xlsx", source="WTO ePing bulk notifications",
                    headers=UA, timeout=1800, overwrite="--refresh" in sys.argv, note="all SPS/TBT notifications, cached outside Dropbox")
    d = pd.read_excel(path, dtype=str)
    d = d.apply(lambda c: c.str.strip())
    d = d[d["Document symbol"].str.startswith("G/TBT/N", na=False)]
    hs = d["HS code(s)"].fillna("").str.replace(".", "", regex=False)
    ics = d["ICS code(s)"].fillna("")
    text = (d["Title"].fillna("") + " " + d["Description"].fillna("") + " " + d["Products covered"].fillna("")
            + " " + d["Keywords"].fillna(""))
    by_hs = hs.str.contains("|".join(rf"(?:^|\D){p}" for p in HS_PREFIXES), regex=True)
    by_ics = ics.str.contains("|".join(rf"(?:^|\D){p.replace('.', r'\.')}" for p in ICS_PREFIXES), regex=True)
    by_kw = text.str.contains(KEYWORDS, case=False, regex=True)
    v = d[by_hs | by_ics | by_kw].copy()
    v["match_hs"], v["match_ics"], v["match_keyword"] = by_hs[v.index], by_ics[v.index], by_kw[v.index]
    OUT.mkdir(parents=True, exist_ok=True)
    out = OUT / "tbt_notifications_vehicles.csv.gz"
    v.to_csv(out, index=False, compression="gzip")
    log_download("WTO ePing (filtered)", URL, out, "TBT notifications on vehicles, parts, batteries, charging, fuels")
    print(f"TBT notifications: {len(d):,} total; {len(v):,} vehicle-related "
          f"(HS {int(v.match_hs.sum()):,}, ICS {int(v.match_ics.sum()):,}, keywords {int(v.match_keyword.sum()):,})")


if __name__ == "__main__":
    main()
