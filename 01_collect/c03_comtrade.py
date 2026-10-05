"""UN Comtrade (Comtrade Plus API): vehicle counts and values.

1. Monthly imports reported by every country, 2022-01 to the latest month, from China
   and from the World, for electric trucks (870460), electric buses (870240),
   electric road tractors (870124), diesel comparators and electric cars.
   Mirror (importer-reported) data track China's 2025-26 e-truck export surge,
   since China's own monthly reports are not in Comtrade after 2024.
2. Annual world totals (partner = World) by reporter, 2017-2025, imports and
   exports, with unit counts (BACI has tonnes only).

Every API call is cached as a CSV under 03_data/01_raw/comtrade/calls/, so the script
resumes where it stopped. The public preview endpoint (no key) caps calls at 500 rows
and has a daily quota: when it answers 403 "Quota Exceeded" the script stops cleanly;
re-run the next day, or set COMTRADE_API_KEY (free tier: 500 calls/day, 100k rows/call;
https://comtradedeveloper.un.org/) to use the full endpoint.

Caution: 870460 also contains low-value electric utility vehicles; filter on unit
values before treating flows as trucks.
"""
import sys
import time
from pathlib import Path

import pandas as pd
import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from config import COMTRADE_API_KEY, RAW_DIR  # noqa: E402
from helpers import SESSION, log_download  # noqa: E402

PREVIEW = "https://comtradeapi.un.org/public/v1/preview/C/{freq}/HS"
FULL = "https://comtradeapi.un.org/data/v1/get/C/{freq}/HS"
GROUPS = {
    "electric": "870460,870240,870124",
    "diesel_trucks": "870421,870422,870423",
    "other": "870210,870121,870380",
}
PARTNERS = {"World": 0, "China": 156}
KEEP = ["freqCode", "refYear", "refMonth", "period", "reporterCode", "flowCode", "partnerCode",
        "cmdCode", "qtyUnitCode", "qty", "isQtyEstimated", "altQtyUnitCode", "altQty", "netWgt",
        "cifvalue", "fobvalue", "primaryValue", "isReported", "isAggregate"]
OUT = RAW_DIR / "comtrade"
CALLS = OUT / "calls"


class QuotaExceeded(Exception):
    pass


def is_fresh(path: Path, period) -> bool:
    """Cached calls are final, except recent periods (reporters keep submitting for ~6 months),
    which are refetched once the cache is a week old."""
    if not path.exists():
        return False
    p = str(period)
    start = pd.Timestamp(f"{p[:4]}-{p[4:6] or '12'}-01")
    recent = start >= pd.Timestamp.today() - pd.DateOffset(months=6)
    age_days = (time.time() - path.stat().st_mtime) / 86400
    return not (recent and age_days > 7)


def call(freq: str, tag: str, **params) -> pd.DataFrame:
    """Fetch one query, caching the result; raise QuotaExceeded on HTTP 403."""
    path = CALLS / f"{tag}.csv"
    if is_fresh(path, params["period"]):
        return pd.read_csv(path)
    base = {"partner2Code": 0, "customsCode": "C00", "motCode": 0}
    url, headers = PREVIEW.format(freq=freq), {}
    if COMTRADE_API_KEY:
        url, headers = FULL.format(freq=freq), {"Ocp-Apim-Subscription-Key": COMTRADE_API_KEY}
    for attempt in range(4):
        r = SESSION.get(url, params={**base, **params}, headers=headers, timeout=120)
        if r.status_code == 403:
            raise QuotaExceeded(r.text[:200])
        if r.status_code == 429 or r.status_code >= 500:
            time.sleep(15 * (attempt + 1))
            continue
        r.raise_for_status()
        rows = r.json().get("data") or []
        if len(rows) >= 500 and not COMTRADE_API_KEY:
            print(f"  WARNING: 500-row cap hit for {tag}")
        d = pd.DataFrame(rows)
        d = d[[c for c in KEEP if c in d]] if not d.empty else pd.DataFrame(columns=KEEP)
        CALLS.mkdir(parents=True, exist_ok=True)
        d.to_csv(path, index=False)
        time.sleep(1.2)
        return d
    raise requests.HTTPError(f"gave up on {tag}")


def months(start="2022-01", end=None) -> list[str]:
    end = end or (pd.Timestamp.today() - pd.DateOffset(months=1)).strftime("%Y-%m")
    return [p.strftime("%Y%m") for p in pd.period_range(start, end, freq="M")]


def queries():
    """Most valuable first: electric imports from China (newest months first), then from the
    World, then the comparator groups, then the annual totals."""
    order = [("China", "electric"), ("World", "electric"), ("China", "diesel_trucks"),
             ("World", "diesel_trucks"), ("China", "other"), ("World", "other")]
    for pname, gname in order:
        for period in reversed(months()):
            yield "M", f"M_{period}_{pname}_{gname}", dict(period=period, cmdCode=GROUPS[gname],
                                                           flowCode="M", partnerCode=PARTNERS[pname])
    codes = [c for g in GROUPS.values() for c in g.split(",")]
    for year in range(2017, 2026):
        for flow in ("M", "X"):
            for code in codes:
                yield "A", f"A_{year}_{flow}_{code}", dict(period=year, cmdCode=code, flowCode=flow,
                                                         partnerCode=0)


def combine() -> None:
    files = sorted(CALLS.glob("*.csv"))
    if not files:
        return
    for prefix, name in (("M_", "comtrade_monthly_imports_2022on.csv.gz"),
                         ("A_", "comtrade_annual_world_totals_2017on.csv.gz")):
        parts = [pd.read_csv(f) for f in files if f.name.startswith(prefix)]
        parts = [p for p in parts if not p.empty]
        if parts:
            d = pd.concat(parts, ignore_index=True)
            path = OUT / name
            d.to_csv(path, index=False, compression="gzip")
            log_download("UN Comtrade API (combined cached calls)", PREVIEW, path,
                         f"{len([f for f in files if f.name.startswith(prefix)])} calls cached")
            print(f"combined {name}: {len(d):,} rows")


def main() -> None:
    todo = [q for q in queries() if not is_fresh(CALLS / f"{q[1]}.csv", q[2]["period"])]
    print(f"{len(todo)} queries to fetch ({'full API' if COMTRADE_API_KEY else 'public preview'})")
    try:
        for i, (freq, tag, params) in enumerate(todo, 1):
            call(freq, tag, **params)
            if i % 25 == 0:
                print(f"  {i}/{len(todo)} done")
    except QuotaExceeded as e:
        print(f"STOPPED: API quota exceeded ({e}). Cached calls are kept; re-run later "
              "or set COMTRADE_API_KEY.")
    combine()
    try:
        ref = SESSION.get("https://comtradeapi.un.org/files/v1/app/reference/Reporters.json",
                          timeout=60).json()["results"]
        pd.DataFrame(ref).to_csv(OUT / "comtrade_reporters.csv", index=False)
    except Exception:  # noqa: BLE001 - reference list is optional
        pass


if __name__ == "__main__":
    main()
