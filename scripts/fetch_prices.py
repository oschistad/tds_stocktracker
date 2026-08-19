"""Fetch daily OHLCV for all instruments in tickers.txt via yfinance.

Runs in GitHub Actions (unrestricted network). Writes data/prices.parquet
(long format: date, ticker, open, high, low, close, adj_close, volume).
"""
import sys
from pathlib import Path

import pandas as pd
import yfinance as yf

ROOT = Path(__file__).resolve().parents[1]
START = "2024-07-01"

def main() -> int:
    tickers = [t.strip() for t in (ROOT / "tickers.txt").read_text().splitlines() if t.strip()]
    print(f"fetching {len(tickers)} instruments from {START}")
    df = yf.download(tickers, start=START, auto_adjust=False, group_by="ticker", threads=True)
    frames = []
    for t in tickers:
        if t not in df.columns.get_level_values(0):
            print(f"WARN: no data for {t}")
            continue
        sub = df[t].dropna(how="all").reset_index()
        sub.columns = [c.lower().replace(" ", "_") for c in sub.columns]
        sub["ticker"] = t
        frames.append(sub)
    out = pd.concat(frames, ignore_index=True)
    out["date"] = pd.to_datetime(out["date"]).dt.date
    (ROOT / "data").mkdir(exist_ok=True)
    out.to_parquet(ROOT / "data" / "prices.parquet", index=False)
    print(f"wrote {len(out)} rows, {out['ticker'].nunique()} tickers, "
          f"{out['date'].min()} -> {out['date'].max()}")
    missing = set(tickers) - set(out["ticker"].unique())
    if missing:
        print(f"MISSING: {sorted(missing)}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
