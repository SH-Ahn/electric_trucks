"""Applied MFN tariffs on electric versus conventional vehicles by country (WITS TRAINS,
reported HS6 simple averages), the input to the 'environmental bias' comparison of
Shapiro (2021) applied to road vehicles.

Electric lines exist only from HS 2022 (870460 trucks, 870124 tractors); buses (870240) and
cars (870380) have separate electric lines from HS 2017. Each pair compares the electric
line with its diesel counterparts in the same nomenclature year:

  truck    870460 vs mean(870422, 870423)   medium and heavy diesel trucks
  tractor  870124 vs 870121
  bus      870240 vs 870210
  car      870380 vs mean(870323, 870332)
  input    850760 vs 840820                 Li-ion batteries vs diesel engines

Input : 03_data/01_raw/wits_tariffs/mfn_tariffs_vehicles.csv
Output: 03_data/02_processed/tariff_gaps_country_year.csv (iso3 x year x pair)
"""
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from config import PROC_DIR, RAW_DIR  # noqa: E402
from countries import iso3_from_m49  # noqa: E402

PAIRS = {"truck": ([870460], [870422, 870423]), "tractor": ([870124], [870121]),
         "bus": ([870240], [870210]), "car": ([870380], [870323, 870332]), "input": ([850760], [840820])}
# WITS reporter codes that differ from the BACI/M49 table
WITS_EXTRA = {158: "TWN", 250: "FRA", 356: "IND", 438: "LIE", 578: "NOR", 756: "CHE", 840: "USA", 918: "EUU",
              412: "XKX"}


def main() -> None:
    w = pd.read_csv(RAW_DIR / "wits_tariffs" / "mfn_tariffs_vehicles.csv")
    w["iso3"] = w.reporter_m49.map(lambda c: WITS_EXTRA.get(int(c)) or iso3_from_m49(c))
    w = w.dropna(subset=["iso3", "mfn_simple_avg"])
    rows = []
    for pair, (ev, ice) in PAIRS.items():
        e = w[w.hs6.isin(ev)].groupby(["iso3", "year"]).mfn_simple_avg.mean().rename("tariff_electric")
        c = w[w.hs6.isin(ice)].groupby(["iso3", "year"]).mfn_simple_avg.mean().rename("tariff_conventional")
        rows.append(pd.concat([e, c], axis=1, join="inner").assign(pair=pair).reset_index())
    d = pd.concat(rows, ignore_index=True)
    d["gap"] = d.tariff_electric - d.tariff_conventional
    d["sign"] = pd.cut(d.gap, [-1e9, -0.5, 0.5, 1e9], labels=["electric lower", "equal", "electric higher"])
    d.to_csv(PROC_DIR / "tariff_gaps_country_year.csv", index=False)
    last = d.sort_values("year").groupby(["iso3", "pair"]).tail(1)
    print(last.groupby("pair").sign.value_counts(normalize=True).unstack().round(2).to_string())


if __name__ == "__main__":
    main()
