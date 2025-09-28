# oauth_setup.py
import json
from google_auth_oauthlib.flow import InstalledAppFlow
from datetime import datetime
import os

# adjust import to your firebase_client API
try:
    from firebase_client import add_document, update_user_profile  # adapt to your client
except Exception:
    # fallback for your environment
    def add_document(collection, data):
        print("Mock add_document:", collection, data)
        return "mock_id"

    def update_user_profile(uid, data):
        print("Mock update_user_profile:", uid, data)
        return True

# Path to OAuth client secrets from Google Cloud Console (create OAuth credentials)
CLIENT_SECRETS_FILE = "client_secret.json"  # download from Google Cloud -> OAuth 2.0 Client IDs

SCOPES = ["https://www.googleapis.com/auth/calendar.events", "openid", "email", "profile"]

def run_flow_and_store(uid="test_user"):
    flow = InstalledAppFlow.from_client_secrets_file(
        CLIENT_SECRETS_FILE,
        scopes=SCOPES
    )
    # This will open a browser and run a local server to receive the auth code
    creds = flow.run_local_server(port=0)

    # Build token dict to store
    token_data = {
        "access_token": creds.token,
        "refresh_token": creds.refresh_token,
        "token_uri": creds.token_uri,
        "client_id": creds.client_id,
        "client_secret": creds.client_secret,
        "scopes": creds.scopes,
        "expiry": creds.expiry.isoformat() if creds.expiry else None,
        "created_at": datetime.utcnow().isoformat()
    }

    # OPTION A: add_document into a tokens collection (simple)
    add_document("google_calendar_tokens", {"uid": uid, "tokens": token_data})

    # OPTION B: update the user's profile structure so your create_event() finds it:
    # The exact path depends on your firebase_client API. Example structure:
    # profile = { 'integrations': { 'google_calendar': { 'tokens': token_data } } }
    update_user_profile(uid, {"integrations.google_calendar.tokens": token_data})
    print("Stored tokens to Firestore for uid:", uid)

if __name__ == "__main__":
    run_flow_and_store(uid="your_test_uid_here")
