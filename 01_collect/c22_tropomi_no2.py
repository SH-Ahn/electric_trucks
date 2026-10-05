"""Satellite NO2 (Sentinel-5P TROPOMI, monthly-mean tropospheric columns, KNMI/TEMIS 0.125-degree
grids) around places where truck policy or truck electrification bites: Dutch zero-emission-zone
cities vs comparison cities, Swiss vs Austrian transalpine truck corridors, Chinese steel and
port cities (heavy e-truck adoption), US container ports (drayage), and other large cities.
NO2 is dominated by combustion and especially diesel traffic, so it is a remote-sensing outcome
for event studies of truck policies.

Global grids (~3.5 MB each, May 2018 onward) are cached outside Dropbox; point extracts
(mean within RADIUS_KM) are written to 03_data/01_raw/tropomi/.

Source: KNMI TEMIS, https://www.temis.nl/airpollution/no2col/no2month_tropomi.php
"""
import gzip
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from config import CACHE_DIR, RAW_DIR  # noqa: E402
from helpers import download, log_download  # noqa: E402

URL = "https://d1qb6yzwaaq4he.cloudfront.net/tropomi/no2/{y}/{m:02d}/no2_{y}{m:02d}.asc.gz"
RADIUS_KM = 20
NLAT, NLON = 1440, 2880
LATS = -89.9375 + 0.125 * np.arange(NLAT)
LONS = -179.9375 + 0.125 * np.arange(NLON)
OUT = RAW_DIR / "tropomi"
OUT.mkdir(parents=True, exist_ok=True)

# name, iso3, group, lat, lon
POINTS = [
    ("Amsterdam", "NLD", "NL zero-emission zone city", 52.3676, 4.9041),
    ("Rotterdam", "NLD", "NL zero-emission zone city", 51.9244, 4.4777),
    ("The Hague", "NLD", "NL zero-emission zone city", 52.0705, 4.3007),
    ("Utrecht", "NLD", "NL zero-emission zone city", 52.0907, 5.1214),
    ("Eindhoven", "NLD", "NL zero-emission zone city", 51.4416, 5.4697),
    ("Antwerp", "BEL", "Comparison city (no ZE zone)", 51.2194, 4.4025),
    ("Brussels", "BEL", "Comparison city (no ZE zone)", 50.8503, 4.3517),
    ("Dusseldorf", "DEU", "Comparison city (no ZE zone)", 51.2277, 6.7735),
    ("Cologne", "DEU", "Comparison city (no ZE zone)", 50.9375, 6.9603),
    ("Duisburg", "DEU", "Comparison city (no ZE zone)", 51.4344, 6.7623),
    ("Gotthard north (Erstfeld)", "CHE", "Swiss transalpine corridor", 46.8200, 8.6500),
    ("Bellinzona", "CHE", "Swiss transalpine corridor", 46.1950, 9.0230),
    ("Innsbruck (Brenner)", "AUT", "Austrian transalpine corridor", 47.2692, 11.4041),
    ("Bolzano (Brenner)", "ITA", "Austrian transalpine corridor", 46.4983, 11.3548),
    ("Tangshan", "CHN", "China steel/port city", 39.6309, 118.1802),
    ("Handan", "CHN", "China steel/port city", 36.6256, 114.5390),
    ("Tianjin", "CHN", "China steel/port city", 39.3434, 117.3616),
    ("Shijiazhuang", "CHN", "China steel/port city", 38.0428, 114.5149),
    ("Baotou", "CHN", "China steel/port city", 40.6571, 109.8403),
    ("Yibin", "CHN", "China steel/port city", 28.7518, 104.6417),
    ("Shanghai", "CHN", "China large city", 31.2304, 121.4737),
    ("Ningbo", "CHN", "China large city", 29.8683, 121.5440),
    ("Shenzhen", "CHN", "China large city", 22.5431, 114.0579),
    ("Qingdao", "CHN", "China large city", 36.0671, 120.3826),
    ("Beijing", "CHN", "China large city", 39.9042, 116.4074),
    ("Los Angeles/Long Beach ports", "USA", "US container port", 33.7500, -118.2200),
    ("New York/New Jersey port", "USA", "US container port", 40.6700, -74.0400),
    ("Houston port", "USA", "US container port", 29.7300, -95.2700),
    ("Savannah port", "USA", "US container port", 32.0800, -81.0900),
    ("Seattle/Tacoma ports", "USA", "US container port", 47.2700, -122.4100),
    ("Delhi", "IND", "Other large city", 28.6139, 77.2090),
    ("Mumbai/JNPT", "IND", "Other large city", 18.9500, 72.9500),
    ("Santiago", "CHL", "Other large city", -33.4489, -70.6693),
    ("Sao Paulo", "BRA", "Other large city", -23.5505, -46.6333),
    ("Mexico City", "MEX", "Other large city", 19.4326, -99.1332),
    ("Bogota", "COL", "Other large city", 4.7110, -74.0721),
]


def parse_grid(path: Path) -> np.ndarray:
    """TEMIS ASCII grid: 4 header lines, then per latitude a 'lat=' line and 2880 4-char values."""
    text = gzip.open(path, "rt").read()
    blocks = text.split("lat=")[1:]
    grid = np.full((NLAT, NLON), np.nan, dtype=np.float32)
    for i, b in enumerate(blocks[:NLAT]):
        body = "".join(b.split("\n")[1:])
        vals = np.array([body[k:k + 4] for k in range(0, NLON * 4, 4)], dtype=np.float32)
        vals[vals <= -999] = np.nan
        grid[i] = vals
    return grid  # units: 1e13 molecules/cm2; rows south->north, cols west->east


def masks(points: pd.DataFrame) -> dict[int, tuple[np.ndarray, np.ndarray]]:
    out = {}
    for idx, p in points.iterrows():
        li = np.where(np.abs(LATS - p.lat) <= RADIUS_KM / 111 + 0.07)[0]
        dlon = RADIUS_KM / (111 * max(np.cos(np.radians(p.lat)), 0.2)) + 0.07
        lj = np.where(np.abs(((LONS - p.lon + 180) % 360) - 180) <= dlon)[0]
        la, lo = np.meshgrid(LATS[li], LONS[lj], indexing="ij")
        d = 6371 * 2 * np.arcsin(np.sqrt(np.sin(np.radians(la - p.lat) / 2) ** 2 + np.cos(np.radians(p.lat))
                                         * np.cos(np.radians(la)) * np.sin(np.radians(lo - p.lon) / 2) ** 2))
        ii, jj = np.where(d <= RADIUS_KM)
        out[idx] = (li[ii], lj[jj])
    return out


def load_points() -> pd.DataFrame:
    pts = pd.DataFrame(POINTS, columns=["name", "iso3", "group", "lat", "lon"])
    ct = RAW_DIR / "climate_trace" / "climate_trace_heavy_industry_assets.csv"
    if ct.exists():
        a = pd.read_csv(ct)
        a = a[(a.subsector == "iron-and-steel") & a.iso3.isin(["CHN", "IND"])].dropna(subset=["lat", "lon"])
        a = a.sort_values("capacity", ascending=False).groupby("iso3").head(25)
        add = a.assign(group=lambda x: x.iso3 + " top steel plant",
                       name=lambda x: x.name.str.slice(0, 60))[["name", "iso3", "group", "lat", "lon"]]
        pts = pd.concat([pts, add], ignore_index=True)
    return pts


def main(start="2018-05") -> None:
    pts = load_points()
    pts.to_csv(OUT / "no2_points.csv", index_label="point_id")
    mk = masks(pts)
    end = (pd.Timestamp.today() - pd.DateOffset(months=1)).to_period("M")
    rows = []
    for per in pd.period_range(start, end, freq="M"):
        y, m = per.year, per.month
        dest = CACHE_DIR / "tropomi" / f"no2_{y}{m:02d}.asc.gz"
        try:
            download(URL.format(y=y, m=m), dest, source="KNMI TEMIS TROPOMI NO2", note="monthly global grid (cache)")
        except Exception as e:  # noqa: BLE001 - month not yet published
            print(f"  skip {per}: {e}")
            continue
        g = parse_grid(dest)
        for idx, (ii, jj) in mk.items():
            v = g[ii, jj]
            rows.append({"point_id": idx, "month": str(per), "no2_1e13": float(np.nanmean(v)) if np.isfinite(v).any() else np.nan,
                         "valid_cells": int(np.isfinite(v).sum()), "cells": len(v)})
        print(f"  {per}: done")
    out = pd.DataFrame(rows).merge(pts.reset_index().rename(columns={"index": "point_id"}), on="point_id")
    path = OUT / "no2_points_monthly.csv"
    out.to_csv(path, index=False)
    log_download("KNMI TEMIS TROPOMI NO2 (point extracts)", URL, path, f"{len(pts)} points, radius {RADIUS_KM} km")
    print(f"done: {out.point_id.nunique()} points x {out.month.nunique()} months")


if __name__ == "__main__":
    main()
