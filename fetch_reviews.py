"""
fetch_reviews.py  (v2) — Milestone 5, Step 1 (data collection)
Pulls recent ChatGPT Android reviews from the Google Play Store (India) into CSVs.

WHAT CHANGED IN v2
  v1 paged through "newest" reviews only. ChatGPT gets ~1,800 reviews a DAY in
  India, so the fetch stalled after one day. v2 fetches each star rating
  separately: complaints (1-3 stars) are rarer, so their pages reach back the
  full 8-12 weeks. Positive reviews (4-5 stars) are capped, since they carry
  little issue signal. It also retries when Google returns an empty page.

HOW TO RUN
  1. pip install google-play-scraper
  2. python fetch_reviews.py
     Options: python fetch_reviews.py --weeks 12 --neg-per-week 45 --pos-per-week 10
  Takes roughly 5-10 minutes. Leave it running.

OUTPUTS
  reviews_raw.csv     every review fetched (your audit trail)
  reviews_sample.csv  balanced weekly sample -> this is what goes to the LLM
  + a printed summary (copy-paste it back)
"""
import argparse
import csv
import random
import re
import sys
import time
from collections import Counter, defaultdict
from datetime import datetime, timedelta

try:
    from google_play_scraper import Sort, reviews
except ImportError:
    sys.exit("Missing library. Run:  pip install google-play-scraper")

APP_ID = "com.openai.chatgpt"

# Money / plan words, used ONLY for the printed sanity check (never put in the
# sample CSV, so the LLM isn't nudged towards our hypothesis).
FEE_TERMS = [
    r"charg\w*", r"deduct\w*", r"refund\w*", r"subscri\w*", r"bill(ed|ing)?",
    r"auto[- ]?pay", r"auto[- ]?renew\w*", r"renew\w*", r"upi", r"gst", r"tax",
    r"pric(e|es|ing)", r"pay", r"paid", r"payment\w*", r"money", r"rupees?", r"rs\.?",
    r"inr", r"trial", r"plus", r"go", r"premium", r"upgrade\w*", r"limit\w*",
    r"cancel\w*", r"free", r"plan", r"expensive", r"costs?", r"wallet",
]
FEE_RE = re.compile(r"(₹|\$|\b(" + "|".join(FEE_TERMS) + r")\b)", re.I)
# "go" and "free" are noisy alone; only count them in plan-like phrases
NOISY = {"go", "free", "plan", "plus"}
PLAN_PHRASE_RE = re.compile(
    r"\b(chatgpt go|go plan|upgrade to go|plus plan|chatgpt plus|free (plan|version|tier|user)s?|"
    r"for free|not free|free app)\b", re.I)

MIN_WORDS = 5


def is_money(text):
    hits = {m.group(0).lower() for m in FEE_RE.finditer(text)}
    strong = hits - NOISY
    return bool(strong) or bool(PLAN_PHRASE_RE.search(text))


def fetch_star(star, cutoff, country, lang, cap, pause):
    """Page through NEWEST reviews for one star rating until cutoff or cap."""
    rows, token, reached_cutoff, pages = [], None, False, 0
    while len(rows) < cap:
        batch = None
        for attempt in range(5):  # Google sometimes returns an empty page; retry with backoff
            try:
                if token is None and pages == 0:
                    batch, token = reviews(APP_ID, lang=lang, country=country, sort=Sort.NEWEST,
                                           count=200, filter_score_with=star)
                else:
                    batch, token = reviews(APP_ID, continuation_token=token)
            except Exception as e:  # network hiccup
                print(f"    {star}* page {pages+1}: error ({e.__class__.__name__}), retrying...")
                batch = []
            if batch:
                break
            time.sleep(3 * (attempt + 1))
        if not batch:
            print(f"    {star}*: Google stopped returning pages after {pages} pages.")
            break
        pages += 1
        for r in batch:
            if r["at"] < cutoff:
                reached_cutoff = True
                break
            rows.append({
                "review_id": r["reviewId"],
                "date": r["at"].strftime("%Y-%m-%d"),
                "week": r["at"].strftime("%G-W%V"),
                "rating": r["score"],
                "review_text": (r["content"] or "").replace("\n", " ").strip(),
                "app_version": r.get("reviewCreatedVersion") or "",
                "thumbs_up": r.get("thumbsUpCount", 0),
            })
        if reached_cutoff or not token:
            break
        if pages % 5 == 0:
            print(f"    {star}*: {len(rows)} reviews, back to {rows[-1]['date']}")
        time.sleep(pause)
    return rows, reached_cutoff


def write_csv(path, rows, fields):
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--weeks", type=int, default=10)
    ap.add_argument("--neg-cap", type=int, default=15000, help="max reviews per 1/2/3-star rating")
    ap.add_argument("--pos-cap", type=int, default=3000, help="max reviews per 4/5-star rating")
    ap.add_argument("--neg-per-week", type=int, default=45, help="1-3 star reviews sampled per week")
    ap.add_argument("--pos-per-week", type=int, default=10, help="4-5 star reviews sampled per week")
    ap.add_argument("--country", default="in")
    ap.add_argument("--lang", default="en")
    ap.add_argument("--pause", type=float, default=1.0, help="seconds between pages (be polite)")
    ap.add_argument("--seed", type=int, default=42)
    a = ap.parse_args()

    cutoff = datetime.now() - timedelta(weeks=a.weeks)
    print(f"ChatGPT reviews | country={a.country} | window: {cutoff:%Y-%m-%d} -> today")
    raw, coverage = [], {}
    for star in (1, 2, 3, 4, 5):
        cap = a.neg_cap if star <= 3 else a.pos_cap
        print(f"  Fetching {star}-star reviews (cap {cap})...")
        rows, done = fetch_star(star, cutoff, a.country, a.lang, cap, a.pause)
        coverage[star] = (len(rows), rows[-1]["date"] if rows else "-", done)
        raw += rows
    if not raw:
        sys.exit("No reviews returned. Check your internet connection and try again.")

    seen, dedup = set(), []
    for r in raw:
        if r["review_id"] not in seen:
            seen.add(r["review_id"])
            r["money_mention"] = is_money(r["review_text"])
            dedup.append(r)
    raw = sorted(dedup, key=lambda r: r["date"], reverse=True)
    write_csv("reviews_raw.csv", raw, list(raw[0].keys()))

    # Balanced sample: per week, mostly complaints (where issues live) plus a few
    # positives so the LLM still sees what users love.
    random.seed(a.seed)
    neg_wk, pos_wk = defaultdict(list), defaultdict(list)
    for r in raw:
        if len(r["review_text"].split()) < MIN_WORDS:
            continue
        (neg_wk if r["rating"] <= 3 else pos_wk)[r["week"]].append(r)
    sample = []
    for wk in sorted(set(neg_wk) | set(pos_wk)):
        sample += random.sample(neg_wk[wk], min(a.neg_per_week, len(neg_wk[wk])))
        sample += random.sample(pos_wk[wk], min(a.pos_per_week, len(pos_wk[wk])))
    sample.sort(key=lambda r: r["date"], reverse=True)
    write_csv("reviews_sample.csv", sample,
              ["review_id", "date", "week", "rating", "review_text", "app_version", "thumbs_up"])

    # ---- Summary ----
    neg = [r for r in raw if r["rating"] <= 3]
    neg_money = [r for r in neg if r["money_mention"]]
    print("\n================ SUMMARY (copy everything below) ================")
    print(f"Window requested: {a.weeks} weeks (from {cutoff:%Y-%m-%d})")
    print("Coverage by star (reviews fetched | oldest date reached | full window?):")
    for s, (n, oldest, done) in coverage.items():
        print(f"  {s}*: {n:>6} | {oldest} | {'YES' if done else 'no (capped/stopped)'}")
    print(f"Unique raw reviews: {len(raw)}")
    print(f"Sample for LLM: {len(sample)} reviews across {len({r['week'] for r in sample})} weeks")
    wk = Counter(r["week"] for r in sample)
    print("  per week: " + ", ".join(f"{w}={n}" for w, n in sorted(wk.items())))
    print(f"Money/plan mentions in 1-3* reviews: {len(neg_money)} of {len(neg)} "
          f"({100*len(neg_money)/max(len(neg),1):.1f}%)")
    by_week = defaultdict(lambda: [0, 0])
    for r in neg:
        by_week[r["week"]][1] += 1
        by_week[r["week"]][0] += r["money_mention"]
    print("  trend by week: " + ", ".join(f"{w}={100*m/t:.0f}%" for w, (m, t) in sorted(by_week.items())))
    print("\n6 most-upvoted money/plan complaints:")
    for r in sorted(neg_money, key=lambda r: -r["thumbs_up"])[:6]:
        print(f"  [{r['date']} | {r['rating']}* | +{r['thumbs_up']}] {r['review_text'][:220]}")
    print("=================================================================")


if __name__ == "__main__":
    main()
