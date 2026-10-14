"""run_cli.py — the same workflow without an AI client, with a typed approval step.
Useful as a backup for the demo, or to test your Google setup.
    python run_cli.py
"""
import core
import google_tools


def ask(question):
    return input(f"\n>>> {question} Type 'yes' to approve: ").strip().lower() == "yes"


p = core.build_payload()
cfg = core.load_config()
entry = core.format_doc_entry(p)

print("=" * 70, "\nPREVIEW 1 of 2 — entry to append to your Google Doc\n" + "=" * 70)
print(entry)
if ask("Append this entry to the doc?"):
    url = google_tools.append_to_doc(cfg["doc_id"], entry)
    core.log_action("append_to_doc", url, "done (cli)")
    print("Appended:", url)
else:
    core.log_action("append_to_doc", cfg.get("doc_id", ""), "rejected by user")
    print("Skipped.")

print("\n" + "=" * 70, "\nPREVIEW 2 of 2 — Gmail draft\n" + "=" * 70)
print(f"To: {p['email_to']}\nSubject: {p['email_subject']}\n\n{p['email_body']}")
if ask("Create this Gmail draft? (it will NOT be sent)"):
    draft_id = google_tools.create_draft(p["email_to"], p["email_subject"], p["email_body"])
    core.log_action("create_email_draft", p["email_subject"], f"done (cli, draft {draft_id})")
    print("Draft saved in Gmail > Drafts. Not sent.")
else:
    core.log_action("create_email_draft", p["email_subject"], "rejected by user")
    print("Skipped.")
