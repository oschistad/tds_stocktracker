"""Fetch the live Truth Social archive mirror (CNN) and merge into data/truth_archive.json.

Runs in GitHub Actions (unrestricted network). Fills the gap after Oct 2025 in the
stiles/trump-truth-social-archive dataset and keeps the archive current.
"""
import json
import sys
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
URL = "https://ix.cnn.io/data/truth-social/truth_archive.json"

def main() -> int:
    dest = ROOT / "data" / "truth_archive.json"
    existing = {}
    if dest.exists():
        for p in json.loads(dest.read_text()):
            existing[p["id"]] = p

    r = requests.get(URL, timeout=120)
    r.raise_for_status()
    fresh = r.json()
    added = 0
    for p in fresh:
        if p["id"] not in existing:
            added += 1
        existing[p["id"]] = p  # fresh copy wins (updated engagement counts)

    merged = sorted(existing.values(), key=lambda p: p.get("created_at", ""))
    dest.parent.mkdir(exist_ok=True)
    dest.write_text(json.dumps(merged, ensure_ascii=False))
    ts = [p["created_at"] for p in merged if p.get("created_at")]
    print(f"{len(merged)} posts total, {added} new; range {ts[0][:10]} -> {ts[-1][:10]}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
