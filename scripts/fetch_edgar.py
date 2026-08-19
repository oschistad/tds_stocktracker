"""Fetch candidate infra announcements from SEC EDGAR full-text search.

Runs in GitHub Actions. Searches 8-K filings for high-signal phrases, filters by
infra SIC codes, downloads a text snippet of each filing, and writes
data/infra_events_raw.jsonl.

SEC fair-access rules: identify via User-Agent, stay under ~8 req/s.
"""
import json
import re
import time
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
UA = {"User-Agent": "tds_stocktracker research (oschistad@gmail.com)"}
FTS = "https://efts.sec.gov/LATEST/search-index"

QUERIES = ['"design win"', '"design wins"', '"multi-year supply agreement"',
           '"volume production"', '"general availability"', '"supply agreement"',
           '"master services agreement"', '"purchase agreement" "data center"',
           '"contract award"', '"long-term agreement"']

# Infra-relevant SIC codes: computers/storage/networking, comms equipment,
# semis & components, power electronics, software/IT services
SIC_OK = {
    "3571", "3572", "3575", "3576", "3577", "3578", "3579",
    "3661", "3663", "3669", "3670", "3672", "3674", "3675", "3677", "3678", "3679",
    "3612", "3613", "3621", "3629", "3825", "3827",
    "7371", "7372", "7373", "7374", "7379",
}

START, END = "2019-01-01", "2025-08-31"
MAX_SNIPPET = 4000

session = requests.Session()
session.headers.update(UA)

def get(url, **kw):
    for attempt in range(4):
        r = session.get(url, timeout=60, **kw)
        if r.status_code == 429:
            time.sleep(3 * (attempt + 1)); continue
        r.raise_for_status()
        time.sleep(0.13)
        return r
    raise RuntimeError(f"rate-limited: {url}")

def date_windows():
    """FTS caps results at 10k per query; slice by quarter to stay under it."""
    ys, ye = int(START[:4]), int(END[:4])
    for y in range(ys, ye + 1):
        for q, (a, b) in enumerate([("01-01", "03-31"), ("04-01", "06-30"),
                                    ("07-01", "09-30"), ("10-01", "12-31")]):
            lo, hi = f"{y}-{a}", f"{y}-{b}"
            if hi < START or lo > END:
                continue
            yield max(lo, START), min(hi, END)

def search():
    hits = {}
    for q in QUERIES:
        for lo, hi in date_windows():
            frm = 0
            while True:
                r = get(FTS, params={"q": q, "forms": "8-K", "startdt": lo,
                                     "enddt": hi, "from": frm})
                d = r.json()
                batch = d.get("hits", {}).get("hits", [])
                for h in batch:
                    s = h["_source"]
                    adsh = s["adsh"]
                    if adsh in hits:
                        hits[adsh]["queries"].append(q)
                        continue
                    names = s.get("display_names", [])
                    m = re.search(r"\(([A-Z.\-]{1,6})\)\s+\(CIK (\d+)\)", names[0]) if names else None
                    hits[adsh] = {
                        "adsh": adsh,
                        "cik": s.get("cik") or (m.group(2) if m else None),
                        "name": re.sub(r"\s*\(.*", "", names[0]) if names else None,
                        "ticker": m.group(1) if m else None,
                        "file_date": s.get("file_date"),
                        "file_id": h.get("_id", ""),
                        "queries": [q],
                    }
                frm += len(batch)
                total = d.get("hits", {}).get("total", {}).get("value", 0)
                if not batch or frm >= min(total, 9990):
                    break
        print(f"{q}: cumulative unique filings {len(hits)}", flush=True)
    return list(hits.values())

_sic_cache = {}
def sic_for(cik):
    cik10 = str(cik).zfill(10)
    if cik10 not in _sic_cache:
        try:
            d = get(f"https://data.sec.gov/submissions/CIK{cik10}.json").json()
            _sic_cache[cik10] = (d.get("sic", ""), d.get("sicDescription", ""),
                                 (d.get("tickers") or [None])[0])
        except Exception:
            _sic_cache[cik10] = ("", "", None)
    return _sic_cache[cik10]

def snippet(ev):
    """Fetch the matched document's text, stripped and truncated."""
    doc = ev["file_id"].split(":", 1)[-1] if ":" in ev["file_id"] else None
    acc = ev["adsh"].replace("-", "")
    if not doc:
        return None
    url = f"https://www.sec.gov/Archives/edgar/data/{int(ev['cik'])}/{acc}/{doc}"
    try:
        t = get(url).text
    except Exception:
        return None
    t = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", t, flags=re.S | re.I)
    t = re.sub(r"<[^>]+>", " ", t)
    t = re.sub(r"&[a-z#0-9]+;", " ", t)
    t = re.sub(r"\s+", " ", t).strip()
    return t[:MAX_SNIPPET] or None

def main():
    events = search()
    print(f"total unique candidate filings: {len(events)}", flush=True)
    kept = []
    for i, ev in enumerate(events):
        if not ev["cik"]:
            continue
        sic, sic_desc, ticker2 = sic_for(ev["cik"])
        if sic not in SIC_OK:
            continue
        ev["sic"], ev["sic_desc"] = sic, sic_desc
        ev["ticker"] = ev["ticker"] or ticker2
        ev["text"] = snippet(ev)
        if ev.pop("file_id", None) is None:
            pass
        if ev["text"]:
            kept.append(ev)
        if i % 500 == 0:
            print(f"  processed {i}/{len(events)}, kept {len(kept)}", flush=True)
    (ROOT / "data").mkdir(exist_ok=True)
    with open(ROOT / "data" / "infra_events_raw.jsonl", "w") as f:
        for ev in kept:
            f.write(json.dumps(ev, ensure_ascii=False) + "\n")
    print(f"wrote {len(kept)} infra events "
          f"({len(set(e['ticker'] for e in kept if e['ticker']))} tickers)")

if __name__ == "__main__":
    main()
