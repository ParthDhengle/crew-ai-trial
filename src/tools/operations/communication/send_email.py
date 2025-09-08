import os
import re
import json
import smtplib
from email.mime.text import MIMEText
from crewai import Agent, Crew, Process, Task, LLM

from common_functions.Find_project_root import find_project_root
from memory_manager import MemoryManager


# --- CONFIG ---
PROJECT_ROOT = find_project_root()
USER_PROFILE_PATH = os.path.join(PROJECT_ROOT, "knowledge", "user_profile.json")
MEMORY_DIR = os.path.join(PROJECT_ROOT, "knowledge", "memory")


# --- KB SEARCH (optimized for email only) ---
def search_KB(parameter: str):
    """
    Searches the knowledge base only for email addresses related to the parameter.
    Returns dict like: {'email': 'abc@example.com', 'source': 'user_profile'}
    or None if not found.
    """
    results = {}
    memory_manager = MemoryManager()

    # 1. Search user_profile.json
    if os.path.exists(USER_PROFILE_PATH):
        with open(USER_PROFILE_PATH, "r", encoding="utf-8") as f:
            profile = json.load(f)
            for key, value in profile.items():
                if parameter.lower() in str(key).lower() or parameter.lower() in str(value).lower():
                    if isinstance(value, str) and re.match(r"[^@]+@[^@]+\.[^@]+", value):
                        return {"email": value, "source": "user_profile"}

    # 2. Search long-term memory (RAG)
    long_term_result = memory_manager.retrieve_long_term(parameter)
    if long_term_result:
        emails = re.findall(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b", str(long_term_result))
        if emails:
            return {"email": emails[0], "source": "long_term"}

    # 3. Search short-term chat history
    short_term_dir = os.path.join(MEMORY_DIR, "short_term")
    if os.path.exists(short_term_dir):
        for file_name in os.listdir(short_term_dir):
            if file_name.endswith(".json"):
                file_path = os.path.join(short_term_dir, file_name)
                with open(file_path, "r", encoding="utf-8") as f:
                    history = json.load(f)
                    for entry in history:
                        emails = re.findall(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b", json.dumps(entry))
                        if emails:
                            return {"email": emails[0], "source": "short_term"}

    return None


# --- SEND EMAIL ---
def send_email(to, subject, body):
    """
    Sends an AI-generated email to the specified recipient with user approval.
    Args:
        to (str): Recipient email address or name (will check KB if not in email format).
        subject (str): Subject of the email.
        body (str): Initial draft of the email (user-provided).
    """

    # Step 1: Resolve recipient email
    email_pattern = r"[^@]+@[^@]+\.[^@]+"
    recipient_email = None

    if re.match(email_pattern, to):
        recipient_email = to
    else:
        print(f"📖 Looking up email for '{to}' in knowledge base...")
        kb_result = search_KB(to)
        if kb_result and "email" in kb_result:
            recipient_email = kb_result["email"]
            print(f"✅ Found email in KB ({kb_result['source']}): {recipient_email}")
        else:
            recipient_email = input(f"❌ No email found for '{to}'. Please enter a valid email: ").strip()

    if not re.match(email_pattern, recipient_email):
        print("❌ Invalid email address provided. Exiting.")
        return

    # Step 2: Configure sender credentials
    from_email = os.getenv("SENDER_EMAIL", "your_email@gmail.com")
    password = os.getenv("EMAIL_PASSWORD", "your_app_password")

    if from_email == "your_email@gmail.com" or password == "your_app_password":
        print("❌ Email credentials not configured.")
        print("   Please set environment variables SENDER_EMAIL and EMAIL_PASSWORD.")
        return

    # Step 3: Setup LLM agent
    try:
        llm = LLM(model="ollama/llama3", base_url="http://localhost:11434")
        print("✅ Using local Ollama LLM for refining emails.")
    except Exception as e:
        print(f"❌ Failed to initialize Ollama LLM: {e}")
        return

    email_writer = Agent(
        role="Professional Email Writer",
        goal=f"Write professional and concise emails to {recipient_email} with subject '{subject}'.",
        backstory="You are an expert in writing clear, polite, and professional emails.",
        llm=llm,
        verbose=False
    )

    final_body = body.strip()

    # Step 4: Feedback loop for refinement
    while True:
        print("\n--- Email Preview ---")
        print(f"To: {recipient_email}\nSubject: {subject}\n\n{final_body}")
        print("---------------------")

        choice = input("\nIs this email okay? (yes/no): ").strip().lower()
        if choice in ["yes", "y"]:
            try:
                msg = MIMEText(final_body, "plain", "utf-8")
                msg["Subject"] = subject
                msg["From"] = from_email
                msg["To"] = recipient_email

                server = smtplib.SMTP("smtp.gmail.com", 587)
                server.starttls()
                server.login(from_email, password)
                server.sendmail(from_email, [recipient_email], msg.as_string())
                server.quit()
                print("✅ Email sent successfully!")
            except Exception as e:
                print(f"❌ Error sending email: {e}")
            break
        else:
            feedback = input("Enter changes or feedback for improving the email: ").strip()
            if not feedback:
                print("❌ Feedback cannot be empty. Try again.")
                continue

            refinement_task = Task(
                description=f"Refine the following email draft based on feedback.\n\n"
                            f"Draft:\n{final_body}\n\n"
                            f"Feedback: {feedback}\n\n"
                            f"Return only the improved email body.",
                expected_output="An improved professional email body.",
                agent=email_writer
            )

            email_crew = Crew(agents=[email_writer], tasks=[refinement_task], process=Process.sequential)
            try:
                result = email_crew.kickoff()
                final_body = str(result).strip()
            except Exception as e:
                print(f"❌ Error refining email: {e}")
                return