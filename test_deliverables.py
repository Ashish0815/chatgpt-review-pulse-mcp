"""Acceptance tests: check the Milestone 5 outputs against the brief.
Run locally with `pytest`; GitHub Actions runs them on every push.
No Google account or network access is needed."""
import csv
import json
import re
from pathlib import Path

import core

ROOT = Path(__file__).resolve().parent
OFFICIAL_DOMAINS = ("help.openai.com", "openai.com", "support.google.com")


def payload():
    return core.build_payload()


def insights():
    return json.loads(core.output_file("step1_insights.json").read_text(encoding="utf-8"))


# ---- Step 1: review intelligence -------------------------------------------

def test_at_most_five_themes_and_three_top():
    data = insights()
    assert len(data["themes"]) <= 5
    assert len(data["top_3_themes"]) == 3
    ids = {t["id"] for t in data["themes"]}
    assert set(data["top_3_themes"]) <= ids


def test_three_quotes_are_verbatim_from_the_reviews_csv():
    """Every quote must appear word for word in the review it cites."""
    sample = ROOT / "reviews_sample.csv"
    if not sample.exists():
        sample = ROOT / "data" / "reviews_sample.csv"
    reviews = {r["review_id"]: r["review_text"]
               for r in csv.DictReader(open(sample, encoding="utf-8-sig"))}
    quotes = insights()["quotes"]
    assert len(quotes) == 3
    for q in quotes:
        assert q["review_id"] in reviews, f"review {q['review_id']} not in sample"
        assert q["text"] in reviews[q["review_id"]], f"quote not verbatim: {q['text'][:60]}"


def test_fee_issue_is_identified():
    assert insights()["fee_issue"]["name"].strip()


# ---- Step 2: weekly pulse ----------------------------------------------------

def test_pulse_is_at_most_250_words():
    md = core.output_file("weekly_pulse.md").read_text(encoding="utf-8")
    tokens = re.sub(r"[#*>_]", "", md).split()
    words = len(tokens)  # strict: even a lone "—" counts, so any word counter agrees
    assert words <= 250, f"pulse is {words} words"


def test_pulse_has_required_sections():
    md = core.output_file("weekly_pulse.md").read_text(encoding="utf-8").lower()
    for section in ("top themes", "what users say", "key observation", "actions"):
        assert section in md, f"missing section: {section}"
    actions = md.split("actions", 1)[1]
    assert len(re.findall(r"^\d\.", actions, flags=re.M)) == 3, "need exactly 3 action ideas"


# ---- Step 3: fee explainer ---------------------------------------------------

def test_explainer_has_at_most_six_bullets():
    assert 1 <= len(payload()["explanation_bullets"]) <= 6


def test_explainer_has_two_official_https_sources():
    links = payload()["source_links"]
    assert len(links) == 2
    for url in links:
        assert url.startswith("https://")
        assert any(d in url for d in OFFICIAL_DOMAINS), f"not an official source: {url}"


def test_explainer_has_last_checked_date():
    assert payload()["last_checked"]


# ---- MCP actions -------------------------------------------------------------

def test_doc_entry_has_every_field_the_brief_lists():
    p = payload()
    for field in ("date", "top_themes", "weekly_pulse", "identified_fee_issue",
                  "explanation_bullets", "source_links"):
        assert p.get(field), f"missing field: {field}"


def test_email_subject_matches_the_brief():
    assert payload()["email_subject"].startswith(
        "Weekly Product Pulse + Customer Clarification — ")


def test_email_body_has_pulse_and_support_snippet():
    body = payload()["email_body"]
    assert "WEEKLY PRODUCT PULSE" in body
    assert "SUPPORT SNIPPET" in body


def test_code_cannot_send_email():
    """Safe by construction: no Gmail send call exists anywhere in the code."""
    for f in ROOT.glob("*.py"):
        if f.name == Path(__file__).name:
            continue
        src = f.read_text(encoding="utf-8")
        assert "drafts().send" not in src and "messages().send" not in src, f.name


def test_gmail_permission_is_compose_only():
    src = (ROOT / "google_tools.py").read_text(encoding="utf-8")
    assert "gmail.compose" in src
    assert "gmail.send" not in src and "mail.google.com/" not in src
