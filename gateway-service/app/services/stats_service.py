from datetime import datetime
from typing import Optional
import structlog

from app.db.repositories import RecommendationsReadRepo
from app.models.schemas import StatsDTO

logger = structlog.get_logger()


class StatsService:
    def __init__(self, recommendations_repo: RecommendationsReadRepo):
        self.recommendations_repo = recommendations_repo

    async def get_summary(
        self,
        league: Optional[str] = None,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
    ) -> StatsDTO:
        stats = await self.recommendations_repo.get_stats(
            league=league,
            from_date=from_date,
            to_date=to_date,
        )

        stats_dto = StatsDTO(
            count_recommendations=stats["count_recommendations"],
            baseline_count=stats["baseline_count"],
            distribution_by_pick=stats["distribution_by_pick"],
            latest_recommendation_ts=stats["latest_recommendation_ts"],
            period_from=from_date,
            period_to=to_date,
            league_key=league,
        )

        logger.info(
            "stats_summary_retrieved",
            count=stats_dto.count_recommendations,
            league=league,
        )

        return stats_dto
