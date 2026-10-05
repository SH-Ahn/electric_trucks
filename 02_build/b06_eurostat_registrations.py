"""Eurostat new registrations of lorries (>3.5 t), road tractors and buses by motor energy:
country x year x segment with zero-emission shares (2013-2025).

Output: 03_data/02_processed/eurostat_new_registrations_fuel.csv
"""
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from config import PROC_DIR, RAW_DIR  # noqa: E402
from countries import EU27  # noqa: E402

ISO2 = {"AT": "AUT", "BE": "BEL", "BG": "BGR", "CY": "CYP", "CZ": "CZE", "DE": "DEU", "DK": "DNK",
        "EE": "EST", "EL": "GRC", "ES": "ESP", "FI": "FIN", "FR": "FRA", "HR": "HRV", "HU": "HUN",
        "IE": "IRL", "IT": "ITA", "LT": "LTU", "LU": "LUX", "LV": "LVA", "MT": "MLT", "NL": "NLD",
        "PL": "POL", "PT": "PRT", "RO": "ROU", "SE": "SWE", "SI": "SVN", "SK": "SVK", "UK": "GBR",
        "NO": "NOR", "IS": "ISL", "LI": "LIE", "CH": "CHE", "TR": "TUR", "RS": "SRB", "ME": "MNE",
        "MK": "MKD", "AL": "ALB", "BA": "BIH", "XK": "XKX", "UA": "UKR", "MD": "MDA", "GE": "GEO",
        "EU27_2020": "EU27"}


def main() -> None:
    frames = []
    for code, seg, filt in (("road_eqr_lormot", "Lorries >3.5 t", ("vehicle", "LOR_GT3P5")),
                            ("road_eqr_tracmot", "Road tractors", None),
                            ("road_eqr_busmot", "Buses and coaches", None)):
        d = pd.read_csv(RAW_DIR / "eurostat" / f"{code}.csv")
        if filt:
            d = d[d[filt[0]] == filt[1]]
        d = d.pivot_table(index=["geo", "TIME_PERIOD"], columns="mot_nrg", values="OBS_VALUE",
                          aggfunc="first").reset_index()
        d["segment"] = seg
        frames.append(d)
    d = pd.concat(frames, ignore_index=True)
    d.columns.name = None
    d = d.rename(columns={"geo": "iso2", "TIME_PERIOD": "year", "TOTAL": "total", "ELC": "bev",
                          "HYD_FCELL": "fcev", "DIE": "diesel", "LNG": "lng", "CNG": "cng"})
    d["iso3"] = d["iso2"].map(ISO2).fillna(d["iso2"])
    zero = d[["bev"]].fillna(0).sum(axis=1) + d.get("fcev", 0).fillna(0)
    d["zev"] = zero.where(d["bev"].notna() | d.get("fcev", pd.Series(index=d.index)).notna())
    d["zev_share"] = d["zev"] / d["total"]
    d["eu27_member"] = d["iso3"].isin(EU27).astype(int)
    cols = ["iso3", "year", "segment", "total", "diesel", "bev", "fcev", "lng", "cng", "zev",
            "zev_share", "eu27_member"]
    d = d[[c for c in cols if c in d.columns]].sort_values(["segment", "iso3", "year"])
    d.to_csv(PROC_DIR / "eurostat_new_registrations_fuel.csv", index=False)
    latest = d[(d.year == d.year.max()) & (d.total > 200)]
    print(latest.pivot_table(index="iso3", columns="segment", values="zev_share").round(3)
          .sort_values("Road tractors", ascending=False).head(20))


if __name__ == "__main__":
    main()
