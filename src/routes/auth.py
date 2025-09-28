from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from firebase_client import sign_in_with_email, create_user, get_current_uid
from google_auth_oauthlib.flow import Flow
from firebase_admin import firestore
from google.oauth2.credentials import Credentials
from firebase_client import db
import os
from firebase_client import set_initial_profile, is_profile_complete
from dotenv import load_dotenv
import json
from routes.events import get_google_creds as get_google_creds_events
from routes.tasks import get_google_creds as get_google_creds_tasks
from firebase_client import get_user_profile, set_user_profile
from firebase_admin import auth
load_dotenv()
client_secret_path = os.getenv("GOOGLE_CLIENT_SECRET_PATH")

GOOGLE_CLIENT_ID = None
GOOGLE_CLIENT_SECRET = None

if client_secret_path and os.path.exists(client_secret_path):
    with open(client_secret_path, "r") as f:
        data = json.load(f)
        # Some Google JSONs have "installed" key, some have "web"
        creds = data.get("installed") or data.get("web")
        GOOGLE_CLIENT_ID = creds.get("client_id")
        GOOGLE_CLIENT_SECRET = creds.get("client_secret")

flow = Flow.from_client_config(
    {
        "web": {
            "client_id": GOOGLE_CLIENT_ID,
            "client_secret": GOOGLE_CLIENT_SECRET,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": ["http://localhost:8000/auth/callback"],
            "scopes": [
                "https://www.googleapis.com/auth/calendar",
                "https://www.googleapis.com/auth/tasks"
            ]
        }
    },
    scopes=[
        "https://www.googleapis.com/auth/calendar",
        "https://www.googleapis.com/auth/tasks"
    ],
    redirect_uri="http://localhost:8000/auth/callback"
)

def get_google_creds(uid: str) -> Credentials:
    try:
        return get_google_creds_events(uid)
    except HTTPException:
        return get_google_creds_tasks(uid)

auth_router = APIRouter(prefix="/auth")

class LoginRequest(BaseModel):
    email: str
    password: str

@auth_router.post("/signup")
async def api_signup(request: LoginRequest):
    try:
        user_data = create_user(request.email, request.password)
        uid = user_data['uid']
        
        # Create initial profile (incomplete)
        set_initial_profile(uid, request.email)
        
        custom_token = auth.create_custom_token(uid)
        if isinstance(custom_token, bytes):
            custom_token = custom_token.decode("utf-8")
        
        return {"uid": uid, "custom_token": custom_token, "profile_complete": False}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@auth_router.post("/login")
async def api_login(request: LoginRequest):
    try:
        uid = sign_in_with_email(request.email, request.password)
        custom_token = auth.create_custom_token(uid)
        if isinstance(custom_token, bytes):
            custom_token = custom_token.decode("utf-8")
        
        # Check if profile is complete
        profile_complete = is_profile_complete(uid)
        
        # Create profile if missing (for existing users)
        profile = get_user_profile(uid)
        if not profile:
            set_initial_profile(uid, request.email)
            profile_complete = False
        
        return {"uid": uid, "custom_token": custom_token, "profile_complete": profile_complete}
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))

@auth_router.get("/url")
def get_auth_url(uid: str = Depends(get_current_uid)):
    authorization_url, state = flow.authorization_url(prompt='consent')
    db.collection('oauth_states').document(state).set({
        'uid': uid,
        'created_at': firestore.SERVER_TIMESTAMP
    })
    return {"url": authorization_url}

@auth_router.get("/callback")
def auth_callback(code: str, state: str):
    state_doc = db.collection('oauth_states').document(state).get()
    if not state_doc.exists:
        raise HTTPException(400, "Invalid state")
    
    data = state_doc.to_dict()
    uid = data['uid']
    
    flow.fetch_token(code=code)
    creds = flow.credentials
    
    token_data = {
        'access_token': creds.token,
        'refresh_token': creds.refresh_token,
        'id_token': creds.id_token,
        'expiry': creds.expiry.isoformat() if creds.expiry else None,
        'scopes': creds.scopes
    }
    
    db.collection('users').document(uid).update({
        'integrations.google_calendar.tokens': token_data
    })
    
    state_doc.reference.delete()
    
    return {"ok": True, "message": "Google integration connected successfully"}

@auth_router.post("/refresh")
def refresh_token(uid: str = Depends(get_current_uid)):
    creds = get_google_creds(uid)
    return {
        "access_token_expires_at": creds.expiry.isoformat() if creds.expiry else None,
        "ok": True
    }

@auth_router.post("/logout")
def logout_google(uid: str = Depends(get_current_uid)):
    user_ref = db.collection('users').document(uid)
    user_ref.update({
        'integrations.google_calendar': firestore.DELETE_FIELD
    })
    return {"ok": True}