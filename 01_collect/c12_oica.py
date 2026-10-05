"""OICA new-vehicle registrations or sales by country, 2005-2024 (via the Transport Data
Commons mirror of OICA's files).

Caution: OICA "commercial vehicles" bundle light commercial vehicles (vans, pickups;
in North America also light trucks) with heavy trucks and buses, so they are a
market-size control, not a measure of MHD truck sales. Total MHD truck sales
consistent with IEA definitions are derived from IEA EV sales / EV sales share.

Source: https://oica.net/sales-statistics/ ; https://portal.transport-data.org/@oica/global-sales-statistics
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from config import RAW_DIR  # noqa: E402
from helpers import download  # noqa: E402

CKAN = "https://ckan.tdc.prod.datopian.com/dataset/2a173e77-2637-4650-a939-31529bb5820f/resource/"
FILES = {
    "oica_cv_sales_2019_2024.csv": "0538b6c2-197d-49d8-ba58-fce3e4c0f4fb/download/cv-sales-2024cv-sales-simplified-y3nc2r.csv",
    "oica_cv_sales_2005_2018.csv": "c2ab5833-2930-4912-a60f-a3b287e0fa2f/download/cv-sales-2018cv-sales-jubve4.csv",
    "oica_total_sales_2019_2024.csv": "ec9e5af3-86fa-4658-9018-abf204657aed/download/total-sales-2024total-simplified-aajdwd.csv",
    "oica_total_sales_2005_2018.csv": "1bd731c2-6cb5-476a-b195-7c16e17abb5f/download/total-sales-2018total-kmyq76.csv",
}
UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) AppleWebKit/537.36 (KHTML, like Gecko)"}


def main() -> None:
    for name, path in FILES.items():
        p = download(CKAN + path, RAW_DIR / "oica" / name, source="OICA via Transport Data Commons",
                     headers=UA, overwrite=True)
        print(f"ok   {p.name} ({p.stat().st_size / 1e3:.0f} kB)")


if __name__ == "__main__":
    main()
