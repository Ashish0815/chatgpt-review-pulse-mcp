"""Size candidate themes across ALL 1-3 star reviews (validation of the LLM read).
Keyword rules are approximate and multi-label: one review can hit several themes."""
import csv, re, sys, collections
T = {
 "T1 Free-plan limits & upgrade prompts": r"limit|upgrade|premium|paywall|subscri|plus\b|\bgo\b plan|chatgpt go|pay(ing|ment)?\b|paid|money|paisa|pesa|fee|fess|cool ?down|try again (later|in)|wait \d+|out of (image|attachment)|hours? later|free (user|version|plan|tier)s?|for free|not free|restriction",
 "T2 Answer quality & instruction-following": r"wrong|incorrect|galat|mistake|halluc|lie|lies|makes? up|accura|follow|instruction|understand|samajh|forget|forgot|memory|context|dumb|stupid|bekar answer|sahi (jawab|answer)",
 "T3 App bugs, crashes & update regressions": r"crash|bug|lag|slow|freez|log ?in|sign ?in|loading|stuck|error|not working|kam nahi|update|dark mode|copy|sync|disappear|black screen|scroll|volume|network",
 "T4 Image generation quality & content blocks": r"image|photo|pic|picture|edit|face|guardrail|violate|polic(y|ies)|not allowed|niyam|generate",
 "T5 Trust, privacy & ethics": r"privacy|data|water|bias|biased|dangerous|politic|censor|neutral|propaganda|spy|stalk",
}
rx = {k: re.compile(v, re.I) for k, v in T.items()}
rows = [r for r in csv.DictReader(open(sys.argv[1] if len(sys.argv) > 1 else "reviews_raw.csv", encoding="utf-8-sig")) if int(r["rating"]) <= 3 and len(r["review_text"].split()) >= 5]
cnt, none = collections.Counter(), 0
for r in rows:
    hit = [k for k, x in rx.items() if x.search(r["review_text"])]
    cnt.update(hit); none += not hit
n = len(rows)
print(f"1-3* reviews with 5+ words: {n}")
for k, c in cnt.most_common(): print(f"  {k:<46} {c:>6}  {100*c/n:5.1f}%")
print(f"  {'(no theme matched — mostly short/vague/other language)':<46} {none:>6}  {100*none/n:5.1f}%")

# Drill into T1: what kind of money/limit confusion?
sub = {
 "a) hit free limit (images/files/chat) + cooldown": r"limit|cool ?down|try again|wait \d+|out of (image|attachment)|hours? later|khatam",
 "b) pushed/forced to upgrade, 'not really free'": r"upgrade|paywall|premium|forc|push|not free|for free|free (user|version|plan)",
 "c) limits unclear / inconsistent / can't track usage": r"clear|unclear|hiding|monitor|how many|not sure|same (version|plan)|some users|counts? as|fine print|confus",
 "d) price too high / can't afford": r"expensive|costly|too high|afford|don.t have money|mahang|cheap",
 "e) billing problem: charged, refund, cancel, not activated": r"charg|deduct|refund|cancel|not activ|why not activ|billed|money not",
 "f) paid but still limited / poor value": r"(i|we) (pay|paid)|paying|\$20|20\$|plus user|subscribed",
}
srx = {k: re.compile(v, re.I) for k, v in sub.items()}
t1 = [r for r in rows if rx["T1 Free-plan limits & upgrade prompts"].search(r["review_text"])]
sc = collections.Counter()
for r in t1: sc.update(k for k, x in srx.items() if x.search(r["review_text"]))
print(f"\nInside T1 ({len(t1)} reviews):")
for k, c in sc.most_common(): print(f"  {k:<56} {c:>5}  {100*c/len(t1):5.1f}%")

# Like-for-like trend (2-star only = the one rating with full 10-week coverage)
wk = collections.defaultdict(lambda: [0, 0])
for r in rows:
    if r["rating"] != "2": continue
    wk[r["week"]][1] += 1; wk[r["week"]][0] += bool(rx["T1 Free-plan limits & upgrade prompts"].search(r["review_text"]))
print("\nT1 share of 2* reviews by week: " + ", ".join(f"{w[-3:]}={100*a/b:.0f}%" for w,(a,b) in sorted(wk.items()) if b>100))
