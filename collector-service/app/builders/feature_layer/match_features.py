"""
Builder for building match features
"""
from typing import List
from uuid import UUID

import structlog

from app.domain.entities.feature_layer.match_features_dto import MatchFeaturesDTO
from app.domain.entities.statistics.dto.fixtures_dto import FixtureHistoryRowDTO, LastFixtureDTO

logger = structlog.get_logger()


class MatchFeaturesBuilder:

    def _result_to_str(self, r: int) -> str:
        if r == 1:
            return "W"
        elif r == 0:
            return "D"
        else:
            return "L"

    def load_last_fixtures(self, rows: list[FixtureHistoryRowDTO], max_matches_per_team: int = 5) -> dict[UUID, list[LastFixtureDTO]]:
        """
        Group fixtures by team and return last N matches per team from team's perspective.
        """
        groups: dict[UUID, list[FixtureHistoryRowDTO]] = {}
        
        for row in rows:
            if row.home_team_id not in groups:
                groups[row.home_team_id] = []
            if row.away_team_id not in groups:
                groups[row.away_team_id] = []
            groups[row.home_team_id].append(row)
            groups[row.away_team_id].append(row)
        
        result: dict[UUID, list[LastFixtureDTO]] = {}
        for team_id, team_rows in groups.items():
            sorted_rows = sorted(team_rows, key=lambda r: r.match_date, reverse=True)
            last_rows = sorted_rows[:max_matches_per_team]
            
            last_fixtures = []
            for row in last_rows:
                if team_id == row.home_team_id:
                    goals_for = row.home_goals
                    goals_against = row.away_goals
                    base_result = row.result
                    opponent_id = row.away_team_id
                else:
                    goals_for = row.away_goals
                    goals_against = row.home_goals
                    base_result = -row.result
                    opponent_id = row.home_team_id
                
                last_fixtures.append(LastFixtureDTO(
                    fixture_id=row.id,
                    team_id=team_id,
                    opponent_id=opponent_id,
                    goals_for=goals_for,
                    goals_against=goals_against,
                    result=base_result,
                    match_date=row.match_date
                ))
            
            result[team_id] = last_fixtures
        
        return result

    def features_from_fixtures(
        self,
        team_fixtures: dict[UUID, List[LastFixtureDTO]],
        competition_id: UUID,
        season: int
    ) -> List[MatchFeaturesDTO]:
        """
        Compute match features from team fixtures.
        
        Args:
            team_fixtures: Dict mapping team_id to list of last fixtures
            competition_id: Competition UUID
            season: Season year
        """
        result = []
        
        for team_id, fixtures in team_fixtures.items():
            if not fixtures:
                continue
            
            goals_for_last_n = sum(x.goals_for for x in fixtures)
            goals_against_last_n = sum(x.goals_against for x in fixtures)
            goals_diff_last_n = goals_for_last_n - goals_against_last_n
            last_matches_count = len(fixtures)
            
            wins_last_n = sum(1 for x in fixtures if x.result == 1)
            draws_last_n = sum(1 for x in fixtures if x.result == 0)
            losses_last_n = sum(1 for x in fixtures if x.result == -1)
            
            avg_goals_for_last_n = goals_for_last_n / last_matches_count if last_matches_count > 0 else 0.0
            avg_goals_against_last_n = goals_against_last_n / last_matches_count if last_matches_count > 0 else 0.0
            
            form_last_n = "".join(self._result_to_str(x.result) for x in fixtures)
            
            result.append(MatchFeaturesDTO(
                team_id=team_id,
                competition_id=competition_id,
                season=season,
                last_matches_count=last_matches_count,
                goals_for_last_n=goals_for_last_n,
                goals_against_last_n=goals_against_last_n,
                goals_diff_last_n=goals_diff_last_n,
                wins_last_n=wins_last_n,
                draws_last_n=draws_last_n,
                losses_last_n=losses_last_n,
                avg_goals_for_last_n=avg_goals_for_last_n,
                avg_goals_against_last_n=avg_goals_against_last_n,
                form_last_n=form_last_n
            ))
        
        return result