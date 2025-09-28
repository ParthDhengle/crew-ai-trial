import os
import sys
import tempfile
from datetime import datetime
import warnings
import json
import re
from dotenv import load_dotenv
import platform
import subprocess

# Suppress syntax warnings
warnings.filterwarnings("ignore", category=SyntaxWarning)

# Absolute imports to avoid relative import issues
try:
    from utils.logger import setup_logger
    from common_functions.Find_project_root import find_project_root
except ImportError:
    def setup_logger():
        import logging
        logger = logging.getLogger("AIAssistant")
        logger.setLevel(logging.DEBUG)
        if not logger.handlers:
            console_handler = logging.StreamHandler()
            console_handler.setLevel(logging.INFO)
            formatter = logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S"
            )
            console_handler.setFormatter(formatter)
            logger.addHandler(console_handler)
        return logger
    
    def find_project_root():
        import os
        current_dir = os.path.abspath(os.path.dirname(__file__))
        root_dir = current_dir
        while root_dir != os.path.dirname(root_dir):
            if os.path.exists(os.path.join(root_dir, '.env')):  # Use '.git', 'requirements.txt', or another root marker if preferred
                return root_dir
            root_dir = os.path.dirname(root_dir)
        return current_dir  # Fallback to script's directory if no marker found

logger = setup_logger()
PROJECT_ROOT = find_project_root()

# Load .env file dynamically from project root
env_path = os.path.join(PROJECT_ROOT, '.env')
if not os.path.exists(env_path):
    logger.error(f".env file not found at {env_path}")
    sys.exit(1)
load_dotenv(env_path)
logger.info(f"Loaded .env file from {env_path}")

def check_vscode_installation():
    """Check if Visual Studio Code is installed on the system."""
    try:
        if platform.system() == "Windows":
            # Common VS Code installation paths
            possible_paths = [
                r"C:\Program Files\Microsoft VS Code\Code.exe",
                r"C:\Program Files (x86)\Microsoft VS Code\Code.exe",
            ]
            
            for path in possible_paths:
                if os.path.exists(path):
                    logger.info(f"Visual Studio Code found at: {path}")
                    return True, path
            
            logger.warning("Visual Studio Code not found in common installation paths")
            return False, None
        else:
            logger.warning("Visual Studio Code auto-open is only supported on Windows")
            return False, None
    except Exception as e:
        logger.error(f"Error checking VS Code installation: {str(e)}")
        return False, None

def call_grok(prompt: str, api_key: str) -> str:
    """Call Grok API directly."""
    try:
        from groq import Groq
        client = Groq(api_key=api_key)
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=1500,
            temperature=0.3
        )
        return response.choices[0].message.content
    except Exception as e:
        logger.warning(f"Grok API failed: {str(e)}")
        return None

def call_gemini(prompt: str, api_key: str) -> str:
    """Call Gemini API as fallback."""
    try:
        import google.generativeai as genai
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel("gemini-1.5-flash-latest")
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        logger.warning(f"Gemini API failed: {str(e)}")
        return None

def clean_llm_response(response: str) -> str:
    """Clean LLM response to extract JSON."""
    if not response:
        return None
    
    logger.debug(f"Raw LLM response: {response[:500]}...")
    
    # Remove markdown code blocks
    response = re.sub(r'^```json\s*|\s*```$', '', response.strip(), flags=re.MULTILINE)
    response = re.sub(r'^```\s*|\s*```$', '', response.strip(), flags=re.MULTILINE)
    response = response.strip()
    
    # Try to find JSON within the response
    json_match = re.search(r'\{.*\}', response, re.DOTALL)
    if json_match:
        json_str = json_match.group(0)
        logger.debug(f"Extracted JSON: {json_str[:200]}...")
        return json_str
    
    logger.warning(f"No JSON found in response: {response[:200]}...")
    return None

def create_fallback_code_content(query: str) -> dict:
    """Create fallback code content when LLM fails."""
    logger.info("Creating fallback code content")
    
    return {
        "project_name": f"Project for: {query}",
        "files": [
            {
                "file_name": "main.py",
                "content": "# This is a basic code file generated as fallback.\n# Please provide a more detailed query for better results.\nprint('Hello World')"
            }
        ]
    }

def create_code_project(project_dir: str, content: dict):
    """Create the code project directory and write files."""
    try:
        # Create project directory if it doesn't exist
        os.makedirs(project_dir, exist_ok=True)
        
        # Write each file
        for file_info in content.get("files", []):
            file_name = file_info.get("file_name")
            file_content = file_info.get("content", "")
            
            if file_name:
                file_path = os.path.join(project_dir, file_name)
                os.makedirs(os.path.dirname(file_path), exist_ok=True)
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(file_content)
                logger.info(f"Created file: {file_path}")
        
        return True
    except Exception as e:
        logger.error(f"Error creating code project: {str(e)}")
        return False

def select_or_create_directory():
    """Prompt user to select or create a directory."""
    while True:
        print("\nOptions:")
        print("1. Create new directory")
        print("2. Select existing directory")
        choice = input("Enter choice (1/2): ").strip()
        
        if choice == '1':
            dir_name = input("Enter new directory name: ").strip()
            base_path = input("Enter base path (default: current dir): ").strip() or os.getcwd()
            project_dir = os.path.join(base_path, dir_name)
            if os.path.exists(project_dir):
                print(f"Directory '{project_dir}' already exists. Try again.")
                continue
            return project_dir
            
        elif choice == '2':
            project_dir = input("Enter existing directory path: ").strip()
            if os.path.exists(project_dir) and os.path.isdir(project_dir):
                return project_dir
            else:
                print(f"Directory '{project_dir}' does not exist or is not a directory. Try again.")
                continue
            
        else:
            print("Invalid choice. Try again.")

def code_generate_from_query(query: str) -> tuple[bool, str]:
    """
    Generates a code project based on a user query using AI-driven content generation.
    Asks user for directory selection/creation, writes code files, and opens in VS Code.
    Does not run the code.
    
    Args:
        query (str): User query describing desired code (e.g., "Create a Node.js application for a todo list").
    
    Returns:
        tuple[bool, str]: (success, result message or error)
    """
    try:
        # Check VS Code installation
        vscode_installed, vscode_path = check_vscode_installation()
        if not vscode_installed:
            logger.warning("Visual Studio Code not found. Project will be created but may not open automatically.")
        
        # Verify API keys
        grok_api_key = os.getenv("GROQ_API_KEY3")
        gemini_api_key = os.getenv("GEMINI_API_KEY3")
        if not grok_api_key and not gemini_api_key:
            logger.error(f"No API keys found for GROQ_API_KEY3 or GEMINI_API_KEY3 in {env_path}")
            return False, f"Error: No API keys found for GROQ_API_KEY3 or GEMINI_API_KEY3 in {env_path}"

        logger.info(f"Generating code project for query: {query}")
        
        # Construct improved prompt for LLM
        prompt = f"""
You are a code generation expert. Generate code files for a project based on this request.

User Query: "{query}"

Return ONLY a valid JSON object with this exact structure:
{{
  "project_name": "Project Name",
  "files": [
    {{
      "file_name": "path/to/file.ext",
      "content": "Full file content as string..."
    }}
  ]
}}

Generate complete, working code files appropriate for the query.
For Node.js apps, include package.json with dependencies.
Use relative paths in file_name.
Return only the JSON, no explanation.
"""
        
        # Call LLM with retry logic
        response = None
        content = None
        
        for attempt in range(3):
            logger.info(f"Attempting LLM call #{attempt + 1}")
            
            if grok_api_key and not response:
                response = call_grok(prompt, grok_api_key)
                if response:
                    cleaned = clean_llm_response(response)
                    if cleaned:
                        try:
                            content = json.loads(cleaned)
                            logger.info("Successfully parsed Grok response")
                            break
                        except json.JSONDecodeError as e:
                            logger.warning(f"Grok JSON decode error: {str(e)}")
                            response = None
            
            if gemini_api_key and not content:
                response = call_gemini(prompt, gemini_api_key)
                if response:
                    cleaned = clean_llm_response(response)
                    if cleaned:
                        try:
                            content = json.loads(cleaned)
                            logger.info("Successfully parsed Gemini response")
                            break
                        except json.JSONDecodeError as e:
                            logger.warning(f"Gemini JSON decode error: {str(e)}")
                            response = None
        
        # Use fallback if LLM failed
        if not content:
            logger.warning("LLM parsing failed after all retries. Using fallback content.")
            content = create_fallback_code_content(query)
        
        logger.info(f"Code content: {content}")
        
        # Ask user for directory
        project_dir = select_or_create_directory()
        
        # Create the project
        if not create_code_project(project_dir, content):
            return False, "Failed to create code project files."
        
        success_message = f"Code project created at: {project_dir}"
        
        if vscode_installed:
            try:
                # Open VS Code in the project directory
                subprocess.run([vscode_path, project_dir], check=True)
                success_message += "\nProject opened in Visual Studio Code."
            except Exception as e:
                logger.warning(f"Failed to open VS Code: {str(e)}")
                success_message += f"\nCould not auto-open in VS Code: {str(e)}. Open manually."
        else:
            # Open the directory instead if VS Code not found
            if platform.system() == "Windows":
                os.startfile(project_dir)
            success_message += "\nProject directory opened."
        
        logger.info(success_message)
        return True, success_message
        
    except Exception as e:
        logger.error(f"Error generating code project: {str(e)}")
        return False, f"Error: {str(e)}"

if __name__ == "__main__":
    # Ensure environment variables are loaded
    grok_api_key = os.getenv("GROQ_API_KEY3")
    gemini_api_key = os.getenv("GEMINI_API_KEY3")
    if not grok_api_key and not gemini_api_key:
        print(f"Error: Please set GROQ_API_KEY3 or GEMINI_API_KEY3 in {env_path}")
        sys.exit(1)
    
    # Example usage
    test_query = "Create a simple code for addition of two numbers in python."
    success, result = code_generate_from_query(test_query)
    print(f"Success: {success}")
    print(result)