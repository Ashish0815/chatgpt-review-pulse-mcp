# Review Pulse MCP — setup guide

Our own MCP server. It gives an AI client three tools:

| Tool | Type | What it does |
|---|---|---|
| `get_weekly_outputs` | read-only | Loads this week's insights, pulse and fee explainer from `outputs/` |
| `append_to_doc` | **write — needs approval** | Appends a dated entry to your Google Doc |
| `create_email_draft` | **write — needs approval** | Saves a Gmail draft. No code in this project can send email. |

Use a **personal** Google account (not a work account) for every step. Total time: about 20 minutes, once.

---

## 1. Google Cloud: let the server use your Docs and Gmail (~10 min)
Google's menu labels change from time to time; if a name differs slightly, look for the closest match.

1. Go to https://console.cloud.google.com and sign in with your personal Gmail.
2. **Create a project:** click the project picker at the top → **New project** → name it `review-pulse` → **Create**. Make sure it's selected.
3. **Turn on the two APIs:** in the top search bar, search **Google Docs API** → **Enable**. Then search **Gmail API** → **Enable**.
4. **Consent screen:** menu ☰ → **APIs & Services** → **OAuth consent screen** (may be called *Google Auth Platform*) → **Get started**.
   - App name: `Review Pulse` · Support email: your Gmail
   - Audience: **External** · Contact email: your Gmail → **Create**
5. **Add yourself as a tester:** **Audience** → **Test users** → **Add users** → your Gmail → **Save**.
6. **Create the key file:** **Clients** → **Create client** → Application type **Desktop app** → **Create** → **Download JSON**.
   Rename the file to `credentials.json` and put it in this folder (next to `server.py`).

> `credentials.json` and `token.json` are private. Don't share them or upload them with your submission.

## 2. Install and sign in (~3 min)
Open Terminal in this folder (Finder: right-click the folder → **New Terminal at Folder**), then:
```
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python auth_setup.py
```
The `.venv` is a private Python environment for this project. Run `source .venv/bin/activate` again in any new Terminal window before running the scripts; your prompt shows `(.venv)` when it's active.
A browser opens. Pick your Gmail. You'll see **"Google hasn't verified this app"** — that's expected for your own app in testing mode: click **Continue**, tick both permissions, **Continue**.
The terminal prints the link to a new Google Doc: **ChatGPT India — Weekly Product Pulse Log**.

## 3. Test without AI (approval by typing `yes`)
```
python run_cli.py
```
It previews the doc entry and asks for approval, then previews the email and asks again. Type `yes` to each.
Check: the Google Doc has a new entry, and **Gmail → Drafts** has the email. Nothing is sent.

## 4. Connect to the Claude desktop app (the MCP demo)
1. In Terminal, inside the project folder, run `pwd` and copy the path it prints (for example `/Users/you/Desktop/review-pulse-mcp`).
2. In the Claude desktop app: **Settings → Developer → Edit Config**. This opens `claude_desktop_config.json`
   (Mac: `~/Library/Application Support/Claude/` · Windows: `%APPDATA%\Claude\`).
3. Add this, replacing `/Users/you/Desktop/review-pulse-mcp` with your path from step 1. Point to the `.venv` Python so the server finds its libraries:
```json
{
  "mcpServers": {
    "review-pulse": {
      "command": "/Users/you/Desktop/review-pulse-mcp/.venv/bin/python",
      "args": ["/Users/you/Desktop/review-pulse-mcp/server.py"]
    }
  }
}
```
   If the file already has an `mcpServers` section, add `review-pulse` inside it.
4. Fully quit and reopen the Claude app. The `review-pulse` tools should appear in the tools/connectors menu.

If your Claude app is on a work account that blocks custom servers, use either `run_cli.py` (step 3) or the official MCP Inspector, which also asks you to approve each tool run: `npx @modelcontextprotocol/inspector python server.py` (needs Node.js).

## 5. Where the approval happens
1. **Claude app:** before each tool runs, Claude shows the tool name and the exact values it will send, with **Allow** / **Deny**. Choose **Allow once** for the two write tools — not "Always allow" — so every write needs a fresh approval.
2. **run_cli.py:** a full preview, then you must type `yes`.
3. **Audit trail:** every approved, rejected or failed write is recorded in `approval_log.csv`.

## 6. Demo script (≤3 min video)
1. (20s) Show `reviews_sample.csv` and the theme numbers in `step1_insights.json`.
2. (30s) Show `weekly_pulse.md` and `fee_explainer.md` and point out the link from reviews to the fee issue.
3. (90s) In the Claude app, type:
   > Use review-pulse to load this week's outputs, show me a short preview, then log them to the doc and create the email draft.
   Claude calls `get_weekly_outputs` → previews → asks approval for `append_to_doc` → **Allow once** → asks approval for `create_email_draft` → **Allow once**.
   Optionally press **Deny** once first to show that nothing happens without approval.
4. (30s) Open the Google Doc entry and Gmail → Drafts. Show `approval_log.csv`.

## Troubleshooting
- **"Not signed in to Google"** → run `python auth_setup.py`.
- **`invalid_grant` after about a week** → Google expires testing-mode sign-ins after 7 days. Delete `token.json` and run `python auth_setup.py` again.
- **Tools don't appear in Claude** → check the paths in the config, then fully quit and reopen the app (closing the window isn't enough).
- **Next week's run** → replace the three files in `outputs/` and run again. Each run appends a new dated entry.
