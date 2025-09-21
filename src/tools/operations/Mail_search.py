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
import re
import numpy as np
from collections import Counter, defaultdict
from common_functions.Find_project_root import find_project_root

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def get_gmail_service(project_root: Optional[str] = None):
    """Authenticate with Gmail API and return a service object."""
    if project_root is None:
        project_root = find_project_root()
        logger.info(f"Project root: {project_root}")

    token_file = os.path.join(project_root, "token.json")
    client_secret_file = os.path.join(project_root, "client_secret.json")
    SCOPES = ["https://mail.google.com/"]
    creds = None
    if os.path.exists(token_file):
        logger.info(f"Loading token from {token_file}")
        creds = Credentials.from_authorized_user_file(token_file, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            logger.info("Refreshing expired token")
            creds.refresh(Request())
        else:
            if not os.path.exists(client_secret_file):
                logger.error(f"❌ client_secret.json missing at {client_secret_file}")
                return None
            logger.info(f"Running OAuth flow with {client_secret_file}")
            flow = InstalledAppFlow.from_client_secrets_file(client_secret_file, SCOPES)
            creds = flow.run_local_server(port=0)

        with open(token_file, "w") as token:
            token.write(creds.to_json())
            logger.info(f"✅ Token saved to {token_file}")

    try:
        service = build("gmail", "v1", credentials=creds)
        logger.info("✅ Gmail service initialized")
        return service
    except HttpError as error:
        logger.error(f"❌ Gmail API error: {error}")
        return None


def search_emails(service, query: str, limit: int = 10) -> List[Dict]:
    """Search emails by query and return email data."""
    try:
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
                msg = service.users().messages().get(
                    userId='me',
                    id=message['id'],
                    format='full'
                ).execute()
                
                headers = msg['payload'].get('headers', [])
                subject = next((h['value'] for h in headers if h['name'] == 'Subject'), 'No Subject')
                sender = next((h['value'] for h in headers if h['name'] == 'From'), 'Unknown Sender')
                date = next((h['value'] for h in headers if h['name'] == 'Date'), 'Unknown Date')
                
                body = extract_email_body(msg['payload'])
                
                email_data.append({
                    'id': message['id'],
                    'subject': subject,
                    'sender': sender,
                    'date': date,
                    'body': body
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
                if not body:
                    data = part['body']['data']
                    body = base64.urlsafe_b64decode(data).decode('utf-8')
    else:
        if payload['mimeType'] == 'text/plain':
            data = payload['body']['data']
            body = base64.urlsafe_b64decode(data).decode('utf-8')
        elif payload['mimeType'] == 'text/html':
            data = payload['body']['data']
            body = base64.urlsafe_b64decode(data).decode('utf-8')
    
    return body.strip()


def extract_relevant_chunks(emails: List[Dict], query: str) -> List[Dict]:
    """Extract up to 10 relevant info chunks from emails using TF-IDF cosine similarity, grouped by email."""
    # Collect all sentences with email index
    all_sentences = []
    for e_idx, email in enumerate(emails):
        body = email['body'].lower()
        sentences = re.split(r'(?<!\w\.\w.)(?<![A-Z][a-z]\.)(?<=\.|\?|\!)\s', body)
        for sent in sentences:
            sent = sent.strip()
            if sent:
                all_sentences.append((e_idx, sent))
    
    if not all_sentences:
        return []
    
    # Preprocess query
    query_lower = query.lower()
    
    # Build corpus: sentences + query
    corpus = [sent for _, sent in all_sentences] + [query_lower]
    
    # Build vocabulary
    vocab = set()
    for doc in corpus:
        words = re.findall(r'\w+', doc)
        vocab.update(words)
    vocab = list(vocab)
    vocab_size = len(vocab)
    word_to_id = {w: i for i, w in enumerate(vocab)}
    
    # Compute TF
    tf = np.zeros((len(corpus), vocab_size))
    for d, doc in enumerate(corpus):
        words = re.findall(r'\w+', doc)
        counter = Counter(words)
        total_words = len(words)
        for w, count in counter.items():
            if w in word_to_id:
                tf[d, word_to_id[w]] = count / total_words if total_words > 0 else 0
    
    # Compute IDF
    df = np.sum(tf > 0, axis=0)
    idf = np.log(len(corpus) / (df + 1e-10))  # Avoid div0
    
    # TF-IDF
    tfidf = tf * idf
    
    # Query vector
    query_vec = tfidf[-1]
    
    # Sentence vectors
    sent_tfidf = tfidf[:-1]
    
    # Compute cosines
    similarities = []
    for i in range(len(all_sentences)):
        sent_vec = sent_tfidf[i]
        norm_sent = np.linalg.norm(sent_vec)
        norm_query = np.linalg.norm(query_vec)
        if norm_sent == 0 or norm_query == 0:
            sim = 0
        else:
            sim = np.dot(sent_vec, query_vec) / (norm_sent * norm_query)
        e_idx, sent = all_sentences[i]
        similarities.append((sim, e_idx, sent))
    
    # Sort descending by similarity
    similarities.sort(key=lambda x: x[0], reverse=True)
    
    # Group by email, collect top chunks per email
    grouped = defaultdict(list)
    chunk_count = 0
    for sim, e_idx, chunk in similarities:
        if sim > 0.05 and chunk_count < 10:
            # Clean the chunk: remove HTML tags, multiple newlines, extra spaces
            clean_chunk = re.sub(r'<.*?>', '', chunk)  # Remove HTML tags
            clean_chunk = re.sub(r'[\n\r\t]+', ' ', clean_chunk).strip()
            clean_chunk = re.sub(r'\s+', ' ', clean_chunk)
            # Unescape unicode if possible
            try:
                clean_chunk = clean_chunk.encode('utf-8').decode('unicode_escape')
            except:
                pass  # If fails, keep as is
            grouped[e_idx].append((sim, clean_chunk))
            chunk_count += 1
    
    if not grouped:
        return []
    
    # For each group, sort chunks by sim desc
    for e_idx in grouped:
        grouped[e_idx].sort(key=lambda x: x[0], reverse=True)
        grouped[e_idx] = [chunk for _, chunk in grouped[e_idx]]
    
    # Get email order by highest sim in each group
    email_order = sorted(grouped.keys(), key=lambda e: max([s[0] for s in similarities if s[1] == e]), reverse=True)
    
    # Construct final output: list of dicts with email metadata and chunks
    final_chunks = []
    for e_idx in email_order:
        email = emails[e_idx]
        final_chunks.append({
            'id': email['id'],
            'subject': email['subject'],
            'sender': email['sender'],
            'date': email['date'],
            'relevant_chunks': grouped[e_idx]
        })
    
    return final_chunks


def searchMail(semantic_query: str, limit=None) -> Tuple[bool, str]:
    """
    Searches emails semantically by fetching recent emails (no keyword filter in q),
    then extracts up to 10 semantically relevant info chunks using TF-IDF on their content.
    
    Args:
        semantic_query (str): The query to search for semantically
        limit (int, optional): Maximum number of emails to retrieve (default: 30 for recent mails)
    
    Returns:
        Tuple[bool, str]: (Success status, JSON list of relevant chunks)
    """
    try:
        if limit is None:
            limit = 20  # Default to recent 30 mails
        
        # Validate inputs
        if not semantic_query or not semantic_query.strip():
            return False, "❌ Query cannot be empty"
        
        if not isinstance(limit, int) or limit <= 0:
            limit = 30
        
        # Limit maximum results
        if limit > 50:
            limit = 50
        
        logger.info(f"🔍 Searching emails semantically for: '{semantic_query}', limit: {limit}")
        
        # Get Gmail service
        service = get_gmail_service()
        if not service:
            logger.error("❌ No Gmail service available")
            return False, "❌ Failed to authenticate with Gmail API"
        
        logger.info("✅ Gmail service obtained")
        
        # Fetch recent emails without specific query filter (gets latest first)
        search_query = ''  # Empty query to get all recent
        logger.info(f"📫 Using Gmail search query: '{search_query}' (fetching recent {limit} emails)")
        
        # Search emails
        emails = search_emails(service, search_query, limit)
        
        if not emails:
            return True, f"No recent emails found."
        
        logger.info(f"📧 Found {len(emails)} recent emails")
        
        # Extract relevant chunks semantically from the recent emails
        chunks = extract_relevant_chunks(emails, semantic_query)
        
        if not chunks:
            return True, f"No relevant chunks found in recent emails for '{semantic_query}'."
        
        # Return as JSON list for next function in chain
        response = json.dumps(chunks, indent=2)
        
        return True, response
        
    except Exception as e:
        logger.error(f"❌ Error in searchMail: {e}")
        return False, f"❌ Error searching emails: {str(e)}"


if __name__ == "__main__":
    success, result = searchMail("internships", 20)
    print(f"Success: {success}")
    print(f"Result: {result}")