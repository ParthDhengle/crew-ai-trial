from fastapi import APIRouter, Depends, HTTPException
from typing import Dict
from firebase_client import get_current_uid, db
from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
import json
from firebase_admin import firestore

google_auth_router = APIRouter(prefix="/api/google-auth", tags=["google-auth"])

@google_auth_router.post("/client-secret")
async def save_client_secret(creds: Dict, uid: str = Depends(get_current_uid)):
    try:
        client_id = creds.get("client_id")
        client_secret = creds.get("client_secret")
        if not client_id or not client_secret:
            raise HTTPException(400, "Invalid client secret: missing client_id or client_secret")
        
        db.collection('users').document(uid).update({
            'integrations.google_calendar': {
                'client_id': client_id,
                'client_secret': client_secret,
                'tokens': {}  # Initialize empty tokens
            },
            'updated_at': firestore.SERVER_TIMESTAMP
        })
        
        return {"message": "Client secret saved successfully"}
    except Exception as e:
        print(f"Error saving client secret: {str(e)}")
        raise HTTPException(500, f"Failed to save client secret: {str(e)}")

@google_auth_router.post("/complete")
async def complete_oauth(data: Dict, uid: str = Depends(get_current_uid)):
    try:
        user_doc = db.collection('users').document(uid).get()
        user = user_doc.to_dict()
        google_cal = user.get('integrations', {}).get('google_calendar', {})
        client_id = google_cal.get('client_id')
        client_secret = google_cal.get('client_secret')
        
        if not client_id or not client_secret:
            raise HTTPException(400, "Client secret not found. Please upload first.")
        
        flow = Flow.from_client_config(
            {"web": {
                "client_id": client_id,
                "client_secret": client_secret,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token"
            }},
            scopes=['https://www.googleapis.com/auth/calendar', 'https://www.googleapis.com/auth/tasks']
        )
        flow.redirect_uri = "postmessage"  # For client-side code flow
        
        flow.fetch_token(code=data['code'])
        creds = flow.credentials
        
        token_data = {
            'access_token': creds.token,
            'refresh_token': creds.refresh_token,
            'expiry': creds.expiry.isoformat() if creds.expiry else None
        }
        
        db.collection('users').document(uid).update({
            'integrations.google_calendar.tokens': token_data,
            'updated_at': firestore.SERVER_TIMESTAMP
        })
        
        return {"message": "OAuth completed and tokens stored"}
    except Exception as e:
        print(f"OAuth completion failed: {str(e)}")
        raise HTTPException(500, f"OAuth failed: {str(e)}")