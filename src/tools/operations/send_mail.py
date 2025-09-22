import os
import re
import json
import base64
import logging
from typing import Optional, Dict, List
from email.mime.text import MIMEText

from crewai import Agent, Task, LLM
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from google.oauth2.credentials import Credentials
from common_functions.Find_project_root import find_project_root
from memory_manager import MemoryManager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ------------------ Gmail Authentication ------------------

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


# ------------------ Knowledge Base Search ------------------

def find_email_in_kb(name: str, project_root: Optional[str] = None) -> Optional[str]:
    """Search knowledge base for email address."""
    if project_root is None:
        project_root = find_project_root()

    user_profile = os.path.join(project_root, "knowledge", "user_profile.json")
    memory_dir = os.path.join(project_root, "knowledge", "memory")
    extracted_facts = os.path.join(memory_dir, "long_term", "extracted_facts.json")

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

    # Search in short-term memory
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


# ------------------ Gemini LLM Handling with Fallback ------------------

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

def refine_email_with_fallback(body: str, feedback: str, recipient: str, subject: str) -> str:
    """Refine email using Gemini AI with fallback mechanism."""
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
                role="Professional Email Writer",
                goal=f"Write professional and concise emails on behalf of {user_info.get('name', 'the user')} "
                    f"(Role: {user_info.get('role', 'N/A')}). "
                    f"Ensure tone matches a professional yet clear communication style.",
                backstory="Expert in professional email writing with years of experience in corporate communication.",
                llm=llm,
                verbose=2
            )

            # Build task with user context included
            task = Task(
                description=f"""
                User identity:
                - Name: {user_info.get('name')}
                - Role: {user_info.get('role')}
                - Email: {user_info.get('email')}
                - Contact: {user_info.get('contact')}

                Original email body:
                {body}

                User feedback for improvement:
                {feedback}

                Please refine this email to be more professional and descriptive while maintaining clarity and conciseness.
                Focus on:
                - Professional tone and language
                - Clear and descriptive content
                - Proper email structure
                - Include a polite closing with the user's name and contact info if appropriate
                """,
                expected_output="A refined, professional email body that incorporates the feedback and includes the user's identity in the signature.",
                agent=agent
            )

            result = agent.execute_task(task)
            refined_body = str(result).strip()

            logger.info("✅ Successfully refined email using LLM")
            return refined_body
            
        except Exception as e:
            error_msg = str(e)
            logger.warning(f"⚠️ LLM {i+1} failed: {error_msg}")
            
            # Check if it's a rate limit error
            if "429" in error_msg or "RATE_LIMIT_EXCEEDED" in error_msg or "Quota exceeded" in error_msg:
                logger.info(f"🔄 Rate limit hit on LLM {i+1}, trying next LLM...")
                continue
            # Check for other common API errors
            elif "401" in error_msg or "403" in error_msg:
                logger.warning(f"🔑 Authentication error on LLM {i+1}, trying next LLM...")
                continue
            else:
                logger.warning(f"❌ Unknown error on LLM {i+1}: {error_msg}")
                continue
    
    # If all LLMs failed, return original body with a warning
    logger.error("❌ All LLMs failed! Returning original email body.")
    print("⚠️ Warning: Unable to refine email due to API issues. Using original content.")
    return body


def refine_email(body: str, feedback: str, recipient: str, subject: str) -> str:
    """Legacy function name - calls the new fallback version."""
    return refine_email_with_fallback(body, feedback, recipient, subject)


# ------------------ Main Send Email Function ------------------

def send_email(to: str, subject: str, body: str, project_root: Optional[str] = None) -> bool:
    """Main function to send email with AI assistance."""
    recipient = to if is_valid_email(to) else find_email_in_kb(to, project_root)

    if not recipient:
        recipient = input(f"❌ No email found for '{to}'. Enter a valid email: ").strip()
        if not is_valid_email(recipient):
            logger.error("❌ Invalid email address provided.")
            return False

    service = get_gmail_service(project_root)
    if not service:
        return False

    final_body = body.strip()

    while True:
        # Preview
        print("\n" + "="*50)
        print("EMAIL PREVIEW")
        print("="*50)
        print(f"To: {recipient}")
        print(f"Subject: {subject}\n")
        print(final_body)
        print("="*50)

        choice = input("\nIs this email okay? (yes/no): ").strip().lower()
        if choice in ["yes", "y"]:
            return _send_via_gmail(service, recipient, subject, final_body)
        else:
            feedback = input("Enter changes or feedback: ").strip()
            print("\n🤖 Refining email with AI assistance...")
            final_body = refine_email(final_body, feedback, recipient, subject)


def _send_via_gmail(service, recipient: str, subject: str, body: str) -> bool:
    """Send email via Gmail API."""
    try:
        msg = MIMEText(body, "plain", "utf-8")
        msg["to"] = recipient
        msg["subject"] = subject
        raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
        message = {"raw": raw}
        service.users().messages().send(userId="me", body=message).execute()
        logger.info("✅ Email sent successfully!")
        return True, "Email sent successfully!"
    except Exception as e:
        logger.error(f"❌ Error sending email: {e}")
        return False, "Error {e}"
