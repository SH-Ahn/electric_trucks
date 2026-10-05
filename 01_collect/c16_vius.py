"""US Census Vehicle Inventory and Use Survey (VIUS) 2021 public-use microdata.

About 150,000 sampled trucks with GVW class, body type, annual and typical daily
distance, range of operation, home-base return, fleet size, fuel, business sector
and weights. Used to measure which segments are technically "electrifiable" with
today's ranges (duty-cycle heterogeneity) and how fleet size is distributed.

Source: https://www.census.gov/programs-surveys/vius.html
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from config import RAW_DIR  # noqa: E402
from helpers import download  # noqa: E402

BASE = "https://www2.census.gov/programs-surveys/vius/datasets/2021/"
FILES = ("vius_2021_puf_csv.zip", "vius-2021-puf-data-dictionary.xlsx")


def main() -> None:
    for f in FILES:
        p = download(BASE + f, RAW_DIR / "vius" / f, source="US Census VIUS 2021")
        print(f"ok   {p.name} ({p.stat().st_size / 1e6:.1f} MB)")


if __name__ == "__main__":
    main()
