"""Germany's truck toll mileage index (Lkw-Maut-Fahrleistungsindex, Destatis): daily and
monthly kilometres driven by heavy trucks (4+ axles) on toll roads since 2008, from the
toll system's process data; a high-frequency measure of freight activity in Europe's
largest truck market and an early indicator of industrial production.

Source: https://www.destatis.de/EN/Service/EXSTAT/Datensaetze/truck-toll-mileage.html
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from config import RAW_DIR  # noqa: E402
from helpers import download, get  # noqa: E402

PAGE = ("https://www.destatis.de/DE/Themen/Branchen-Unternehmen/Industrie-Verarbeitendes-Gewerbe/"
        "Tabellen/Lkw-Maut-Fahrleistungsindex-Daten.html")
UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) AppleWebKit/537.36"}


def main() -> None:
    html = get(PAGE, headers=UA).text
    href = re.search(r'href="([^"]+lkw-maut-fahrleistungsindex[^"]+\.xlsx[^"]*)"', html).group(1)
    url = "https://www.destatis.de" + href.replace("&amp;amp;", "&").replace("&amp;", "&")
    p = download(url, RAW_DIR / "germany_toll_index" / "lkw_maut_fahrleistungsindex.xlsx",
                 source="Destatis truck toll mileage index", headers=UA, overwrite=True)
    print(f"ok {p.name} ({p.stat().st_size / 1e3:.0f} kB)")


if __name__ == "__main__":
    main()
