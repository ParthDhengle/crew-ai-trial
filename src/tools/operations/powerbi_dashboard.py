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

def create_manual_pbip_project(output_dir: str, project_name: str, csv_path: str, plan: dict) -> str:
    """Create a Power BI project manually without using the problematic library."""
    project_dir = os.path.join(output_dir, project_name)
    os.makedirs(project_dir, exist_ok=True)
    
    # Create .pbip file (main project file) - Fixed schema
    pbip_content = {
        "version": "1.0",
        "artifacts": [
            {
                "report": {
                    "path": f"{project_name}.Report"
                }
            },
            {
                "semanticModel": {
                    "path": f"{project_name}.SemanticModel"
                }
            }
        ]
    }
    
    pbip_file = os.path.join(project_dir, f"{project_name}.pbip")
    with open(pbip_file, 'w', encoding='utf-8') as f:
        json.dump(pbip_content, f, indent=2)
    
    # Create Report folder and definition
    report_dir = os.path.join(project_dir, f"{project_name}.Report")
    os.makedirs(report_dir, exist_ok=True)
    
    # Create basic report definition
    report_content = {
        "version": "5.0",
        "config": {
            "version": "5.0",
            "themeCollection": {
                "baseTheme": {
                    "name": "CY24SU06"
                }
            }
        },
        "sections": [
            {
                "name": "ReportSection",
                "displayName": "Main Page",
                "visualContainers": create_visual_containers(plan)
            }
        ]
    }
    
    report_file = os.path.join(report_dir, "definition.pbir")
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(report_content, f, indent=2)
    
    # Create SemanticModel folder and definition
    model_dir = os.path.join(project_dir, f"{project_name}.SemanticModel")
    os.makedirs(model_dir, exist_ok=True)
    
    # Copy CSV file to model directory
    csv_name = os.path.basename(csv_path)
    target_csv = os.path.join(model_dir, csv_name)
    shutil.copy2(csv_path, target_csv)
    
    # Create semantic model definition
    model_content = create_semantic_model_definition(csv_name, plan)
    
    model_file = os.path.join(model_dir, "definition.pbism")
    with open(model_file, 'w', encoding='utf-8') as f:
        json.dump(model_content, f, indent=2)
    
    logger.info(f"Manual Power BI project created at: {project_dir}")
    return pbip_file

def create_visual_containers(plan: dict) -> list:
    """Create visual containers for the report."""
    containers = []
    
    for i, visual in enumerate(plan.get("visuals", [])):
        visual_type = visual.get("type", "bar")
        
        # Map visual types to Power BI visual types
        pbi_visual_type = {
            "bar": "clusteredBarChart",
            "line": "lineChart", 
            "pie": "pieChart",
            "card": "card"
        }.get(visual_type, "clusteredBarChart")
        
        container = {
            "name": f"visual_{i}",
            "position": {
                "x": 100 + (i * 400),
                "y": 200,
                "width": 400,
                "height": 300,
                "tabOrder": i
            },
            "visual": {
                "visualType": pbi_visual_type,
                "query": create_visual_query(visual),
                "objects": {}
            }
        }
        containers.append(container)
    
    return containers

def create_visual_query(visual: dict) -> dict:
    """Create query definition for a visual."""
    return {
        "queryState": {
            "Values": [{
                "Column": {
                    "Expression": {
                        "SourceRef": {"Source": "c1"}
                    },
                    "Property": visual.get("y_field", "")
                },
                "Name": f"Aggregate({visual.get('y_field', '')})"
            }],
            "Category": [{
                "Column": {
                    "Expression": {
                        "SourceRef": {"Source": "c1"}
                    },
                    "Property": visual.get("x_field", "")
                },
                "Name": visual.get("x_field", "")
            }]
        }
    }

def create_semantic_model_definition(csv_name: str, plan: dict) -> dict:
    """Create semantic model definition."""
    table_name = os.path.splitext(csv_name)[0]
    
    return {
        "version": "1.0",
        "model": {
            "culture": "en-US",
            "dataSources": [
                {
                    "name": "LocalFile",
                    "connectionDetails": {
                        "protocol": "file",
                        "address": {
                            "path": csv_name
                        }
                    }
                }
            ],
            "tables": [
                {
                    "name": table_name,
                    "dataCategory": "Uncategorized",
                    "columns": [],  # Will be populated based on CSV
                    "partitions": [
                        {
                            "name": "Partition",
                            "dataView": "full",
                            "source": {
                                "type": "m",
                                "expression": f'let\n    Source = Csv.Document(File.Contents("{csv_name}"),[Delimiter=",", Columns=null, Encoding=65001, QuoteStyle=QuoteStyle.None]),\n    #"Promoted Headers" = Table.PromoteHeaders(Source, [PromoteAllScalars=true])\nin\n    #"Promoted Headers"'
                            }
                        }
                    ]
                }
            ]
        }
    }

def fix_pbi_dashboard_creator_resources():
    """Attempt to fix the PBI_dashboard_creator resources issue."""
    try:
        import PBI_dashboard_creator
        package_path = Path(PBI_dashboard_creator.__file__).parent
        resources_path = package_path / "dashboard_resources"
        
        if not resources_path.exists():
            logger.warning(f"Resources path doesn't exist: {resources_path}")
            # Try to create the missing directory structure
            resources_path.mkdir(parents=True, exist_ok=True)
            logger.info(f"Created resources directory: {resources_path}")
            
            # Create minimal required files
            template_dir = resources_path / "template"
            template_dir.mkdir(exist_ok=True)
            
            # Create a basic template structure
            with open(template_dir / "template.pbip", 'w') as f:
                f.write('{"version": "1.0", "artifacts": []}')
            
            return True
        return True
    except Exception as e:
        logger.error(f"Failed to fix PBI_dashboard_creator resources: {str(e)}")
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
            logger.warning("Power BI Desktop not found. Dashboard files will be created but may not open automatically.")
        
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
        
        logger.info(f"Dashboard plan: {plan}")
        
        # Create temporary directory for dashboard
        output_dir = tempfile.mkdtemp(prefix="powerbi_dashboard_")
        dashboard_name = f"auto_dashboard_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Try using the library first, but fall back to manual creation
        use_manual_creation = True
        pbip_file = None
        
        try:
            # Try to fix the library resources issue
            if fix_pbi_dashboard_creator_resources():
                import PBI_dashboard_creator
                
                # Create new blank dashboard
                PBI_dashboard_creator.create_blank_dashboard.create_new_dashboard(output_dir, dashboard_name)
                dashboard_path = os.path.join(output_dir, dashboard_name)
                logger.info(f"Created new dashboard at: {dashboard_path}")
                
                # Add CSV data source
                dataset_id = PBI_dashboard_creator.add_local_csv.add_csv(dashboard_path, csv_path)
                logger.info(f"Added CSV data source with dataset_id: {dataset_id}")
                
                # Determine dataset_name (assuming it's the CSV filename without extension)
                dataset_name = os.path.basename(csv_path).split('.')[0]
                logger.info(f"Using dataset_name: {dataset_name}")
                
                # Add a new page
                page_id = PBI_dashboard_creator.create_new_page.add_new_page(dashboard_path, "MainPage", title=query)
                logger.info(f"Added new page with page_id: {page_id}")
                
                # Add visuals based on plan
                visual_index = 0
                agg_map = {
                    "sum": "Sum",
                    "count": "Count",
                    "avg": "Average", 
                    "min": "Minimum",
                    "max": "Maximum"
                }
                for visual in plan.get("visuals", []):
                    visual_type = visual.get("type")
                    x_field = visual.get("x_field")
                    y_field = visual.get("y_field")
                    agg = visual.get("aggregation").lower()
                    agg_type = agg_map.get(agg, "Sum")  # Default to Sum if unknown
                    
                    # Example positions (adjust as needed)
                    x_pos = 100 + visual_index * 400
                    y_pos = 200
                    height = 300
                    width = 400
                    visual_id = f"visual_{visual_index}"
                    chart_title = f"{visual_type.capitalize()} of {y_field} by {x_field}"
                    x_axis_title = x_field
                    y_axis_title = y_field
                    
                    chart_type = None
                    if visual_type == "bar":
                        chart_type = "clusteredBarChart"  # Horizontal bar chart; use "clusteredColumnChart" for vertical/column
                    elif visual_type == "line":
                        chart_type = "lineChart"
                    elif visual_type == "pie":
                        chart_type = "pieChart"
                    elif visual_type == "card":
                        chart_type = "card"  # Assuming supported; if not, skip
                    else:
                        logger.warning(f"Unsupported visual type: {visual_type}")
                        continue
                    
                    PBI_dashboard_creator.create_new_chart.add_chart(
                        dashboard_path, page_id, visual_id, chart_type, dataset_name,
                        chart_title=chart_title, x_axis_title=x_axis_title, y_axis_title=y_axis_title,
                        x_axis_var=x_field, y_axis_var=y_field,
                        y_axis_var_aggregation_type=agg_type,
                        x_position=x_pos, y_position=y_pos, height=height, width=width
                    )
                    logger.info(f"Added {visual_type} chart with id: {visual_id}")
                    visual_index += 1
                
                pbip_file = os.path.join(dashboard_path, f"{dashboard_name}.pbip")
                use_manual_creation = False
                
        except Exception as e:
            logger.warning(f"Library approach failed: {str(e)}. Falling back to manual creation.")
            use_manual_creation = True
        
        # Manual creation fallback
        if use_manual_creation:
            logger.info("Using manual Power BI project creation")
            pbip_file = create_manual_pbip_project(output_dir, dashboard_name, csv_path, plan)
        
        # Try to open the dashboard directly in Power BI Desktop
        success_message = f"Dashboard created at: {os.path.dirname(pbip_file)}"
        
        if pbi_installed and pbip_file and os.path.exists(pbip_file):
            try:
                subprocess.run([pbi_path, pbip_file], check=True)
                success_message += "\nDashboard opened in Power BI Desktop."
            except Exception as e:
                logger.warning(f"Failed to open dashboard: {str(e)}")
                success_message += f"\nFailed to open dashboard automatically: {str(e)}. You can open it manually by double-clicking: {pbip_file}"
        else:
            success_message += f"\nTo open the dashboard, double-click: {pbip_file}"
        
        logger.info(success_message)
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
    test_csv = r"C:\Users\Parth Dhengle\Desktop\Projects\Gen Ai\crew\agent_demo\music_model_data.csv"
    test_query = "Generate Power BI dashboard showing bar chart and line chart."
    success, result = powerbi_generate_dashboard(test_csv, test_query)
    print(f"Success: {success}")
    print(result)
    