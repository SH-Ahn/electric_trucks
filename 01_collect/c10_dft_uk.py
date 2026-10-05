"""UK Department for Transport vehicle licensing statistics (DVLA register).

VEH0160_UK  first registrations by body type (incl. HGV, buses and coaches), make,
            generic model, model and fuel, quarterly 2014Q3- (model x quarter panel)
VEH0270     first registrations by body type, make, model, fuel, engine size, annual 2015-
VEH0520     goods vehicles >3.5 t at year end by tax class, wheel plan, detailed body type,
            maximum gross weight band, year of first use and fuel, 1994-

File URLs change with every release, so they are scraped from the landing page.
Source: https://www.gov.uk/government/statistical-data-sets/vehicle-licensing-statistics-data-files
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from config import RAW_DIR  # noqa: E402
from helpers import download, get  # noqa: E402

PAGE = "https://www.gov.uk/government/statistical-data-sets/vehicle-licensing-statistics-data-files"
TABLES = ("df_VEH0160_UK.csv", "df_VEH0270.csv", "df_VEH0520.csv")
OUT = RAW_DIR / "dft_uk"


def main() -> None:
    html = get(PAGE, headers={"User-Agent": "Mozilla/5.0"}).text
    links = set(re.findall(r'https://assets\.publishing\.service\.gov\.uk/media/[^"]+\.csv', html))
    for table in TABLES:
        url = next((u for u in links if u.endswith("/" + table)), None)
        if url is None:
            print(f"FAIL {table}: link not found on landing page")
            continue
        p = download(url, OUT / table, source="UK DfT vehicle licensing statistics", overwrite=True,
                     headers={"User-Agent": "Mozilla/5.0"})
        print(f"ok   {table} ({p.stat().st_size / 1e6:.1f} MB)")


if __name__ == "__main__":
    main()
