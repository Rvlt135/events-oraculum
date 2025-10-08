/*
  # Odds Service Schema - Initial Setup

  ## Overview
  This migration creates the core database schema for the odds-service component of Layerbit-Oraculum-AI.
  The service collects, normalizes, and stores betting odds data for football events (UEFA Champions League for MVP).

  ## New Tables

  ### 1. `sports`
  Reference table for supported sports types
  - `id` (uuid, primary key)
  - `name` (text, unique) - Sport name (e.g., "football")
  - `display_name` (text) - Human-readable name
  - `is_active` (boolean) - Whether sport is currently tracked
  - `created_at` (timestamptz)

  ### 2. `leagues`
  Reference table for sports leagues/competitions
  - `id` (uuid, primary key)
  - `sport_id` (uuid, foreign key to sports)
  - `key` (text, unique) - League identifier (e.g., "soccer_uefa_champs_league")
  - `name` (text) - League display name
  - `region` (text) - Geographic region
  - `is_active` (boolean) - Whether league is currently tracked
  - `created_at` (timestamptz)

  ### 3. `teams`
  Teams participating in events
  - `id` (uuid, primary key)
  - `name` (text) - Original team name
  - `normalized_name` (text, unique) - Normalized team name for matching
  - `sport_id` (uuid, foreign key to sports)
  - `external_ids` (jsonb) - Mapping of external API IDs
  - `created_at` (timestamptz)
  - `updated_at` (timestamptz)

  ### 4. `events`
  Betting events (matches/games)
  - `id` (uuid, primary key)
  - `external_id` (text, unique) - External API event ID
  - `sport_id` (uuid, foreign key to sports)
  - `league_id` (uuid, foreign key to leagues)
  - `home_team_id` (uuid, foreign key to teams)
  - `away_team_id` (uuid, foreign key to teams)
  - `commence_time` (timestamptz) - When the event starts
  - `status` (text) - Event status (upcoming, live, completed, cancelled)
  - `metadata` (jsonb) - Additional event data
  - `created_at` (timestamptz)
  - `updated_at` (timestamptz)

  ### 5. `bookmakers`
  Reference table for bookmakers/sportsbooks
  - `id` (uuid, primary key)
  - `key` (text, unique) - Bookmaker identifier from API
  - `name` (text) - Display name
  - `region` (text) - Operating region
  - `is_active` (boolean) - Whether bookmaker is tracked
  - `created_at` (timestamptz)

  ### 6. `odds_snapshots`
  Raw odds data snapshots from API calls
  - `id` (uuid, primary key)
  - `event_id` (uuid, foreign key to events)
  - `bookmaker_id` (uuid, foreign key to bookmakers)
  - `market_type` (text) - Market type (h2h, spreads, totals)
  - `outcomes` (jsonb) - Raw outcomes data with odds
  - `timestamp_source` (timestamptz) - Timestamp from API provider
  - `timestamp_ingested` (timestamptz) - When data was ingested
  - `created_at` (timestamptz)

  ### 7. `normalized_odds`
  Normalized and aggregated odds data
  - `id` (uuid, primary key)
  - `event_id` (uuid, foreign key to events)
  - `market_type` (text) - Market type
  - `home_odds_avg` (numeric) - Average home team odds
  - `away_odds_avg` (numeric) - Average away team odds
  - `draw_odds_avg` (numeric) - Average draw odds (nullable)
  - `home_odds_best` (numeric) - Best home team odds
  - `away_odds_best` (numeric) - Best away team odds
  - `draw_odds_best` (numeric) - Best draw odds (nullable)
  - `bookmakers_count` (integer) - Number of bookmakers
  - `timestamp_normalized` (timestamptz) - When normalization occurred
  - `created_at` (timestamptz)

  ## Security
  - Enable RLS on all tables
  - Add policies for service role access (required for backend services)

  ## Indexes
  - Performance indexes on frequently queried columns
  - Composite indexes for common query patterns
*/

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

CREATE TABLE IF NOT EXISTS sports (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  name TEXT UNIQUE NOT NULL,
  display_name TEXT NOT NULL,
  is_active BOOLEAN DEFAULT true,
  created_at TIMESTAMPTZ DEFAULT now()
);

ALTER TABLE sports ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Service role has full access to sports"
  ON sports
  FOR ALL
  USING (true);

CREATE TABLE IF NOT EXISTS leagues (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  sport_id UUID NOT NULL REFERENCES sports(id) ON DELETE CASCADE,
  key TEXT UNIQUE NOT NULL,
  name TEXT NOT NULL,
  region TEXT NOT NULL,
  is_active BOOLEAN DEFAULT true,
  created_at TIMESTAMPTZ DEFAULT now()
);

ALTER TABLE leagues ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Service role has full access to leagues"
  ON leagues
  FOR ALL
  USING (true);

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

ALTER TABLE teams ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Service role has full access to teams"
  ON teams
  FOR ALL
  USING (true);

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

ALTER TABLE events ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Service role has full access to events"
  ON events
  FOR ALL
  USING (true);

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

ALTER TABLE bookmakers ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Service role has full access to bookmakers"
  ON bookmakers
  FOR ALL
  USING (true);

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

ALTER TABLE odds_snapshots ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Service role has full access to odds_snapshots"
  ON odds_snapshots
  FOR ALL
  USING (true);

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
  timestamp_normalized TIMESTAMPTZ DEFAULT now(),
  created_at TIMESTAMPTZ DEFAULT now()
);

ALTER TABLE normalized_odds ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Service role has full access to normalized_odds"
  ON normalized_odds
  FOR ALL
  USING (true);

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
