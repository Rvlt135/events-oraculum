import pytest

from app.utils.text_utils import create_team_slug, match_slug, slugs_match


"""
pytest app/tests/test_team_slug_matching.py::test_epl_slug_names -v -s
pytest app/tests/test_team_slug_matching.py::test_uefa_champs_league_slug_names -v -s
pytest app/tests/test_team_slug_matching.py -v
pytest app/tests/ -v
pytest -v
pytest app/tests/test_team_slug_matching.py -v -s
"""

def test_epl_slug_names(capsys):
    """
    Test team slug matching for English Premier League teams.
    """
    api_slugs = ["fulham", "aston-villa", "west-ham", "manchester-united", "brentford", "wolves", "chelsea", "burnley", "liverpool", "newcastle", "leeds", "arsenal", "tottenham", "bournemouth", "crystal-palace", "manchester-city", "nottingham-forest", "everton", "sunderland", "brighton"]

    odds_team_names = [
    "Arsenal",
    "Aston Villa",
    "Bournemouth",
    "Brentford",
    "Brighton and Hove Albion",
    "Burnley",
    "Chelsea",
    "Crystal Palace",
    "Everton",
    "Fulham",
    "Leeds United",
    "Liverpool",
    "Manchester City",
    "Manchester United",
    "Newcastle United",
    "Nottingham Forest",
    "Sunderland",
    "Tottenham Hotspur",
    "West Ham United",
    "Wolverhampton Wanderers"
]

    for raw_name in odds_team_names:
        odds_slug = create_team_slug(raw_name)
        matched_slug = match_slug(odds_slug, api_slugs)

        # Проверяем, что функция отрабатывает без ошибок и возвращает либо None, либо строку
        assert matched_slug is None or isinstance(matched_slug, str)

        # Выводим для дебага
        print(f"raw={raw_name!r}, odds_slug={odds_slug!r}, matched={matched_slug!r}")


def test_uefa_champs_league_slug_names(capsys):
    """
    Test team slug matching for UEFA Champions League teams.
    """
    # TODO: заменить api_slugs на реальные значения из Redis-кэша competitions (UEFA Champions League)
    api_slugs = ["fc-basel-1893", "manchester-city", "servette-fc", "sturm-graz", "bayern-munchen", "bayer-leverkusen", "buducnost-podgorica", "malmo-ff", "ajax", "plzen", "chelsea", "virtus", "nice", "benfica", "feyenoord", "atalanta", "shkendija", "villarreal", "kups", "fc-copenhagen", "club-brugge-kv", "athletic-club", "fc-levadia-tallinn", "celtic", "qarabag", "bodoglimt", "breidablik", "zrinjski", "fenerbahce", "real-madrid", "rgas-fs", "juventus", "galatasaray", "hamrun-spartans", "monaco", "lech-poznan", "ludogorets", "slavia-praha", "shelbourne", "panathinaikos", "vikingur-gota", "inter", "barcelona", "borussia-dortmund", "dynamo-kyiv", "slovan-bratislava", "kairat-almaty", "sporting-cp", "atletico-madrid", "marseille", "pafos", "linfield", "newcastle", "egnatia-rrogozhin", "maccabi-tel-aviv", "olimpija-ljubljana", "eintracht-frankfurt", "fc-noah", "fcsb", "fk-crvena-zvezda", "inter-club-descaldes", "liverpool", "hnk-rijeka", "union-st-gilloise", "dinamo-minsk", "saburtalo", "arsenal", "lincoln-red-imps-fc", "fk-zalgiris-vilnius", "paris-saint-germain", "rangers", "brann", "napoli", "tottenham", "drita", "milsami-orhei", "psv-eindhoven", "ferencvarosi-tc", "olympiakos-piraeus", "red-bull-salzburg", "the-new-saints", "fc-differdange-03"]

    # TODO: заменить odds_team_names на реальные имена из odds-api для UEFA Champions League
    odds_team_names = [
    "Ajax", "AS Monaco", "Atalanta BC", "Athletic Bilbao", "Atlético Madrid",
    "Barcelona", "Bayer Leverkusen", "Bayern Munich", "Benfica", "Bodø/Glimt",
    "Borussia Dortmund", "Chelsea", "Club Brugge", "Eintracht Frankfurt",
    "FC Copenhagen", "FC Kairat", "Galatasaray", "Inter Milan", "Juventus",
    "Liverpool", "Manchester City", "Marseille", "Napoli", "Newcastle United",
    "Olympiakos Piraeus", "PSV Eindhoven", "Pafos FC", "Paris Saint Germain",
    "Qarabağ FK", "Real Madrid", "Slavia Praha", "Sporting Lisbon",
    "Tottenham Hotspur", "Union Saint-Gilloise", "Villarreal", "Arsenal"
]

    for raw_name in odds_team_names:
        odds_slug = create_team_slug(raw_name)
        matched_slug = match_slug(odds_slug, api_slugs)

        # Проверяем, что функция отрабатывает без ошибок и возвращает либо None, либо строку
        assert matched_slug is None or isinstance(matched_slug, str)

        # Выводим для дебага
        print(f"raw={raw_name!r}, odds_slug={odds_slug!r}, matched={matched_slug!r}")

