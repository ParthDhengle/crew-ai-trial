# src/agent_demo/tools/operations/system.py
import psutil

def shutdown_system():
    return (True, "Placeholder: Would shut down the system.")

def restart_system():
    return (True, "Placeholder: Would restart the system.")

def check_system_status():
    try:
        cpu = psutil.cpu_percent()
        memory = psutil.virtual_memory().percent
        disk = psutil.disk_usage('/').percent
        return (True, f"System Status:\nCPU: {cpu}%\nMemory: {memory}%\nDisk: {disk}%")
    except Exception as e:
        return (False, f"Failed to check system status: {e}")

def list_running_processes():
    return (True, "Placeholder: Would list all running processes.")

def kill_process(process_id: str):
    return (True, f"Placeholder: Would kill process with ID: {process_id}.")

def run_command(command: str):
    return (True, f"Placeholder: Would run shell command: '{command}'.")

def update_system():
    return (True, "Placeholder: Would check for and apply system updates.")