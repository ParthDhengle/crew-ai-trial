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
        if any(word in col_lower for word in ['amount', 'price', 'cost', 'value', 'total', 'sum', 'quantity', 'qty']):
            numeric_cols.append(col)
        elif any(word in col_lower for word in ['date', 'time', 'year', 'month', 'day']):
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

def create_simple_dashboard_files(output_dir: str, dashboard_name: str, df: pd.DataFrame, plan: dict, query: str):
    """Create simple dashboard files without using PBI_dashboard_creator."""
    logger.info("Creating dashboard files manually")
    
    dashboard_path = os.path.join(output_dir, dashboard_name)
    os.makedirs(dashboard_path, exist_ok=True)
    
    # Create a simple Power BI project structure
    # Note: This creates a basic structure, but actual Power BI functionality requires proper PBIP format
    model_bim = {
        "name": dashboard_name,
        "tables": [
            {
                "name": "DataTable",
                "columns": [{"name": col, "dataType": "string"} for col in df.columns]
            }
        ]
    }
    
    with open(os.path.join(dashboard_path, "model.bim"), 'w') as f:
        json.dump(model_bim, f, indent=2)
    
    # Create report layout file (simplified)
    report_layout = {
        "name": dashboard_name,
        "pages": [
            {
                "name": "Page1",
                "visuals": plan.get("visuals", [])
            }
        ]
    }
    
    with open(os.path.join(dashboard_path, "report.json"), 'w') as f:
        json.dump(report_layout, f, indent=2)
    
    # Save CSV data
    csv_output_path = os.path.join(dashboard_path, "data.csv")
    df.to_csv(csv_output_path, index=False)
    
    # Create a README file with dashboard details
    readme_content = f"""# Power BI Dashboard: {dashboard_name}

## Query: {query}

## Data Source: 
- File: data.csv
- Columns: {', '.join(df.columns)}
- Rows: {len(df)}

## Planned Visuals:
"""
    
    for i, visual in enumerate(plan.get("visuals", []), 1):
        readme_content += f"{i}. {visual.get('type', 'unknown').title()} Chart - {visual.get('x_field', 'N/A')} vs {visual.get('y_field', 'N/A')}\n"
    
    readme_content += f"\n## Slicers: {', '.join(plan.get('slicers', []))}\n"
    
    with open(os.path.join(dashboard_path, "README.md"), 'w') as f:
        f.write(readme_content)
    
    return dashboard_path

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
            logger.warning("Power BI Desktop not found. Dashboard files will be created but may not open automatically.")
        
        # Verify API keys
        grok_api_key = os.getenv("GROQ_API_KEY1")
        gemini_api_key = os.getenv("GEMINI_API_KEY1")
        if not grok_api_key and not gemini_api_key:
            logger.error(f"No API keys found for GROQ_API_KEY1 or GEMINI_API_KEY1 in {env_path}")
            return False, f"Error: No API keys found for GROQ_API_KEY1 or GEMINI_API_KEY1 in {env_path}"

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
        
        logger.info(f"Dashboard plan: {plan}")
        
        # Create temporary directory for dashboard
        output_dir = tempfile.mkdtemp(prefix="powerbi_dashboard_")
        dashboard_name = f"auto_dashboard_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Always create dashboard files manually (PBI functions unavailable)
        dashboard_path = create_simple_dashboard_files(output_dir, dashboard_name, df, plan, query)
        logger.info("Created manual dashboard files (PBI automation unavailable).")
        
        # Try to open the dashboard
        success_message = f"Dashboard files created at: {dashboard_path}"
        
        if pbi_installed:
            try:
                # Try to open with Power BI if available
                pbip_file = os.path.join(dashboard_path, f"{dashboard_name}.pbip")
                if os.path.exists(pbip_file):
                    os.startfile(pbip_file)
                    success_message += "\nDashboard opened in Power BI Desktop."
                else:
                    # Open the directory instead
                    if platform.system() == "Windows":
                        os.startfile(dashboard_path)
                    success_message += "\nDashboard directory opened. Check README.md for details."
            except Exception as e:
                logger.warning(f"Failed to open dashboard: {str(e)}")
                success_message += f"\nCould not auto-open dashboard: {str(e)}"
        
        logger.info(success_message)
        return True, success_message
        
    except Exception as e:
        logger.error(f"Error generating Power BI dashboard: {str(e)}")
        return False, f"Error: {str(e)}"

if __name__ == "__main__":
    # Ensure environment variables are loaded
    grok_api_key = os.getenv("GROQ_API_KEY1")
    gemini_api_key = os.getenv("GEMINI_API_KEY1")
    if not grok_api_key and not gemini_api_key:
        print(f"Error: Please set GROQ_API_KEY1 or GEMINI_API_KEY1 in {env_path}")
        sys.exit(1)
    
    # Example usage
    test_csv = os.path.join(PROJECT_ROOT, "sales_data.csv")  # Relative to project root
    test_query = "Generate Power BI dashboard showing bar chart and line chart."
    success, result = powerbi_generate_dashboard(test_csv, test_query)
    print(f"Success: {success}")
    print(result)