import os
import smtplib
from email.mime.text import MIMEText
from crewai import Agent, Crew, Process, Task, LLM
from twilio.rest import Client
import os.path
import json
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
import platform
import subprocess
from pathlib import Path

def send_email(to, subject):
    """
    Send email using LLM for content generation with CrewAI
   
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
    password = os.getenv("EMAIL_PASSWORD", "qguxhyduifxtuafv") # Use app password for Gmail
    smtp_server = "smtp.gmail.com"
    smtp_port = 587
   
    # Validate email configuration
    if not from_email or not password:
        print("❌ Email credentials not configured. Please set:")
        print(" - SENDER_EMAIL environment variable")
        print(" - EMAIL_PASSWORD environment variable (Gmail App Password)")
        return
   
    # Auto-detect available LLM based on API keys - Use operations_llm (local Ollama)
    llm = None
    model_name = None
   
    # Use local Ollama for operations
    try:
        model_name = "ollama/llama3.1:8b-instruct-q5_0"
        llm = LLM(
            model=model_name,
            base_url="http://localhost:11434",
            api_key="ollama"
        )
        print(f"✅ Using local Ollama LLM for operations: {model_name}")
    except Exception as e:
        print(f"❌ Failed to initialize Ollama LLM: {e}")
        # Fallback to other APIs if needed...
   
    if not llm:
        print("❌ No valid API key found. Please set one of the following environment variables:")
        print(" - GROQ_API_KEY (for Groq)")
        print(" - GOOGLE_API_KEY or GEMINI_API_KEY (for Gemini)")
        print(" - OPENAI_API_KEY (for OpenAI)")
        print(" - ANTHROPIC_API_KEY (for Anthropic)")
        return
   
    # Define the email drafting agent
    email_drafter = Agent(
        role="Professional Email Writer",
        goal=f"Create a professional, concise, and well-structured email to {to} with subject '{subject}'",
        backstory="You are an experienced business communication specialist who excels at writing clear, professional emails that achieve their intended purpose while maintaining appropriate tone and etiquette.",
        llm=llm,
        verbose=False # Set to True for debugging
    )
   
    # Get initial email description from user
    description = input("Please provide a short description for the email content: ").strip()
   
    if not description:
        print("❌ Email description is required.")
        return
   
    iteration = 1
    while True:
        print(f"\n📝 Generating email draft (attempt {iteration})...")
       
        # Create email drafting task
        email_task = Task(
            description=f"""
            Write a professional email with the following requirements:
            - Recipient: {to}
            - Subject: {subject}
            - Content based on: {description}
           
            Guidelines:
            - Keep it concise and professional
            - Use appropriate greeting and closing
            - Ensure clear and polite tone
            - Include all necessary information
            - Make it actionable if needed
           
            Return only the email body text without subject line or recipient info.
            """,
            expected_output="A professional email body in plain text format",
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
       
        # Display the generated email
        print("\n" + "="*50)
        print("📧 GENERATED EMAIL PREVIEW")
        print("="*50)
        print(f"To: {to}")
        print(f"Subject: {subject}")
        print(f"From: {from_email}")
        print("-" * 50)
        print(body)
        print("="*50)
       
        # Get user confirmation
        while True:
            choice = input("\n\nChoose an action:\n1. Send email (yes)\n2. Provide feedback and regenerate (feedback)\n3. Cancel (no)\nYour choice: ").strip().lower()
           
            if choice in ['yes', '1', 'y']:
                # Send the email
                try:
                    msg = MIMEText(body, 'plain', 'utf-8')
                    msg['Subject'] = subject
                    msg['From'] = from_email
                    msg['To'] = to
                   
                    print("\n📤 Sending email...")
                    server = smtplib.SMTP(smtp_server, smtp_port)
                    server.starttls()
                    server.login(from_email, password)
                    server.sendmail(from_email, [to], msg.as_string())
                    server.quit()
                   
                    print("✅ Email sent successfully!")
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

def send_sms(to):
    """
    Send SMS using LLM for content generation with CrewAI
   
    Required environment variables:
    - TWILIO_ACCOUNT_SID: Your Twilio Account SID
    - TWILIO_AUTH_TOKEN: Your Twilio Auth Token
    - TWILIO_PHONE_NUMBER: Your Twilio phone number (e.g., +1234567890)
   
    LLM API Keys (one required):
    - GROQ_API_KEY (for Groq)
    - GOOGLE_API_KEY or GEMINI_API_KEY (for Gemini)
    - OPENAI_API_KEY (for OpenAI)
    - ANTHROPIC_API_KEY (for Anthropic)
   
    Get Twilio credentials from: https://console.twilio.com/
    """
   
    # Twilio configuration - Check environment variables
    account_sid = os.getenv("TWILIO_ACCOUNT_SID")
    auth_token = os.getenv("TWILIO_AUTH_TOKEN")
    twilio_phone = os.getenv("TWILIO_PHONE_NUMBER")
   
    if not all([account_sid, auth_token, twilio_phone]):
        print("❌ Twilio credentials not found. Please set the following environment variables:")
        print(" - TWILIO_ACCOUNT_SID")
        print(" - TWILIO_AUTH_TOKEN")
        print(" - TWILIO_PHONE_NUMBER")
        print("\n📱 Get your credentials from: https://console.twilio.com/")
        return
   
    # Validate phone number format
    if not to.startswith('+'):
        print("❌ Phone number must include country code (e.g., +1234567890)")
        return
   
    # Initialize Twilio client
    try:
        twilio_client = Client(account_sid, auth_token)
        print(f"✅ Twilio client initialized successfully")
    except Exception as e:
        print(f"❌ Failed to initialize Twilio client: {e}")
        return
   
    # Auto-detect available LLM based on API keys - Use operations_llm (local Ollama)
    llm = None
    model_name = None
   
    # Use local Ollama for operations
    try:
        model_name = "ollama/llama3.1:8b-instruct-q5_0"
        llm = LLM(
            model=model_name,
            base_url="http://localhost:11434",
            api_key="ollama"
        )
        print(f"✅ Using local Ollama LLM for operations: {model_name}")
    except Exception as e:
        print(f"❌ Failed to initialize Ollama LLM: {e}")
        # Fallback to other APIs if needed...
   
    if not llm:
        print("❌ No valid API key found. Please set one of the following environment variables:")
        print(" - GROQ_API_KEY (for Groq)")
        print(" - GOOGLE_API_KEY or GEMINI_API_KEY (for Gemini)")
        print(" - OPENAI_API_KEY (for OpenAI)")
        print(" - ANTHROPIC_API_KEY (for Anthropic)")
        return
   
    # Define the SMS drafting agent
    sms_drafter = Agent(
        role="Professional SMS Writer",
        goal=f"Create a concise, clear, and effective SMS message to {to}",
        backstory="You are an expert in mobile communication who specializes in writing clear, concise SMS messages that convey information effectively within character limits while maintaining appropriate tone.",
        llm=llm,
        verbose=False
    )
   
    # Get initial SMS description from user
    description = input("Please provide a short description for the SMS content: ").strip()
   
    if not description:
        print("❌ SMS description is required.")
        return
   
    iteration = 1
    while True:
        print(f"\n📱 Generating SMS draft (attempt {iteration})...")
       
        # Create SMS drafting task
        sms_task = Task(
            description=f"""
            Write a professional SMS message with the following requirements:
            - Recipient: {to}
            - Content based on: {description}
           
            Guidelines:
            - Keep it VERY concise (under 160 characters if possible, max 320 characters)
            - Use clear and direct language
            - Maintain professional but friendly tone
            - Include essential information only
            - Make it actionable if needed
            - No excessive punctuation or emojis
            - Use appropriate greeting only if necessary (to save characters)
           
            Return only the SMS message text, nothing else.
            """,
            expected_output="A concise SMS message in plain text format",
            agent=sms_drafter
        )
       
        # Create and execute crew
        sms_crew = Crew(
            agents=[sms_drafter],
            tasks=[sms_task],
            process=Process.sequential,
            verbose=False
        )
       
        try:
            result = sms_crew.kickoff()
            # Handle different result types from CrewAI
            if hasattr(result, 'raw'):
                message = result.raw.strip()
            elif hasattr(result, 'output'):
                message = result.output.strip()
            else:
                message = str(result).strip()
               
        except Exception as e:
            print(f"❌ Error generating SMS: {e}")
            retry = input("Would you like to try again? (yes/no): ").strip().lower()
            if retry != 'yes':
                return
            iteration += 1
            continue
       
        # Display the generated SMS
        char_count = len(message)
        char_status = "✅" if char_count <= 160 else "⚠️" if char_count <= 320 else "❌"
       
        print("\n" + "="*50)
        print("📱 GENERATED SMS PREVIEW")
        print("="*50)
        print(f"To: {to}")
        print(f"From: {twilio_phone}")
        print(f"Length: {char_count} characters {char_status}")
        print("-" * 50)
        print(message)
        print("="*50)
       
        if char_count > 320:
            print("⚠️ Warning: Message exceeds 320 characters. Consider shortening it.")
        elif char_count > 160:
            print("ℹ️ Note: Message will be sent as multiple SMS parts.")
       
        # Get user confirmation
        while True:
            choice = input("\nChoose an action:\n1. Send SMS (yes)\n2. Provide feedback and regenerate (feedback)\n3. Cancel (no)\nYour choice: ").strip().lower()
           
            if choice in ['yes', '1', 'y']:
                # Send the SMS
                try:
                    print("\n📤 Sending SMS...")
                    message_obj = twilio_client.messages.create(
                        body=message,
                        from_=twilio_phone,
                        to=to
                    )
                   
                    print("✅ SMS sent successfully!")
                    print(f"📱 Sent to: {to}")
                    print(f"📨 Message SID: {message_obj.sid}")
                    print(f"📏 Length: {char_count} characters")
                    return
                   
                except Exception as e:
                    print(f"❌ Error sending SMS: {e}")
                    print("Please check your Twilio credentials and phone number format.")
                    return
                   
            elif choice in ['feedback', '2', 'f']:
                feedback = input("\nPlease provide specific feedback or mention missing points: ").strip()
                if feedback:
                    description += f"\n\nUser feedback for improvement: {feedback}"
                    iteration += 1
                    break
                else:
                    print("Please provide some feedback to improve the SMS.")
                   
            elif choice in ['no', '3', 'n', 'cancel']:
                print("📪 SMS cancelled.")
                return
               
            else:
                print("Invalid choice. Please enter 'yes', 'feedback', or 'no'.")

# Alternative function using free SMS services (for testing)
def send_sms_free(to):
    """
    Alternative SMS sender using free services (for testing purposes)
    Uses email-to-SMS gateway (limited carriers)
    """
   
    print("📱 Free SMS Service (Email-to-SMS Gateway)")
    print("Note: This works only for supported carriers in the US")
   
    # Common carrier email-to-SMS gateways
    carriers = {
        "verizon": "vtext.com",
        "att": "txt.att.net",
        "tmobile": "tmomail.net",
        "sprint": "messaging.sprintpcs.com",
        "boost": "smsmyboostmobile.com",
        "cricket": "sms.cricketwireless.net",
        "uscellular": "email.uscc.net"
    }
   
    print("\nSupported carriers:")
    for carrier, gateway in carriers.items():
        print(f" - {carrier.title()}: {gateway}")
   
    carrier = input("\nEnter your carrier (verizon/att/tmobile/sprint/boost/cricket/uscellular): ").strip().lower()
   
    if carrier not in carriers:
        print("❌ Unsupported carrier")
        return
   
    # Remove country code and formatting from phone number
    phone_clean = to.replace("+1", "").replace("-", "").replace("(", "").replace(")", "").replace(" ", "")
    sms_email = f"{phone_clean}@{carriers[carrier]}"
   
    print(f"📧 Converting SMS to email: {sms_email}")
   
    # Use the existing email function but with SMS-specific settings
    print("📱 Generating SMS content...")
   
    # This would integrate with your existing email function
    # For now, just show what would happen
    print(f"✅ Would send SMS via email gateway to: {sms_email}")
    print("Note: Implement email sending logic similar to send_email() function")

# This defines what the script is allowed to do. '.readonly' means it CANNOT change your contacts.
SCOPES = ["https://www.googleapis.com/auth/contacts.readonly"]
#------------------------------------------------------------------------------------------------------------------------------------------------
#------------------------------------------------------------------------------------------------------------------------------------------------
import os
import json
import subprocess
import platform
import webbrowser
from pathlib import Path
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
SCOPES = ["https://www.googleapis.com/auth/contacts.readonly"]

def make_call(to):
    """
    Make a phone call from your device using native system integration.
   
    Args:
        to (str): Either a contact name or phone number
                 Examples: "John Doe", "Mom", "+1234567890"
   
    Returns:
        bool: True if call was initiated successfully, False otherwise
    """
   
    # Determine if input is phone number or name
    clean_input = to.replace('+', '').replace('-', '').replace('(', '').replace(')', '').replace(' ', '')
    if clean_input.isdigit() and len(clean_input) >= 10:
        phone_number = to
        contact_name = "Unknown Contact"
        print(f"Direct number provided: {phone_number}")
    else:
        print(f"Searching for contact: {to}")
        phone_number, contact_name = search_contacts(to)
       
        if not phone_number:
            print(f"Contact '{to}' not found in any available contact sources.")
            return False
   
    print(f"Preparing to call: {contact_name} ({phone_number})")
   
    # Confirm before calling
    confirm = input("Press Enter to make the call, or type 'no' to cancel: ").strip().lower()
    if confirm == 'no':
        print("Call cancelled.")
        return False
   
    # Initiate the call based on platform
    return initiate_call(phone_number, contact_name)

def search_contacts(name):
    """Search for contact by name using Google Contacts first, then local fallback."""
    phone, contact_name = search_google_contacts(name)
    if phone:
        return phone, contact_name
   
    phone, contact_name = search_local_contacts(name)
    return phone, contact_name

def search_google_contacts(name):
    """Search Google Contacts for the given name."""
    try:
        contacts = get_google_contacts()
        if not contacts:
            return None, None
       
        for contact in contacts:
            if name.lower() in contact['name'].lower():
                return contact['phone'], contact['name']
       
        return None, None
       
    except Exception as e:
        print(f"Error searching Google Contacts: {e}")
        return None, None

def get_google_contacts():
    """Fetch contacts from Google Contacts API with authentication handling."""
    try:
        creds = None
       
        if os.path.exists("token.json"):
            creds = Credentials.from_authorized_user_file("token.json", SCOPES)
       
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                except Exception:
                    creds = None
           
            if not creds:
                if not os.path.exists("client_secret.json"):
                    return None
               
                flow = InstalledAppFlow.from_client_secrets_file("client_secret.json", SCOPES)
                creds = flow.run_local_server(port=0)
           
            with open("token.json", "w") as token:
                token.write(creds.to_json())
       
        service = build("people", "v1", credentials=creds)
       
        results = service.people().connections().list(
            resourceName="people/me",
            pageSize=1000,
            personFields="names,phoneNumbers"
        ).execute()
       
        connections = results.get("connections", [])
        contacts_list = []
       
        for person in connections:
            names = person.get("names", [])
            phone_numbers = person.get("phoneNumbers", [])
           
            if names and phone_numbers:
                name = names[0].get("displayName")
                phone = phone_numbers[0].get("value")
               
                if name and phone:
                    contacts_list.append({"name": name, "phone": phone})
       
        print(f"Loaded {len(contacts_list)} contacts from Google")
        return contacts_list
       
    except Exception:
        return None

def search_local_contacts(name):
    """Search local contacts.json file as fallback."""
    try:
        contacts_file = Path.home() / "contacts.json"
       
        if not contacts_file.exists():
            sample_contacts = [
                {"name": "John Doe", "phone": "+1234567890"},
                {"name": "Jane Smith", "phone": "+0987654321"}
            ]
           
            with open(contacts_file, 'w') as f:
                json.dump(sample_contacts, f, indent=2)
           
            print(f"Created sample contacts file: {contacts_file}")
       
        with open(contacts_file, 'r') as f:
            contacts = json.load(f)
       
        for contact in contacts:
            if name.lower() in contact.get('name', '').lower():
                return contact.get('phone'), contact.get('name')
       
        return None, None
       
    except Exception:
        return None, None

def initiate_call(phone_number, contact_name):
    """Initiate call using the best method for each platform."""
    try:
        system = platform.system().lower()
        print(f"Initiating call to {contact_name} ({phone_number})...")
       
        if system == "windows":
            # Method 1: Try browser-based tel: protocol (works with most setups)
            try:
                webbrowser.open(f'tel:{phone_number}')
                print("✓ Call request sent via browser. Check your default calling app.")
                return True
            except Exception:
                pass
           
            # Method 2: Try Skype (most reliable Windows option)
            try:
                subprocess.run(['start', f'skype:{phone_number}?call'], shell=True, check=True, timeout=5)
                print("✓ Call initiated through Skype.")
                return True
            except subprocess.CalledProcessError:
                pass
           
            # Method 3: Try Windows native tel: protocol
            try:
                subprocess.run(['start', '', f'tel:{phone_number}'], shell=True, check=True, timeout=5)
                print("✓ Call request sent to Windows default phone app.")
                return True
            except subprocess.CalledProcessError:
                pass
           
            # Method 4: Try callto: protocol
            try:
                subprocess.run(['start', f'callto:{phone_number}'], shell=True, check=True, timeout=5)
                print("✓ Call initiated with callto protocol.")
                return True
            except subprocess.CalledProcessError:
                pass
               
            print("❌ No Windows calling app found. Please install:")
            print(" • Your Phone app from Microsoft Store")
            print(" • Skype")
            print(" • Or any other calling application")
                   
        elif system == "darwin": # macOS
            try:
                subprocess.run(['open', f'tel:{phone_number}'], check=True, timeout=5)
                print("✓ Call initiated through macOS. Check your iPhone or Mac.")
                return True
            except subprocess.CalledProcessError:
                try:
                    subprocess.run(['open', f'facetime-audio://{phone_number}'], check=True, timeout=5)
                    print("✓ FaceTime Audio call initiated.")
                    return True
                except subprocess.CalledProcessError:
                    print("❌ macOS calling methods failed.")
                   
        elif system == "linux":
            try:
                subprocess.run(['xdg-open', f'tel:{phone_number}'], check=True, timeout=5)
                print("✓ Call initiated through system handler.")
                return True
            except subprocess.CalledProcessError:
                try:
                    subprocess.run(['kdeconnect-cli', '--name', 'phone', '--call', phone_number],
                                 check=True, timeout=5)
                    print("✓ Call initiated through KDE Connect.")
                    return True
                except (subprocess.CalledProcessError, FileNotFoundError):
                    print("❌ Linux calling methods failed. Install KDE Connect or similar.")
       
        # Manual fallback
        print(f"\n📞 Manual dial required: {phone_number}")
        print(f"👤 Contact: {contact_name}")
       
        # Copy to clipboard
        try:
            if system == "darwin":
                subprocess.run(['pbcopy'], input=phone_number.encode(), timeout=2)
                print("📋 Number copied to clipboard (⌘+V to paste)")
            elif system == "linux":
                subprocess.run(['xclip', '-selection', 'clipboard'], input=phone_number.encode(), timeout=2)
                print("📋 Number copied to clipboard (Ctrl+V to paste)")
            elif system == "windows":
                subprocess.run(['clip'], input=phone_number.encode(), shell=True, timeout=2)
                print("📋 Number copied to clipboard (Ctrl+V to paste)")
        except:
            pass
       
        return False
       
    except Exception as e:
        print(f"❌ Call failed: {e}")
        print(f"📞 Please manually dial: {phone_number}")
        return False

# Example usage
if __name__ == "__main__":
    print("📞 Universal Phone Call Function")
    print("Usage: make_call('Contact Name') or make_call('+1234567890')")
   
    test_contact = input("\nEnter contact name or phone number: ").strip()
    if test_contact:
        success = make_call(test_contact)
       
        if not success:
            print("\n💡 To enable automatic calling on Windows:")
            print(" 1. Install 'Your Phone' app from Microsoft Store")
            print(" 2. Connect your Android phone")
            print(" 3. Or install Skype for calling")