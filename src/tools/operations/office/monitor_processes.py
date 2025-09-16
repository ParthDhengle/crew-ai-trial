# src/tools/operations/office/monitor_processes.py
import psutil
from ....utils.logger import setup_logger

logger = setup_logger()

def monitor_processes(filter_app: str = None) -> str:
    """Monitor open processes/apps on PC."""
    try:
        processes = []
        for proc in psutil.process_iter(['pid', 'name', 'username']):
            try:
                info = proc.info
                if filter_app and filter_app.lower() not in info['name'].lower():
                    continue
                processes.append(f"PID: {info['pid']} | Name: {info['name']} | User: {info['username']}")
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        result = "\n".join(processes) or "No matching processes found."
        logger.info(f"Monitored processes (filter: {filter_app}): {result[:200]}...")  # Log
        return result
    except Exception as e:
        logger.error(f"Monitoring error: {str(e)}")  # Log error
        return str(e)