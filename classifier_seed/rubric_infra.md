# Classification rubric: infra company 8-K announcements

You are annotating SEC 8-K filing excerpts from IT-infrastructure companies (semis,
networking, hardware, software) for a long-horizon event study. The question the study
asks: do SUBSTANTIVE business announcements predict stock drift over the following
3–12 months? Your job: grade the substance of each filing excerpt.

Read the input file (JSONL: adsh, ticker, name, date, text). Classify EVERY entry.
Write the output file. The text is a raw stripped excerpt — it may contain boilerplate,
legal headers, or be a fragment; judge from what's there.

## Fields per entry
- `adsh`: copy from input.
- `kind`: one of
  - `design_win` — a NEW design win / product selected into a customer's product or platform
  - `revenue_contract` — signed contract, purchase order, or supply agreement with revenue implications
  - `product_launch` — new product general availability / volume production milestone
  - `capacity` — new fab/factory/datacenter capacity, major capex commitment
  - `partnership` — collaboration/alliance/MoU without committed revenue
  - `financing` — securities purchase agreement, notes, equity raise, ATM (these match "purchase agreement" spuriously)
  - `earnings` — quarterly/annual results release (if the prefilter missed it)
  - `other` — anything else (governance, personnel, legal, etc.)
- `substantive`: boolean. TRUE only if the filing announces NEW committed business or a
  concrete commercial milestone: a named or clearly described customer/counterparty, a
  signed agreement, a shipping/production milestone. FALSE for: aspirational language,
  "we continue to see strong design win momentum", partnerships without commitment,
  financings, earnings, boilerplate.
- `named_counterparty`: boolean — is a specific customer/partner identified (by name, or
  unambiguous description like "a top-3 hyperscaler")?
- `quantified`: boolean — is a value/volume/duration stated (dollar amount, unit volume,
  multi-year term)?
- `direction`: `positive` (good news for the company) | `negative` (loss/cancellation) |
  `neutral`.
- `confidence`: `high` | `medium` | `low`.

## Output format (STRICT)
A single JSON array to the output path you were given, one object per input entry, same
order as input, no markdown fences:
[
  {"adsh": "...", "kind": "revenue_contract", "substantive": true,
   "named_counterparty": true, "quantified": true, "direction": "positive",
   "confidence": "high"},
  ...
]
Every input entry MUST appear exactly once.
