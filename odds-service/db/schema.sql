CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

CREATE TABLE IF NOT EXISTS sports (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  name TEXT UNIQUE NOT NULL,
  display_name TEXT NOT NULL,
  is_active BOOLEAN DEFAULT true,
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS leagues (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  sport_id UUID NOT NULL REFERENCES sports(id) ON DELETE CASCADE,
  key TEXT UNIQUE NOT NULL,
  name TEXT NOT NULL,
  region TEXT NOT NULL,
  is_active BOOLEAN DEFAULT true,
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_leagues_sport_id ON leagues(sport_id);
CREATE INDEX IF NOT EXISTS idx_leagues_is_active ON leagues(is_active);

CREATE TABLE IF NOT EXISTS teams (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  name TEXT NOT NULL,
  normalized_name TEXT UNIQUE NOT NULL,
  sport_id UUID NOT NULL REFERENCES sports(id) ON DELETE CASCADE,
  external_ids JSONB DEFAULT '{}',
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_teams_sport_id ON teams(sport_id);
CREATE INDEX IF NOT EXISTS idx_teams_normalized_name ON teams(normalized_name);

CREATE TABLE IF NOT EXISTS events (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  external_id TEXT UNIQUE NOT NULL,
  sport_id UUID NOT NULL REFERENCES sports(id) ON DELETE CASCADE,
  league_id UUID NOT NULL REFERENCES leagues(id) ON DELETE CASCADE,
  home_team_id UUID NOT NULL REFERENCES teams(id) ON DELETE CASCADE,
  away_team_id UUID NOT NULL REFERENCES teams(id) ON DELETE CASCADE,
  commence_time TIMESTAMPTZ NOT NULL,
  status TEXT DEFAULT 'upcoming',
  metadata JSONB DEFAULT '{}',
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_events_sport_id ON events(sport_id);
CREATE INDEX IF NOT EXISTS idx_events_league_id ON events(league_id);
CREATE INDEX IF NOT EXISTS idx_events_commence_time ON events(commence_time);
CREATE INDEX IF NOT EXISTS idx_events_status ON events(status);
CREATE INDEX IF NOT EXISTS idx_events_external_id ON events(external_id);

CREATE TABLE IF NOT EXISTS bookmakers (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  key TEXT UNIQUE NOT NULL,
  name TEXT NOT NULL,
  region TEXT NOT NULL,
  is_active BOOLEAN DEFAULT true,
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_bookmakers_key ON bookmakers(key);
CREATE INDEX IF NOT EXISTS idx_bookmakers_is_active ON bookmakers(is_active);

CREATE TABLE IF NOT EXISTS odds_snapshots (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  event_id UUID NOT NULL REFERENCES events(id) ON DELETE CASCADE,
  bookmaker_id UUID NOT NULL REFERENCES bookmakers(id) ON DELETE CASCADE,
  market_type TEXT NOT NULL,
  outcomes JSONB NOT NULL,
  timestamp_source TIMESTAMPTZ NOT NULL,
  timestamp_ingested TIMESTAMPTZ DEFAULT now(),
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_odds_snapshots_event_id ON odds_snapshots(event_id);
CREATE INDEX IF NOT EXISTS idx_odds_snapshots_bookmaker_id ON odds_snapshots(bookmaker_id);
CREATE INDEX IF NOT EXISTS idx_odds_snapshots_market_type ON odds_snapshots(market_type);
CREATE INDEX IF NOT EXISTS idx_odds_snapshots_timestamp_ingested ON odds_snapshots(timestamp_ingested DESC);

CREATE TABLE IF NOT EXISTS normalized_odds (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  event_id UUID NOT NULL REFERENCES events(id) ON DELETE CASCADE,
  market_type TEXT NOT NULL,
  home_odds_avg NUMERIC(10,2) NOT NULL,
  away_odds_avg NUMERIC(10,2) NOT NULL,
  draw_odds_avg NUMERIC(10,2),
  home_odds_best NUMERIC(10,2) NOT NULL,
  away_odds_best NUMERIC(10,2) NOT NULL,
  draw_odds_best NUMERIC(10,2),
  bookmakers_count INTEGER NOT NULL DEFAULT 0,
  timestamp_source TIMESTAMPTZ NOT NULL,
  timestamp_ingested TIMESTAMPTZ NOT NULL,
  timestamp_normalized TIMESTAMPTZ DEFAULT now(),
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_normalized_odds_event_id ON normalized_odds(event_id);
CREATE INDEX IF NOT EXISTS idx_normalized_odds_market_type ON normalized_odds(market_type);
CREATE INDEX IF NOT EXISTS idx_normalized_odds_timestamp_normalized ON normalized_odds(timestamp_normalized DESC);

INSERT INTO sports (name, display_name, is_active)
VALUES ('football', 'Football (Soccer)', true)
ON CONFLICT (name) DO NOTHING;

INSERT INTO leagues (sport_id, key, name, region, is_active)
SELECT
  s.id,
  'soccer_uefa_champs_league',
  'UEFA Champions League',
  'eu',
  true
FROM sports s
WHERE s.name = 'football'
ON CONFLICT (key) DO NOTHING;
