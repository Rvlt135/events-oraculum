from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from app.domain.orm_models import Sport, League, Team, Event, Bookmaker, OddsSnapshot, NormalizedOdds

logger = structlog.get_logger()


class OddsRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_or_create_sport(self, name: str, display_name: str) -> UUID:
        result = await self.session.execute(
            select(Sport).where(Sport.name == name)
        )
        sport = result.scalar_one_or_none()

        if not sport:
            sport = Sport(name=name, display_name=display_name, is_active=True)
            self.session.add(sport)
            await self.session.flush()
            logger.info("sport_created", name=name)

        return sport.id

    async def get_or_create_league(
        self, sport_id: UUID, key: str, name: str, region: str
    ) -> UUID:
        result = await self.session.execute(
            select(League).where(League.key == key)
        )
        league = result.scalar_one_or_none()

        if not league:
            league = League(
                sport_id=sport_id,
                key=key,
                name=name,
                region=region,
                is_active=True
            )
            self.session.add(league)
            await self.session.flush()
            logger.info("league_created", key=key, name=name)
        else:
            league.name = name
            await self.session.flush()

        return league.id

    async def get_or_create_team(
        self, name: str, normalized_name: str, sport_id: UUID, external_ids: Dict[str, Any]
    ) -> UUID:
        result = await self.session.execute(
            select(Team).where(Team.normalized_name == normalized_name)
        )
        team = result.scalar_one_or_none()

        if not team:
            team = Team(
                name=name,
                normalized_name=normalized_name,
                sport_id=sport_id,
                external_ids=external_ids
            )
            self.session.add(team)
            await self.session.flush()
            logger.info("team_created", name=name)
        else:
            team.name = name
            team.external_ids = external_ids
            team.updated_at = datetime.utcnow()
            await self.session.flush()

        return team.id

    async def get_or_create_bookmaker(self, key: str, name: str, region: str) -> UUID:
        result = await self.session.execute(
            select(Bookmaker).where(Bookmaker.key == key)
        )
        bookmaker = result.scalar_one_or_none()

        if not bookmaker:
            bookmaker = Bookmaker(
                key=key,
                name=name,
                region=region,
                is_active=True
            )
            self.session.add(bookmaker)
            await self.session.flush()
            logger.info("bookmaker_created", key=key)
        else:
            bookmaker.name = name
            await self.session.flush()

        return bookmaker.id

    async def create_or_update_event(
        self,
        external_id: str,
        sport_id: UUID,
        league_id: UUID,
        home_team_id: UUID,
        away_team_id: UUID,
        commence_time: datetime,
        status: str,
        metadata: Dict[str, Any],
    ) -> UUID:
        result = await self.session.execute(
            select(Event).where(Event.external_id == external_id)
        )
        event = result.scalar_one_or_none()

        if not event:
            event = Event(
                external_id=external_id,
                sport_id=sport_id,
                league_id=league_id,
                home_team_id=home_team_id,
                away_team_id=away_team_id,
                commence_time=commence_time,
                status=status,
                metadata=metadata
            )
            self.session.add(event)
            await self.session.flush()
            logger.info("event_created", external_id=external_id)
        else:
            event.commence_time = commence_time
            event.status = status
            event.metadata = metadata
            event.updated_at = datetime.utcnow()
            await self.session.flush()
            logger.info("event_updated", external_id=external_id)

        return event.id

    async def create_odds_snapshot(
        self,
        event_id: UUID,
        bookmaker_id: UUID,
        market_type: str,
        outcomes: Dict[str, Any],
        timestamp_source: datetime,
    ) -> UUID:
        snapshot = OddsSnapshot(
            event_id=event_id,
            bookmaker_id=bookmaker_id,
            market_type=market_type,
            outcomes=outcomes,
            timestamp_source=timestamp_source,
            timestamp_ingested=datetime.utcnow()
        )
        self.session.add(snapshot)
        await self.session.flush()

        return snapshot.id

    async def create_normalized_odds(
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
        normalized = NormalizedOdds(
            event_id=event_id,
            market_type=market_type,
            home_odds_avg=home_odds_avg,
            away_odds_avg=away_odds_avg,
            draw_odds_avg=draw_odds_avg,
            home_odds_best=home_odds_best,
            away_odds_best=away_odds_best,
            draw_odds_best=draw_odds_best,
            bookmakers_count=bookmakers_count,
            timestamp_source=timestamp_source,
            timestamp_ingested=timestamp_ingested,
            timestamp_normalized=datetime.utcnow()
        )
        self.session.add(normalized)
        await self.session.flush()

        return normalized.id

    async def commit(self) -> None:
        await self.session.commit()
