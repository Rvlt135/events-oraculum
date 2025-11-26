from uuid import UUID

from pydantic import BaseModel


class MatchFeaturesDTO(BaseModel):
    team_id: UUID
    competition_id: UUID
    season: int

    last_matches_count: int          # сколько матчей вошло в расчёт (<= N)

    goals_for_last_n: int            # суммарные голы GF за последние N
    goals_against_last_n: int        # суммарные GA за последние N
    goals_diff_last_n: int           # GF - GA

    wins_last_n: int                 # количество W
    draws_last_n: int                # количество D
    losses_last_n: int               # количество L

    avg_goals_for_last_n: float      # goals_for_last_n / last_matches_count
    avg_goals_against_last_n: float  # goals_against_last_n / last_matches_count

    form_last_n: str                 # строка: "WDLWD"
