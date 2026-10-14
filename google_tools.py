"""google_tools.py — the only code that touches your Google account.
Scopes are kept minimal: edit Google Docs, and compose Gmail drafts.
There is deliberately NO function that sends email."""
import base64
from email.message import EmailMessage
from pathlib import Path

ROOT = Path(__file__).resolve().parent
TOKEN = ROOT / "token.json"
SECRET = ROOT / "credentials.json"
SCOPES = [
    "https://www.googleapis.com/auth/documents",
    "https://www.googleapis.com/auth/gmail.compose",
]


def get_creds(interactive=False):
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials

    creds = Credentials.from_authorized_user_file(str(TOKEN), SCOPES) if TOKEN.exists() else None
    if creds and creds.valid:
        return creds
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
        TOKEN.write_text(creds.to_json())
        return creds
    if not interactive:
        # The MCP server must never open a browser; sign in once with auth_setup.py
        raise RuntimeError("Not signed in to Google. Run:  python auth_setup.py")
    from google_auth_oauthlib.flow import InstalledAppFlow
    if not SECRET.exists():
        raise FileNotFoundError("credentials.json not found. See SETUP.md step 1.")
    flow = InstalledAppFlow.from_client_secrets_file(str(SECRET), SCOPES)
    creds = flow.run_local_server(port=0)
    TOKEN.write_text(creds.to_json())
    return creds


def _docs(creds=None):
    from googleapiclient.discovery import build
    return build("docs", "v1", credentials=creds or get_creds(), cache_discovery=False)


def _gmail(creds=None):
    from googleapiclient.discovery import build
    return build("gmail", "v1", credentials=creds or get_creds(), cache_discovery=False)


def doc_url(doc_id):
    return f"https://docs.google.com/document/d/{doc_id}/edit"


def create_doc(title, creds=None):
    doc = _docs(creds).documents().create(body={"title": title}).execute()
    return doc["documentId"]


def append_to_doc(doc_id, text):
    """Append text at the end of the doc; style its first line as Heading 2."""
    svc = _docs()
    doc = svc.documents().get(documentId=doc_id).execute()
    end = doc["body"]["content"][-1]["endIndex"] - 1
    first_line = text.split("\n", 1)[0]
    start = end + 1  # after the leading newline we insert
    requests = [
        {"insertText": {"location": {"index": end}, "text": "\n" + text}},
        {"updateParagraphStyle": {
            "range": {"startIndex": start, "endIndex": start + len(first_line)},
            "paragraphStyle": {"namedStyleType": "HEADING_2"},
            "fields": "namedStyleType"}},
    ]
    svc.documents().batchUpdate(documentId=doc_id, body={"requests": requests}).execute()
    return doc_url(doc_id)


def create_draft(to, subject, body):
    msg = EmailMessage()
    if to:
        msg["To"] = to
    msg["Subject"] = subject
    msg.set_content(body)
    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
    draft = _gmail().users().drafts().create(userId="me", body={"message": {"raw": raw}}).execute()
    return draft["id"]
