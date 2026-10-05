"""Project paths and shared constants.

The git repository is ``02_code/``. Data, outputs, documentation and references
live in sibling folders of the Dropbox project root and are not version-controlled:

    electric_trucks/
    ├── 01_project_documentation/
    ├── 02_code/            <- this repository
    ├── 03_data/
    │   ├── 01_raw/         <- untouched downloads, one folder per source
    │   ├── 02_processed/   <- tidy panels built by 02_build/
    │   └── 03_purchased/   <- licensed truck & bus sales data (when it arrives)
    ├── 04_output/{01_figure,02_table}/
    └── 05_reference/

Issue branches are checked out as git worktrees under ``06_issues/<issue>/``, so the
project root is found by searching upward for ``03_data/``. Set ``ET_PROJECT_ROOT`` to
run the code from a clone outside the Dropbox folder.
"""
from __future__ import annotations

import os
from pathlib import Path

CODE_DIR = Path(__file__).resolve().parent


def _find_root() -> Path:
    if os.environ.get("ET_PROJECT_ROOT"):
        return Path(os.environ["ET_PROJECT_ROOT"])
    for d in CODE_DIR.parents:
        if (d / "03_data").is_dir():
            return d
    return CODE_DIR.parent


PROJECT_ROOT = _find_root()

DOC_DIR = PROJECT_ROOT / "01_project_documentation"
DATA_DIR = PROJECT_ROOT / "03_data"
RAW_DIR = DATA_DIR / "01_raw"
PROC_DIR = DATA_DIR / "02_processed"
PURCHASED_DIR = DATA_DIR / "03_purchased"
OUT_DIR = PROJECT_ROOT / "04_output"
FIG_DIR = OUT_DIR / "01_figure"
TAB_DIR = OUT_DIR / "02_table"
REF_DIR = PROJECT_ROOT / "05_reference"

# Multi-GB downloads (BACI zips) are cached outside Dropbox; only filtered
# extracts are written to RAW_DIR.
CACHE_DIR = Path(os.environ.get("ET_CACHE", Path.home() / ".cache" / "electric_trucks"))

# Optional API keys, read from the environment (never hard-code them).
CENSUS_API_KEY = os.environ.get("CENSUS_API_KEY")  # https://api.census.gov/data/key_signup.html
NREL_API_KEY = os.environ.get("NREL_API_KEY", "DEMO_KEY")  # https://developer.nrel.gov/signup/
COMTRADE_API_KEY = os.environ.get("COMTRADE_API_KEY")  # https://comtradedeveloper.un.org/

# Sample window shared by most panels.
START_YEAR = 2010
END_YEAR = 2026

for _d in (RAW_DIR, PROC_DIR, PURCHASED_DIR, FIG_DIR, TAB_DIR, CACHE_DIR):
    _d.mkdir(parents=True, exist_ok=True)
