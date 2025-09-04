# src/agent_demo/tools/operations/utilities.py
import random
import string

def translate(text: str, target_language: str):
    return (True, f"Placeholder: Would translate '{text}' to {target_language}.")

def summarize_text(text: str):
    return (True, f"Placeholder: Would summarize text: '{text[:50]}...'.")

def scan_qr_code(image_path: str):
    return (True, f"Placeholder: Would scan QR code from {image_path}.")

def calculate(expression: str):
    try:
        allowed_chars = set('0123456789+-*/.() ')
        if all(c in allowed_chars for c in expression):
            result = eval(expression)
            return (True, f"Result: {result}")
        else:
            return (False, "Expression contains invalid characters")
    except Exception as e:
        return (False, f"Failed to calculate: {e}")

def unit_convert(value: float, from_unit: str, to_unit: str):
    return (True, f"Placeholder: Would convert {value} {from_unit} to {to_unit}.")

def spell_check(text: str):
    return (True, f"Placeholder: Would spell check text: '{text[:50]}...'.")

def generate_password(length: int = 12):
    try:
        chars = string.ascii_letters + string.digits + "!@#$%^&*"
        password = ''.join(random.choice(chars) for _ in range(int(length)))
        return (True, f"Generated password: {password}")
    except Exception as e:
        return (False, f"Failed to generate password: {e}")