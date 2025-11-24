from typing import Optional, List, Dict, Any
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from app.infrastructure.db.orm.standings_football import StandingsFootball
from app.utils.time_utils import now_utc
from app.infrastructure.repositories.base import BaseRepository
from sqlalchemy.dialects.postgresql import insert
from app.utils.text_utils import create_team_slug, normalize_name
from app.utils.text_utils import normalize_name

logger = structlog.get_logger()


class StandingsFootballRepository(BaseRepository[StandingsFootball]):
    def __init__(self, session: AsyncSession):
        super().__init__(StandingsFootball, session)

