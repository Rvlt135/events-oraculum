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


def create_slug(name: str) -> str:
    """
    Create URL-friendly slug from name.

    Converts name to slug format:
    - Unicode NFC normalization
    - Lowercase conversion
    - Replace spaces with hyphens
    - Remove special characters (keep only alphanumeric and hyphens)
    - Collapse multiple hyphens to single hyphen
    - Trim leading/trailing hyphens

    Args:
        name: Name string to convert to slug

    Returns:
        Slug string (e.g., "manchester-united" from "Manchester United")
    """
    if not name:
        return ""

    # Unicode NFC normalization
    slug = unicodedata.normalize("NFC", name)

    # Lowercase
    slug = slug.lower()

    # Replace spaces and underscores with hyphens
    slug = re.sub(r"[\s_]+", "-", slug)

    # Remove special characters, keep only alphanumeric and hyphens
    slug = re.sub(r"[^a-z0-9\-]", "", slug)

    # Collapse multiple hyphens to single hyphen
    slug = re.sub(r"-+", "-", slug)

    # Trim leading/trailing hyphens
    slug = slug.strip("-")

    return slug


def create_team_slug(name: str) -> str:
    """
    Create team slug from raw team name.

    This is a dedicated function for creating team slugs used as unique identifiers.
    Uses the same logic as create_slug for consistency.

    Args:
        name: Raw team name string

    Returns:
        Team slug string (e.g., "manchester-united" from "Manchester United")
    """
    return create_slug(name)
