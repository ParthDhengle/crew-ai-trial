# src/tools/operations/powerbi_dashboard.py
import os
import sys
import tempfile
import pandas as pd
from datetime import datetime
import warnings
import json
import re
from dotenv import load_dotenv
import subprocess
import platform
from ...utils.logger import setup_logger
from ...crew import AiAgent  # For LLM call integration

# Load .env from project root
env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), ".env")
load_dotenv(env_path)

logger = setup_logger()

# Suppress syntax warnings
warnings.filterwarnings("ignore", category=SyntaxWarning)

PBI_FUNCTIONS_AVAILABLE = False
try:
    import PBI_dashboard_creator
    # Check if functions are available
    required_functions = ['create_blank_dashboard', 'add_csv_from_blob', 'add_card', 'add_slicer', 'add_text_box']
    available_functions = dir(PBI_dashboard_creator)
    
    logger.debug(f"Available PBI functions: {available_functions}")
    
    missing_functions = [func for func in required_functions if func not in available_functions]
    if missing_functions:
        logger.warning(f"Missing PBI functions: {missing_functions}")
    else:
        from PBI_dashboard_creator import (
            create_blank_dashboard,
            add_csv_from_blob,
            add_card,
            add_slicer,
            add_text_box
        )
        PBI_FUNCTIONS_AVAILABLE = True
        logger.info("Successfully imported PBI functions")
except ImportError as e:
    logger.error(f"PBI import error: {str(e)}")
    PBI_FUNCTIONS_AVAILABLE = False

def check_powerbi_installation():
    """Dynamically check if Power BI Desktop is installed by searching common paths and registry."""
    logger.info("Checking Power BI installation.")
    if platform.system() != "Windows":
        logger.warning("Power BI Desktop is Windows-only.")
        return False, None
            possible_paths = [
                r"C:\Program Files\Microsoft Power BI Desktop\bin\PBIDesktop.exe",
                r"C:\Program Files (x86)\Microsoft Power BI Desktop\bin\PBIDesktop.exe",
        os.path.expanduser(r"~\AppData\Local\Microsoft\WindowsApps\Microsoft.MicrosoftPowerBIDesktop_8wekyb3d8bbwe\PBIDesktop.exe")
            ]   
            for path in possible_paths:
                if os.path.exists(path):
            logger.info(f"Power BI found at: {path}")
            return True, path
    # Agentic: Use LLM to generate safe registry query command
    try:
        crew = AiAgent()
        check_query = "Generate safe Windows command to query registry for Power BI Desktop installation path (e.g., reg query HKLM\\SOFTWARE\\Microsoft\\Power BI Desktop)."
        command = crew.run_workflow(check_query)  # Assumes returns safe command str
        result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=10)
        if result.returncode == 0 and "Power BI" in result.stdout:
            # Parse path from output (example regex; adjust based on actual output)
            path_match = re.search(r'([A-Z]:\\(?:[^\\\/:*?"<>|\r\n]+\\)*PBIDesktop\.exe)', result.stdout, re.IGNORECASE)
            if path_match:
                path = path_match.group(1)
                logger.info(f"Power BI found via registry: {path}")
                    return True, path
    except Exception as e:
        logger.error(f"Dynamic install check error: {str(e)}")
    logger.warning("Power BI Desktop not found.")
        return False, None

def get_llm_visual_plan(dataset_path: str, user_query: str) -> dict:
    """Use LLM to analyze dataset and suggest visualizations."""
    logger.info("Getting LLM visual plan.")
    try:
        df = pd.read_csv(dataset_path)
        columns = df.columns.tolist()
        sample = df.head(5).to_json(orient='records')
        crew = AiAgent()
        llm_query = f"Analyze dataset columns: {columns}. Sample: {sample}. User query: {user_query}. Suggest visuals (e.g., [{'type': 'bar', 'x': 'col1', 'y': 'col2'}]). Output JSON."
        response = crew.run_workflow(llm_query)
        plan = json.loads(response)  # Assume JSON output
        logger.debug(f"LLM visual plan: {plan}")
        return plan
    except Exception as e:
        logger.error(f"LLM visual plan error: {str(e)}")
        return {"visuals": []}  # Fallback empty plan

def create_simple_dashboard_files(output_dir: str, dashboard_name: str, df: pd.DataFrame, plan: dict, query: str):
    """Create simple dashboard files without PBI_dashboard_creator (fallback)."""
    logger.info("Creating fallback dashboard files.")
    dashboard_path = os.path.join(output_dir, dashboard_name)
    os.makedirs(dashboard_path, exist_ok=True)
    
    # Save CSV
    csv_path = os.path.join(dashboard_path, "data.csv")
    df.to_csv(csv_path, index=False)
    
    # Create mock PBIX structure (basic JSON for visuals)
    pbix_mock = {
        "name": dashboard_name,
        "data_source": "data.csv",
        "visuals": plan.get("visuals", []),
        "query": query
    }
    with open(os.path.join(dashboard_path, "dashboard.json"), 'w') as f:
        json.dump(pbix_mock, f, indent=2)
    
    logger.info(f"Fallback dashboard created at {dashboard_path}")
    return dashboard_path

def powerbi_generate_dashboard(dataset_path: str, user_query: str) -> tuple[bool, str]:
    """Automate Power BI Desktop: Open app, load data, create LLM-suggested visuals."""
    logger.info(f"Generating Power BI dashboard for {dataset_path} with query: {user_query}")
    try:
        pbi_installed, pbi_path = check_powerbi_installation()
        if not pbi_installed:
            logger.warning("Power BI not installed. Using fallback file creation.")
            # Fallback: Create simple files
            df = pd.read_csv(dataset_path)
            plan = get_llm_visual_plan(dataset_path, user_query)
            output_dir = tempfile.mkdtemp(prefix="pbi_fallback_")
            dashboard_path = create_simple_dashboard_files(output_dir, "fallback_dashboard", df, plan, user_query)
            return True, f"Power BI not found. Created fallback files at {dashboard_path}"
        
        # Get LLM plan for visuals
        plan = get_llm_visual_plan(dataset_path, user_query)
        
        # Open Power BI
        subprocess.Popen([pbi_path])
        logger.info("Power BI Desktop opened.")
        
        # Automation with pywin32: Power BI doesn't have full COM, so limited (e.g., use pywinauto for UI if installed)
        # Note: Full visual creation automation may require pywinauto or manual steps.
        try:
            import pywinauto
            logger.info("pywinauto available for advanced UI automation.")
            # Example: Connect to Power BI window and simulate clicks (advanced; placeholder)
            app = pywinauto.Application().connect(title_re="Power BI Desktop")
            # Simulate loading CSV: This is pseudo-code; actual automation needs recording clicks/keystrokes
            # app.top_window().menu_select("Home -> Get Data -> Text/CSV")
            # ... (implement specific automation steps)
            return True, "Power BI opened and automation started. Manual visual creation may be needed."
        except ImportError:
            logger.warning("pywinauto not installed. Limited to opening app.")
        
        # If PBI_FUNCTIONS_AVAILABLE, use them to generate PBIX
        if PBI_FUNCTIONS_AVAILABLE:
            output_dir = tempfile.mkdtemp(prefix="pbi_")
        dashboard_name = f"auto_dashboard_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                dashboard_path = os.path.join(output_dir, dashboard_name)
                    create_blank_dashboard(dashboard_path)
            add_csv_from_blob(dashboard_path, f"file://{dataset_path}", table_name="Data")
            # Add visuals based on plan
            for visual in plan.get('visuals', []):
                if visual['type'] == 'card':
                    add_card(dashboard_path, visual['field'], visual.get('aggregation', 'sum'))
                # ... (add for slicer, text_box, etc.)
            logger.info(f"PBIX generated at {dashboard_path}")
            if os.getenv("PBI_AUTO_OPEN", "1") == "1":
                subprocess.run([pbi_path, os.path.join(dashboard_path, f"{dashboard_name}.pbix")])
            return True, f"Dashboard generated and opened at {dashboard_path}"
        
        return True, "Power BI opened. Load data manually or install pywinauto for full automation."
                    except Exception as e:
        logger.error(f"Power BI generation error: {str(e)}")
        return False, str(e)

if __name__ == "__main__":
    test_dataset = r"C:\path\to\test.csv"
    test_query = "Create sales dashboard with bar and line charts."
    success, result = powerbi_generate_dashboard(test_dataset, test_query)
    print(success, result)