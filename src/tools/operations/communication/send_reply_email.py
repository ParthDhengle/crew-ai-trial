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

SCOPES = [
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/contacts.readonly"
]
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


def send_reply_email():
    """
    Initiates a workflow to reply to a recent email using an AI agent.
    1. Fetches recent emails.
    2. Asks user to select an email to reply to.
    3. Uses CrewAI to generate a reply body.
    4. Sends the email as a threaded reply using the Gmail API.
    """
    print("\n📧 Initiating Email Reply Workflow...")
    
    # Step 1: Let user choose an email to reply to
    recent_emails = retrieveMails(max_results=5)
    if not recent_emails:
        return

    try:
        choice_idx = int(input("\nEnter the number of the email you want to reply to: ")) - 1
        if not (0 <= choice_idx < len(recent_emails)):
            print("❌ Invalid selection.")
            return
        
        email_to_reply = recent_emails[choice_idx]
        
    except (ValueError, IndexError):
        print("❌ Invalid input. Please enter a valid number.")
        return

    original_subject = email_to_reply['subject']
    original_sender = email_to_reply['from']
    thread_id = email_to_reply['threadId']
    original_message_id = email_to_reply['message_id_header']

    # Prepare reply details
    reply_to_email = original_sender.split('<')[-1].strip('>') # Extract clean email address
    reply_subject = f"Re: {original_subject}" if not original_subject.lower().startswith("re:") else original_subject

    print("\n--- Replying to ---")
    print(f"To: {reply_to_email}")
    print(f"Subject: {reply_subject}")
    print("--------------------")
    
    # Step 2: Use CrewAI to generate reply body (similar to send_email)
    try:
        model_name = "ollama/llama3.1:8b-instruct-q5_0"
        llm = LLM(model="ollama/llama3", base_url="http://localhost:11434")
        print(f"✅ Using local Ollama LLM for operations: {model_name}")
    except Exception as e:
        print(f"❌ Failed to initialize Ollama LLM: {e}")
        return

    email_drafter = Agent(
        role="Professional Email Responder",
        goal=f"Craft a professional and concise reply to an email from {reply_to_email} about '{original_subject}'",
        backstory="You are a skilled communications assistant, expert in drafting clear, polite, and effective email replies.",
        llm=llm,
        verbose=False
    )

    description = input("Please provide a short description for the reply content: ").strip()
    if not description:
        print("❌ Reply description is required.")
        return
        
    email_task = Task(
        description=f"""
        Draft a reply to an email.
        Original Sender: {original_sender}
        Original Subject: {original_subject}
        Your reply should be based on this instruction: {description}
        
        Guidelines:
        - Keep the reply professional and concise.
        - Directly address the points from the instruction.
        - Do NOT include a subject line or greeting (e.g., "Hi John,"). Just provide the main body text.
        """,
        expected_output="A professional email reply body in plain text format.",
        agent=email_drafter
    )

    email_crew = Crew(agents=[email_drafter], tasks=[email_task], process=Process.sequential)
    
    try:
        result = email_crew.kickoff()
        reply_body = str(result).strip()
    except Exception as e:
        print(f"❌ Error generating reply content: {e}")
        return

    print("\n--- Generated Reply Preview ---")
    print(reply_body)
    print("-----------------------------\n")

    # Step 3: Send the reply via Gmail API
    confirm = input("Do you want to send this reply? (yes/no): ").strip().lower()
    if confirm not in ['yes', 'y']:
        print("📪 Reply cancelled.")
        return

    service = get_google_service('gmail', 'v1', SCOPES)
    if not service:
        return

    try:
        message = MIMEMultipart()
        message['to'] = reply_to_email
        message['subject'] = reply_subject
        message['In-Reply-To'] = original_message_id
        message['References'] = original_message_id
        
        message.attach(MIMEText(reply_body, 'plain'))
        
        raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
        
        send_payload = {
            'raw': raw_message,
            'threadId': thread_id # This ensures the reply is threaded correctly
        }

        print("\n📤 Sending reply...")
        sent_message = service.users().messages().send(userId='me', body=send_payload).execute()
        print(f"✅ Reply sent successfully! Message ID: {sent_message['id']}")
        
    except HttpError as error:
        print(f"❌ An error occurred while sending the reply: {error}")
