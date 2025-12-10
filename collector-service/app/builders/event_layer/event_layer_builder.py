"""
Builder for building event layer features
"""
import json
from uuid import UUID

import structlog

from app.domain.entities.event_layer.dto import EventLayerBuildInputDTO, MarketOddsDTO, UpcomingEventDTO, \
    EventFeatureBundleDTO, EventEdgeDTO, ValueCandidateDTO
from app.domain.entities.feature_layer.team_features_dto import ScopesInputFeaturesDTO
from app.domain.entities.models_layer.dto import ModelScopesDTO
from app.domain.entities.odds_models.odds import NormalizedOddsDTO
from app.domain.entities.statistics.dto.fixtures_dto import UpcomingFixtureDTO
from app.infrastructure.db.orm.event_leayer.event_feature_bundle import EventFeatureBundleORM

logger = structlog.get_logger()


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
            
            # Poisson L2 features (raw from F3 - contains lambda values)
            poisson_event_features = data.poisson_features[e.event_id]
            
            # Model outputs (L3 - probabilities and fair odds only, no lambda)
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

    def parse_bundle(
        self,
        raw_json: dict | str | bytes | None,
    ) -> EventFeatureBundleDTO | None:
        """Parse raw JSON data into EventFeatureBundleDTO.
        
        Args:
            raw_json: Raw data as dict, JSON string, bytes, or None.
            
        Returns:
            EventFeatureBundleDTO if parsing succeeds, None otherwise.
        """
        logger.debug("parse_bundle_called", raw_json_type=type(raw_json).__name__)
        
        if raw_json is None:
            return None
        
        try:
            # Convert to dict based on input type
            if isinstance(raw_json, bytes):
                bundle_dict: dict = json.loads(raw_json.decode("utf-8"))
            elif isinstance(raw_json, str):
                bundle_dict: dict = json.loads(raw_json)
            elif isinstance(raw_json, dict):
                bundle_dict: dict = raw_json
            else:
                logger.debug("parse_bundle_failed", error=f"Unsupported type: {type(raw_json).__name__}")
                return None
            
            # Validate and create DTO (EventFeatureBundleDTO handles event_id and extra fields itself)
            bundle = EventFeatureBundleDTO.model_validate(bundle_dict)
            
            logger.debug("parse_bundle_success", event_id=str(bundle.event_id))
            return bundle
            
        except Exception as e:
            logger.debug("parse_bundle_failed", error=str(e))
            return None

    def parse_bundles(
        self,
        items: list[EventFeatureBundleORM],
    ) -> dict[UUID, EventFeatureBundleDTO]:
        """Parse multiple event feature bundles from ORM objects.
        
        Args:
            items: List of EventFeatureBundleORM instances to parse.
            
        Returns:
            Dictionary mapping event_id to EventFeatureBundleDTO (successfully parsed only).
        """
        if not items:
            return {}
        
        logger.debug("parse_bundles_called", items_count=len(items))
        
        result: dict[UUID, EventFeatureBundleDTO] = {}
        for orm in items:
            dto = self.parse_bundle(orm.bundle_json)
            if dto is not None:
                result[orm.event_id] = dto
        
        logger.debug("parsed_bundles_completed", total=len(result))
        return result

    def compute_edges(self, bundles: dict[UUID, EventFeatureBundleDTO]) -> dict[UUID, EventEdgeDTO]:
        """Compute betting edges from event feature bundles.
        
        Args:
            bundles: Dictionary mapping event_id to EventFeatureBundleDTO.
            
        Returns:
            Dictionary mapping event_id to EventEdgeDTO containing fair odds, edges, and value candidates.
        """
        if not bundles:
            return {}
        
        logger.debug("compute_edges_called", bundles_count=len(bundles))
        
        result: dict[UUID, EventEdgeDTO] = {}
        
        for bundle in bundles.values():
            # Compute fair odds from probabilities
            fair_home = 1.0 / bundle.elo_output.p_home
            fair_draw = 1.0 / bundle.elo_output.p_draw
            fair_away = 1.0 / bundle.elo_output.p_away
            
            # Compute edge percentages
            edge_home = (bundle.market_odds.home_best - fair_home) / fair_home
            edge_draw = (bundle.market_odds.draw_best - fair_draw) / fair_draw if bundle.market_odds.draw_best is not None else 0.0
            edge_away = (bundle.market_odds.away_best - fair_away) / fair_away
            
            # Build value candidates for each selection
            value_candidates: list[ValueCandidateDTO] = [
                ValueCandidateDTO(
                    selection="home",
                    fair_odds=fair_home,
                    market_odds=bundle.market_odds.home_best,
                    edge_percent=edge_home,
                ),
                ValueCandidateDTO(
                    selection="draw",
                    fair_odds=fair_draw,
                    market_odds=bundle.market_odds.draw_best if bundle.market_odds.draw_best is not None else 0.0,
                    edge_percent=edge_draw,
                ),
                ValueCandidateDTO(
                    selection="away",
                    fair_odds=fair_away,
                    market_odds=bundle.market_odds.away_best,
                    edge_percent=edge_away,
                ),
            ]
            
            # Build EventEdgeDTO
            edge = EventEdgeDTO(
                event_id=bundle.event_id,
                fair_home=fair_home,
                fair_draw=fair_draw,
                fair_away=fair_away,
                edge_home=edge_home,
                edge_draw=edge_draw,
                edge_away=edge_away,
                value_candidates=value_candidates,
            )
            
            result[bundle.event_id] = edge
            logger.debug("edge_computed", event_id=str(bundle.event_id), edge_count=len(value_candidates))
        
        logger.debug("compute_edges_completed", total_edges=len(result))
        return result