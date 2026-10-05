"""European Commission Weekly Oil Bulletin: weekly consumer prices of diesel, petrol and
LPG with and without taxes for every EU member state since 2005, plus VAT, excise
duties (with dates of change) and other indirect taxes.

Prices are in EUR per 1,000 litres. Parsed into a tidy panel by 02_build/b03_fuel_prices.py.

Source: https://energy.ec.europa.eu/data-and-analysis/weekly-oil-bulletin_en
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from config import RAW_DIR  # noqa: E402
from helpers import download  # noqa: E402

BASE = "https://energy.ec.europa.eu/document/download/"
FILES = {
    "oil_bulletin_history.xlsx":
        "906e60ca-8b6a-44e7-8589-652854d2fd3f_en?filename=Weekly_Oil_Bulletin_Prices_History_maticni_4web.xlsx",
    "oil_bulletin_duties_and_taxes.xlsx":
        "ccdc6e96-6792-40cb-b0b4-b6609f1e30d0_en?filename=Oil_Bulletin_Duties_and_taxes.xlsx",
}
OUT = RAW_DIR / "eu_oil_bulletin"


def main(overwrite: bool = True) -> None:
    for name, path in FILES.items():
        p = download(BASE + path, OUT / name, source="EC Weekly Oil Bulletin", overwrite=overwrite,
                     headers={"User-Agent": "Mozilla/5.0"})
        print(f"ok {p.name} ({p.stat().st_size / 1e6:.1f} MB)")


if __name__ == "__main__":
    main()
