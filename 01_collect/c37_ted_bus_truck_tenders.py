"""EU public procurement notices for buses and municipal trucks (TED, Tenders Electronic Daily,
Search API v3; no key). eForms notices (mandatory from late 2023) carry the buyer, the winning
supplier and its country, tender values and the number of tenders received, so award notices
identify who wins public bus and refuse-truck contracts by country and year (home bias, Chinese
entry, Clean Vehicles Directive procurement).

CPV codes: 34120000 vehicles for 10+ persons; 34121000-34121500 buses, public-service, articulated,
double-deck, low-floor buses and coaches; 34144910 electric buses; 34144900 electric vehicles;
34144510-34144512 refuse vehicles.

Older award notices (2017-2023, before eForms) come from the TED CSV bulk files on data.europa.eu
(one row per award, with winner name and country, number of offers and of non-EU tenders, award
value), filtered to the same CPV codes.

Output: 03_data/01_raw/ted/ted_notices_buses_trucks.csv (API, one row per notice; lists joined by '|')
        03_data/01_raw/ted/ted_can_bulk_2017_2023_buses_trucks.csv (bulk, one row per award)
"""
import sys
import zipfile
import time
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from config import CACHE_DIR, RAW_DIR  # noqa: E402
from helpers import SESSION, download, log_download  # noqa: E402

URL = "https://api.ted.europa.eu/v3/notices/search"
CPV = ["34120000", "34121000", "34121100", "34121200", "34121300", "34121400", "34121500", "34144910", "34144900",
       "34144510", "34144511", "34144512"]
FIELDS = ["publication-number", "publication-date", "notice-type", "procedure-type", "buyer-country", "buyer-name",
          "winner-name", "winner-country", "winner-owner-nationality", "winner-size", "organisation-name-tenderer",
          "organisation-country-tenderer", "total-value", "total-value-cur", "tender-value", "tender-value-cur",
          "result-value-notice", "result-value-cur-notice", "estimated-value-proc", "estimated-value-cur-proc",
          "received-submissions-type-val", "received-submissions-type-code", "classification-cpv",
          "main-classification-proc", "title-proc", "place-of-performance"]
OUT = RAW_DIR / "ted"
BULK = "https://data.europa.eu/api/hub/store/data/ted-contract-award-notices-{y}.zip"
BULK_COLS = ["ID_NOTICE_CAN", "YEAR", "DT_DISPATCH", "CANCELLED", "CAE_NAME", "CAE_TOWN", "ISO_COUNTRY_CODE", "CAE_TYPE",
             "TYPE_OF_CONTRACT", "TAL_LOCATION_NUTS", "CPV", "ADDITIONAL_CPVS", "ID_LOT", "LOTS_NUMBER", "VALUE_EURO",
             "B_EU_FUNDS", "TOP_TYPE", "CRIT_CODE", "CRIT_PRICE_WEIGHT", "NUMBER_AWARDS", "ID_AWARD",
             "INFO_ON_NON_AWARD", "B_AWARDED_TO_A_GROUP", "WIN_NAME", "WIN_TOWN", "WIN_COUNTRY_CODE", "B_CONTRACTOR_SME",
             "TITLE", "NUMBER_OFFERS", "NUMBER_TENDERS_SME", "NUMBER_TENDERS_OTHER_EU", "NUMBER_TENDERS_NON_EU",
             "AWARD_EST_VALUE_EURO", "AWARD_VALUE_EURO", "DT_AWARD"]


def bulk() -> pd.DataFrame:
    keep = tuple(CPV)
    frames = []
    for y in ("2017", "2018-2023"):
        z = download(BULK.format(y=y), CACHE_DIR / "ted" / f"ted-can-{y}.zip", source="TED CSV bulk awards",
                     timeout=7200, note="cached outside Dropbox")
        with zipfile.ZipFile(z) as zf:
            with zf.open(zf.namelist()[0]) as fh:
                for ch in pd.read_csv(fh, usecols=lambda c: c in BULK_COLS, dtype=str, chunksize=500_000,
                                      low_memory=False):
                    cpv = ch.CPV.fillna("").str[:8]
                    add = ch.ADDITIONAL_CPVS.fillna("").str[:8]
                    frames.append(ch[cpv.str.startswith(keep) | add.str.startswith(keep)])
    return pd.concat(frames, ignore_index=True)


def flat(v):
    if isinstance(v, dict):  # multilingual text: take English if present, else the first language
        v = v.get("eng") or next(iter(v.values()), "")
    if isinstance(v, list):
        return "|".join(str(x) for x in v)
    return v


def main(start="20170101") -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    body = {"query": f"classification-cpv IN ({' '.join(CPV)}) AND publication-date >= {start}", "fields": FIELDS,
            "limit": 250, "scope": "ALL", "paginationMode": "ITERATION"}
    rows, token, k = [], None, 0
    while True:
        if token:
            body["iterationNextToken"] = token
        r = SESSION.post(URL, json=body, timeout=300)
        r.raise_for_status()
        d = r.json()
        for n in d.get("notices", []):
            n.pop("links", None)
            rows.append({f: flat(n.get(f)) for f in FIELDS})
        token = d.get("iterationNextToken")
        k += 1
        if k % 20 == 0:
            print(f"  {len(rows):,} notices")
        if not token or not d.get("notices"):
            break
        time.sleep(0.5)
    t = pd.DataFrame(rows)
    path = OUT / "ted_notices_buses_trucks.csv"
    t.to_csv(path, index=False)
    log_download("TED Search API v3", URL, path, f"CPV {', '.join(CPV)}; from {start}; {len(t):,} notices")
    print(f"TED: {len(t):,} notices; types {t['notice-type'].value_counts().head(8).to_dict()}")
    b = bulk()
    path = OUT / "ted_can_bulk_2017_2023_buses_trucks.csv"
    b.to_csv(path, index=False)
    log_download("TED CSV bulk award notices (filtered)", BULK.format(y="2017|2018-2023"), path,
                 f"CPV {', '.join(CPV)}; {len(b):,} award rows")
    print(f"TED bulk: {len(b):,} award rows, {b.YEAR.min()}-{b.YEAR.max()}")


if __name__ == "__main__":
    if "--bulk-only" in sys.argv:
        b = bulk()
        b.to_csv(OUT / "ted_can_bulk_2017_2023_buses_trucks.csv", index=False)
        log_download("TED CSV bulk award notices (filtered)", BULK.format(y="2017|2018-2023"),
                     OUT / "ted_can_bulk_2017_2023_buses_trucks.csv", f"{len(b):,} award rows")
        print(f"TED bulk: {len(b):,} award rows, {b.YEAR.min()}-{b.YEAR.max()}")
    else:
        main()
