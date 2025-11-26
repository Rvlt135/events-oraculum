"""
Service for building team features
"""
import structlog
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from typing import List
from uuid import UUID
from app.infrastructure.cache.catalog.catalog_cache_helper import CatalogCacheHelper
from app.infrastructure.repositories.standings import StandingsFootballRepository
from app.infrastructure.repositories.feature_layer.team_features import TeamFeaturesRepository
from app.domain.entities.feature_layer.team_features_dto import TeamFeaturesDTO
from app.domain.entities.statistics.dto.standings_dto import StandingMinimalDTO
from app.infrastructure.cache.catalog.standings import StandingsFootballCache
from app.infrastructure.cache.feature_layer.team_features import TeamFeaturesCache
from app.infrastructure.config.policy_loader import PolicyLoader
from app.infrastructure.db.orm.standings_football import StandingsFootball

logger = structlog.get_logger()


class TeamFeaturesBuilder:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        policy_loader: PolicyLoader,
        standings_cache: StandingsFootballCache,
        team_features_cache: TeamFeaturesCache,
        catalog_cache_helper: CatalogCacheHelper,
    ):
        self.session_factory = session_factory
        self.policy_loader = policy_loader
        self.standings_cache = standings_cache
        self.team_features_cache = team_features_cache
        self.catalog_cache_helper = catalog_cache_helper

    async def load_standings_rows(self, competition_id: UUID, season: int) -> List[StandingMinimalDTO]:
        """Load standings rows and convert to minimal DTO for feature generation."""
        async with self.session_factory() as session:
            repo = StandingsFootballRepository(session)
            orm_rows = await repo.get_by_competition(competition_id, season)
            
            return [
                StandingMinimalDTO(
                    team_id=row.team_id,
                    rank=row.rank,
                    points=row.points,
                    goal_diff=row.goal_diff,
                    all_played=row.all_played,
                    all_goals_for=row.all_goals_for,
                    all_goals_against=row.all_goals_against,
                    form_raw=row.form_raw,
                )
                for row in orm_rows
            ]

    def _normalize_strength(self, rank: int | None, points: int | None) -> float:
        """Normalize rank and points to strength value."""
        if rank is None or points is None:
            return 0.0
        return float(points) / max(rank, 1)

    def _form_to_score(self, form_raw: str | None) -> float:
        """Parse form string to numeric score."""
        if not form_raw:
            return 0.0
        wins = form_raw.count('W')
        draws = form_raw.count('D')
        return float(wins * 3 + draws) / max(len(form_raw), 1)

    async def features_from_standings(
        self, 
        rows: List[StandingMinimalDTO], 
        competition_id: UUID, 
        season: int
    ) -> list[TeamFeaturesDTO]:
        """Build team features from standings data."""
        features = []
        
        for row in rows:
            strength_initial = self._normalize_strength(row.rank, row.points)
            form_score = self._form_to_score(row.form_raw)
            
            all_played = row.all_played or 0
            goals_for_avg = (row.all_goals_for / all_played) if all_played > 0 else 0.0
            goals_against_avg = (row.all_goals_against / all_played) if all_played > 0 else 0.0
            goal_diff = row.goal_diff or 0
            
            feature = TeamFeaturesDTO(
                team_id=row.team_id,
                competition_id=competition_id,
                season=season,
                strength_initial=strength_initial,
                form_score=form_score,
                goals_for_avg=goals_for_avg,
                goals_against_avg=goals_against_avg,
                goal_diff=goal_diff,
                games_played=all_played,
            )
            features.append(feature)
        
        return features

    async def save_team_features(
        self,
        team_features: list[TeamFeaturesDTO],
        competition_id: UUID,
        season: int
    ) -> int:
        """Save team features to database and cache."""
        async with self.session_factory() as session:
            repo = TeamFeaturesRepository(session)
            count = await repo.bulk_upsert_team_features(team_features)
            await session.commit()
        
        await self.team_features_cache.save_team_features(team_features)
        return count