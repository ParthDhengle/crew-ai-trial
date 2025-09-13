import os

def create_folder(path):
    os.makedirs(path, exist_ok=True)
    