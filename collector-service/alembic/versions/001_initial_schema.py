"""initial_schema

Revision ID: 001_initial_schema
Revises: 
Create Date: 2025-11-20 21:06:42.672000

Initial database schema for collector-service.
All tables with current structure including slug_key in competitions and event_priorities.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '001_initial_schema'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create all tables with current schema or migrate existing ones."""
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing_tables = inspector.get_table_names()
    
    # Create UUID extension
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')
    
    # Rename provider_key to slug_key in existing tables if needed
    rename_tables = [
        ('competitions', 'uq_competitions_provider_key', 'uq_competitions_slug_key'),
        ('event_priorities', 'uq_event_priorities_provider_key_event_id', 'uq_event_priorities_slug_key_event_id'),
    ]
    
    for table_name, old_constraint, new_constraint in rename_tables:
        if table_name in existing_tables:
            columns = {col['name']: col for col in inspector.get_columns(table_name)}
            if 'provider_key' in columns and 'slug_key' not in columns:
                op.execute(sa.text(f"ALTER TABLE {table_name} RENAME COLUMN provider_key TO slug_key"))
                inspector = sa.inspect(conn)
            constraints = inspector.get_unique_constraints(table_name)
            for constraint in constraints:
                if constraint['name'] == old_constraint:
                    op.execute(sa.text(f"ALTER TABLE {table_name} RENAME CONSTRAINT {old_constraint} TO {new_constraint}"))
                    break
    
    # Create sports table
    if 'sports' not in existing_tables:
        op.create_table(
            'sports',
            sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column('provider', sa.Text(), nullable=False, server_default='odds_api'),
            sa.Column('category', sa.Text(), nullable=False),
            sa.Column('is_active', sa.Boolean(), nullable=False),
            sa.Column('plan_visibility', sa.Text(), nullable=False, server_default='free'),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('provider', 'category', name='uq_sports_provider_category')
        )
        op.create_index('idx_sports_is_active', 'sports', ['is_active'])
    
    # Create competitions table (with slug_key)
    if 'competitions' not in existing_tables:
        op.create_table(
            'competitions',
            sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column('sport_id', postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column('title', sa.Text(), nullable=False),
            sa.Column('description', sa.Text(), nullable=True),
            sa.Column('provider', sa.Text(), nullable=False, server_default='odds_api'),
            sa.Column('slug_key', sa.Text(), nullable=False),
            sa.Column('is_active', sa.Boolean(), nullable=False),
            sa.Column('plan_visibility', sa.Text(), nullable=False, server_default='free'),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
            sa.ForeignKeyConstraint(['sport_id'], ['sports.id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('provider', 'slug_key', name='uq_competitions_slug_key')
        )
        op.create_index('idx_competitions_sport_id', 'competitions', ['sport_id'])
        op.create_index('idx_competitions_is_active', 'competitions', ['is_active'])
    
    # Create teams table
    if 'teams' not in existing_tables:
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
            sa.UniqueConstraint('sport_id', 'normalized_name', name='uq_teams_sport_normalized_name')
        )
        op.create_index('idx_teams_sport_id', 'teams', ['sport_id'])
        op.create_index('idx_teams_sport_normalized_name', 'teams', ['sport_id', 'normalized_name'])
    
    # Create events table
    if 'events' not in existing_tables:
        op.create_table(
            'events',
            sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column('provider', sa.Text(), nullable=False, server_default='odds_api'),
            sa.Column('external_id', sa.Text(), nullable=False),
            sa.Column('sport_id', postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column('competition_id', postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column('home_team_id', postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column('away_team_id', postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column('home_team_name', sa.Text(), nullable=True),
            sa.Column('away_team_name', sa.Text(), nullable=True),
            sa.Column('commence_time', sa.DateTime(timezone=True), nullable=False),
            sa.Column('status', sa.Text(), server_default='upcoming'),
            sa.Column('participant_mode', sa.Text(), nullable=False, server_default='unknown'),
            sa.Column('participants', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='[]'),
            sa.Column('event_metadata', postgresql.JSONB(astext_type=sa.Text()), server_default='{}'),
            sa.Column('ingested_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('last_seen_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
            sa.ForeignKeyConstraint(['sport_id'], ['sports.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['competition_id'], ['competitions.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['home_team_id'], ['teams.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['away_team_id'], ['teams.id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('provider', 'external_id', name='uq_events_provider_external_id'),
            sa.CheckConstraint(
                "participant_mode IN ('duel', 'solo', 'field', 'unknown')",
                name='chk_events_participant_mode'
            )
        )
        op.create_index('idx_events_sport_id', 'events', ['sport_id'])
        op.create_index('idx_events_competition_id', 'events', ['competition_id'])
        op.create_index('idx_events_commence_time', 'events', ['commence_time'])
        op.create_index('idx_events_status', 'events', ['status'])
        op.create_index('idx_events_external_id', 'events', ['external_id'])
        op.create_index('idx_events_competition_commence', 'events', ['competition_id', 'commence_time'])
    
    # Create bookmakers table
    if 'bookmakers' not in existing_tables:
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
    if 'odds_snapshots' not in existing_tables:
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
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('event_id', 'bookmaker_id', 'market_type', name='uq_odds_snapshots_event_book_mkt')
        )
        op.create_index('idx_odds_snapshots_event_id', 'odds_snapshots', ['event_id'])
        op.create_index('idx_odds_snapshots_bookmaker_id', 'odds_snapshots', ['bookmaker_id'])
        op.create_index('idx_odds_snapshots_market_type', 'odds_snapshots', ['market_type'])
        op.create_index('idx_odds_snapshots_timestamp_ingested', 'odds_snapshots', ['timestamp_ingested'], postgresql_ops={'timestamp_ingested': 'DESC'})
    
    # Create normalized_odds table
    if 'normalized_odds' not in existing_tables:
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
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('event_id', 'market_type', name='uq_normalized_odds_event_market')
        )
        op.create_index('idx_normalized_odds_event_id', 'normalized_odds', ['event_id'])
        op.create_index('idx_normalized_odds_market_type', 'normalized_odds', ['market_type'])
        op.create_index('idx_normalized_odds_timestamp_normalized', 'normalized_odds', ['timestamp_normalized'], postgresql_ops={'timestamp_normalized': 'DESC'})
    
    # Create event_priorities table (with slug_key)
    if 'event_priorities' not in existing_tables:
        op.create_table(
            'event_priorities',
            sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column('provider', sa.Text(), nullable=False),
            sa.Column('slug_key', sa.Text(), nullable=False),
            sa.Column('event_id', postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column('priority', sa.Numeric(4, 3), nullable=False),
            sa.Column('model', sa.Text(), nullable=False),
            sa.Column('evaluated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column('meta', postgresql.JSONB(astext_type=sa.Text()), nullable=True, server_default='{}'),
            sa.ForeignKeyConstraint(['event_id'], ['events.id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('slug_key', 'event_id', name='uq_event_priorities_slug_key_event_id')
        )
        op.create_index(
            'idx_event_priorities_slug_key_priority',
            'event_priorities',
            ['slug_key', 'priority'],
            postgresql_ops={'priority': 'DESC'}
        )
        op.create_index('idx_event_priorities_event_id', 'event_priorities', ['event_id'])
        op.create_index('idx_event_priorities_evaluated_at', 'event_priorities', ['evaluated_at'])


def downgrade() -> None:
    """Drop all tables."""
    op.drop_index('idx_event_priorities_evaluated_at', table_name='event_priorities')
    op.drop_index('idx_event_priorities_event_id', table_name='event_priorities')
    op.drop_index('idx_event_priorities_slug_key_priority', table_name='event_priorities')
    op.drop_table('event_priorities')
    
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
    
    op.drop_index('idx_events_competition_commence', table_name='events')
    op.drop_index('idx_events_external_id', table_name='events')
    op.drop_index('idx_events_status', table_name='events')
    op.drop_index('idx_events_commence_time', table_name='events')
    op.drop_index('idx_events_competition_id', table_name='events')
    op.drop_index('idx_events_sport_id', table_name='events')
    op.drop_table('events')
    
    op.drop_index('idx_teams_sport_normalized_name', table_name='teams')
    op.drop_index('idx_teams_sport_id', table_name='teams')
    op.drop_table('teams')
    
    op.drop_index('idx_competitions_is_active', table_name='competitions')
    op.drop_index('idx_competitions_sport_id', table_name='competitions')
    op.drop_table('competitions')
    
    op.drop_index('idx_sports_is_active', table_name='sports')
    op.drop_table('sports')

