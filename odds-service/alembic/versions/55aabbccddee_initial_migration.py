"""initial_migration_create_all_tables

Revision ID: 55aabbccddee
Revises: 
Create Date: 2025-01-10 14:00:00.000000

This migration creates all tables for the odds-service database.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '55aabbccddee'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema: Create all tables from scratch."""
    
    # Create UUID extension
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')
    
    # Create sports table
    op.create_table(
        'sports',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('provider', sa.Text(), nullable=False, server_default='odds_api'),
        sa.Column('category', sa.Text(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('provider', 'category', name='uq_sports_provider_category')
    )
    op.create_index('idx_sports_is_active', 'sports', ['is_active'])
    
    # Create competitions table
    op.create_table(
        'competitions',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('sport_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('title', sa.Text(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('provider', sa.Text(), nullable=False, server_default='odds_api'),
        sa.Column('provider_key', sa.Text(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.ForeignKeyConstraint(['sport_id'], ['sports.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('provider', 'provider_key', name='uq_competitions_provider_key')
    )
    op.create_index('idx_competitions_sport_id', 'competitions', ['sport_id'])
    op.create_index('idx_competitions_is_active', 'competitions', ['is_active'])
    
    # Create teams table
    op.create_table(
        'teams',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.Text(), nullable=False),
        sa.Column('normalized_name', sa.Text(), nullable=False),
        sa.Column('sport_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('external_ids', postgresql.JSONB(astext_type=sa.Text()), server_default='{}'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.ForeignKeyConstraint(['sport_id'], ['sports.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('normalized_name')
    )
    op.create_index('idx_teams_sport_id', 'teams', ['sport_id'])
    op.create_index('idx_teams_normalized_name', 'teams', ['normalized_name'])
    
    # Create events table
    op.create_table(
        'events',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('external_id', sa.Text(), nullable=False),
        sa.Column('sport_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('competition_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('home_team_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('away_team_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('commence_time', sa.DateTime(timezone=True), nullable=False),
        sa.Column('status', sa.Text(), server_default='upcoming'),
        sa.Column('event_metadata', postgresql.JSONB(astext_type=sa.Text()), server_default='{}'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.ForeignKeyConstraint(['sport_id'], ['sports.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['competition_id'], ['competitions.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['home_team_id'], ['teams.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['away_team_id'], ['teams.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('external_id')
    )
    op.create_index('idx_events_sport_id', 'events', ['sport_id'])
    op.create_index('idx_events_competition_id', 'events', ['competition_id'])
    op.create_index('idx_events_commence_time', 'events', ['commence_time'])
    op.create_index('idx_events_status', 'events', ['status'])
    op.create_index('idx_events_external_id', 'events', ['external_id'])
    
    # Create bookmakers table
    op.create_table(
        'bookmakers',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('key', sa.Text(), nullable=False),
        sa.Column('name', sa.Text(), nullable=False),
        sa.Column('region', sa.Text(), nullable=False),
        sa.Column('is_active', sa.Boolean(), server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('key')
    )
    op.create_index('idx_bookmakers_key', 'bookmakers', ['key'])
    op.create_index('idx_bookmakers_is_active', 'bookmakers', ['is_active'])
    
    # Create odds_snapshots table
    op.create_table(
        'odds_snapshots',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('event_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('bookmaker_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('market_type', sa.Text(), nullable=False),
        sa.Column('outcomes', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('timestamp_source', sa.DateTime(timezone=True), nullable=False),
        sa.Column('timestamp_ingested', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['event_id'], ['events.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['bookmaker_id'], ['bookmakers.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_odds_snapshots_event_id', 'odds_snapshots', ['event_id'])
    op.create_index('idx_odds_snapshots_bookmaker_id', 'odds_snapshots', ['bookmaker_id'])
    op.create_index('idx_odds_snapshots_market_type', 'odds_snapshots', ['market_type'])
    op.create_index('idx_odds_snapshots_timestamp_ingested', 'odds_snapshots', ['timestamp_ingested'], postgresql_ops={'timestamp_ingested': 'DESC'})
    
    # Create normalized_odds table
    op.create_table(
        'normalized_odds',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('event_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('market_type', sa.Text(), nullable=False),
        sa.Column('home_odds_avg', sa.Numeric(10, 2), nullable=False),
        sa.Column('away_odds_avg', sa.Numeric(10, 2), nullable=False),
        sa.Column('draw_odds_avg', sa.Numeric(10, 2), nullable=True),
        sa.Column('home_odds_best', sa.Numeric(10, 2), nullable=False),
        sa.Column('away_odds_best', sa.Numeric(10, 2), nullable=False),
        sa.Column('draw_odds_best', sa.Numeric(10, 2), nullable=True),
        sa.Column('bookmakers_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('timestamp_source', sa.DateTime(timezone=True), nullable=False),
        sa.Column('timestamp_ingested', sa.DateTime(timezone=True), nullable=False),
        sa.Column('timestamp_normalized', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['event_id'], ['events.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_normalized_odds_event_id', 'normalized_odds', ['event_id'])
    op.create_index('idx_normalized_odds_market_type', 'normalized_odds', ['market_type'])
    op.create_index('idx_normalized_odds_timestamp_normalized', 'normalized_odds', ['timestamp_normalized'], postgresql_ops={'timestamp_normalized': 'DESC'})


def downgrade() -> None:
    """Downgrade schema: Drop all tables."""
    op.drop_index('idx_normalized_odds_timestamp_normalized', table_name='normalized_odds')
    op.drop_index('idx_normalized_odds_market_type', table_name='normalized_odds')
    op.drop_index('idx_normalized_odds_event_id', table_name='normalized_odds')
    op.drop_table('normalized_odds')
    
    op.drop_index('idx_odds_snapshots_timestamp_ingested', table_name='odds_snapshots')
    op.drop_index('idx_odds_snapshots_market_type', table_name='odds_snapshots')
    op.drop_index('idx_odds_snapshots_bookmaker_id', table_name='odds_snapshots')
    op.drop_index('idx_odds_snapshots_event_id', table_name='odds_snapshots')
    op.drop_table('odds_snapshots')
    
    op.drop_index('idx_bookmakers_is_active', table_name='bookmakers')
    op.drop_index('idx_bookmakers_key', table_name='bookmakers')
    op.drop_table('bookmakers')
    
    op.drop_index('idx_events_external_id', table_name='events')
    op.drop_index('idx_events_status', table_name='events')
    op.drop_index('idx_events_commence_time', table_name='events')
    op.drop_index('idx_events_competition_id', table_name='events')
    op.drop_index('idx_events_sport_id', table_name='events')
    op.drop_table('events')
    
    op.drop_index('idx_teams_normalized_name', table_name='teams')
    op.drop_index('idx_teams_sport_id', table_name='teams')
    op.drop_table('teams')
    
    op.drop_index('idx_competitions_is_active', table_name='competitions')
    op.drop_index('idx_competitions_sport_id', table_name='competitions')
    op.drop_table('competitions')
    
    op.drop_index('idx_sports_is_active', table_name='sports')
    op.drop_table('sports')
