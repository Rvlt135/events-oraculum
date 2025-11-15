from datetime import datetime
from decimal import Decimal
from typing import Optional, List, Dict, Any
from uuid import UUID
from sqlalchemy import select, and_
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import aliased
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from app.infrastructure.db.orm.odds import NormalizedOdds
from app.domain.entities.odds import NormalizedOddsDTO
from app.infrastructure.db.orm.events import Event
from app.infrastructure.db.orm.competition import Competition
from app.infrastructure.db.orm.teams import Team
from app.utils.time_utils import now_utc
from app.infrastructure.repositories.base import BaseRepository

logger = structlog.get_logger()


class NormalizedOddsRepository(BaseRepository[NormalizedOdds]):
    def __init__(self, session: AsyncSession):
        super().__init__(NormalizedOdds, session)

    async def upsert_normalized(self, dto: NormalizedOddsDTO) -> UUID:
        """
        Upsert normalized odds by key (event_id, market_type).

        Key: (event_id, market_type) - unique constraint.

        Behavior:
        - If record exists: UPDATE all calculated fields (avg/best, bookmakers_count, timestamps)
        - If not exists: INSERT new record
        - created_at is preserved on update (not touched)

        Args:
            dto: NormalizedOddsDTO (id and created_at can be None for new records)

        Returns:
            UUID of normalized odds (existing or newly created)
        """
        stmt = (
            insert(NormalizedOdds)
            .values(
                event_id=dto.event_id,
                market_type=dto.market_type,
                home_odds_avg=dto.home_odds_avg,
                away_odds_avg=dto.away_odds_avg,
                draw_odds_avg=dto.draw_odds_avg,
                home_odds_best=dto.home_odds_best,
                away_odds_best=dto.away_odds_best,
                draw_odds_best=dto.draw_odds_best,
                bookmakers_count=dto.bookmakers_count,
                timestamp_source=dto.timestamp_source,
                timestamp_ingested=dto.timestamp_ingested,
                timestamp_normalized=dto.timestamp_normalized,
            )
            .on_conflict_do_update(
                index_elements=["event_id", "market_type"],
                set_=dict(
                    home_odds_avg=dto.home_odds_avg,
                    away_odds_avg=dto.away_odds_avg,
                    draw_odds_avg=dto.draw_odds_avg,
                    home_odds_best=dto.home_odds_best,
                    away_odds_best=dto.away_odds_best,
                    draw_odds_best=dto.draw_odds_best,
                    bookmakers_count=dto.bookmakers_count,
                    timestamp_source=dto.timestamp_source,
                    timestamp_ingested=dto.timestamp_ingested,
                    timestamp_normalized=dto.timestamp_normalized,
                )
            )
            .returning(NormalizedOdds.id)
        )

        result = await self.session.execute(stmt)
        normalized_id = result.scalar_one()
        await self.session.flush()

        logger.debug(
            "normalized_odds_upserted",
            event_id=str(dto.event_id),
            market_type=dto.market_type,
            normalized_id=str(normalized_id)
        )

        return normalized_id

    async def create_normalized(
        self,
        event_id: UUID,
        market_type: str,
        home_odds_avg: float,
        away_odds_avg: float,
        draw_odds_avg: Optional[float],
        home_odds_best: float,
        away_odds_best: float,
        draw_odds_best: Optional[float],
        bookmakers_count: int,
        timestamp_source: datetime,
        timestamp_ingested: datetime,
    ) -> UUID:
        """Deprecated: Use upsert_normalized with NormalizedOddsDTO instead."""
        dto = NormalizedOddsDTO(
            id=None,
            event_id=event_id,
            market_type=market_type,
            home_odds_avg=Decimal(str(home_odds_avg)),
            away_odds_avg=Decimal(str(away_odds_avg)),
            draw_odds_avg=Decimal(str(draw_odds_avg)) if draw_odds_avg is not None else None,
            home_odds_best=Decimal(str(home_odds_best)),
            away_odds_best=Decimal(str(away_odds_best)),
            draw_odds_best=Decimal(str(draw_odds_best)) if draw_odds_best is not None else None,
            bookmakers_count=bookmakers_count,
            timestamp_source=timestamp_source,
            timestamp_ingested=timestamp_ingested,
            timestamp_normalized=now_utc(),
            created_at=None,
        )
        return await self.upsert_normalized(dto)

    async def get_by_event(
        self,
        event_id: UUID,
        market_type: Optional[str] = None
    ) -> List[NormalizedOdds]:
        query = select(NormalizedOdds).where(NormalizedOdds.event_id == event_id)

        if market_type:
            query = query.where(NormalizedOdds.market_type == market_type)

        query = query.order_by(NormalizedOdds.timestamp_normalized.desc())

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_latest_by_event(
        self, event_id: UUID, market_type: str
    ) -> Optional[NormalizedOdds]:
        result = await self.session.execute(
            select(NormalizedOdds)
            .where(
                and_(
                    NormalizedOdds.event_id == event_id,
                    NormalizedOdds.market_type == market_type
                )
            )
            .order_by(NormalizedOdds.timestamp_normalized.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def get_normalized_snapshots(
        self, limit: int = 100, competition_key: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get normalized odds snapshots with related event, competition, and team data.
        
        Optimized query using SQLAlchemy 2.0 ORM with proper joins and aliases.
        """
        # Create aliases for home and away teams
        HomeTeam = aliased(Team)
        AwayTeam = aliased(Team)
        
        # Build query with joins
        query = (
            select(
                NormalizedOdds,
                Event.external_id,
                Competition.provider_key.label("competition_key"),
                HomeTeam.name.label("home_team"),
                AwayTeam.name.label("away_team"),
                Event.commence_time,
            )
            .join(Event, NormalizedOdds.event_id == Event.id)
            .join(Competition, Event.competition_id == Competition.id)
            .join(HomeTeam, Event.home_team_id == HomeTeam.id)
            .join(AwayTeam, Event.away_team_id == AwayTeam.id)
            .order_by(NormalizedOdds.timestamp_normalized.desc())
            .limit(limit)
        )
        
        # Add competition filter if provided
        if competition_key:
            query = query.where(Competition.provider_key == competition_key)
        
        result = await self.session.execute(query)
        rows = result.all()
        
        # Convert to dict format matching SnapshotSummary schema
        snapshots = []
        for row in rows:
            normalized = row[0]  # NormalizedOdds instance
            snapshot_dict = {
                "id": normalized.id,
                "event_id": normalized.event_id,
                "market_type": normalized.market_type,
                "home_odds_avg": float(normalized.home_odds_avg),
                "away_odds_avg": float(normalized.away_odds_avg),
                "draw_odds_avg": float(normalized.draw_odds_avg) if normalized.draw_odds_avg else None,
                "home_odds_best": float(normalized.home_odds_best),
                "away_odds_best": float(normalized.away_odds_best),
                "draw_odds_best": float(normalized.draw_odds_best) if normalized.draw_odds_best else None,
                "bookmakers_count": normalized.bookmakers_count,
                "timestamp_source": normalized.timestamp_source,
                "timestamp_ingested": normalized.timestamp_ingested,
                "timestamp_normalized": normalized.timestamp_normalized,
                "created_at": normalized.created_at,
                "external_id": row[1],  # Event.external_id
                "competition_key": row[2],  # Competition.provider_key
                "home_team": row[3],  # HomeTeam.name
                "away_team": row[4],  # AwayTeam.name
                "commence_time": row[5],  # Event.commence_time
            }
            snapshots.append(snapshot_dict)
        
        return snapshots
