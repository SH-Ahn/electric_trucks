"""Country-code helpers shared by the build scripts.

Maps the country names used by IEA, Ember and others to ISO3, and M49 numeric
codes (BACI, Comtrade) to ISO3, using the World Bank and BACI code lists in
03_data/01_raw. Regional aggregates return None.
"""
from __future__ import annotations

from functools import lru_cache

import pandas as pd

from config import RAW_DIR

EU27 = ["AUT", "BEL", "BGR", "HRV", "CYP", "CZE", "DNK", "EST", "FIN", "FRA", "DEU", "GRC",
        "HUN", "IRL", "ITA", "LVA", "LTU", "LUX", "MLT", "NLD", "POL", "PRT", "ROU", "SVK",
        "SVN", "ESP", "SWE"]

# Names whose spelling differs from the World Bank list.
_MANUAL = {
    "USA": "USA", "United States": "USA", "Korea": "KOR", "South Korea": "KOR",
    "Turkiye": "TUR", "Turkey": "TUR", "Viet Nam": "VNM", "Vietnam": "VNM", "Lao PDR": "LAO",
    "Czech Republic": "CZE", "Czechia": "CZE", "Russia": "RUS", "Slovakia": "SVK",
    "Egypt": "EGY", "Iran": "IRN", "Hong Kong": "HKG", "Taiwan": "TWN", "Chinese Taipei": "TWN",
    "Kyrgyzstan": "KGZ", "Venezuela": "VEN", "Yemen": "YEM", "Gambia": "GMB", "Bahamas": "BHS",
    "Congo": "COG", "DR Congo": "COD", "Democratic Republic of the Congo": "COD",
    "Cote d'Ivoire": "CIV", "Ivory Coast": "CIV", "Macedonia": "MKD", "North Macedonia": "MKD",
    "Syria": "SYR", "Micronesia": "FSM", "Saint Lucia": "LCA", "Moldova": "MDA",
    "Bosnia Herzegovina": "BIH", "Bosnia and Herzegovina": "BIH", "Brunei": "BRN",
    "Cape Verde": "CPV", "Swaziland": "SWZ", "Eswatini": "SWZ", "Kosovo": "XKX",
    "United Kingdom": "GBR", "UK": "GBR", "Great Britain": "GBR",
}

# BACI/Comtrade report Taiwan as 490 "Other Asia, nes" (ISO3 placeholder S19).
_M49_EXTRA = {490: "TWN"}

# Eurostat geo codes (ISO2 except EL = Greece, UK = United Kingdom, EU aggregates).
EUROSTAT_GEO = {
    "AT": "AUT", "BE": "BEL", "BG": "BGR", "CY": "CYP", "CZ": "CZE", "DE": "DEU", "DK": "DNK",
    "EE": "EST", "EL": "GRC", "ES": "ESP", "FI": "FIN", "FR": "FRA", "HR": "HRV", "HU": "HUN",
    "IE": "IRL", "IT": "ITA", "LT": "LTU", "LU": "LUX", "LV": "LVA", "MT": "MLT", "NL": "NLD",
    "PL": "POL", "PT": "PRT", "RO": "ROU", "SE": "SWE", "SI": "SVN", "SK": "SVK", "UK": "GBR",
    "NO": "NOR", "IS": "ISL", "LI": "LIE", "CH": "CHE", "TR": "TUR", "RS": "SRB", "ME": "MNE",
    "MK": "MKD", "AL": "ALB", "BA": "BIH", "XK": "XKX", "UA": "UKR", "MD": "MDA", "GE": "GEO",
    "EU27_2020": "EU27",
}


@lru_cache(maxsize=1)
def _wb_names() -> dict[str, str]:
    meta = pd.read_csv(RAW_DIR / "worldbank" / "wdi_countries.csv")
    meta = meta[~meta["is_aggregate"]]
    return dict(zip(meta["name"], meta["iso3"]))


def iso3_from_name(name: str) -> str | None:
    """Return ISO3 for a country name, or None for regions/aggregates."""
    if not isinstance(name, str):
        return None
    name = name.strip()
    if name in _MANUAL:
        return _MANUAL[name]
    return _wb_names().get(name)


@lru_cache(maxsize=1)
def _m49_table() -> dict[int, str]:
    p = RAW_DIR / "baci" / "country_codes_V202601.csv"
    d = pd.read_csv(p)
    m = dict(zip(d["country_code"].astype(int), d["country_iso3"]))
    m.update(_M49_EXTRA)
    return m


def iso3_from_m49(code) -> str | None:
    try:
        return _m49_table().get(int(code))
    except (TypeError, ValueError):
        return None


def region_of(iso3: str) -> str:
    """Coarse world region used in figures (China, Europe, North America, other blocs)."""
    if iso3 == "CHN":
        return "China"
    if iso3 in EU27 or iso3 in {"GBR", "NOR", "CHE", "ISL", "LIE"}:
        return "Europe"
    if iso3 in {"USA", "CAN"}:
        return "US & Canada"
    if iso3 in {"MEX", "BRA", "CHL", "COL", "ARG", "PER", "URY", "CRI", "ECU", "DOM", "PAN", "GTM"}:
        return "Latin America"
    if iso3 in {"IND", "PAK", "BGD", "LKA", "NPL"}:
        return "South Asia"
    if iso3 in {"THA", "VNM", "IDN", "PHL", "MYS", "SGP", "KHM", "LAO", "MMR"}:
        return "Southeast Asia"
    if iso3 in {"AUS", "NZL"}:
        return "Australasia"
    return "Rest of world"
