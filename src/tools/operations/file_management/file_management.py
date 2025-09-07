import os
import shutil
import glob

def create_file(filename, content):
    """
    Creates a file with the given content.
    
    Args:
        filename (str): The name of the file to create.
        content (str): The content to write to the file.
    
    Returns:
        tuple: (success: bool, message: str)
    """
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(content)
        return (True, f"File '{filename}' created successfully.")
    except Exception as e:
        return (False, f"Error creating file '{filename}': {str(e)}")

def read_file(filename):
    """
    Reads and returns the content of a file.
    
    Args:
        filename (str): The name of the file to read.
    
    Returns:
        tuple: (success: bool, content or message: str)
    """
    try:
        if not os.path.exists(filename):
            return (False, f"File '{filename}' does not exist.")
        with open(filename, 'r', encoding='utf-8') as f:
            content = f.read()
        return (True, content)
    except Exception as e:
        return (False, f"Error reading file '{filename}': {str(e)}")

def update_file(filename, new_content):
    """
    Updates the content of an existing file.
    
    Args:
        filename (str): The name of the file to update.
        new_content (str): The new content to write to the file.
    
    Returns:
        tuple: (success: bool, message: str)
    """
    try:
        if not os.path.exists(filename):
            return (False, f"File '{filename}' does not exist.")
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(new_content)
        return (True, f"File '{filename}' updated successfully.")
    except Exception as e:
        return (False, f"Error updating file '{filename}': {str(e)}")

def delete_file(filename):
    """
    Deletes the specified file.
    
    Args:
        filename (str): The name of the file to delete.
    
    Returns:
        tuple: (success: bool, message: str)
    """
    try:
        if not os.path.exists(filename):
            return (False, f"File '{filename}' does not exist.")
        os.remove(filename)
        return (True, f"File '{filename}' deleted successfully.")
    except Exception as e:
        return (False, f"Error deleting file '{filename}': {str(e)}")

def list_files(directory):
    """
    Lists all files in the specified directory.
    
    Args:
        directory (str): The path to the directory.
    
    Returns:
        tuple: (success: bool, files_list or message: list or str)
    """
    try:
        if not os.path.isdir(directory):
            return (False, f"Directory '{directory}' does not exist or is not a directory.")
        files = [f for f in os.listdir(directory) if os.path.isfile(os.path.join(directory, f))]
        return (True, files)
    except Exception as e:
        return (False, f"Error listing files in '{directory}': {str(e)}")

def copy_file(source, destination):
    """
    Copies a file from source to destination.
    
    Args:
        source (str): The source file path.
        destination (str): The destination file path.
    
    Returns:
        tuple: (success: bool, message: str)
    """
    try:
        if not os.path.exists(source):
            return (False, f"Source file '{source}' does not exist.")
        shutil.copy2(source, destination)
        return (True, f"File copied from '{source}' to '{destination}' successfully.")
    except Exception as e:
        return (False, f"Error copying file from '{source}' to '{destination}': {str(e)}")

def move_file(source, destination):
    """
    Moves a file from source to destination.
    
    Args:
        source (str): The source file path.
        destination (str): The destination file path.
    
    Returns:
        tuple: (success: bool, message: str)
    """
    try:
        if not os.path.exists(source):
            return (False, f"Source file '{source}' does not exist.")
        shutil.move(source, destination)
        return (True, f"File moved from '{source}' to '{destination}' successfully.")
    except Exception as e:
        return (False, f"Error moving file from '{source}' to '{destination}': {str(e)}")

def search_files(directory, pattern):
    """
    Searches for files matching a pattern in a directory.
    
    Args:
        directory (str): The path to the directory.
        pattern (str): The file pattern to match (e.g., '*.txt').
    
    Returns:
        tuple: (success: bool, matching_files or message: list or str)
    """
    try:
        if not os.path.isdir(directory):
            return (False, f"Directory '{directory}' does not exist or is not a directory.")
        search_path = os.path.join(directory, pattern)
        matching_files = glob.glob(search_path)
        return (True, matching_files)
    except Exception as e:
        return (False, f"Error searching files in '{directory}' with pattern '{pattern}': {str(e)}")