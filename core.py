"""core.py — builds the weekly entry and the email from the files in outputs/.
Pure Python, no Google or MCP code, so it can be tested on its own."""
import csv
import json
import re
from datetime import date, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CONFIG = ROOT / "config.json"
LOG = ROOT / "approval_log.csv"


def load_config():
    """config.json is private (git-ignored); fall back to the committed example."""
    path = CONFIG if CONFIG.exists() else ROOT / "config.example.json"
    return json.loads(path.read_text(encoding="utf-8"))


def output_file(name):
    """Find an output file in outputs/ if that folder exists, else next to this script."""
    cfg = load_config()
    candidate = ROOT / cfg.get("outputs_dir", "outputs") / name
    return candidate if candidate.exists() else ROOT / name


def save_config(cfg):
    CONFIG.write_text(json.dumps(cfg, indent=2), encoding="utf-8")


def md_to_text(md):
    """Markdown -> plain text that reads well in a Google Doc or email."""
    out = []
    for line in md.splitlines():
        line = re.sub(r"^#+\s*", "", line)          # headings
        line = line.replace("**", "").replace("*", "")  # bold / italics
        line = re.sub(r"^- ", "• ", line)             # bullets
        out.append(line.rstrip())
    return "\n".join(out).strip()


def build_payload():
    """Read outputs/ and return the structured entry the brief asks for."""
    cfg = load_config()
    insights = json.loads(output_file("step1_insights.json").read_text(encoding="utf-8"))
    pulse_md = output_file("weekly_pulse.md").read_text(encoding="utf-8")
    fee_md = output_file("fee_explainer.md").read_text(encoding="utf-8")

    themes = {t["id"]: t for t in insights["themes"]}
    top_themes = [f'{themes[i]["name"]} ({themes[i]["share_of_substantive_complaints"]}%)'
                  for i in insights["top_3_themes"]]
    bullets = [md_to_text(l[2:]) for l in fee_md.splitlines() if l.startswith("- **")]
    sources_block = fee_md.split("**Sources**")[1].split("**Last checked")[0]
    sources = re.findall(r"https?://\S+", sources_block)
    m = re.search(r"\*\*Last checked:\*\*\s*(.+)", fee_md)
    last_checked = m.group(1).strip() if m else ""

    today = date.today()
    payload = {
        "date": today.isoformat(),
        "top_themes": top_themes,
        "weekly_pulse": md_to_text(pulse_md),
        "identified_fee_issue": insights["fee_issue"]["name"],
        "explanation_bullets": bullets,
        "source_links": sources,
        "last_checked": last_checked,
    }
    payload["email_subject"] = (f"Weekly Product Pulse + Customer Clarification — "
                                f"{today.strftime('%d %b %Y')}")
    payload["email_body"] = format_email_body(payload)
    payload["email_to"] = cfg.get("draft_to", "")
    return payload


def format_doc_entry(p):
    lines = [f"Weekly entry — {p['date']}", ""]
    lines.append("Top themes:")
    lines += [f"  • {t}" for t in p["top_themes"]]
    lines += ["", "Weekly pulse:", p["weekly_pulse"], ""]
    lines.append(f"Identified fee issue: {p['identified_fee_issue']}")
    lines += ["", "Fee explanation:"]
    lines += [f"  • {b}" for b in p["explanation_bullets"]]
    lines += ["", "Sources:"]
    lines += [f"  • {s}" for s in p["source_links"]]
    if p.get("last_checked"):
        lines.append(f"Last checked: {p['last_checked']}")
    lines += ["", "—" * 30, ""]
    return "\n".join(lines)


def format_email_body(p):
    parts = [
        "Hi team,",
        "",
        "Below is this week's product pulse, followed by a support snippet on the fee issue "
        "users are most confused about. The snippet can be pasted into support replies as-is.",
        "",
        "=" * 40,
        "WEEKLY PRODUCT PULSE",
        "=" * 40,
        p["weekly_pulse"],
        "",
        "=" * 40,
        f"SUPPORT SNIPPET: {p['identified_fee_issue']}",
        "=" * 40,
    ]
    parts += [f"- {b}" for b in p["explanation_bullets"]]
    parts += ["", "Sources:"] + [f"- {s}" for s in p["source_links"]]
    if p.get("last_checked"):
        parts.append(f"Last checked: {p['last_checked']}")
    parts += ["", "Drafted by the Review Pulse workflow. Review before sending."]
    return "\n".join(parts)


def log_action(action, target, status):
    """Every approved write is recorded — evidence for the README and demo."""
    new = not LOG.exists()
    with open(LOG, "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if new:
            w.writerow(["timestamp", "action", "target", "status"])
        w.writerow([datetime.now().isoformat(timespec="seconds"), action, target, status])
