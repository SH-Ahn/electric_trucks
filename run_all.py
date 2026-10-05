"""Run the pipeline: collect -> build -> explore.

    python run_all.py                 # build + explore from existing raw data
    python run_all.py --collect       # also re-download every source first
    python run_all.py --only b05 e05  # run selected scripts by prefix

Collection scripts that need credentials (c14 Census: CENSUS_API_KEY) or hit API
quotas (c03 Comtrade) report and continue rather than stopping the pipeline.
"""
import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
STAGES = {"collect": ROOT / "01_collect", "build": ROOT / "02_build", "explore": ROOT / "03_explore"}


def scripts(stage: str) -> list[Path]:
    return sorted(STAGES[stage].glob("[cbe][0-9][0-9]_*.py"))


def run(path: Path) -> bool:
    print(f"\n=== {path.relative_to(ROOT)}", flush=True)
    res = subprocess.run([sys.executable, str(path)], cwd=ROOT)
    if res.returncode != 0:
        print(f"!!! {path.name} exited with code {res.returncode}", flush=True)
    return res.returncode == 0


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--collect", action="store_true", help="re-download raw data first")
    ap.add_argument("--only", nargs="*", help="script name prefixes, e.g. c01 b03 e05")
    args = ap.parse_args()
    todo = []
    for stage in ("collect", "build", "explore"):
        if stage == "collect" and not args.collect and not args.only:
            continue
        todo += scripts(stage)
    if args.only:
        todo = [p for p in todo if any(p.name.startswith(o) for o in args.only)]
    failed = [p.name for p in todo if not run(p)]
    print("\nFailed:", failed if failed else "none")


if __name__ == "__main__":
    main()
