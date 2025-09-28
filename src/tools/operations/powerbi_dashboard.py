import os
import sys
import tempfile
import pandas as pd
from datetime import datetime
import warnings
import json
import requests
import re
from dotenv import load_dotenv
import subprocess
import platform
import shutil
import zipfile
from pathlib import Path

# Add src/ to sys.path to fix module discovery for absolute imports
script_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.dirname(os.path.dirname(script_dir))  # This points to src/
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

# Suppress syntax warnings (no longer from PBI_dashboard_creator)
warnings.filterwarnings("ignore", category=SyntaxWarning)
from common_functions.Find_project_root import find_project_root
# No sys.path adjustment needed for standalone, as we're removing PBI import

# PBI functions are unavailable; always use manual fallback
PBI_FUNCTIONS_AVAILABLE = False

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
    
    def find_project_root(marker_files=None):
        """
        Fallback: Walk up the directory tree to find the project root based on marker files.
        Defaults to looking for 'README.md' at the root.
        """
        if marker_files is None:
            marker_files = ['README.md']
        
        current_dir = os.path.abspath(os.path.dirname(__file__))
        root = os.path.dirname(current_dir)  # Start from parent to search upward
        
        while root != current_dir:
            if any(os.path.exists(os.path.join(current_dir, marker)) for marker in marker_files):
                return current_dir
            current_dir = root
            root = os.path.dirname(current_dir)
        
        raise ValueError("Project root not found. Ensure a marker file like 'README.md' exists at the root.")

logger = setup_logger()
PROJECT_ROOT = find_project_root()

# Load .env file dynamically from project root
env_path = os.path.join(PROJECT_ROOT, '.env')
if not os.path.exists(env_path):
    logger.error(f".env file not found at {env_path}")
    sys.exit(1)
load_dotenv(env_path)
logger.info(f"Loaded .env file from {env_path}")

def check_powerbi_installation():
    """Check if Power BI Desktop is installed on the system."""
    try:
        if platform.system() == "Windows":
            # Common Power BI installation paths
            possible_paths = [
                r"C:\Program Files\Microsoft Power BI Desktop\bin\PBIDesktop.exe",
                r"C:\Program Files (x86)\Microsoft Power BI Desktop\bin\PBIDesktop.exe",
                r"C:\Users\{}\AppData\Local\Microsoft\WindowsApps\Microsoft.MicrosoftPowerBIDesktop_8wekyb3d8bbwe\PBIDesktop.exe".format(os.getenv('USERNAME'))
            ]
            
            for path in possible_paths:
                if os.path.exists(path):
                    logger.info(f"Power BI Desktop found at: {path}")
                    return True, path
            
            logger.warning("Power BI Desktop not found in common installation paths")
            return False, None
        else:
            logger.warning("Power BI Desktop is only available on Windows")
            return False, None
    except Exception as e:
        logger.error(f"Error checking Power BI installation: {str(e)}")
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

def create_fallback_dashboard_config(columns: list, query: str) -> dict:
    """Create a fallback dashboard configuration when LLM fails."""
    logger.info("Creating fallback dashboard configuration")
    
    # Analyze column types
    numeric_cols = []
    categorical_cols = []
    date_cols = []
    
    for col in columns:
        col_lower = col.lower()
        if any(word in col_lower for word in ['amount', 'price', 'cost', 'value', 'total', 'sum', 'quantity', 'qty', 'score', 'rate', 'bpm']):
            numeric_cols.append(col)
        elif any(word in col_lower for word in ['date', 'time', 'year', 'month', 'day', 'timestamp']):
            date_cols.append(col)
        else:
            categorical_cols.append(col)
    
    # Create basic visuals based on query and available columns
    visuals = []
    
    # Determine visual types from query
    query_lower = query.lower()
    wants_bar = 'bar' in query_lower or 'column' in query_lower
    wants_line = 'line' in query_lower or 'trend' in query_lower
    wants_pie = 'pie' in query_lower or 'donut' in query_lower
    
    # Add bar chart if requested or as default
    if (wants_bar or not (wants_line or wants_pie)) and categorical_cols and numeric_cols:
        visuals.append({
            "type": "bar",
            "x_field": categorical_cols[0],
            "y_field": numeric_cols[0],
            "aggregation": "sum",
            "filters": {}
        })
    
    # Add line chart if requested
    if wants_line and numeric_cols:
        x_field = date_cols[0] if date_cols else categorical_cols[0] if categorical_cols else columns[0]
        visuals.append({
            "type": "line",
            "x_field": x_field,
            "y_field": numeric_cols[0],
            "aggregation": "sum",
            "filters": {}
        })
    
    # Add pie chart if requested
    if wants_pie and categorical_cols and numeric_cols:
        visuals.append({
            "type": "pie",
            "x_field": categorical_cols[0],
            "y_field": numeric_cols[0],
            "aggregation": "sum",
            "filters": {}
        })
    
    # Default to simple bar chart if no visuals created
    if not visuals:
        visuals.append({
            "type": "bar",
            "x_field": columns[0],
            "y_field": columns[1] if len(columns) > 1 else columns[0],
            "aggregation": "sum",
            "filters": {}
        })
    
    return {
        "visuals": visuals,
        "slicers": date_cols + categorical_cols[:2]  # Add up to 2 categorical slicers plus date slicers
    }

def create_powerbi_template_file(output_dir: str, project_name: str, csv_path: str, plan: dict) -> str:
    """Create a Power BI template file that opens CSV data directly."""
    
    # Generate Power BI M Query for CSV import
    csv_name = os.path.basename(csv_path)
    csv_full_path = os.path.abspath(csv_path).replace('\\', '\\\\')  # Escape backslashes for M query
    
    # Create M Query string
    m_query = f'''let
    Source = Csv.Document(File.Contents("{csv_full_path}"),[Delimiter=",", Columns=null, Encoding=65001, QuoteStyle=QuoteStyle.None]),
    #"Promoted Headers" = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),
    #"Changed Type" = Table.TransformColumnTypes(#"Promoted Headers",{{}})
in
    #"Changed Type"'''
    
    # Create a simple Power BI template file (.pbit)
    template_content = create_pbit_template(csv_name, m_query, plan)
    
    # Save as .pbit file (Power BI Template)
    template_path = os.path.join(output_dir, f"{project_name}.pbit")
    
    try:
        # Create the .pbit file (which is essentially a zip file)
        with zipfile.ZipFile(template_path, 'w', zipfile.ZIP_DEFLATED) as pbit_zip:
            # Add the main template files
            pbit_zip.writestr('DataModelSchema', json.dumps(template_content['schema'], indent=2))
            pbit_zip.writestr('Connections', json.dumps(template_content['connections'], indent=2))
            pbit_zip.writestr('Report/Layout', json.dumps(template_content['layout'], indent=2))
            pbit_zip.writestr('Metadata', json.dumps(template_content['metadata'], indent=2))
            
        logger.info(f"Power BI template created at: {template_path}")
        return template_path
    except Exception as e:
        logger.error(f"Failed to create .pbit file: {e}")
        # Fallback: Create instruction file instead
        return create_instruction_file(output_dir, project_name, csv_path, plan)

def create_instruction_file(output_dir: str, project_name: str, csv_path: str, plan: dict) -> str:
    """Create an instruction file with manual steps if PBIT creation fails."""
    instruction_file = os.path.join(output_dir, f"{project_name}_Instructions.txt")
    
    instructions = f"""Power BI Dashboard Creation Instructions
======================================

CSV File: {csv_path}
Query: {plan.get('query', 'Dashboard creation')}

MANUAL STEPS TO CREATE DASHBOARD:

1. Open Power BI Desktop
2. Click "Get Data" > "Text/CSV"
3. Select the CSV file: {csv_path}
4. Click "Load" to import the data

RECOMMENDED VISUALS:
"""
    
    for i, visual in enumerate(plan.get('visuals', []), 1):
        visual_type = visual.get('type', 'bar').title()
        x_field = visual.get('x_field', '')
        y_field = visual.get('y_field', '')
        aggregation = visual.get('aggregation', 'sum').title()
        
        instructions += f"""
{i}. {visual_type} Chart:
   - Drag '{x_field}' to Axis/Category
   - Drag '{y_field}' to Values
   - Aggregation: {aggregation}
"""
    
    if plan.get('slicers'):
        instructions += f"""
RECOMMENDED SLICERS:
"""
        for slicer in plan.get('slicers', []):
            instructions += f"- {slicer}\n"
    
    instructions += f"""
NOTES:
- All files have been prepared in: {output_dir}
- The CSV data should load automatically when you follow these steps
- Adjust visual formatting as needed
- Save your work as a .pbix file when complete

For automatic dashboard creation, ensure you have the latest Power BI Desktop version
and that all file paths are accessible.
"""
    
    with open(instruction_file, 'w', encoding='utf-8') as f:
        f.write(instructions)
    
    logger.info(f"Instruction file created at: {instruction_file}")
    return instruction_file

def create_pbit_template(csv_name: str, m_query: str, plan: dict) -> dict:
    """Create a basic Power BI template structure."""
    table_name = os.path.splitext(csv_name)[0]
    
    # Basic template structure
    template = {
        'schema': {
            'version': '2.0',
            'model': {
                'name': table_name,
                'tables': [
                    {
                        'name': table_name,
                        'source': {
                            'type': 'm',
                            'expression': m_query
                        }
                    }
                ]
            }
        },
        'connections': [],
        'layout': {
            'sections': [
                {
                    'name': 'ReportSection',
                    'displayName': 'Page 1',
                    'visualContainers': []
                }
            ]
        },
        'metadata': {
            'version': '1.0',
            'template': True
        }
    }
    
    return template

def open_powerbi_with_csv(csv_path: str, pbi_path: str) -> bool:
    """Try to open Power BI Desktop and let user manually import CSV."""
    try:
        # Just open Power BI Desktop - user will manually load CSV
        subprocess.Popen([pbi_path])
        logger.info("Power BI Desktop opened. Please manually import your CSV file.")
        return True
    except Exception as e:
        logger.error(f"Failed to open Power BI Desktop: {e}")
        return False

def powerbi_generate_dashboard(csv_file: str, query: str) -> tuple[bool, str]:
    """
    Generates a Power BI dashboard from a CSV file and user query using AI-driven parsing.
    
    Args:
        csv_file (str): Path to the CSV file (absolute or relative to project root).
        query (str): User query describing desired visuals (e.g., "bar chart of sales by region").
    
    Returns:
        tuple[bool, str]: (success, result message or error)
    """
    try:
        # Check Power BI installation
        pbi_installed, pbi_path = check_powerbi_installation()
        if not pbi_installed:
            logger.warning("Power BI Desktop not found. Instructions will be created instead.")
        
        # Verify API keys
        grok_api_key = os.getenv("GROQ_API_KEY3")
        gemini_api_key = os.getenv("GEMINI_API_KEY3")
        if not grok_api_key and not gemini_api_key:
            logger.error(f"No API keys found for GROQ_API_KEY3 or GEMINI_API_KEY3 in {env_path}")
            return False, f"Error: No API keys found for GROQ_API_KEY3 or GEMINI_API_KEY3 in {env_path}"

        # Resolve CSV path relative to project root
        csv_path = os.path.abspath(os.path.join(PROJECT_ROOT, csv_file)) if not os.path.isabs(csv_file) else csv_file
        if not os.path.exists(csv_path):
            logger.error(f"CSV file not found: {csv_path}")
            return False, f"CSV file not found: {csv_path}"
        
        logger.info(f"Generating Power BI dashboard for CSV: {csv_path} with query: {query}")
        
        # Analyze CSV with encoding fallbacks
        df = None
        encodings = ['utf-8', 'latin1', 'iso-8859-1', 'windows-1252']
        for encoding in encodings:
            try:
                df = pd.read_csv(csv_path, encoding=encoding)
                logger.info(f"Successfully read CSV with encoding: {encoding}")
                break
            except UnicodeDecodeError as e:
                logger.warning(f"Failed to read CSV with encoding {encoding}: {str(e)}")
                continue
        
        if df is None:
            logger.error("Failed to read CSV with any encoding. Trying with errors='replace'.")
            try:
                df = pd.read_csv(csv_path, encoding='utf-8', errors='replace')
                logger.info("Read CSV with errors='replace'.")
            except Exception as e:
                logger.error(f"Failed to read CSV: {str(e)}")
                return False, f"Error reading CSV: {str(e)}"
        
        columns = df.columns.tolist()
        sample_data = df.head(3).to_dict(orient='records')  # Reduced sample size
        logger.debug(f"CSV columns: {columns}, Sample data: {sample_data}")
        
        # Construct improved prompt for LLM
        prompt = f"""
You are a Power BI expert. Generate a JSON configuration for a dashboard based on this request.

User Query: "{query}"
CSV Columns: {columns}
Sample Data: {sample_data}

Return ONLY a valid JSON object with this exact structure:
{{
  "visuals": [
    {{
      "type": "bar",
      "x_field": "column_name",
      "y_field": "column_name", 
      "aggregation": "sum",
      "filters": {{}}
    }}
  ],
  "slicers": ["column_name1", "column_name2"]
}}

Visual types: bar, line, pie, card
Aggregations: sum, count, avg, min, max
Choose appropriate fields from the available columns.
Return only the JSON, no explanation.
"""
        
        # Call LLM with retry logic
        response = None
        plan = None
        
        for attempt in range(3):
            logger.info(f"Attempting LLM call #{attempt + 1}")
            
            if grok_api_key and not response:
                response = call_grok(prompt, grok_api_key)
                if response:
                    cleaned = clean_llm_response(response)
                    if cleaned:
                        try:
                            plan = json.loads(cleaned)
                            logger.info("Successfully parsed Grok response")
                            break
                        except json.JSONDecodeError as e:
                            logger.warning(f"Grok JSON decode error: {str(e)}")
                            response = None
            
            if gemini_api_key and not plan:
                response = call_gemini(prompt, gemini_api_key)
                if response:
                    cleaned = clean_llm_response(response)
                    if cleaned:
                        try:
                            plan = json.loads(cleaned)
                            logger.info("Successfully parsed Gemini response")
                            break
                        except json.JSONDecodeError as e:
                            logger.warning(f"Gemini JSON decode error: {str(e)}")
                            response = None
        
        # Use fallback if LLM failed
        if not plan:
            logger.warning("LLM parsing failed after all retries. Using fallback configuration.")
            plan = create_fallback_dashboard_config(columns, query)
        
        # Add the query to the plan for instruction generation
        plan['query'] = query
        
        logger.info(f"Dashboard plan: {plan}")
        
        # Create temporary directory for dashboard
        output_dir = tempfile.mkdtemp(prefix="powerbi_dashboard_")
        dashboard_name = f"auto_dashboard_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Copy CSV to output directory for easier access
        csv_copy_path = os.path.join(output_dir, os.path.basename(csv_path))
        shutil.copy2(csv_path, csv_copy_path)
        logger.info(f"CSV copied to: {csv_copy_path}")
        
        # Create template or instruction file
        logger.info("Creating Power BI template/instruction file")
        result_file = create_powerbi_template_file(output_dir, dashboard_name, csv_copy_path, plan)
        
        # Prepare success message
        success_message = f"Power BI dashboard resources created at: {output_dir}\n"
        success_message += f"Main file: {result_file}\n"
        success_message += f"CSV file: {csv_copy_path}\n\n"
        
        if result_file.endswith('.pbit'):
            success_message += "NEXT STEPS:\n"
            success_message += "1. Double-click the .pbit file to open it in Power BI Desktop\n"
            success_message += "2. The template should load with your data automatically\n"
            success_message += "3. Customize visuals as needed\n"
            success_message += "4. Save as .pbix when complete\n"
        else:
            success_message += "Please follow the instructions in the text file to manually create your dashboard.\n"
        
        # Try to open Power BI Desktop or the result file
        if pbi_installed:
            try:
                if result_file.endswith('.pbit'):
                    # Try to open the template file directly
                    subprocess.run([pbi_path, result_file], check=False)
                    success_message += "\nTemplate opened in Power BI Desktop."
                else:
                    # Just open Power BI Desktop
                    open_powerbi_with_csv(csv_copy_path, pbi_path)
                    success_message += "\nPower BI Desktop opened. Please follow the instructions to import your data."
            except Exception as e:
                logger.warning(f"Failed to open Power BI automatically: {str(e)}")
                success_message += f"\nNote: Could not open Power BI automatically. Please open manually: {result_file}"
        
        logger.info("Dashboard creation process completed successfully")
        return True, success_message
        
    except Exception as e:
        logger.error(f"Error generating Power BI dashboard: {str(e)}")
        return False, f"Error: {str(e)}"

if __name__ == "__main__":
    # Ensure environment variables are loaded
    grok_api_key = os.getenv("GROQ_API_KEY3")
    gemini_api_key = os.getenv("GEMINI_API_KEY3")
    if not grok_api_key and not gemini_api_key:
        print(f"Error: Please set GROQ_API_KEY3 or GEMINI_API_KEY3 in {env_path}")
        sys.exit(1)
    
    # Example usage (replace with your CSV and query)
    test_csv = r"C:\Users\parth\Downloads\CarPrice_Assignment.csv"
    test_query = "Generate Power BI dashboard showing bar chart and line chart."
    success, result = powerbi_generate_dashboard(test_csv, test_query)
    print(f"Success: {success}")
    print(result)