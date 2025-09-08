import os
import logging
from typing import Tuple, List, Dict, Optional
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from google.oauth2.credentials import Credentials
import base64
import json
from crewai import Agent, Task, LLM
from common_functions.Find_project_root import find_project_root

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def get_gmail_service(project_root: Optional[str] = None):
    """Authenticate with Gmail API and return a service object."""
    if project_root is None:
        project_root = find_project_root()

    token_file = os.path.join(project_root, "token.json")
    client_secret_file = os.path.join(project_root, "client_secret.json")
    SCOPES = ["https://mail.google.com/"]
    creds = None
    if os.path.exists(token_file):
        creds = Credentials.from_authorized_user_file(token_file, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists(client_secret_file):
                logger.error("❌ client_secret.json missing in project root")
                return None
            flow = InstalledAppFlow.from_client_secrets_file(client_secret_file, SCOPES)
            creds = flow.run_local_server(port=0)

        with open(token_file, "w") as token:
            token.write(creds.to_json())
            logger.info("✅ Token saved.")

    try:
        return build("gmail", "v1", credentials=creds)
    except HttpError as error:
        logger.error(f"❌ Gmail API error: {error}")
        return None


def get_llm_chain() -> List[LLM]:
    """Return list of available LLMs with API keys."""
    keys = [
        os.getenv("GEMINI_API_KEY1"),
        os.getenv("GEMINI_API_KEY2"),
        os.getenv("GEMINI_API_KEY3"),
        os.getenv("GEMINI_API_KEY4"),
    ]
    llms = []
    for key in keys:
        if key:
            llms.append(LLM(model="gemini/gemini-1.5-flash-latest", api_key=key))
    return llms


def search_emails(service, keyword: str, limit: int = 10) -> List[Dict]:
    """Search emails by keyword and return email data."""
    try:
        # Search query - searches in subject, body, and from fields
        query = f"{keyword}"
        
        # Get list of messages
        results = service.users().messages().list(
            userId='me',
            q=query,
            maxResults=limit
        ).execute()
        
        messages = results.get('messages', [])
        if not messages:
            return []
        
        email_data = []
        for message in messages:
            try:
                # Get full message details
                msg = service.users().messages().get(
                    userId='me',
                    id=message['id'],
                    format='full'
                ).execute()
                
                # Extract headers
                headers = msg['payload'].get('headers', [])
                subject = next((h['value'] for h in headers if h['name'] == 'Subject'), 'No Subject')
                sender = next((h['value'] for h in headers if h['name'] == 'From'), 'Unknown Sender')
                date = next((h['value'] for h in headers if h['name'] == 'Date'), 'Unknown Date')
                
                # Extract body
                body = extract_email_body(msg['payload'])
                
                email_data.append({
                    'id': message['id'],
                    'subject': subject,
                    'sender': sender,
                    'date': date,
                    'body': body[:500] + '...' if len(body) > 500 else body  # Truncate long bodies
                })
                
            except Exception as e:
                logger.warning(f"⚠️ Error processing message {message['id']}: {e}")
                continue
                
        return email_data
        
    except HttpError as error:
        logger.error(f"❌ Gmail API error during search: {error}")
        return []


def extract_email_body(payload) -> str:
    """Extract email body from Gmail API payload."""
    body = ""
    
    if 'parts' in payload:
        for part in payload['parts']:
            if part['mimeType'] == 'text/plain':
                data = part['body']['data']
                body = base64.urlsafe_b64decode(data).decode('utf-8')
                break
            elif part['mimeType'] == 'text/html':
                # If no plain text, use HTML as fallback
                if not body:
                    data = part['body']['data']
                    body = base64.urlsafe_b64decode(data).decode('utf-8')
    else:
        # Single part message
        if payload['mimeType'] == 'text/plain':
            data = payload['body']['data']
            body = base64.urlsafe_b64decode(data).decode('utf-8')
        elif payload['mimeType'] == 'text/html':
            data = payload['body']['data']
            body = base64.urlsafe_b64decode(data).decode('utf-8')
    
    return body.strip()


def generate_ai_response(emails: List[Dict], keyword: str) -> str:
    """Generate AI response about found emails."""
    llms = get_llm_chain()
    if not llms:
        logger.warning("⚠️ No LLM API keys available, generating basic response")
        return generate_basic_response(emails, keyword)

    logger.info(f"🔧 Available LLMs: {len(llms)}")
    
    for i, llm in enumerate(llms):
        try:
            logger.info(f"🤖 Trying LLM {i+1}/{len(llms)}...")
            
            agent = Agent(
                role="Email Analysis Assistant",
                goal="Analyze found emails and provide helpful summaries about what senders are asking, telling, or requesting",
                backstory="Expert at analyzing email content and providing concise, helpful summaries of email communications",
                llm=llm,
                verbose=False
            )

            # Prepare email summaries for AI
            email_summaries = []
            for email in emails[:5]:  # Limit to first 5 emails to avoid token limits
                email_summaries.append({
                    'subject': email['subject'],
                    'sender': email['sender'],
                    'date': email['date'],
                    'body_preview': email['body'][:300]  # First 300 chars
                })

            task = Task(
                description=f"""
                I found {len(emails)} email(s) matching the keyword '{keyword}'.
                
                Here are the email details:
                {json.dumps(email_summaries, indent=2)}
                
                Please provide a friendly, helpful response that:
                1. Confirms that emails were found
                2. Summarizes what each sender is asking about, telling about, or requesting
                3. Highlights the key topics or themes
                4. Uses a conversational, helpful tone
                
                Keep the response concise but informative. Focus on what's actionable or important for the user to know.
                """,
                expected_output="A friendly, conversational response summarizing the found emails and what the senders are communicating about",
                agent=agent
            )

            result = agent.execute_task(task)
            ai_response = str(result).strip()
            
            logger.info("✅ Successfully generated AI response")
            return ai_response
            
        except Exception as e:
            error_msg = str(e)
            logger.warning(f"⚠️ LLM {i+1} failed: {error_msg}")
            
            if "429" in error_msg or "RATE_LIMIT_EXCEEDED" in error_msg or "Quota exceeded" in error_msg:
                logger.info(f"🔄 Rate limit hit on LLM {i+1}, trying next LLM...")
                continue
            elif "401" in error_msg or "403" in error_msg:
                logger.warning(f"🔑 Authentication error on LLM {i+1}, trying next LLM...")
                continue
            else:
                logger.warning(f"❌ Unknown error on LLM {i+1}: {error_msg}")
                continue
    
    # If all LLMs failed, return basic response
    logger.error("❌ All LLMs failed! Generating basic response.")
    return generate_basic_response(emails, keyword)


def generate_basic_response(emails: List[Dict], keyword: str) -> str:
    """Generate basic response when AI is unavailable."""
    if not emails:
        return f"No emails found matching '{keyword}'."
    
    response = f"✅ Found {len(emails)} email(s) matching '{keyword}':\n\n"
    
    for i, email in enumerate(emails[:3], 1):  # Show first 3 emails
        sender_name = email['sender'].split('<')[0].strip() if '<' in email['sender'] else email['sender']
        response += f"{i}. From: {sender_name}\n"
        response += f"   Subject: {email['subject']}\n"
        response += f"   Date: {email['date']}\n\n"
    
    if len(emails) > 3:
        response += f"... and {len(emails) - 3} more emails.\n"
    
    return response


def searchMail(keyword: str, limit=None) -> Tuple[bool, str]:
    """
    Searches emails by keyword in subject, body, or sender and provides AI-generated response.
    
    Args:
        keyword (str): The keyword to search for
        limit (int, optional): Maximum number of emails to retrieve (default: 10)
    
    Returns:
        Tuple[bool, str]: (Success status, AI-generated response about found emails)
    """
    try:
        if limit is None:
            limit = 10
        
        # Validate inputs
        if not keyword or not keyword.strip():
            return False, "❌ Keyword cannot be empty"
        
        if not isinstance(limit, int) or limit <= 0:
            limit = 10
        
        # Limit maximum results to avoid overwhelming responses
        if limit > 50:
            limit = 50
        
        logger.info(f"🔍 Searching emails with keyword: '{keyword}', limit: {limit}")
        
        # Get Gmail service
        service = get_gmail_service()
        if not service:
            return False, "❌ Failed to authenticate with Gmail API"
        
        # Search emails
        emails = search_emails(service, keyword.strip(), limit)
        
        if not emails:
            return True, f"No emails found matching '{keyword}'. Try different keywords or check your spelling."
        
        logger.info(f"📧 Found {len(emails)} emails")
        
        # Generate AI response about the emails
        ai_response = generate_ai_response(emails, keyword)
        
        return True, ai_response
        
    except Exception as e:
        logger.error(f"❌ Error in searchMail: {e}")
        return False, f"❌ Error searching emails: {str(e)}"
    
    
print(searchMail("Manoj"))