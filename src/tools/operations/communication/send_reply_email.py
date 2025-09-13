import os
import re
import json
import base64
import logging
from typing import Optional, Dict, List
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from crewai import Agent, Task, LLM
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from google.oauth2.credentials import Credentials
from common_functions.Find_project_root import find_project_root
from memory_manager import MemoryManager

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


def find_email_in_kb(name: str, project_root: Optional[str] = None) -> Optional[str]:
    """Search knowledge base for email address."""
    if project_root is None:
        project_root = find_project_root()

    user_profile = os.path.join(project_root, "knowledge", "user_profile.json")
    memory_dir = os.path.join(project_root, "knowledge", "memory")

    mm = MemoryManager()

    # Search in user profile
    if os.path.exists(user_profile):
        try:
            with open(user_profile, "r", encoding="utf-8") as f:
                profile = json.load(f)
            for key, value in profile.items():
                if (name.lower() in str(key).lower() or name.lower() in str(value).lower()):
                    if isinstance(value, str) and is_valid_email(value):
                        return value
        except Exception:
            pass

    # Search in long-term memory (RAG)
    try:
        long_term = mm.retrieve_long_term(name)
        if long_term:
            emails = extract_emails(str(long_term))
            if emails:
                return emails[0]
    except Exception:
        pass

    short_term_dir = os.path.join(memory_dir, "short_term")
    if os.path.exists(short_term_dir):
        for file in os.listdir(short_term_dir):
            if not file.endswith(".json"):
                continue
            try:
                with open(os.path.join(short_term_dir, file), "r", encoding="utf-8") as f:
                    history = json.load(f)
                for entry in history if isinstance(history, list) else []:
                    if name.lower() in json.dumps(entry).lower():
                        emails = extract_emails(json.dumps(entry))
                        if emails:
                            return emails[0]
            except Exception:
                continue

    return None


def extract_emails(text: str) -> List[str]:
    """Extract emails from text."""
    return re.findall(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b", text)


def is_valid_email(email: str) -> bool:
    return bool(re.match(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$", email))


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


def load_user_profile(project_root: str) -> dict:
    """Load user profile JSON and return only relevant fields for email writing."""
    profile_path = os.path.join(project_root, "knowledge", "user_profile.json")
    if not os.path.exists(profile_path):
        return {}

    with open(profile_path, "r", encoding="utf-8") as f:
        profile = json.load(f)

    # Extract only relevant info
    return {
        "name": profile.get("Name"),
        "role": profile.get("Role"),
        "email": profile.get("email"),
        "contact": profile.get("contacts")
    }



def _get_header(headers, name):
    """Gets a specific header value from a list of email headers."""
    for header in headers:
        if header['name'].lower() == name.lower():
            return header['value']
    return None


def get_email_body(payload):
    """Extract the email body from the message payload."""
    body = ""
    
    if 'parts' in payload:
        for part in payload['parts']:
            if part['mimeType'] == 'text/plain':
                data = part['body']['data']
                body = base64.urlsafe_b64decode(data).decode('utf-8')
                break
            elif part['mimeType'] == 'text/html' and not body:
                data = part['body']['data']
                body = base64.urlsafe_b64decode(data).decode('utf-8')
    else:
        if payload['mimeType'] == 'text/plain':
            data = payload['body']['data']
            body = base64.urlsafe_b64decode(data).decode('utf-8')
    
    return body


def retrieve_emails_from_sender(sender_email: str, max_results: int = 5, project_root: Optional[str] = None) -> List[Dict]:
    """
    Retrieve recent emails from a specific sender.
    
    Args:
        sender_email (str): Email address of the sender
        max_results (int): Maximum number of emails to retrieve
        project_root (str): Project root directory
    
    Returns:
        list: A list of dictionaries containing email details
    """
    logger.info(f"📥 Retrieving emails from: {sender_email}")
    service = get_gmail_service(project_root)
    if not service:
        return []

    try:
        # Search for emails from the specific sender
        query = f"from:{sender_email}"
        results = service.users().messages().list(
            userId='me', 
            q=query, 
            maxResults=max_results
        ).execute()
        
        messages = results.get('messages', [])
        
        if not messages:
            logger.info(f"No emails found from {sender_email}")
            return []

        email_list = []
        logger.info(f"📬 Found {len(messages)} emails from {sender_email}")

        for i, msg in enumerate(messages):
            try:
                # Fetch the full message details
                msg_data = service.users().messages().get(userId='me', id=msg['id']).execute()
                payload = msg_data.get('payload', {})
                headers = payload.get('headers', [])
                
                # Extract key details
                subject = _get_header(headers, 'Subject')
                sender = _get_header(headers, 'From')
                date = _get_header(headers, 'Date')
                snippet = msg_data.get('snippet', 'No snippet available.')
                body = get_email_body(payload)
                
                email_info = {
                    'id': msg['id'],
                    'threadId': msg['threadId'],
                    'subject': subject,
                    'from': sender,
                    'date': date,
                    'snippet': snippet,
                    'body': body,
                    'message_id_header': _get_header(headers, 'Message-ID')
                }
                email_list.append(email_info)
                
                logger.info(f"[{i + 1}] Subject: {subject}")
                
            except Exception as e:
                logger.warning(f"Error processing email {i+1}: {e}")
                continue
                
        return email_list

    except HttpError as error:
        logger.error(f"❌ An error occurred while retrieving emails: {error}")
        return []


# ------------------ AI Response Generation ------------------

def generate_reply_with_fallback(original_email: Dict, description: str, project_root: Optional[str] = None) -> str:
    """Generate email reply using Gemini AI with fallback mechanism."""
    llms = get_llm_chain()
    if not llms:
        logger.warning("⚠️ No LLM API keys available")
        return f"Thank you for your email regarding '{original_email.get('subject', 'your message')}'. {description}"

    logger.info(f"🔧 Available LLMs: {len(llms)}")
    
    for i, llm in enumerate(llms):
        try:
            logger.info(f"🤖 Trying LLM {i+1}/{len(llms)}...")
            user_info = load_user_profile(project_root or find_project_root())
            
            agent = Agent(
                role="Professional Email Responder",
                goal=f"Write professional email replies on behalf of {user_info.get('name', 'the user')} "
                    f"(Role: {user_info.get('role', 'N/A')}). "
                    f"Craft contextual responses that address the original email content.",
                backstory="Expert in professional email communication with years of experience in corporate correspondence and client relations.",
                llm=llm,
                verbose=False
            )

            task = Task(
                description=f"""
                User identity:
                - Name: {user_info.get('name')}
                - Role: {user_info.get('role')}
                - Email: {user_info.get('email')}
                - Contact: {user_info.get('contact')}

                Original email details:
                - From: {original_email.get('from')}
                - Subject: {original_email.get('subject')}
                - Date: {original_email.get('date')}
                - Content: {original_email.get('body', original_email.get('snippet', ''))}

                Reply instruction/description: {description}

                Please craft a professional email reply that:
                - Directly addresses the content and context of the original email
                - Incorporates the user's instruction: {description}
                - Maintains a professional and appropriate tone
                - Includes proper email structure with greeting and closing
                - Signs off with the user's name and contact information
                - Is clear, concise, and actionable

                Do NOT include the subject line in your response, only the email body.
                """,
                expected_output="A complete professional email reply body that addresses the original email and incorporates the user's instructions.",
                agent=agent
            )

            result = agent.execute_task(task)
            reply_body = str(result).strip()

            logger.info("✅ Successfully generated reply using LLM")
            return reply_body
            
        except Exception as e:
            error_msg = str(e)
            logger.warning(f"⚠️ LLM {i+1} failed: {error_msg}")
            
            # Check if it's a rate limit error
            if "429" in error_msg or "RATE_LIMIT_EXCEEDED" in error_msg or "Quota exceeded" in error_msg:
                logger.info(f"🔄 Rate limit hit on LLM {i+1}, trying next LLM...")
                continue
            elif "401" in error_msg or "403" in error_msg:
                logger.warning(f"🔑 Authentication error on LLM {i+1}, trying next LLM...")
                continue
            else:
                logger.warning(f"❌ Unknown error on LLM {i+1}: {error_msg}")
                continue
    
    logger.error("❌ All LLMs failed! Returning basic reply.")
    print("⚠️ Warning: Unable to generate AI reply due to API issues. Using basic template.")
    return f"Thank you for your email regarding '{original_email.get('subject', 'your message')}'. {description}"


def refine_reply_with_fallback(body: str, feedback: str, original_email: Dict) -> str:
    """Refine reply using Gemini AI with fallback mechanism."""
    llms = get_llm_chain()
    if not llms:
        logger.warning("⚠️ No LLM API keys available, returning original body")
        return body

    logger.info(f"🔧 Available LLMs: {len(llms)}")
    
    for i, llm in enumerate(llms):
        try:
            logger.info(f"🤖 Trying LLM {i+1}/{len(llms)}...")
            user_info = load_user_profile(project_root=find_project_root())
            
            agent = Agent(
                role="Professional Email Editor",
                goal=f"Refine and improve email replies on behalf of {user_info.get('name', 'the user')} "
                    f"based on user feedback while maintaining professional standards.",
                backstory="Expert in email editing and refinement with attention to tone, clarity, and professional communication.",
                llm=llm,
                verbose=False
            )

            task = Task(
                description=f"""
                User identity:
                - Name: {user_info.get('name')}
                - Role: {user_info.get('role')}
                - Email: {user_info.get('email')}
                - Contact: {user_info.get('contact')}

                Original email being replied to:
                - From: {original_email.get('from')}
                - Subject: {original_email.get('subject')}
                
                Current reply body:
                {body}

                User feedback for improvement:
                {feedback}

                Please refine this email reply incorporating the user's feedback while maintaining:
                - Professional tone and language
                - Contextual relevance to the original email
                - Clear and effective communication
                - Proper email structure and closing
                """,
                expected_output="A refined, professional email reply body that incorporates the feedback.",
                agent=agent
            )

            result = agent.execute_task(task)
            refined_body = str(result).strip()

            logger.info("✅ Successfully refined reply using LLM")
            return refined_body
            
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
    
    logger.error("❌ All LLMs failed! Returning original reply body.")
    print("⚠️ Warning: Unable to refine reply due to API issues. Using original content.")
    return body


def _send_reply_via_gmail(service, recipient: str, subject: str, body: str, thread_id: str, original_message_id: str) -> bool:
    """Send reply email via Gmail API."""
    try:
        message = MIMEMultipart()
        message['to'] = recipient
        message['subject'] = subject
        message['In-Reply-To'] = original_message_id
        message['References'] = original_message_id
        
        message.attach(MIMEText(body, 'plain'))
        
        raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
        
        send_payload = {
            'raw': raw_message,
            'threadId': thread_id
        }

        service.users().messages().send(userId='me', body=send_payload).execute()
        logger.info("✅ Reply sent successfully!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error sending reply: {e}")
        return False


# ------------------ Main Reply Function ------------------

def send_reply_email(to: str, description: str, limit: int = 5, project_root: Optional[str] = None) -> bool:
    """
    Send a contextual reply to recent emails from a specific sender.
    
    Args:
        to (str): Email address or name of the sender to reply to
        description (str): Description/instruction for the reply content
        limit (int): Number of recent emails to retrieve (default: 5)
        project_root (str): Project root directory
    
    Returns:
        bool: True if reply sent successfully, False otherwise
    """
    logger.info(f"📧 Starting reply workflow for: {to}")
    
    # Resolve email address
    sender_email = to if is_valid_email(to) else find_email_in_kb(to, project_root)
    
    if not sender_email:
        sender_email = input(f"❌ No email found for '{to}'. Enter a valid email: ").strip()
        if not is_valid_email(sender_email):
            logger.error("❌ Invalid email address provided.")
            return False

    # Retrieve recent emails from the sender
    recent_emails = retrieve_emails_from_sender(sender_email, limit, project_root)
    
    if not recent_emails:
        logger.error(f"❌ No emails found from {sender_email}")
        return False

    # Let user select which email to reply to
    print("\n" + "="*60)
    print(f"📬 Recent emails from {sender_email}:")
    print("="*60)
    
    for i, email in enumerate(recent_emails):
        print(f"[{i + 1}] Subject: {email['subject']}")
        print(f"    Date: {email['date']}")
        print(f"    Snippet: {email['snippet'][:100]}...")
        print("-" * 40)

    try:
        choice_idx = int(input(f"\nEnter the number of the email to reply to (1-{len(recent_emails)}): ")) - 1
        if not (0 <= choice_idx < len(recent_emails)):
            logger.error("❌ Invalid selection.")
            return False
        
        email_to_reply = recent_emails[choice_idx]
        
    except (ValueError, IndexError):
        logger.error("❌ Invalid input. Please enter a valid number.")
        return False

    # Prepare reply details
    original_subject = email_to_reply['subject']
    reply_subject = f"Re: {original_subject}" if not original_subject.lower().startswith("re:") else original_subject
    thread_id = email_to_reply['threadId']
    original_message_id = email_to_reply['message_id_header']

    logger.info(f"📝 Generating reply to: {original_subject}")
    
    # Generate reply using AI
    reply_body = generate_reply_with_fallback(email_to_reply, description, project_root)

    service = get_gmail_service(project_root)
    if not service:
        return False

    while True:
        # Preview
        print("\n" + "="*50)
        print("EMAIL REPLY PREVIEW")
        print("="*50)
        print(f"To: {sender_email}")
        print(f"Subject: {reply_subject}")
        print(f"In Reply To: {original_subject}\n")
        print(reply_body)
        print("="*50)

        choice = input("\nIs this reply okay? (yes/no): ").strip().lower()
        if choice in ["yes", "y"]:
            return _send_reply_via_gmail(
                service, sender_email, reply_subject, reply_body, 
                thread_id, original_message_id
            )
        else:
            feedback = input("Enter changes or feedback: ").strip()
            print("\n🤖 Refining reply with AI assistance...")
            reply_body = refine_reply_with_fallback(reply_body, feedback, email_to_reply)


# ------------------ Convenience Function ------------------

def retrieve_from_email(sender_email: str, limit: int = 10, project_root: Optional[str] = None) -> List[Dict]:
    """
    Convenience function to just retrieve emails from a sender without sending a reply.
    
    Args:
        sender_email (str): Email address of the sender
        limit (int): Maximum number of emails to retrieve
        project_root (str): Project root directory
    
    Returns:
        list: List of email dictionaries
    """
    return retrieve_emails_from_sender(sender_email, limit, project_root)


if __name__ == "__main__":
    # Example usage
    print("📧 Email Reply System")
    send_reply_email(to="Atharva Deo", description="Please provide updates on the project status.", limit=5)