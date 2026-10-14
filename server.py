"""server.py — our own MCP server ("review-pulse").

It exposes three tools to any MCP client (e.g. the Claude desktop app):
  get_weekly_outputs   read-only   loads this week's pulse + fee explainer
  append_to_doc        WRITE       appends the entry to your Google Doc
  create_email_draft   WRITE       creates a Gmail draft (never sends)

APPROVAL GATE: the MCP client asks you to Allow or Deny every tool call before
it runs. Choose "Allow once" for the write tools so you approve each time.
"""
try:  # mcp 2.x
    from mcp.server.mcpserver import MCPServer as Server
except ImportError:  # mcp 1.x
    from mcp.server.fastmcp import FastMCP as Server
from mcp.types import ToolAnnotations

import core
import google_tools

mcp = Server("review-pulse")

READ_ONLY = ToolAnnotations(title="Load weekly outputs", readOnlyHint=True)
WRITE = lambda title: ToolAnnotations(title=title, readOnlyHint=False,
                                      destructiveHint=False, idempotentHint=False)


@mcp.tool(annotations=READ_ONLY)
def get_weekly_outputs() -> dict:
    """READ-ONLY. Load this week's review insights, weekly product pulse and fee explainer.
    Returns the doc entry fields (date, top_themes, weekly_pulse, identified_fee_issue,
    explanation_bullets, source_links, last_checked) plus a suggested email_subject,
    email_body and email_to. Call this first, show the user a short preview, then
    call append_to_doc and create_email_draft with these exact values."""
    return core.build_payload()


@mcp.tool(annotations=WRITE("Append entry to Google Doc"))
def append_to_doc(date: str, top_themes: list[str], weekly_pulse: str,
                  identified_fee_issue: str, explanation_bullets: list[str],
                  source_links: list[str], last_checked: str = "") -> str:
    """WRITE ACTION — only call after the user has approved. Appends one weekly entry to
    the user's Weekly Pulse Google Doc. Pass the values returned by get_weekly_outputs."""
    cfg = core.load_config()
    doc_id = cfg.get("doc_id")
    if not doc_id:
        return "No Google Doc configured. Run: python auth_setup.py"
    entry = core.format_doc_entry({
        "date": date, "top_themes": top_themes, "weekly_pulse": weekly_pulse,
        "identified_fee_issue": identified_fee_issue,
        "explanation_bullets": explanation_bullets,
        "source_links": source_links, "last_checked": last_checked,
    })
    try:
        url = google_tools.append_to_doc(doc_id, entry)
    except Exception as e:
        core.log_action("append_to_doc", doc_id, f"failed: {e}")
        return f"Could not append to the doc: {e}"
    core.log_action("append_to_doc", url, "done")
    return f"Appended the {date} entry to {url}"


@mcp.tool(annotations=WRITE("Create Gmail draft (no send)"))
def create_email_draft(subject: str, body: str, to: str = "") -> str:
    """WRITE ACTION — only call after the user has approved. Saves a Gmail DRAFT in the
    user's account. It does not send; the user reviews and sends it themselves."""
    try:
        draft_id = google_tools.create_draft(to, subject, body)
    except Exception as e:
        core.log_action("create_email_draft", subject, f"failed: {e}")
        return f"Could not create the draft: {e}"
    core.log_action("create_email_draft", subject, f"done (draft {draft_id})")
    return f"Draft saved in Gmail > Drafts: '{subject}'. Not sent."


if __name__ == "__main__":
    mcp.run()
