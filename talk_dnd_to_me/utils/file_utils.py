"""File utility functions."""

import hashlib
import os
from typing import Optional


def get_file_hash(file_path: str) -> Optional[str]:
    """Calculate SHA256 hash of a file.
    
    Args:
        file_path: Path to the file to hash
        
    Returns:
        SHA256 hash string or None if error
    """
    hash_sha256 = hashlib.sha256()
    try:
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_sha256.update(chunk)
        return hash_sha256.hexdigest()
    except Exception as e:
        print(f"Error hashing file {file_path}: {e}")
        return None


def get_md5_hash(text: str) -> str:
    """Calculate MD5 hash of text.
    
    Args:
        text: Text to hash
        
    Returns:
        MD5 hash string
    """
    return hashlib.md5(text.encode()).hexdigest()


def find_markdown_files(base_path: str) -> list[str]:
    """Find all markdown files recursively in a directory.
    
    Args:
        base_path: Base directory to search
        
    Returns:
        List of markdown file paths
    """
    md_files = []
    if not os.path.exists(base_path):
        return md_files
    
    for root, dirs, files in os.walk(base_path):
        for file in files:
            if file.endswith('.md'):
                md_files.append(os.path.join(root, file))
    
    return md_files
