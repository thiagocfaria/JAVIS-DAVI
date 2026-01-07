"""
Utility functions for Jarvis core modules.
"""
from __future__ import annotations


def normalize_text(text: str) -> str:
    """
    Normalize text for comparison (strip whitespace and convert to lowercase).
    
    This function is used throughout the codebase to ensure consistent
    text comparison. It reduces memory allocations by providing a single
    point of normalization.
    
    Args:
        text: Input text to normalize
        
    Returns:
        Normalized text (stripped and lowercased)
    """
    return text.strip().lower()






