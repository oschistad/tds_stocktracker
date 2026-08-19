# Truth Social posts → stock moves: analysis plan

Goal: quantify whether specific Truth Social posts by Donald Trump are associated with
statistically significant abnormal price moves in identifiable stocks, sectors, or ETFs.

Scope decisions (agreed): window 2025-01 → present, daily returns, prototype in the
Cowork workspace, GitHub for the data pipeline.

## Environment constraints discovered (these shaped the design)

The analysis sandbox has allowlisted network egress: GitHub (`raw.githubusercontent.com`,
repo-scoped API) and package registries are reachable; Yahoo Finance, Stooq, civictracker.us,
trumpstruth.org and ix.cnn.io are not. Therefore:

- The **GitHub repo is the data plane.** GitHub Actions runners have unrestricted network,
  so all external fetching (prices, fresh posts) runs there and commits data files to the repo.
- The **sandbox is the compute plane.** It pulls committed data via raw.githubusercontent
  and runs annotation, modeling, and reporting.

## Data status

- **Posts (done):** `stiles/trump-truth-social-archive` on GitHub provides a clean JSON
  archive. Extracted and cleaned: **5,028 posts, 2025-01-01 → 2025-10-26** (3,895 with text)
  → `posts.jsonl` (id, UTC timestamp, stripped text, url, engagement counts).
- **Post gap (Nov 2025 → present):** CNN maintains a live mirror updated every 5 minutes at
  `ix.cnn.io/data/truth-social/truth_archive.json` — unreachable from the sandbox, trivially
  fetchable from an Actions runner.
- **Prices (pending GitHub):** daily OHLCV via yfinance in an Actions job; needs the ticker
  list from the annotation phase first. Fetch from 2024-07 onward (extra history for beta
  estimation). Benchmark: SPY; sector ETFs (XLF, XLE, XLV, XLI, XLK, ITA, IBIT, …) for
  posts that target sectors/themes rather than single companies.

## Task breakdown (by who does the work)

### T2 — Post annotation — *cheap LLM agents (Haiku-class), batched*
1. Rule-based prefilter (regex/keyword, no LLM): company names, tickers, cashtags, and
   market-relevant themes (tariff, Fed, rates, drugs/pharma, chips, crypto, autos, defense,
   trade deal, specific CEOs). Cuts ~3,900 text posts to a few hundred candidates.
2. Batched classification by small agents, strict JSON output per post:
   `{market_relevant: bool, entities: [{name, ticker|null}], sector_etfs: [], direction:
   positive|negative|ambiguous, theme, confidence}`. Rubric + few-shot examples in the
   prompt; each agent gets ~50 posts and needs no other context — ideal for delegation.
3. QA: a verifier agent re-classifies a random 5% sample; disagreement rate reported.
   Entity→ticker resolution table reviewed once (deterministic lookup, not per-post LLM).

### T7 — GitHub data pipeline — *user + one scripted setup pass*
- User creates a repo and connects it to the session (`add_repo`, push access).
- Commit: ingestion scripts, `posts.jsonl`, annotation outputs.
- Actions workflow 1: fetch CNN truth archive, dedupe, commit (fills post gap; hourly cron).
- Actions workflow 2: given `tickers.txt` from T2, fetch daily OHLCV via yfinance, commit
  parquet (daily cron).

### T4 — Event-study model — *deterministic code, no LLM judgment*
- Alignment: post before 16:00 ET on a trading day → same-day close-to-close return
  (t=0); after hours/weekend → next trading day. All timestamps UTC → America/New_York.
- Abnormal return: market model `r_i = α + β·r_SPY + ε`, β estimated on trading days
  −140…−20 relative to event; AR = actual − predicted. CARs over windows [0], [0,+1],
  [0,+3]; pre-window [−3,−1] measured separately for reverse-causality screening.
- Inference: per-event standardized ARs; per-ticker and per-theme aggregation with
  t-tests; **placebo bootstrap** (same tickers, random non-event dates, 10k draws) as the
  primary significance yardstick; Benjamini–Hochberg FDR across all hypotheses.
- Direction test: does signed AR match the annotated post direction more often than chance?
- Overlap handling: cluster same-ticker posts <2 trading days apart into single events.

### T5 — Report — *one pass, dataviz skill*
- Ranked table of strongest post→move associations (ticker, date, post excerpt, CAR, p, FDR).
- Aggregate results by theme (tariffs, Fed, pharma, crypto, …) and direction-match rate.
- CAR event-time plots; methodology appendix. HTML report.

### T6 — Verification — *mixed: one script + a few web-search agents*
- Recompute a sample of ARs independently (different code path) to catch math bugs.
- For the top ~10 findings, web-search the news record: did public news precede the post
  (reaction, not cause)? Findings that fail this check get flagged, not dropped silently.

## Honest limitations
- Daily bars cannot prove intra-day causality; this measures association at daily
  resolution with a reverse-causality screen, not tick-level causation.
- Posts often coincide with official actions (executive orders, announcements) — attribution
  is to the event, the post is the timestamp proxy.
- Multiple-testing correction is essential: ~hundreds of hypotheses will produce spurious
  hits without it (hence placebo bootstrap + FDR).

## Cost profile
T1 done. T3/T4/T5 are scripts (≈ zero LLM cost). T2 is the only token-heavy phase and is
delegated to small agents (~few hundred posts × small prompt). T6 uses a handful of
search agents.
