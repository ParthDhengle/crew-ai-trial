import os
import smtplib
import re
from email.mime.text import MIMEText
from crewai import Agent, Task, Crew, Process, LLM
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
import base64

# Gmail API Configuration
SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.send",
]

def get_service():
    """Authenticate and return Gmail API service"""
    creds = None
    try:
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)
    except Exception:
        flow = InstalledAppFlow.from_client_secrets_file("client_secret.json", SCOPES)
        creds = flow.run_local_server(port=0)
        with open("token.json", "w") as token:
            token.write(creds.to_json())
    return build("gmail", "v1", credentials=creds)

def clean_snippet(text):
    """Remove zero-width & BOM-like characters"""
    return re.sub(r'[\u200c\ufeff\u200b\u200d]', '', text)

def retrieveMails(from_email, limit=3):
    """Retrieve last N emails from a specific sender"""
    service = get_service()
    query = f"from:{from_email}"
    results = service.users().messages().list(userId="me", q=query, maxResults=limit).execute()
    messages = results.get("messages", [])
    mails = []
    for msg in messages:
        msg_data = service.users().messages().get(userId="me", id=msg["id"]).execute()
        headers = msg_data["payload"]["headers"]
        subject = next((h["value"] for h in headers if h["name"] == "Subject"), "No Subject")
        sender = next((h["value"] for h in headers if h["name"] == "From"), "Unknown Sender")
        snippet = msg_data.get("snippet", "")
        mails.append({
            "from": sender, 
            "subject": subject, 
            "snippet": clean_snippet(snippet)
        })
    return mails

def searchMail(keyword, limit=5):
    """Search mails with a keyword (subject, body, or sender)"""
    service = get_service()
    results = service.users().messages().list(userId="me", q=keyword, maxResults=limit).execute()
    messages = results.get("messages", [])
    mails = []
    for msg in messages:
        msg_data = service.users().messages().get(userId="me", id=msg["id"]).execute()
        headers = msg_data["payload"]["headers"]
        subject = next((h["value"] for h in headers if h["name"] == "Subject"), "No Subject")
        sender = next((h["value"] for h in headers if h["name"] == "From"), "Unknown Sender")
        snippet = msg_data.get("snippet", "")
        mails.append({
            "from": sender, 
            "subject": subject, 
            "snippet": clean_snippet(snippet)
        })
    return mails

def writeMail(to, subject, body):
    """Send an email using Gmail API"""
    service = get_service()
    message = MIMEText(body)
    message["to"] = to
    message["subject"] = subject
    raw = base64.urlsafe_b64encode(message.as_bytes()).decode()

    send_message = service.users().messages().send(
        userId="me", body={"raw": raw}
    ).execute()
    return send_message

def format_email_context(emails):
    """Format retrieved emails for LLM context"""
    if not emails:
        return ""
    
    context = "\n--- EMAIL CONVERSATION HISTORY ---\n"
    for i, email in enumerate(emails, 1):
        context += f"\nEmail {i}:\n"
        context += f"From: {email['from']}\n"
        context += f"Subject: {email['subject']}\n"
        context += f"Content: {email['snippet']}\n"
        context += "-" * 40 + "\n"
    
    return context

def send_email(to, subject, info=None):
    """
    Send email using LLM for content generation with CrewAI
    
    Args:
        to (str): Recipient email address
        subject (str): Email subject
        info (list, optional): List of retrieved emails for context. 
                              Each email should be a dict with 'from', 'subject', 'snippet' keys
    
    Required environment variables based on your LLM choice:
    - For Groq: GROQ_API_KEY
    - For Gemini: GOOGLE_API_KEY or GEMINI_API_KEY
    - For OpenAI: OPENAI_API_KEY
    - For Anthropic: ANTHROPIC_API_KEY
    
    Email credentials (replace these with your actual values):
    - Gmail: Use app password from https://support.google.com/accounts/answer/185833
    """
    
    # Email configuration - Can be set via environment variables for security
    from_email = os.getenv("SENDER_EMAIL", "parthdhengle12@gmail.com")
    password = os.getenv("EMAIL_PASSWORD", "qguxhyduifxtuafv")  # Use app password for Gmail
    smtp_server = "smtp.gmail.com"
    smtp_port = 587
    
    # Validate email configuration
    if not from_email or not password:
        print("❌ Email credentials not configured. Please set:")
        print("   - SENDER_EMAIL environment variable")
        print("   - EMAIL_PASSWORD environment variable (Gmail App Password)")
        return
    
    # Auto-detect available LLM based on API keys
    llm = None
    model_name = None
    
    # Check for Groq API key first
    if os.getenv("GROQ_API_KEY"):
        try:
            model_name = "groq/llama3-8b-8192"
            llm = LLM(
                model=model_name,
                api_key=os.getenv("GROQ_API_KEY")
            )
            print(f"✅ Using Groq LLM: {model_name}")
        except Exception as e:
            print(f"❌ Failed to initialize Groq LLM: {e}")
    
    # Fallback to Gemini
    elif os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY"):
        try:
            model_name = "gemini/gemini-1.5-flash"
            api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
            llm = LLM(
                model=model_name,
                api_key=api_key
            )
            print(f"✅ Using Gemini LLM: {model_name}")
        except Exception as e:
            print(f"❌ Failed to initialize Gemini LLM: {e}")
    
    # Fallback to OpenAI
    elif os.getenv("OPENAI_API_KEY"):
        try:
            model_name = "openai/gpt-3.5-turbo"
            llm = LLM(
                model=model_name,
                api_key=os.getenv("OPENAI_API_KEY")
            )
            print(f"✅ Using OpenAI LLM: {model_name}")
        except Exception as e:
            print(f"❌ Failed to initialize OpenAI LLM: {e}")
    
    # Fallback to Anthropic
    elif os.getenv("ANTHROPIC_API_KEY"):
        try:
            model_name = "anthropic/claude-3-haiku-20240307"
            llm = LLM(
                model=model_name,
                api_key=os.getenv("ANTHROPIC_API_KEY")
            )
            print(f"✅ Using Anthropic LLM: {model_name}")
        except Exception as e:
            print(f"❌ Failed to initialize Anthropic LLM: {e}")
    
    if not llm:
        print("❌ No valid API key found. Please set one of the following environment variables:")
        print("   - GROQ_API_KEY (for Groq)")
        print("   - GOOGLE_API_KEY or GEMINI_API_KEY (for Gemini)")
        print("   - OPENAI_API_KEY (for OpenAI)")
        print("   - ANTHROPIC_API_KEY (for Anthropic)")
        return
    
    # Format email context if provided
    email_context = ""
    if info:
        email_context = format_email_context(info)
        print(f"📧 Using context from {len(info)} previous emails")
    
    # Define the email drafting agent with enhanced context awareness
    email_drafter = Agent(
        role="Professional Email Writer & Reply Specialist",
        goal=f"Create a professional, contextually relevant email to {to} with subject '{subject}', taking into account any previous email conversation history",
        backstory="You are an experienced business communication specialist who excels at writing clear, professional emails. You're particularly skilled at crafting appropriate responses that acknowledge previous correspondence and maintain conversation continuity while achieving the intended purpose.",
        llm=llm,
        verbose=False
    )
    
    # Get initial email description from user
    if info:
        print("\n📨 Previous email context detected. The LLM will use this to craft a relevant response.")
        description = input("Please describe what you want to communicate (or type 'reply' for a general response): ").strip()
    else:
        description = input("Please provide a description for the email content: ").strip()
    
    if not description:
        print("❌ Email description is required.")
        return
    
    iteration = 1
    while True:
        print(f"\n📝 Generating email draft (attempt {iteration})...")
        
        # Create enhanced email drafting task with context
        task_description = f"""
        Write a professional email with the following requirements:
        - Recipient: {to}
        - Subject: {subject}
        - Content based on: {description}
        
        {email_context}
        
        Guidelines:
        - Keep it concise and professional
        - Use appropriate greeting and closing
        - Ensure clear and polite tone
        - Include all necessary information
        - Make it actionable if needed
        {"- This appears to be a reply to previous emails, so acknowledge the conversation history appropriately" if info else ""}
        {"- Reference relevant points from the previous emails when appropriate" if info else ""}
        {"- Maintain conversation continuity and context" if info else ""}
        
        Return only the email body text without subject line or recipient info.
        """
        
        email_task = Task(
            description=task_description,
            expected_output="A professional email body in plain text format that appropriately responds to any provided email context",
            agent=email_drafter
        )
        
        # Create and execute crew
        email_crew = Crew(
            agents=[email_drafter],
            tasks=[email_task],
            process=Process.sequential,
            verbose=False
        )
        
        try:
            result = email_crew.kickoff()
            # Handle different result types from CrewAI
            if hasattr(result, 'raw'):
                body = result.raw.strip()
            elif hasattr(result, 'output'):
                body = result.output.strip()
            else:
                body = str(result).strip()
                
        except Exception as e:
            print(f"❌ Error generating email: {e}")
            retry = input("Would you like to try again? (yes/no): ").strip().lower()
            if retry != 'yes':
                return
            iteration += 1
            continue
        
        # Display the generated email with context info
        print("\n" + "="*60)
        print("📧 GENERATED EMAIL PREVIEW")
        print("="*60)
        print(f"To: {to}")
        print(f"Subject: {subject}")
        print(f"From: {from_email}")
        if info:
            print(f"Context: Replying to conversation with {len(info)} previous emails")
        print("-" * 60)
        print(body)
        print("="*60)
        
        # Get user confirmation
        while True:
            choice = input("\nChoose an action:\n1. Send email (yes)\n2. Provide feedback and regenerate (feedback)\n3. Cancel (no)\nYour choice: ").strip().lower()
            
            if choice in ['yes', '1', 'y']:
                # Send the email using Gmail API (preferred) or SMTP as fallback
                try:
                    # Try Gmail API first
                    try:
                        send_message = writeMail(to, subject, body)
                        print("✅ Email sent successfully via Gmail API!")
                        print(f"📧 Sent to: {to}")
                        print(f"📝 Subject: {subject}")
                        print(f"🆔 Message ID: {send_message.get('id', 'N/A')}")
                        return
                    except Exception as api_error:
                        print(f"⚠️ Gmail API failed ({api_error}), falling back to SMTP...")
                        
                        # Fallback to SMTP
                        msg = MIMEText(body, 'plain', 'utf-8')
                        msg['Subject'] = subject
                        msg['From'] = from_email
                        msg['To'] = to
                        
                        server = smtplib.SMTP(smtp_server, smtp_port)
                        server.starttls()
                        server.login(from_email, password)
                        server.sendmail(from_email, [to], msg.as_string())
                        server.quit()
                        
                        print("✅ Email sent successfully via SMTP!")
                        print(f"📧 Sent to: {to}")
                        print(f"📝 Subject: {subject}")
                        return
                        
                except Exception as e:
                    print(f"❌ Error sending email: {e}")
                    print("Please check your email credentials and try again.")
                    return
                    
            elif choice in ['feedback', '2', 'f']:
                feedback = input("\nPlease provide specific feedback or mention missing points: ").strip()
                if feedback:
                    description += f"\n\nUser feedback for improvement: {feedback}"
                    iteration += 1
                    break
                else:
                    print("Please provide some feedback to improve the email.")
                    
            elif choice in ['no', '3', 'n', 'cancel']:
                print("📪 Email cancelled.")
                return
                
            else:
                print("Invalid choice. Please enter 'yes', 'feedback', or 'no'.")

# Enhanced helper function for easy email retrieval and sending
def send_reply_email(to, subject, retrieve_from_email=None, limit=3):
    """
    Convenience function to retrieve emails from a sender and use them as context for reply
    
    Args:
        to (str): Recipient email address
        subject (str): Email subject  
        retrieve_from_email (str, optional): Email address to retrieve previous emails from
        limit (int): Number of previous emails to retrieve for context
    """
    previous_emails = None
    
    if retrieve_from_email:
        print(f"📥 Retrieving last {limit} emails from {retrieve_from_email}...")
        try:
            previous_emails = retrieveMails(retrieve_from_email, limit)
            if previous_emails:
                print(f"✅ Retrieved {len(previous_emails)} emails for context")
                # Display retrieved emails summary
                for i, email in enumerate(previous_emails, 1):
                    print(f"  {i}. {email['subject']} - {email['snippet'][:100]}...")
            else:
                print("⚠️ No emails found from this sender")
        except Exception as e:
            print(f"❌ Error retrieving emails: {e}")
            previous_emails = None
    
    # Send email with context
    send_email(to, subject, info=previous_emails)

# Example usage functions
def example_usage():
    """Example usage of the enhanced email system"""
    
    # Example 1: Send a regular email without context
    print("=== Example 1: Regular Email ===")
    #send_email("deoatharva44@gmail.com", "Updated Project Proposal")
    
    # Example 2: Send email with manually retrieved context
    print("\n=== Example 2: Email with Retrieved Context ===")
    #previous_emails = retrieveMails("pradnya@ycstech.in", limit=2)
    #print(previous_emails)
    # send_email("recipient@example.com", "Re: Your Inquiry", info=previous_emails)
    
    # Example 3: Use convenience function for reply
    print("\n=== Example 3: Reply Email (Convenience Function) ===")
    send_reply_email("recipient@example.com", "Re: Your Question", 
                     retrieve_from_email="recipient@example.com", limit=3)
    
    # Example 4: Search and use specific emails as context
    print("\n=== Example 4: Using Search Results as Context ===")
    #search_results = searchMail("project", limit=2)
    # send_email("team@example.com", "Project Update", info=search_results)

if __name__ == "__main__":
    # Uncomment to run examples
    example_usage()
    pass