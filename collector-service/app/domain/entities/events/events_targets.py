"""
Domain entities for events collection targets.
"""
from typing import Literal, List
from pydantic import BaseModel


class FilteredReasonDTO(BaseModel):
    """DTO for filtered out competition with reason."""
    slug_key: str
    reason: Literal["not_found", "inactive"]


class EventsTargetsDTO(BaseModel):
    """DTO for events collection targets with batching."""
    provider: Literal["odds_api"]
    plan: Literal["free", "pro", "all"]
    total_in_policy: int
    total_valid: int
    filtered_out: List[FilteredReasonDTO]
    batches: List[List[str]]
