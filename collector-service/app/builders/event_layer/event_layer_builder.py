"""
Builder for building event layer features
"""
from uuid import UUID

from app.domain.entities.event_layer.dto import EventLayerBuildInputDTO, MarketOddsDTO, UpcomingEventDTO, \
    EventFeatureBundleDTO
from app.domain.entities.feature_layer.team_features_dto import ScopesInputFeaturesDTO
from app.domain.entities.models_layer.dto import ModelScopesDTO
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

    def build_input(
        self,
        fixtures: list[UpcomingFixtureDTO],
        odds_map: dict[UUID, NormalizedOddsDTO],
        scopes_features: ScopesInputFeaturesDTO,
        model_scopes: ModelScopesDTO,
    ) -> EventLayerBuildInputDTO:
        """Build event layer input from fixtures, odds, features, and model scopes.
        
        Args:
            fixtures: List of upcoming fixtures.
            odds_map: Dictionary mapping event_id to normalized odds.
            scopes_features: Input features for scopes (team, match, poisson).
            model_scopes: Model outputs (Elo and Poisson).
            
        Returns:
            EventLayerBuildInputDTO ready for bundle building.
        """
        # Build upcoming events list
        upcoming_events = self.build_upcoming_events(
            fixtures=fixtures,
            odds_map=odds_map,
        )
        
        # Extract feature maps from scopes_features
        team_features = scopes_features.team_features
        match_features = scopes_features.match_features
        poisson_features = scopes_features.poisson_features
        
        # Build final DTO
        return EventLayerBuildInputDTO(
            events=upcoming_events,
            team_features=team_features,
            match_features=match_features,
            poisson_features=poisson_features,
            model_outputs=model_scopes,
        )

    def build_bundles(
        self,
        data: EventLayerBuildInputDTO,
    ) -> list[EventFeatureBundleDTO]:
        """Build event feature bundles from input data.
        
        Args:
            data: Event layer build input containing events, features, and model outputs.
            
        Returns:
            List of event feature bundles in the same order as input events.
        """
        bundles: list[EventFeatureBundleDTO] = []
        
        for e in data.events:
            # Team features
            home_team = data.team_features[e.home_team_id]
            away_team = data.team_features[e.away_team_id]
            
            # Match history
            match_history_home = data.match_features[e.home_team_id]
            match_history_away = data.match_features[e.away_team_id]
            
            # Poisson L2 features
            poisson_event_features = data.poisson_features[e.event_id]
            
            # Model outputs (L3)
            elo_output = data.model_outputs.elo_outputs[e.event_id]
            poisson_output = data.model_outputs.poisson_outputs[e.event_id]
            
            # Market odds
            market_odds = e.market_odds
            
            # Time
            match_date = e.match_date
            
            bundle = EventFeatureBundleDTO(
                event_id=e.event_id,
                home_team=home_team,
                away_team=away_team,
                match_history_home=match_history_home,
                match_history_away=match_history_away,
                poisson_event_features=poisson_event_features,
                elo_output=elo_output,
                poisson_output=poisson_output,
                market_odds=market_odds,
                match_date=match_date,
            )
            bundles.append(bundle)
        
        return bundles