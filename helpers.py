"""Shared helpers: polite HTTP downloads with retries and a provenance log."""
from __future__ import annotations

import csv
import datetime as dt
import subprocess
import time
from pathlib import Path

import requests

from config import RAW_DIR

USER_AGENT = "electric-trucks-research/0.1 (academic research; github.com/SH-Ahn/electric_trucks)"
SESSION = requests.Session()
SESSION.headers.update({"User-Agent": USER_AGENT})

LOG_PATH = RAW_DIR / "_download_log.csv"


def log_download(source: str, url: str, path: Path, note: str = "") -> None:
    """Append one row to the raw-data provenance log (03_data/01_raw/_download_log.csv)."""
    new = not LOG_PATH.exists()
    with LOG_PATH.open("a", newline="") as f:
        w = csv.writer(f)
        if new:
            w.writerow(["accessed_utc", "source", "url", "path", "bytes", "note"])
        size = path.stat().st_size if path.exists() else ""
        rel = path.relative_to(RAW_DIR.parent) if path.is_relative_to(RAW_DIR.parent) else path
        w.writerow([dt.datetime.now(dt.UTC).strftime("%Y-%m-%d %H:%M"), source, url, rel, size, note])


def get(url: str, *, params: dict | None = None, headers: dict | None = None,
        retries: int = 4, timeout: int = 120, pause: float = 0.0) -> requests.Response:
    """GET with exponential back-off on network errors, 429 and 5xx."""
    for attempt in range(retries):
        try:
            r = SESSION.get(url, params=params, headers=headers, timeout=timeout)
            if r.status_code == 429 or r.status_code >= 500:
                raise requests.HTTPError(f"HTTP {r.status_code}", response=r)
            r.raise_for_status()
            if pause:
                time.sleep(pause)
            return r
        except (requests.ConnectionError, requests.Timeout, requests.HTTPError) as e:
            status = getattr(getattr(e, "response", None), "status_code", None)
            if status is not None and 400 <= status < 500 and status != 429:
                raise
            if attempt == retries - 1:
                raise
            time.sleep(2 ** attempt * 3)
    raise RuntimeError("unreachable")


def _curl(url: str, tmp: Path, headers: dict | None, timeout: int) -> bool:
    """Resumable curl transfer into ``tmp``; True on success."""
    cmd = ["curl", "-sSfL", "-g", "--retry", "5", "--retry-delay", "10", "-C", "-",
           "--max-time", str(timeout), "-o", str(tmp), url]
    for k, v in (headers or {"User-Agent": USER_AGENT}).items():
        cmd[1:1] = ["-H", f"{k}: {v}"]
    return subprocess.run(cmd).returncode == 0


def download(url: str, dest: Path, *, source: str, params: dict | None = None,
             headers: dict | None = None, overwrite: bool = False, note: str = "",
             timeout: int = 600) -> Path:
    """Stream ``url`` to ``dest`` (skipped if it exists unless ``overwrite``) and log it."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists() and not overwrite:
        return dest
    tmp = dest.with_suffix(dest.suffix + ".part")
    for attempt in range(8):
        try:
            done = tmp.stat().st_size if tmp.exists() else 0
            hdr = dict(headers or {})
            if done:
                hdr["Range"] = f"bytes={done}-"  # resume a partial transfer
            with SESSION.get(url, params=params, headers=hdr, stream=True, timeout=timeout) as r:
                r.raise_for_status()
                mode = "ab" if done and r.status_code == 206 else "wb"
                with tmp.open(mode) as f:
                    for chunk in r.iter_content(chunk_size=1 << 20):
                        f.write(chunk)
            break
        except (requests.ConnectionError, requests.Timeout, requests.exceptions.ChunkedEncodingError):
            if attempt >= 2 and not params and _curl(url, tmp, headers, timeout):
                break  # some servers (e.g. ORNL) reset Python's TLS handshake but accept curl
            if attempt == 7:
                raise
            time.sleep(min(2 ** attempt * 3, 60))
    tmp.replace(dest)
    log_download(source, url if not params else f"{url}?{requests.compat.urlencode(params)}", dest, note)
    return dest
