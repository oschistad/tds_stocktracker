# Handoff / continuation notes

Project: event study of Trump Truth Social posts vs. stock moves.
Full methodology and task breakdown: see PLAN.md. Annotation rules: rubric.md.

## State of play (as of 2026-08-19)

Done:
- Ingestion: posts.jsonl — 5,028 cleaned posts, 2025-01-01 → 2025-10-26
  (source: raw.githubusercontent.com/stiles/trump-truth-social-archive/main/data/truth_archive.json)
- Annotation: annotations_final.json / events.jsonl — 439 market-relevant events
  (Haiku prefilter+classify, Sonnet refinement of entities+direction; QA agreement:
  relevance 86%, theme 81%; direction was 58% pre-refinement, hence the Sonnet pass)
- tickers.txt — 58 instruments (46 company tickers + SPY/TLT/sector ETFs/BTC)
- scripts/fetch_prices.py + scripts/fetch_posts.py + .github/workflows/data.yml

Not yet done:
1. Push this folder to a GitHub repo (public repo lets the Cowork cloud session
   read data files via raw.githubusercontent.com without any GitHub integration).
2. Enable Actions and run the "fetch-data" workflow (manual dispatch works) →
   commits data/prices.parquet and data/truth_archive.json.
3. Event-study model (PLAN.md § T4): market-model abnormal returns, event alignment
   (post <16:00 ET on trading day → t=0 same day, else next trading day; timestamps
   are UTC in created_at), CARs [0], [0,+1], [0,+3], pre-window [-3,-1] drift screen,
   placebo bootstrap (10k draws), Benjamini-Hochberg FDR, direction-match test,
   cluster same-ticker events <2 trading days apart.
4. Report with charts; verify top-10 findings against the news record.
5. Optional: annotate the Nov 2025 → present post gap once fetch_posts.py fills it
   (re-run the rubric pipeline on new posts).

## File formats
- posts.jsonl: {id, created_at (UTC ISO), text, url, has_media, reblogs, favs}
- events.jsonl: {id, created_at, text, url, theme, direction, confidence,
  entity_tickers[], entity_names[], theme_instruments[]}
- tickers.txt: one symbol per line (yfinance-compatible)
