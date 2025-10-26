import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from app.domain.utils.time_utils import now_utc, parse_utc
from app.infra.repositories import (
    TeamRepository,
    EventRepository,
    BookmakerRepository,
    OddsSnapshotRepository,
    NormalizedOddsRepository,
)

logger = structlog.get_logger()


class OddsNormalizer:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.team_repo = TeamRepository(session)
        self.event_repo = EventRepository(session)
        self.bookmaker_repo = BookmakerRepository(session)
        self.snapshot_repo = OddsSnapshotRepository(session)
        self.normalized_repo = NormalizedOddsRepository(session)

    @staticmethod
    def normalize_team_name(name: str) -> str:
        normalized = name.lower().strip()
        normalized = re.sub(r"[^\w\s]", "", normalized)
        normalized = re.sub(r"\s+", "_", normalized)
        return normalized

    def calculate_odds_stats(
        self, outcomes: List[Dict[str, Any]]
    ) -> Tuple[float, float, Optional[float], float, float, Optional[float], int, datetime]:
        home_odds: List[float] = []
        away_odds: List[float] = []
        draw_odds: List[float] = []
        latest_timestamp = now_utc()

        for outcome in outcomes:
            name = outcome.get("name", "").lower()
            price = float(outcome.get("price", 0))

            if "draw" in name or name == "draw":
                draw_odds.append(price)
            elif len(home_odds) == 0:
                home_odds.append(price)
            else:
                away_odds.append(price)

        home_avg = sum(home_odds) / len(home_odds) if home_odds else 0.0
        away_avg = sum(away_odds) / len(away_odds) if away_odds else 0.0
        draw_avg = sum(draw_odds) / len(draw_odds) if draw_odds else None

        home_best = max(home_odds) if home_odds else 0.0
        away_best = max(away_odds) if away_odds else 0.0
        draw_best = max(draw_odds) if draw_odds else None

        bookmakers_count = len(outcomes) // 2 if len(outcomes) >= 2 else 1

        return (
            home_avg,
            away_avg,
            draw_avg,
            home_best,
            away_best,
            draw_best,
            bookmakers_count,
            latest_timestamp,
        )

    async def process_event_data(
        self, event_data: Dict[str, Any], sport_id: UUID, competition_id: UUID
    ) -> Optional[UUID]:
        try:
            external_id = event_data.get("id")
            home_team_name = event_data.get("home_team")
            away_team_name = event_data.get("away_team")
            commence_time_str = event_data.get("commence_time")

            if not all([external_id, home_team_name, away_team_name, commence_time_str]):
                logger.warning("missing_event_data", external_id=external_id)
                return None

            commence_time = parse_utc(commence_time_str)

            home_team_id = await self.team_repo.get_or_create(
                name=home_team_name,
                normalized_name=self.normalize_team_name(home_team_name),
                sport_id=sport_id,
                external_ids={"odds_api": external_id},
            )

            away_team_id = await self.team_repo.get_or_create(
                name=away_team_name,
                normalized_name=self.normalize_team_name(away_team_name),
                sport_id=sport_id,
                external_ids={"odds_api": external_id},
            )

            event_id = await self.event_repo.create_or_update(
                external_id=external_id,
                sport_id=sport_id,
                competition_id=competition_id,
                home_team_id=home_team_id,
                away_team_id=away_team_id,
                commence_time=commence_time,
                status="upcoming",
                event_metadata={"sport_key": event_data.get("sport_key")},
            )

            timestamp_ingested = now_utc()

            bookmakers = event_data.get("bookmakers", [])
            all_outcomes: List[Dict[str, Any]] = []

            for bookmaker_data in bookmakers:
                bookmaker_key = bookmaker_data.get("key")
                bookmaker_name = bookmaker_data.get("title")

                if not bookmaker_key or not bookmaker_name:
                    continue

                bookmaker_id = await self.bookmaker_repo.get_or_create(
                    key=bookmaker_key,
                    name=bookmaker_name,
                    region="eu",
                )

                markets = bookmaker_data.get("markets", [])
                for market in markets:
                    market_type = market.get("key")
                    outcomes = market.get("outcomes", [])

                    if not market_type or not outcomes:
                        continue

                    last_update_str = market.get("last_update")
                    last_update = (
                        parse_utc(last_update_str)
                        if last_update_str
                        else now_utc()
                    )

                    await self.snapshot_repo.create_snapshot(
                        event_id=event_id,
                        bookmaker_id=bookmaker_id,
                        market_type=market_type,
                        outcomes={"outcomes": outcomes},
                        timestamp_source=last_update,
                    )

                    if market_type == "h2h":
                        all_outcomes.extend(outcomes)

            if all_outcomes:
                (
                    home_avg,
                    away_avg,
                    draw_avg,
                    home_best,
                    away_best,
                    draw_best,
                    bookmakers_count,
                    timestamp_source,
                ) = self.calculate_odds_stats(all_outcomes)

                await self.normalized_repo.create_normalized(
                    event_id=event_id,
                    market_type="h2h",
                    home_odds_avg=home_avg,
                    away_odds_avg=away_avg,
                    draw_odds_avg=draw_avg,
                    home_odds_best=home_best,
                    away_odds_best=away_best,
                    draw_odds_best=draw_best,
                    bookmakers_count=bookmakers_count,
                    timestamp_source=timestamp_source,
                    timestamp_ingested=timestamp_ingested,
                )

            logger.info("processed_event", event_id=str(event_id), external_id=external_id)
            return event_id

        except Exception as e:
            logger.error("error_processing_event", error=str(e), external_id=external_id)
            return None
