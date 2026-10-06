"""IEA Policies and Measures database (api.iea.org/policies, no key): all ~13,000 energy,
transport, climate, industry and trade policies with country, year, status, jurisdiction,
topics, technologies and policy types.

A systematic complement to the hand-curated policy database: it covers transport (vehicle
standards, purchase incentives, charging), energy (fuel taxes, electricity, hydrogen),
industry and trade policies across ~180 jurisdictions. The full JSON is cached outside
Dropbox; a flattened table is written to 03_data/01_raw/iea_policies/.

Source: https://www.iea.org/policies (IEA Policies and Measures Database)
"""
import json
import re
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from config import CACHE_DIR, RAW_DIR  # noqa: E402
from helpers import download, log_download  # noqa: E402

URL = "https://api.iea.org/policies"


def names(v) -> str:
    return "; ".join((x.get("name") or x.get("iso3") or "") if isinstance(x, dict) else str(x) for x in (v or []))


def main() -> None:
    path = download(URL, CACHE_DIR / "iea_policies" / "policies.json", source="IEA Policies and Measures database",
                    overwrite="--refresh" in sys.argv, timeout=900, note="full JSON, cached outside Dropbox")
    d = json.load(open(path))
    rows = []
    for x in d:
        desc = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", x.get("description") or "")).strip()
        rows.append({"policy_id": x["policyId"], "title": x["title"], "year": x.get("year"), "year_ended": x.get("yearEnded"),
                     "status": x.get("status"), "jurisdiction": x.get("jurisdiction"), "mandatory": x.get("mandatory"),
                     "iso3": "; ".join(c.get("iso3", "") for c in x.get("countries") or []),
                     "countries": names(x.get("countries")), "states": names(x.get("states")),
                     "topics": names(x.get("topics")), "technologies": names(x.get("technologies")),
                     "policy_types": names(x.get("policyTypes")), "tags": names(x.get("tags")),
                     "date_promulgated": x.get("datePromulgated"), "url": x.get("learnMore"),
                     "description": desc[:3000]})
    out = RAW_DIR / "iea_policies" / "iea_policies.csv.gz"
    out.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(out, index=False, compression="gzip")
    log_download("IEA Policies and Measures database", URL, out, f"{len(rows):,} policies, flattened")
    print(f"IEA policies: {len(rows):,}")


if __name__ == "__main__":
    main()
