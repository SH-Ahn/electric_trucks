"""CARB Large Entity Reporting (Advanced Clean Trucks one-time fleet reporting, 2021): statewide
aggregates for 1,866 large entities and government fleets in California, 386,286 vehicles over
8,500 lb GVWR. Parsed tables by vehicle group (day-cab tractors, sleeper-cab tractors, other
vehicles): fuel type, daily mileage, return to base, fuelling at base, predictable use, parking at
base for more than 8 hours, annual miles and holding period. These are the usage moments that
decide depot charging feasibility and residual-value risk.

Source PDF: https://ww2.arb.ca.gov/sites/default/files/2022-02/Large_Entity_Reporting_Aggregated_Data_ADA.pdf
Output: 03_data/01_raw/carb/carb_ler_vehicle_tables.csv (question x row x vehicle group)
"""
import re
import subprocess
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from config import RAW_DIR  # noqa: E402
from helpers import download, log_download  # noqa: E402

URL = "https://ww2.arb.ca.gov/sites/default/files/2022-02/Large_Entity_Reporting_Aggregated_Data_ADA.pdf"
OUT = RAW_DIR / "carb"
GROUPS = ["day_cab_tractor", "sleeper_cab_tractor", "other_vehicles"]
# question number -> (topic, row labels); numbers on each row are read left to right, percent columns dropped
TABLES = {
    16: ("fuel_type", ["Diesel", "Gasoline", "Natural gas", "Electricity", "Hydrogen", "Other", "Invalid responses"]),
    18: ("daily_mileage", ["Operate up to 100 miles", "101 to 150 miles", "151 to 200 miles", "201 to 300 miles",
                           "Over 300 miles"]),
    19: ("returns_to_base_daily", ["Yes", "No"]),
    20: ("fuels_at_home_base", ["Yes", "No"]),
    21: ("predictable_usage", ["Yes", "No"]),
    27: ("parked_over_8h_at_base", ["Yes", "No"]),
    31: ("annual_miles", ["5,000 or less", "10,000", "20,000", "30,000", "40,000", "50,000", "60,000", "70,000",
                          "80,000", "90,000", "100,000", "More than 100,000"]),
    32: ("years_kept", ["Less than 4", "5 to 10", "11 to 15", "16 to 20", "More than 20"]),
}


def section(text: str, q: int) -> str:
    starts = [m.start() for m in re.finditer(rf"^\s*{q}\.\s", text, re.M)]
    s = starts[-1]  # the last match is the table, the first is the table of contents
    nxt = re.search(rf"^\s*{q + 1}\.\s", text[s + 5:], re.M)
    return text[s: s + 5 + nxt.start()] if nxt else text[s:]


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    pdf = download(URL, OUT / "Large_Entity_Reporting_Aggregated_Data_ADA.pdf", source="CARB Large Entity Reporting")
    text = subprocess.run(["pdftotext", "-layout", str(pdf), "-"], capture_output=True, text=True).stdout
    rows = []
    for q, (topic, labels) in TABLES.items():
        sec = section(text, q)
        for lab in labels:
            m = re.search(rf"^\s*{re.escape(lab)}\s+([\d,\.%\s]+)$", sec, re.M)
            if not m:
                print(f"  missing: Q{q} {lab}")
                continue
            nums = [int(x.replace(",", "")) for x in m.group(1).split() if not x.endswith("%")]
            for g, v in zip(GROUPS, nums):
                rows.append({"question": q, "topic": topic, "row": lab, "group": g, "vehicles": v})
    d = pd.DataFrame(rows)
    path = OUT / "carb_ler_vehicle_tables.csv"
    d.to_csv(path, index=False)
    log_download("CARB Large Entity Reporting (parsed)", URL, path, "statewide aggregates, 2021 reporting")
    print(d.pivot_table(index=["topic", "row"], columns="group", values="vehicles", sort=False).to_string())


if __name__ == "__main__":
    main()
