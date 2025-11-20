"""
Policy loader for provider policy configuration.
Loads YAML configuration once at startup and caches in memory.
"""
from typing import Dict, Literal, Optional
from pathlib import Path
import yaml
import structlog
from pydantic import BaseModel

from app.domain.entities.events.events_window import EventsPolicyDTO
from app.domain.policy.dto import OddsPolicyDTO

logger = structlog.get_logger()

PlanVisibility = Literal["free", "pro", "unavailable"]


class LLMRetryDTO(BaseModel):
    """DTO for LLM retry configuration."""
    max_attempts: int
    base_delay_sec: int
    max_delay_sec: int
    special_delays: Dict[str, int] = {}  # status_code -> delay_sec
    retriable_status_codes: list[int]


class PrioritizerPolicyDTO(BaseModel):
    """DTO for prioritizer policy configuration."""
    enabled: bool = True
    mode: str = "all"
    max_events: int
    ttl_sec: int
    llm_retry: Optional[LLMRetryDTO] = None


class CompetitionsPlanDTO(BaseModel):
    """DTO for competitions plan configuration."""
    free: list[str] = []
    pro: list[str] = []


class PolicyLoader:
    """Policy loader with in-memory cache."""
    
    def __init__(self, path: str, load_sync: bool = False):
        """
        Initialize policy loader.
        
        Args:
            path: Path to provider_policy.yml file
            load_sync: If True, load policy synchronously on init
        """
        self._path = Path(path)
        self._cache: Optional[Dict] = None
        if load_sync:
            self._load_sync()
    
    def _load_sync(self) -> None:
        """Load policy from YAML file synchronously."""
        try:
            with open(self._path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
                self._cache = data or {}
                logger.info("policy_loaded_sync", path=str(self._path), providers=list(self._cache.keys()))
        except FileNotFoundError:
            logger.error("policy_file_not_found", path=str(self._path))
            self._cache = {}
        except yaml.YAMLError as e:
            logger.error("policy_yaml_parse_error", error=str(e))
            self._cache = {}
        except Exception as e:
            logger.error("policy_load_unexpected_error", error=str(e))
            self._cache = {}
    
    async def load(self) -> None:
        """
        Load policy from YAML file once at startup.
        
        Raises:
            FileNotFoundError: If policy file not found
            yaml.YAMLError: If YAML parsing fails
        """
        try:
            with open(self._path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
                self._cache = data or {}
                logger.info("policy_loaded", path=str(self._path), providers=list(self._cache.keys()))
        except FileNotFoundError:
            logger.error("policy_file_not_found", path=str(self._path))
            self._cache = {}
        except yaml.YAMLError as e:
            logger.error("policy_yaml_parse_error", error=str(e))
            self._cache = {}
        except Exception as e:
            logger.error("policy_load_unexpected_error", error=str(e))
            self._cache = {}
    
    def get_providers(self) -> list[str]:
        """Get list of all providers from policy."""
        if not self._cache:
            logger.warning("policy_cache_empty_providers")
            return []
        return list(self._cache.keys())
    
    def get_events_policy(self, provider: str) -> Optional[EventsPolicyDTO]:
        """Get events policy for provider as DTO."""
        if not self._cache:
            logger.warning("policy_cache_empty_events_policy", provider=provider)
            return None
        
        provider_config = self._cache.get(provider, {})
        if not provider_config:
            return None
        
        events_window = provider_config.get("events_window", {})
        rate_limit = events_window.get("rate_limit", {})
        retry_policy = events_window.get("retry_policy", {})
        competitions_config = provider_config.get("competitions", {})
        events_config = provider_config.get("events", {})
        admin_config = provider_config.get("admin", {})
        events_cache_config = provider_config.get("events_cache", {})
        
        teams_normalization_config = events_config.get("teams_normalization", {})
        teams_normalization_enabled = teams_normalization_config.get("enabled", False)
        
        return EventsPolicyDTO(
            provider=provider,
            competitions={
                "free": competitions_config.get("free", []),
                "pro": competitions_config.get("pro", []),
            },
            period=events_window.get("period", 30),
            batch_size_competitions=events_window.get("batch_size_competitions", 10),
            delay_between_competitions_sec=rate_limit.get("delay_between_competitions_sec", 10),
            max_concurrency=rate_limit.get("max_concurrency", 1),
            retriable_statuses=retry_policy.get("retriable_statuses", [429, 500, 502, 503, 504]),
            max_attempts=retry_policy.get("max_attempts", 3),
            base_delay_sec=retry_policy.get("base_delay_sec", 2),
            max_delay_sec=retry_policy.get("max_delay_sec", 10),
            jitter=retry_policy.get("jitter", True),
            teams_normalization_enabled=teams_normalization_enabled,
            events_view_limit=admin_config.get("events_view_limit", 200),
            events_cache_upcoming_ttl_sec=events_cache_config.get("upcoming_ttl_sec", 300),
        )
    
    def get_prioritizer_policy(self, provider: str) -> Optional[PrioritizerPolicyDTO]:
        """Get prioritizer policy for provider as DTO."""
        if not self._cache:
            return None
        
        provider_config = self._cache.get(provider, {})
        prioritizer_config = provider_config.get("prioritizer", {})
        if not prioritizer_config:
            return None
        
        # Parse llm_retry if present
        llm_retry_config = prioritizer_config.get("llm_retry")
        llm_retry = None
        if llm_retry_config:
            llm_retry = LLMRetryDTO(**llm_retry_config)
        
        # Build DTO with llm_retry
        dto_data = {k: v for k, v in prioritizer_config.items() if k != "llm_retry"}
        dto_data["llm_retry"] = llm_retry
        return PrioritizerPolicyDTO(**dto_data)
    
    def get_odds_policy(self, provider: str) -> Optional[OddsPolicyDTO]:
        """Get odds_models policy for provider as DTO."""
        if not self._cache:
            return None
        
        provider_config = self._cache.get(provider, {})
        odds_config = provider_config.get("odds_models", {})
        if not odds_config:
            return None
        
        return OddsPolicyDTO(**odds_config)
    
    def get_competitions(self, provider: str) -> Optional[CompetitionsPlanDTO]:
        """Get competitions plan for provider as DTO."""
        if not self._cache:
            return None
        
        provider_config = self._cache.get(provider, {})
        competitions_config = provider_config.get("competitions", {})
        return CompetitionsPlanDTO(**competitions_config) if competitions_config else None
    
    def get_visibility_for_category(self, provider: str, category: str) -> PlanVisibility:
        """
        Get plan visibility for a sport category.
        
        Args:
            provider: Provider name (e.g., "odds_api")
            category: Sport category (e.g., "soccer")
            
        Returns:
            PlanVisibility: "free", "pro", or "unavailable"
        """
        # First check competitions config (newer approach)
        competitions = self.get_competitions(provider)
        if competitions:
            normalized_category = category.strip().title()
            if normalized_category in competitions.free:
                return "free"
            if normalized_category in competitions.pro:
                return "pro"
        
        # Fallback to sports config (legacy)
        if not self._cache:
            return "unavailable"
        provider_config = self._cache.get(provider, {})
        sports_config = provider_config.get("sports", {})
        normalized_category = category.strip().title()
        if normalized_category in sports_config.get("free", []):
            return "free"
        if normalized_category in sports_config.get("pro", []):
            return "pro"
        return "unavailable"
    
    def get_visibility_for_competition(self, provider: str, slug_key: str) -> PlanVisibility:
        """
        Get plan visibility for a competition by slug key.
        
        Args:
            provider: Provider name (e.g., "odds_api")
            slug_key: Competition slug key
            
        Returns:
            PlanVisibility: "free", "pro", or "unavailable"
        """
        competitions = self.get_competitions(provider)
        if competitions:
            normalized_key = slug_key.strip().lower()
            if normalized_key in competitions.free:
                return "free"
            if normalized_key in competitions.pro:
                return "pro"
        
        # Fallback to competitions config (legacy)
        if not self._cache:
            return "unavailable"
        provider_config = self._cache.get(provider, {})
        competitions_config = provider_config.get("competitions", {})
        normalized_key = slug_key.strip().lower()
        if normalized_key in competitions_config.get("free", []):
            return "free"
        if normalized_key in competitions_config.get("pro", []):
            return "pro"
        return "unavailable"
    
    def get_participant_mode_for_sport(self, provider: str, sport_key: str) -> str:
        """Get participant mode for a sport from policy."""
        if not self._cache:
            return "unknown"
        
        provider_config = self._cache.get(provider, {})
        participants_config = provider_config.get("participants", {})
        mode_by_sport = participants_config.get("participant_mode_by_sport", {})
        return mode_by_sport.get(sport_key.lower(), "unknown")
    
    def reload(self) -> None:
        """Reload policy from file (dev-only)."""
        self._cache = None
        import asyncio
        asyncio.run(self.load())
        logger.info("policy_reloaded", path=str(self._path))

