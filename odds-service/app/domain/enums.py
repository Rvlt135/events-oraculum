from enum import Enum


class Provider(str, Enum):
    THE_ODDS_API = "the_odds_api"

class Region(str, Enum):
    EU = "eu"
    US = "us"
    UK = "uk"
    AU = "au"

class MarketType(str, Enum):
    H2H = "h2h"
    SPREADS = "spreads"
    TOTALS = "totals"


class SportType(str, Enum):
    FOOTBALL = "football"
    BASKETBALL = "basketball"
    TENNIS = "tennis"
    HOCKEY = "hockey"


class EventStatus(str, Enum):
    UPCOMING = "upcoming"
    LIVE = "live"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
