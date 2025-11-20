"""
Text utility functions for normalization and processing.
"""
import unicodedata
import re


def normalize_name(raw: str) -> str:
    """
    Normalize team/participant name for matching.

    Applies:
    - Unicode NFC normalization
    - Lowercase conversion
    - Trim leading/trailing whitespace
    - Collapse multiple spaces to single space

    Args:
        raw: Raw name string

    Returns:
        Normalized name string
    """
    if not raw:
        return ""

    # Unicode NFC normalization
    normalized = unicodedata.normalize("NFC", raw)

    # Lowercase
    normalized = normalized.lower()

    # Collapse multiple spaces to single space
    normalized = re.sub(r"\s+", " ", normalized)

    # Trim
    normalized = normalized.strip()

    return normalized
