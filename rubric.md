# Classification rubric for Truth Social posts (market relevance)

You are annotating posts by Donald Trump for an event study of stock-market reactions.
Read the input file, classify EVERY post, write the output file. Follow the schema exactly.

## Task
For each post decide whether a trader reading it at publication time would see it as
relevant to the price of specific publicly traded companies or market sectors.

- `market_relevant: true` only if the post targets, praises, threatens, or announces policy
  affecting identifiable companies, industries, or macro-financial variables (tariffs on a
  country/industry, Fed/interest rates, drug pricing, chip export rules, crypto policy,
  a named company or CEO, oil/energy policy, the stock market itself).
- `market_relevant: false` for general politics, elections, legal cases, immigration,
  culture war, congratulations, rally announcements — even if they mention a country.
  A post mentioning China/Mexico/EU is relevant ONLY if it concerns trade, tariffs,
  economics, or named industries — not diplomacy, war, or border topics alone.

## Fields per post
- `id`: copy from input.
- `market_relevant`: boolean.
- `entities`: publicly traded companies directly implicated (named, or unambiguous like
  "Truth Social" → DJT, "the EV mandate" does NOT name a company). Each entry:
  `{"name": "...", "ticker": "XXXX" or null}`. Use the US-listed parent ticker; null if
  unsure. Empty list if none.
- `theme`: one of `tariffs`, `fed_rates`, `pharma`, `chips`, `crypto`, `energy`,
  `defense`, `media`, `autos`, `steel_metals`, `tech`, `retail_consumer`,
  `macro_markets`, `company_specific`, `other`. Pick the dominant one.
- `direction`: expected price impact ON THE NAMED ENTITIES (or the theme's sector if no
  entities) from the post's stance:
  - `negative`: threats, tariffs on that industry, attacks on the company/CEO, demands to
    lower their prices.
  - `positive`: praise, favorable policy (deregulation for them, subsidies, protection
    FROM foreign competition, pro-crypto policy for crypto theme).
  - `ambiguous`: mixed, unclear, or purely informational.
  Note: a tariff post is `negative` for importing/targeted industries but if it is framed
  as protecting a named US industry (e.g. steel tariffs protecting US Steel), direction
  for that protected entity is `positive`. Judge per the post's main thrust.
- `confidence`: `high` | `medium` | `low`.

## Output format (STRICT)
Write a single JSON array to the output path you were given, one object per input post,
same order as input, no trailing commas, no comments, no markdown fences in the file:

[
  {"id": "...", "market_relevant": true, "entities": [{"name": "Apple", "ticker": "AAPL"}],
   "theme": "tariffs", "direction": "negative", "confidence": "high"},
  ...
]

Every input post MUST appear exactly once. Do not skip empty or unclear posts — classify
them with `market_relevant: false`, `confidence: low` if needed.
