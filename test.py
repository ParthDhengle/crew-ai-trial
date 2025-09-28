# command_runner.py
import subprocess
import os
import platform
import re
from pathlib import Path

def get_desktop_path():
    """
    Get the user's desktop path across different operating systems.
    
    Returns:
        str: Path to user's desktop directory
    """
    if platform.system() == "Windows":
        # Try multiple methods to get desktop path on Windows
        desktop_path = os.path.join(os.path.expanduser("~"), "Desktop")
        if os.path.exists(desktop_path):
            return desktop_path
        
        # Alternative for Windows with different language settings
        import winreg
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, 
                                r"Software\Microsoft\Windows\CurrentVersion\Explorer\Shell Folders")
            desktop_path = winreg.QueryValueEx(key, "Desktop")[0]
            winreg.CloseKey(key)
            return desktop_path
        except:
            pass
    
    # Fallback for other systems or if Windows method fails
    return os.path.join(os.path.expanduser("~"), "Desktop")

def should_use_desktop_default(command: str) -> bool:
    """
    Determine if command should default to desktop path.
    
    Args:
        command (str): The command to analyze
        
    Returns:
        bool: True if command should use desktop as default path
    """
    command_lower = command.strip().lower()
    
    # Commands that typically work with files/directories
    file_commands = ['mkdir', 'rmdir', 'copy', 'xcopy', 'move', 'ren', 'del', 'type', 'echo']
    
    # Check if command starts with file operation
    first_word = command_lower.split()[0] if command_lower.split() else ""
    if first_word not in file_commands:
        return False
    
    # Don't change if command already contains absolute paths
    if ':' in command:  # Windows absolute path (C:\, D:\, etc.)
        return False
    
    # Don't change if command contains relative path indicators
    if '..' in command or command.startswith('./') or command.startswith('.\\'):
        return False
        
    # Don't change if command already contains full paths
    if '\\' in command and len(command.split('\\')) > 2:
        return False
        
    return True

def add_desktop_path_to_command(command: str) -> str:
    """
    Modify command to operate in desktop directory when no path is specified.
    
    Args:
        command (str): Original command
        
    Returns:
        str: Modified command with desktop path
    """
    if not should_use_desktop_default(command):
        return command
    
    desktop_path = get_desktop_path()
    parts = command.split()
    
    if not parts:
        return command
    
    cmd = parts[0].lower()
    
    # Handle different command types
    if cmd == 'mkdir' and len(parts) == 2:
        # mkdir folder_name -> mkdir "C:\Users\User\Desktop\folder_name"
        folder_name = parts[1].strip('"')
        return f'mkdir "{os.path.join(desktop_path, folder_name)}"'
    
    elif cmd in ['copy', 'xcopy'] and len(parts) >= 2:
        # If source doesn't have path, add desktop path
        source = parts[1].strip('"')
        if not ('\\' in source or ':' in source):
            parts[1] = f'"{os.path.join(desktop_path, source)}"'
        
        # If destination doesn't have path and exists, add desktop path
        if len(parts) >= 3:
            dest = parts[2].strip('"')
            if not ('\\' in dest or ':' in dest):
                parts[2] = f'"{os.path.join(desktop_path, dest)}"'
        
        return ' '.join(parts)
    
    elif cmd == 'move' and len(parts) >= 3:
        # Similar to copy
        source = parts[1].strip('"')
        if not ('\\' in source or ':' in source):
            parts[1] = f'"{os.path.join(desktop_path, source)}"'
        
        dest = parts[2].strip('"')
        if not ('\\' in dest or ':' in dest):
            parts[2] = f'"{os.path.join(desktop_path, dest)}"'
        
        return ' '.join(parts)
    
    elif cmd in ['ren', 'del', 'type'] and len(parts) >= 2:
        # Single file operations
        filename = parts[1].strip('"')
        if not ('\\' in filename or ':' in filename):
            parts[1] = f'"{os.path.join(desktop_path, filename)}"'
        
        return ' '.join(parts)
    
    elif cmd == 'echo' and '>' in command:
        # echo "text" > filename
        parts = command.split('>')
        if len(parts) == 2:
            echo_part = parts[0].strip()
            filename = parts[1].strip().strip('"')
            if not ('\\' in filename or ':' in filename):
                return f'{echo_part} > "{os.path.join(desktop_path, filename)}"'
    
    return command

def run_command(command: str, use_desktop_default: bool = True):
    """
    Run a Windows shell command and return its output and error if any.
    Only accepts executable commands, not natural language descriptions.
    
    Args:
        command (str): Valid Windows command (e.g., "mkdir test_folder", "ren old.txt new.txt").
        use_desktop_default (bool): If True, operations without specified paths default to Desktop.
    
    Returns:
        dict: Contains 'success' (bool), 'output' (str), 'error' (str), and 'executed_command' (str).
    """
    try:
        # Validate command is not natural language
        if _is_natural_language(command):
            return {
                "success": False,
                "output": "",
                "error": "Invalid input: Pass executable commands only (e.g., 'ren file.txt new.txt'), not descriptive text",
                "executed_command": command
            }
        
        # Apply Windows command fixes
        command = _fix_windows_command(command)
        
        # Apply desktop path default if enabled
        original_command = command
        if use_desktop_default:
            command = add_desktop_path_to_command(command)
        
        # Execute via cmd.exe for Windows compatibility
        full_command = ['cmd', '/c', command]
        
        result = subprocess.run(
            full_command,
            check=True,
            capture_output=True,
            text=True,
            timeout=30,
            cwd=get_desktop_path() if use_desktop_default else os.getcwd()
        )
        
        return {
            "success": True, 
            "output": result.stdout.strip() if result.stdout else "Command executed successfully", 
            "error": "",
            "executed_command": command,
            "original_command": original_command
        }
        
    except subprocess.CalledProcessError as e:
        return {
            "success": False, 
            "output": e.stdout.strip() if e.stdout else "", 
            "error": e.stderr.strip() if e.stderr else f"Command failed with exit code {e.returncode}",
            "executed_command": command,
            "original_command": original_command if 'original_command' in locals() else command
        }
    except subprocess.TimeoutExpired:
        return {
            "success": False, 
            "output": "", 
            "error": "Command timed out after 30 seconds",
            "executed_command": command,
            "original_command": original_command if 'original_command' in locals() else command
        }
    except Exception as e:
        return {
            "success": False, 
            "output": "", 
            "error": f"Unexpected error: {str(e)}",
            "executed_command": command,
            "original_command": original_command if 'original_command' in locals() else command
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
    print("=== Desktop Path Detection ===")
    print(f"Desktop path: {get_desktop_path()}")
    
    # Test cases - commands that should get desktop path
    desktop_commands = [
        "mkdir test_folder",
        "echo Hello World > test.txt", 
        "ren test.txt renamed_test.txt",
        "copy file1.txt file2.txt",
        "del unwanted.txt"
    ]
    
    # Test cases - commands that should NOT get desktop path
    absolute_path_commands = [
        "mkdir C:\\temp\\new_folder",
        "copy C:\\source.txt D:\\destination.txt",
        "dir C:\\Windows",
        "ping google.com"
    ]
    
    print("\n=== Testing Commands with Desktop Default ===")
    for cmd in desktop_commands:
        print(f"\nOriginal: {cmd}")
        modified = add_desktop_path_to_command(cmd)
        print(f"Modified: {modified}")
        # Uncomment to actually execute:
        # result = run_command(cmd)
        # print(f"Success: {result['success']}")
    
    print("\n=== Testing Commands that Should NOT Use Desktop Default ===")
    for cmd in absolute_path_commands:
        print(f"\nOriginal: {cmd}")
        modified = add_desktop_path_to_command(cmd)
        print(f"Modified: {modified}")
        print(f"Changed: {'Yes' if cmd != modified else 'No'}")
    
    print("\n=== Example with Actual Execution ===")
    # Safe test command
    test_cmd = "mkdir test_desktop_folder"
    print(f"Testing: {test_cmd}")
    result = run_command(test_cmd)
    print(f"Success: {result['success']}")
    print(f"Original command: {result.get('original_command', 'N/A')}")
    print(f"Executed command: {result['executed_command']}")
    if result['error']:
        print(f"Error: {result['error']}")


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