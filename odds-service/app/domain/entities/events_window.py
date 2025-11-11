"""
Domain entities for events collection window and policy.
"""
from typing import Literal, Dict, Optional
from pydantic import BaseModel


class EventsPolicyDTO(BaseModel):
    """DTO for events collection policy configuration."""
    # Provider info
    provider: str
    
    # Competitions
    competitions: Dict[str, list[str]]  # {"free": [...], "pro": [...]}
    
    # Events window configuration
    period: int
    batch_size_competitions: int
    delay_between_competitions_sec: int
    max_concurrency: int
    retriable_statuses: list[int]
    max_attempts: int
    base_delay_sec: int
    max_delay_sec: int
    jitter: bool
    
    # Events configuration
    teams_normalization_enabled: bool
    
    # Admin configuration
    events_view_limit: int = 200
    
    # Cache configuration
    events_cache_upcoming_ttl_sec: int = 300


class EventsWindowDTO(BaseModel):
    """DTO for events collection time window."""
    from_iso: str
    to_iso: str
    period_days: int


class EventKeyResultDTO(BaseModel):
    """DTO for single competition key result."""
    provider_key: str
    status: Literal["success", "failed", "skipped"]
    attempts: int
    duration_ms: int
    events_count: int
    error: str | None = None


class EventsRunSummaryDTO(BaseModel):
    """DTO for events collection run summary."""
    processed: int
    failed: int
    skipped: int
    total_events: int
    per_key: Dict[str, EventKeyResultDTO]
