import os
from typing import Tuple, Type, Optional
from pydantic import BaseModel, Field, PrivateAttr
from crewai.tools import BaseTool
from groq import Groq
from dotenv import load_dotenv
import PyPDF2
from docx import Document
from common_functions.Find_project_root import find_project_root
from utils.logger import setup_logger

# Load environment variables
load_dotenv()
PROJECT_ROOT = find_project_root()
logger = setup_logger()

class DocumentProcessorInput(BaseModel):
    """Input schema for DocumentProcessorTool."""
    file_path: str = Field(..., description="Path to the PDF, Word, or text file")
    query: str = Field(..., description="User query specifying summarization or translation")
    target_lang: str = Field(default=None, description="Target language for translation (optional)")
    max_length: int = Field(default=100, description="Maximum length for summarization (optional)")

class DocumentProcessorTool(BaseTool):
    """Tool for summarizing or translating content from PDF, Word, or text files."""
    name: str = "DocumentProcessor"
    description: str = (
        "Extracts text from PDF, Word, or text files and processes it (summarizes or translates) "
        "based on the user query. Supports summarization (with optional max_length) and translation "
        "(requires target_lang). Uses Groq API for text processing."
    )
    args_schema: Type[BaseModel] = DocumentProcessorInput
    
    # Define private attributes for Pydantic
    _groq_client: Optional[Groq] = PrivateAttr(default=None)
    _api_available: bool = PrivateAttr(default=False)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
        # Try multiple API keys with better error handling
        groq_api_key = None
        api_key_vars = ["GROQ_API_KEY1"]
        
        for key_var in api_key_vars:
            groq_api_key = os.getenv(key_var)
            if groq_api_key and groq_api_key.strip():
                logger.info(f"Using {key_var} for Groq API")
                break
        
        if not groq_api_key:
            logger.warning("No valid GROQ API key found. Falling back to local processing (no AI enhancement).")
            return
        
        try:
            self._groq_client = Groq(api_key=groq_api_key)
            # Test the API key with a simple call (wrapped to avoid blocking)
            try:
                self._test_api_key()
                self._api_available = True
                logger.info("DocumentProcessorTool initialized with Groq API successfully.")
            except Exception as test_e:
                logger.warning(f"Groq API test failed (e.g., rate limit or invalid model): {str(test_e)}. Using basic mode.")
                self._api_available = False  # Don't raise; fallback
        except Exception as e:
            logger.error(f"Failed to initialize Groq client: {str(e)}. Using basic mode.")
            self._api_available = False

    def _test_api_key(self):
        """Test if the API key is valid with a minimal request."""
        if not self._groq_client:
            raise ValueError("Groq client not initialized.")
        response = self._groq_client.chat.completions.create(
            model="llama3-70b-8192",  # Valid Groq model (fixed)
            messages=[{"role": "user", "content": "Hello"}],
            max_tokens=10,
            temperature=0.1
        )
        logger.info("API key validation successful")

    def _extract_text(self, file_path: str) -> Tuple[bool, str]:
        """Extract text from PDF, Word, or text files."""
        if not os.path.exists(file_path):
            logger.error(f"File not found: {file_path}")
            return False, f"File not found: {file_path}"

        ext = os.path.splitext(file_path)[1].lower()
        try:
            if ext == '.pdf':
                with open(file_path, 'rb') as file:
                    reader = PyPDF2.PdfReader(file)
                    text = ""
                    for page in reader.pages:
                        try:
                            extracted = page.extract_text()
                            text += extracted or ""
                        except Exception as page_error:
                            logger.warning(f"Error extracting text from page: {page_error}")
                            continue
                logger.info(f"Successfully extracted text from PDF: {file_path}")
                return True, text.strip()

            elif ext in ['.docx', '.doc']:
                if ext == '.docx':
                    doc = Document(file_path)
                    text = "\n".join([para.text for para in doc.paragraphs if para.text.strip()])
                else:
                    logger.warning("DOC files not fully supported, only DOCX")
                    return False, "DOC files not supported, please use DOCX format"
                logger.info(f"Successfully extracted text from Word document: {file_path}")
                return True, text.strip()

            elif ext == '.txt':
                # Try different encodings
                encodings = ['utf-8', 'utf-16', 'latin-1', 'cp1252']
                text = None
                for encoding in encodings:
                    try:
                        with open(file_path, 'r', encoding=encoding) as file:
                            text = file.read()
                        break
                    except UnicodeDecodeError:
                        continue
                
                if text is None:
                    return False, f"Could not decode text file with any supported encoding"
                
                logger.info(f"Successfully extracted text from text file: {file_path}")
                return True, text.strip()

            else:
                logger.error(f"Unsupported file type: {ext}")
                return False, f"Unsupported file type: {ext}. Supported: .pdf, .docx, .txt"

        except Exception as e:
            logger.error(f"Error extracting text from {file_path}: {str(e)}")
            return False, f"Error extracting text from {file_path}: {str(e)}"

    def _process_with_groq(self, text: str, query: str, target_lang: str = None, max_length: int = 100) -> Tuple[bool, str]:
        """Process text using Groq API for summarization or translation (with fallback)."""
        query_lower = query.lower()
        is_summary = 'summar' in query_lower
        is_translation = 'translat' in query_lower

        # Validate input
        if not text.strip():
            return False, "No text content to process"

        # Truncate text if too long
        max_text_length = 8000
        if len(text) > max_text_length:
            text = text[:max_text_length] + "... [truncated]"
            logger.warning(f"Text truncated to {max_text_length} characters due to token limits")

        if not is_summary and not is_translation:
            logger.error("Query must specify 'summarize' or 'translate'")
            return False, "Query must specify 'summarize' or 'translate'"

        if is_translation and not target_lang:
            logger.error("Translation requires target_lang parameter")
            return False, "Translation requires target language to be specified"

        # Fallback if API not available
        if not self._api_available or not self._groq_client:
            logger.warning("Groq API unavailable; using basic fallback processing.")
            if is_summary:
                # Simple word-based summary
                words = text.split()
                summary = ' '.join(words[:max_length * 2]) + "..."
                return True, f"Fallback summary (~{max_length} words): {summary}"
            elif is_translation:
                return True, f"Fallback: Full translation to {target_lang} requires API. Preview (first 200 chars unchanged): {text[:200]}..."

        prompt = ""
        if is_summary:
            prompt = (
                f"Please provide a concise summary of the following text in approximately {max_length} words. "
                f"Focus on the main points, key findings, and important conclusions:\n\n{text}"
            )
        elif is_translation:
            prompt = (
                f"Please translate the following text accurately into {target_lang}. "
                f"Maintain the original meaning and tone:\n\n{text}"
            )

        try:
            response = self._groq_client.chat.completions.create(
                model="llama3-70b-8192",  # Valid model
                messages=[{"role": "user", "content": "prompt"}],
                max_tokens=max_length * 3 if is_summary else 2000,
                temperature=0.3
            )
            
            result = response.choices[0].message.content.strip()
            if not result:
                return False, "Empty response from Groq API"
            
            logger.info(f"Groq API processed {'summary' if is_summary else 'translation'} successfully.")
            return True, result

        except Exception as e:
            logger.error(f"Groq API error: {str(e)}")
            # Fallback
            if is_summary:
                words = text.split()
                summary = ' '.join(words[:max_length * 2]) + "..."
                return True, f"API error fallback summary: {summary}"
            else:
                return True, f"API error fallback: Original text (untranslated): {text[:200]}..."

    def _run(self, file_path: str, query: str, target_lang: str = None, max_length: int = 100) -> str:
        """Run document processing: extract text and summarize or translate based on query."""
        logger.info(f"Processing document: {file_path} with query: {query}")
        
        # Validate inputs
        if not file_path or not query:
            return "Error: Both file_path and query are required"
        
        # Extract text
        success, text_or_error = self._extract_text(file_path)
        if not success:
            return f"Error: {text_or_error}"

        if not text_or_error.strip():
            return "Error: No text content found in the document"

        # Process with Groq (or fallback)
        success, result = self._process_with_groq(text_or_error, query, target_lang, max_length)
        if not success:
            return f"Error: {result}"

        action = "summarized" if 'summar' in query.lower() else "translated"
        logger.info(f"Successfully {action} document: {file_path}")
        return f"Successfully {action} content from {os.path.basename(file_path)}:\n\n{result}"


def document_summarize(file_path: str, query: str, max_length: int = 100) -> Tuple[bool, str]:
    """Operation to summarize document content."""
    logger.info(f"Running document_summarize for file: {file_path}")
    try:
        tool = DocumentProcessorTool()
        result = tool._run(file_path=file_path, query=query, max_length=max_length)
        success = not result.startswith("Error:")
        return success, result
    except Exception as e:
        logger.error(f"Error in document_summarize: {str(e)}")
        return False, f"Error in document_summarize: {str(e)}"


def document_translate(file_path: str, query: str, target_lang: str) -> Tuple[bool, str]:
    """Operation to translate document content."""
    logger.info(f"Running document_translate for file: {file_path} to {target_lang}")
    try:
        tool = DocumentProcessorTool()
        result = tool._run(file_path=file_path, query=query, target_lang=target_lang)
        success = not result.startswith("Error:")
        return success, result
    except Exception as e:
        logger.error(f"Error in document_translate: {str(e)}")
        return False, f"Error in document_translate: {str(e)}"


# if __name__ == "__main__":
#     # Test the function - use raw string for Windows paths to avoid escape issues
#     test_file_path = r"C:\Users\Parth Dhengle\Downloads\ML_text.txt"
#     success, result = document_translate(test_file_path, "translate the document to French", "French")
#     print(f"Success: {success}")
#     print(result)