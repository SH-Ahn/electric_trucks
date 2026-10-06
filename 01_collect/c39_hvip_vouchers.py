"""California HVIP (Clean Truck and Bus Voucher Incentive Project; CARB/CALSTART; no key):

1. Voucher records behind the public HVIP voucher funding map (2010 onward): voucher amount,
   drivetrain, manufacturer, vocation, gross-weight class, county, census tract, ZIP code, public
   or private purchaser, disadvantaged-community flag, small-fleet and drayage flags, request date,
   redemption status, purchaser and dealership (company names as published on the map).
2. The HVIP eligible-vehicle catalog (model, OEM, category, technology, voucher amount, battery,
   model year, GVWR bracket).

Used for subsidised purchases by fleet, place and model, the closest public analogue to transaction
data for US zero-emission trucks, and for spatial designs (census tracts, ports).

Output: 03_data/01_raw/hvip/hvip_vouchers.csv, hvip_catalog.csv
"""
import io
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from config import RAW_DIR  # noqa: E402
from helpers import SESSION, log_download  # noqa: E402

VOUCHERS = "https://hvip-voucher-funding-map.zevtoolbox.org/api/vouchers/hvip"
CATALOG = "https://californiahvip.org/vehicles/?hvip_export=csv"
UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/126.0 Safari/537.36"}
OUT = RAW_DIR / "hvip"


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    v = pd.DataFrame(SESSION.get(VOUCHERS, headers=UA, timeout=300).json())
    v.to_csv(OUT / "hvip_vouchers.csv", index=False)
    log_download("California HVIP voucher map (API)", VOUCHERS, OUT / "hvip_vouchers.csv", f"{len(v):,} vouchers")
    r = SESSION.get(CATALOG, headers=UA, timeout=120)
    c = pd.read_csv(io.StringIO(r.content.decode("utf-8-sig")))
    c.to_csv(OUT / "hvip_catalog.csv", index=False)
    log_download("California HVIP vehicle catalog", CATALOG, OUT / "hvip_catalog.csv", f"{len(c):,} models")
    print(f"HVIP: {len(v):,} vouchers {v.voucher_requested_year.min():.0f}-{v.voucher_requested_year.max():.0f}; "
          f"drivetrains {v.drivetrain.value_counts().to_dict()}; catalog {len(c)} models")


if __name__ == "__main__":
    main()
