"""
Text utility functions for normalization and processing.
"""
import unicodedata
import re

TRANSLIT = {
    "ø": "o",
    "ö": "o",
    "ä": "a",
    "æ": "ae",
    "œ": "oe",
    "ß": "ss",
    "ł": "l",
    "š": "s",
    "á": "a",
    "à": "a",
    "â": "a",
    "ã": "a",
    "å": "a",
    "é": "e",
    "è": "e",
    "ê": "e",
    "í": "i",
    "ğ": "g",
    "ì": "i",
    "î": "i",
    "ó": "o",
    "ò": "o",
    "ô": "o",
    "õ": "o",
    "ü": "u",
    "ú": "u",
    "ù": "u",
    "û": "u",
    "ç": "c",
    "ñ": "n",
}

TOKEN_CANON = {
    "st": "saint",
    "st.": "saint",
}

SERVICE_TOKENS = {"fc", "afc", "fk", "club", "cf", "ac", "bc", "cd", "as"}

TEAM_ALIAS = {
    # TODO: Move to the alias table
    "wolverhampton-wanderers": "wolves",
    "athletic-bilbao": "athletic-club",
    "sporting-cp": "sporting-lisbon",
    "bayern-munich": "bayern-munchen"
}

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
    - Transliteration of special characters
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

    # Transliteration before character removal
    result = []
    for char in slug:
        result.append(TRANSLIT.get(char, char))
    slug = "".join(result)

    # Replace spaces and underscores with hyphens
    slug = re.sub(r"[\s_]+", "-", slug)

    # Remove special characters, keep only alphanumeric and hyphens
    slug = re.sub(r"[^a-z0-9\-]", "", slug)

    # Collapse multiple hyphens to single hyphen
    slug = re.sub(r"-+", "-", slug)

    # Trim leading/trailing hyphens
    slug = slug.strip("-")

    return slug


def apply_alias(slug: str) -> str:
    return TEAM_ALIAS.get(slug, slug)

def match_slug(odds_slug: str, api_slugs: list[str]) -> str | None:
    if odds_slug in api_slugs:
        return odds_slug

    # 1. alias-слой
    normalized = apply_alias(odds_slug)
    if normalized in api_slugs:
        return normalized

    # 2. fallback — мягкий slugs_match
    for api_slug in api_slugs:
        if slugs_match(api_slug, odds_slug):
            return api_slug

    return None


def canon_parts(slug: str) -> list[str]:
    """
    Canonicalize slug parts using token mapping.

    Args:
        slug: Slug string (e.g., "st-gilloise")

    Returns:
        List of canonicalized parts (e.g., ["saint", "gilloise"])
    """
    parts = [p for p in slug.split("-") if p]
    parts = [p for p in parts if p not in SERVICE_TOKENS]
    return [TOKEN_CANON.get(p, p) for p in parts]


def slugs_match(api_slug: str, odds_slug: str) -> bool:
    if api_slug == odds_slug:
        return True

    api_parts = canon_parts(api_slug)
    odds_parts = canon_parts(odds_slug)

    n = min(len(api_parts), len(odds_parts), 2)
    if n > 0 and api_parts[:n] == odds_parts[:n]:
        return True
    return False


def create_team_slug(name: str) -> str:
    """
    Create team slug from raw team name.

    This is a dedicated function for creating team slugs used as unique identifiers.
    Uses create_slug for consistency.

    Args:
        name: Raw team name string

    Returns:
        Team slug string (e.g., "manchester-united" from "Manchester United")
    """
    return create_slug(name)
