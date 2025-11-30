"""
Builder for building event layer features
"""
from uuid import UUID

from app.domain.entities.event_layer.dto import MarketOddsDTO, UpcomingEventDTO
from app.domain.entities.odds_models.odds import NormalizedOddsDTO
from app.domain.entities.statistics.dto.fixtures_dto import UpcomingFixtureDTO


class EventLayerBuilder:
    """Builder for event layer features for football fixtures."""

    def __init__(self):
        pass

    def build_upcoming_events(
        self,
        fixtures: list[UpcomingFixtureDTO],
        odds_map: dict[UUID, NormalizedOddsDTO],
    ) -> list[UpcomingEventDTO]:
        """Build upcoming events with market odds from fixtures and normalized odds.
        
        Args:
            fixtures: List of upcoming fixtures.
            odds_map: Dictionary mapping event_id to normalized odds.
            
        Returns:
            List of upcoming events with market odds. Events without odds are skipped.
        """
        results: list[UpcomingEventDTO] = []
        
        for fixture in fixtures:
            if fixture.event_id not in odds_map:
                continue
            
            odds = odds_map[fixture.event_id]
            
            # Convert Decimal to float for MarketOddsDTO
            market_odds = MarketOddsDTO(
                market_type=odds.market_type,
                home_avg=float(odds.home_odds_avg),
                away_avg=float(odds.away_odds_avg),
                draw_avg=float(odds.draw_odds_avg) if odds.draw_odds_avg is not None else None,
                home_best=float(odds.home_odds_best),
                away_best=float(odds.away_odds_best),
                draw_best=float(odds.draw_odds_best) if odds.draw_odds_best is not None else None,
                bookmakers_count=odds.bookmakers_count
                # timestamp_source=odds.timestamp_source,
                # timestamp_ingested=odds.timestamp_ingested,
                # timestamp_normalized=odds.timestamp_normalized,
            )
            
            event = UpcomingEventDTO(
                event_id=fixture.event_id,
                home_team_id=fixture.home_team_id,
                away_team_id=fixture.away_team_id,
                match_date=fixture.match_date,
                competition_id=fixture.competition_id,
                season=fixture.season,
                market_odds=market_odds,
            )
            
            results.append(event)
        
        return results