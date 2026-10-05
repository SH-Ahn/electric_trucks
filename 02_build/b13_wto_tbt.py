"""WTO TBT notifications on road vehicles, parts, batteries, charging and fuels, tagged by
topic and segment, with the notifying member's ISO3 code.

Topics (not exclusive): EV, battery and charging; emissions and fuel economy; safety and
type approval; tyres; fuels; cybersecurity and connectivity. `heavy` flags notifications
naming trucks, buses, heavy-duty or commercial vehicles, or HS 8701/8702/8704.

Output: 03_data/02_processed/tbt_vehicle_notifications.csv (one row per notification)
        03_data/02_processed/tbt_vehicle_member_year.csv   (regular notifications, counts by topic)
"""
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from config import PROC_DIR, RAW_DIR  # noqa: E402
from countries import iso3_from_name  # noqa: E402

TOPICS = {
    "ev_battery_charging": r"electric vehicle|\bEVs?\b|charging|charger|traction batter|lithium|batter(?:y|ies)|fuel cell|hydrogen",
    "emissions_fuel_economy": r"emission|pollutant|exhaust|fuel (?:consumption|economy|efficiency)|CO2|carbon dioxide|energy efficiency",
    "safety_type_approval": r"safety|type[- ]approval|homologation|conformity assessment|certification|brak|lighting|crash",
    "tyres": r"\btyres?\b|\btires?\b",
    "fuels": r"diesel fuel|gasoline|petrol|biodiesel|ethanol|fuel quality|lubricant",
    "cyber_connectivity": r"cyber|software update|connected vehicle|data security|telematic|radio equipment",
}
HEAVY = r"\btrucks?\b|\blorr(?:y|ies)\b|heavy[- ]duty|commercial vehicles?|\bbus(?:es)?\b|\bcoach(?:es)?\b|categor(?:y|ies) (?:N2|N3|M3)\b"
MEMBER_ISO = {"European Union": "EUU", "Korea, Republic of": "KOR", "Chinese Taipei": "TWN",
              "Saudi Arabia, Kingdom of": "SAU", "United States of America": "USA", "Russian Federation": "RUS",
              "Hong Kong, China": "HKG", "Kyrgyz Republic": "KGZ", "Türkiye": "TUR", "Viet Nam": "VNM"}


def main() -> None:
    d = pd.read_csv(RAW_DIR / "wto_tbt" / "tbt_notifications_vehicles.csv.gz", dtype=str)
    text = (d.Title.fillna("") + " " + d.Description.fillna("") + " " + d["Products covered"].fillna("")
            + " " + d.Keywords.fillna(""))
    hs = d["HS code(s)"].fillna("")
    out = pd.DataFrame({
        "symbol": d["Document symbol"], "member": d["Notifying Member"],
        "date": pd.to_datetime(d["Distribution date"], errors="coerce"), "type": d["Notification type"],
        "title": d.Title, "hs_codes": d["HS code(s)"], "objectives": d.Objectives,
        "adoption_date": d["Proposed adoption  date"], "entry_into_force": d["Proposed entry  into  force date"],
        "link": d["Link to notification(EN)"]})
    out["iso3"] = out.member.map(MEMBER_ISO).fillna(out.member.map(iso3_from_name))
    out["year"] = out.date.dt.year
    for k, pat in TOPICS.items():
        out[k] = text.str.contains(pat, case=False, regex=True).astype(int)
    out["heavy"] = (text.str.contains(HEAVY, case=False, regex=True)
                    | hs.str.contains(r"(?:^|\D)87(?:01|02|04)", regex=True)).astype(int)
    out.to_csv(PROC_DIR / "tbt_vehicle_notifications.csv", index=False)
    reg = out[out.type == "Regular notification"]
    panel = reg.groupby(["iso3", "member", "year"])[list(TOPICS) + ["heavy"]].sum()
    panel["notifications"] = reg.groupby(["iso3", "member", "year"]).size()
    panel.reset_index().to_csv(PROC_DIR / "tbt_vehicle_member_year.csv", index=False)
    print(f"{len(out):,} notifications ({len(reg):,} regular) from {reg.member.nunique()} members, "
          f"{int(reg.year.min())}-{int(reg.year.max())}; EV/battery/charging {reg.ev_battery_charging.sum():,}; "
          f"heavy {reg.heavy.sum():,}")


if __name__ == "__main__":
    main()
