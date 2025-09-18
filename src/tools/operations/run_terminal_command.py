# command_runner.py
import subprocess
import os
import platform
import re

def run_command(command: str):
    """
    Run a Windows shell command and return its output and error if any.
    Only accepts executable commands, not natural language descriptions.
    
    Args:
        command (str): Valid Windows command (e.g., "mkdir test_folder", "ren old.txt new.txt").
    
    Returns:
        dict: Contains 'success' (bool), 'output' (str), and 'error' (str).
    """
    try:
        # Validate command is not natural language
        if _is_natural_language(command):
            return {
                "success": False,
                "output": "",
                "error": "Invalid input: Pass executable commands only (e.g., 'ren file.txt new.txt'), not descriptive text"
            }
        
        # Apply Windows command fixes
        command = _fix_windows_command(command)
        
        # Execute via cmd.exe for Windows compatibility
        full_command = ['cmd', '/c', command]
        
        result = subprocess.run(
            full_command,
            check=True,
            capture_output=True,
            text=True,
            timeout=30,
            cwd=os.getcwd()  # Use current working directory
        )
        
        return {
            "success": True, 
            "output": result.stdout.strip() if result.stdout else "Command executed successfully", 
            "error": ""
        }
        
    except subprocess.CalledProcessError as e:
        return {
            "success": False, 
            "output": e.stdout.strip() if e.stdout else "", 
            "error": e.stderr.strip() if e.stderr else f"Command failed with exit code {e.returncode}"
        }
    except subprocess.TimeoutExpired:
        return {
            "success": False, 
            "output": "", 
            "error": "Command timed out after 30 seconds"
        }
    except Exception as e:
        return {
            "success": False, 
            "output": "", 
            "error": f"Unexpected error: {str(e)}"
        }

def _is_natural_language(command: str) -> bool:
    """
    Check if the input is natural language instead of a valid command.
    
    Args:
        command (str): Input to check
        
    Returns:
        bool: True if appears to be natural language
    """
    command_lower = command.strip().lower()
    
    # Natural language indicators
    natural_language_patterns = [
        r'\b(please|can you|could you|would you|i want|i need|help me)\b',
        r'\b(create a|make a|generate|produce)\b',
        r'\b(file called|folder called|directory called)\b',
        r'\b(to the|from the|in the|on the)\b',
        r'\b(and then|after that|next)\b',
        r'\.(txt|pdf|docx|xlsx)\s+to\s+',  # "rename file.txt to newname.txt"
        r'\bmatch(ing)?\s+(file|files|path)\b'
    ]
    
    for pattern in natural_language_patterns:
        if re.search(pattern, command_lower):
            return True
    
    # Check if command starts with common Windows commands
    valid_command_starts = [
        'mkdir', 'rmdir', 'dir', 'cd', 'copy', 'xcopy', 'move', 'ren', 'del', 
        'type', 'echo', 'cls', 'tree', 'attrib', 'find', 'findstr', 'sort',
        'tasklist', 'taskkill', 'ping', 'ipconfig', 'systeminfo', 'where'
    ]
    
    first_word = command_lower.split()[0] if command_lower.split() else ""
    
    # If starts with valid command, probably not natural language
    if first_word in valid_command_starts:
        return False
    
    # If contains question words or long sentences, likely natural language
    if any(word in command_lower for word in ['what', 'how', 'why', 'when', 'where', 'which']):
        return True
    
    # If more than 8 words, likely natural language
    if len(command.split()) > 8:
        return True
        
    return False

def _fix_windows_command(command: str) -> str:
    """
    Fix common Windows command issues and provide proper syntax.
    
    Args:
        command (str): Original command
        
    Returns:
        str: Fixed command for Windows
    """
    command = command.strip()
    
    # Common command fixes for Windows
    fixes = {
        # File operations
        'rename': 'ren',  # Windows uses 'ren' not 'rename'
        'remove': 'del',  # Windows uses 'del' not 'remove'
        'list': 'dir',    # Windows uses 'dir' not 'list'
        'copy': 'copy',   # Already correct
        'move': 'move',   # Already correct
        
        # Directory operations
        'mkdir': 'mkdir', # Already correct
        'rmdir': 'rmdir', # Already correct
    }
    
    # Split command to get the base command
    parts = command.split()
    if parts:
        base_cmd = parts[0].lower()
        if base_cmd in fixes:
            parts[0] = fixes[base_cmd]
            command = ' '.join(parts)
    
    # Handle specific problematic patterns
    if 'rename ' in command.lower():
        # Convert "rename old_file new_file" to "ren old_file new_file"
        command = re.sub(r'\brename\s+', 'ren ', command, flags=re.IGNORECASE)
    
    # Fix "file.txt to newfile.txt" pattern
    if ' to ' in command.lower():
        # Convert "ren file.txt to newfile.txt" to "ren file.txt newfile.txt"
        command = re.sub(r'\s+to\s+', ' ', command, flags=re.IGNORECASE)
    
    # Handle file paths with spaces - ensure they're quoted
    if ' ' in command and not ('"' in command or "'" in command):
        parts = command.split()
        if len(parts) >= 2:
            # Check if any part looks like a file path with spaces
            for i, part in enumerate(parts[1:], 1):  # Skip the command itself
                if ('\\' in part or '/' in part) and ' ' in part:
                    # Looks like a path with spaces, wrap in quotes
                    parts[i] = f'"{part}"'
            command = ' '.join(parts)
    
    return command

def validate_command_safety(command: str) -> dict:
    """
    Check command for safety issues (optional validation).
    
    Args:
        command (str): Command to validate
        
    Returns:
        dict: Contains 'safe' (bool) and 'warnings' (list)
    """
    command_lower = command.strip().lower()
    warnings = []
    
    # Check for potentially destructive operations
    dangerous_patterns = [
        ('del *', 'Deletes all files in directory'),
        ('rmdir /s', 'Recursively deletes directory'),
        ('format', 'Formats disk drive'),
        ('diskpart', 'Disk partitioning tool')
    ]
    
    for pattern, description in dangerous_patterns:
        if pattern in command_lower:
            warnings.append(f"WARNING: {description} - {pattern}")
    
    return {
        'safe': len(warnings) == 0,
        'warnings': warnings
    }

# Example usage and testing
if __name__ == "__main__":
    # Test cases - valid commands only
    valid_commands = [
        "mkdir test_folder",
        "echo Hello World > test.txt", 
        "dir",
        "ren test.txt renamed_test.txt",
        "copy renamed_test.txt backup.txt",
        "del backup.txt"
    ]
    
    # Test cases - invalid natural language inputs
    invalid_inputs = [
        "rename top matching file path to AI_Ethics_ES.pdf",
        "please create a folder called documents",
        "can you list all files in the directory",
        "I want to copy file1.txt to backup folder"
    ]
    
    print("=== Testing Valid Commands ===")
    for cmd in valid_commands:
        print(f"\nTesting: {cmd}")
        result = run_command(cmd)
        print(f"Success: {result['success']}")
        if result['output']:
            print(f"Output: {result['output']}")
        if result['error']:
            print(f"Error: {result['error']}")
    
    print("\n=== Testing Invalid Natural Language Inputs ===")
    for cmd in invalid_inputs:
        print(f"\nTesting: {cmd}")
        result = run_command(cmd)
        print(f"Success: {result['success']}")
        print(f"Error: {result['error']}")