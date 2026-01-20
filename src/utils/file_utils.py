"""
File utilities for saving and managing files
"""
import os
import re
from pathlib import Path
from typing import Tuple


def sanitize_filename(filename: str) -> str:
    """
    Create a safe filename by removing special characters
    
    Args:
        filename: Original filename
        
    Returns:
        Sanitized filename
    """
    # Remove special characters
    safe = re.sub(r'[^\w\s-]', '', filename)
    # Replace spaces and hyphens with underscores
    safe = re.sub(r'[-\s]+', '_', safe)
    return safe.strip('_')


def save_pdf(content: bytes, filename: str, directory: Path) -> str:
    """
    Save PDF content to file
    
    Args:
        content: PDF bytes
        filename: Base filename
        directory: Directory to save to
        
    Returns:
        Path to saved file
    """
    safe_filename = sanitize_filename(filename)
    filepath = directory / f"{safe_filename}.pdf"
    
    with open(filepath, 'wb') as f:
        f.write(content)
    
    return str(filepath)


def save_text(content: str, filename: str, directory: Path, metadata: dict = None) -> str:
    """
    Save text content to file with optional metadata header
    
    Args:
        content: Text content
        filename: Base filename
        directory: Directory to save to
        metadata: Optional metadata to include
        
    Returns:
        Path to saved file
    """
    safe_filename = sanitize_filename(filename)
    filepath = directory / f"{safe_filename}.txt"
    
    with open(filepath, 'w', encoding='utf-8') as f:
        # Write metadata if provided
        if metadata:
            for key, value in metadata.items():
                f.write(f"{key}: {value}\n")
            f.write("=" * 80 + "\n\n")
        
        # Write content
        f.write(content)
    
    return str(filepath)


def file_exists(filename: str, directory: Path) -> bool:
    """
    Check if a file exists
    
    Args:
        filename: Base filename
        directory: Directory to check
        
    Returns:
        True if file exists
    """
    safe_filename = sanitize_filename(filename)
    filepath = directory / f"{safe_filename}.pdf"
    return filepath.exists()