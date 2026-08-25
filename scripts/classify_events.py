"""Classify infra 8-K events without touching a Cowork session budget.

Pipeline (runs in GitHub Actions):
  1. regex-drop earnings docs (free)
  2. local TF-IDF classifier auto-decides confident cases (free, ~94% acc)
  3. uncertain cases -> Anthropic Batch API with Haiku (user's API key, 50% batch discount)

Input:  data/infra_events_raw.jsonl  (from fetch_edgar.py)
Output: data/infra_annotations.jsonl (adsh, ticker, date, substantive_positive, source, ...)
Env:    ANTHROPIC_API_KEY (repo secret) — only needed if there are uncertain cases.
"""
import json
import os
import re
import time
from pathlib import Path

import joblib

ROOT = Path(__file__).resolve().parents[1]
LO, HI = 0.35, 0.65          # local-classifier confidence margins
HAIKU = "claude-haiku-4-5"
EARN = re.compile(r'(EDITED TRANSCRIPT|Earnings Call|STREETEVENTS|Reports? (First|Second|Third|Fourth) Quarter|'
                  r'Q[1-4] (FY)?20\d\d (Financial )?Results|Announces (First|Second|Third|Fourth).{0,15}Quarter|'
                  r'Quarterly Results|Fiscal (Year|20\d\d) Results|Financial Results for)', re.I)

def load_events():
    evs, seen = [], set()
    with open(ROOT / "data" / "infra_events_raw.jsonl") as f:
        for line in f:
            e = json.loads(line)
            if not e.get("ticker") or not e.get("text"):
                continue
            if EARN.search(e["text"][:1200]):
                continue
            key = (e["ticker"], e["file_date"])
            if key in seen:
                continue
            seen.add(key)
            evs.append(e)
    return evs

def existing_labels():
    p = ROOT / "data" / "infra_annotations.jsonl"
    if not p.exists():
        return {}
    return {json.loads(l)["adsh"]: json.loads(l) for l in open(p)}

def classify_local(events):
    bundle = joblib.load(ROOT / "models" / "infra_classifier.joblib")
    vec, clf = bundle["vectorizer"], bundle["model"]
    X = vec.transform([(e["text"] or "")[:3000] for e in events])
    return clf.predict_proba(X)[:, 1]

def haiku_batch(uncertain):
    import anthropic
    client = anthropic.Anthropic()
    rubric = (ROOT / "rubric_infra.md").read_text()
    reqs = []
    for e in uncertain:
        prompt = (f"{rubric}\n\nClassify this single filing excerpt. Reply with ONLY one JSON object "
                  f"(fields: adsh, kind, substantive, named_counterparty, quantified, direction, confidence).\n\n"
                  f"adsh: {e['adsh']}\nticker: {e['ticker']}\ndate: {e['file_date']}\n"
                  f"text: {(e['text'] or '')[:2200]}")
        reqs.append({"custom_id": e["adsh"].replace("-", ""),
                     "params": {"model": HAIKU, "max_tokens": 300,
                                "messages": [{"role": "user", "content": prompt}]}})
    batch = client.messages.batches.create(requests=reqs)
    print(f"batch {batch.id}: {len(reqs)} requests submitted")
    while True:
        b = client.messages.batches.retrieve(batch.id)
        if b.processing_status == "ended":
            break
        print(f"  status={b.processing_status} …", flush=True)
        time.sleep(60)
    out = {}
    for r in client.messages.batches.results(batch.id):
        if r.result.type != "succeeded":
            continue
        try:
            txt = r.result.message.content[0].text
            j = json.loads(re.search(r"\{.*\}", txt, re.S).group(0))
            out[r.custom_id] = j
        except Exception:
            pass
    print(f"batch returned {len(out)} parsed labels")
    return out

def main():
    events = load_events()
    done = existing_labels()
    todo = [e for e in events if e["adsh"] not in done]
    print(f"{len(events)} clean events, {len(done)} already labeled, {len(todo)} new")
    if not todo:
        return
    probs = classify_local(todo)
    records, uncertain = [], []
    for e, p in zip(todo, probs):
        base = {"adsh": e["adsh"], "ticker": e["ticker"], "name": e.get("name"),
                "file_date": e["file_date"], "sic": e.get("sic"), "p_local": round(float(p), 3)}
        if p <= LO:
            records.append({**base, "substantive_positive": False, "source": "local"})
        elif p >= HI:
            records.append({**base, "substantive_positive": True, "source": "local"})
        else:
            uncertain.append(e)
    print(f"local: {len(records)} auto-decided, {len(uncertain)} -> Haiku")
    if uncertain:
        if not os.environ.get("ANTHROPIC_API_KEY"):
            raise SystemExit("uncertain cases exist but ANTHROPIC_API_KEY is not set")
        labels = haiku_batch(uncertain)
        for e in uncertain:
            j = labels.get(e["adsh"].replace("-", ""))
            if not j:
                continue
            records.append({"adsh": e["adsh"], "ticker": e["ticker"], "name": e.get("name"),
                            "file_date": e["file_date"], "sic": e.get("sic"),
                            "substantive_positive": bool(j.get("substantive")) and j.get("direction") == "positive",
                            "kind": j.get("kind"), "named_counterparty": j.get("named_counterparty"),
                            "quantified": j.get("quantified"), "confidence": j.get("confidence"),
                            "source": "haiku"})
    merged = {**done, **{r["adsh"]: r for r in records}}
    with open(ROOT / "data" / "infra_annotations.jsonl", "w") as f:
        for r in merged.values():
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    n_pos = sum(1 for r in merged.values() if r.get("substantive_positive"))
    print(f"wrote {len(merged)} labels ({n_pos} substantive positive)")

if __name__ == "__main__":
    main()
