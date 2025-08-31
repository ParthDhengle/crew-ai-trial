# src/agent_demo/desktop_app.py (modified)
import tkinter as tk
import threading
import time
from pynput import mouse
import pyautogui
import win32clipboard
import win32gui
import sys
import signal
import os
import subprocess
import base64  # Added for encoding multi-line text

# Global variables
popup = None
start_x = 0
start_y = 0
original_hwnd = None
listener = None  # Declare listener as global for signal handler access
root = tk.Tk()
root.withdraw()  # Hide the main root window

def signal_handler(sig, frame):
    global popup, listener, root
    print("Caught Ctrl+C, shutting down...")
    if popup:
        popup.destroy()
    if listener:
        listener.stop()
    root.destroy()
    sys.exit(0)

# Set up signal handler for Ctrl+C (SIGINT)
signal.signal(signal.SIGINT, signal_handler)

def show_popup(x, y):
    global popup, original_hwnd
    if popup:
        popup.destroy()

    # Capture the current foreground window (where the selection likely happened)
    original_hwnd = win32gui.GetForegroundWindow()

    popup = tk.Toplevel(root)
    popup.overrideredirect(True)  # Remove window borders
    popup.attributes('-topmost', True)  # Always on top

    btn = tk.Button(popup, text="Ask AI", command=on_click)
    btn.pack()

    # Position the popup near the mouse cursor with a slight offset
    popup.geometry(f"+{x + 20}+{y + 20}")

    # Automatically hide the popup after 5 seconds if not clicked
    popup.after(5000, lambda: popup.destroy() if popup else None)

def on_click():
    global popup, original_hwnd
    if original_hwnd is None:
        print("No original window captured.")
        return

    # Destroy the popup first to remove it from view
    popup.destroy()
    popup = None

    # Restore focus to the original window
    win32gui.SetForegroundWindow(original_hwnd)
    time.sleep(0.1)  # Brief delay to ensure focus is set

    # Simulate Ctrl+C to copy selected text to clipboard
    pyautogui.hotkey('ctrl', 'c')
    time.sleep(0.1)  # Brief delay to ensure copy operation completes

    # Read from clipboard
    win32clipboard.OpenClipboard()
    try:
        text = win32clipboard.GetClipboardData(win32clipboard.CF_UNICODETEXT)
    except:
        text = "No text selected or unable to copy"
    finally:
        win32clipboard.CloseClipboard()

    # If no valid text, skip
    if text == "No text selected or unable to copy":
        return

    # Prepend "Explain this " to the selected text
    query = f"Explain this {text}"

    # Encode the query in base64 to safely handle multi-line text and special characters
    query_encoded = base64.b64encode(query.encode('utf-8')).decode('ascii')

    # Path to Electron app directory (assuming desktop_app.py is in the same dir as main.py)
    electron_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), 'electron_app'))

    # "Launch" Electron with the encoded query as arg (single instance will forward to existing window)
    subprocess.Popen(['npm', 'start', '--', f'--selected-text-encoded={query_encoded}'], cwd=electron_dir, shell=True)

def on_mouse_click(x, y, button, pressed):
    global start_x, start_y
    if button == mouse.Button.left:
        if pressed:
            start_x, start_y = x, y
        else:
            # Calculate drag distance
            dx = abs(x - start_x)
            dy = abs(y - start_y)
            # If drag detected (threshold to avoid false positives on simple clicks)
            if dx > 10 or dy > 10:
                show_popup(int(x), int(y))

# Start the mouse listener in a separate thread
listener = mouse.Listener(on_click=on_mouse_click)
thread = threading.Thread(target=listener.start)
thread.daemon = True  # Allow thread to exit when main program exits
thread.start()

# Run the Tkinter main loop to handle GUI events
root.mainloop()