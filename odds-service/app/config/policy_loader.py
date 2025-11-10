"""
Policy loader for plan visibility configuration.
Loads YAML configuration once at startup and caches in memory.
"""
from typing import Dict, Literal, Optional
import yaml
from pathlib import Path
import structlog

logger = structlog.get_logger()

PlanVisibility = Literal["free", "pro", "unavailable"]

_policy_cache: Optional[Dict] = None
_POLICY_FILE_PATH = Path(__file__).parent / "provider_policy.yml"


def _load_yaml() -> Dict:
    """Load YAML policy file from disk."""
    try:
        with open(_POLICY_FILE_PATH, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
            logger.info("policy_yaml_loaded", path=str(_POLICY_FILE_PATH))
            return data or {}
    except FileNotFoundError:
        logger.error("policy_file_not_found", path=str(_POLICY_FILE_PATH))
        return {}
    except yaml.YAMLError as e:
        logger.error("policy_yaml_parse_error", error=str(e))
        return {}
    except Exception as e:
        logger.error("policy_load_unexpected_error", error=str(e))
        return {}


def _initialize_policy() -> None:
    """Initialize policy cache if not already loaded."""
    global _policy_cache
    if _policy_cache is None:
        _policy_cache = _load_yaml()
        logger.info("policy_cache_initialized")


def reload_policy() -> None:
    """
    Reload policy from YAML file.
    This function is for future hot-reload support.
    Currently not used in production.
    """
    global _policy_cache
    _policy_cache = _load_yaml()
    logger.info("policy_cache_reloaded")


def get_visibility_for_category(provider: str, category: str) -> PlanVisibility:
    """
    Get plan visibility for a sport category.

    Args:
        provider: Provider name (e.g., 'odds_api')
        category: Sport category (e.g., 'soccer', 'tennis')

    Returns:
        'free', 'pro', or 'unavailable'
    """
    _initialize_policy()

    if not _policy_cache:
        logger.warning("policy_cache_empty", provider=provider, category=category)
        return "unavailable"

    try:
        provider_config = _policy_cache.get(provider, {})
        sports_config = provider_config.get("sports", {})

        # Normalize category for comparison
        normalized_category = category.strip().title()

        # Check free tier
        free_sports = sports_config.get("free", [])
        if normalized_category in free_sports:
            logger.debug("policy_applied", provider=provider, category=category, visibility="free")
            return "free"

        # Check pro tier
        pro_sports = sports_config.get("pro", [])
        if normalized_category in pro_sports:
            logger.debug("policy_applied", provider=provider, category=category, visibility="pro")
            return "pro"

        # Not found in any tier
        logger.warning("unavailable_detected", provider=provider, category=category, type="category")
        return "unavailable"

    except Exception as e:
        logger.error("policy_lookup_error", provider=provider, category=category, error=str(e))
        return "unavailable"


def get_visibility_for_competition(provider: str, provider_key: str) -> PlanVisibility:
    """
    Get plan visibility for a competition.

    Args:
        provider: Provider name (e.g., 'odds_api')
        provider_key: Competition provider key (e.g., 'soccer_uefa_champs_league')

    Returns:
        'free', 'pro', or 'unavailable'
    """
    _initialize_policy()

    if not _policy_cache:
        logger.warning("policy_cache_empty", provider=provider, provider_key=provider_key)
        return "unavailable"

    try:
        provider_config = _policy_cache.get(provider, {})
        competitions_config = provider_config.get("competitions", {})

        # Normalize provider_key for comparison
        normalized_key = provider_key.strip().lower()

        # Check free tier
        free_competitions = competitions_config.get("free", [])
        if normalized_key in free_competitions:
            logger.debug("policy_applied", provider=provider, provider_key=provider_key, visibility="free")
            return "free"

        # Check pro tier
        pro_competitions = competitions_config.get("pro", [])
        if normalized_key in pro_competitions:
            logger.debug("policy_applied", provider=provider, provider_key=provider_key, visibility="pro")
            return "pro"

        # Not found in any tier
        logger.warning("unavailable_detected", provider=provider, provider_key=provider_key, type="competition")
        return "unavailable"

    except Exception as e:
        logger.error("policy_lookup_error", provider=provider, provider_key=provider_key, error=str(e))
        return "unavailable"


def get_competitions_whitelist(provider: str, plan: Literal["free", "pro", "all"] = "all") -> list[str]:
    """
    Get competition provider_keys from policy based on plan filter.

    Args:
        provider: Provider name (e.g., 'odds_api')
        plan: Plan filter - 'free' (only free), 'pro' (free + pro), 'all' (free + pro)

    Returns:
        List of provider_keys sorted deterministically
    """
    _initialize_policy()

    if not _policy_cache:
        logger.warning("policy_cache_empty_whitelist", provider=provider, plan=plan)
        return []

    try:
        provider_config = _policy_cache.get(provider, {})
        competitions_config = provider_config.get("competitions", {})

        free_competitions = competitions_config.get("free", [])
        pro_competitions = competitions_config.get("pro", [])

        # Build whitelist based on plan
        if plan == "free":
            whitelist = set(free_competitions)
        elif plan == "pro" or plan == "all":
            whitelist = set(free_competitions) | set(pro_competitions)
        else:
            whitelist = set()

        # Normalize and sort deterministically
        result = sorted([key.strip().lower() for key in whitelist])
        logger.info("competitions_whitelist_loaded", provider=provider, plan=plan, count=len(result))
        return result

    except Exception as e:
        logger.error("competitions_whitelist_error", provider=provider, plan=plan, error=str(e))
        return []


def get_batch_size_competitions(provider: str, default: int = 10) -> int:
    """
    Get batch size for competitions from policy.

    Args:
        provider: Provider name (e.g., 'odds_api')
        default: Default batch size if not found in policy

    Returns:
        Batch size for competitions processing
    """
    _initialize_policy()

    if not _policy_cache:
        return default

    try:
        provider_config = _policy_cache.get(provider, {})
        events_window = provider_config.get("events_window", {})
        batch_size = events_window.get("batch_size_competitions", default)
        return int(batch_size)
    except Exception as e:
        logger.error("batch_size_lookup_error", provider=provider, error=str(e))
        return default


def get_events_policy(provider: str) -> Dict:
    """
    Get events collection policy configuration.

    Args:
        provider: Provider name (e.g., 'odds_api')

    Returns:
        Dictionary with events policy configuration
    """
    _initialize_policy()

    if not _policy_cache:
        logger.warning("policy_cache_empty_events_policy", provider=provider)
        return {}

    try:
        provider_config = _policy_cache.get(provider, {})
        events_window = provider_config.get("events_window", {})
        rate_limit = events_window.get("rate_limit", {})
        retry_policy = events_window.get("retry_policy", {})

        policy = {
            "period": events_window.get("period", 30),
            "batch_size_competitions": events_window.get("batch_size_competitions", 10),
            "delay_between_competitions_sec": rate_limit.get("delay_between_competitions_sec", 10),
            "max_concurrency": rate_limit.get("max_concurrency", 1),
            "retriable_statuses": retry_policy.get("retriable_statuses", [429, 500, 502, 503, 504]),
            "max_attempts": retry_policy.get("max_attempts", 3),
            "base_delay_sec": retry_policy.get("base_delay_sec", 2),
            "max_delay_sec": retry_policy.get("max_delay_sec", 10),
            "jitter": retry_policy.get("jitter", True),
        }

        logger.debug("events_policy_loaded", provider=provider)
        return policy

    except Exception as e:
        logger.error("events_policy_lookup_error", provider=provider, error=str(e))
        return {}


def get_events_window_period(provider: str, default: int = 30) -> int:
    """
    Get events window period in days from policy.

    Args:
        provider: Provider name (e.g., 'odds_api')
        default: Default period if not found in policy

    Returns:
        Period in days for events window
    """
    _initialize_policy()

    if not _policy_cache:
        logger.warning("policy_cache_empty_period", provider=provider, default=default)
        return default

    try:
        provider_config = _policy_cache.get(provider, {})
        events_window = provider_config.get("events_window", {})
        period = events_window.get("period", default)
        return int(period)
    except Exception as e:
        logger.error("period_lookup_error", provider=provider, error=str(e))
        return default
