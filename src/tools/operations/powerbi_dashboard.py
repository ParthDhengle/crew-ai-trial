import os
import sys
import tempfile
import pandas as pd
from datetime import datetime
import warnings
import json
import requests

# Suppress syntax warnings from PBI_dashboard_creator
warnings.filterwarnings("ignore", category=SyntaxWarning)

# Adjust sys.path for standalone execution
if __name__ == "__main__":
    sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

try:
    from PBI_dashboard_creator import (
        create_blank_dashboard,
        add_csv_from_blob,
        add_card,
        add_slicer,
        add_text_box
    )
except ImportError as e:
    raise ImportError(
        f"Failed to import required functions from PBI_dashboard_creator: {str(e)}. "
        "Run 'import PBI_dashboard_creator; print(dir(PBI_dashboard_creator))' to check available functions. "
        "Look for alternatives like add_data_source, add_table, or add_report_page."
    )

# Absolute imports to avoid relative import issues
try:
    from src.utils.logger import setup_logger
    from src.common_functions.Find_project_root import find_project_root
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
        return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logger = setup_logger()
PROJECT_ROOT = find_project_root()

def call_grok(prompt: str, api_key: str) -> str:
    """Call Grok API directly."""
    try:
        from groq import Groq
        client = Groq(api_key=api_key)
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=1000
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
        # Resolve CSV path
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
        sample_data = df.head(5).to_dict(orient='records')
        logger.debug(f"CSV columns: {columns}, Sample data: {sample_data}")
        
        # Construct prompt for LLM
        prompt = f"""
        You are a Power BI expert. Given a user query and a CSV dataset, generate a plan for a Power BI dashboard.
        Query: {query}
        CSV Columns: {columns}
        Sample Data (first 5 rows): {sample_data}
        
        Analyze the query and dataset to determine:
        1. Visual types (e.g., bar, line, pie, card).
        2. Fields for each visual (x-axis, y-axis, value, etc.).
        3. Aggregations (e.g., sum, count) if needed.
        4. Filters or slicers (e.g., by date, category).
        
        Output a JSON object with:
        - visuals: List of visuals [{{"type": "bar", "x_field": "column_name", "y_field": "column_name", "aggregation": "sum", "filters": {{"column": "value"}}}}, ...]
        - slicers: List of slicer fields ["column_name", ...]
        
        If the query is vague, infer appropriate visuals based on data types (e.g., categorical → bar, time series → line).
        """
        
        # Call LLM (Grok first, Gemini fallback)
        response = None
        grok_api_key = os.getenv("GROQ_API_KEY1")
        gemini_api_key = os.getenv("GEMINI_API_KEY1")
        
        if grok_api_key:
            response = call_grok(prompt, grok_api_key)
        if not response and gemini_api_key:
            response = call_gemini(prompt, gemini_api_key)
        
        if not response:
            logger.warning("LLM parsing failed. Falling back to default bar card.")
            plan = {
                "visuals": [{"type": "bar", "x_field": columns[0], "y_field": columns[-1], "aggregation": "sum", "filters": {}}],
                "slicers": [col for col in columns if "date" in col.lower()]
            }
        else:
            try:
                plan = json.loads(response.strip())
            except json.JSONDecodeError as e:
                logger.warning(f"LLM response not valid JSON: {str(e)}. Falling back to default bar card.")
                plan = {
                    "visuals": [{"type": "bar", "x_field": columns[0], "y_field": columns[-1], "aggregation": "sum", "filters": {}}],
                    "slicers": [col for col in columns if "date" in col.lower()]
                }
        
        visuals = plan.get("visuals", [])
        slicers = plan.get("slicers", [])
        if not visuals:
            logger.warning("No visuals generated; using default bar card")
            visuals = [{"type": "bar", "x_field": columns[0], "y_field": columns[-1], "aggregation": "sum", "filters": {}}]
        
        # Create temporary directory for dashboard
        output_dir = tempfile.mkdtemp(prefix="powerbi_dashboard_")
        dashboard_name = f"auto_dashboard_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        dashboard_path = os.path.join(output_dir, dashboard_name)
        
        # Create and populate dashboard
        create_blank_dashboard(dashboard_path)
        # Add CSV data
        try:
            add_csv_from_blob(dashboard_path, f"file://{csv_path}", table_name="DataTable")
        except Exception as e:
            logger.warning(f"add_csv_from_blob failed: {str(e)}. Trying DataFrame workaround.")
            try:
                from PBI_dashboard_creator import add_table
                add_table(dashboard_path, table_name="DataTable", data=df)
            except (ImportError, Exception) as e:
                logger.error(f"No suitable method to add CSV data: {str(e)}. Check PBI_dashboard_creator documentation.")
                return False, "Error: No suitable method to add CSV data."
        
        # Assume create_blank_dashboard creates a default page
        add_text_box(dashboard_path, page_id="default", text=query, x=10, y=10, width=500, height=50)
        
        # Add visuals using add_card
        pos_y = 100
        for visual in visuals:
            card_type = visual.get("type", "bar")
            x_field = visual.get("x_field", columns[0])
            y_field = visual.get("y_field", columns[-1])
            aggregation = visual.get("aggregation", "sum")
            
            if x_field not in columns or y_field not in columns:
                logger.warning(f"Invalid fields {x_field}, {y_field}; skipping visual")
                continue
                
            try:
                add_card(
                    dashboard_path,
                    page_id="default",
                    card_type=card_type,
                    x_field=x_field,
                    y_field=y_field,
                    aggregation=aggregation,
                    x=10,
                    y=pos_y,
                    width=400,
                    height=300
                )
                pos_y += 350
            except Exception as e:
                logger.warning(f"add_card failed: {str(e)}. Skipping visual.")
                continue
        
        # Add slicers
        for slicer_field in slicers:
            if slicer_field in columns:
                try:
                    add_slicer(dashboard_path, page_id="default", field=slicer_field, x=420, y=100, width=200, height=300)
                except Exception as e:
                    logger.warning(f"add_slicer failed: {str(e)}. Skipping slicer.")
        
        # Open the dashboard
        pbip_file = os.path.join(dashboard_path, f"{dashboard_name}.pbip")
        try:
            os.startfile(pbip_file)
            logger.info(f"Dashboard generated and opened: {pbip_file}")
            return True, f"Power BI dashboard generated and opened at {pbip_file}"
        except Exception as e:
            logger.error(f"Failed to open dashboard: {str(e)}")
            return False, f"Error opening dashboard: {str(e)}"
    
    except Exception as e:
        logger.error(f"Error generating Power BI dashboard: {str(e)}")
        return False, f"Error: {str(e)}"

if __name__ == "__main__":
    # Ensure environment variables are set
    if not os.getenv("GROQ_API_KEY1") and not os.getenv("GEMINI_API_KEY1"):
        print("Error: Please set GROQ_API_KEY1 or GEMINI_API_KEY1 environment variable.")
        sys.exit(1)
    
    # Example usage
    test_csv = r"C:\Users\soham\OneDrive\Desktop\sales_data_sample.csv"
    test_query = "Generate Power BI dashboard showing bar chart of sales by region and line chart of sales over time"
    success, result = powerbi_generate_dashboard(test_csv, test_query)
    print(f"Success: {success}")
    print(result)