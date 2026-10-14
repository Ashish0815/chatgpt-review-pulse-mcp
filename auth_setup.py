"""auth_setup.py — run ONCE. Signs you in to Google and creates the log doc.
    python auth_setup.py
"""
import core
import google_tools

DOC_TITLE = "ChatGPT India — Weekly Product Pulse Log"

print("Opening your browser to sign in to Google...")
creds = google_tools.get_creds(interactive=True)
print("Signed in.")

cfg = core.load_config()
if not cfg.get("doc_id"):
    cfg["doc_id"] = google_tools.create_doc(DOC_TITLE, creds)
    core.save_config(cfg)
    print(f"Created Google Doc '{DOC_TITLE}'")
print("Doc:", google_tools.doc_url(cfg["doc_id"]))
print("Setup complete. Next: python run_cli.py   (or connect server.py to the Claude app)")
