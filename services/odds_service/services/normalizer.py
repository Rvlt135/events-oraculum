import re
from datetime import datetime
from typing import Any
from uuid import UUID

from services.odds_service.repositories import EventsRepository


class OddsNormalizer:
    def __init__(self, repository: EventsRepository) -> None:
        self.repository = repository

    @staticmethod
    def normalize_team_name(name: str) -> str:
        normalized = name.lower().strip()
        normalized = re.sub(r"[^\w\s]", "", normalized)
        normalized = re.sub(r"\s+", "_", normalized)
        return normalized

    def calculate_odds_stats(
        self, outcomes: list[dict[str, Any]]
    ) -> tuple[float, float, float | None, float, float, float | None, int]:
        home_odds: list[float] = []
        away_odds: list[float] = []
        draw_odds: list[float] = []

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

        bookmakers_count = len(set([o.get("bookmaker") for o in outcomes if o.get("bookmaker")]))

        return (
            home_avg,
            away_avg,
            draw_avg,
            home_best,
            away_best,
            draw_best,
            bookmakers_count,
        )

    async def process_event_data(
        self, event_data: dict[str, Any], sport_id: UUID, league_id: UUID
    ) -> UUID | None:
        try:
            external_id = event_data.get("id")
            home_team_name = event_data.get("home_team")
            away_team_name = event_data.get("away_team")
            commence_time_str = event_data.get("commence_time")

            if not all([external_id, home_team_name, away_team_name, commence_time_str]):
                return None

            commence_time = datetime.fromisoformat(commence_time_str.replace("Z", "+00:00"))

            home_team_id = await self.repository.get_or_create_team(
                name=home_team_name,
                normalized_name=self.normalize_team_name(home_team_name),
                sport_id=sport_id,
                external_ids={"odds_api": external_id},
            )

            away_team_id = await self.repository.get_or_create_team(
                name=away_team_name,
                normalized_name=self.normalize_team_name(away_team_name),
                sport_id=sport_id,
                external_ids={"odds_api": external_id},
            )

            event_id = await self.repository.create_or_update_event(
                external_id=external_id,
                sport_id=sport_id,
                league_id=league_id,
                home_team_id=home_team_id,
                away_team_id=away_team_id,
                commence_time=commence_time,
                status="upcoming",
                metadata={"sport_key": event_data.get("sport_key")},
            )

            bookmakers = event_data.get("bookmakers", [])
            for bookmaker_data in bookmakers:
                bookmaker_key = bookmaker_data.get("key")
                bookmaker_name = bookmaker_data.get("title")

                if not bookmaker_key or not bookmaker_name:
                    continue

                bookmaker_id = await self.repository.get_or_create_bookmaker(
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
                        datetime.fromisoformat(last_update_str.replace("Z", "+00:00"))
                        if last_update_str
                        else datetime.utcnow()
                    )

                    await self.repository.create_odds_snapshot(
                        event_id=event_id,
                        bookmaker_id=bookmaker_id,
                        market_type=market_type,
                        outcomes={"outcomes": outcomes},
                        timestamp_source=last_update,
                    )

                    if market_type == "h2h":
                        (
                            home_avg,
                            away_avg,
                            draw_avg,
                            home_best,
                            away_best,
                            draw_best,
                            bookmakers_count,
                        ) = self.calculate_odds_stats(outcomes)

                        await self.repository.create_normalized_odds(
                            event_id=event_id,
                            market_type=market_type,
                            home_odds_avg=home_avg,
                            away_odds_avg=away_avg,
                            draw_odds_avg=draw_avg,
                            home_odds_best=home_best,
                            away_odds_best=away_best,
                            draw_odds_best=draw_best,
                            bookmakers_count=bookmakers_count,
                        )

            return event_id

        except Exception as e:
            print(f"Error processing event data: {e}")
            return None
