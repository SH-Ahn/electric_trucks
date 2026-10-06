"""China's catalogues of new-energy vehicle models exempt from (2017-2023) or eligible for reduced
(2024 onward) vehicle purchase tax (MIIT and State Taxation Administration; no key):
免征 / 减免车辆购置税的新能源汽车车型目录. Each batch lists every approved model by powertrain
(battery-electric, plug-in hybrid, fuel cell) and vehicle class (passenger car, bus, truck,
special-purpose vehicle) with manufacturer, model code, common name and, for battery-electric
models, driving range, curb mass, battery mass and battery energy (kWh).

This is a model-level census of Chinese electric trucks and buses entering the market, with
entry dates (batch publication) and attributes, for the supply side (RQ4, RQ5) and attributes.

Batch pages are found through the MIIT site search API; the attachments (Word .doc) are converted
with macOS textutil and the tables parsed from Word's cell markers.

Output: 03_data/01_raw/china_miit/miit_nev_tax_catalogue_models.csv (one row per model x batch)
"""
import json
import re
import subprocess
import sys
import time
import urllib.parse
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from config import CACHE_DIR, RAW_DIR  # noqa: E402
from helpers import SESSION, log_download  # noqa: E402

SITE = "https://www.miit.gov.cn"
SEARCH = (SITE + "/search-front-server/api/search/info?websiteid=110000000000000&scope=basic&q={q}&pg=20&cateid="
          "&pos=title_text&dateField=deploytime&selectFields=title,url,deploytime&group=distinct&p={p}&sortFields=")
UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/126.0 Safari/537.36", "Referer": SITE + "/search/index.html"}
QUERIES = {"exemption": "免征车辆购置税的新能源汽车车型目录", "reduction": "减免车辆购置税的新能源汽车车型目录"}
CN = {"零": 0, "一": 1, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7, "八": 8, "九": 9}
POWERTRAIN = {"纯电动": "BEV", "插电式混合动力": "PHEV", "燃料电池": "FCEV"}
CLASS = {"乘用车": "passenger_car", "客车": "bus", "货车": "truck", "专用车": "special_purpose"}
CACHE = CACHE_DIR / "china_miit"
OUT = RAW_DIR / "china_miit"


def cn_number(s: str) -> int | None:
    """Chinese numerals up to 999 (e.g. 七十三 -> 73)."""
    if s.isdigit():
        return int(s)
    total, cur = 0, 0
    for ch in s:
        if ch in CN:
            cur = CN[ch]
        elif ch == "十":
            total += (cur or 1) * 10
            cur = 0
        elif ch == "百":
            total += (cur or 1) * 100
            cur = 0
    total += cur
    return total or None


def batch_pages() -> dict[tuple[str, int], tuple[list[str], str]]:
    """(catalogue, batch number) -> (candidate page URLs, publication date)."""
    out = {}
    for cat, q in QUERIES.items():
        for p in range(1, 40):
            r = SESSION.get(SEARCH.format(q=urllib.parse.quote(q), p=p), headers=UA, timeout=60).json()
            res = r["data"]["searchResult"]["dataResults"]
            if not res:
                break
            for g in res:
                for x in (g.get("groupData") or [g]):
                    d = x.get("data") or {}
                    title, url = d.get("title", ""), d.get("url", "")
                    m = re.search(rf"{q}》?（第([一二三四五六七八九十百零\d]+)批）", title)
                    if not (m and url):
                        continue
                    key = (cat, cn_number(m.group(1)))
                    date = pd.to_datetime(int(d.get("deploytime", 0)), unit="ms").strftime("%Y-%m-%d")
                    urls, first = out.get(key, ([], date))
                    out[key] = (urls + [url], min(first, date))
            time.sleep(0.3)
    return out


def attachment(page_urls: list[str], cat: str) -> str | None:
    word = "免征" if cat == "exemption" else "减免"
    for page_url in page_urls:
        url = page_url.replace("http://", "https://") if page_url.startswith("http") else SITE + page_url
        try:
            html = SESSION.get(url, headers=UA, timeout=60).text
        except Exception:  # noqa: BLE001 - mirror pages are sometimes unreachable
            continue
        for href, text in re.findall(r'href="([^"]+\.(?:doc|docx|wps))"[^>]*>([^<]*)', html):
            if word in text and "购置税" in text:
                return href if href.startswith("http") else SITE + href
        time.sleep(0.3)
    return None


def parse(txt: str) -> list[dict]:
    rows, pt, cls = [], None, None
    blocks = re.split(r"\n", txt)
    for line in blocks:
        s = line.strip()
        if not s:
            continue
        if "\x07" not in s:
            bare = re.sub(r"^[（(]?[一二三四五六七八九十]+[）)、．.]?\s*", "", s)
            for k, v in POWERTRAIN.items():
                if re.search(rf"[一二三四五六七八九十]、{k}", s) or bare in (k, k + "汽车"):
                    pt = v
            for k, v in CLASS.items():
                if re.search(rf"（[一二三四五六七八九十]+）{k}", s) or bare == k:
                    cls = v
            continue
        tokens = s.split("\x07")
        try:
            ncol = tokens.index("")
        except ValueError:
            continue
        header = [t.strip().replace("（", "(").replace("）", ")").replace(" ", "") for t in tokens[:ncol]]
        if not header or header[0] != "序号":
            continue
        body = tokens[ncol + 1:]
        last_firm = None
        for i in range(0, len(body) - ncol + 1, ncol + 1):
            cells = [c.strip() for c in body[i:i + ncol]]
            if len(cells) < ncol or not any(cells[1:]):
                continue
            rec = dict(zip(header, cells))
            firm = rec.get("汽车生产企业名称") or rec.get("生产企业名称") or rec.get("企业名称") or ""
            if firm:
                last_firm = firm
            rec["firm"] = firm or last_firm
            rec["powertrain"], rec["vehicle_class"] = pt, cls
            rows.append(rec)
    return rows


MODEL = re.compile(r"[A-Z0-9][A-Za-z0-9\-./()]{4,}")


def parse_html(html: str) -> list[dict]:
    """Newer batch files: cells are separated by empty <span> tags and empty or merged cells
    (serial number, remark, repeated manufacturer) are dropped, so rows are rebuilt from the
    header: a token naming a company starts a new manufacturer, a model code starts a row."""
    rows, pt, cls = [], None, None
    for para in re.findall(r"<p[^>]*>(.*?)</p>", html, re.S):
        text = re.sub(r"<[^>]+>", "", para).strip()
        if "序号" not in text:
            for k, v in POWERTRAIN.items():
                if re.search(rf"[一二三四五六七八九十]、{k}", text):
                    pt = v
            for k, v in CLASS.items():
                if re.search(rf"（[一二三四五六七八九十]+）{k}", text):
                    cls = v
            continue
        toks = [re.sub(r"<[^>]+>", "", t).strip() for t in re.split(r'<span class="s\d+"></span>', para)]
        toks = [t for t in toks if t]
        if "备注" not in toks:
            continue
        k = toks.index("备注")
        header = [t.replace("（", "(").replace("）", ")") for t in toks[:k + 1]]
        cols = [c for c in header if c not in ("序号", "备注")]
        firm_col, rest = cols[0], cols[1:]
        body, i, firm = toks[k + 1:], 0, None
        while i < len(body):
            t = body[i]
            if "公司" in t or t.endswith("集团"):
                firm, i = t, i + 1
                continue
            cells = body[i:i + len(rest)]
            if len(cells) == len(rest) and MODEL.fullmatch(cells[0]) and re.search(r"\d", cells[0]):
                rec = dict(zip(rest, cells))
                rec[firm_col], rec["firm"], rec["powertrain"], rec["vehicle_class"] = firm, firm, pt, cls
                rows.append(rec)
                i += len(rest)
            else:
                i += 1
    return rows


def main() -> None:
    CACHE.mkdir(parents=True, exist_ok=True)
    OUT.mkdir(parents=True, exist_ok=True)
    pages = batch_pages()
    print(f"{len(pages)} catalogue batches found")
    frames = []
    for (cat, n), (urls, date) in sorted(pages.items()):
        doc = CACHE / f"{cat}_{n:03d}.doc"
        if not doc.exists():
            href = attachment(urls, cat)
            if not href:
                print(f"  no Word attachment: {cat} batch {n}")
                continue
            doc.write_bytes(SESSION.get(href, headers=UA, timeout=120).content)
            time.sleep(0.5)
        txt = doc.with_suffix(".txt")
        if not txt.exists():
            subprocess.run(["textutil", "-convert", "txt", str(doc), "-output", str(txt)], capture_output=True)
        if not txt.exists():
            print(f"  conversion failed: {doc.name}")
            continue
        raw = txt.read_text(errors="ignore")
        rows = parse(raw)
        if not rows or "\x07" not in raw:
            html = doc.with_suffix(".html")
            if not html.exists():
                subprocess.run(["textutil", "-convert", "html", str(doc), "-output", str(html)], capture_output=True)
            rows = parse_html(html.read_text(errors="ignore")) if html.exists() else rows
        if rows:
            d = pd.DataFrame(rows)
            d.insert(0, "published", date)
            d.insert(0, "batch", n)
            d.insert(0, "catalogue", cat)
            frames.append(d)
    d = pd.concat(frames, ignore_index=True)
    ren = {"车辆型号": "model_code", "通用名称": "common_name", "纯电动续驶里程(km)": "range_km",
           "整车整备质量(kg)": "curb_mass_kg", "动力蓄电池组总质量(kg)": "battery_mass_kg",
           "动力蓄电池组总能量(kWh)": "battery_kwh", "备注": "remark", "产品名称": "product_name",
           "燃料电池系统额定功率(kW)": "fuel_cell_kw", "驱动电机额定功率(kW)": "motor_kw",
           "燃料消耗量(L/100km)": "fuel_l_100km", "发动机排量(mL)": "engine_ml"}
    d = d.rename(columns=ren)
    keep = ["catalogue", "batch", "published", "powertrain", "vehicle_class", "firm", "model_code", "common_name",
            "product_name", "range_km", "curb_mass_kg", "battery_mass_kg", "battery_kwh", "remark"]
    keep = [c for c in keep if c in d.columns]
    other = [c for c in d.columns if c not in keep and c not in ("序号", "汽车生产企业名称")]
    d = d[keep + other]
    path = OUT / "miit_nev_tax_catalogue_models.csv"
    d.to_csv(path, index=False)
    log_download("MIIT NEV purchase-tax catalogues (parsed)", SITE, path,
                 f"{d.batch.nunique()} batches; {len(d):,} model entries")
    print(f"MIIT: {len(d):,} model entries; {d.groupby(['powertrain', 'vehicle_class']).size().to_dict()}")


if __name__ == "__main__":
    main()
