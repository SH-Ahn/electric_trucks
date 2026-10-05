"""BIS central bank policy rates (daily/monthly, ~40 economies plus euro area).

E-trucks are capital-intensive (purchase price 2-3x diesel, lower running costs),
so financing costs shift their total cost of ownership relative to diesel. Policy
rates proxy the cost of capital faced by fleets in the 2022-24 tightening cycle.

Source: https://data.bis.org/topics/CBPOL (bulk CSV, no key)
"""
import io
import sys
import zipfile
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from config import RAW_DIR  # noqa: E402
from helpers import get, log_download  # noqa: E402

URL = "https://data.bis.org/static/bulk/WS_CBPOL_csv_flat.zip"
OUT = RAW_DIR / "bis"
OUT.mkdir(parents=True, exist_ok=True)


def main() -> None:
    z = zipfile.ZipFile(io.BytesIO(get(URL, timeout=300).content))
    d = pd.read_csv(z.open(z.namelist()[0]), low_memory=False)
    keep = [c for c in d.columns if c.split(":")[0] in {"FREQ", "REF_AREA", "TIME_PERIOD", "OBS_VALUE"}]
    d = d[keep]
    d.columns = [c.split(":")[0].lower() for c in keep]
    d = d[d["freq"].astype(str).str.startswith("M")]
    path = OUT / "bis_policy_rates_monthly.csv"
    d.to_csv(path, index=False)
    log_download("BIS central bank policy rates", URL, path, "monthly series only")
    print(f"ok   {len(d):,} rows, {d.ref_area.nunique()} areas, {d.time_period.min()} - {d.time_period.max()}")


if __name__ == "__main__":
    main()
