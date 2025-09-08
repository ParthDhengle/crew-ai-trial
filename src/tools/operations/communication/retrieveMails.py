import os
import smtplib
import base64
import json
import platform
import subprocess
import webbrowser
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from pathlib import Path

from crewai import Agent, Crew, Process, Task, LLM
# from twilio.rest import Client # Twilio functions are commented out as in original

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

SCOPES = ["https://mail.google.com/"]

TOKEN_FILE = "token.json"
CLIENT_SECRET_FILE = "client_secret.json"


def get_google_service(api_name, api_version, scopes):
    """
    Handles Google API authentication and service creation.
    Creates or refreshes 'token.json' as needed.
    """
    creds = None
    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, scopes)
    
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except Exception as e:
                print(f"⚠️ Token refresh failed: {e}. Re-authenticating...")
                creds = None # Force re-authentication
        
        if not creds:
            if not os.path.exists(CLIENT_SECRET_FILE):
                print(f"❌ Error: '{CLIENT_SECRET_FILE}' not found.")
                print("Please download it from your Google Cloud Console and place it in the same directory.")
                return None
            flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRET_FILE, scopes)
            creds = flow.run_local_server(port=0)
        
        with open(TOKEN_FILE, "w") as token:
            token.write(creds.to_json())
            print(f"✅ Token saved to '{TOKEN_FILE}'")
            
    try:
        service = build(api_name, api_version, credentials=creds)
        print(f"✅ Successfully connected to Google {api_name.capitalize()} API.")
        return service
    except HttpError as error:
        print(f"❌ An error occurred with the Google API: {error}")
        return None


def _get_header(headers, name):
    """Gets a specific header value from a list of email headers."""
    for header in headers:
        if header['name'].lower() == name.lower():
            return header['value']
    return None


def retrieveMails(max_results=10):
    """
    Retrieves and displays recent emails from the user's Gmail inbox.

    Args:
        max_results (int): The maximum number of emails to retrieve.
    
    Returns:
        list: A list of dictionaries, each containing details of an email.
    """
    print("\n📥 Retrieving recent emails...")
    service = get_google_service('gmail', 'v1', SCOPES)
    if not service:
        return []

    try:
        # Get a list of message IDs from the inbox
        results = service.users().messages().list(userId='me', labelIds=['INBOX'], maxResults=max_results).execute()
        messages = results.get('messages', [])
        
        if not messages:
            print("No new messages found in your inbox.")
            return []

        email_list = []
        print("="*60)
        print(f"📬 Displaying last {len(messages)} emails:")
        print("="*60)

        for i, msg in enumerate(messages):
            # Fetch the full message details for each ID
            msg_data = service.users().messages().get(userId='me', id=msg['id']).execute()
            payload = msg_data.get('payload', {})
            headers = payload.get('headers', [])
            
            # Extract key details
            subject = _get_header(headers, 'Subject')
            sender = _get_header(headers, 'From')
            date = _get_header(headers, 'Date')
            snippet = msg_data.get('snippet', 'No snippet available.')
            
            email_info = {
                'id': msg['id'],
                'threadId': msg['threadId'],
                'subject': subject,
                'from': sender,
                'date': date,
                'snippet': snippet,
                'message_id_header': _get_header(headers, 'Message-ID') # Needed for replies
            }
            email_list.append(email_info)

            # Print a clean summary
            print(f"[{i + 1}] From: {sender}")
            print(f"    Subject: {subject}")
            print(f"    Snippet: {snippet[:100]}...")
            print("-" * 30)
            
        return email_list

    except HttpError as error:
        print(f"❌ An error occurred while retrieving emails: {error}")
        return []


retrieveMails()