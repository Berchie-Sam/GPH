"""
Preprocessing utilities

Helper functions for the Hansard preprocessing pipeline.
"""

import re
from typing import Optional


def clean_text(text: str) -> str:
    """
    Basic text cleaning for Hansard content.
    
    - Strip whitespace
    - Normalize multiple spaces
    - Remove control characters
    """
    text = text.strip()
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"[\x00-\x08\x0b-\x0c\x0e-\x1f]", "", text)
    return text


def extract_speaker_and_text(line: str) -> tuple:
    """
    Simple speaker extraction for fallback parsing.
    
    Args:
        line: Raw line from Hansard
        
    Returns:
        (speaker, text) tuple or (None, line) if no speaker pattern
    """
    # Simple pattern: "Name: Text"
    match = re.match(r"^([A-Z][A-Za-z\.\s\-']+?):\s*(.*)", line)
    if match:
        speaker = match.group(1).strip()
        text = match.group(2).strip()
        return speaker, text
    return None, line.strip()


def is_stage_direction(text: str) -> bool:
    """
    Detect stage directions like [Applause], [Laughter], [Interruption].
    
    Stage directions are typically in square brackets and describe
    actions rather than spoken content.
    """
    text = text.strip()
    return bool(re.match(r"^\[.*\]$", text))


def is_interjection(text: str, threshold: int = 12) -> bool:
    """
    Detect short interjections heuristically.
    
    Interjections are typically:
    - Short (fewer than threshold words)
    - Don't end with proper sentence punctuation
    
    Args:
        text: Text to check
        threshold: Word count threshold (default 12)
    """
    word_count = len(text.split())
    ends_properly = text.strip().endswith((".", "!", "?"))
    return word_count < threshold and not ends_properly


def is_question(text: str) -> bool:
    """Detect if text contains a question."""
    return "?" in text


def normalize_name(name: str) -> str:
    """
    Normalize name for matching.
    
    - Remove titles (Mr, Mrs, Dr, etc.)
    - Lowercase
    - Collapse multiple spaces
    """
    # Remove common titles
    titles = ["mr", "mrs", "ms", "miss", "dr", "prof", "hon", 
              "alhaji", "hajia", "rt hon", "rt. hon."]
    name_lower = name.lower()
    for title in titles:
        name_lower = re.sub(rf"^{title}\.?\s+", "", name_lower)
        name_lower = re.sub(rf"\s+{title}\.?\s+", " ", name_lower)
    
    # Normalize spaces and hyphens
    name_lower = re.sub(r"-\s+", "-", name_lower)
    name_lower = re.sub(r"\s+", " ", name_lower)
    
    return name_lower.strip()


def extract_date_from_filename(filename: str) -> Optional[str]:
    """
    Extract date from Hansard filename.
    
    Examples:
        Hansard_1st_August_2025.txt → 1 August 2025
        Hansard_12th_December_2025.txt → 12 December 2025
    """
    # Pattern: number_word_year
    match = re.search(
        r'(\d{1,2})(?:st|nd|rd|th)?[_\s]+([A-Za-z]+)[_\s]+(\d{4})',
        filename
    )
    if match:
        day = match.group(1)
        month = match.group(2)
        year = match.group(3)
        return f"{day} {month} {year}"
    return None


def format_duration(seconds: int) -> str:
    """Format duration in human-readable form."""
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    
    parts = []
    if hours > 0:
        parts.append(f"{hours}h")
    if minutes > 0:
        parts.append(f"{minutes}m")
    if secs > 0 or not parts:
        parts.append(f"{secs}s")
    
    return " ".join(parts)


def calculate_attribution_rate(rows: list) -> dict:
    """
    Calculate party attribution statistics.
    
    Args:
        rows: List of parsed speaker turn dicts
        
    Returns:
        Dict with attribution statistics
    """
    total_speakers = len([r for r in rows if r.get("is_stage_direction") != "1"])
    with_party = len([r for r in rows if r.get("party")])
    
    return {
        "total_speakers": total_speakers,
        "with_party": with_party,
        "without_party": total_speakers - with_party,
        "attribution_rate": with_party / total_speakers if total_speakers > 0 else 0
    }


if __name__ == "__main__":
    # Simple tests
    print("Testing text cleaning...")
    test_text = "  This   is   a    test\nwith  multiple   spaces  "
    print(f"  Input:  {repr(test_text)}")
    print(f"  Output: {repr(clean_text(test_text))}")
    
    print("\nTesting speaker extraction...")
    test_line = "Mr. Speaker: I rise to make a statement."
    speaker, text = extract_speaker_and_text(test_line)
    print(f"  Input: {test_line}")
    print(f"  Speaker: {speaker}, Text: {text}")
    
    print("\nTesting stage direction detection...")
    print(f"  [Applause]: {is_stage_direction('[Applause]')}")
    print(f"  Normal speech: {is_stage_direction('This is normal speech.')}")
