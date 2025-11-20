from pydantic import BaseModel


class OddsPolicyDTO(BaseModel):
    """DTO for odds_models policy configuration."""
    regions: list[str]
    markets: list[str]
    bookmakers: list[str]
    include_links: bool
    include_sids: bool
    include_bet_limits: bool
    include_rotation_numbers: bool
    max_events_per_request: int
    use_event_ids: bool = False

